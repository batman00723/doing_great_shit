# since langchain doesnt provide sst model wrapper so im using groq raw
from groq import Groq
from backend.config import settings

client= Groq(
    api_key= settings.groq_api_key.get_secret_value()
)

def transcribe_audio(file_path: str):
    with open(file_path, "rb") as audio_file:
        transcription= client.audio.transcriptions.create(
            file=audio_file,
            model= "whisper-large-v3"
        )
    print(transcription.text)
    return transcription.text