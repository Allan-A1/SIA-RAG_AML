# backend/agents/graph/state.py
from typing import TypedDict, List, Optional
from backend.ingestion.schemas import DocumentChunk
from backend.web.schemas import WebChunk


class GraphState(TypedDict):
    # Input
    query: str

    # Router outputs
    intent: Optional[str]
    retrieval: Optional[str]
    granularity: Optional[str]
    sources: Optional[List[str]]  # ["pdf"], ["web"], ["pdf", "web"]

    # Retrieval outputs
    pdf_chunks: List[DocumentChunk]
    web_chunks: List[WebChunk]
    
    # Tracking flags
    zoomed_out: Optional[bool]  # Track if we zoomed out during retrieval

    # Final output
    final_answer: Optional[str]

