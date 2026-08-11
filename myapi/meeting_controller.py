from ninja_extra import ControllerBase, api_controller, http_post, http_get
from backend.config import settings
import logging
from ninja import Schema
from myapi.services.transcript_processor import process_transcript
from ninja import File
from ninja.files import UploadedFile
import os
import uuid
from myapi.services.process_audio import process_audio
from myapi.auth_controller import JWTAuth

class MeetingRequest(Schema):
    transcript: str
    customer_id: int

class EditReportSchema(Schema):
    html_report: str

class SendEmailSchema(Schema):
    recipient_email: str



@api_controller("/analyse", tags= ['Transcript → Report'])
class MeetingOperationController(ControllerBase):
    @http_post("/report", auth=JWTAuth())
    def agent(self, request, payload: MeetingRequest):
        print("starting to call agent")

        try:
            from myapi.models import Customer
            customer = Customer.objects.get(id=payload.customer_id)
            response = process_transcript(payload.transcript, request.user, customer)

            return {
                "analysis": response
            }
            
        except Exception as e:
            logger= logging.getLogger(__name__)
            logger.error(f"Agent Execution Error: {str(e)}", exc_info= True)

            return {
                "message": "Agent Execution Falied",
                "details": str(e) if settings.debug else "Internal Server Error"
            }

    @http_get("/customer/{customer_id}", auth=JWTAuth())
    def list_customer_meetings(self, request, customer_id: int):
        from myapi.models import Meeting
        # Securely fetch meetings for this customer belonging to the logged-in user's organisation
        meetings = Meeting.objects.filter(
            customer_id=customer_id,
            organisation=request.user.organisation
        ).order_by("-meeting_date")
        
        return [
            {
                "id": m.id,
                "title": m.title,
                "meeting_date": m.meeting_date.isoformat(),
                "status": m.status
            }
            for m in meetings
        ]

    @http_get("/{meeting_id}/report", auth=JWTAuth())
    def get_meeting_report(self, request, meeting_id: int):
        from myapi.models import MeetingReport
        try:
            # Securely fetch the report ensuring it belongs to their org
            report = MeetingReport.objects.get(
                meeting_id=meeting_id,
                organisation=request.user.organisation
            )
            return {"html": report.html_report}
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found or processing not finished.", status_code=404)

    @http_post("/{meeting_id}/report", auth=JWTAuth()) # Changed to post because ninja sometimes complains about put
    def edit_meeting_report(self, request, meeting_id: int, payload: EditReportSchema):
        from myapi.models import MeetingReport
        try:
            report = MeetingReport.objects.get(
                meeting_id=meeting_id,
                organisation=request.user.organisation
            )
            report.html_report = payload.html_report
            report.save()
            return {"message": "Report updated successfully!"}
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found.", status_code=404)
            
    @http_post("/{meeting_id}/send-email", auth=JWTAuth())
    def send_report_email(self, request, meeting_id: int, payload: SendEmailSchema):
        from myapi.models import MeetingReport, Meeting
        import requests
        try:
            report = MeetingReport.objects.get(
                meeting_id=meeting_id,
                organisation=request.user.organisation
            )
            meeting = report.meeting
            
            api_key = settings.brevo_api_key.get_secret_value() if settings.brevo_api_key else None
            if not api_key:
                return self.create_response("Brevo API key not configured.", status_code=500)
                
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            }
            
            data = {
                "sender": {
                    "name": request.user.salesperson_name,
                    "email": request.user.email
                },
                "to": [{"email": payload.recipient_email}],
                "subject": f"Meeting Report: {meeting.title}",
                "htmlContent": report.html_report
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code in [201, 202]:
                return {"message": f"Email sent successfully to {payload.recipient_email}!"}
            else:
                return self.create_response({"message": "Failed to send email", "details": response.text}, status_code=400)
                
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found.", status_code=404)
        


@api_controller("/audio", tags= ['Audio → Report'])
class AudioController(ControllerBase):
    @http_post("/analyse", auth=JWTAuth())
    def analyse_audio(self, request, customer_id: int, audio_file: UploadedFile= File(...)):
        print("Agent Started")

        os.makedirs("recordings", exist_ok=True)  
        file_path = f"recordings/{uuid.uuid4()}_{audio_file.name}"
        
        try:

            with open(file_path, "wb+") as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            from myapi.models import Customer
            customer = Customer.objects.get(id=customer_id)
            response = process_audio(file_path, request.user, customer)

            return {
                "status": "success",
                "analysis": response
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


class ChatRequest(Schema):
    query: str
    session_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    specific_date: str | None = None


@api_controller("/chat", tags=['Chatbot API'])
class ChatController(ControllerBase):
    @http_post("/ask", auth=JWTAuth())
    def ask_bot(self, request, payload: ChatRequest):
        from myapi.services.rag_retrieval_pipeline import retrieve_and_generate
        
        try:
            result = retrieve_and_generate(
                user_query=payload.query,
                user=request.user,
                session_id=payload.session_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
                specific_date=payload.specific_date
            )
            return {
                "status": "success",
                "answer": result["answer"],
                "session_id": result["session_id"]
            }
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Chatbot Error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to generate answer",
                "details": str(e) if settings.debug else "Internal Server Error"
            }

    @http_get("/history/{session_id}", auth=JWTAuth())
    def get_chat_history(self, request, session_id: str):
        from myapi.models import ChatSession, ChatTurn
        try:
            # Securely fetch the session ensuring it belongs to their org
            session = ChatSession.objects.get(
                id=session_id,
                organisation=request.user.organisation
            )
            # Fetch all turns ordered by creation time
            turns = ChatTurn.objects.filter(session=session).order_by("created_at")
            
            return [
                {
                    "id": turn.id,
                    "query": turn.query,
                    "answer": turn.answer,
                    "created_at": turn.created_at.isoformat()
                }
                for turn in turns
            ]
        except ChatSession.DoesNotExist:
            return self.create_response("Chat session not found.", status_code=404)

    @http_get("/sessions", auth=JWTAuth())
    def list_chat_sessions(self, request):
        from myapi.models import ChatSession, ChatTurn
        # Fetch all sessions for this specific salesperson, ordered newest to oldest
        sessions = ChatSession.objects.filter(
            salesperson=request.user
        ).order_by("-created_at")
        
        result = []
        for session in sessions:
            # Grab the very first question they asked to use as the "Title" in the sidebar
            first_turn = ChatTurn.objects.filter(session=session).order_by("created_at").first()
            title = first_turn.query[:40] + "..." if first_turn else "New Chat"
            
            result.append({
                "id": str(session.id),
                "title": title,
                "created_at": session.created_at.isoformat()
            })
            
        return result


