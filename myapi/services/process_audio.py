from myapi.services.sst import transcribe_audio
from myapi.services.transcript_processor import process_transcript
import logging

logger = logging.getLogger(__name__) 

async def process_audio(audio_path: str, user, customer):
    logger.info("Audio processing started")

    try:
        transcript = await  transcribe_audio(audio_path)
        result = await process_transcript(transcript, user, customer)
        logger.info("Audio Processed")

        return result

    except Exception as e:
        logger.error(f"Audio processing failed: {e}", exc_info= True)
        raise