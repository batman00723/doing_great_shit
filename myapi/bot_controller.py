import requests
from ninja_extra import ControllerBase, api_controller, http_post
from ninja import Schema
from backend.config import settings
from myapi.auth_controller import JWTAuth
from myapi.services.transcript_processor import process_transcript
from myapi.models import User

# ── Schemas ─────────────────────────────────────────────────────────────────
class DeployBotSchema(Schema):
    meeting_url: str
    customer_id: int

# Since Webhooks come from outside and have varying shapes, we often just use dict
# but we can define a basic schema if we know Recall's payload. 
# For now, we will accept any dict.


# ── Controller ──────────────────────────────────────────────────────────────
@api_controller("/bot", tags=["Recall AI Integration"])
class BotController(ControllerBase):

    @http_post("/deploy", auth=JWTAuth())
    def deploy_bot(self, request, payload: DeployBotSchema):
        """
        Salesperson pastes a link here. We attach their user_id to the metadata 
        and tell Recall.ai to join the meeting.
        """
        api_key = settings.recall_api_key.get_secret_value() if settings.recall_api_key else None
        if not api_key:
            return self.create_response("RECALL_API_KEY is not configured.", status_code=500)
            
        url = "https://api.recall.ai/api/v1/bot"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "meeting_url": payload.meeting_url,
            "bot_name": "Alura AI Notetaker",
            # We attach this so the webhook knows exactly who requested it!
            "metadata": {
                "user_id": request.user.id,
                "customer_id": payload.customer_id
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            bot_data = response.json()
            return {
                "message": "Bot deployed successfully!",
                "bot_id": bot_data.get("id"),
                "status": "recording"
            }
        else:
            return self.create_response(
                {"message": "Failed to deploy bot", "details": response.text}, 
                status_code=400
            )

    @http_post("/webhook")
    def recall_webhook(self, request, payload: dict):
        """
        Recall.ai hits this endpoint when the meeting finishes.
        We extract the transcript, look up the user from metadata, 
        and run our LangGraph pipeline to generate and save everything!
        """
        event_type = payload.get("event")
        data = payload.get("data", {})
        
        # We only care when the bot finishes and the transcript is fully ready
        if event_type == "bot.status_change" and data.get("status") == "done":
            bot_id = data.get("bot_id")
            metadata = data.get("metadata", {})
            user_id = metadata.get("user_id")
            customer_id = metadata.get("customer_id")
            
            if not user_id or not customer_id:
                return {"message": "Ignored. Missing user_id or customer_id in metadata."}
                
            try:
                user = User.objects.get(id=user_id)
                from myapi.models import Customer
                customer = Customer.objects.get(id=customer_id)
            except (User.DoesNotExist, Customer.DoesNotExist):
                return {"message": "User or Customer not found."}
                
            # 1. Fetch the actual transcript from Recall.ai
            # (Recall usually sends it in another webhook or you fetch it via API)
            # For this MVP flow, if it's in the payload, we grab it, 
            # otherwise we fetch it using the bot_id.
            
            api_key = settings.recall_api_key.get_secret_value() if settings.recall_api_key else None
            transcript_url = f"https://api.recall.ai/api/v1/bot/{bot_id}/transcript"
            
            headers = {"Authorization": f"Token {api_key}"}
            t_res = requests.get(transcript_url, headers=headers)
            
            if t_res.status_code == 200:
                # Format the transcript into a single string for our pipeline
                transcript_data = t_res.json()
                # Recall returns a list of words or blocks. Let's assume we extract raw text:
                full_text = ""
                for chunk in transcript_data:
                    full_text += f"{chunk.get('speaker', 'Unknown')}: {chunk.get('text', '')}\n"
                
                # 2. Feed it into our beautiful RAG pipeline!
                # This will automatically create the Meeting row and save the vectors.
                process_transcript(full_text, user, customer)
                
                return {"message": "Meeting processed and saved to database!"}
            else:
                return {"message": "Failed to fetch transcript from Recall.ai"}
                
        return {"message": "Event received, no action taken."}
