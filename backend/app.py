from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests, re
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import time

app = FastAPI()

visited = set()
results = []

def is_bad_alt(alt, src):
    if not alt or alt.strip() == "":
        return True
    if len(alt.split()) < 2:
        return True
    filename = src.split("/")[-1].split(".")[0]
    if alt.lower() in filename.lower():
        return True
    if re.match(r"^[a-zA-Z0-9_-]+$", alt):
        return True
    return False

def rule_based_suggestion(alt, src):
    filename = src.split("/")[-1].split(".")[0]
    name_clean = re.sub(r"[_-]", " ", filename)
    if not alt:
        return f"Image showing {name_clean}"
    if "logo" in filename.lower():
        return "Company logo"
    if "banner" in filename.lower():
        return "Promotional banner"
    if len(alt.split()) <= 2:
        return f"More descriptive text needed for '{alt}'"
    return "Looks okay"

def count_images(url, base_domain, visited_local, depth=0, max_depth=2):
    if depth > max_depth or url in visited_local:
        return 0
    visited_local.add(url)
    count = 0
    try:
        resp = requests.get(url, timeout=5)
        if "text/html" not in resp.headers.get("Content-Type", ""):
            return 0
        soup = BeautifulSoup(resp.text, "html.parser")
        count += len(soup.find_all("img"))
        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"])
            if urlparse(next_url).netloc == base_domain:
                count += count_images(next_url, base_domain, visited_local, depth+1, max_depth)
    except:
        pass
    return count



def crawl(url, base_domain):
    if url in visited:
        return
    visited.add(url)

    try:
        resp = requests.get(url, timeout=5)
        if "text/html" not in resp.headers.get("Content-Type", ""):
            return
        soup = BeautifulSoup(resp.text, "html.parser")

        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if not src:
                continue
            img_url = urljoin(url, src)
            bad = is_bad_alt(alt, src)
            suggestion = rule_based_suggestion(alt, src)

            results.append({
                "page_url": url,
                "image_url": img_url,
                "alt_text": alt,
                "status": "Needs Fix" if bad else "OK",
                "suggestion": suggestion
            })

        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"])
            if urlparse(next_url).netloc == base_domain:
                crawl(next_url, base_domain)

    except Exception as e:
        print(f"Error visiting {url}: {e}")

@app.get("/")
def home():
    return {"message": "✅ Alt Text Checker API is running! Visit /docs to test or connect your frontend."}



# --- Add CORS to allow frontend requests ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/check")
def check_site(url: str = Query(..., description="Website URL to scan for images")):
    """
    Crawls the given website (only internal pages) and checks image alt texts.
    Returns a JSON list with image URL, current alt text, status, and suggestion.
    """
    global visited, results
    visited, results = set(), []

    base_domain = urlparse(url).netloc
    crawl(url, base_domain)

    return {"url": url, "results": results}

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
import json
import time

# --- Existing imports & code (crawl, is_bad_alt, etc.) remain the same ---

@app.get("/stream")
def stream_site(url: str = Query(...)):
    def event_generator():
        visited_local = set()
        results_local = []

        base_domain = urlparse(url).netloc

        # --- Helper: count images per page only ---
        def count_images_page(u):
            try:
                r = requests.get(u, timeout=5)
                if "text/html" not in r.headers.get("Content-Type", ""):
                    return 0
                soup = BeautifulSoup(r.text, "html.parser")
                return len(soup.find_all("img"))
            except:
                return 0

        # --- Crawl and stream ---
        def crawl_stream(u, depth=0, max_depth=2):
            if depth > max_depth or u in visited_local:
                return
            visited_local.add(u)

            try:
                r = requests.get(u, timeout=5)
                if "text/html" not in r.headers.get("Content-Type", ""):
                    return
                soup = BeautifulSoup(r.text, "html.parser")

                # Count images on this page for progress
                page_imgs = soup.find_all("img")
                total_page = len(page_imgs)
                for img in page_imgs:
                    src = img.get("src", "")
                    alt = img.get("alt", "")
                    if not src:
                        continue
                    img_url = urljoin(u, src)
                    bad = is_bad_alt(alt, src)
                    suggestion = rule_based_suggestion(alt, src) if bad else "Looks good"

                    result = {
                        "page_url": u,
                        "image_url": img_url,
                        "alt_text": alt,
                        "status": "Needs Fix" if bad else "OK",
                        "suggestion": suggestion
                    }
                    results_local.append(result)
                    yield f"data: {json.dumps({'type':'result','result':result})}\n\n"

                # Crawl internal links
                for link in soup.find_all("a", href=True):
                    next_url = urljoin(u, link["href"])
                    if urlparse(next_url).netloc == base_domain:
                        yield from crawl_stream(next_url, depth+1, max_depth)

            except Exception as e:
                print(f"Error visiting {u}: {e}")

        # --- Start crawl ---
        yield f"data: {json.dumps({'type':'total', 'total': 0})}\n\n"  # optional: front-end can handle unknown total
        yield from crawl_stream(url)
        yield "data: DONE\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
