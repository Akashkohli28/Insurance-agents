from .state import AgentState
from db import update_policyholder
from langchain_core.messages import AIMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def hitl_node(state: AgentState):
    """Route to human staff for manual intervention asynchronously."""
    data = state.get("policyholder_data")
    logger.warning(f"Escalating policyholder {data['id']} ({data['name']}) to human staff.")
    
    await update_policyholder(data['id'], {"renewal_status": "ESCALATED", "history": data['history'] + ["ESCALATED_TO_HUMAN"]})
    return {"messages": [AIMessage(content=f"Handed over to human staff for {data['name']}.")], "status": "ESCALATED"}
