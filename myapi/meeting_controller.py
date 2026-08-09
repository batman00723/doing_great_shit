from ninja_extra import ControllerBase, api_controller, http_post
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


