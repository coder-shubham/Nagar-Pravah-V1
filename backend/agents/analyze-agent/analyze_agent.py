from pydantic import BaseModel
from typing import List
from enum import Enum
from semantic_deduplication import text_deduplication, update_content
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


load_dotenv('.env',  override=True)


"""
const firebaseConfig = {
  apiKey: "AIzaSyBfVf_w9up56L8o1zJAhPS-UHX57lumekA",
  authDomain: "fir-pulse-app.firebaseapp.com",
  projectId: "fir-pulse-app",
  storageBucket: "fir-pulse-app.firebasestorage.app",
  messagingSenderId: "660958366144",
  appId: "1:660958366144:web:b5c3a21db6bd6cfad76025"
};
"""



credentials = service_account.Credentials.from_service_account_file(
    'nagar-pravah-fb-b49a37073a4a.json'
)

firestore_client = firestore.Client(project="nagar-pravah-fb", credentials=credentials)

gmaps = googlemaps.Client(key='AIzaSyDJAVjVjtZmy9-Erp4BQnAVQzXeDrJdLy8')


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo_client = MongoClient("mongodb+srv://kartikayraheja:bQyCgeg9UC5jSzmZ@cluster0.awbhsa.mongodb.net/")
mongo_db = mongo_client["app_db"]
collection_name = "analyzed-events"

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

class Source(Enum):
    Twitter = "twitter"
    Facebook = "facebook"
    Event = "event"
    Traffic = "traffic"
    Weather = "weather"
    News = "news"


@dataclass
class ScoutData:
    content: str
    location: str
    source: Source
    createdAt: Any
    engagementCount: int
    sourceId: str


@dataclass
class BatchScoutData:
    data: List[ScoutData]


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
class AnalyzeData:
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
class GeminiAnalyzeData:
    category: AnalyzeCategory
    locationString: str
    severity: AnalyzeSeverity
    text: str

# gemini_creds = service_account.Credentials.from_service_account_file("linear-trees-831-9b636f056c58.json")
gemini_client = genai.Client(api_key="AIzaSyDOgIGjr0Xpij4d49mr78wQZ8Xe3smCWP8")

def generate_analyze_data(scout_data: ScoutData) -> AnalyzeData:
    prompt = f"""You are an analysis agent that takes in given data and transforms it into more meaningful and actionable insight.
Given Data: {asdict(scout_data)}
Generate the following data in the format:
category: str [One of {AnalyzeCategory.Traffic.value}, {AnalyzeCategory.Weather.value}, {AnalyzeCategory.CivicIssues.value}, {AnalyzeCategory.Event.value}]
locationString: str [Proper geographic location, which can be used for geocoding]
severity: str [One of {AnalyzeSeverity.Low.value}, {AnalyzeSeverity.Medium.value}, {AnalyzeSeverity.High.value}]
text: str [The text of the data, should be a concise summary of the data and include every detail that is important]
Response:
"""
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_schema=GeminiAnalyzeData,
            response_mime_type="application/json"
    )
    )
    gemini_analyze_data: GeminiAnalyzeData = response.parsed

    return gemini_analyze_data

def calculate_priority_score(engagement_count: int, severity: AnalyzeSeverity) -> float:
    severity_weights = {
        AnalyzeSeverity.Low.value: 1.0,
        AnalyzeSeverity.Medium.value: 2.0,
        AnalyzeSeverity.High.value: 3.0
    }
    return engagement_count * severity_weights[severity]

def dataclass_enum_to_value(obj: Any) -> dict:
    if not is_dataclass(obj):
        raise ValueError("Input must be a dataclass instance")

    result = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, Enum):
            result[f.name] = value.value
        else:
            result[f.name] = value  # leave as-is
    return result

def analyze_scout_data(batch_data: BatchScoutData):
    collection = firestore_client.collection("analyzed-events")
    for item in batch_data.data:
        # Perform analysis on each ScoutData item
        uris= {"mongo_1":{
                        "uri": "mongodb+srv://kartikayraheja:bQyCgeg9UC5jSzmZ@cluster0.awbhsa.mongodb.net/",
                        "kb_ids":["analyzed-events"]
                    }}
        response = text_deduplication(item.content, uris)
        if response[0] == "same":
            continue
        elif response[0] == "different":
            # Handle different content
            print(f"Different content found for {item.sourceId}: {item.content}")
            gemini_analyze_data = generate_analyze_data(item)
            geocode_result = gmaps.geocode(gemini_analyze_data.locationString, language='en', region='IN')
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat, lng = location['lat'], location['lng']
                geopoint = GeoPoint(lat, lng)
            else:
                raise Exception("Address not found")
            # Get current time in Asia/Kolkata
            embeddings = gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=[gemini_analyze_data.text],
                config=types.EmbedContentConfig(output_dimensionality=3072, task_type='RETRIEVAL_DOCUMENT')
            )
            embedding_values = embeddings.embeddings[0].values
            print(type(embedding_values))
            analyze_data = AnalyzeData(
                uniqueId=item.sourceId,
                category=gemini_analyze_data.category,
                locationString=gemini_analyze_data.locationString,
                locationGeo=geopoint,
                text=gemini_analyze_data.text,
                severity=gemini_analyze_data.severity,
                priorityScore=calculate_priority_score(item.engagementCount, gemini_analyze_data.severity.value),
                engagementCount=item.engagementCount,
                sourceScoutIds=[item.sourceId],
                createdAt=firestore.SERVER_TIMESTAMP,
                updatedAt=firestore.SERVER_TIMESTAMP,  # Assuming createdAt is the same as updatedAt initially
                embeddings=embedding_values

            )
            # Here you would typically save analyze_data to Firestore or another database
            # logger.info(f"Analyzed data: {dataclass_enum_to_value(analyze_data)}")
            analyze_data = dataclass_enum_to_value(analyze_data)
            collection.add(analyze_data)
            del analyze_data['locationGeo']  # Remove GeoPoint for MongoDB compatibility
            del analyze_data['createdAt']  # Remove createdAt for MongoDB compatibility
            del analyze_data['updatedAt']  # Remove updatedAt for MongoDB compatibility
            mongo_collection.insert_one(analyze_data)

        elif response[0] == "additional":
            # Handle additional content
            existing_doc = response[1]
            updated_content = update_content(existing_doc['text'], item.content)
            updated_engagement_count = existing_doc['engagementCount'] + item.engagementCount
            update_source_ids = existing_doc['sourceScoutIds'] + [item.sourceId]
            updated_priority_score = calculate_priority_score(updated_engagement_count, existing_doc['severity'])
            updated_embedding = gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=[updated_content],
                config=types.EmbedContentConfig(output_dimensionality=3072, task_type='RETRIEVAL_DOCUMENT')
            )
            updated_embedding_values = updated_embedding.embeddings[0].values
            geocode_result = gmaps.geocode(existing_doc['locationString'], language='en', region='IN')
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat, lng = location['lat'], location['lng']
                geopoint = GeoPoint(lat, lng)
            else:
                raise Exception("Address not found")
            print(type(updated_embedding_values))
            updated_analyze_data = AnalyzeData(
                uniqueId=existing_doc['uniqueId'],
                category=existing_doc['category'],
                locationString=existing_doc['locationString'],
                locationGeo=geopoint,
                text=updated_content,
                severity=existing_doc['severity'],
                priorityScore=updated_priority_score,
                engagementCount=updated_engagement_count,
                sourceScoutIds=update_source_ids,
                createdAt=firestore.SERVER_TIMESTAMP,  # Assuming createdAt is the same as updatedAt initially
                updatedAt=firestore.SERVER_TIMESTAMP,  # Update timestamp
                embeddings=updated_embedding_values
            )
            # Here you would typically update the existing document in Firestore
            updated_analyze_data = dataclass_enum_to_value(updated_analyze_data)
            del updated_analyze_data['locationGeo']  # Remove GeoPoint for MongoDB compatibility
            del updated_analyze_data['createdAt']  # Remove createdAt for MongoDB compatibility
            del updated_analyze_data['updatedAt']  # Remove updatedAt for MongoDB compatibility
            mongo_collection.update_one(
                {"uniqueId": existing_doc['uniqueId']},
                {"$set": updated_analyze_data}
            )
            docs = firestore_client.collection('analyzed-events').where('uniqueId', '==', existing_doc['uniqueId']).stream()

            # Loop through and update each document
            for doc in docs:
                firestore_client.collection('analyzed-events').document(doc.id).update(updated_analyze_data)


def collection_exists(collection_name):
    """
    Returns True if the Firestore collection has any documents, False otherwise.
    """
    docs = firestore_client.collection(collection_name).limit(1).stream()
    return any(True for _ in docs)

if __name__ == "__main__":
    # Example usage
    scout_data_example1 = ScoutData(
        content="Heavy traffic from Yelahanka to Hebbal",
        location="Yelahanka, Bangalore, Karnataka",
        source=Source.Traffic,
        createdAt=firestore.SERVER_TIMESTAMP,
        engagementCount=10,
        sourceId="12345"
    )
    
    scout_data_example2 = ScoutData(
        content="Rainy weather in Yelahanka",
        location="Yelahanka, Bangalore, Karnataka",
        source=Source.Weather,
        createdAt=firestore.SERVER_TIMESTAMP,
        engagementCount=5,
        sourceId="67890"
    )

    scout_data_example3 = ScoutData(
        content="Community event in Yelahanka",
        location="Yelahanka, Bangalore, Karnataka",
        source=Source.Event,
        createdAt=firestore.SERVER_TIMESTAMP,
        engagementCount=15,
        sourceId="11223"
    )

    scout_data_example4 = ScoutData(
        content="Traffic jam reported in Yelahanka",
        location="Yelahanka, Bangalore, Karnataka",
        source=Source.Traffic,
        createdAt=firestore.SERVER_TIMESTAMP,
        engagementCount=20,
        sourceId="44556"
    )
    batch_data = BatchScoutData(data=[
        scout_data_example1,
        scout_data_example2,
        scout_data_example3,
        scout_data_example4
    ])
    analyze_scout_data(batch_data)
    logger.info("Analysis completed.")
    # This will analyze the scout data and print the results
    # You can replace the example data with actual ScoutData instances as needed.
    # Make sure to handle Firestore connections and other configurations as needed.
    # Note: The Firestore client and Google Maps client should be properly configured with your credentials
    # and project settings.