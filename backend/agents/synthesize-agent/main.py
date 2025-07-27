import functions_framework
import base64
import json
import logging
import time
from flask import Response
from uuid import uuid4
from synthesize_agent import synthesize_events_from_batch  # Import your main function
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.cloud_event
def handle_cloud_event(cloud_event):
    start_time = time.time()
    
    uuid_for_instance = uuid4()
    logger.info(">>> Handler was invoked (ENTRYPOINT) <<<")
    envelope = cloud_event.data
    if not envelope:
        return Response("Bad Request: expected CloudEvent", status=400)

    try:
        message    = envelope["message"]
        b64_data   = message.get("data", "")
        attributes = message.get("attributes", {})
        message_id = message.get("messageId", "unknown")
    except (KeyError, TypeError):
        return Response("Bad Request: malformed CloudEvent for Pub/Sub", status=400)

    # Decode base64 payload
    if b64_data:
        try:
            payload_text = base64.b64decode(b64_data).decode("utf-8")
        except Exception as e:
            logger.error(f"{uuid_for_instance} : Error base64-decoding Pub/Sub data: {e}")
            return Response("Bad Request: invalid base64 payload", status=400)
    else:
        payload_text = "{}"

    try:
        msg = json.loads(payload_text)
        job_id = msg.get("job_id")
        correlation_id = msg.get("correlation_id")
        data = msg.get("batch", [])


    except json.JSONDecodeError as e:
        logger.error(f"{uuid_for_instance} : : Error parsing JSON payload: {e}")
        return Response("Bad Request: invalid JSON payload", status=400)

    logger.info(f"Received Pub/Sub messageId={message_id}, attributes={attributes}, payload={msg}")
    synthesize_events_from_batch(batch_data=data)
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Processing completed in {elapsed_time:.2f} seconds for messageId={message_id}")
    callback_payload = {
        "job_id": job_id,
        "correlation_id": correlation_id,
        "source": "stage1"
    }
    OBSERVER_CALLBACK_URL = "http://34.126.223.182:8000/callback"
    try:
        response = requests.post(OBSERVER_CALLBACK_URL, json=callback_payload)
        response.raise_for_status()
        print(f"✅ Stage1 callback sent: {correlation_id}")
    except Exception as e:
        print(f"❌ Failed to send stage1 callback: {e}")



