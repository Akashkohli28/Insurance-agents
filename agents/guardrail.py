from .state import AgentState
from .utils import llm, get_prompt
from langchain_core.messages import HumanMessage
from logging_config import get_logger

logger = get_logger(__name__)

async def guardrail_agent_node(state: AgentState):
    """Structured guardrail check asynchronously."""
    last_message = state["messages"][-1].content
    channel = state["communication_channel"]
    data = state["policyholder_data"]
    
    logger.info(f"Running compliance check for {channel} message to {data['id']}")
    
    prompt_template = get_prompt("guardrail_agent.txt")
    prompt = prompt_template.format(
        channel=channel,
        name=data['name'],
        policy_id=data['policy_id'],
        renewal_date=data['renewal_date'],
        message=last_message
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = response.content.strip()
    
    logger.info(f"Guardrail result for {data['id']}: {result}")
    
    if "GUARDRAIL_PASSED" in result:
        return {"guardrail_status": "APPROVED", "status": "FINALIZED"}
    else:
        return {"guardrail_status": result, "status": "REJECTED_BY_GUARDRAIL"}
