import os
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate # Ensure this is imported
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage

from tools import all_tools
from config import Config

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
    history = get_session_history(user_id, session_id) # Ensure correct session context
    history.append(HumanMessage(content=human_message))
    history.append(AIMessage(content=ai_message))
    logger.debug(f"Session history updated for {user_id}/{session_id}: {history}")

def create_conversational_agent():
    # print("DEBUG all_tools:", all_tools)
    # print("DEBUG all_tools types:", [type(t) for t in all_tools])
    """
    Initializes and returns the Langchain conversational agent.
    """
    if not Config.GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not set. Cannot initialize LLM for agent.")
        raise ValueError("GOOGLE_API_KEY environment variable is required.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    # --- UPDATED PROMPT TEMPLATE ---
    prompt_template = PromptTemplate.from_template("""
    You are BengaluruPulse, an intelligent conversational AI agent providing real-time,
    actionable insights about Bengaluru's data noise (traffic, civic, events, weather).
    Your goal is to help citizens navigate the city with foresight.

    **Instructions:**
    1. **Be Cool, Professional, Sympathetic, and Understanding:** Tailor your tone to be helpful and empathetic.
    2. **Be Concise:** Provide information directly and avoid lengthy explanations.
    3. **Utilize Tools:** You have access to the following tools:
    {tools}

    Use them to gather information.
       - Prioritize `get_synthesized_events` for broader stories.
       - Use `get_analyzed_events` for specific, granular data if synthesis doesn't yield enough.
       - Use `get_user_profile` to understand user preferences and tailor responses.
       - Use `get_traffic`, `get_events`, `get_weather` for real-time external data.
    4. **Information Certainty:** Only provide information if you are certain and have retrieved it from your tools.
    5. **Handle Uncertainty:** If you cannot find reliable information using your tools, apologize and explain that
       you cannot provide a reliable answer at this moment. Do not make up information.
    6. **Suggest Alternatives/Next Steps:** Based on the context, offer relevant suggestions or ask clarifying questions
       to gather more information (e.g., "Can you specify the area?", "What dates are you interested in?").
    7. **Session Management:** Remember the conversation context from `chat_history`.
    8. **User Profile Integration:** If `get_user_profile` provides preferences (interests, home/work locations),
       use them to personalize responses or make relevant suggestions. For example, if a user's home/work locations
       are found, use them as default locations for queries like "Is there any activity along my route?".

    **Example User Queries and Expected Agent Behavior:**
    - "I am looking to travel NandiHill this weekend."
      - Check `get_synthesized_events` for NandiHill/weekend.
      - Check `get_analyzed_events` for NandiHill/weekend.
      - Use `get_traffic`, `get_weather`, `get_events` for NandiHill/weekend.
      - Respond based on findings, offer suggestions (e.g., "Consider leaving early due to weekend traffic," "There's a flower show happening").
    - "Is there any activity along my route?"
      - First, use `get_user_profile` to find `homeLocation` and `workLocation`.
      - If locations are found, query events/traffic/etc. along that route.
      - If not found, ask for the route details: "Could you please tell me your starting and destination points?"

    **The only tools you may use are: {tool_names}**

    **Current Conversation:**
    {chat_history}

    **User Query:** {input}
    {agent_scratchpad}
    """)
    # --- END UPDATED PROMPT TEMPLATE ---
    

    agent = create_react_agent(llm, all_tools, prompt_template)
    print(f"DEBUG:Prompt Template: {prompt_template}")
    agent_executor = AgentExecutor(
        agent=agent,
        tools=all_tools,
        verbose=True, # Set to False in production
        handle_parsing_errors=True, # Robust error handling for tool outputs
        max_iterations=10, # Limit agent's thinking steps
        # return_intermediate_steps=True # For debugging to see tool calls
    )
    return agent_executor

def run_agent_query(user_id: str, session_id: str, query: str) -> str:
     """
     Runs a query through the conversational agent.
     Manages session history.
     """
     agent_executor = create_conversational_agent()
     chat_history = get_session_history(user_id, session_id)
     print(f"DEBUG: Running agent query for user {user_id}, session {session_id} with query: {query}")
     print(f"DEBUG: Chat history for user {user_id}, session {session_id}: {chat_history}")

     try:
         response = agent_executor.invoke({
             "input": query,
             "chat_history": chat_history
         })
        #  response = agent_executor.invoke({
        #      "input": query
        #  })
         ai_response = response.get("output", "I'm sorry, I couldn't process that request.")
         update_session_history(user_id, session_id, query, ai_response)
         return ai_response
     except Exception as e:
         logger.error(f"Error running agent query for user {user_id}, session {session_id}: {e}", exc_info=True)
         # Attempt to provide a helpful, apologetic message even on agent internal errors
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
     initialize_firestore() # Ensure Firestore is initialized for tool access

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
     # For this to work well, ensure a user profile for 'test_user_123' exists in Firestore
     # with homeLocation and workLocation.
     # If not, the agent will ask for clarification as per the prompt.
     response3 = run_agent_query(test_user_id, test_session_id_new, "Is there any activity along my route?")
     print(f"AI: {response3}")

     # Example 4: Query about an uncertain topic (should apologize)
     print("\nUser Query 4: Tell me about secret alien bases in Bengaluru.")
     response4 = run_agent_query(test_user_id, test_session_id_new, "Tell me about secret alien bases in Bengaluru.")
     print(f"AI: {response4}")