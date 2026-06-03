import streamlit as st
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Research Paper Summarizer",
    page_icon="🔬",
    layout="centered",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif;
    background-color: #F7F4EF !important;
    color: #1C1C1C;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2.5rem !important; max-width: 760px !important; }

/* ── Header ── */
.header-wrap {
    text-align: center;
    padding: 2.8rem 0 0.6rem;
    border-bottom: 1.5px solid #D9D3C9;
    margin-bottom: 2rem;
}
.header-eyebrow {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #9C7C5A;
    margin-bottom: 0.6rem;
}
.header-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.9rem;
    font-weight: 400;
    color: #1C1C1C;
    line-height: 1.15;
    margin: 0 0 0.7rem;
    letter-spacing: -0.02em;
}
.header-title em {
    font-style: italic;
    color: #9C7C5A;
}
.header-sub {
    font-size: 0.93rem;
    color: #6B6560;
    font-weight: 300;
    max-width: 480px;
    margin: 0 auto 1.8rem;
    line-height: 1.6;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #9C7C5A;
    margin-bottom: 0.8rem;
    margin-top: 0.2rem;
}

/* ── Tab overrides ── */
div[data-testid="stTabs"] {
    border-bottom: 1.5px solid #D9D3C9;
    margin-bottom: 1.4rem;
}
div[data-testid="stTabs"] button {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: #9A9390 !important;
    background: transparent !important;
    border: none !important;
    padding: 0.5rem 1.1rem 0.6rem !important;
    border-radius: 0 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1C1C1C !important;
    border-bottom: 2px solid #9C7C5A !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #FFFFFF;
    border: 1.5px dashed #C8BFB5;
    border-radius: 10px;
    padding: 1rem;
}
[data-testid="stFileUploader"]:hover {
    border-color: #9C7C5A;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #FFFFFF !important;
    border: 1.5px solid #D9D3C9 !important;
    border-radius: 8px !important;
    color: #1C1C1C !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 0.9rem !important;
    box-shadow: none !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #9C7C5A !important;
    box-shadow: 0 0 0 3px rgba(156,124,90,0.1) !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #B0AAA5 !important;
}

/* ── Labels ── */
.stTextInput label, .stTextArea label, .stFileUploader label {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #5A5450 !important;
    letter-spacing: 0.01em !important;
    margin-bottom: 0.3rem !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #1C1C1C !important;
    color: #F7F4EF !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.55rem 1.6rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.03em !important;
    transition: background 0.2s, transform 0.1s !important;
    cursor: pointer !important;
}
.stButton > button:hover:not(:disabled) {
    background: #3A3633 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    background: #C8BFB5 !important;
    color: #F7F4EF !important;
    cursor: not-allowed !important;
}
.stButton > button:focus { box-shadow: 0 0 0 3px rgba(156,124,90,0.25) !important; }

/* ── Paper meta card ── */
.meta-card {
    background: #FFFFFF;
    border: 1px solid #E0D9D1;
    border-left: 3.5px solid #9C7C5A;
    border-radius: 10px;
    padding: 1.1rem 1.3rem 1rem;
    margin: 1.2rem 0 0.4rem;
}
.meta-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    color: #1C1C1C;
    line-height: 1.4;
    margin-bottom: 0.45rem;
}
.meta-byline {
    font-size: 0.78rem;
    color: #7A7370;
    font-weight: 400;
    display: flex;
    gap: 1.2rem;
    flex-wrap: wrap;
}
.meta-byline span { display: flex; align-items: center; gap: 0.3rem; }

/* ── Divider ── */
hr, .stDivider {
    border: none !important;
    border-top: 1px solid #D9D3C9 !important;
    margin: 1.8rem 0 !important;
}

/* ── Answer box ── */
.answer-wrap {
    margin-top: 1.4rem;
}
.answer-header {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #9C7C5A;
    margin-bottom: 0.7rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.answer-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #D9D3C9;
}
.answer-box {
    background: #FFFFFF;
    border: 1px solid #E0D9D1;
    border-radius: 10px;
    padding: 1.6rem 1.8rem;
    line-height: 1.85;
    color: #2A2622;
    font-size: 0.95rem;
    font-weight: 300;
    box-shadow: 0 2px 12px rgba(28,28,28,0.05);
}
.answer-box p { margin: 0 0 1rem 0; }
.answer-box p:last-child { margin-bottom: 0; }

/* ── Alert/success/error tweaks ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}

/* ── Reset caption ── */
.stCaption { color: #A09A95 !important; font-size: 0.78rem !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-top-color: #9C7C5A !important; }
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-wrap">
    <div class="header-eyebrow">AI-Powered Research Tool</div>
    <h1 class="header-title">Research Paper<br><em>Summarizer</em></h1>
    <p class="header-sub">Load any academic paper via PDF or ArXiv — ask a question, get a clear and concise summary in seconds.</p>
</div>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "paper_meta" not in st.session_state:
    st.session_state.paper_meta = None
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

# ─── Load Paper ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">01 — Load a Paper</div>', unsafe_allow_html=True)

tab_pdf, tab_arxiv = st.tabs(["  Upload PDF  ", "  ArXiv ID / URL  "])

with tab_pdf:
    uploaded_file = st.file_uploader("Select a PDF file (max 20 MB)", type=["pdf"], label_visibility="visible")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Process PDF", key="btn_pdf", disabled=uploaded_file is None):
            with st.spinner("Extracting and indexing..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/ingest/pdf",
                        files={"file": (uploaded_file.name, uploaded_file.read(), "application/pdf")},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.paper_meta = data
                    st.session_state.last_answer = None
                    st.success("Paper ready — ask your question below.")
                except Exception as e:
                    st.error(f"{e}")

with tab_arxiv:
    arxiv_input = st.text_input(
        "ArXiv ID or full URL",
        placeholder="e.g. 2305.10403 or https://arxiv.org/abs/2305.10403",
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Fetch Paper", key="btn_arxiv", disabled=not arxiv_input.strip()):
            with st.spinner("Fetching from ArXiv..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/ingest/arxiv",
                        json={"arxiv_id": arxiv_input.strip()},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.paper_meta = data
                    st.session_state.last_answer = None
                    st.success("Paper ready — ask your question below.")
                except Exception as e:
                    st.error(f"{e}")

# ─── Paper Metadata ───────────────────────────────────────────────────────────
if st.session_state.paper_meta:
    meta = st.session_state.paper_meta
    authors_str = ", ".join(meta["authors"]) if isinstance(meta["authors"], list) else meta["authors"]
    st.markdown(f"""
    <div class="meta-card">
        <div class="meta-title">{meta['title']}</div>
        <div class="meta-byline">
            <span>✦ {authors_str}</span>
            <span>◦ {meta['published']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Q&A ──────────────────────────────────────────────────────────────────────
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown('<div class="section-label">02 — Ask a Question</div>', unsafe_allow_html=True)

question = st.text_area(
    "What would you like to know about this paper?",
    placeholder="e.g. What problem does this paper solve? What methods were used? What are the key findings?",
    height=110,
    disabled=st.session_state.session_id is None,
    label_visibility="visible",
)

if st.session_state.session_id is None:
    st.caption("Load a paper above to unlock this section.")

col1, col2 = st.columns([1, 3])
with col1:
    ask_btn = st.button(
        "Summarize",
        disabled=st.session_state.session_id is None or not (question or "").strip(),
        key="btn_ask",
    )

if ask_btn and question.strip():
    with st.spinner("Generating summary..."):
        try:
            resp = httpx.post(
                f"{BACKEND_URL}/query",
                json={"session_id": st.session_state.session_id, "question": question},
                timeout=60,
            )
            resp.raise_for_status()
            st.session_state.last_answer = resp.json()["answer"]
        except Exception as e:
            st.error(f"{e}")

if st.session_state.last_answer:
    paragraphs = "".join(
        f"<p>{p.strip()}</p>" for p in st.session_state.last_answer.split("\n") if p.strip()
    )
    st.markdown(f"""
    <div class="answer-wrap">
        <div class="answer-header">Summary</div>
        <div class="answer-box">{paragraphs}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── Reset ────────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown('<hr>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("↩ Load New Paper", key="btn_reset"):
            st.session_state.session_id = None
            st.session_state.paper_meta = None
            st.session_state.last_answer = None
            st.rerun()
