import streamlit as st
import pandas as pd
import requests
import zipfile
import io
import yfinance as yf
import re


def normalize(text):
    return re.sub(r"[\W_]", "", str(text)).lower()


# 미국 전체 종목 목록 불러오기
@st.cache_data(ttl=86400)
def load_stock_list():

    markets = {
        "nas": "NASDAQ",
        "nys": "NYSE",
        "ams": "AMEX"
    }

    records = []
    failed = []

    for market, exchange in markets.items():

        url = (
            "https://new.real.download.dws.co.kr/"
            f"common/master/{market}mst.cod.zip"
        )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with zipfile.ZipFile(
                io.BytesIO(response.content)
            ) as archive:

                filename = next(
                    name for name in archive.namelist()
                    if name.lower().endswith(".cod")
                )

                data = archive.read(filename).decode("cp949")

            for line in data.splitlines():

                row = line.split("\t")

                if len(row) < 9:
                    continue

                # 일반 주식만 포함
                if row[8].strip() != "2":
                    continue

                symbol = row[4].strip()

                if not symbol:
                    continue

                records.append({
                    "ticker": symbol.replace(".", "-"),
                    "korean_name": row[6].strip(),
                    "english_name": row[7].strip(),
                    "exchange": exchange
                })

        except Exception as e:
            failed.append(f"{exchange}: {e}")
                 

    df = pd.DataFrame(
        records,
        columns=[
            "ticker",
            "korean_name",
            "english_name",
            "exchange"
        ]
    )

    df = df.drop_duplicates(subset=["ticker"])

    return df, failed


# 기업 검색 기능
def search_company(query, stocks):

    keyword = normalize(query)

    if not keyword:
        return []

    # 한글 별칭 보완
    aliases = {
        "네비우스": "NBIS",
        "네비우스그룹": "NBIS",
        "아이온큐": "IONQ",
        "아이렌": "IREN",
        "로켓랩": "RKLB",
        "구글": "GOOGL",
        "엔비디아": "NVDA"
    }

    keyword = normalize(
        aliases.get(keyword, keyword)
    )

    # 종목코드, 한글명, 영어명 검색
    results = stocks[
        stocks["ticker"].map(normalize).str.contains(
            keyword, regex=False
        )
        |
        stocks["korean_name"].map(normalize).str.contains(
            keyword, regex=False
        )
        |
        stocks["english_name"].map(normalize).str.contains(
            keyword, regex=False
        )
    ].copy()

    if not results.empty:

        # 정확히 일치하는 종목을 우선 표시
        results["priority"] = results.apply(
            lambda row: 0 if keyword in [
                normalize(row["ticker"]),
                normalize(row["korean_name"]),
                normalize(row["english_name"])
            ] else 1,
            axis=1
        )

        results = results.sort_values(
            ["priority", "korean_name"]
        )

        return results.head(50).to_dict("records")

    # 목록에 없는 종목은 Yahoo Finance에서 검색
    fallback = []

    try:
        search = yf.Search(query, max_results=20)

        for item in search.quotes:

            if (
                item.get("quoteType") == "EQUITY"
                and item.get("exchange") in [
                    "NMS", "NYQ", "NGM", "NCM",
                    "ASE", "BTS", "PCX", "BATS"
                ]
            ):

                fallback.append({
                    "ticker": item["symbol"],
                    "korean_name": "",
                    "english_name": (
                        item.get("longname")
                        or item.get("shortname")
                        or item["symbol"]
                    ),
                    "exchange": item.get("exchange", "")
                })

    except Exception:
        pass

    return fallback