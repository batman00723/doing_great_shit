from myapi.services.sst import transcribe_audio
from myapi.services.transcript_processor import process_transcript

def process_audio(audio_path: str, user, customer):
    print("Audio processing started")

    try:
        transcript = transcribe_audio(audio_path)
        result = process_transcript(transcript, user, customer)
        print("Audio Processed")

        return result

    except Exception as e:
        print(f"Audio processing failed: {e}")
        raise