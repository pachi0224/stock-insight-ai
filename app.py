import streamlit as st
from stock_price import show_stock_price
from stock_search import load_stock_list, search_company
from company_news import show_company_news
from earnings import show_earnings
from company_card import show_company_card

st.set_page_config(
    page_title="Stock Insight AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Insight AI")
st.write("미국 주식 정보 조회 서비스")


# 미국 종목 목록 불러오기
with st.spinner("미국 주식 종목 목록을 불러오는 중입니다..."):

    stocks, failed = load_stock_list()


st.caption(f"등록된 미국 주식 종목: {len(stocks):,}개")

if failed:
    st.warning(
        "일부 거래소의 종목 목록을 불러오지 못했습니다: "
        + ", ".join(failed)
    )


# 기업 검색
with st.form("search_form"):

    query = st.text_input(
        "기업명 또는 종목코드를 입력하세요.",
        placeholder="예: 네비우스, 아이온큐, 테슬라, AAPL"
    )

    submitted = st.form_submit_button("검색")


if "search_results" not in st.session_state:
    st.session_state.search_results = []


if submitted:

    st.session_state.search_results = []

    if query.strip():

        st.session_state.search_results = search_company(
            query, stocks
        )

        if not st.session_state.search_results:

            st.warning(
                "검색 결과가 없습니다. "
                "영어 기업명 또는 종목코드로 검색해 주세요."
            )

    else:
        st.warning("기업명을 입력해 주세요.")


results = st.session_state.search_results


# 검색 결과 표시
if results:

    def make_label(item):

        korean = item["korean_name"]
        english = item["english_name"]
        ticker = item["ticker"]

        if korean:
            return f"{korean} | {english} ({ticker})"

        return f"{english} ({ticker})"


    selected = st.selectbox(
        "조회할 기업을 선택하세요.",
        range(len(results)),
        format_func=lambda i: make_label(results[i])
    )

    company = results[selected]
    ticker = company["ticker"]

    st.divider()

    st.subheader(
        company["korean_name"] or company["english_name"]
    )

    st.caption(
        f"종목코드: {ticker} | 거래소: {company['exchange']}"
    )

    # 기존 주가 조회 기능 연결
    company_name = company["korean_name"] or company["english_name"]
    view = st.radio(
        "조회할 정보",
        ["주가", "실적 요약", "기업 분석", "회사 정보 · 뉴스"],
        index=3,
        horizontal=True,
    )
    if view == "기업 분석":
        show_company_card(ticker, company_name)

    if view == "주가":
        show_stock_price(ticker)

    if view == "실적 요약":
        show_earnings(ticker, company_name)

    if view == "회사 정보 · 뉴스":
        show_company_news(company_name, ticker)
        


st.caption(
    "종목 목록 출처: 한국투자증권 / 주가 출처: Yahoo Finance"
)
