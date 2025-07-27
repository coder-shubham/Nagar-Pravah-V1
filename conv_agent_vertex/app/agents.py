import os
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage

from tools import all_tools
from config import Config

# Import the ordered agent wrapper
try:
    from ordered_agent_wrapper import OrderedBengaluruAgent, create_ordered_agent
    ORDERED_AGENT_AVAILABLE = True
except ImportError:
    ORDERED_AGENT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session store: userId -> {sessionId: conversation_history}
# conversation_history is a list of Langchain messages (HumanMessage, AIMessage)
SESSION_STORE: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"current_session_id": None, "history": []})

def get_session_history(user_id: str, session_id: str) -> list:
    """Retrieves or initializes the conversation history for a given user and session."""
    user_sessions = SESSION_STORE[user_id]

    if user_sessions["current_session_id"] != session_id:
        logger.info(f"New session ID '{session_id}' for user '{user_id}'. Clearing old session history.")
        user_sessions["current_session_id"] = session_id
        user_sessions["history"] = []
    else:
        logger.info(f"Continuing session '{session_id}' for user '{user_id}'.")

    return user_sessions["history"]

def update_session_history(user_id: str, session_id: str, human_message: str, ai_message: str):
    """Updates the conversation history with new messages."""
    history = get_session_history(user_id, session_id)
    history.append(HumanMessage(content=human_message))
    history.append(AIMessage(content=ai_message))
    logger.debug(f"Session history updated for {user_id}/{session_id}: {history}")

def format_chat_history(messages: list) -> str:
    """Convert list of messages to formatted string for the agent."""
    if not messages:
        return ""
    
    formatted_history = []
    for message in messages:
        if isinstance(message, HumanMessage):
            formatted_history.append(f"Human: {message.content}")
        elif isinstance(message, AIMessage):
            formatted_history.append(f"Assistant: {message.content}")
    
    return "\n".join(formatted_history)

def create_conversational_agent():
    """
    Initializes and returns the Langchain conversational agent.
    """
    if not Config.GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not set. Cannot initialize LLM for agent.")
        raise ValueError("GOOGLE_API_KEY environment variable is required.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.1)

    # Verify all tools have the required attributes
    for tool in all_tools:
        if not hasattr(tool, 'name'):
            logger.error(f"Tool {tool} missing 'name' attribute")
            raise ValueError(f"Tool {tool} is not properly decorated with @tool")
        if not hasattr(tool, 'description'):
            logger.error(f"Tool {tool} missing 'description' attribute")
            raise ValueError(f"Tool {tool} is not properly decorated with @tool")

    # Updated prompt template with strict tool usage hierarchy and proper React format
    prompt_template = PromptTemplate.from_template("""
You are BengaluruPulse, an intelligent conversational AI agent providing real-time,
actionable insights about Bengaluru's data noise (traffic, civic, events, weather).
Your goal is to help citizens navigate the city with foresight.

**CRITICAL: TOOL USAGE GUIDELINES**
Depending on the user's query, you have to use appropriate tools:

- Always use `get_synthesized_events` to check for synthesized stories/events
- This gives you the big picture and coherent narratives about what's happening

**IF SYNTHESIZED DATA IS INSUFFICIENT:**
- SECOND: Only if synthesized events don't provide enough detail, then use `get_analyzed_events`
- This gives you granular, specific incident data

**For specific queries**
- THIRD: Only after checking both synthesized and analyzed events, you may use external tools:
  - `get_traffic` for current traffic conditions
  - `get_events` for external event listings  
  - `get_weather` for weather information
  - `get_user_profile` for user personalization (can be used earlier if needed for location context)

**NEVER use external tools before checking internal data sources.**

Use the tools, in order to answer the user's query effectively.
                                                   
**Available Tools:**
{tools}

**Tool Names:** {tool_names}

**IMPORTANT: Use the standard ReAct format:**
```
Thought: I need to think about what to do
Action: tool_name
Action Input: tool_input
Observation: tool_result
```

**Example Tool Usage Flow:**
For query "I am looking to travel NandiHill this weekend":
```
Thought: I need to check for any synthesized events about NandiHill this weekend first
Action: get_synthesized_events
Action Input: {{"query": "NandiHill this weekend"}}
Observation: [synthesized events result]
Thought: Now I should check for more specific analyzed events if needed
Action: get_analyzed_events  
Action Input: {{"query": "NandiHill this weekend"}}
Observation: [analyzed events result]
Thought: Now I can check current traffic conditions
Action: get_traffic
Action Input: NandiHill
Observation: [traffic result]
```

**Previous Conversation:**
{chat_history}

**Current Question:** {input}

**Remember: Always start with get_synthesized_events, then get_analyzed_events if needed, then external tools.**

Begin!

Thought: {agent_scratchpad}
""")

    agent = create_react_agent(llm, all_tools, prompt_template)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=all_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,  # Increased to allow for the 3-step tool order
        early_stopping_method="force",  # Stop after first valid response
        return_intermediate_steps=True,
        max_execution_time=60  # Timeout after 60 seconds
    )
    return agent_executor

def validate_tool_usage_order(agent_steps: list) -> bool:
    """
    Validates that tools are used in the correct order:
    1. get_synthesized_events first
    2. get_analyzed_events second (if needed)
    3. External tools last (get_traffic, get_events, get_weather)
    get_user_profile can be used anytime for context.
    """
    if not agent_steps:
        return True
    
    tool_order = []
    for step in agent_steps:
        if hasattr(step, 'tool') and step.tool:
            tool_order.append(step.tool)
    
    # Check if synthesized_events was called first (excluding user_profile)
    non_profile_tools = [t for t in tool_order if t != 'get_user_profile']
    if non_profile_tools and non_profile_tools[0] != 'get_synthesized_events':
        logger.warning(f"Tool usage order violation: {tool_order}")
        return False
    
    return True

def run_agent_query(user_id: str, session_id: str, query: str, use_ordered_wrapper: bool = False) -> str:
    """
    Runs a query through the conversational agent.
    Manages session history and enforces tool usage order.
    
    Args:
        user_id: User identifier
        session_id: Session identifier  
        query: User query
        use_ordered_wrapper: Whether to use the strict tool ordering wrapper (disabled by default due to callback issues)
    """
    try:
        base_agent_executor = create_conversational_agent()
        chat_history = get_session_history(user_id, session_id)
        formatted_history = format_chat_history(chat_history)
        
        logger.info(f"Running agent query for user {user_id}, session {session_id} with query: {query}")
        logger.debug(f"Chat history for user {user_id}, session {session_id}: {formatted_history}")

        # Enhanced query with explicit ordering instructions
        enhanced_query = f"""
TOOL ORDER REMINDER:
1. If user wants to know about the latest developments around the city then start with get_synthesized_events, when synthesized events are not sufficient, use get_analyzed_events. 
2. Use get_analyzed_events only if you need more specific details after step 1
3. Use external tools (get_traffic, get_events, get_weather) when users asks for events, traffic, or weather
4. get_user_profile can be used anytime for context

USER QUERY: {query}

Follow the ReAct format:
Thought: [your reasoning]
Action: [tool_name]
Action Input: [tool_input]
"""
            
        response = base_agent_executor.invoke({
            "input": enhanced_query,
            "chat_history": formatted_history
        })
        
        # Log intermediate steps for debugging
        if "intermediate_steps" in response:
            tool_sequence = []
            for step in response['intermediate_steps']:
                if len(step) >= 1 and hasattr(step[0], 'tool'):
                    tool_sequence.append(step[0].tool)
            
            if tool_sequence:
                logger.info(f"Agent tool usage sequence: {tool_sequence}")
                
                # Validate tool sequence
                non_profile_tools = [t for t in tool_sequence if t != 'get_user_profile']
                if non_profile_tools and non_profile_tools[0] != 'get_synthesized_events':
                    logger.warning(f"Tool order violation detected: {tool_sequence}")
                    logger.warning("Agent did not start with get_synthesized_events as required")
        
        ai_response = response.get("output", "I'm sorry, I couldn't process that request.")
        update_session_history(user_id, session_id, query, ai_response)
        return ai_response
        
    except Exception as e:
        logger.error(f"Error running agent query for user {user_id}, session {session_id}: {e}", exc_info=True)
        error_message = (
            "I apologize, but I encountered an internal issue while trying to process your request. "
            "Please try again in a moment, or rephrase your query. "
            "I'm continuously learning to provide better assistance."
        )
        update_session_history(user_id, session_id, query, error_message)
        return error_message

# Example usage (for testing agent logic directly)
if __name__ == "__main__":
    from firestore_utils import initialize_firestore
    initialize_firestore()

    print("--- Bengaluru AI Agent Test ---")

    test_user_id = "test_user_123"
    test_session_id = "test_session_abc"

    # Example 1: NandiHill travel
    print("\nUser Query 1: I am looking to travel NandiHill this weekend.")
    response1 = run_agent_query(test_user_id, test_session_id, "I am looking to travel NandiHill this weekend.")
    print(f"AI: {response1}")

    # Example 2: Follow-up question in the same session
    print("\nUser Query 2 (follow-up): What about the weather there?")
    response2 = run_agent_query(test_user_id, test_session_id, "What about the weather there?")
    print(f"AI: {response2}")

    # Example 3: New session for the same user
    test_session_id_new = "test_session_def"
    print(f"\n--- Starting New Session: {test_session_id_new} ---")
    print("User Query 3: Is there any activity along my route?")
    response3 = run_agent_query(test_user_id, test_session_id_new, "Is there any activity along my route?")
    print(f"AI: {response3}")

    # Example 4: Query about an uncertain topic (should apologize)
    print("\nUser Query 4: Tell me about secret alien bases in Bengaluru.")
    response4 = run_agent_query(test_user_id, test_session_id_new, "Tell me about secret alien bases in Bengaluru.")
    print(f"AI: {response4}")