from stock_translation import display_korean
from stock_translation import translate_text
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests
import streamlit as st


# 회사 소개는 여기에 등록된 기업에 표시돼.
# 뉴스는 아래 목록에 없는 회사도 이름으로 검색할 수 있어.
COMPANIES = {
    "005930": ("삼성전자", "반도체·전자제품",
               "메모리 반도체, 스마트폰, TV, 생활가전 등을 만드는 기업입니다."),
    "000660": ("SK하이닉스", "반도체",
               "서버와 컴퓨터 등에 쓰이는 DRAM과 NAND 플래시 메모리를 만드는 기업입니다."),
    "005380": ("현대차", "자동차",
               "승용차, SUV, 전기차, 상용차 등을 개발하고 판매하는 기업입니다."),
    "035720": ("카카오", "인터넷 서비스",
               "카카오톡을 기반으로 광고, 커머스, 콘텐츠 등의 서비스를 제공하는 기업입니다."),
    "066570": ("LG전자", "전자제품",
               "생활가전, TV, 자동차 부품 등을 개발하고 판매하는 기업입니다."),
}


@st.cache_data(ttl=600, show_spinner=False)
def get_news(company_name):
    params = {
        "q": f'"{company_name}" when:7d',
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
    }
    response = requests.get(
        "https://news.google.com/rss/search",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)

    articles = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "").strip()
        if not title or not link.startswith(("https://", "http://")):
            continue

        # 제목 끝에 언론사 이름이 붙어 있으면 한 번만 표시해.
        if source:
            title = title.removesuffix(f" - {source}")

        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
            timestamp = published.timestamp()
            date = published.strftime("%Y.%m.%d")
        except (TypeError, ValueError, OverflowError):
            timestamp = 0
            date = ""

        articles.append((timestamp, title, source, date, link))

    articles.sort(key=lambda article: article[0], reverse=True)

    latest = []
    seen_titles = set()
    for _, title, source, date, link in articles:
        if title not in seen_titles:
            latest.append((title, source, date, link))
            seen_titles.add(title)
        if len(latest) == 3:
            break
    return latest
import textwrap
from deep_translator import GoogleTranslator


@st.cache_data(ttl=86400, show_spinner=False)
def translate_to_korean(text):
    translator = GoogleTranslator(source="en", target="ko")
    parts = textwrap.wrap(text, width=4000)
    translated = []

    for part in parts:
        result = translator.translate(part)
        if not result:
            raise ValueError("번역 결과가 비어 있습니다.")
        translated.append(result)

    return " ".join(translated)


def korean_or_original(text):
    if not text:
        return ""
    try:
        return translate_to_korean(text)
    except Exception:
        return f"{text} (영문 원문 · 번역을 불러오지 못했습니다)"

def show_company_news(company_name, ticker=""):
    company_name = company_name.strip()
    if not company_name:
        return

    code = str(ticker or "").strip().split(".")[0]
    if code.isdigit():
        code = code.zfill(6)

    # 단독 실행하면 회사명으로, 조장의 화면과 연결하면 종목코드로도 찾을 수 있어.
    if not code:
        for stock_code, (name, _, _) in COMPANIES.items():
            if name.casefold() == company_name.casefold():
                code = stock_code
                break

    st.subheader(f"{company_name} 회사 정보")
    if code:
        st.caption(f"종목코드 {code}")

    if code in {"NBIS", "AAPL", "TSLA"}:
        profiles_ko = {
            "NBIS": (
                "인터넷 콘텐츠·정보 서비스",
                "네비우스 그룹은 AI 개발을 위한 GPU 클러스터, 클라우드 플랫폼, "
                "개발 도구를 제공합니다.",
            ),
            "AAPL": (
                "소비자 전자제품",
                "애플은 아이폰, 맥, 아이패드 등을 설계하고 판매하며, "
                "앱스토어와 아이클라우드 등의 서비스를 제공합니다.",
            ),
            "TSLA": (
                "자동차 제조",
                "테슬라는 전기자동차를 설계·제조·판매하며, "
                "배터리 에너지 저장 시스템과 전기차 충전망도 운영합니다.",
            ),
        }
        industry_ko, description_ko = profiles_ko[code]
        st.write(f"**업종** · {industry_ko}")
        st.write(description_ko)
    elif code:
        import yfinance as yf

        try:
            yahoo_ticker = code.replace(".", "-")
            with st.spinner("미국 기업 정보를 불러오는 중입니다..."):
                info = yf.Ticker(yahoo_ticker).get_info() or {}
        except Exception:
            info = {}

        industry = info.get("industry") or info.get("sector")
        description = info.get("longBusinessSummary")


        if industry:
            industry_names = {
                "internet content & information": "인터넷 콘텐츠·정보 서비스",
                "consumer electronics": "소비자 전자제품",
                "auto manufacturers": "자동차 제조",
                "semiconductors": "반도체",
            }
            industry_ko = industry_names.get(industry.strip().casefold())
            if industry_ko is None:
                try:
                    industry_ko = translate_text(industry)
                except Exception:
                    industry_ko = industry
            st.write(f"**업종** · {industry_ko}")

        if description:
            try:
                with st.spinner("회사 소개를 한국어로 번역하는 중입니다..."):
                    description_ko = translate_text(description)
                st.write(description_ko)
            except Exception as error:
                st.warning(f"회사 소개 번역 실패 · {type(error).__name__}: {error}")
                with st.expander("영어 원문 보기"):
                    st.write(description)
        else:
            st.caption("현재 제공되는 회사 소개가 없습니다.")
    st.subheader("최근 관련 뉴스")
    st.caption("최근 7일간의 Google 뉴스 검색 결과에서 최신순으로 최대 3건을 표시합니다.")

    search_params = urlencode({
        "q": company_name, "hl": "ko", "gl": "KR", "ceid": "KR:ko"
    })
    search_url = f"https://news.google.com/search?{search_params}"

    try:
        with st.spinner("관련 뉴스를 불러오는 중입니다..."):
            articles = get_news(company_name)
    except (requests.RequestException, ET.ParseError):
        st.warning("현재 뉴스 목록을 불러올 수 없습니다.")
        st.link_button("Google 뉴스에서 직접 보기", search_url)
        return

    if not articles:
        st.info("최근 7일 동안 검색된 기사가 없습니다.")
        st.link_button("기간 제한 없이 뉴스 검색", search_url)
        return

    for title, source, date, link in articles:
        with st.container(border=True):
            st.caption(" · ".join(value for value in (source, date) if value))
            st.write(title)
            st.link_button("기사 보기", link)
if __name__ == "__main__":
    st.title("기업 정보와 뉴스")
    company_name = st.text_input("조회할 기업", placeholder="예: 삼성전자, 카카오")
    if company_name.strip():
        show_company_news(company_name, "")