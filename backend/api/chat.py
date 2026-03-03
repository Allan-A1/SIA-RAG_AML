from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Literal
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singleton — avoids stale graph if modules reload
_graph = None

def _get_graph():
    global _graph
    if _graph is None:
        from backend.agents.graph.graph import build_graph
        logger.info("[chat] Building LangGraph pipeline...")
        _graph = build_graph()
        logger.info("[chat] Graph ready.")
    return _graph


class ChatRequest(BaseModel):
    query: str
    search_mode: Optional[Literal["auto", "pdf", "web", "both"]] = "auto"


class ChatResponse(BaseModel):
    answer: str


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Map search_mode to sources
    sources = None
    if request.search_mode == "pdf":
        sources = ["pdf"]
    elif request.search_mode == "web":
        sources = ["web"]
    elif request.search_mode == "both":
        sources = ["pdf", "web"]

    initial_state = {
        "query":        request.query,
        "intent":       None,
        "retrieval":    None,
        "granularity":  None,
        "sources":      sources,
        "pdf_chunks":   [],
        "web_chunks":   [],
        "final_answer": None,
    }

    try:
        result = _get_graph().invoke(initial_state)
        return ChatResponse(answer=result["final_answer"])

    except Exception as exc:
        # Return a structured JSON error instead of an unhandled 500
        # so the browser receives a proper CORS response (not a bare error)
        logger.error(f"[chat] Error during graph invoke: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "answer": f"❌ Server error: {exc}"},
        )
