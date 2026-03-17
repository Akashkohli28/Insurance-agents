from .state import AgentState
from .utils import llm, send_voice_call, get_prompt
from db import update_policyholder
from langchain_core.messages import HumanMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def voice_agent_node(state: AgentState):
    """Simulate and initiate a voice call asynchronously."""
    data = state.get("policyholder_data")
    logger.info(f"Initiating voice call process for {data['name']} ({data['id']})")
    
    prompt_template = get_prompt("voice_agent.txt")
    prompt = prompt_template.format(
        name=data['name'], 
        policy_id=data['policy_id'], 
        renewal_date=data['renewal_date']
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # Send real voice call
    try:
        success = send_voice_call(data['phone'])
    except Exception:
        success = False
        logger.error(f"Critical failure initiating voice call to {data['phone']} after retries.")
    
    await update_policyholder(data['id'], {"renewal_status": "VOICE_CALL_MADE", "history": data['history'] + ["VOICE_CALL_MADE"]})
    return {"messages": [response], "status": "COMPLETED"}
