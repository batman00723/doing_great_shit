from myapi.agent.llm import LLMService
from myapi.agent.graph import build_graph
from myapi.models import User, Organisation, Meeting, Customer

llm = LLMService()
meeting_agent = build_graph()


def process_transcript(transcript: str, user, customer):
    print("Transcription is processing")

    organisation = user.organisation
    salesperson = user

    from datetime import timedelta
    from django.utils import timezone

    meeting = Meeting.objects.create(
        organisation=organisation,
        customer=customer,
        salesperson=salesperson,
        meeting_date=timezone.now(),
        duration=timedelta(),
        title="Demo Meeting",
        meeting_type="Sales Call",
        status= Meeting.Status.PROCESSING,
    )

    initial_state = {
        "meeting_id": meeting.id,
        "organisation_id": organisation.id,
        "salesperson_id": salesperson.id,
        "customer_id": customer.id,
        "transcript": transcript,
        "status": "pending",
        "errors": []
    }

    config= {
        "configurable": {
            "thread_id": str(meeting.id)
        }
    }

    try:
        final_state = meeting_agent.invoke(initial_state, config= config)
        meeting.status = Meeting.Status.COMPLETED
        meeting.save()


        return final_state.get("status")

    except Exception as e:
        meeting.status = Meeting.Status.FAILED
        meeting.save()
        print(f"Transcript processing failed: {e}")
        raise

    