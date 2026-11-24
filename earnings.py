import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# 분기 손익계산서에서 가져올 항목 (yfinance 이름 → 화면에 보일 이름)
ITEMS = {
    "Total Revenue": "매출",
    "Operating Income": "영업이익",
    "Net Income": "순이익",
    "Diluted EPS": "주당순이익(EPS)",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_quarterly_earnings(ticker):
    """최근 분기 실적을 가져와서 오래된 분기 → 최신 분기 순서의 표로 돌려줘."""
    income = yf.Ticker(ticker).quarterly_income_stmt

    if income is None or income.empty:
        return None

    rows = [name for name in ITEMS if name in income.index]
    if "Total Revenue" not in rows:
        return None

    table = income.loc[rows].T          # 행: 분기, 열: 항목
    table = table.sort_index()          # 오래된 분기 → 최신 분기
    table = table.dropna(subset=["Total Revenue"])
    table = table.tail(5)               # 최근 5개 분기 (전년 동기 비교용)
    table.columns = [ITEMS[name] for name in table.columns]
    table.index = [pd.Timestamp(d).strftime("%Y.%m") for d in table.index]
    return table


def money(value):
    """큰 금액을 $1.23B 형태로 바꿔."""
    if value is None or pd.isna(value):
        return "-"
    value = float(value)
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(value) >= size:
            return f"${value / size:,.2f}{unit}"
    return f"${value:,.0f}"


def change_rate(new, old):
    """증감률(%)을 계산해. 계산할 수 없으면 None."""
    if new is None or old is None or pd.isna(new) or pd.isna(old) or old == 0:
        return None
    return (float(new) - float(old)) / abs(float(old)) * 100


def rate_text(rate):
    if rate is None:
        return "비교 불가"
    word = "증가" if rate >= 0 else "감소"
    return f"{abs(rate):.1f}% {word}"


def make_basic_summary(table):
    """숫자를 계산해서 한국어 요약 문장을 만들어 (AI 없이도 항상 동작)."""
    latest = table.iloc[-1]
    quarter = table.index[-1]
    lines = []

    revenue = latest.get("매출")
    sentence = f"**{quarter} 분기 매출은 {money(revenue)}**"
    if len(table) >= 2:
        sentence += f"으로 직전 분기보다 {rate_text(change_rate(revenue, table['매출'].iloc[-2]))}했습니다"
    else:
        sentence += "입니다"
    if len(table) >= 5:
        sentence += f" (1년 전 같은 분기보다 {rate_text(change_rate(revenue, table['매출'].iloc[-5]))})"
    lines.append(sentence + ".")

    if "영업이익" in table.columns and pd.notna(latest.get("영업이익")) and revenue:
        margin = float(latest["영업이익"]) / float(revenue) * 100
        lines.append(
            f"영업이익은 {money(latest['영업이익'])}로, 매출 100달러당 약 {margin:.0f}달러를 "
            f"영업으로 남겼습니다 (영업이익률 {margin:.1f}%)."
        )

    if "순이익" in table.columns and pd.notna(latest.get("순이익")):
        status = "흑자" if float(latest["순이익"]) >= 0 else "적자"
        lines.append(f"순이익은 {money(latest['순이익'])}로 {status}입니다.")

    return lines


def get_ai_summary(ticker, company_name, table):
    """OpenAI로 초보자용 실적 요약을 만들어. 키가 없으면 None."""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
        model = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")
    except Exception:
        return None
    if not api_key:
        return None

    return ask_openai(api_key, model, ticker, company_name, table.to_string())


@st.cache_data(ttl=3600, show_spinner=False)
def ask_openai(api_key, model, ticker, company_name, table_text):
    from openai import OpenAI

    prompt = f"""너는 미국 주식을 처음 공부하는 한국 대학생에게 설명하는 애널리스트야.
아래는 {company_name}({ticker})의 최근 분기 실적이야. 매출·영업이익·순이익 단위는 달러, EPS는 주당 달러야.

{table_text}

다음 형식으로 한국어로 답해줘.
- 첫 줄: 실적 흐름을 한 문장으로 요약
- 이어서 글머리표 3개 이하로 매출, 이익, EPS의 변화와 그 의미
- 어려운 용어는 괄호로 짧게 풀어서 설명
- 표에 없는 숫자나 사실은 지어내지 말고, 투자 추천이나 매수·매도 의견은 쓰지 마"""

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def show_earnings(ticker, company_name=""):
    company_name = company_name or ticker
    st.subheader(f"{company_name} 실적 요약")

    try:
        with st.spinner("실적 정보를 불러오는 중입니다..."):
            table = get_quarterly_earnings(ticker)
    except Exception:
        table = None

    if table is None or table.empty:
        st.warning("현재 이 종목의 실적 정보를 불러올 수 없습니다.")
        return

    latest = table.iloc[-1]
    previous = table.iloc[-2] if len(table) >= 2 else None

    # 최신 분기 핵심 숫자 (한국식: 오르면 빨강)
    st.caption(f"최신 분기: {table.index[-1]} (직전 분기 대비 증감)")
    cols = st.columns(4)
    for col, name in zip(cols, ["매출", "영업이익", "순이익", "주당순이익(EPS)"]):
        if name not in table.columns:
            col.metric(name, "-")
            continue
        value = latest[name]
        shown = f"${float(value):,.2f}" if name == "주당순이익(EPS)" and pd.notna(value) else money(value)
        rate = change_rate(value, previous[name]) if previous is not None else None
        col.metric(name, shown, f"{rate:+.1f}%" if rate is not None else None, delta_color="inverse")

    # 한눈에 보는 실적 (자동 계산)
    st.markdown("#### 📌 한눈에 보는 실적")
    for line in make_basic_summary(table):
        st.markdown(f"- {line}")

    # AI 요약
    st.markdown("#### 🤖 AI 실적 해설")
    try:
        with st.spinner("AI가 실적을 요약하는 중입니다..."):
            ai_text = get_ai_summary(ticker, company_name, table)
        if ai_text:
            st.markdown(ai_text)
        else:
            st.info("AI 해설을 보려면 Streamlit Secrets에 OPENAI_API_KEY를 등록하세요.")
    except Exception as error:
        st.warning(f"AI 해설을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요. ({type(error).__name__})")

    # 분기별 매출·순이익 차트
    st.markdown("#### 📊 분기별 매출과 순이익")
    fig = go.Figure()
    fig.add_bar(x=table.index, y=table["매출"] / 1e9, name="매출", marker_color="#4C78A8")
    if "순이익" in table.columns:
        fig.add_bar(x=table.index, y=table["순이익"] / 1e9, name="순이익", marker_color="#F58518")
    fig.update_layout(
        barmode="group",
        yaxis_title="십억 달러 ($B)",
        xaxis_title="결산 분기",
        height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 상세 표
    with st.expander("분기별 실적 표 보기"):
        display = table.T.copy().astype(object)
        for name in display.index:
            if name == "주당순이익(EPS)":
                display.loc[name] = [f"${float(v):,.2f}" if pd.notna(v) else "-" for v in table[name]]
            else:
                display.loc[name] = [money(v) for v in table[name]]
        st.dataframe(display)

    st.caption("실적 출처: Yahoo Finance (분기 손익계산서) · AI 해설은 틀릴 수 있으며 투자 권유가 아닙니다.")


if __name__ == "__main__":
    st.title("실적 요약")
    ticker = st.text_input("종목코드", placeholder="예: AAPL, NVDA")
    if ticker.strip():
        show_earnings(ticker.strip().upper())
