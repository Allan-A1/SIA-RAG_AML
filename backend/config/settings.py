import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal


class Settings(BaseSettings):
    """Centralized configuration for SIA-RAG system."""
    
    # ============================================
    # LLM Provider Selection
    # ============================================
    llm_provider: Literal["openai", "ollama", "gemini", "groq", "huggingface"] = Field(default="ollama", env="LLM_PROVIDER")
    
    # ============================================
    # OpenAI Configuration
    # ============================================
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # ============================================
    # Ollama Configuration (FREE, LOCAL)
    # ============================================
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = Field(default="gemma2:2b", env="OLLAMA_MODEL")
    
    # ============================================
    # Google Gemini Configuration (FREE TIER)
    # ============================================
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model: str = "gemini-1.5-flash"
    
    # ============================================
    # Groq Configuration (FREE TIER, FAST)
    # ============================================
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    groq_model: str = "llama-3.1-8b-instant"

    # ============================================
    # HuggingFace Inference API
    # ============================================
    huggingface_api_key: Optional[str] = Field(default=None, env="HUGGINGFACE_API_KEY")
    huggingface_model: str = Field(default="Qwen/Qwen3-30B-A3B-Instruct-2507", env="HUGGINGFACE_MODEL")
    huggingface_base_url: str = "https://api-inference.huggingface.co/v1/"
    
    # ============================================
    # Model Configuration (applies to active provider)
    # ============================================
    router_model: str = "gpt-4o-mini"  # Used if provider is OpenAI
    verifier_model: str = "gpt-4o"     # Used if provider is OpenAI
    
    # ============================================
    # Embedding Configuration
    # ============================================
    embedding_provider: Literal["openai", "local"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"  # Local model (sentence-transformers)
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_device: str = Field(default="auto", env="EMBEDDING_DEVICE")
    # "auto"  → detected at runtime (cuda > mps > cpu)
    # "cuda"  → NVIDIA GPU
    # "mps"   → Apple Silicon
    # "cpu"   → Force CPU
    
    # ============================================
    # ChromaDB Configuration
    # ============================================
    chroma_persist_directory: str = "./chroma_db"
    collection_micro: str = "documents_sentences"
    collection_macro: str = "documents_sections"
    
    # ============================================
    # Retrieval Configuration
    # ============================================
    default_k: int = 10            # candidates fetched per retriever

    # ── Cross-encoder reranker ──
    reranker_enabled: bool = Field(default=True,  env="RERANKER_ENABLED")
    reranker_model:   str  = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", env="RERANKER_MODEL")
    reranker_top_k:   int  = Field(default=8,     env="RERANKER_TOP_K")
    # Top-k after reranking — this is what the verifier receives

    # ── Verifier context ──
    max_context_chunks: int = Field(default=10, env="MAX_CONTEXT_CHUNKS")
    # Hard cap on chunks sent to LLM — shorter prompt → faster response
    
    # ============================================
    # Search Configuration
    # ============================================
    search_api_key: Optional[str] = os.getenv("SEARCH_API_KEY")
    search_endpoint: Optional[str] = os.getenv("SEARCH_ENDPOINT")
    tavily_api_key: Optional[str] = os.getenv("TAVILY_API_KEY")
    web_search_max_results: int = 5
    
    # ============================================
    # System Configuration
    # ============================================
    temperature: float = 0.3  # Increased for more varied, query-specific responses
    max_retries: int = 2
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_llm_client():
    """
    Get the appropriate LLM adapter based on settings.
    Returns an adapter with a consistent OpenAI-compatible interface.
    """
    from backend.config.llm_adapter import (
        OpenAIAdapter,
        GeminiAdapter,
        OllamaAdapter,
        GroqAdapter,
        HuggingFaceAdapter,
    )
    
    if settings.llm_provider == "openai":
        from openai import OpenAI
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        client = OpenAI(api_key=settings.openai_api_key)
        return OpenAIAdapter(client)
    
    elif settings.llm_provider == "ollama":
        from openai import OpenAI
        # Ollama has OpenAI-compatible API
        client = OpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama"  # Ollama doesn't need a real key
        )
        return OllamaAdapter(client)
    
    elif settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
        return GeminiAdapter(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model
        )
    
    elif settings.llm_provider == "groq":
        from openai import OpenAI
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when using Groq provider")
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key
        )
        return GroqAdapter(client)

    elif settings.llm_provider == "huggingface":
        if not settings.huggingface_api_key:
            raise ValueError("HUGGINGFACE_API_KEY is required when using HuggingFace provider")
        return HuggingFaceAdapter(
            api_key=settings.huggingface_api_key,
            model=settings.huggingface_model,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_model_name(role: str = "verifier"):
    """Get the appropriate model name based on provider and role."""
    if settings.llm_provider == "openai":
        return settings.verifier_model if role == "verifier" else settings.router_model
    elif settings.llm_provider == "ollama":
        return settings.ollama_model
    elif settings.llm_provider == "gemini":
        return settings.gemini_model
    elif settings.llm_provider == "groq":
        return settings.groq_model
    elif settings.llm_provider == "huggingface":
        return settings.huggingface_model
    else:
        return settings.ollama_model  # Default fallback


def validate_config():
    """Validate that required configuration is present."""
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI")
    
    if settings.llm_provider == "gemini" and not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required when using Gemini")
    
    if settings.llm_provider == "groq" and not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required when using Groq")
    
    return True
