from typing import List,Dict,TypedDict,Optional,Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

from .models import SourceItem



class AgentState(TypedDict):
    original_query : Optional[str]
    message : Annotated[list[AnyMessage],add_messages]
    retrived_chunks : List[SourceItem]
    metadata: List[Dict]
