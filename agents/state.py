from typing import Annotated, List, Union, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    policyholder_id: str
    policyholder_data: dict
    next_node: str
    communication_channel: str
    status: str
    guardrail_status: str # APPROVED, REJECTED, or feedback
