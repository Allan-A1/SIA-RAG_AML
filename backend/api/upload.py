from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.ingestion.ingest_pipeline import ingest_pdf
from backend.ingestion.pdf_parser import get_converter
import asyncio
import os
import tempfile
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)

# Thread-pool shared across all upload requests so embeddings and Docling
# run in worker threads rather than blocking the asyncio event loop.
_executor = None  # lazily created (default ThreadPoolExecutor)


@router.on_event("startup")
async def warmup():
    """
    Pre-load the Docling DocumentConverter in a thread on server startup
    so the FIRST real upload is fast (no 30-second model-load delay).
    """
    logger.info("Warming up DocumentConverter in background thread…")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, get_converter)
    logger.info("DocumentConverter warm-up complete.")


@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and ingest a PDF file with dual-granularity indexing.
    Ingestion runs in a thread pool so the server stays responsive.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        temp_path = tmp.name

    try:
        t0 = time.perf_counter()
        loop = asyncio.get_event_loop()

        # Run blocking ingestion in a worker thread — keeps event loop free
        doc_id = await loop.run_in_executor(
            _executor,
            lambda: ingest_pdf(temp_path, doc_name=file.filename)
        )
        elapsed = round(time.perf_counter() - t0, 1)
        logger.info(f"Ingested '{file.filename}' in {elapsed}s  doc_id={doc_id}")

        return {
            "filename":  file.filename,
            "doc_id":    doc_id,
            "status":    "success",
            "elapsed_s": elapsed,
            "message":   f"PDF ingested into both micro and macro indexes in {elapsed}s",
        }

    except Exception as e:
        logger.exception(f"Ingestion failed for '{file.filename}'")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
