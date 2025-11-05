from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import alt_checker  # adjust if your folder is different


app = FastAPI(
    title="Alt Text Checker API",
    version="2.0",
    description="API to analyze image alt texts across web pages"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alt_checker.router)

@app.get("/")
def home():
    return {"message": "✅ Alt Text Checker API is running! Visit /docs to test or connect your frontend."}
