from flask import Flask, request, jsonify
import logging
from agents import run_agent_query
from firestore_utils import initialize_firestore # Import for initialization
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY # Needed for Flask sessions if you were using them directly

# Initialize Firestore when the app starts
with app.app_context():
    db_client = initialize_firestore()
    if not db_client:
        logger.critical("Failed to initialize Firestore. Exiting application.")
        # You might want to raise an exception or handle this more gracefully
        # depending on your deployment strategy.
        exit(1) # Or simply log and allow app to run with limited functionality

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles incoming chat requests from the mobile app.
    Expected JSON payload: {"query": "user message", "userId": "user_id", "sessionId": "session_id"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    query = data.get('query')
    user_id = data.get('userId')
    session_id = data.get('sessionId')

    if not all([query, user_id, session_id]):
        return jsonify({"error": "Missing query, userId, or sessionId in request"}), 400

    logger.info(f"Received request from User: {user_id}, Session: {session_id}, Query: '{query}'")

    try:
        # Run the query through the Langchain agent
        ai_response = run_agent_query(user_id, session_id, query)
        return jsonify({"response": ai_response}), 200
    except Exception as e:
        logger.error(f"Unhandled error during chat processing for user {user_id}, session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred while processing your request."}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "message": "Bengaluru AI Agent is running!"}), 200

if __name__ == '__main__':
    # Flask development server
    # For production, use a WSGI server like Gunicorn
    app.run(host='0.0.0.0', port=5010, debug=True) # debug=True should be False in production
