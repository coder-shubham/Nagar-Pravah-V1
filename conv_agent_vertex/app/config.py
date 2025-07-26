import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
     """
     Configuration class for the application.
     Loads environment variables for Firebase and Google API.
     """
     FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
     GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
     FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a_default_secret_key_if_not_set") # Provide a default for local testing