from ninja_extra import ControllerBase, api_controller, http_post
from backend.config import settings
import logging
from ninja import Schema
from myapi.services.transcript_processor import process_transcript

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
        


