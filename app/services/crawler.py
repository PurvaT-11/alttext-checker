# app/services/crawler.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests, re
from app.utils.logger import setup_logger

logger = setup_logger()

visited_global = set()

# ----------------- Helper functions -----------------
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

# ----------------- Full crawl -----------------
def crawl_site(url, max_depth=2):
    results = []
    visited = set()

    def crawl(u, depth):
        if depth > max_depth or u in visited:
            return
        visited.add(u)
        try:
            r = requests.get(u, timeout=5)
            if "text/html" not in r.headers.get("Content-Type", ""):
                return
            soup = BeautifulSoup(r.text, "html.parser")
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "")
                if not src:
                    continue
                img_url = urljoin(u, src)
                bad = is_bad_alt(alt, src)
                suggestion = rule_based_suggestion(alt, src)
                results.append({
                    "page_url": u,
                    "image_url": img_url,
                    "alt_text": alt,
                    "status": "Needs Fix" if bad else "OK",
                    "suggestion": suggestion
                })
            for link in soup.find_all("a", href=True):
                next_url = urljoin(u, link["href"])
                if urlparse(next_url).netloc == urlparse(url).netloc:
                    crawl(next_url, depth+1)
        except Exception as e:
            logger.error(f"Error visiting {u}: {e}")

    crawl(url, 0)
    return results

# ----------------- Streaming crawl -----------------
def crawl_site_stream(url, max_depth=2):
    visited = set()

    def crawl(u, depth):
        if depth > max_depth or u in visited:
            return
        visited.add(u)
        try:
            r = requests.get(u, timeout=5)
            if "text/html" not in r.headers.get("Content-Type", ""):
                return
            soup = BeautifulSoup(r.text, "html.parser")
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "")
                if not src:
                    continue
                img_url = urljoin(u, src)
                bad = is_bad_alt(alt, src)
                suggestion = rule_based_suggestion(alt, src)
                yield {
                    "page_url": u,
                    "image_url": img_url,
                    "alt_text": alt,
                    "status": "Needs Fix" if bad else "OK",
                    "suggestion": suggestion
                }
            for link in soup.find_all("a", href=True):
                next_url = urljoin(u, link["href"])
                if urlparse(next_url).netloc == urlparse(url).netloc:
                    yield from crawl(next_url, depth+1)
        except Exception as e:
            logger.error(f"Error visiting {u}: {e}")

    yield from crawl(url, 0)
