import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from rag import load_from_pdf_bytes, load_from_arxiv, build_vectorstore, build_rag_chain
from rag.chain import invoke_with_usage
from guardrails import validate_question, validate_arxiv_id, validate_pdf_upload
from audit_logger import log_ingest, log_query, log_guardrail_rejection, log_pii_flag, log_session_expired

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

# ─── Governance Config ────────────────────────────────────────────────────────
SESSION_TTL_SECONDS = 2 * 60 * 60   
MAX_QUERIES_PER_SESSION = 50         

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

sessions: dict = {}


# ─── Session Helpers ──────────────────────────────────────────────────────────

def _get_live_session(session_id: str) -> dict:
    """
    Return session if it exists and has not expired.
    Evicts and audit-logs expired sessions.
    Raises 404 if missing or 410 if expired.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please ingest a paper first.")

    age = time.time() - session["created_at"]
    if age > SESSION_TTL_SECONDS:
        log_session_expired(session_id, age)
        del sessions[session_id]
        raise HTTPException(status_code=410, detail="Session expired. Please re-ingest the paper.")

    return session


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ArxivRequest(BaseModel):
    arxiv_id: str

    @field_validator("arxiv_id")
    @classmethod
    def sanitize_arxiv_id(cls, v):
        if not v or not v.strip():
            raise ValueError("arxiv_id cannot be empty.")
        if len(v) > 200:
            raise ValueError("arxiv_id too long.")
        return v.strip()


class QueryRequest(BaseModel):
    session_id: str
    question: str

    @field_validator("session_id")
    @classmethod
    def sanitize_session_id(cls, v):
        import re
        if not re.match(r"^[\w\-\.]{1,150}$", v):
            raise ValueError("Invalid session_id format.")
        return v

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("question cannot be empty.")
        return v


class IngestResponse(BaseModel):
    session_id: str
    title: str
    authors: list[str]
    published: str
    message: str


class QueryResponse(BaseModel):
    answer: str
    session_id: str


# ─── Global exception handler for guardrail rejections ───────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    check = getattr(exc, "guardrail_check", None)
    if check:
        log_guardrail_rejection(
            check=check,
            reason=exc.detail,
            input_snippet=getattr(exc, "guardrail_snippet", ""),
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "active_sessions": len(sessions)}


@app.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """Upload a PDF and build the RAG index."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    
    safe_filename = validate_pdf_upload(file_bytes, file.filename)

    docs, info = load_from_pdf_bytes(file_bytes, safe_filename)
    if not docs:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    vectorstore = build_vectorstore(docs, OPENAI_API_KEY)
    chain = build_rag_chain(vectorstore, OPENAI_API_KEY)

    session_id = safe_filename.replace(" ", "_").replace(".pdf", "")
    sessions[session_id] = {
        "chain": chain,
        "title": safe_filename,
        "authors": ["N/A"],
        "published": "N/A",
        "created_at": time.time(),
        "query_count": 0,
    }

   
    log_ingest("pdf", session_id, safe_filename, info["page_count"])
    if info["pii_types"]:
        log_pii_flag(session_id, safe_filename, info["pii_types"])

    return IngestResponse(
        session_id=session_id,
        title=safe_filename,
        authors=["N/A"],
        published="N/A",
        message="PDF ingested successfully. You can now ask questions.",
    )


@app.post("/ingest/arxiv", response_model=IngestResponse)
async def ingest_arxiv(req: ArxivRequest):
    """Fetch an ArXiv paper by ID/URL and build the RAG index."""
    clean_id = validate_arxiv_id(req.arxiv_id)

    try:
        docs, meta = load_from_arxiv(clean_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    vectorstore = build_vectorstore(docs, OPENAI_API_KEY)
    chain = build_rag_chain(vectorstore, OPENAI_API_KEY)

    session_id = meta["arxiv_id"]
    sessions[session_id] = {
        "chain": chain,
        "title": meta["title"],
        "authors": meta["authors"],
        "published": meta["published"],
        "created_at": time.time(),
        "query_count": 0,
    }

    
    log_ingest("arxiv", session_id, meta["title"], meta["page_count"])
    if meta.get("pii_types"):
        log_pii_flag(session_id, meta["title"], meta["pii_types"])

    return IngestResponse(
        session_id=session_id,
        title=meta["title"],
        authors=meta["authors"],
        published=meta["published"],
        message="ArXiv paper ingested successfully. You can now ask questions.",
    )


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a question against an ingested paper."""
    
    clean_question = validate_question(req.question)

   
    session = _get_live_session(req.session_id)

    
    if session["query_count"] >= MAX_QUERIES_PER_SESSION:
        raise HTTPException(
            status_code=429,
            detail=f"Query limit of {MAX_QUERIES_PER_SESSION} reached for this session."
        )

    try:
        answer, token_usage = invoke_with_usage(session["chain"], clean_question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Governance: increment counter + audit log query with token usage
    session["query_count"] += 1
    log_query(req.session_id, clean_question, len(answer), token_usage)

    return QueryResponse(answer=answer, session_id=req.session_id)
