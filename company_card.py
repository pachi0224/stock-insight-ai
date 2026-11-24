import html
import json
import re
from datetime import date

import streamlit as st
import yfinance as yf


# ─────────────────────────────────────────────
# 데이터 불러오기
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_company_info(ticker):
    return yf.Ticker(ticker).get_info() or {}


def get_secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def pick_ai():
    """OpenAI 키가 있으면 OpenAI, 없으면 Gemini 키를 써. 둘 다 없으면 None."""
    if get_secret("OPENAI_API_KEY"):
        return "openai", get_secret("OPENAI_API_KEY"), get_secret("OPENAI_MODEL") or "gpt-4o-mini"
    if get_secret("GEMINI_API_KEY"):
        return "gemini", get_secret("GEMINI_API_KEY"), get_secret("GEMINI_MODEL") or "gemini-2.5-flash"
    return None


# ─────────────────────────────────────────────
# AI 분석
# ─────────────────────────────────────────────
PROMPT = """너는 미국 주식을 처음 공부하는 한국 대학생에게 회사를 설명하는 애널리스트야.
아래 영문 회사 소개만 근거로 이 회사가 어떻게 돈을 버는지 분석해줘.

회사: {name} ({ticker})
섹터/산업: {sector} / {industry}
회사 소개:
{description}

규칙:
- 모든 글은 쉬운 한국어로 써. 영어 제품명·사업부 이름은 그대로 써도 돼.
- 회사 소개에 없는 숫자(매출, 비중, 금액 등)는 절대 쓰지 마.
- 투자 추천이나 매수·매도 의견은 쓰지 마.

아래 JSON 형식으로만 답해:
{{
  "one_liner": "친구에게 2분 안에 설명하듯 이 회사를 한두 문장으로 (60자~120자)",
  "flow": [
    {{"label": "돈의 흐름 단계 (15자 이내)", "core": false}}
  ],
  "segments": [
    {{"name": "사업 부문 또는 주요 제품군", "role": "핵심 수익원 | 성장 동력 | 보조 사업 중 하나", "what": "무엇을 팔아서 누구에게 돈을 받는지 한 문장"}}
  ],
  "customers": "누가 이 회사에 돈을 내는지 한 문장",
  "analogy": "일상적인 비유 한 문장"
}}

flow는 '돈을 내는 고객'에서 시작해 '회사가 돈을 버는 지점'까지 4~6단계로 쓰고,
가장 핵심인 단계 하나만 core를 true로 해. segments는 2~4개로 써."""


def parse_json(text):
    text = (text or "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)  # ```json ... ``` 같은 포장 제거
    return json.loads(match.group(0) if match else text)


@st.cache_data(ttl=86400, show_spinner=False)
def analyze_company(provider, _api_key, model, ticker, name, sector, industry, description):
    """회사 소개를 AI로 분석해. 같은 종목은 하루 동안 다시 묻지 않아."""
    prompt = PROMPT.format(
        name=name, ticker=ticker, sector=sector, industry=industry, description=description
    )

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
    else:
        from google import genai

        client = genai.Client(api_key=_api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        text = response.text

    return parse_json(text)


# ─────────────────────────────────────────────
# 화면 꾸미기
# ─────────────────────────────────────────────
CSS = """
<style>
.cc-meta {font-size: 0.8rem; opacity: 0.65; margin-bottom: 0.6rem;}
.cc-meta b {color: #5BA4CF;}
.cc-title {font-size: 1.5rem; font-weight: 800; margin: 0.2rem 0 0.8rem;}
.cc-title span {font-size: 1rem; font-weight: 400; opacity: 0.7; margin-left: 0.5rem;}
.cc-h {font-size: 1.05rem; font-weight: 700; margin: 1.4rem 0 0.6rem;}
.cc-one {border-left: 4px solid #5BA4CF; padding: 0.3rem 0 0.3rem 1rem; font-size: 1.1rem; font-weight: 700; line-height: 1.7;}
.cc-flow {display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem;}
.cc-chip {border: 1px solid rgba(128,128,128,0.45); border-radius: 8px; padding: 0.45rem 0.8rem; font-size: 0.9rem;}
.cc-chip.core {border: 1.5px solid #5BA4CF; color: #5BA4CF; font-weight: 700;}
.cc-arrow {opacity: 0.55;}
.cc-segs {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.7rem;}
.cc-seg {border: 1px solid rgba(128,128,128,0.3); border-radius: 10px; padding: 0.8rem 1rem;}
.cc-seg-name {font-weight: 700; margin-bottom: 0.3rem;}
.cc-badge {display: inline-block; font-size: 0.72rem; padding: 0.1rem 0.5rem; border-radius: 99px; margin-bottom: 0.45rem;
           background: rgba(91,164,207,0.15); color: #5BA4CF;}
.cc-badge.grow {background: rgba(232,150,80,0.15); color: #E89650;}
.cc-badge.sub {background: rgba(128,128,128,0.15); color: inherit; opacity: 0.8;}
.cc-seg-what {font-size: 0.9rem; line-height: 1.6; opacity: 0.9;}
.cc-note {background: rgba(91,164,207,0.08); border-radius: 10px; padding: 0.8rem 1rem; line-height: 1.7; font-size: 0.95rem;}
</style>
"""


def esc(text):
    return html.escape(str(text or ""))


def flow_html(flow):
    parts = []
    for i, step in enumerate(flow):
        if i:
            parts.append('<span class="cc-arrow">→</span>')
        css = "cc-chip core" if step.get("core") else "cc-chip"
        parts.append(f'<span class="{css}">{esc(step.get("label"))}</span>')
    return '<div class="cc-flow">' + "".join(parts) + "</div>"


def segments_html(segments):
    cards = []
    for seg in segments:
        role = str(seg.get("role", ""))
        badge = "cc-badge grow" if "성장" in role else "cc-badge sub" if "보조" in role else "cc-badge"
        cards.append(
            '<div class="cc-seg">'
            f'<div class="cc-seg-name">{esc(seg.get("name"))}</div>'
            f'<span class="{badge}">{esc(role)}</span>'
            f'<div class="cc-seg-what">{esc(seg.get("what"))}</div>'
            "</div>"
        )
    return '<div class="cc-segs">' + "".join(cards) + "</div>"


def money(value):
    if value is None:
        return "-"
    value = float(value)
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(value) >= size:
            return f"${value / size:,.1f}{unit}"
    return f"${value:,.0f}"


def percent(value):
    return "-" if value is None else f"{float(value) * 100:.1f}%"


def heading(number, text):
    st.markdown(f'<div class="cc-h">{number} {esc(text)}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 메인: 기업 분석 카드
# ─────────────────────────────────────────────
def show_company_card(ticker, company_name=""):
    try:
        with st.spinner("회사 정보를 불러오는 중입니다..."):
            info = get_company_info(ticker)
    except Exception:
        info = {}

    english_name = info.get("longName") or info.get("shortName") or ticker
    korean_name = company_name if company_name and company_name != english_name else ""
    description = info.get("longBusinessSummary")
    sector = info.get("sector") or "-"
    industry = info.get("industry") or "-"

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="cc-meta"><b>AI 분석 · 회사 소개 기반</b> &nbsp; {date.today():%Y-%m-%d} 기준 &nbsp; '
        f'출처: Yahoo Finance 회사 소개·재무 지표</div>'
        f'<div class="cc-title">{esc(ticker)}<span>{esc(korean_name or english_name)}</span></div>',
        unsafe_allow_html=True,
    )

    if not description:
        st.warning("현재 이 종목의 회사 소개를 불러올 수 없습니다. ETF나 일부 종목은 회사 소개가 없습니다.")
        return

    ai = pick_ai()
    result = None
    if ai is None:
        st.info("AI 분석을 보려면 Streamlit Secrets에 OPENAI_API_KEY 또는 GEMINI_API_KEY를 등록하세요.")
    else:
        try:
            with st.spinner("AI가 회사를 분석하는 중입니다..."):
                result = analyze_company(*ai, ticker, english_name, sector, industry, description)
        except Exception as error:
            st.warning(f"AI 분석을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요. ({type(error).__name__})")

    if result:
        heading("①", "2분 드릴 한 문장")
        st.markdown(f'<div class="cc-one">{esc(result.get("one_liner"))}</div>', unsafe_allow_html=True)

        if result.get("flow"):
            heading("②", "돈 버는 구조")
            st.markdown(flow_html(result["flow"]), unsafe_allow_html=True)

        if result.get("segments"):
            heading("③", "주요 사업")
            st.markdown(segments_html(result["segments"]), unsafe_allow_html=True)

    # 실제 재무 숫자 (AI가 아닌 Yahoo Finance 값)
    heading("④" if result else "①", "숫자로 보는 회사")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("연매출 (최근 12개월)", money(info.get("totalRevenue")))
    col2.metric("매출 성장률 (전년 동기 대비)", percent(info.get("revenueGrowth")))
    col3.metric("영업이익률", percent(info.get("operatingMargins")))
    col4.metric("순이익률", percent(info.get("profitMargins")))
    st.caption(f"섹터: {sector} · 산업: {industry} · 숫자 출처: Yahoo Finance")

    if result and (result.get("customers") or result.get("analogy")):
        heading("⑤", "누가 돈을 내고, 쉽게 말하면?")
        st.markdown(
            '<div class="cc-note">'
            f'<b>주요 고객</b> · {esc(result.get("customers"))}<br>'
            f'<b>쉽게 비유하면</b> · {esc(result.get("analogy"))}'
            "</div>",
            unsafe_allow_html=True,
        )

    with st.expander("영문 회사 소개 원문 보기"):
        st.write(description)

    st.caption("AI 분석은 회사 소개를 바탕으로 작성되며 틀릴 수 있습니다. 투자 권유가 아닙니다.")


if __name__ == "__main__":
    st.title("기업 분석")
    ticker = st.text_input("종목코드", placeholder="예: UNH, NVDA")
    if ticker.strip():
        show_company_card(ticker.strip().upper())
