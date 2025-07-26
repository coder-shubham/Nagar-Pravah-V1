# Analyze Agent - main.py
import os
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from google.cloud import firestore
from googlemaps import Client as GoogleMapsClient
from utils import NagarPravahUtils

app = Flask(__name__)

class AnalyzeAgent:
    """Agent responsible for analyzing and enriching scouted data"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.utils = NagarPravahUtils(os.getenv('GEMINI_API_KEY'))
        self.gmaps = GoogleMapsClient(key=os.getenv('GOOGLE_MAPS_API_KEY'))
        
    def get_unprocessed_data(self, limit: int = 500) -> list:
        """
        Get unprocessed data from scouted-data collection based on checkpoint
        
        Args:
            limit: Maximum number of documents to process
            
        Returns:
            List of unprocessed documents
        """
        try:
            # Get last processed timestamp
            last_timestamp = self.utils.get_checkpoint_timestamp('analyze')
            
            # Query for new documents
            query = self.db.collection('scouted-data').order_by('fetched_at')
            
            if last_timestamp:
                query = query.where('fetched_at', '>', last_timestamp)
            
            docs = query.limit(limit).stream()
            
            documents = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                documents.append(doc_data)
            
            return documents
            
        except Exception as e:
            print(f"Error getting unprocessed data: {e}")
            return []
    
    def process_documents_batch(self, documents: list) -> bool:
        """
        Process a batch of documents through the analysis pipeline
        
        Args:
            documents: List of document dictionaries to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Calculate fingerprints and check for existing documents
            unique_documents = []
            existing_updates = []
            
            for doc in documents:
                fingerprint = self.utils.calculate_fingerprint(doc)
                
                # Check if document already exists in analyzed-data
                existing_doc_ref = self.db.collection('analyzed-data').document(fingerprint)
                existing_doc = existing_doc_ref.get()
                
                if existing_doc.exists:
                    # Document exists, prepare for mention count increment
                    existing_updates.append({
                        'doc_ref': existing_doc_ref,
                        'source_id': doc.get('source_id'),
                        'current_data': existing_doc.to_dict()
                    })
                else:
                    # New document, add to unique processing queue
                    doc['fingerprint'] = fingerprint
                    unique_documents.append(doc)
            
            # Step 2: Update existing documents (increment mention_count)
            if existing_updates:
                batch = self.db.batch()
                for update in existing_updates:
                    current_data = update['current_data']
                    new_mention_count = current_data.get('mention_count', 1) + 1
                    
                    # Add source_id if it's not already in the list
                    source_ids = current_data.get('source_ids', [])
                    source_id = update['source_id']
                    if source_id not in source_ids:
                        source_ids.append(source_id)
                    
                    batch.update(update['doc_ref'], {
                        'mention_count': new_mention_count,
                        'source_ids': source_ids,
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                
                batch.commit()
                print(f"Updated {len(existing_updates)} existing documents")
            
            # Step 3: Process unique documents if any exist
            if not unique_documents:
                return True
            
            # Step 4: Batch analyze content with Gemini
            content_batch = [doc.get('content', '') for doc in unique_documents]
            analysis_results = self.utils.analyze_content_with_gemini(content_batch)
            
            # Step 5: Geocode locations
            geocoded_locations = self.batch_geocode_locations(analysis_results)
            
            # Step 6: Calculate priority scores and prepare final documents
            final_documents = []
            for i, doc in enumerate(unique_documents):
                analysis = analysis_results[i] if i < len(analysis_results) else {}
                location_data = geocoded_locations[i] if i < len(geocoded_locations) else {}
                
                # Calculate priority score
                priority_data = {
                    'semantic_severity': analysis.get('semantic_severity', 5),
                    'source': doc.get('source', 'default'),
                    'content': doc.get('content', '')
                }
                priority_score = self.utils.calculate_priority_score(priority_data)
                
                analyzed_doc = {
                    'fingerprint': doc['fingerprint'],
                    'category': analysis.get('category', 'Unknown'),
                    'content_summary': analysis.get('content_summary', doc.get('content', '')[:100]),
                    'location': {
                        'geopoint': location_data.get('geopoint'),
                        'address_string': analysis.get('address_string', 'Bangalore')
                    },
                    'priority_score': priority_score,
                    'semantic_severity': analysis.get('semantic_severity', 5),
                    'mention_count': 1,
                    'source_ids': [doc.get('source_id', '')],
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }
                final_documents.append(analyzed_doc)
            
            # Step 7: Batch write to analyzed-data collection
            if final_documents:
                batch = self.db.batch()
                for doc_data in final_documents:
                    doc_ref = self.db.collection('analyzed-data').document(doc_data['fingerprint'])
                    batch.set(doc_ref, doc_data)
                
                batch.commit()
                print(f"Created {len(final_documents)} new analyzed documents")
            
            return True
            
        except Exception as e:
            print(f"Error processing documents batch: {e}")
            return False
    
    def batch_geocode_locations(self, analysis_results: list) -> list:
        """
        Geocode location strings using Google Maps API
        
        Args:
            analysis_results: List of analysis results containing address_string
            
        Returns:
            List of geocoding results
        """
        geocoded_results = []
        
        for analysis in analysis_results:
            address_string = analysis.get('address_string', '')
            
            try:
                if address_string and address_string != 'Bangalore':
                    # Add Bangalore context for better geocoding
                    full_address = f"{address_string}, Bangalore, Karnataka, India"
                    
                    geocode_result = self.gmaps.geocode(full_address)
                    
                    if geocode_result:
                        location = geocode_result[0]['geometry']['location']
                        geopoint = firestore.GeoPoint(location['lat'], location['lng'])
                        geocoded_results.append({'geopoint': geopoint})
                    else:
                        # Default to Bangalore center if geocoding fails
                        geocoded_results.append({
                            'geopoint': firestore.GeoPoint(12.9716, 77.5946)
                        })
                else:
                    # Default location for Bangalore
                    geocoded_results.append({
                        'geopoint': firestore.GeoPoint(12.9716, 77.5946)
                    })
                    
            except Exception as e:
                print(f"Error geocoding address '{address_string}': {e}")
                geocoded_results.append({
                    'geopoint': firestore.GeoPoint(12.9716, 77.5946)
                })
        
        return geocoded_results
    
    def run_analyze_cycle(self):
        """Execute one complete analyze cycle"""
        print("Starting analyze cycle...")
        
        # Get unprocessed documents
        documents = self.get_unprocessed_data()
        
        if not documents:
            return {"status": "success", "message": "No new documents to process"}
        
        print(f"Processing {len(documents)} documents")
        
        # Process the batch
        success = self.process_documents_batch(documents)
        
        if success and documents:
            # Update checkpoint to the latest processed timestamp
            latest_timestamp = max(doc.get('fetched_at', datetime.now(timezone.utc)) 
                                 for doc in documents)
            self.utils.update_checkpoint_timestamp('analyze', latest_timestamp)
            
            return {
                "status": "success", 
                "documents_processed": len(documents),
                "latest_timestamp": latest_timestamp.isoformat()
            }
        else:
            return {"status": "error", "message": "Failed to process documents"}


# Flask routes for Cloud Run
@app.route('/', methods=['POST', 'GET'])
def main():
    """Main entry point for Cloud Scheduler trigger"""
    try:
        analyzer = AnalyzeAgent()
        result = analyzer.run_analyze_cycle()
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in analyze agent: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)