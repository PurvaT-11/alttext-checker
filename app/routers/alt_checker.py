# app/routers/alt_checker.py
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.services.crawler import crawl_site, crawl_site_stream
from app.utils.logger import setup_logger
import json

router = APIRouter()
logger = setup_logger()

# ----------------- Normal /check endpoint -----------------
@router.get(
    "/check",
    summary="Check all images on a webpage for missing or poor alt text",
    response_description="Returns a list of images with their alt text status"
)
def check_site(
    url: str = Query(..., description="Website URL to scan (must start with http or https)")
):
    try:
        results = crawl_site(url)
        return {"url": url, "results": results}
    except ValueError as e:
        logger.warning(f"Invalid URL: {url} - {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to check {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ----------------- Streaming /stream endpoint -----------------
@router.get(
    "/stream",
    summary="Stream alt text check results as they are processed",
    response_description="Streams individual image results"
)
def stream_site(url: str = Query(..., description="Website URL to scan (must start with http or https)")):
    try:
        def event_generator():
            # crawl_site_stream yields each image result
            for result in crawl_site_stream(url):
                yield f"data: {json.dumps({'type':'result','result':result})}\n\n"
            yield "data: DONE\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except ValueError as e:
        logger.warning(f"Invalid URL for streaming: {url} - {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Streaming failed for {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
