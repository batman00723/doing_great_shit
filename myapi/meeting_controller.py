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

class MeetingRequest(Schema):
    transcript: str

@api_controller("/analyse", tags= ['Transcript → Report'])
class MeetingOperationController(ControllerBase):
    @http_post("/report")
    def agent(self, request, payload: MeetingRequest):
        print("starting to call agent")

        try:
            response = process_transcript(payload.transcript)

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
    @http_post("/analyse")
    def analyse_audio(self, request, audio_file: UploadedFile= File(...)):
        print("Agent Started")

        os.makedirs("recordings", exist_ok=True)  
        file_path = f"recordings/{uuid.uuid4()}_{audio_file.name}"
        
        try:

            with open(file_path, "wb+") as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            response = process_audio(file_path)

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


