# Maps Agent - main.py
import os
import json
from flask import Flask, request, jsonify
from google.cloud import firestore
import base64

app = Flask(__name__)

class MapsAgent:
    """Agent responsible for creating map-optimized data from synthesized events"""
    
    def __init__(self):
        self.db = firestore.Client()
        
        # Mapping configurations for different event types
        self.category_mappings = {
            'traffic': {
                'map_type': 'traffic',
                'severity_mapping': {
                    'High': {'severity_level': 5, 'marker_icon': 'icon_traffic_critical'},
                    'Medium': {'severity_level': 3, 'marker_icon': 'icon_traffic_medium'},
                    'Low': {'severity_level': 1, 'marker_icon': 'icon_traffic_low'}
                }
            },
            'civic': {
                'map_type': 'event',
                'severity_mapping': {
                    'High': {'severity_level': 4, 'marker_icon': 'icon_civic_urgent'},
                    'Medium': {'severity_level': 2, 'marker_icon': 'icon_civic_medium'},
                    'Low': {'severity_level': 1, 'marker_icon': 'icon_civic_low'}
                }
            },
            'weather': {
                'map_type': 'weather',
                'severity_mapping': {
                    'High': {'severity_level': 5, 'marker_icon': 'icon_weather_severe'},
                    'Medium': {'severity_level': 3, 'marker_icon': 'icon_weather_moderate'},
                    'Low': {'severity_level': 1, 'marker_icon': 'icon_weather_mild'}
                }
            },
            'cultural': {
                'map_type': 'event',
                'severity_mapping': {
                    'High': {'severity_level': 2, 'marker_icon': 'icon_event_major'},
                    'Medium': {'severity_level': 1, 'marker_icon': 'icon_event_regular'},
                    'Low': {'severity_level': 1, 'marker_icon': 'icon_event_small'}
                }
            },
            'emergency': {
                'map_type': 'emergency',
                'severity_mapping': {
                    'High': {'severity_level': 5, 'marker_icon': 'icon_emergency_critical'},
                    'Medium': {'severity_level': 4, 'marker_icon': 'icon_emergency_moderate'},
                    'Low': {'severity_level': 2, 'marker_icon': 'icon_emergency_minor'}
                }
            },
            'infrastructure': {
                'map_type': 'infrastructure',
                'severity_mapping': {
                    'High': {'severity_level': 4, 'marker_icon': 'icon_infrastructure_major'},
                    'Medium': {'severity_level': 2, 'marker_icon': 'icon_infrastructure_medium'},
                    'Low': {'severity_level': 1, 'marker_icon': 'icon_infrastructure_minor'}
                }
            }
        }
        
        # Default mapping for unknown categories
        self.default_mapping = {
            'map_type': 'overall',
            'severity_mapping': {
                'High': {'severity_level': 3, 'marker_icon': 'icon_general_high'},
                'Medium': {'severity_level': 2, 'marker_icon': 'icon_general_medium'},
                'Low': {'severity_level': 1, 'marker_icon': 'icon_general_low'}
            }
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
    
    def determine_category_mapping(self, story: dict) -> dict:
        """
        Determine the appropriate category mapping for a story
        
        Args:
            story: Story document dictionary
            
        Returns:
            Category mapping configuration
        """
        title = story.get('title', '').lower()
        
        # Check for traffic-related keywords
        traffic_keywords = ['traffic', 'gridlock', 'jam', 'road', 'accident', 'vehicle', 'route']
        if any(keyword in title for keyword in traffic_keywords):
            return self.category_mappings.get('traffic', self.default_mapping)
        
        # Check for weather-related keywords
        weather_keywords = ['rain', 'storm', 'weather', 'flood', 'monsoon', 'cyclone']
        if any(keyword in title for keyword in weather_keywords):
            return self.category_mappings.get('weather', self.default_mapping)
        
        # Check for emergency keywords
        emergency_keywords = ['fire', 'explosion', 'emergency', 'accident', 'rescue', 'evacuation']
        if any(keyword in title for keyword in emergency_keywords):
            return self.category_mappings.get('emergency', self.default_mapping)
        
        # Check for civic issues
        civic_keywords = ['water', 'power', 'electricity', 'civic', 'municipality', 'garbage', 'sewage']
        if any(keyword in title for keyword in civic_keywords):
            return self.category_mappings.get('civic', self.default_mapping)
        
        # Check for cultural events
        cultural_keywords = ['event', 'festival', 'concert', 'cultural', 'celebration', 'parade']
        if any(keyword in title for keyword in cultural_keywords):
            return self.category_mappings.get('cultural', self.default_mapping)
        
        # Check for infrastructure
        infrastructure_keywords = ['construction', 'maintenance', 'infrastructure', 'bridge', 'flyover']
        if any(keyword in title for keyword in infrastructure_keywords):
            return self.category_mappings.get('infrastructure', self.default_mapping)
        
        return self.default_mapping
    
    def create_map_data_documents(self, story: dict) -> list:
        """
        Create map-data documents from a synthesized story
        
        Args:
            story: Story document dictionary
            
        Returns:
            List of map-data document dictionaries
        """
        try:
            category_mapping = self.determine_category_mapping(story)
            severity_config = category_mapping['severity_mapping'].get(
                story.get('severity', 'Medium'),
                category_mapping['severity_mapping']['Medium']
            )
            
            map_documents = []
            story_locations = story.get('locations', [])
            
            # If no specific locations, use a default Bangalore center point
            if not story_locations:
                story_locations = [firestore.GeoPoint(12.9716, 77.5946)]
            
            # Create a document for each location
            for i, location in enumerate(story_locations):
                # Create document ID
                doc_id = f"{category_mapping['map_type']}-{story.get('doc_id', 'unknown')}"
                if len(story_locations) > 1:
                    doc_id += f"-{i}"
                
                map_doc = {
                    'map_type': category_mapping['map_type'],
                    'title': story.get('title', ''),
                    'summary': story.get('summary', ''),
                    'geopoint': location,
                    'marker_icon': severity_config['marker_icon'],
                    'severity_level': severity_config['severity_level'],
                    'updated_at': story.get('updated_at'),
                    'original_event_id': story.get('doc_id', '')
                }
                
                map_documents.append({
                    'doc_id': doc_id,
                    'data': map_doc
                })
            
            # For high-impact events, also create an "overall" map entry
            if story.get('severity') == 'High' and category_mapping['map_type'] != 'overall':
                overall_doc_id = f"overall-{story.get('doc_id', 'unknown')}"
                
                # Use the first location or center of all locations
                primary_location = story_locations[0] if story_locations else firestore.GeoPoint(12.9716, 77.5946)
                
                overall_map_doc = {
                    'map_type': 'overall',
                    'title': story.get('title', ''),
                    'summary': story.get('summary', ''),
                    'geopoint': primary_location,
                    'marker_icon': 'icon_priority_high',
                    'severity_level': 5,
                    'updated_at': story.get('updated_at'),
                    'original_event_id': story.get('doc_id', '')
                }
                
                map_documents.append({
                    'doc_id': overall_doc_id,
                    'data': overall_map_doc
                })
            
            return map_documents
            
        except Exception as e:
            print(f"Error creating map data documents: {e}")
            return []
    
    def analyze_story_sentiment(self, story: dict) -> dict:
        """
        Analyze story sentiment for mood mapping (future enhancement)
        
        Args:
            story: Story document dictionary
            
        Returns:
            Sentiment analysis result
        """
        # This is a placeholder for sentiment analysis
        # Could be integrated with Gemini for sentiment analysis
        title = story.get('title', '').lower()
        summary = story.get('summary', '').lower()
        
        # Simple keyword-based sentiment analysis
        negative_keywords = ['accident', 'fire', 'explosion', 'gridlock', 'jam', 'flood', 'emergency']
        positive_keywords = ['festival', 'celebration', 'event', 'opening', 'launch']
        neutral_keywords = ['maintenance', 'construction', 'update', 'information']
        
        text_content = f"{title} {summary}"
        
        negative_score = sum(1 for keyword in negative_keywords if keyword in text_content)
        positive_score = sum(1 for keyword in positive_keywords if keyword in text_content)
        
        if negative_score > positive_score:
            return {
                'sentiment': 'negative',
                'emoji_icon': 'emoji_concerned',
                'mood_level': min(5, negative_score + 1)
            }
        elif positive_score > negative_score:
            return {
                'sentiment': 'positive',
                'emoji_icon': 'emoji_happy',
                'mood_level': min(3, positive_score)
            }
        else:
            return {
                'sentiment': 'neutral',
                'emoji_icon': 'emoji_neutral',
                'mood_level': 2
            }
    
    def create_mood_map_entry(self, story: dict) -> dict:
        """
        Create a mood-based map entry for sentiment visualization
        
        Args:
            story: Story document dictionary
            
        Returns:
            Mood map document or None
        """
        try:
            sentiment_data = self.analyze_story_sentiment(story)
            story_locations = story.get('locations', [])
            
            if not story_locations:
                return None
            
            # Use the primary location for mood mapping
            primary_location = story_locations[0]
            
            mood_doc_id = f"mood-{story.get('doc_id', 'unknown')}"
            
            mood_map_doc = {
                'map_type': 'mood',
                'title': f"City Mood: {sentiment_data['sentiment'].title()}",
                'summary': f"Based on recent events: {story.get('title', '')}",
                'geopoint': primary_location,
                'marker_icon': sentiment_data['emoji_icon'],
                'severity_level': sentiment_data['mood_level'],
                'updated_at': story.get('updated_at'),
                'original_event_id': story.get('doc_id', '')
            }
            
            return {
                'doc_id': mood_doc_id,
                'data': mood_map_doc
            }
            
        except Exception as e:
            print(f"Error creating mood map entry: {e}")
            return None
    
    def write_map_documents_to_firestore(self, map_documents: list) -> bool:
        """
        Write map documents to Firestore using batch operations
        
        Args:
            map_documents: List of map document dictionaries with doc_id and data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not map_documents:
                return True
            
            batch = self.db.batch()
            collection_ref = self.db.collection('map-data')
            
            for map_doc in map_documents:
                doc_ref = collection_ref.document(map_doc['doc_id'])
                batch.set(doc_ref, map_doc['data'])
            
            batch.commit()
            print(f"Successfully wrote {len(map_documents)} map documents to Firestore")
            return True
            
        except Exception as e:
            print(f"Error writing map documents: {e}")
            return False
    
    def cleanup_old_map_entries(self, original_event_id: str) -> bool:
        """
        Clean up old map entries for the same event (in case of updates)
        
        Args:
            original_event_id: The original synthesized event ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Query for existing map entries for this event
            map_ref = self.db.collection('map-data')
            existing_docs = map_ref.where('original_event_id', '==', original_event_id).stream()
            
            batch = self.db.batch()
            deleted_count = 0
            
            for doc in existing_docs:
                batch.delete(doc.reference)
                deleted_count += 1
            
            if deleted_count > 0:
                batch.commit()
                print(f"Cleaned up {deleted_count} old map entries for event {original_event_id}")
            
            return True
            
        except Exception as e:
            print(f"Error cleaning up old map entries: {e}")
            return False
    
    def process_new_story(self, story_id: str) -> dict:
        """
        Process a new synthesized story for map data creation
        
        Args:
            story_id: Document ID of the new story
            
        Returns:
            Processing result dictionary
        """
        # Fetch the story document
        story = self.get_story_document(story_id)
        if not story:
            return {"status": "error", "message": "Story not found"}
        
        print(f"Processing story for maps: {story.get('title', 'Unknown')}")
        
        # Clean up any existing map entries for this event
        self.cleanup_old_map_entries(story_id)
        
        # Create map data documents
        map_documents = self.create_map_data_documents(story)
        
        # Add mood map entry if applicable
        mood_doc = self.create_mood_map_entry(story)
        if mood_doc:
            map_documents.append(mood_doc)
        
        if not map_documents:
            return {"status": "error", "message": "No map documents created"}
        
        # Write to Firestore
        success = self.write_map_documents_to_firestore(map_documents)
        
        if success:
            return {
                "status": "success",
                "story_id": story_id,
                "map_documents_created": len(map_documents),
                "map_types": list(set(doc['data']['map_type'] for doc in map_documents)),
                "story_title": story.get('title', '')
            }
        else:
            return {"status": "error", "message": "Failed to write map documents"}


# Flask routes for Cloud Run
@app.route('/_ah/push-handlers/new-story', methods=['POST'])
def pubsub_handler():
    """Handle Pub/Sub push messages for new stories"""
    try:
        envelope = request.get_json()
        if not envelope:
            return 'Bad Request: no Pub/Sub message received', 400
        
        if not isinstance(envelope, dict) or 'message' not in envelope:
            return 'Bad Request: invalid Pub/Sub message format', 400
        
        # Decode the message
        message_data = base64.b64decode(envelope['message']['data']).decode('utf-8')
        message_json = json.loads(message_data)
        
        story_id = message_json.get('story_id')
        if not story_id:
            return 'Bad Request: no story_id in message', 400
        
        # Process the story for maps
        maps_agent = MapsAgent()
        result = maps_agent.process_new_story(story_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in Maps Agent Pub/Sub handler: {e}")
        return f'Internal Server Error: {str(e)}', 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/process-story', methods=['POST'])
def process_story_endpoint():
    """Manual endpoint for processing stories (useful for testing)"""
    try:
        data = request.get_json()
        story_id = data.get('story_id')
        
        if not story_id:
            return jsonify({"error": "story_id is required"}), 400
        
        maps_agent = MapsAgent()
        result = maps_agent.process_new_story(story_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in manual story processing: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)