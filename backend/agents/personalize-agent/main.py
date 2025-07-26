# Personalize Agent - main.py
import os
import json
import math
from flask import Flask, request, jsonify
from google.cloud import firestore, pubsub_v1, translate_v2 as translate
from firebase_admin import credentials, messaging, initialize_app

app = Flask(__name__)

# Initialize Firebase Admin SDK
try:
    cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
    if cred_path:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
    else:
        # Use default credentials in Cloud Run
        initialize_app()
except Exception as e:
    print(f"Firebase initialization error: {e}")

class PersonalizeAgent:
    """Agent responsible for personalizing content and sending notifications"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.translate_client = translate.Client()
        
        # Supported languages
        self.supported_languages = {
            'en': 'English',
            'kn': 'Kannada',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'te': 'Telugu'
        }
    
    def get_story_document(self, story_id: str) -> dict:
        """
        Fetch story document from synthesized-events collection
        
        Args:
            story_id: Document ID of the story
            
        Returns:
            Story document dictionary or None
        """
        try:
            doc_ref = self.db.collection('synthesized-events').document(story_id)
            doc = doc_ref.get()
            
            if doc.exists:
                story_data = doc.to_dict()
                story_data['doc_id'] = doc.id
                return story_data
            else:
                print(f"Story document {story_id} not found")
                return None
                
        except Exception as e:
            print(f"Error fetching story document: {e}")
            return None
    
    def find_relevant_users(self, story: dict) -> list:
        """
        Find users who should receive notifications for this story
        
        Args:
            story: Story document dictionary
            
        Returns:
            List of relevant user profiles
        """
        try:
            relevant_users = []
            
            # Get all user profiles
            users_ref = self.db.collection('user-profiles')
            users = users_ref.stream()
            
            story_locations = story.get('locations', [])
            story_category = story.get('title', '').lower()
            
            for user_doc in users:
                user_data = user_doc.to_dict()
                user_data['uid'] = user_doc.id
                
                is_relevant = False
                
                # Check location relevance
                if story_locations:
                    user_home = user_data.get('home_location')
                    user_work = user_data.get('work_location')
                    
                    for story_location in story_locations:
                        # Check if story location is within 10km of user's locations
                        if user_home and self.calculate_distance(user_home, story_location) <= 10:
                            is_relevant = True
                            break
                        if user_work and self.calculate_distance(user_work, story_location) <= 10:
                            is_relevant = True
                            break
                
                # Check interest relevance
                user_interests = user_data.get('interests', [])
                if user_interests:
                    for interest in user_interests:
                        if interest.lower() in story_category:
                            is_relevant = True
                            break
                
                # High severity events go to all users
                if story.get('severity') == 'High':
                    is_relevant = True
                
                if is_relevant:
                    relevant_users.append(user_data)
            
            return relevant_users
            
        except Exception as e:
            print(f"Error finding relevant users: {e}")
            return []
    
    def calculate_distance(self, point1, point2) -> float:
        """
        Calculate distance between two GeoPoints in kilometers
        
        Args:
            point1, point2: GeoPoint objects
            
        Returns:
            Distance in kilometers
        """
        try:
            # Haversine formula
            lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
            lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth's radius in kilometers
            r = 6371
            
            return c * r
            
        except Exception as e:
            print(f"Error calculating distance: {e}")
            return float('inf')
    
    def translate_content(self, text: str, target_language: str) -> str:
        """
        Translate text to target language using Google Translate
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'kn', 'hi')
            
        Returns:
            Translated text
        """
        try:
            if target_language == 'en':
                return text
            
            result = self.translate_client.translate(
                text,
                target_language=target_language,
                source_language='en'
            )
            
            return result['translatedText']
            
        except Exception as e:
            print(f"Error translating to {target_language}: {e}")
            return text  # Return original text if translation fails
    
    def cache_translations(self, story_id: str, translations: dict) -> bool:
        """
        Cache translations in the story document
        
        Args:
            story_id: Story document ID
            translations: Dictionary of language_code -> translated_content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection('synthesized-events').document(story_id)
            doc_ref.update({
                'translations': translations
            })
            return True
            
        except Exception as e:
            print(f"Error caching translations: {e}")
            return False
    
    def send_personalized_notification(self, user: dict, story: dict, translated_content: dict) -> bool:
        """
        Send personalized FCM notification to user
        
        Args:
            user: User profile dictionary
            story: Story document dictionary
            translated_content: Dictionary with translated title and summary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user's FCM token (assuming it's stored in user profile)
            fcm_token = user.get('fcm_token')
            if not fcm_token:
                print(f"No FCM token for user {user.get('uid')}")
                return False
            
            # Create personalized notification
            notification = messaging.Notification(
                title=translated_content.get('title', story.get('title', '')),
                body=translated_content.get('summary', story.get('summary', ''))[:150] + '...'
            )
            
            # Add custom data
            data = {
                'story_id': story.get('doc_id', ''),
                'severity': story.get('severity', 'Medium'),
                'category': story.get('title', '').split()[0] if story.get('title') else 'Update',
                'type': 'city_update'
            }
            
            # Create message
            message = messaging.Message(
                notification=notification,
                data=data,
                token=fcm_token,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='city_alert',
                        color='#FF6B35',
                        priority='high' if story.get('severity') == 'High' else 'normal'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Send notification
            response = messaging.send(message)
            print(f"Notification sent successfully: {response}")
            return True
            
        except Exception as e:
            print(f"Error sending notification to user {user.get('uid')}: {e}")
            return False
    
    def process_new_story(self, story_id: str) -> dict:
        """
        Process a new story for personalization and notifications
        
        Args:
            story_id: Document ID of the new story
            
        Returns:
            Processing result dictionary
        """
        # Fetch story document
        story = self.get_story_document(story_id)
        if not story:
            return {"status": "error", "message": "Story not found"}
        
        # Find relevant users
        relevant_users = self.find_relevant_users(story)
        if not relevant_users:
            return {"status": "success", "message": "No relevant users found"}
        
        print(f"Found {len(relevant_users)} relevant users for story: {story.get('title', '')}")
        
        # Group users by language for batch translation
        users_by_language = {}
        for user in relevant_users:
            lang = user.get('preferred_language', 'en')
            if lang not in users_by_language:
                users_by_language[lang] = []
            users_by_language[lang].append(user)
        
        # Prepare translations cache
        translations_cache = story.get('translations', {})
        
        # Process each language group
        notifications_sent = 0
        for language, users in users_by_language.items():
            # Check if translation already exists
            if language not in translations_cache:
                translated_title = self.translate_content(story.get('title', ''), language)
                translated_summary = self.translate_content(story.get('summary', ''), language)
                
                translations_cache[language] = {
                    'title': translated_title,
                    'summary': translated_summary
                }
            
            # Send notifications to all users in this language group
            translated_content = translations_cache[language]
            for user in users:
                if self.send_personalized_notification(user, story, translated_content):
                    notifications_sent += 1
        
        # Cache all translations
        if translations_cache != story.get('translations', {}):
            self.cache_translations(story_id, translations_cache)
        
        return {
            "status": "success",
            "story_id": story_id,
            "relevant_users": len(relevant_users),
            "notifications_sent": notifications_sent,
            "languages_processed": list(users_by_language.keys())
        }


# Pub/Sub message handler
def handle_pubsub_message(message):
    """Handle incoming Pub/Sub message"""
    try:
        message_data = json.loads(message.data.decode('utf-8'))
        story_id = message_data.get('story_id')
        
        if not story_id:
            print("No story_id in message")
            message.ack()
            return
        
        personalizer = PersonalizeAgent()
        result = personalizer.process_new_story(story_id)
        
        print(f"Personalization result: {result}")
        message.ack()
        
    except Exception as e:
        print(f"Error processing Pub/Sub message: {e}")
        message.nack()


# Flask routes for Cloud Run
@app.route('/_ah/push-handlers/new-story', methods=['POST'])
def pubsub_handler():
    """Handle Pub/Sub push messages"""
    try:
        envelope = request.get_json()
        if not envelope:
            return 'Bad Request: no Pub/Sub message received', 400
        
        if not isinstance(envelope, dict) or 'message' not in envelope:
            return 'Bad Request: invalid Pub/Sub message format', 400
        
        # Decode the message
        import base64
        message_data = base64.b64decode(envelope['message']['data']).decode('utf-8')
        message_json = json.loads(message_data)
        
        story_id = message_json.get('story_id')
        if not story_id:
            return 'Bad Request: no story_id in message', 400
        
        # Process the story
        personalizer = PersonalizeAgent()
        result = personalizer.process_new_story(story_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in Pub/Sub handler: {e}")
        return f'Internal Server Error: {str(e)}', 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)