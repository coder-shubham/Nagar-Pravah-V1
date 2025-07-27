import asyncio
from dataclasses import dataclass
from google.cloud.firestore_v1 import GeoPoint
from typing import Dict, List
from enum import Enum
from pydantic import BaseModel
from pydantic import BaseModel
from typing import List
from enum import Enum
import logging
from google import genai
from google.genai import types
import googlemaps
from datetime import datetime
from google.cloud.firestore import GeoPoint
from datetime import datetime
from dataclasses import dataclass, fields, is_dataclass
from zoneinfo import ZoneInfo
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.oauth2 import service_account
from typing import Optional, List, Any
from dotenv import load_dotenv
from dataclasses import dataclass, asdict
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel
import logging
from retriever import retrieve_chunks_from_all_kbs
from semantic_deduplication import check_text_with_gemini_and_update
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


"""
{
    "title":"",
    "content": "",
    "status":"", //active, future, past
    "severity": "",
    "priorityScore":int,
    "locationString": "",
    "locationGeo":"", //Firestore Geopoint
    "engagementCount":int,
    "suggestion":"",
    “sentiment”:””,
    "category": "",
    "translations":{
        "kn":{
            "content":"",
            "suggestion":""
        },
        "hi":{
            "content":"",
            "suggestion":""
        }
    }
}
"""

credentials = service_account.Credentials.from_service_account_file(
    'serviceKey.json'
)

firestore_client = firestore.Client(project="nagar-pravah-fb", credentials=credentials)

gmaps = googlemaps.Client(key='')

mongo_client = MongoClient("mongodb+srv://user:id@cluster0.awbhsa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
mongo_db = mongo_client["app_db"]
collection_name = "synthesize-events"
gemini_client = genai.Client(api_key="")

def create_vector_index(collection):
    """Create a vector search index on the collection if it doesn't exist."""
    try:
        existing_indexes = collection.list_search_indexes()
        for index in existing_indexes:
            if index.get('name') == 'faq_vector':
                return
        index_name = "faq_vector"
        search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "numDimensions": 3072,
                        "path": "embeddings",
                        "similarity": "cosine"
                    }
                ]
            },
            name=index_name,
            type="vectorSearch"
        )
        collection.create_search_index(model=search_index_model)
        logger.info(f"Vector search index '{index_name}' created successfully")
    except Exception as e:
        logger.error(f"Error creating search index: {e}")
        raise e


def create_fts_search_index(collection):
    """Create a full-text search index on the collection if it doesn't exist."""
    try:
        index_name = "search_index"
        existing_indexes = collection.list_search_indexes()
        for index in existing_indexes:
            if index.get('name') == index_name:
                return
        search_index_model = SearchIndexModel(
            definition={
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "text": [
                            {"type": "string"}
                        ]
                    }
                },
            },
            name=index_name,
        )
        collection.create_search_index(model=search_index_model)
        logger.info(f"FTS search index created successfully!")
    except Exception as e:
        logger.error(f"Error creating fts search index: {e}")
        raise e

if collection_name in mongo_db.list_collection_names():
    logger.info(f"Collection {collection_name} already exists. Skipping creation.")
else:
    collection = mongo_db.create_collection(collection_name)
    logger.info(f"Collection {collection_name} created successfully")
    try:
        create_vector_index(collection=collection)
        create_fts_search_index(collection=collection)
    except Exception as e:
        logger.error(f"Error occurred while creating vector index for collection {collection_name}: {e}")
        mongo_db[collection_name].drop()
        raise e

mongo_collection = mongo_db[collection_name]



class EventSeverity(Enum):
    Low = "low"
    Medium = "medium"
    High = "high"

class EventStatus(Enum):
    Active = "active"
    Future = "future"
    Past = "past"

class AnalyzeCategory(Enum):
    Traffic = "traffic"
    Weather = "weather"
    CivicIssues = "civic_issues"
    Event = "event"


class AnalyzeSeverity(Enum):
    Low = "low"
    Medium = "medium"
    High = "high"
    


@dataclass
class AnalysisData:
    uniqueId: str
    category: AnalyzeCategory
    locationString: str
    locationGeo: GeoPoint
    text: str
    severity: AnalyzeSeverity
    priorityScore: float
    engagementCount: int
    sourceScoutIds: List[str]
    createdAt: Any
    updatedAt: Any
    embeddings: List[float] = None

@dataclass
class BatchAnalysisData:
    data: List[AnalysisData]



@dataclass
class AnalysisData:
    uniqueId: str
    category: AnalyzeCategory
    locationString: str
    locationGeo: GeoPoint
    text: str
    severity: AnalyzeSeverity
    priorityScore: float
    engagementCount: int
    sourceScoutIds: List[str]
    createdAt: Any
    updatedAt: Any
    embeddings: List[float] = None


class Category(Enum):
    Traffic = "traffic"
    Weather = "weather"
    CivicIssues = "civic_issues"
    Event = "event"

@dataclass
class SynthesizeEvent:
    uniqueId: str
    title: str
    text: str
    status: EventStatus
    severity: EventSeverity
    locationString: str
    locationGeo: GeoPoint
    suggestion: str
    sentiment: str
    category: Category
    translations: Dict[str, Dict[str, str]]
    createdAt: Any
    updatedAt: Any
    sourceScoutIds: List[str] = None
    embeddings: List[float] = None
    priorityScore: int = 0
    engagementCount: int = 0



class EventSentiment(str, Enum):
    Positive = "positive"
    Negative = "negative"
    Neutral = "neutral"


class MongoSynthesizeEvent(BaseModel):
    uniqueId: str
    title: str
    text: str
    status: str
    severity: EventSeverity
    locationString: str
    suggestion: str
    sentiment: str
    category: str
    translations: Dict[str, Dict[str, str]]
    createdAt: Any

class EventData(BaseModel):
    title: str
    text: str
    status: str
    severity: EventSeverity
    locationString: str
    suggestion: str
    sentiment: EventSentiment
    category: Category
    translations: Dict[str, Dict[str, str]]
    createdAt: str
    priorityScore: int
    engagementCount: int

class AllEventData(BaseModel):
    data: List[EventData]

def dataclass_enum_to_value(data) -> Dict:
    """
    Convert dataclass to a dictionary, handling GeoPoint conversion for MongoDB compatibility.
    """
    data_dict = asdict(data)
    if isinstance(data_dict.get('locationGeo'), GeoPoint):
        data_dict['locationGeo'] = {
            'latitude': data_dict['locationGeo'].latitude,
            'longitude': data_dict['locationGeo'].longitude
        }
    if isinstance(data_dict.get('status'), EventStatus):
        data_dict['status'] = data_dict['status'].value
    if isinstance(data_dict.get('category'), AnalyzeCategory):
        data_dict['category'] = data_dict['category'].value
    if isinstance(data_dict.get('severity'), AnalyzeSeverity):
        data_dict['severity'] = data_dict['severity'].value
    if isinstance(data_dict.get('category'), Category):
        data_dict['category'] = data_dict['category'].value
    if isinstance(data_dict.get('severity'), EventSeverity):
        data_dict['severity'] = data_dict['severity'].value
    if isinstance(data_dict.get('sentiment'), EventSentiment):
        data_dict['sentiment'] = data_dict['sentiment'].value
    return data_dict

def generate_events(batch_data: BatchAnalysisData):
    """
    Convert BatchAnalysisData to a list of SynthesizeEvent.
    """
    data_list = []
    for data in batch_data.data:
        data_dict = dataclass_enum_to_value(data)
        del data_dict['embeddings']  # Remove embeddings for MongoDB compatibility
        data_list.append(data_dict)
    prompt= f"""
You are an event synthesis agent, convert the following batch of analysis data into a list of unique events with actionable insights for the users.
Each event should be a JSON object with the following structure:
title: the title of the event 
text: the content of the event
status: the status of the event (active, future, past)  (only one of three options, always in small case and exact values)
severity: the severity of the event (low, medium, high)  (only one of three options, always in small case and exact values)
locationString: the location of the event in the format "Whitefield, Bangalore"
suggestion: a suggestion for the event (has to be meaningful, insightful and actionable that is it can be followed by the user)
sentiment: the sentiment of the event (positive, negative, neutral) (only one of three options, always in small case and exact values)
category: the category of the event (traffic, weather, civic_issues, event)
translations: translations of the event and suggestions in different languages (hindi and kannada)
priorityScore: the priority score of the event (1-10)
engagementCount: the engagement count of the event

Analysed Data:
{data_list}

Provide a list of json like this [STRICT] in your response nothing else
```json
[
    {{
      "title": "Network Outage",
      "text": "There is a major outage affecting the data center.",
      "status": "active",
      "severity": "high",
      "locationString": "San Francisco, CA",
      "suggestion": "Switch to backup network.",
      "sentiment": "negative",
      "category": "infrastructure",
      "translations": {{
            "ka": {{
            "title": "ನೆಟ್ವರ್ಕ್ ವ್ಯತ್ಯಯ",
            "text": "ಡೇಟಾ ಕೇಂದ್ರವನ್ನು ಪ್ರಭಾವಿತ ಮಾಡುವ ದೊಡ್ಡ ವ್ಯತ್ಯಯವಿದೆ.",
            "suggestion": "ಬ್ಯಾಕ್‌ಅಪ್ ನೆಟ್ವರ್ಕ್‌ಗೆ ಸ್ವಿಚ್ ಮಾಡಿ."
            }},
            "hi": {{
            "title": "नेटवर्क आउटेज",
            "text": "डेटा केंद्र को प्रभावित करने वाला एक बड़ा आउटेज है।",
            "suggestion": "बैकअप नेटवर्क पर स्विच करें।"
            }}
      }},
      "priorityScore": 95,
      "engagementCount": 123
    }}
  ]
```
Response:
"""
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
    )
    response_text = response.text
    response_text =response_text.strip("```json")
    data: AllEventData = eval(response_text)

    return data

def synthesize_events_from_batch(batch_data: BatchAnalysisData) -> List[SynthesizeEvent]:
    """
    Synthesize events from a batch of analysis data.
    """
    synthesized_events = generate_events(batch_data)
    for event in synthesized_events:
        # Convert GeminiSynthesizeEvent to SynthesizeEvent
        event_dict = event
        gemini_event_data = event_dict
        geocode_result = gmaps.geocode(gemini_event_data['locationString'], language='en', region='IN')
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
            geopoint = GeoPoint(lat, lng)
        else:
            raise Exception("Address not found")
        # Get current time in Asia/Kolkata
        now_kolkata = datetime.now(ZoneInfo("Asia/Kolkata"))

        # ISO 8601 format with timezone
        iso_format = now_kolkata.isoformat()

        related_events = check_for_related_events(gemini_event_data['text'])
        if related_events[0] == "same":
            continue
        elif related_events[0] == "additional":
            updated_event = update_content(gemini_event_data['text'], related_events[1]['text'])
            gemini_event_data['text'] = updated_event
            gemini_event_data['embeddings'] = gemini_embed_text(updated_event)[0]
            updated_synthesis_data = SynthesizeEvent(
                uniqueId=related_events[1]['uniqueId'],
                title=gemini_event_data['title'],
                text=gemini_event_data['text'],
                status=gemini_event_data['status'],
                severity=gemini_event_data['severity'],
                locationString=gemini_event_data['locationString'],
                priorityScore=gemini_event_data['priorityScore'],
                engagementCount=gemini_event_data['engagementCount'],
                locationGeo=geopoint,
                suggestion=gemini_event_data['suggestion'],
                sentiment=gemini_event_data['sentiment'],
                category=gemini_event_data['category'],
                translations=gemini_event_data['translations'],
                createdAt=firestore.SERVER_TIMESTAMP,
                updatedAt=firestore.SERVER_TIMESTAMP,
                embeddings=gemini_event_data.get('embeddings', [])
            )
            # Convert to dictionary for MongoDB compatibility
            updated_synthesis_data = dataclass_enum_to_value(updated_synthesis_data)
            del updated_synthesis_data['locationGeo']  # Remove GeoPoint for MongoDB compatibility
            del updated_synthesis_data['createdAt']  # Remove createdAt for MongoDB compatibility
            del updated_synthesis_data['updatedAt']  # Remove updatedAt for MongoDB compatibility
            mongo_collection.update_one(
                {"uniqueId": related_events[1]['uniqueId']},
                {"$set": updated_synthesis_data}
            )
            docs = firestore_client.collection('synthesize-events').where('uniqueId', '==', related_events[1]['uniqueId']).stream()

            # Loop through and update each document
            for doc in docs:
                firestore_client.collection('synthesize-events').document(doc.id).update(updated_synthesis_data)
        else:
            gemini_event_data['embeddings'] = gemini_embed_text(gemini_event_data['text'])[0]
        synthesize_event = SynthesizeEvent(
            uniqueId=str(uuid.uuid4()),
            title=gemini_event_data['title'],
            text=gemini_event_data['text'],
            status=gemini_event_data['status'],
            severity=gemini_event_data['severity'],
            priorityScore=gemini_event_data['priorityScore'],
            locationString=gemini_event_data['locationString'],
            locationGeo=geopoint,
            engagementCount=gemini_event_data['engagementCount'],
            suggestion=gemini_event_data['suggestion'],
            sentiment=gemini_event_data['sentiment'],
            category=gemini_event_data['category'],
            translations=gemini_event_data['translations'],
            createdAt=firestore.SERVER_TIMESTAMP,
            updatedAt=firestore.SERVER_TIMESTAMP,
            embeddings=gemini_event_data.get('embeddings', [])
        )
        # Convert to dictionary for MongoDB compatibility
        synthesize_event_dict = dataclass_enum_to_value(synthesize_event)
        firestore_client.collection('synthesize-events').add(synthesize_event_dict)
        del synthesize_event_dict['locationGeo']  # Remove GeoPoint for MongoDB compatibility
        del synthesize_event_dict['createdAt']  # Remove createdAt for MongoDB compatibility
        del synthesize_event_dict['updatedAt']  # Remove updatedAt for MongoDB compatibility
        mongo_collection.insert_one(synthesize_event_dict)


def gemini_embed_text(texts):
    """
    Generate embeddings for the input text using OpenAI's API.
    :param texts: List of strings to embed.
    :return: List of embeddings.
    """
    if not isinstance(texts, list):
        texts = [texts]

    embeddings = []
    for text in texts:
        response = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=3072, task_type='RETRIEVAL_QUERY')
        )
        embeddings.append(response.embeddings[0].values)
    return embeddings  # Already in list format suitable for JSON serialization




def check_for_related_events(text:str):
    related_or_similar_events = asyncio.run(retrieve_chunks_from_all_kbs(mongo_uris={"mongo_1":{
                        "uri": "mongodb+srv://user:id@cluster0.awbhsa.mongodb.net/",
                        "kb_ids":["event_store"]
                    }}, query=text, top_k=5))
    for event in related_or_similar_events:
        if "same" in check_text_with_gemini_and_update(text, event['text']).lower():
            return "same", None
        elif "additional" in check_text_with_gemini_and_update(text, event['text']).lower():
            return "additional", event
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


if __name__ == "__main__":

    collection_ref = firestore_client.collection('analyzed-events')
    # Get all documents
    docs = collection_ref.stream()

    batch_data = []
    for doc in docs:
        print(f"Processing document: {doc.id}")
        analysis_data = AnalysisData(
            uniqueId=doc.id,
            category=AnalyzeCategory(doc.to_dict().get('category')),
            locationString=doc.to_dict().get('locationString'),
            locationGeo=GeoPoint(doc.to_dict().get('locationGeo').latitude, doc.to_dict().get('locationGeo').longitude),
            text=doc.to_dict().get('text'),
            severity=AnalyzeSeverity(doc.to_dict().get('severity')),
            priorityScore=doc.to_dict().get('priorityScore', 0),
            engagementCount=doc.to_dict().get('engagementCount', 0),
            sourceScoutIds=doc.to_dict().get('sourceScoutIds', []),
            createdAt=doc.to_dict().get('createdAt', firestore.SERVER_TIMESTAMP),
            updatedAt=doc.to_dict().get('updatedAt', firestore.SERVER_TIMESTAMP),
        )
        batch_data.append(analysis_data)
    batch_data = BatchAnalysisData(data=batch_data)
    synthesize_events_from_batch(batch_data)
    print("Synthesis completed successfully.")
