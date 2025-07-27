import os
import pprint
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from typing import Dict
from pymongo.errors import ServerSelectionTimeoutError
from fastapi import HTTPException
import json
from google import genai
from google.genai import types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from pydantic import BaseModel


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Question(BaseModel):
    text: str


gemini_client = genai.Client(api_key="")


async def validate_mongo_uris_and_kbids(mongo_uris):
    """
    Validates connection to each Mongo URI and checks if each KB exists
    """
    results = {}

    async def validate_one(label: str, entry):
        errors = []
        try:
            client = AsyncIOMotorClient(entry.uri)
            await client.server_info()  # force connection

            db = client.app_db

            for kb_id in entry.kb_ids:
                if kb_id not in await db.list_collection_names():
                    errors.append(f"KB '{kb_id}' not found in Mongo URI '{entry.uri}'")
                    continue

        except Exception as e:
            errors.append(f"Connection to URI '{entry.uri}' failed: {str(e)}")

        results[label] = errors

        tasks = [validate_one(label, entry) for label, entry in mongo_uris.items()]
        await asyncio.gather(*tasks)
        return results

async def get_unique_chunks(chunks):
    covered_parent_chunks = set()
    
    unique_chunks = list()
    
    for fc in chunks:
        if fc.get('chunk_parent_id'):
            if fc.get('chunk_parent_id') in covered_parent_chunks:
                pass
            else:
                unique_chunks.append(fc)
                covered_parent_chunks.add(fc.get('chunk_parent_id'))
        else:
            unique_chunks.append(fc)

    return unique_chunks
 
    
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

# embeddings_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device="cpu") 

async def retrieve_chunks_from_all_kbs(mongo_uris: dict, query: str, top_k: int = 5):
    logger.info("Starting chunk retrieval for query: %s", query)
    # query_embedding = embeddings_model.encode(query).tolist()
    query_embedding = gemini_embed_text(query)[0]  # Assuming gemini_embed_text returns a list of embeddings

    v_threshold = (1 + float(os.getenv('KB_SEARCH_COSINE_SIM_THR', '0.60'))) / 2.0
    fts_threshold = float(os.getenv('FTS_SEARCH_SIM_THR', '1.5'))
    alpha = 0.8

    # Build aggregation pipeline for a given query
    def build_pipeline(collection_name):
        logger.info("Building aggregation pipeline")
        return [
            {'$vectorSearch': {
                'index': 'faq_vector',
                'path': 'embeddings',
                'queryVector': query_embedding,
                'exact': True,
                'limit': 20
            }},
            {'$addFields': {'v_score': {'$meta': 'vectorSearchScore'}}},
            {'$group': {'_id': None, 'docs': {'$push': '$$ROOT'}}},
            {'$unwind': {'path': '$docs', 'includeArrayIndex': 'v_rank'}},
            {'$addFields': {
                'docs.v_rrf': {'$divide': [1, {'$add': ['$v_rank', 60.0, 1]}]},
                'docs.v_rank': '$v_rank',
                '_id': '$docs._id'
            }},
            {'$replaceRoot': {'newRoot': '$docs'}},
            {'$unionWith': {
                'coll': collection_name,
                'pipeline': [
                    {'$search': {
                        'index': 'search_index',
                        'text': {'query': query, 'path': 'text'}
                    }},
                    {'$addFields': {'fts_score': {'$meta': 'searchScore'}}},
                    {'$limit': 20},
                    {'$group': {'_id': None, 'docs': {'$push': '$$ROOT'}}},
                    {'$unwind': {'path': '$docs', 'includeArrayIndex': 'fts_rank'}},
                    {'$addFields': {
                        'docs.fts_rrf': {'$divide': [1, {'$add': ['$fts_rank', 60.0, 1]}]},
                        'docs.fts_rank': '$fts_rank',
                        '_id': '$docs._id'
                    }},
                    {'$replaceRoot': {'newRoot': '$docs'}}
                ]
            }},
            {'$group': {'_id': '$_id', 'docs': {'$mergeObjects': '$$ROOT'}}},
            {'$replaceRoot': {'newRoot': '$docs'}},
            {'$set': {
                'v_rrf': {'$ifNull': ['$v_rrf', 0]},
                'fts_rrf': {'$ifNull': ['$fts_rrf', 0]}
            }},
            {'$match': {
                '$expr': {
                    '$or': [
                        {'$gte': ['$fts_score', fts_threshold]},
                        {'$gte': ['$v_score', v_threshold]}
                    ]
                }
            }},
            {'$addFields': {
                'score': {
                    '$add': [
                        {'$multiply': ['$v_rrf', alpha]},
                        {'$multiply': ['$fts_rrf', (1 - alpha)]}
                    ]
                }
            }},
            {'$sort': {'score': -1}},
            {'$limit': 20},
            {'$project': {'_id': 0, 'embeddings': 0, 'fts_rank': 0, 'v_rank': 0, 'v_rrf': 0, 'fts_rrf': 0}}
        ]
        
    # Async function to fetch from one KB
    async def fetch_kb_results(label: str, uri: str, kb_id: str):
        try:
            client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=30000)
            db = client.app_db
            collection_name = f"{kb_id}"
            logger.info(f"Querying KB: {kb_id} on {label}")
            collection = db[collection_name]
            cursor = collection.aggregate(build_pipeline(collection_name))
            results = [doc async for doc in cursor]
            logger.info(f"Retrieved {len(results)} docs from {label}.{kb_id}")
            for doc in results:
                doc["source"] = f"{label}.{kb_id}"
            return results
        
        except (ServerSelectionTimeoutError, Exception) as e:
            logger.exception(f"Error for {label}.{kb_id} at {uri}: {e}")
            raise HTTPException(status_code=503, detail=f"Error accessing {label}: {e}")
        
        finally:
            client.close()
            
    # Build all concurrent tasks
    logger.info("Launching concurrent KB retrieval tasks...")
    tasks = [
        fetch_kb_results(label, entry['uri'], kb_id)
        for label, entry in mongo_uris.items()
        for kb_id in entry['kb_ids']
    ]

    all_results_nested = await asyncio.gather(*tasks)
    all_results = [doc for sublist in all_results_nested for doc in sublist]

    logger.info("Aggregated %d total documents across all KBs", len(all_results))

    # Sort globally by score and return top_k
    sorted_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
    unique_results = await get_unique_chunks(sorted_results)
    top_k_unique_results = unique_results[:top_k]
    return [i for i in top_k_unique_results]

