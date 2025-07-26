# Synthesize Agent - main.py
import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from google.cloud import firestore, pubsub_v1
import google.generativeai as genai

app = Flask(__name__)

class SynthesizeAgent:
    """Agent responsible for creating high-level stories from analyzed events"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.publisher = pubsub_v1.PublisherClient()
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Pub/Sub topic for new stories
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.topic_path = self.publisher.topic_path(project_id, 'new-story-topic')
    
    def get_significant_events(self, lookback_minutes: int = 15, min_priority: float = 5.0) -> list:
        """
        Get significant events from the last N minutes with priority above threshold
        
        Args:
            lookback_minutes: How far back to look for events
            min_priority: Minimum priority score to consider
            
        Returns:
            List of significant events
        """
        try:
            # Calculate cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            
            # Query for significant events
            events_ref = self.db.collection('analyzed-data')
            query = (events_ref
                    .where('updated_at', '>=', cutoff_time)
                    .where('priority_score', '>', min_priority)
                    .order_by('priority_score', direction=firestore.Query.DESCENDING)
                    .limit(20))  # Limit to top 20 events to avoid overwhelming synthesis
            
            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                event_data['doc_id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            print(f"Error getting significant events: {e}")
            return []
    
    def synthesize_events_with_gemini(self, events: list) -> dict:
        """
        Use Gemini to synthesize events into cohesive stories
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dictionary containing synthesized story data
        """
        if not events:
            return None
        
        # Prepare events data for Gemini
        events_summary = []
        for event in events:
            summary = {
                'category': event.get('category', 'Unknown'),
                'summary': event.get('content_summary', ''),
                'location': event.get('location', {}).get('address_string', 'Bangalore'),
                'priority_score': event.get('priority_score', 0),
                'severity': event.get('semantic_severity', 5),
                'mention_count': event.get('mention_count', 1)
            }
            events_summary.append(summary)
        
        synthesis_prompt = f"""
        You are a city news synthesizer for Bangalore. Given these {len(events)} significant events, 
        create a cohesive, newsworthy story that citizens would find valuable.
        
        Events data: {json.dumps(events_summary, indent=2)}
        
        Create a synthesis that includes:
        1. A compelling newspaper-style headline (title)
        2. A detailed paragraph summary explaining the situation, causes, and current impact
        3. Current status (one of: "active", "developing", "closed")
        4. Severity level (one of: "High", "Medium", "Low")
        5. An actionable suggestion with type and text
        
        Focus on the most impactful events and create a narrative that connects related incidents.
        If events are in different categories, create separate stories or focus on the highest priority ones.
        
        Return as JSON:
        {{
            "title": "...",
            "summary": "...",
            "status": "...",
            "severity": "...",
            "suggestion": {{
                "type": "...",
                "text": "..."
            }}
        }}
        """
        
        try:
            response = self.model.generate_content(synthesis_prompt)
            synthesis_result = json.loads(response.text)
            
            # Add metadata
            synthesis_result['related_analyzed_ids'] = [event['doc_id'] for event in events]
            synthesis_result['locations'] = self.extract_geopoints_from_events(events)
            
            return synthesis_result
            
        except Exception as e:
            print(f"Error synthesizing with Gemini: {e}")
            # Return a basic synthesis as fallback
            return {
                'title': f"Multiple {events[0].get('category', 'Events')} Reports in Bangalore",
                'summary': f"Several incidents reported across the city with {len(events)} separate reports. Citizens advised to stay informed and plan accordingly.",
                'status': 'active',
                'severity': 'Medium',
                'suggestion': {
                    'type': 'general_awareness',
                    'text': 'Stay updated with local news and plan your routes accordingly.'
                },
                'related_analyzed_ids': [event['doc_id'] for event in events],
                'locations': self.extract_geopoints_from_events(events)
            }
    
    def extract_geopoints_from_events(self, events: list) -> list:
        """
        Extract all valid geopoints from events for map display
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of GeoPoint objects
        """
        geopoints = []
        for event in events:
            location = event.get('location', {})
            geopoint = location.get('geopoint')
            if geopoint:
                geopoints.append(geopoint)
        
        return geopoints
    
    def create_synthesized_event(self, synthesis_data: dict) -> str:
        """
        Create a new document in synthesized-events collection
        
        Args:
            synthesis_data: Dictionary containing synthesized event data
            
        Returns:
            Document ID of created event
        """
        try:
            # Prepare the document
            event_doc = {
                'title': synthesis_data.get('title', ''),
                'summary': synthesis_data.get('summary', ''),
                'status': synthesis_data.get('status', 'active'),
                'severity': synthesis_data.get('severity', 'Medium'),
                'locations': synthesis_data.get('locations', []),
                'suggestion': synthesis_data.get('suggestion', {}),
                'related_analyzed_ids': synthesis_data.get('related_analyzed_ids', []),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'translations': {}  # Will be populated by personalize agent
            }
            
            # Add to Firestore
            doc_ref = self.db.collection('synthesized-events').document()
            doc_ref.set(event_doc)
            
            return doc_ref.id
            
        except Exception as e:
            print(f"Error creating synthesized event: {e}")
            return None
    
    def publish_new_story(self, story_id: str) -> bool:
        """
        Publish new story ID to Pub/Sub topic
        
        Args:
            story_id: Document ID of the new story
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_data = json.dumps({'story_id': story_id}).encode('utf-8')
            future = self.publisher.publish(self.topic_path, message_data)
            message_id = future.result()
            print(f"Published story {story_id} with message ID: {message_id}")
            return True
            
        except Exception as e:
            print(f"Error publishing to Pub/Sub: {e}")
            return False
    
    def group_events_by_category(self, events: list) -> dict:
        """
        Group events by category for better synthesis
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dictionary with categories as keys and event lists as values
        """
        grouped = {}
        for event in events:
            category = event.get('category', 'Unknown')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(event)
        
        return grouped
    
    def run_synthesis_cycle(self):
        """Execute one complete synthesis cycle"""
        print("Starting synthesis cycle...")
        
        # Get significant events
        events = self.get_significant_events()
        
        if not events:
            return {"status": "success", "message": "No significant events found"}
        
        print(f"Found {len(events)} significant events")
        
        # Group events by category for better synthesis
        grouped_events = self.group_events_by_category(events)
        
        created_stories = []
        
        # Process each category separately
        for category, category_events in grouped_events.items():
            # Only synthesize if we have enough significant events in this category
            if len(category_events) >= 1 and any(event.get('priority_score', 0) > 6.0 for event in category_events):
                
                print(f"Synthesizing {len(category_events)} events in category: {category}")
                
                # Synthesize events
                synthesis_data = self.synthesize_events_with_gemini(category_events)
                
                if synthesis_data:
                    # Create synthesized event
                    story_id = self.create_synthesized_event(synthesis_data)
                    
                    if story_id:
                        # Publish to Pub/Sub
                        if self.publish_new_story(story_id):
                            created_stories.append({
                                'story_id': story_id,
                                'category': category,
                                'events_count': len(category_events),
                                'title': synthesis_data.get('title', '')
                            })
        
        if created_stories:
            return {
                "status": "success",
                "stories_created": len(created_stories),
                "details": created_stories
            }
        else:
            return {"status": "success", "message": "No stories met synthesis threshold"}


# Flask routes for Cloud Run
@app.route('/', methods=['POST', 'GET'])
def main():
    """Main entry point for Cloud Scheduler trigger"""
    try:
        synthesizer = SynthesizeAgent()
        result = synthesizer.run_synthesis_cycle()
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in synthesize agent: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)