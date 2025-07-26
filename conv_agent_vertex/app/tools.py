import requests
import logging
from langchain.tools import tool
from firestore_utils import get_collection_data
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- External Tool Mock-ups (replace with actual APIs) ---
@tool
def get_traffic(location: str) -> str:
    """
    Fetches real-time traffic information for a specific location in Bengaluru.
    Useful for checking road conditions, congestion, and delays.
    Args:
        location (str): The specific area or road in Bengaluru (e.g., "Koramangala", "ORR").
    Returns:
        str: A summary of traffic conditions or an error message.
    """
    try:
        logger.info(f"Calling external tool: get_traffic for location: {location}")
        # In a real scenario, this would call a traffic API (e.g., Google Maps API)
        # For now, it's a mock.
        if "NandiHill" in location:
            return "Traffic to Nandi Hills is moderate. Expect slight delays near the base due to weekend rush. Parking might be an issue."
        elif "ORR" in location:
            return "Outer Ring Road (ORR) has heavy traffic during peak hours, especially near Marathahalli and Silk Board. Consider alternative routes."
        elif "MG Road" in location:
            return "MG Road traffic is normal for this time of day. No major incidents reported."
        else:
            return f"No specific traffic information found for {location} at the moment."
    except Exception as e:
        logger.error(f"Error in get_traffic tool for {location}: {e}")
        return f"Could not retrieve traffic information for {location} due to an error."

@tool
def get_events(location: str = "", category: str = "", date: str = "") -> str:
    """
    Fetches information about upcoming or ongoing events in Bengaluru.
    Can filter by location, category (e.g., "Music", "Tech", "Food"), or date.
    Args:
        location (str): The specific area in Bengaluru.
        category (str): The type of event.
        date (str): The date of the event (e.g., "today", "this weekend", "2023-12-25").
    Returns:
        str: A list of events or an error message.
    """
    try:
        logger.info(f"Calling external tool: get_events for location: {location}, category: {category}, date: {date}")
        # In a real scenario, this would call an events API (e.g., BookMyShow, Eventbrite)
        # For now, it's a mock.
        if "NandiHill" in str(location) and "weekend" in str(date):
            return "There's a paragliding festival scheduled near Nandi Hills this weekend. Also, the local horticulture department is hosting a flower show."
        elif "Koramangala" in str(location) and "music" in str(category):
            return "Live music at Indigo Live Music Bar on Friday. Check their schedule for specifics."
        elif "today" in str(date):
            return "Multiple art exhibitions across UB City and Indiranagar. A tech meetup is happening in Manyata Tech Park."
        else:
            return "No specific events found matching your criteria."
    except Exception as e:
        logger.error(f"Error in get_events tool for location={location}, category={category}, date={date}: {e}")
        return "Could not retrieve events information due to an error."

@tool
def get_weather(location: str) -> str:
    """
    Fetches current weather conditions and forecast for a specific location in Bengaluru.
    Useful for planning outdoor activities.
    Args:
        location (str): The specific area in Bengaluru (e.g., "Bengaluru city", "Electronic City").
    Returns:
        str: Weather summary or an error message.
    """
    try:
        logger.info(f"Calling external tool: get_weather for location: {location}")
        # In a real scenario, this would call a weather API (e.g., OpenWeatherMap)
        # For now, it's a mock.
        if "NandiHill" in location:
            return "Weather at Nandi Hills this weekend: Partly cloudy with a chance of light rain in the afternoon. Temperatures around 20-25°C. Pleasant for a morning visit."
        elif "Bengaluru" in location or "city" in location:
            return "Current weather in Bengaluru: 28°C, clear skies. Forecast for the next few hours: sunny with a gentle breeze."
        else:
            return f"Weather information for {location} is not available."
    except Exception as e:
        logger.error(f"Error in get_weather tool for {location}: {e}")
        return f"Could not retrieve weather information for {location} due to an error."

# --- Firestore Query Tools ---

@tool
def get_synthesized_events(query_params: str = "{}") -> str:
    """
    Retrieves synthesized stories/events from the 'synthesized-events' collection in Firestore.
    These are coherent stories derived from raw data.
    Useful for understanding major incidents, trends, or hidden connections in the city.
    Args:
        query_params (str): A JSON string of parameters to filter the events.
                           Example: '{"category": "Traffic", "status": "active", "locationString": "NandiHill"}'
                           Common filterable fields: 'title', 'content', 'status', 'severity',
                           'locationString', 'category', 'sentiment'.
    Returns:
        str: A formatted string of matching synthesized events or empty if none found.
    """
    logger.info(f"Calling Firestore tool: get_synthesized_events with query: {query_params}")
    try:
        import json
        # Parse query_params from JSON string
        if query_params and query_params != "{}":
            query_dict = json.loads(query_params)
        else:
            query_dict = None
        logging.info(f"Querying synthesized events with parameters: {query_dict}")    
            
        events = get_collection_data("synthesized-events", query_dict)
        if events:
            logger.info(f"Found {len(events)} synthesized events.")
            # Format events for the LLM
            result_parts = []
            for i, event in enumerate(events[:5], 1):  # Limit to first 5 events
                event_info = f"Event {i}:\n"
                for key in ['title', 'content', 'status', 'severity', 'locationString', 'category', 'suggestion', 'sentiment']:
                    if key in event:
                        event_info += f"  {key}: {event[key]}\n"
                result_parts.append(event_info)
            return "\n".join(result_parts)
        logger.warning("No synthesized events found matching the criteria.")
        return "No synthesized events found matching the criteria."
    except Exception as e:
        logger.error(f"Error in get_synthesized_events tool with query {query_params}: {e}")
        return f"Error retrieving synthesized events: {str(e)}"

@tool
def get_analyzed_events(query_params: str = "{}") -> str:
    """
    Retrieves analyzed events from the 'analyzed-events' collection in Firestore.
    These are verified and structured raw data points before synthesis.
    Useful for detailed, specific incidents that might not yet be part of a larger story.
    Args:
        query_params (str): A JSON string of parameters to filter the events.
                           Example: '{"category": "CivicIssue", "severity": "High", "locationString": "Koramangala"}'
                           Common filterable fields: 'category', 'locationString', 'severity', 'content'.
    Returns:
        str: A formatted string of matching analyzed events or empty if none found.
    """
    logger.info(f"Calling Firestore tool: get_analyzed_events with query: {query_params}")
    try:
        import json
        # Parse query_params from JSON string
        if query_params and query_params != "{}":
            query_dict = json.loads(query_params)
        else:
            query_dict = None
            
        events = get_collection_data("analyzed-events", query_dict)
        if events:
            logger.info(f"Found {len(events)} analyzed events.")
            # Format events for the LLM
            result_parts = []
            for i, event in enumerate(events[:5], 1):  # Limit to first 5 events
                event_info = f"Event {i}:\n"
                for key in ['category', 'locationString', 'content', 'severity']:
                    if key in event:
                        event_info += f"  {key}: {event[key]}\n"
                result_parts.append(event_info)
            return "\n".join(result_parts)
        return "No analyzed events found matching the criteria."
    except Exception as e:
        logger.error(f"Error in get_analyzed_events tool with query {query_params}: {e}")
        return f"Error retrieving analyzed events: {str(e)}"

@tool
def get_user_profile(user_id: str) -> str:
    """
    Retrieves a user's profile information from the 'user-profile' collection in Firestore.
    This includes user preferences, interests, home, and work locations.
    Useful for tailoring responses and providing personalized suggestions.
    Args:
        user_id (str): The unique ID of the user.
    Returns:
        str: The user's profile information as a formatted string, or "Not found" if not found.
    """
    logger.info(f"Calling Firestore tool: get_user_profile for user_id: {user_id}")
    try:
        # Query by 'uid' field
        profiles = get_collection_data("user-profile", {"uid": user_id})
        if profiles and len(profiles) > 0:
            logger.info(f"Found user profile for {user_id}.")
            profile = profiles[0]
            # Format profile info
            profile_info = f"User Profile for {user_id}:\n"
            for key in ['uid', 'displayName', 'interests', 'homeLocation', 'workLocation']:
                if key in profile:
                    profile_info += f"  {key}: {profile[key]}\n"
            return profile_info
        logger.warning(f"User profile not found for user_id: {user_id}")
        return f"User profile not found for user_id: {user_id}"
    except Exception as e:
        logger.error(f"Error in get_user_profile tool for user_id {user_id}: {e}")
        return f"Error retrieving user profile: {str(e)}"

# List of all tools available to the agent
all_tools = [
    get_traffic,
    get_events,
    get_weather,
    get_synthesized_events,
    get_analyzed_events,
    get_user_profile
]

# Debug: Print tool information
if __name__ == "__main__":
    print("Available tools:")
    for tool in all_tools:
        print(f"- {tool.name}: {tool.description}")