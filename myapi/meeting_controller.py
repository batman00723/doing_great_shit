from ninja_extra import ControllerBase, api_controller, http_post, http_get
from backend.config import settings
import logging
from ninja import Schema
from myapi.services.transcript_processor import process_transcript
from ninja import File
from ninja.files import UploadedFile
import os
import httpx
import uuid
from myapi.services.process_audio import process_audio
from myapi.auth_controller import JWTAuth
from myapi.models import MeetingReport, Meeting
from myapi.models import Customer
from myapi.services.rag_retrieval_pipeline import retrieve_and_generate
from myapi.models import ChatSession, ChatTurn
from datetime import timedelta
from django.utils import timezone
import asyncio

class MeetingRequest(Schema):
    transcript: str
    customer_id: int

class EditReportSchema(Schema):
    html_report: str

# set() creates a memory for background tasks so that we can keep them here and then remove them without storing background tasks in set python garbage collector will remove them from memory
# in middle of processing so we will keep track of them in set and remove them  (.discard) when that background task is done to then free up space.
# set() is a data struture in python like list but it doesnot allows duplicates so we can add and rmove background tasks without worrying about 
# duplicates and also its faster than list operations as .discard has time complexity has O(1) nd list has O(n).
BACKGROUND_TASKS = set()

# 
def schedule_background_task(coro):
    # schedule the corotuine on python evven loop
    task = asyncio.create_task(coro)

    # put the task in the set to tell python garbage ccollector that this task is still in use and not to remove it from memory
    BACKGROUND_TASKS.add(task)

    # when the task is done or crashes we will remove it from the set to free up memory
    task.add_done_callback(BACKGROUND_TASKS.discard)

    return task



# Here we need to give the customer_id by the user and in frontend it wil show a drop down of the customer name and we seslet which custoemr this report belongs to 
# and then in the recall ai webhook this will be the same the user will provide the custoemr id and recall will give it after the transcript via webhook.
# when we wil give the meetig link to the recall ai we will also give customer id via drop down link i frontend and then it will bring back the custoemr id for next steps in the report genration so we are golden.
@api_controller("/analyse", tags= ['Transcript → Report'])
class MeetingOperationController(ControllerBase):
    @http_post("/report", auth=JWTAuth())
    async def agent(self, request, payload: MeetingRequest):
        logger = logging.getLogger(__name__) 
        logger.info("starting to call agent")

        try:
            
            customer = await Customer.objects.aget(id=payload.customer_id, organisation_id=request.user.organisation_id)
            meeting_count = await Meeting.objects.filter(customer=customer).acount()
            sequential_title = f"Meeting {meeting_count + 1}"


            # Here we first create a meeting object 
            meeting = await Meeting.objects.acreate(
                organisation_id=request.user.organisation_id,
                customer=customer,
                salesperson_id=request.user.id,
                meeting_date=timezone.now(),
                duration=timedelta(),
                title=sequential_title,
                meeting_type="Sales Call",
                status= Meeting.Status.PROCESSING,
            )


            # Here we use the background task to process transcript and so it's free alternative to celery background workers but this works entirely on RAM so it can work on rander free tier.
            schedule_background_task(process_transcript(payload.transcript, request.user, customer, meeting)) # fetch the user object from the logged in user via request.user

            return {
                "status": meeting.status,
                "meeting": meeting.id,
                "title": meeting.title,
                "message": "Report generation has started"

            }
            
        except Exception as e:
            logger.error(f"Agent Execution Error: {str(e)}", exc_info= True)

            return {
                "message": "Agent Execution Falied",
                "details": str(e) if settings.debug else "Internal Server Error"
            }

    @http_get("/meetings", auth=JWTAuth())
    async def list_all_my_meetings(self, request):
        
        # Fetch all meetings for a specefic salesperson, newest first, with customer info also

        meetings = [m async for m in Meeting.objects.filter(
            salesperson=request.user
        ).select_related("customer").order_by("-meeting_date")]

        return [
            {
                "meeting_id": m.id,
                "title": m.title,
                "meeting_date": m.meeting_date.isoformat(),
                "status": m.status,
                "customer": {
                    "id": m.customer.id,
                    "customer_name": m.customer.customer_name,
                    "industry": m.customer.industry,
                    "status": m.customer.status
                }
            }
            for m in meetings
        ]

    @http_get("/customer/{customer_id}", auth=JWTAuth())
    async def list_customer_meetings(self, request, customer_id: int):
        # Securely fetch meetings for this customer belonging to the logged in salesperson
        meetings = [c async for c in Meeting.objects.filter(
            customer_id=customer_id,
            salesperson=request.user
        ).order_by("-meeting_date")]
        
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
    async def get_meeting_report(self, request, meeting_id: int):
        try:
            # Securely fetch the report ensuring it belongs to their salesperson account
            report = await MeetingReport.objects.aget(
                meeting_id=meeting_id,
                salesperson=request.user
            )
            return {"html": report.html_report}
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found or processing not finished.", status_code=404)

    @http_post("/{meeting_id}/report", auth=JWTAuth()) # Changed to post because ninja sometimes complains about put
    async def edit_meeting_report(self, request, meeting_id: int, payload: EditReportSchema):
        try:
            report = await MeetingReport.objects.aget(
                meeting_id=meeting_id,
                salesperson=request.user
            )
            report.html_report = payload.html_report
            await report.asave()
            return {"message": "Report updated successfully!"}
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found.", status_code=404)



# Here I have to change the architecture of the Email delivery so Brevo can only send maild from the verified domains only so I will 
# send it woth my comnpanys verified domain and then use replyTo and five the salesperson email address so the customers can reply to the salesperson. 
# so when the custoemer clicks on reply button when they get the mail they can reply to orignal salesperon mail account.
            
    @http_post("/{meeting_id}/send-email", auth=JWTAuth())
    async def send_report_email(self, request, meeting_id: int):
        
        try:
            report = await MeetingReport.objects.aget(
                meeting_id=meeting_id,
                salesperson=request.user
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
                    "email": "batmanmishra23@gmail.com"       
                },

                "replyTo": {                                                                                                                                                           
                    "email": request.user.email,                                                                                                                                       
                    "name": request.user.salesperson_name                                                                                                                              
                },

                "to": [{"email": meeting.customer.email}],
                "subject": f"Meeting Report: {meeting.title}",
                "htmlContent": report.html_report
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
            
            if response.status_code in [201, 202]:
                return {"message": f"Email sent successfully to {meeting.customer.email}!"}
            else:
                return self.create_response({"message": "Failed to send email", "details": response.text}, status_code=400)
                
        except MeetingReport.DoesNotExist:
            return self.create_response("Report not found.", status_code=404)
        


@api_controller("/audio", tags= ['Audio → Report'])
class AudioController(ControllerBase):
    @http_post("/analyse", auth=JWTAuth())
    async def analyse_audio(self, request, customer_id: int, audio_file: UploadedFile= File(...)):
        logger = logging.getLogger(__name__) 

        logger.info("Agent Started")

        os.makedirs("recordings", exist_ok=True)  
        file_path = f"recordings/{uuid.uuid4()}_{audio_file.name}"
        
        try:

            with open(file_path, "wb+") as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            logger.info(f"Wrote file {file_path}, size: {os.path.getsize(file_path)}")

            
            customer = await Customer.objects.aget(id=customer_id, organisation_id=request.user.organisation_id)

            meeting_count = await Meeting.objects.filter(customer=customer).acount()
            sequential_title = f"Meeting {meeting_count + 1}"


            # Here we first create a meeting object 
            meeting = await Meeting.objects.acreate(
                organisation_id=request.user.organisation_id,
                customer=customer,
                salesperson_id=request.user.id,
                meeting_date=timezone.now(),
                duration=timedelta(),
                title=sequential_title,
                meeting_type="Sales Call",
                status= Meeting.Status.PROCESSING,
            )


            schedule_background_task(process_audio(file_path, request.user, customer, meeting)) # fetch the user object from the logged in user via request.user

            return {
                "status": "pending",
                "message": "Audio analysis given to background tasks."
            }

        except Exception as e:
            logger.error(f"Error:{e}", exc_info= True)
            return {
                "status": "error",
                "message": str(e)
            }



class ChatRequest(Schema):
    query: str
    session_id: str | None = None
    customer_id: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    specific_date: str | None = None


@api_controller("/chat", tags=['Chatbot API'])
class ChatController(ControllerBase):
    @http_post("/ask", auth=JWTAuth())
    async def ask_bot(self, request, payload: ChatRequest):
        
        
        try:
            result = await retrieve_and_generate(
                user_query=payload.query,
                user=request.user,
                session_id=payload.session_id,
                customer_id=payload.customer_id,
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
    async def get_chat_history(self, request, session_id: str):
        
        try:
            # Securely fetch the session ensuring it belongs to their org
            session = await ChatSession.objects.aget(
                id=session_id,
                organisation_id=request.user.organisation_id
            )
            # Fetch all turns ordered by creation time
            turns =  [chat async for chat in ChatTurn.objects.filter(session=session).order_by("created_at")]
            
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
    async def list_chat_sessions(self, request):
        # Fetch all sessions for this specific salesperson, ordered newest to oldest
        sessions = [c async for c in ChatSession.objects.filter(
            salesperson=request.user
        ).order_by("-created_at")]
        
        result = []
        for session in sessions:
            # Grab the very first question they asked to use as the "Title" in the sidebar
            first_turn = await ChatTurn.objects.filter(session=session).order_by("created_at").afirst()
            title = first_turn.query[:40] + "..." if first_turn else "New Chat"
            
            result.append({
                "id": str(session.id),
                "title": title,
                "created_at": session.created_at.isoformat()
            })
            
        return result



@http_get("/{meeting_id}/status", auth=JWTAuth())
async def get_meeting_status(self, request, meeting_id: int):
    try:
        meeting = await Meeting.objects.aget(
            id=meeting_id,
            salesperson=request.user
        )
        return {
            "meeting_id": meeting.id,
            "title": meeting.title,
            "status": meeting.status
        }
    except Meeting.DoesNotExist:
        return self.create_response("Meeting not found.", status_code=404)