# main.py
from langgraph.graph import StateGraph, START, END
from agents import (
    AgentState, 
    data_retrieval_node, 
    strategy_node, 
    email_agent_node, 
    voice_agent_node, 
    whatsapp_agent_node, 
    guardrail_agent_node, 
    hitl_node
)
from logging_config import get_logger

logger = get_logger(__name__)

# Router for guardrail
def guardrail_router(state: AgentState):
    if state["guardrail_status"] == "APPROVED":
        return "end"
    else:
        return "hitl"

# Initialize the state graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("data_retrieval", data_retrieval_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("email", email_agent_node)
workflow.add_node("voice", voice_agent_node)
workflow.add_node("whatsapp", whatsapp_agent_node)
workflow.add_node("guardrail", guardrail_agent_node)
workflow.add_node("hitl", hitl_node)

# Add edges
workflow.add_edge(START, "data_retrieval")
workflow.add_edge("data_retrieval", "strategy")

# Conditional edges from strategy
workflow.add_conditional_edges(
    "strategy",
    lambda x: x["next_node"],
    {
        "email": "email",
        "whatsapp": "whatsapp",
        "voice": "voice",
        "hitl": "hitl"
    }
)

# Edges to guardrail (for asynchronous channels)
workflow.add_edge("email", "guardrail")
workflow.add_edge("whatsapp", "guardrail")

# Conditional edges from guardrail
workflow.add_conditional_edges(
    "guardrail",
    guardrail_router,
    {
        "end": END,
        "hitl": "hitl"
    }
)

# Final edges to end
workflow.add_edge("voice", END)
workflow.add_edge("hitl", END)

# Compile the graph
app = workflow.compile()

async def run_automation(ph_id: str):
    logger.info(f"--- STARTING ASYNC AUTOMATION FOR {ph_id} ---")
    initial_state = {
        "messages": [],
        "policyholder_id": ph_id,
        "policyholder_data": {},
        "next_node": "",
        "communication_channel": "",
        "status": "",
        "guardrail_status": ""
    }
    
    # Run the graph asynchronously
    async for output in app.astream(initial_state):
        if "__metadata__" in output:
            continue
        # Intermediate logging if needed
        pass
    logger.info(f"--- COMPLETED AUTOMATION FOR {ph_id} ---")
    
if __name__ == "__main__":
    # For local testing, we'd need a runner but we'll use API primarily
    import asyncio
    asyncio.run(run_automation("PH_EMAIL"))
