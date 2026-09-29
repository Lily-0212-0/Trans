"""AI 다국어 번역기 - Streamlit 앱.

실행: streamlit run app.py
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from translator import LANGUAGES, MAX_CHARS, TONES, TranslationError, get_model, translate

HISTORY_LIMIT = 10
HISTORY_FILE = Path(__file__).with_name("history.json")

# 국기 이모지는 Windows에서 "US" 같은 글자로 표시되므로 쓰지 않는다.
LANGUAGE_LABELS = {
    "en": ("English", "영어"),
    "ja": ("日本語", "일본어"),
    "vi": ("Tiếng Việt", "베트남어"),
}

CSS = """
<style>
.block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 760px; }

.hero { margin-bottom: 1.25rem; }
.hero h1 {
    font-size: 2rem; font-weight: 800; margin: 0; padding: 0;
    letter-spacing: -0.02em;
}
.hero p { margin: 0.35rem 0 0; color: var(--muted-text); font-size: 0.95rem; }
.hero .chips { margin-top: 0.75rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }
.hero .chip {
    font-size: 0.8rem; padding: 0.2rem 0.65rem; border-radius: 999px;
    background: var(--chip-bg); color: var(--chip-text); font-weight: 600;
}

.lang-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.lang-head .name { font-weight: 700; font-size: 1.02rem; }
.lang-head .ko { color: var(--muted-text); font-size: 0.85rem; }
.lang-head .code {
    margin-left: auto; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;
    padding: 0.1rem 0.5rem; border-radius: 6px; background: var(--chip-bg); color: var(--chip-text);
}

/* 결과 카드 안의 코드 블록을 일반 텍스트처럼 보이게 한다. */
.st-key-results [data-testid="stCode"] pre {
    font-family: inherit !important; font-size: 1rem; line-height: 1.6;
    white-space: pre-wrap !important; word-break: break-word;
}
.st-key-results [data-testid="stCode"] code { font-family: inherit !important; }

.section-label { font-weight: 700; font-size: 0.9rem; color: var(--muted-text); margin: 1.5rem 0 0.5rem; }

/* 앱 테마는 .streamlit/config.toml에서 light로 고정한다. */
:root { --muted-text: #6b7280; --chip-bg: #eef2ff; --chip-text: #4338ca; }
</style>
"""

def load_saved_history() -> list[dict]:
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))[:HISTORY_LIMIT]
    except (OSError, ValueError):
        return []


def save_history() -> None:
    try:
        HISTORY_FILE.write_text(json.dumps(state.history, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # 기록 저장 실패는 번역 자체에 영향을 주지 않는다.


st.set_page_config(page_title="AI 번역기", page_icon="🌐", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

state = st.session_state
state.setdefault("source", "")
state.setdefault("result", None)
state.setdefault("error", None)
if "history" not in state:
    state.history = load_saved_history()


def run_translation() -> None:
    text = state.source
    state.error = None
    if not text.strip():
        state.error = "번역할 내용을 입력하세요."
        return
    try:
        with st.spinner("번역 중..."):
            result = translate(text, state.get("tone", "기본"))
    except TranslationError as e:
        state.error = str(e)
        return

    state.result = result
    state.history.insert(0, {"time": datetime.now().strftime("%m/%d %H:%M"), "source": text.strip(), "result": result})
    del state.history[HISTORY_LIMIT:]
    save_history()


def clear() -> None:
    state.source = ""
    state.result = None
    state.error = None


def load_history(item: dict) -> None:
    state.source = item["source"]
    state.result = item["result"]
    state.error = None


def clear_history() -> None:
    state.history = []
    save_history()


# ---------- 사이드바: 설정 & 최근 기록 ----------
with st.sidebar:
    st.subheader("⚙️ 설정")
    st.radio("어조", list(TONES), key="tone", horizontal=True)
    st.caption(f"모델 · `{get_model()}`")

    st.divider()
    st.subheader("🕘 최근 번역")
    if not state.history:
        st.caption("아직 번역 기록이 없습니다.")
    for i, item in enumerate(state.history):
        preview = item["source"].replace("\n", " ")
        if len(preview) > 20:
            preview = preview[:20] + "…"
        st.button(f"{item['time']} · {preview}", key=f"history_{i}", on_click=load_history, args=(item,),
                  width="stretch")
    if state.history:
        st.button("기록 삭제", type="tertiary", on_click=clear_history)

# ---------- 헤더 ----------
st.markdown(
    """
    <div class="hero">
      <h1>🌐 AI 번역기</h1>
      <p>한 번 입력하면 세 언어로 동시에 번역합니다.</p>
      <div class="chips">
        <span class="chip">English</span><span class="chip">日本語</span><span class="chip">Tiếng Việt</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- 입력 ----------
with st.form("translate_form", border=True):
    st.text_area(
        "번역할 내용",
        key="source",
        height=160,
        placeholder="번역할 내용을 입력하세요...",
        label_visibility="collapsed",
    )
    # max_chars는 초과 분량을 붙여넣으면 안내 없이 무시하므로 쓰지 않고, 길이는 translate()에서 검사한다.
    st.form_submit_button("번역하기", type="primary", width="stretch", on_click=run_translation)

# 폼 안에 제출 버튼이 둘 이상이면 Ctrl + Enter가 "지우기"를 실행하므로 폼 밖에 둔다.
hint, clear_col = st.columns([4, 1], vertical_alignment="center")
hint.caption(f"⌨️ Ctrl + Enter로 바로 번역 · 최대 {MAX_CHARS:,}자")
clear_col.button("🧹 지우기", type="tertiary", width="stretch", on_click=clear)

if state.error:
    with st.container(border=True):
        st.error(state.error, icon="⚠️")
        if state.source.strip():
            st.button("🔄 다시 시도", on_click=run_translation)

# ---------- 결과 ----------
result = state.result
if result:
    with st.container(key="results"):
        st.markdown('<div class="section-label">번역 결과</div>', unsafe_allow_html=True)
        for code in LANGUAGES:
            name, ko = LANGUAGE_LABELS[code]
            with st.container(border=True):
                st.markdown(
                    f'<div class="lang-head"><span class="name">{name}</span><span class="ko">{ko}</span>'
                    f'<span class="code">{code.upper()}</span></div>',
                    unsafe_allow_html=True,
                )
                # st.code는 우측 상단에 복사 버튼을 제공한다.
                st.code(result[code], language=None, wrap_lines=True)

        with st.expander("📋 세 언어 한 번에 복사"):
            combined = "\n\n".join(f"[{code.upper()}] {result[code]}" for code in LANGUAGES)
            st.code(combined, language=None, wrap_lines=True)
