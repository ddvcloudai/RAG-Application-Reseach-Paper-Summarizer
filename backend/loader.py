import arxiv
import fitz  
import requests
import tempfile
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.schema import Document
from guardrails import detect_pii

MAX_PAGES = 100  


def load_from_pdf_bytes(file_bytes: bytes, filename: str) -> tuple[list[Document], dict]:
    """
    Load text from PDF bytes.
    Returns (docs, info) where info contains page_count and pii_types found.
    Filename is expected to already be sanitized by guardrails.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        pages = []
        full_text_sample = "" 

        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            text = page.get_text()
            if text.strip():
                pages.append(Document(
                    page_content=text,
                    metadata={"source": filename, "page": i + 1}
                ))
                if len(full_text_sample) < 5000:
                    full_text_sample += text

        doc.close()

        
        pii_found = detect_pii(full_text_sample)

        info = {
            "page_count": len(pages),
            "pii_types": pii_found,
        }
        return pages, info

    finally:
        os.unlink(tmp_path)


def load_from_arxiv(arxiv_id: str) -> tuple[list[Document], dict]:
    """
    Fetch paper from ArXiv by ID. arxiv_id must already be validated and cleaned
    (YYMM.NNNNN format) by guardrails.validate_arxiv_id().
    """
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(search.results())
    if not results:
        raise ValueError(f"No paper found for ArXiv ID: {arxiv_id}")

    paper = results[0]
    pdf_url = paper.pdf_url

    if "arxiv.org" not in pdf_url:
        raise ValueError("Unexpected PDF URL from ArXiv response.")

    response = requests.get(pdf_url, timeout=30)
    response.raise_for_status()

    docs, info = load_from_pdf_bytes(response.content, f"{arxiv_id}.pdf")

    metadata = {
        "title": paper.title,
        "authors": [a.name for a in paper.authors],
        "published": str(paper.published.date()),
        "abstract": paper.summary,
        "arxiv_id": arxiv_id,
        "page_count": info["page_count"],
        "pii_types": info["pii_types"],
    }
    return docs, metadata
