from .state import AgentState
from .utils import llm, send_email, get_prompt
from db import update_policyholder
from langchain_core.messages import HumanMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def email_agent_node(state: AgentState):
    """Generate and send a renewal email asynchronously."""
    data = state.get("policyholder_data")
    logger.info(f"Drafting renewal email for {data['name']} ({data['id']})")
    
    prompt_template = get_prompt("email_agent.txt")
    prompt = prompt_template.format(
        name=data['name'], 
        policy_id=data['policy_id'], 
        renewal_date=data['renewal_date']
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # Send real email
    subject = f"Insurance Renewal Notice - Policy {data['policy_id']}"
    email_body = response.content
    
    try:
        success = send_email(data['email'], subject, email_body)
    except Exception:
        success = False
        logger.error(f"Critical failure sending email to {data['email']} after retries.")
    
    await update_policyholder(data['id'], {"renewal_status": "EMAIL_SENT", "history": data['history'] + ["EMAIL_SENT"]})
    return {"messages": [response], "status": "WAITING_FOR_CRITIC"}
