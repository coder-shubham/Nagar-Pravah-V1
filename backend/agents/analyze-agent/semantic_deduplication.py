import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from google import genai
from google.genai import types
from pydantic import BaseModel
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.oauth2 import service_account
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel
from retriever import retrieve_chunks_from_all_kbs
import asyncio

from dotenv import load_dotenv
import logging
# load_dotenv('.env',  override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

credentials = service_account.Credentials.from_service_account_file(
    'nagar-pravah-fb-b49a37073a4a.json'
)

firestore_client = firestore.Client(project="nagar-pravah-fb", credentials=credentials)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# gemini_creds = service_account.Credentials.from_service_account_file("linear-trees-831-9b636f056c58.json")
gemini_client = genai.Client(api_key="AIzaSyDOgIGjr0Xpij4d49mr78wQZ8Xe3smCWP8")


def check_text_with_gemini_and_update(text1, text2):
    prompt=f"""
You are a document analysis agent, check whether the two texts (text1 and text2) are talking about the same event or topic.
If they are talking about the same topic or event, then check if text2 is providing any additional information.
Provide answer as one of the three outputs only: "Same", "different", "Additional"
"same": Same is for the case where both texts are same and not providing any additional info.
"different": Different is for the case when both texts are different
"additional": When both are talking about the same thing but text2 is providing some additional information
Provide only one of the three in the response and nothing else.
Text1: {text1}
Text2: {text2}
Response:
"""
    response = gemini_client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[prompt]
    )
    return response.text

def text_deduplication(text, uri):
    docs = asyncio.run(retrieve_chunks_from_all_kbs(mongo_uris=uri, query=text, top_k=3))

    for doc in docs:
        if "same" in check_text_with_gemini_and_update(text, doc['text']).lower() :
            return "same", None
        elif "additional" in check_text_with_gemini_and_update(text, doc['text']).lower():
            return "additional", doc
        else:
            continue
    return "different", None

def update_content(text1, text2):
    prompt =f"""You are given two texts, both are talking about the same topic or event while text2 has some additional information which text1 is missing, provide a combined text content.
Do not provide any reasoning just provide the combined text in the response.
text1: {text1}
text2:{text2}
Response:
"""
    response = gemini_client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[prompt]
    )
    return response.text
