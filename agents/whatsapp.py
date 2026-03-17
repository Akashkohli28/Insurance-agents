from .state import AgentState
from .utils import llm, send_whatsapp, get_prompt
from db import update_policyholder
from langchain_core.messages import HumanMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def whatsapp_agent_node(state: AgentState):
    """Generate and send a WhatsApp message asynchronously."""
    data = state.get("policyholder_data")
    logger.info(f"Drafting WhatsApp notice for {data['name']} ({data['id']})")
    
    prompt_template = get_prompt("whatsapp_agent.txt")
    prompt = prompt_template.format(
        name=data['name'], 
        policy_id=data['policy_id'], 
        renewal_date=data['renewal_date']
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # Send real WhatsApp
    whatsapp_body = response.content
    try:
        success = send_whatsapp(data['phone'], whatsapp_body)
    except Exception:
        success = False
        logger.error(f"Critical failure sending WhatsApp to {data['phone']} after retries.")
    
    await update_policyholder(data['id'], {"renewal_status": "WHATSAPP_SENT", "history": data['history'] + ["WHATSAPP_SENT"]})
    return {"messages": [response], "status": "WAITING_FOR_CRITIC"}
