'''from pydantic import BaseModel
from typing import List, Dict, Any

class DocState(BaseModel):
    folder_path: str = ""
    documents: List = []
    summary: str = ""
    entities: List[Dict] = []
    visuals: Dict = {}
    user_query: str = ""
    rag_response: str = ""
    use_rag: bool = False
    index: Any = None
    ocr_text: str = ""#
    image_previews: list = []#
    chart_candidates: list = []#
'''
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Annotated
from langgraph.graph.message import add_messages

class DocState(BaseModel):
    messages: Annotated[list, add_messages] = []
    filename: str = ""
    folder_path: str = ""
    documents: List = []
    summary: str = ""
    entities: List[Dict] = []
    visuals: Dict = {}
    user_query: str = ""
    rag_response: str = ""
    use_rag: bool = False
    index: Any = None
    extracted_images: List[str] = Field(default_factory=list)
    image_descriptions: List[str] = Field(default_factory=list)
    extracted_tables: List[Dict] = Field(default_factory=list)
    image_insights: List[str] = Field(default_factory=list)
    # Analytics fields
    sql: str = ""
    data_head: str = ""
    error: str = ""
    iteration: int = 0
    viz_requested: bool = False
    schema_context: str = ""

