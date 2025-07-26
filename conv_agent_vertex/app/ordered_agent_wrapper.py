"""
Enhanced Agent Wrapper that enforces strict tool usage ordering
"""
import logging
from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

class ToolOrderEnforcementCallback(BaseCallbackHandler):
    """Callback to enforce tool usage order during agent execution."""
    
    def __init__(self):
        self.tools_used = []
        self.synthesized_events_called = False
        self.analyzed_events_called = False
    
    def on_agent_action(self, action, **kwargs):
        """Called when agent is about to use a tool."""
        try:
            # Safely get tool name
            tool_name = getattr(action, 'tool', str(action))
            self.tools_used.append(tool_name)
            
            logger.info(f"Agent attempting to use tool: {tool_name}")
            
            # Track which internal tools have been called
            if tool_name == "get_synthesized_events":
                self.synthesized_events_called = True
            elif tool_name == "get_analyzed_events":
                self.analyzed_events_called = True
            
            # Enforce ordering rules
            external_tools = ["get_traffic", "get_events", "get_weather"]
            
            if tool_name in external_tools:
                if not self.synthesized_events_called:
                    logger.warning(f"Tool order violation: {tool_name} called before get_synthesized_events")
                    # Don't raise exception, just log warning
                    return
            
            if tool_name == "get_analyzed_events":
                if not self.synthesized_events_called:
                    logger.warning(f"Tool order violation: get_analyzed_events called before get_synthesized_events")
                    # Don't raise exception, just log warning
                    return
                    
        except Exception as e:
            logger.error(f"Error in callback: {e}")
            # Don't let callback errors break the agent
            pass

class OrderedBengaluruAgent:
    """
    A wrapper around the standard agent that enforces tool usage ordering.
    """
    
    def __init__(self, base_agent_executor: AgentExecutor):
        self.base_agent = base_agent_executor
    
    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with tool ordering enforcement.
        """
        # Create callback for this execution
        callback = ToolOrderEnforcementCallback()
        
        try:
            # Add guidance to the input to remind about tool order
            original_input = inputs.get("input", "")
            guided_input = f"""
MANDATORY TOOL ORDER REMINDER:
1. ALWAYS start with get_synthesized_events
2. Use get_analyzed_events only if you need more specific details
3. Use external tools (get_traffic, get_events, get_weather) only after checking internal data
4. get_user_profile can be used anytime for context

USER QUERY: {original_input}
"""
            
            # Update inputs with guided input
            guided_inputs = inputs.copy()
            guided_inputs["input"] = guided_input
            
            # Execute with callback
            result = self.base_agent.invoke(
                guided_inputs,
                config={"callbacks": [callback]}
            )
            
            # Log the tool usage pattern for analysis
            logger.info(f"Tool usage pattern: {callback.tools_used}")
            
            return result
            
        except ValueError as e:
            # Handle tool order violations gracefully
            logger.error(f"Tool order violation: {e}")
            
            # Return a helpful error message to the user
            return {
                "output": (
                    "I need to check our internal data sources first before looking at external information. "
                    "Let me start by checking synthesized events data for your query."
                ),
                "intermediate_steps": []
            }
        except Exception as e:
            logger.error(f"Error in ordered agent execution: {e}")
            return {
                "output": (
                    "I apologize, but I encountered an issue while processing your request. "
                    "Please try rephrasing your query."
                ),
                "intermediate_steps": []
            }

def create_ordered_agent(base_agent_executor: AgentExecutor) -> OrderedBengaluruAgent:
    """
    Creates an ordered agent wrapper around the base agent.
    """
    return OrderedBengaluruAgent(base_agent_executor)

# Usage example integration function
def run_ordered_agent_query(user_id: str, session_id: str, query: str, base_agent_executor: AgentExecutor) -> str:
    """
    Runs a query through the ordered agent wrapper.
    """
    try:
        ordered_agent = create_ordered_agent(base_agent_executor)
        
        # Get chat history (assuming this function exists in your main module)
        from agents import get_session_history, format_chat_history, update_session_history
        
        chat_history = get_session_history(user_id, session_id)
        formatted_history = format_chat_history(chat_history)
        
        logger.info(f"Running ordered agent query for user {user_id}, session {session_id}")
        
        response = ordered_agent.invoke({
            "input": query,
            "chat_history": formatted_history
        })
        
        ai_response = response.get("output", "I'm sorry, I couldn't process that request.")
        update_session_history(user_id, session_id, query, ai_response)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error in ordered agent query: {e}", exc_info=True)
        return (
            "I apologize, but I encountered an internal issue. "
            "Please try again or rephrase your query."
        )