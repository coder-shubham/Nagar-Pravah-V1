"""
Core helper functions and logic for Nagar Pravah AI Platform
Shared across all agents for consistent data processing
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import google.generativeai as genai
from google.cloud import firestore


class NagarPravahUtils:
    """Core utility functions for the Nagar Pravah platform"""
    
    def __init__(self, gemini_api_key: str):
        """Initialize with Gemini API key"""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.db = firestore.Client()
    
    def calculate_fingerprint(self, scouted_data: Dict[str, Any]) -> str:
        """
        Generate a unique fingerprint for event deduplication
        
        Args:
            scouted_data: Dictionary containing 'content' and 'fetched_at' fields
            
        Returns:
            String fingerprint in format: EVENT_TYPE-LOCATION_NOUN-YYYYMMDD_HH00
        """
        content = scouted_data.get('content', '')
        fetched_at = scouted_data.get('fetched_at')
        
        # Step 1: Extract entities using Gemini
        entity_prompt = """
        From the following text, extract the primary event type (e.g., 'Traffic', 'Fire', 'Protest') 
        and the most specific location noun (e.g., 'Marathahalli Bridge', 'Forum Mall'). 
        Return as JSON: {"event_type": "...", "location_noun": "..."}
        
        Text: {content}
        """.format(content=content)
        
        try:
            response = self.model.generate_content(entity_prompt)
            entities = json.loads(response.text)
            event_type = entities.get('event_type', 'UNKNOWN')
            location_noun = entities.get('location_noun', 'UNKNOWN')
        except Exception as e:
            print(f"Error extracting entities: {e}")
            event_type = 'UNKNOWN'
            location_noun = 'UNKNOWN'
        
        # Step 2: Normalize text
        normalized_event_type = event_type.upper().replace(' ', '_')
        normalized_location_noun = location_noun.upper().replace(' ', '_')
        
        # Step 3: Bucket timestamp to hour
        if isinstance(fetched_at, datetime):
            timestamp = fetched_at
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Truncate to hour and format
        hourly_timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        formatted_timestamp = hourly_timestamp.strftime('%Y%m%d_%H00')
        
        # Step 4: Concatenate and return
        fingerprint = f"{normalized_event_type}-{normalized_location_noun}-{formatted_timestamp}"
        return fingerprint
    
    def calculate_priority_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate priority score for an event based on multiple factors
        
        Args:
            data: Dictionary containing 'semantic_severity', 'source', and 'content'
            
        Returns:
            Float between 1.0 and 10.0 representing priority
        """
        # Define weights
        semantic_weight = 0.5
        source_authority_weight = 0.3
        keyword_weight = 0.2
        
        # Get semantic score (1-10 from Gemini)
        semantic_score = data.get('semantic_severity', 5)
        
        # Source authority mapping
        source_authority_map = {
            "@blrcitytraffic": 10,
            "@BangaloreMirror": 8,
            "user_report": 7,
            "default": 4
        }
        source = data.get('source', 'default')
        source_score = source_authority_map.get(source, source_authority_map['default'])
        
        # Keyword urgency mapping
        keyword_urgency_map = {
            "fire": 10,
            "explosion": 10,
            "accident": 9,
            "gridlock": 8,
            "traffic jam": 7,
            "road closure": 6,
            "protest": 8,
            "flood": 9
        }
        
        content = data.get('content', '').lower()
        keyword_score = 0
        for keyword, score in keyword_urgency_map.items():
            if keyword in content:
                keyword_score = max(keyword_score, score)
        
        # Calculate weighted average
        priority_score = (
            (semantic_score * semantic_weight) +
            (source_score * source_authority_weight) +
            (keyword_score * keyword_weight)
        )
        
        # Ensure score is between 1.0 and 10.0
        return max(1.0, min(10.0, priority_score))
    
    def analyze_content_with_gemini(self, content_batch: list) -> list:
        """
        Batch analyze content using Gemini for category, summary, severity, and location
        
        Args:
            content_batch: List of content strings to analyze
            
        Returns:
            List of analysis results
        """
        batch_prompt = """
        Analyze the following content items and return a JSON array with analysis for each item.
        For each item, provide:
        - category: Primary category (e.g., "Traffic", "Civic Issue", "Weather", "Cultural Event")
        - content_summary: One-sentence summary of the event
        - semantic_severity: Severity score from 1-10 based on language nuance
        - address_string: Most specific location mentioned in the text
        
        Content items:
        {content_items}
        
        Return format: [
            {{
                "category": "...",
                "content_summary": "...",
                "semantic_severity": ...,
                "address_string": "..."
            }},
            ...
        ]
        """.format(content_items=json.dumps(content_batch, indent=2))
        
        try:
            response = self.model.generate_content(batch_prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Error analyzing content with Gemini: {e}")
            # Return default analysis for each item
            return [
                {
                    "category": "Unknown",
                    "content_summary": content[:100] + "...",
                    "semantic_severity": 5,
                    "address_string": "Bangalore"
                }
                for content in content_batch
            ]
    
    def get_checkpoint_timestamp(self, agent_name: str) -> Optional[datetime]:
        """
        Get the last processed timestamp for an agent
        
        Args:
            agent_name: Name of the agent (e.g., 'analyze-agent')
            
        Returns:
            Last processed timestamp or None if not found
        """
        try:
            doc_ref = self.db.collection('agent-state').document(f'{agent_name}-checkpoint')
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get('last_processed_timestamp')
            return None
        except Exception as e:
            print(f"Error getting checkpoint: {e}")
            return None
    
    def update_checkpoint_timestamp(self, agent_name: str, timestamp: datetime) -> bool:
        """
        Update the checkpoint timestamp for an agent
        
        Args:
            agent_name: Name of the agent
            timestamp: New timestamp to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection('agent-state').document(f'{agent_name}-checkpoint')
            doc_ref.set({
                'last_processed_timestamp': timestamp
            }, merge=True)
            return True
        except Exception as e:
            print(f"Error updating checkpoint: {e}")
            return False


# Configuration constants
SOURCE_AUTHORITY_CONFIG = {
    "@blrcitytraffic": 10,
    "@BangaloreMirror": 8,
    "@timesofindia": 7,
    "user_report": 7,
    "default": 4
}

KEYWORD_URGENCY_CONFIG = {
    "fire": 10,
    "explosion": 10,
    "accident": 9,
    "gridlock": 8,
    "traffic jam": 7,
    "road closure": 6,
    "protest": 8,
    "flood": 9,
    "power outage": 6,
    "water shortage": 7
}

CATEGORY_MAPPING = {
    "traffic": "Traffic",
    "civic": "Civic Issue", 
    "weather": "Weather",
    "culture": "Cultural Event",
    "emergency": "Emergency",
    "infrastructure": "Infrastructure"
}