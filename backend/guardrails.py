
import re
import unicodedata
from fastapi import HTTPException

# ─── Constants ───────────────────────────────────────────────────────────────

MAX_QUESTION_LENGTH = 500
MAX_FILENAME_LENGTH = 100
MAX_PDF_SIZE_MB = 20
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024
MAX_CONTEXT_CHUNK_LENGTH = 2000
ARXIV_ID_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")

# ─── Prompt Injection Patterns ────────────────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|system|earlier)\s+(instructions?|prompts?|context|rules?)",
    r"(forget|disregard|override|bypass)\s+(your\s+)?(instructions?|training|rules?|guidelines?|system\s+prompt)",
    r"you\s+are\s+now\s+(a\s+)?(different|new|another|evil|unrestricted|free)",
    r"act\s+as\s+(if\s+you\s+(are|were)\s+)?(a\s+)?(different|unrestricted|jailbroken|evil|DAN)",
    r"(pretend|imagine|roleplay|simulate)\s+(you\s+(are|were|have\s+no)|there\s+(are|is)\s+no)",
    r"(do\s+)?anything\s+now",
    r"jailbreak",
    r"developer\s+mode",
    r"(system|assistant|user)\s*:\s*\[",
    r"<\s*(system|assistant|user|instruction)\s*>",
    r"---+\s*(end|stop|ignore)",
    r"###\s*(new\s+)?(instruction|prompt|system|task)",
    r"\[\s*(system|inst|instruction)\s*\]",
    r"<<\s*(sys|system|SYS)\s*>>",
    r"(reveal|print|show|output|repeat|tell\s+me|display)\s+(your\s+)?(system\s+prompt|instructions?|context|api\s+key|secret)",
    r"what\s+(are|is)\s+your\s+(system\s+prompt|instructions?|context\s+window|rules?)",
    r"translate\s+(the\s+)?(above|following|this)\s+(to|into)\s+\w+\s+and\s+execute",
    r"execute\s+(the\s+)?(following|above|this)\s+(as\s+)?(code|command|instruction)",
]

COMPILED_INJECTION = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]

INVISIBLE_CHAR_PATTERN = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u206a-\u206f\ufeff\u00ad]"
)

# ─── PII Patterns ─────────────────────────────────────────────────────────────

PII_PATTERNS: dict[str, re.Pattern] = {
    "email":       re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"),
    "phone_us":    re.compile(r"\b(\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"),
    "ssn":         re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ip_address":  re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


# ─── Validators ──────────────────────────────────────────────────────────────

def validate_question(question: str) -> str:
    """
    Validate and sanitize a user question.
    Returns (sanitized_question, rejection_reason | None).
    Raises HTTPException 400 on violation — also returns rejection metadata
    for the caller to pass to audit_logger.
    """
    if not question or not question.strip():
        _reject("empty_question", "Question cannot be empty.", "")

    question = INVISIBLE_CHAR_PATTERN.sub("", question)
    question = "".join(
        c for c in question
        if unicodedata.category(c) not in ("Cc", "Cf") or c in ("\n", "\t")
    )
    question = question.strip()

    if len(question) > MAX_QUESTION_LENGTH:
        _reject(
            "question_too_long",
            f"Question too long. Max {MAX_QUESTION_LENGTH} characters allowed.",
            question[:80],
        )

    if not re.search(r"[a-zA-Z0-9]", question):
        _reject("no_alphanumeric", "Question must contain readable text.", question[:80])

    for pattern in COMPILED_INJECTION:
        if pattern.search(question):
            _reject(
                "injection_pattern",
                "Question contains disallowed content. Please ask a question about the research paper.",
                question[:80],
            )

    return question


def validate_arxiv_id(arxiv_id: str) -> str:
    """Validate ArXiv ID format and sanitize URL inputs."""
    arxiv_id = INVISIBLE_CHAR_PATTERN.sub("", arxiv_id.strip())

    if not arxiv_id:
        _reject("arxiv_empty", "ArXiv ID cannot be empty.", "")

    if len(arxiv_id) > 200:
        _reject("arxiv_too_long", "ArXiv input too long.", arxiv_id[:80])

    if "arxiv.org" in arxiv_id:
        if not re.match(r"^https?://(www\.)?arxiv\.org/", arxiv_id):
            _reject("arxiv_bad_domain", "Only arxiv.org URLs are accepted.", arxiv_id[:80])
        arxiv_id = arxiv_id.rstrip("/").split("/")[-1].replace(".pdf", "")

    if not ARXIV_ID_PATTERN.match(arxiv_id):
        _reject(
            "arxiv_bad_format",
            f"Invalid ArXiv ID format: '{arxiv_id}'. Expected YYMM.NNNNN (e.g. 2305.10403).",
            arxiv_id[:80],
        )

    return arxiv_id


def validate_pdf_upload(file_bytes: bytes, filename: str) -> str:
    """
    Validate uploaded PDF: size, magic bytes, filename safety.
    Returns sanitized filename.
    """
    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        _reject("pdf_too_large", f"PDF too large. Max size is {MAX_PDF_SIZE_MB} MB.", filename[:80])

    if len(file_bytes) < 4:
        _reject("pdf_too_small", "File too small to be a valid PDF.", filename[:80])

    if file_bytes[:4] != b"%PDF":
        _reject("pdf_bad_magic", "File does not appear to be a valid PDF.", filename[:80])

    safe_name = re.sub(r"[^\w\-. ]", "_", filename)[:MAX_FILENAME_LENGTH]
    if not safe_name.endswith(".pdf"):
        safe_name += ".pdf"

    return safe_name


def sanitize_context(context: str) -> str:
    """
    Sanitize retrieved context chunks before injecting into the LLM prompt.
    Defends against indirect prompt injection embedded in PDF content.
    """
    context = INVISIBLE_CHAR_PATTERN.sub("", context)

    if len(context) > MAX_CONTEXT_CHUNK_LENGTH * 10:
        context = context[:MAX_CONTEXT_CHUNK_LENGTH * 10] + "\n[...truncated]"

    def neutralize_line(line: str) -> str:
        for pattern in COMPILED_INJECTION:
            if pattern.search(line):
                return f"[DOCUMENT TEXT]: {line}"
        return line

    return "\n".join(neutralize_line(l) for l in context.splitlines())


def validate_response(answer: str) -> str:
    """Post-generation output check — catches model manipulation leaking through."""
    suspicious = [
        r"(system\s*prompt|my\s+instructions?\s+(are|say)|i\s+am\s+instructed\s+to)",
        r"(ignore\s+(all|previous)\s+instructions?)",
    ]
    for p in suspicious:
        if re.search(p, answer, re.IGNORECASE):
            return "I'm unable to provide a response to that query. Please ask a question about the research paper."
    return answer.strip()


def detect_pii(text: str) -> list[str]:
    """
    Scan extracted document text for PII patterns.
    Returns a list of PII type names found (e.g. ["email", "phone_us"]).
    Does NOT return the actual values — only the type labels for audit logging.
    """
    found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            found.append(pii_type)
    return found


# ─── Internal ────────────────────────────────────────────────────────────────

def _reject(check: str, message: str, snippet: str) -> None:
    """
    Raise HTTPException and surface structured rejection metadata.
    The caller (main.py route) catches the extra attributes for audit logging.
    """
    exc = HTTPException(status_code=400, detail=message)
    exc.guardrail_check = check      
    exc.guardrail_snippet = snippet  
    raise exc
