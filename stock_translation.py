import html
import re

import requests
import streamlit as st


INDUSTRIES = {
    "Consumer Electronics": "소비자 전자제품",
    "Auto Manufacturers": "자동차 제조",
    "Semiconductors": "반도체",
    "Software - Infrastructure": "인프라 소프트웨어",
    "Software - Application": "응용 소프트웨어",
    "Internet Retail": "온라인 소매",
    "Internet Content & Information": "인터넷 콘텐츠·정보 서비스",
}


def split_for_translation(text):
    """가능하면 문장 단위로 묶고, 긴 문장은 단어 단위로 나눈다."""
    chunks = []
    current = ""

    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        units = [sentence]
        if len(sentence.encode("utf-8")) > 500:
            units = sentence.split()

        for unit in units:
            candidate = f"{current} {unit}".strip()
            if len(candidate.encode("utf-8")) <= 500:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(unit.encode("utf-8")) > 500:
                    raise ValueError("번역 가능한 길이를 넘는 단어가 있습니다.")
                current = unit

    if current:
        chunks.append(current)
    return chunks


@st.cache_data(ttl=86400, show_spinner=False)
def translate_chunk(chunk):
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": chunk, "langpair": "en|ko"},
        timeout=8,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("quotaFinished"):
        raise ValueError("무료 번역 한도를 소진했습니다.")
    if str(data.get("responseStatus")) != "200":
        raise ValueError("번역 서비스가 요청을 처리하지 못했습니다.")

    result = (data.get("responseData") or {}).get("translatedText")
    if not result:
        raise ValueError("번역 결과가 비어 있습니다.")
    return html.unescape(result)


def translate_text(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text in INDUSTRIES:
        return INDUSTRIES[text]
    return " ".join(translate_chunk(part) for part in split_for_translation(text))


def display_korean(text):
    try:
        return translate_text(text)
    except (requests.RequestException, ValueError) as error:
        st.caption(f"한국어 번역을 불러오지 못해 영어 원문을 표시합니다. ({error})")
        return text