# Conversational Agent - main.py
import os
import json
import re
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from google.cloud import firestore
import google.generativeai as genai
import googlemaps
from typing import Dict, Any, List

app = Flask(__name__)

class ConversationalAgent:
    """Agent responsible for handling user queries using ReAct methodology"""
    
    def __init__(self):
        self.db = firestore.Client()
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Initialize Google Maps client
        self.gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
        
        # Available tools
        self.tools = {
            'search_synthesized_events': self.search_synthesized_events,
            'search_analyzed_data': self.search_analyzed_data,
            'get_live_traffic_tool': self.get_live_traffic_tool,
            'get_weather_info': self.get_weather_info,
            'get_location_events': self.get_location_events
        }
    
    def search_synthesized_events(self, keywords: str, limit: int = 10) -> List[Dict]:
        """
        Search synthesized events by keywords
        
        Args:
            keywords: Search keywords
            limit: Maximum number of results
            
        Returns:
            List of matching events
        """
        try:
            events_ref = self.db.collection('synthesized-events')
            
            # Get recent events (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            query = events_ref.where('created_at', '>=', cutoff_time).order_by('created_at', direction=firestore.Query.DESCENDING)
            
            events = []
            for doc in query.limit(50).stream():  # Get more to filter by keywords
                event_data = doc.to_dict()
                event_data['doc_id'] = doc.id
                
                # Simple keyword matching
                search_text = f"{event_data.get('title', '')} {event_data.get('summary', '')}".lower()
                if any(keyword.lower() in search_text for keyword in keywords.split()):
                    events.append({
                        'id': doc.id,
                        'title': event_data.get('title', ''),
                        'summary': event_data.get('summary', ''),
                        'severity': event_data.get('severity', 'Medium'),
                        'status': event_data.get('status', 'active'),
                        'created_at': event_data.get('created_at'),
                        'suggestion': event_data.get('suggestion', {})
                    })
                
                if len(events) >= limit:
                    break
            
            return events
            
        except Exception as e:
            print(f"Error searching synthesized events: {e}")
            return []
    
    def search_analyzed_data(self, keywords: str, location: str = None, limit: int = 15) -> List[Dict]:
        """
        Search analyzed data by keywords and optionally location
        
        Args:
            keywords: Search keywords
            location: Optional location filter
            limit: Maximum number of results
            
        Returns:
            List of matching analyzed data
        """
        try:
            data_ref = self.db.collection('analyzed-data')
            
            # Get recent data (last 6 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6)
            query = data_ref.where('updated_at', '>=', cutoff_time).order_by('updated_at', direction=firestore.Query.DESCENDING)
            
            results = []
            for doc in query.limit(100).stream():  # Get more to filter
                data = doc.to_dict()
                
                # Keywords matching
                search_text = f"{data.get('content_summary', '')} {data.get('category', '')}".lower()
                keyword_match = any(keyword.lower() in search_text for keyword in keywords.split())
                
                # Location matching if specified
                location_match = True
                if location:
                    address_string = data.get('location', {}).get('address_string', '').lower()
                    location_match = location.lower() in address_string
                
                if keyword_match and location_match:
                    results.append({
                        'category': data.get('category', 'Unknown'),
                        'summary': data.get('content_summary', ''),
                        'location': data.get('location', {}).get('address_string', ''),
                        'priority_score': data.get('priority_score', 0),
                        'severity': data.get('semantic_severity', 5),
                        'mention_count': data.get('mention_count', 1),
                        'updated_at': data.get('updated_at')
                    })
                
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            print(f"Error searching analyzed data: {e}")
            return []
    
    def get_live_traffic_tool(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Get live traffic information between two points
        
        Args:
            origin: Starting location
            destination: Ending location
            
        Returns:
            Traffic information dictionary
        """
        try:
            # Add Bangalore context if not present
            if 'bangalore' not in origin.lower() and 'bengaluru' not in origin.lower():
                origin = f"{origin}, Bangalore"
            if 'bangalore' not in destination.lower() and 'bengaluru' not in destination.lower():
                destination = f"{destination}, Bangalore"
            
            # Get directions with traffic
            directions_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode="driving",
                departure_time=datetime.now(),
                traffic_model="best_guess"
            )
            
            if not directions_result:
                return {"error": "No route found"}
            
            route = directions_result[0]
            leg = route['legs'][0]
            
            return {
                "origin": leg['start_address'],
                "destination": leg['end_address'],
                "distance": leg['distance']['text'],
                "duration": leg['duration']['text'],
                "duration_in_traffic": leg.get('duration_in_traffic', {}).get('text', 'N/A'),
                "traffic_delay": self.calculate_traffic_delay(leg),
                "overview_polyline": route['overview_polyline']['points'],
                "steps_summary": [step['html_instructions'] for step in leg['steps'][:3]]  # First 3 steps
            }
            
        except Exception as e:
            print(f"Error getting traffic info: {e}")
            return {"error": f"Failed to get traffic information: {str(e)}"}
    
    def calculate_traffic_delay(self, leg: Dict) -> str:
        """Calculate traffic delay from route leg data"""
        try:
            if 'duration_in_traffic' in leg and 'duration' in leg:
                traffic_duration = leg['duration_in_traffic']['value']
                normal_duration = leg['duration']['value']
                delay_seconds = traffic_duration - normal_duration
                
                if delay_seconds > 60:
                    delay_minutes = delay_seconds // 60
                    return f"{delay_minutes} minutes delay due to traffic"
                else:
                    return "No significant traffic delay"
            return "Traffic data not available"
        except:
            return "Traffic data not available"
    
    def get_weather_info(self, location: str = "Bangalore") -> Dict[str, Any]:
        """
        Get weather information (placeholder - integrate with weather API)
        
        Args:
            location: Location for weather info
            
        Returns:
            Weather information dictionary
        """
        # This is a placeholder - integrate with actual weather API
        return {
            "location": location,
            "status": "This feature requires weather API integration",
            "suggestion": "Check local weather apps for current conditions"
        }
    
    def get_location_events(self, location: str, radius_km: float = 5.0) -> List[Dict]:
        """
        Get events near a specific location
        
        Args:
            location: Location to search around
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby events
        """
        try:
            # Geocode the location
            geocode_result = self.gmaps.geocode(f"{location}, Bangalore")
            if not geocode_result:
                return []
            
            center_point = geocode_result[0]['geometry']['location']
            center_geopoint = firestore.GeoPoint(center_point['lat'], center_point['lng'])
            
            # Search synthesized events
            events_ref = self.db.collection('synthesized-events')
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
            
            nearby_events = []
            for doc in events_ref.where('created_at', '>=', recent_cutoff).stream():
                event_data = doc.to_dict()
                event_locations = event_data.get('locations', [])
                
                for event_location in event_locations:
                    if self.calculate_distance_km(center_geopoint, event_location) <= radius_km:
                        nearby_events.append({
                            'title': event_data.get('title', ''),
                            'summary': event_data.get('summary', ''),
                            'severity': event_data.get('severity', 'Medium'),
                            'distance_km': round(self.calculate_distance_km(center_geopoint, event_location), 1)
                        })
                        break  # Only add once per event
            
            return sorted(nearby_events, key=lambda x: x['distance_km'])[:10]
            
        except Exception as e:
            print(f"Error getting location events: {e}")
            return []
    
    def calculate_distance_km(self, point1, point2) -> float:
        """Calculate distance between two GeoPoints in kilometers"""
        import math
        
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return c * 6371  # Earth's radius in km
    
    def plan_with_gemini(self, user_query: str) -> Dict[str, Any]:
        """
        Use Gemini to plan the response strategy
        
        Args:
            user_query: User's question/request
            
        Returns:
            Planning result with tool selection and parameters
        """
        planning_prompt = f"""
        You are a city assistant for Bangalore. Analyze this user query and determine the best approach to answer it.
        
        User Query: "{user_query}"
        
        Available Tools:
        1. search_synthesized_events(keywords) - Search recent city stories and events
        2. search_analyzed_data(keywords, location) - Search detailed incident data
        3. get_live_traffic_tool(origin, destination) - Get traffic and route information
        4. get_weather_info(location) - Get weather information
        5. get_location_events(location, radius_km) - Get events near a location
        
        Determine:
        1. Which tool(s) to use
        2. What parameters to pass
        3. The overall strategy to answer the user
        
        Return as JSON:
        {{
            "strategy": "brief description of approach",
            "tools_to_use": [
                {{
                    "tool": "tool_name",
                    "parameters": {{"param1": "value1", "param2": "value2"}},
                    "reason": "why this tool is needed"
                }}
            ],
            "expected_response_type": "informational/navigational/advisory"
        }}
        """
        
        try:
            response = self.model.generate_content(planning_prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Error in planning: {e}")
            # Default fallback plan
            return {
                "strategy": "Search for relevant city information",
                "tools_to_use": [
                    {
                        "tool": "search_synthesized_events",
                        "parameters": {"keywords": user_query},
                        "reason": "General search for relevant information"
                    }
                ],
                "expected_response_type": "informational"
            }
    
    def execute_tools(self, tools_plan: List[Dict]) -> Dict[str, Any]:
        """
        Execute the planned tools and collect results
        
        Args:
            tools_plan: List of tools to execute with parameters
            
        Returns:
            Dictionary of tool results
        """
        tool_results = {}
        
        for tool_plan in tools_plan:
            tool_name = tool_plan.get('tool')
            parameters = tool_plan.get('parameters', {})
            
            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**parameters)
                    tool_results[tool_name] = {
                        'result': result,
                        'success': True,
                        'reason': tool_plan.get('reason', '')
                    }
                except Exception as e:
                    tool_results[tool_name] = {
                        'result': None,
                        'success': False,
                        'error': str(e),
                        'reason': tool_plan.get('reason', '')
                    }
            else:
                tool_results[tool_name] = {
                    'result': None,
                    'success': False,
                    'error': f"Tool '{tool_name}' not available"
                }
        
        return tool_results
    
    def synthesize_response_with_gemini(self, user_query: str, tool_results: Dict, strategy: str) -> str:
        """
        Use Gemini to synthesize the final response
        
        Args:
            user_query: Original user query
            tool_results: Results from executed tools
            strategy: The planned strategy
            
        Returns:
            Final response string
        """
        synthesis_prompt = f"""
        You are a helpful city assistant for Bangalore. Based on the user's query and the tool results, 
        provide a comprehensive and helpful response.
        
        User Query: "{user_query}"
        Strategy: {strategy}
        
        Tool Results:
        {json.dumps(tool_results, indent=2, default=str)}
        
        Guidelines:
        - Be conversational and helpful
        - Provide specific, actionable information when available
        - If traffic/route info is requested, give clear directions
        - If events are mentioned, summarize the most relevant ones
        - Always prioritize user safety and current information
        - Keep the response concise but informative
        - If no relevant information is found, suggest alternative sources or actions
        
        Provide your response in a natural, conversational tone.
        """
        
        try:
            response = self.model.generate_content(synthesis_prompt)
            return response.text
        except Exception as e:
            print(f"Error synthesizing response: {e}")
            return "I'm sorry, I encountered an issue while processing your request. Please try asking again or contact support if the problem persists."
    
    def process_user_query(self, user_query: str, user_id: str = None) -> Dict[str, Any]:
        """
        Process user query using ReAct methodology
        
        Args:
            user_query: User's question or request
            user_id: Optional user ID for personalization
            
        Returns:
            Response dictionary
        """
        try:
            # Step 1: Planning
            plan = self.plan_with_gemini(user_query)
            
            # Step 2: Tool Execution
            tool_results = self.execute_tools(plan.get('tools_to_use', []))
            
            # Step 3: Response Synthesis
            final_response = self.synthesize_response_with_gemini(
                user_query, 
                tool_results, 
                plan.get('strategy', '')
            )
            
            return {
                "status": "success",
                "response": final_response,
                "query": user_query,
                "tools_used": list(tool_results.keys()),
                "response_type": plan.get('expected_response_type', 'informational')
            }
            
        except Exception as e:
            print(f"Error processing user query: {e}")
            return {
                "status": "error",
                "response": "I'm sorry, I couldn't process your request at the moment. Please try again later.",
                "error": str(e)
            }


# Flask routes
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Main chat endpoint for user queries"""
    try:
        data = request.get_json()
        user_query = data.get('query', '')
        user_id = data.get('user_id')
        
        if not user_query:
            return jsonify({"error": "Query is required"}), 400
        
        agent = ConversationalAgent()
        result = agent.process_user_query(user_query, user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)