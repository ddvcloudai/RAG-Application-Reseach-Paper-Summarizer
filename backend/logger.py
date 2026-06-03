import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

# ─── Setup ────────────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "audit.log")

_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=7)
_handler.setFormatter(logging.Formatter("%(message)s"))  

_logger = logging.getLogger("audit")
_logger.setLevel(logging.INFO)
_logger.addHandler(_handler)
_logger.propagate = False  


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash(value: str) -> str:
    """SHA-256 hash of a string — used for question fingerprinting without storing raw text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]  # first 16 chars, readable


def _emit(event_type: str, payload: dict) -> None:
    entry = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    _logger.info(json.dumps(entry))


# ─── Public API ──────────────────────────────────────────────────────────────

def log_ingest(source: str, session_id: str, title: str, page_count: int) -> None:
    """Log a successful paper ingestion."""
    _emit("INGEST", {
        "source": source,           
        "session_id": session_id,
        "title": title,
        "page_count": page_count,
    })


def log_query(session_id: str, question: str, answer_length: int, token_usage: dict) -> None:
    """Log a query — stores question hash, not raw text."""
    _emit("QUERY", {
        "session_id": session_id,
        "question_hash": _hash(question),   
        "question_length": len(question),
        "answer_length_chars": answer_length,
        "tokens_input": token_usage.get("input_tokens", 0),
        "tokens_output": token_usage.get("output_tokens", 0),
        "tokens_total": token_usage.get("total_tokens", 0),
    })


def log_guardrail_rejection(check: str, reason: str, input_snippet: str = "") -> None:
    """
    Log a guardrail block event with the specific check that fired.
    input_snippet is truncated to 80 chars max — enough to debug, not enough to be sensitive.
    """
    _emit("GUARDRAIL_REJECTION", {
        "check": check,                           
        "reason": reason,
        "input_snippet": input_snippet[:80] if input_snippet else "",
    })


def log_pii_flag(session_id: str, filename: str, pii_types: list[str]) -> None:
    """Log when PII is detected in an ingested document."""
    _emit("PII_FLAG", {
        "session_id": session_id,
        "filename": filename,
        "pii_types_found": pii_types,          
    })


def log_session_expired(session_id: str, age_seconds: float) -> None:
    """Log when a session is evicted due to TTL expiry."""
    _emit("SESSION_EXPIRED", {
        "session_id": session_id,
        "age_seconds": round(age_seconds, 1),
    })
