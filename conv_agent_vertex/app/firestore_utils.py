import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.field_path import FieldPath # Import for __name__ query if needed
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = None

def initialize_firestore():
    """Initializes the Firestore client."""
    global db
    if db is None:
        try:
            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Firestore client initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Firestore: {e}")
            db = None # Ensure db is None if initialization fails
    return db

def get_db():
    """Returns the initialized Firestore client."""
    if db is None:
        return initialize_firestore()
    return db

def get_collection_data(collection_name: str, query_params: dict = None):
    """
    Retrieves data from a Firestore collection.
    Args:
        collection_name (str): The name of the collection.
        query_params (dict): Optional dictionary of field-value pairs to filter by.
                             Example: {"status": "active", "category": "Traffic"}
                             Supports direct equality checks.
    Returns:
        list: A list of dictionaries, where each dictionary is a document from the collection.
              Returns an empty list on error or no data.
    """
    db_client = get_db()
    if not db_client:
        logger.error(f"Firestore DB client not available for collection: {collection_name}")
        return []

    try:
        collection_ref = db_client.collection(collection_name)
        if query_params:
            for field, value in query_params.items():
                # Firestore does not allow querying by FieldPath('__name__') directly for standard queries
                # For document ID queries, you'd typically use .document(doc_id).get()
                # For filtering by document ID (which is not a field), it's a specific operation.
                # Assuming query_params are for actual document fields for now.
                collection_ref = collection_ref.where(field, "==", value)

        docs = collection_ref.stream()
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id # Include document ID
            results.append(doc_data)
        logger.info(f"Successfully retrieved {len(results)} documents from {collection_name} with query {query_params}.")
        return results
    except Exception as e:
        logger.error(f"Error retrieving data from collection '{collection_name}': {e}")
        return []

# Example usage (for testing)
if __name__ == "__main__":
    # Ensure you have a firebase-service-account.json in the root directory for this to work
    # Or set the FIREBASE_SERVICE_ACCOUNT_KEY_PATH env variable
    # For local testing, you might hardcode a dummy path or ensure your .env is set up.
    # Placeholder for actual path if running outside Docker with a different structure
    # os.environ["FIREBASE_SERVICE_ACCOUNT_KEY_PATH"] = "path/to/your/firebase-service-account.json"
    initialize_firestore()

    # Test synthesized-events
    print("\n--- Synthesized Events (Active Traffic) ---")
    synthesized_events = get_collection_data("synthesized-events", {"status": "active", "category": "Traffic"})
    for event in synthesized_events:
        print(event)

    # Test analyzed-events
    print("\n--- Analyzed Events (High Severity) ---")
    analyzed_events = get_collection_data("analyzed-events", {"severity": "High"})
    for event in analyzed_events:
        print(event)

    # Test user-profile
    print("\n--- User Profile (Specific User - placeholder ID) ---")
    # You'd typically query user-profile by 'uid' (user ID)
    # For demonstration, let's assume a user with interests in "Sports"
    user_profiles = get_collection_data("user-profile") # No specific uid filter here for general testing
    if user_profiles:
        print(user_profiles[0]) # Print first found profile
    else:
        print("No user profiles found or initialized DB failed.")