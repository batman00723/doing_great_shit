# since langchain doesnt provide sst model wrapper so im using groq raw
from groq import AsyncGroq
from backend.config import settings
import logging

logger = logging.getLogger(__name__) 


client= AsyncGroq(
    api_key= settings.groq_api_key.get_secret_value()
)

async def transcribe_audio(file_path: str):
    with open(file_path, "rb") as audio_file:
        transcription= await client.audio.transcriptions.create(
            file=audio_file,
            model= "whisper-large-v3"
        )
    logging.debug(f"Transcription: {transcription.text}")
    return transcription.text