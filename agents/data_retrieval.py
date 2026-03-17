from .state import AgentState
from db import get_policyholder
from langchain_core.messages import AIMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def data_retrieval_node(state: AgentState):
    """Retrieve policyholder data from the mock database asynchronously."""
    ph_id = state.get("policyholder_id")
    logger.info(f"Retrieving data for policyholder: {ph_id}")
    data = await get_policyholder(ph_id)
    if not data:
        logger.error(f"Policyholder {ph_id} not found in database.")
        return {"messages": [AIMessage(content=f"Error: Policyholder {ph_id} not found.")], "status": "FAILED"}
    return {"policyholder_data": data, "status": "IN_PROGRESS"}
