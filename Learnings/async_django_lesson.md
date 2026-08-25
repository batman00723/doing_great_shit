# Today's Fixes: Async Background Tasks in Django & LangGraph

---

## 1. The Core Problem: Blocking the User
Your `/analyse/report` endpoint was forcing the user to wait for the entire AI pipeline to finish before they got a response (30+ seconds). 

To fix this, we moved the pipeline into a **background task**. The endpoint now creates a task, immediately returns `200 OK {"status": "processing"}`, and lets the AI run in the background.

```python
# meeting_controller.py
from asyncio import create_task

BACKGROUND_TASKS = set()

def schedule_background_task(coro):
    task = create_task(coro)
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)

@http_post("/report")
async def analyse_report(self, request, payload):
    # Fire and forget!
    schedule_background_task(process_transcript(...))
    return {"status": "processing"}
```
*(We use a global `set()` to keep strong references to the tasks so Python's Garbage Collector doesn't delete them mid-flight).*

---

## 2. Bug #1: The LLM Fallback Issue (`llm.py`)
We had OpenRouter as the primary model and Gemini as a fallback. 
Previously, the code tried to apply `.with_structured_output(schema)` to the combined fallback chain. LangChain doesn't support this, so it was silently failing.

**The Fix:** Apply the structured schema to each model *individually*, and then link them together.

```python
# CORRECT WAY
primary_structured = self.primary_model.with_structured_output(schema)
fallback_structured = self.fallback_model.with_structured_output(schema)

# Now combine the structured versions:
robust_structured = primary_structured.with_fallbacks([fallback_structured])
return await robust_structured.ainvoke(messages)
```

---

## 3. Bug #2: The Server (WSGI vs ASGI)
You were running the server using `python manage.py runserver`. This starts Django's default WSGI server, which is **synchronous**. If you launch an `asyncio.create_task` inside a WSGI server, it often kills the background tasks as soon as the HTTP response goes out.

**The Fix:** We switched to **Uvicorn**, which is an ASGI (Asynchronous Server Gateway Interface) server. It natively understands and preserves background tasks.
```bash
uvicorn backend.asgi:application --reload
```

---

## 4. Bug #3: Django ORM in Background Tasks (The Final Boss)
This was the hardest bug, and it caused the `SynchronousOnlyOperation` and `CurrentThreadExecutor already quit` errors.

### How Django Thinks
Django's ORM is designed for synchronous, thread-per-request servers. When a web request comes in, Django sets up a special thread (`CurrentThreadExecutor`) for it. 
When you run code inside `asyncio.create_task()`, you are running outside of the web request's thread.

If you try to touch the database (like calling `Meeting.objects.get` or doing an `async for` loop on a QuerySet) inside a background task, Django panics because it can't find its safe thread.

### Step 1: Wrap DB calls in `sync_to_async`
We had to take every database operation inside `nodes.py` and `transcript_processor.py` and wrap it in `sync_to_async`. This takes the synchronous DB code and safely runs it in a thread pool.

### Step 2: The `thread_sensitive=False` Trap
At first, we used `sync_to_async(thread_sensitive=True)`. 
`thread_sensitive=True` tells Django to route the database work back to the **main HTTP request thread**.

**But wait!** Our endpoint returns `200 OK` instantly. That means the HTTP request thread shuts down and gets destroyed while our background task is still running the LLM!

When the AI finished (10 seconds later) and tried to save to the database, Django tried to route the save to the HTTP request thread — but the thread was dead. Boom: `CurrentThreadExecutor already quit or is broken`.

### The Final Fix
We changed all database calls in the background tasks to use `thread_sensitive=False`. This tells Django: *"Don't use the fragile HTTP request thread. Just use a standard, long-living background thread from the global pool."*

```python
from asgiref.sync import sync_to_async

# How to safely fetch from DB in a background task:
@sync_to_async(thread_sensitive=False)
def _fetch_previous():
    return list(MeetingAnalysis.objects.filter(...))

previous_meetings = await _fetch_previous()

# How to safely save to DB in a background task:
await sync_to_async(meeting.save, thread_sensitive=False)(update_fields=['status'])
```

---

## Summary Cheat Sheet
1. **Background tasks in Django?** Use `asyncio.create_task` + a global `set()`.
2. **LLM Fallbacks with Schemas?** Apply the schema to each model *before* calling `.with_fallbacks()`.
3. **Running async Django?** Use `uvicorn backend.asgi:application`, never `runserver`.
4. **Database inside a background task?** Always wrap it in `sync_to_async(thread_sensitive=False)`.
