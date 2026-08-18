"""
ActiveReaderPresi
Assistive SQ3R + SPIDER Annotation Studio
Presidency University – Postgraduate Research Training

Core principle: The student performs every intellectual act.
The application only provides structure, storage, and visibility.

Pedagogical sources:
- Diana Ridley (2012), The Literature Review, Chapter 4
- SPIDER framework (Sample, Phenomenon of Interest, Design, Evaluation, Research type)
"""

import streamlit as st
import json
import io
from datetime import datetime

# Optional parsers
try:
    import fitz  # PyMuPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    HAS_EPUB = True
except ImportError:
    HAS_EPUB = False

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

STAGES = ["Survey", "Question", "Read + Annotate", "Recall", "Review", "Write Review"]
SPIDER_KEYS = ["S", "P", "D", "E", "R"]
SPIDER_LABELS = {
    "S": "Sample",
    "P": "Phenomenon of Interest",
    "D": "Design",
    "E": "Evaluation",
    "R": "Research type",
}

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="ActiveReaderPresi",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
def init_state():
    defaults = {
        "mode": "student",
        "article_text": "",
        "article_title": "Untitled",
        "current_stage": "Survey",
        "survey_gist": "",
        "questions": ["", "", "", ""],
        "annotations": [],
        "recall": {k: "" for k in SPIDER_KEYS},
        "review_checks": {k: "" for k in SPIDER_KEYS},
        "final_review": "",
        "ai_flags": {stage: {"used": False, "note": ""} for stage in STAGES},
        "feedback": [],
        "completed_stages": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def mark_complete(stage_name: str):
    cs = st.session_state.get("completed_stages", [])
    if not isinstance(cs, list):
        cs = list(cs)
    if stage_name not in cs:
        cs.append(stage_name)
    st.session_state.completed_stages = cs


def show_progress():
    current = st.session_state.current_stage
    try:
        idx = STAGES.index(current)
    except ValueError:
        idx = 0
    st.progress((idx + 1) / len(STAGES), text=f"Stage {idx + 1} of {len(STAGES)}: {current}")


# ------------------------------------------------------------
# Text extraction
# ------------------------------------------------------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not HAS_PDF:
        return "[PDF support not available – install pymupdf]"
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    if not HAS_DOCX:
        return "[DOCX support not available – install python-docx]"
    doc = Document(io.BytesIO(file_bytes))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_epub(file_bytes: bytes) -> str:
    if not HAS_EPUB:
        return "[EPUB support not available – install ebooklib beautifulsoup4]"
    book = epub.read_epub(io.BytesIO(file_bytes))
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:
            soup = BeautifulSoup(item.get_content(), "lxml")
            texts.append(soup.get_text(separator="\n", strip=True))
    return "\n\n".join(texts)


def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if len(data) > MAX_FILE_SIZE_BYTES:
        st.error(f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.")
        return ""

    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    elif name.endswith(".docx"):
        return extract_text_from_docx(data)
    elif name.endswith(".epub"):
        return extract_text_from_epub(data)
    elif name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    else:
        st.warning("Unsupported format. Please upload PDF, DOCX, EPUB or TXT.")
        return ""


# ------------------------------------------------------------
# AI Usage Flag
# ------------------------------------------------------------
def render_ai_flag(stage: str):
    st.markdown("---")
    st.markdown(f"**AI Usage Flag — {stage}** (required)")
    used = st.radio(
        "Did you use AI in this stage?",
        ["No AI used", "AI used"],
        key=f"ai_radio_{stage}",
        horizontal=True,
        label_visibility="collapsed",
    )
    note = ""
    if used == "AI used":
        note = st.text_area(
            "Briefly describe how AI was used",
            key=f"ai_note_{stage}",
            height=70,
            placeholder="e.g. Checked a definition / Asked for grammar check of my own paragraph",
        )
    st.session_state.ai_flags[stage] = {
        "used": used == "AI used",
        "note": note if used == "AI used" else "",
    }


# ------------------------------------------------------------
# Sidebar (revised – more reliable on Streamlit Cloud)
# ------------------------------------------------------------
with st.sidebar:
    st.title("ActiveReaderPresi")
    st.caption("SQ3R + SPIDER · Assistive only")
    st.markdown(
        '<p style="font-size:0.72rem; color:#7A7A7A; line-height:1.35;">'
        "Based on Diana Ridley (2012), Ch. 4<br>SPIDER framework"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Stable mode selector
    mode_options = ["Student", "Supervisor"]
    current_mode = st.session_state.get("mode", "student").capitalize()
    if current_mode not in mode_options:
        current_mode = "Student"
    selected_mode = st.radio(
        "Mode",
        mode_options,
        index=mode_options.index(current_mode),
        key="mode_selector",
    )
    st.session_state.mode = selected_mode.lower()

    st.markdown("---")
    st.markdown("**Stages**")

    # Stage navigation – no explicit st.rerun() for reliability on Cloud
    for s in STAGES:
        is_done = s in st.session_state.get("completed_stages", [])
        label = f"✓ {s}" if is_done else s

        if s == st.session_state.get("current_stage"):
            st.markdown(f"**→ {label}**")
        else:
            if st.button(label, key=f"nav_{s}", use_container_width=True):
                st.session_state.current_stage = s

    st.markdown("---")

    if st.button("Reset all work", use_container_width=True):
        keep_mode = st.session_state.get("mode", "student")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.mode = keep_mode
        st.session_state.current_stage = "Survey"
        st.rerun()

    if st.button("Export all work (JSON)", use_container_width=True):
        export = {
            "title": st.session_state.get("article_title", "Untitled"),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "survey_gist": st.session_state.get("survey_gist", ""),
            "questions": st.session_state.get("questions", []),
            "annotations": st.session_state.get("annotations", []),
            "recall": st.session_state.get("recall", {}),
            "review_checks": st.session_state.get("review_checks", {}),
            "final_review": st.session_state.get("final_review", ""),
            "ai_flags": st.session_state.get("ai_flags", {}),
            "feedback": st.session_state.get("feedback", []),
        }
        st.download_button(
            "Download JSON",
            data=json.dumps(export, indent=2, ensure_ascii=False),
            file_name="ActiveReaderPresi_export.json",
            mime="application/json",
            use_container_width=True,
        )


# ------------------------------------------------------------
# Supervisor view
# ------------------------------------------------------------
if st.session_state.mode == "supervisor":
    st.header("Supervisor Module")
    st.info("Read-only view. You may add formative feedback. You cannot edit the student’s intellectual content.")

    with st.expander("1. Survey", expanded=True):
        st.write(st.session_state.survey_gist or "_Not completed_")
        flag = st.session_state.ai_flags.get("Survey", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    with st.expander("2. Question"):
        for i, q in enumerate(st.session_state.questions, 1):
            if q.strip():
                st.markdown(f"{i}. {q}")
        flag = st.session_state.ai_flags.get("Question", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    with st.expander("3. Read + Annotate"):
        st.write(f"{len(st.session_state.annotations)} annotation(s)")
        for ann in st.session_state.annotations:
            st.markdown(
                f"- **[{ann.get('color', '')} · {ann.get('spider', '')}]** "
                f"{ann.get('comment') or ann.get('text', '')[:80]}"
            )
        flag = st.session_state.ai_flags.get("Read + Annotate", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    with st.expander("4. Recall (SPIDER)"):
        for k in SPIDER_KEYS:
            st.markdown(f"**{k} – {SPIDER_LABELS[k]}**  \n{st.session_state.recall.get(k) or '_empty_'}")
        flag = st.session_state.ai_flags.get("Recall", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    with st.expander("5. Review Decisions"):
        for k in SPIDER_KEYS:
            st.write(f"{k}: {st.session_state.review_checks.get(k) or '—'}")
        flag = st.session_state.ai_flags.get("Review", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    with st.expander("6. Final Review"):
        st.write(st.session_state.final_review or "_Not written_")
        flag = st.session_state.ai_flags.get("Write Review", {})
        st.caption(f"AI Flag: {'Yes — ' + flag.get('note', '') if flag.get('used') else 'No AI used'}")

    st.markdown("---")
    st.subheader("Add Feedback")
    fb = st.text_area("Formative comment", height=100)
    if st.button("Save feedback"):
        if fb.strip():
            st.session_state.feedback.append({
                "ts": datetime.utcnow().isoformat() + "Z",
                "text": fb.strip(),
            })
            st.success("Feedback saved.")
            st.rerun()

    if st.session_state.feedback:
        st.markdown("**Previous feedback**")
        for f in st.session_state.feedback:
            st.markdown(f"- `{f['ts']}` — {f['text']}")

    st.stop()


# ------------------------------------------------------------
# Student – Upload
# ------------------------------------------------------------
if not st.session_state.article_text:
    st.header("ActiveReaderPresi")
    st.markdown("**Assistive SQ3R + SPIDER Annotation Studio**")
    st.caption("Core intellectual work remains the student’s. Maximum file size: 25 MB.")
    st.markdown(
        """
        <div style="font-size:0.85rem; color:#7A7A7A; margin-top:0.4rem;">
        Pedagogical sources: <strong>Diana Ridley (2012), <em>The Literature Review</em>, Chapter 4</strong>
        &nbsp;·&nbsp; <strong>SPIDER framework</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Quick start – how this app works", expanded=True):
        st.markdown("""
1. **Upload** an article (PDF / DOCX / EPUB / TXT) or paste text.
2. Work through six stages: **Survey → Question → Read + Annotate → Recall → Review → Write Review**.
3. In **Read + Annotate** use the three colours recommended by Ridley to separate the author’s words from your own thinking.
4. In **Recall** the original text is hidden – write from memory under the five SPIDER headings.
5. Declare **AI usage** honestly at every stage.
6. Your supervisor can view all stages and add feedback.
7. Export your complete work as JSON when finished.

You can return to any stage at any time from the sidebar.
        """)

    uploaded = st.file_uploader(
        "Upload article or book chapter",
        type=["pdf", "docx", "epub", "txt"],
        help=f"Maximum size {MAX_FILE_SIZE_MB} MB",
    )
    paste = st.text_area("Or paste text here", height=200)

    if uploaded is not None:
        with st.spinner("Extracting text…"):
            text = extract_text(uploaded)
            if text.strip():
                st.session_state.article_text = text
                st.session_state.article_title = uploaded.name
                st.success(f"Loaded: {uploaded.name} ({len(text):,} characters)")
                st.rerun()

    if paste.strip() and st.button("Use pasted text"):
        st.session_state.article_text = paste.strip()
        st.session_state.article_title = "Pasted text"
        st.rerun()

    st.stop()


# ------------------------------------------------------------
# Student stages
# ------------------------------------------------------------
stage = st.session_state.current_stage
show_progress()
st.header(stage)

# ----- SURVEY -----
if stage == "Survey":
    st.markdown("""
    **Survey** (Diana Ridley, Chapter 4)  
    Skim the **entire** article in the left panel. Write your gist in the right panel at the same time.
    """)

    with st.expander("How to Survey (Ridley)", expanded=False):
        st.markdown("""
        - Look at the title and any abstract.
        - Scan all headings and sub-headings.
        - Read the opening paragraphs and the conclusion.
        - Notice the overall organisation.
        - Do **not** yet take detailed notes or annotate.
        - Write a short gist that captures what the article is about.
        """)

    # ---------- Parallel layout ----------
    left, right = st.columns([3, 2])

    with left:
        st.markdown("##### Article — skim here")
        # Scrollable HTML container is more reliable than disabled text_area for long documents
        import html as _html
        safe_text = _html.escape(st.session_state.article_text)
        st.markdown(
            f"""
            <div style="
                height: 520px;
                overflow-y: auto;
                border: 1px solid #D9D5CC;
                border-radius: 6px;
                padding: 14px 16px;
                background: #FFFFFF;
                font-size: 0.92rem;
                line-height: 1.55;
                white-space: pre-wrap;
                font-family: Georgia, 'Times New Roman', serif;
            ">{safe_text}</div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"{len(st.session_state.article_text):,} characters · scroll to skim the whole text")

    with right:
        st.markdown("##### Your gist")
        gist_val = st.text_area(
            "Gist",
            value=st.session_state.survey_gist,
            height=420,
            placeholder="While skimming the article on the left, write what it is about in your own words…",
            label_visibility="collapsed",
            key="survey_gist_box",
        )
        st.session_state.survey_gist = gist_val
        st.caption("Write here while you skim. Both panels stay visible.")

    # AI flag + save
    render_ai_flag("Survey")

    if st.button("Save Survey & continue", type="primary", key="btn_save_survey"):
        if not st.session_state.survey_gist.strip():
            st.warning("Please write a gist before continuing.")
        else:
            mark_complete("Survey")
            st.session_state.current_stage = "Question"
            st.rerun()

# ----- QUESTION -----
elif stage == "Question":
    st.markdown("Formulate questions you want the article to answer. The questions must be your own.")
    new_questions = []
    for i in range(max(4, len(st.session_state.questions))):
        q = st.text_input(
            f"Question {i+1}",
            value=st.session_state.questions[i] if i < len(st.session_state.questions) else "",
            key=f"q_{i}",
        )
        new_questions.append(q)
    st.session_state.questions = new_questions

    if st.button("Add another question"):
        st.session_state.questions.append("")
        st.rerun()

    render_ai_flag("Question")
    if st.button("Save Questions & continue", type="primary"):
        mark_complete("Question")
        st.session_state.current_stage = "Read + Annotate"
        st.rerun()

# ----- READ + ANNOTATE -----
elif stage == "Read + Annotate":
    st.markdown("""
    **Active annotation** (following Diana Ridley, Chapter 4)  
    Separate the author’s words from your own thinking. Use colour to keep the distinction clear.
    """)
    st.markdown("""
    <div style="display:flex; gap:1.2rem; margin-bottom:0.8rem; font-size:0.88rem; flex-wrap:wrap;">
      <div><span style="background:#bbf7d0; padding:2px 8px; border-radius:4px;">Green – Source</span> Key claims, evidence, definitions</div>
      <div><span style="background:#bfdbfe; padding:2px 8px; border-radius:4px;">Blue – Structure</span> Organisation, section purpose, flow</div>
      <div><span style="background:#fecaca; padding:2px 8px; border-radius:4px;">Red – Response</span> Your critical comments, questions, links</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Source: Diana Ridley (2012), Chapter 4. SPIDER tags may be added to any annotation.")

    st.text_area("Article text", value=st.session_state.article_text, height=280, disabled=True)

    with st.expander("Add new annotation", expanded=True):
        sel_text = st.text_area("Paste or type the passage you are annotating", height=70)
        color = st.selectbox(
            "Colour category (Ridley distinction)",
            [
                "Green – Source (author’s claims / evidence)",
                "Blue – Structure (organisation / flow)",
                "Red – Response (your critical comment)",
            ],
        )
        spider = st.selectbox(
            "SPIDER tag (optional)",
            ["", "S – Sample", "P – Phenomenon", "D – Design", "E – Evaluation", "R – Research type"],
        )
        comment = st.text_area("Your comment / note", height=70)
        if st.button("Add annotation"):
            if sel_text.strip():
                if color.startswith("Green"):
                    ckey = "Source"
                elif color.startswith("Blue"):
                    ckey = "Structure"
                else:
                    ckey = "Response"
                st.session_state.annotations.append({
                    "text": sel_text.strip(),
                    "color": ckey,
                    "spider": spider[:1] if spider else "",
                    "comment": comment.strip(),
                    "ts": datetime.utcnow().isoformat() + "Z",
                })
                st.success("Annotation added.")
                st.rerun()

    st.markdown(f"**Current annotations ({len(st.session_state.annotations)})**")
    for i, ann in enumerate(st.session_state.annotations):
        icon = {"Source": "🟢", "Structure": "🔵", "Response": "🔴"}.get(ann.get("color", ""), "⚪")
        st.markdown(
            f"{i+1}. {icon} `{ann['color']}` `{ann.get('spider') or '—'}` — "
            f"{ann.get('comment') or ann['text'][:100]}"
        )
        if st.button(f"Delete #{i+1}", key=f"del_ann_{i}"):
            st.session_state.annotations.pop(i)
            st.rerun()

    render_ai_flag("Read + Annotate")
    if st.button("Save Annotations & continue", type="primary"):
        mark_complete("Read + Annotate")
        st.session_state.current_stage = "Recall"
        st.rerun()

# ----- RECALL -----
elif stage == "Recall":
    st.warning("Source text is hidden. Write from memory only under the five SPIDER headings.")
    with st.expander("How to use this stage (Ridley + SPIDER)"):
        st.markdown("""
- Close the original text in your mind.
- Write what you remember under each SPIDER heading.
- Do **not** look back at the article or your annotations yet.
- After you finish, move to Review to check accuracy.
- This stage trains active recall (Ridley, Chapter 4).
        """)
    for k in SPIDER_KEYS:
        st.session_state.recall[k] = st.text_area(
            f"{k} – {SPIDER_LABELS[k]}",
            value=st.session_state.recall.get(k, ""),
            height=90,
            key=f"recall_{k}",
        )
    render_ai_flag("Recall")
    if st.button("Save Recall & continue", type="primary"):
        mark_complete("Recall")
        st.session_state.current_stage = "Review"
        st.rerun()

# ----- REVIEW -----
elif stage == "Review":
    st.markdown("Compare your Recall notes with the original text. Mark each SPIDER element.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Your Recall**")
        for k in SPIDER_KEYS:
            st.markdown(f"**{k}**  \n{st.session_state.recall.get(k) or '_empty_'}")
    with col2:
        st.markdown("**Original (excerpt)**")
        st.text_area(
            "Source",
            value=st.session_state.article_text[:4000],
            height=380,
            disabled=True,
            label_visibility="collapsed",
        )

    st.markdown("**Verification decisions**")
    for k in SPIDER_KEYS:
        st.session_state.review_checks[k] = st.radio(
            f"{k} – {SPIDER_LABELS[k]}",
            ["", "Accurate", "Incomplete", "Needs revision"],
            key=f"check_{k}",
            horizontal=True,
        )

    render_ai_flag("Review")
    if st.button("Save Review & continue", type="primary"):
        mark_complete("Review")
        st.session_state.current_stage = "Write Review"
        st.rerun()

# ----- WRITE REVIEW -----
elif stage == "Write Review":
    st.markdown("Write the complete review using only your own previous work. The app supplies structure; you write the prose.")
    with st.expander("Your accumulated notes", expanded=False):
        st.markdown(f"**Gist**  \n{st.session_state.survey_gist or '—'}")
        st.markdown("**Questions**")
        for q in st.session_state.questions:
            if q.strip():
                st.markdown(f"- {q}")
        st.markdown("**SPIDER Recall**")
        for k in SPIDER_KEYS:
            st.markdown(f"- **{k}**: {st.session_state.recall.get(k) or '—'}")
        st.markdown(f"**Annotations**: {len(st.session_state.annotations)} item(s)")

    st.session_state.final_review = st.text_area(
        "Final review",
        value=st.session_state.final_review,
        height=380,
        placeholder="Write your complete review of the article here…",
    )
    render_ai_flag("Write Review")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save draft"):
            mark_complete("Write Review")
            st.success("Draft saved.")
    with col_b:
        if st.button("Mark complete", type="primary"):
            mark_complete("Write Review")
            st.success("Review marked complete. You may still return to any stage and iterate. Use the sidebar to Export.")
