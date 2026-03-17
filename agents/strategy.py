# Strategy is purely logic, so it doesn't strictly need to be async, 
# but making it async for consistency in the graph is fine.
from .state import AgentState
from logging_config import get_logger

logger = get_logger(__name__)

async def strategy_node(state: AgentState):
    """Decide the communication channel based on days remaining."""
    data = state.get("policyholder_data")
    days = data.get("days_remaining", 30)
    
    logger.info(f"Evaluating strategy for {data['id']}: {days} days remaining.")
    
    if days >= 30:
        channel = "EMAIL"
    elif days >= 15:
        channel = "WHATSAPP"
    elif days >= 3:
        channel = "VOICE"
    else:
        channel = "HITL"
        logger.info(f"Urgent case ({days} days) selected: HITL")
        return {"next_node": "hitl", "communication_channel": channel}
    
    logger.info(f"Selected channel for {data['id']}: {channel}")
    return {"next_node": channel.lower(), "communication_channel": channel}
