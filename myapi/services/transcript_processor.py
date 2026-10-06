from myapi.agent.graph import build_graph
import logging
from myapi.models import User, Organisation, Meeting, Customer
from asgiref.sync import sync_to_async


meeting_agent = build_graph()


logger = logging.getLogger(__name__) 



async def process_transcript(transcript: str, user, customer, meeting: Meeting):
    logger.info(f"Background task started for processing transcript. Meeting ID: {meeting.id}")

    organisation_id = user.organisation_id                                                                                                                                     
    salesperson_id = user.id 

    initial_state = {
        "meeting_id": meeting.id,
        "organisation_id": organisation_id,
        "salesperson_id": salesperson_id,
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
        final_state = await meeting_agent.ainvoke(initial_state, config= config)
        meeting.status = Meeting.Status.COMPLETED
        await sync_to_async(meeting.save, thread_sensitive=False)(update_fields=['status'])

        return final_state.get("status")

    except Exception as e:
        meeting.status = Meeting.Status.FAILED
        await sync_to_async(meeting.save, thread_sensitive=False)(update_fields=['status'])
        logger.error(f"Transcript processing failed: {e}", exc_info= True)
        raise

# so when a user logs in it takes whole user row oe we can say object so this is how request.user has the org id and al credntials

# earlier we were fetching the whole user id from the logged in user okay got it then it was actaully using a sql query to fetch from db but i didnt knew cus it was sync
#   but when i made that function async i got to know it already has id in request.user still it is fetching all object from db that was sync so we changed it to only fetch id and id
#   was in request.user object which does not require db call now and another was to add_id as we only had id cus its a syntax rule