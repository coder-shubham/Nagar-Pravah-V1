from fastapi import FastAPI
from google.cloud import firestore, pubsub_v1
import json, uuid, asyncio


credentials = service_account.Credentials.from_service_account_file(
    'nagar-pravah-fb-b49a37073a4a.json'
)

firestore_client = firestore.Client(project="nagar-pravah-fb", credentials=credentials)

app = FastAPI()
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

TOPIC1 = publisher.topic_path("nagar-pravah-v1", "analyzed-topic")
TOPIC2 = publisher.topic_path("nagar-pravah-v1", "sythesized-topic")

# In-memory state tracker
job_state = {}

# ---------- CURSOR UTILS ----------
async def get_last_cursor(stage: str):
    doc_ref = db.collection("job_state_tracking").document(f"{stage}_cursor")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("last_createdAt")
    return None

async def update_last_cursor(stage: str, last_createdAt):
    doc_ref = db.collection("job_state_tracking").document(f"{stage}_cursor")
    doc_ref.set({"last_createdAt": last_createdAt})

# ---------- CALLBACK HANDLER ----------
@app.post("/callback")
async def callback(data: dict):
    job_id = data["job_id"]
    correlation_id = data["correlation_id"]
    source = data["source"]

    state = job_state.get(job_id)
    if not state:
        return {"error": "unknown job"}

    if source == "stage1":
        state["stage1_received"] += 1
        print(f"✅ Stage 1 ack {correlation_id}: {state['stage1_received']}/{state['stage1_expected']}")

        if state["stage1_received"] == state["stage1_expected"] and not state["stage2_sent"]:
            await send_stage2(job_id)
            state["stage2_sent"] = True

    elif source == "stage2":
        print(f"✅ Stage 2 ack received for job {job_id}")
        state["stage2_ack"] = True

    return {"status": "ok"}

# ---------- STAGE 1 ----------
async def send_stage1(job_id):
    coll_ref = db.collection("scouted_data")
    batch_size = 20
    total_sent = 0
    last_cursor = await get_last_cursor("stage1")
    last_doc = None

    while total_sent < 100:
        query = coll_ref.order_by("createdAt").limit(batch_size)
        if last_cursor:
            query = query.start_after({"createdAt": last_cursor})
        elif last_doc:
            query = query.start_after(last_doc)

        docs = list(query.stream())
        if not docs:
            break

        for doc in docs:
            cid = f"{job_id}-{doc.id}"
            publisher.publish(TOPIC1, json.dumps({
                "job_id": job_id,
                "correlation_id": cid,
                "payload": doc.to_dict()
            }).encode())
            print(f"📤 Stage 1 sent: {cid}")

        last_doc = docs[-1]
        total_sent += len(docs)

    if last_doc:
        await update_last_cursor("stage1", last_doc.to_dict().get("createdAt"))

    job_state[job_id] = {
        "stage1_expected": total_sent,
        "stage1_received": 0,
        "stage2_sent": False,
        "stage2_ack": False
    }

# ---------- STAGE 2 ----------
async def send_stage2(job_id):
    coll_ref = db.collection("analyzed-event")
    last_cursor = await get_last_cursor("stage2")

    query = coll_ref.order_by("createdAt").limit(5)
    if last_cursor:
        query = query.start_after({"createdAt": last_cursor})

    docs = list(query.stream())
    if not docs:
        print(f"⚠️ No new docs for Stage 2")
        return

    publisher.publish(TOPIC2, json.dumps({
        "job_id": job_id,
        "correlation_id": job_id,
        "batch": [doc.to_dict() for doc in docs]
    }).encode())

    print(f"📤 Stage 2 triggered with {len(docs)} docs")

    await update_last_cursor("stage2", docs[-1].to_dict().get("createdAt"))

# ---------- ORCHESTRATION LOOP ----------
async def orchestrator_loop():
    while True:
        job_id = f"job-{uuid.uuid4()}"
        print(f"\n🚀 Starting new job: {job_id}")
        await send_stage1(job_id)

        # Wait until stage 2 is acknowledged
        while True:
            state = job_state.get(job_id)
            if state and state.get("stage2_ack"):
                print(f"✅ Job {job_id} fully processed.")
                break
            await asyncio.sleep(2)

        print(f"⏳ Sleeping 2 minutes before next job...")
        await asyncio.sleep(120)

# ---------- FASTAPI STARTUP ----------
@app.on_event("startup")
async def start():
    asyncio.create_task(orchestrator_loop())

@app.get("/")
async def root():
    return {"message": "Observer service is running. Use /callback to send updates."}
