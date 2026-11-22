import streamlit as st
import yfinance as yf
import plotly.graph_objects as go


@st.cache_data(ttl=60)
def get_history(ticker, period):
    stock = yf.Ticker(ticker)

    return stock.history(
        period=period,
        auto_adjust=False
    )


def show_stock_price(ticker):

    try:
        recent = get_history(ticker, "5d")

        if len(recent) < 2:
            st.warning("주가 정보를 충분히 불러올 수 없습니다.")
            return

        # 최근 주가 및 등락률
        current = float(recent["Close"].iloc[-1])
        previous = float(recent["Close"].iloc[-2])
        change = current - previous
        change_rate = change / previous * 100
        volume = int(recent["Volume"].iloc[-1])

        st.subheader(f"{ticker} 주가 정보")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "최근 주가",
            f"${current:,.2f}",
            f"{change:+.2f} ({change_rate:+.2f}%)",
            delta_color="inverse"
        )

        col2.metric(
            "직전 거래일 종가",
            f"${previous:,.2f}"
        )

        col3.metric(
            "최근 거래량",
            f"{volume:,}"
        )

        st.caption(
            f"시세 기준일: {recent.index[-1].strftime('%Y-%m-%d')}"
        )

        # 조회 기간 선택
        period_options = {
            "1개월": "1mo",
            "3개월": "3mo",
            "6개월": "6mo",
            "1년": "1y",
            "5년": "5y"
        }

        selected = st.radio(
            "조회 기간",
            list(period_options.keys()),
            horizontal=True
        )

        chart_type = st.radio(
            "차트 종류",
            ["캔들 차트", "선 차트"],
            horizontal=True
        )

        history = get_history(
            ticker,
            period_options[selected]
        )

        if history.empty:
            st.warning("해당 기간의 주가 데이터가 없습니다.")
            return

        fig = go.Figure()

        # 캔들 차트
        if chart_type == "캔들 차트":

            fig.add_trace(
                go.Candlestick(
                    x=history.index,
                    open=history["Open"],
                    high=history["High"],
                    low=history["Low"],
                    close=history["Close"],
                    increasing_line_color="#EF4444",
                    increasing_fillcolor="#EF4444",
                    decreasing_line_color="#2563EB",
                    decreasing_fillcolor="#2563EB",
                    name="주가"
                )
            )

        # 선 차트
        else:

            fig.add_trace(
                go.Scatter(
                    x=history.index,
                    y=history["Close"],
                    mode="lines",
                    name="주가",
                    line=dict(
                        color="#2196F3",
                        width=2
                    )
                )
            )

        fig.update_layout(
            title=f"{ticker} 주가 흐름",
            xaxis_title="날짜",
            yaxis_title="주가 (USD)",
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            height=500
        )

        # 주말 공백 제거
        fig.update_xaxes(
            rangebreaks=[
                dict(bounds=["sat", "mon"])
            ]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # 기간별 최고가, 최저가
        col4, col5 = st.columns(2)

        col4.metric(
            "기간 내 최고가",
            f"${history['High'].max():,.2f}"
        )

        col5.metric(
            "기간 내 최저가",
            f"${history['Low'].min():,.2f}"
        )

        # 최근 거래일 상세 정보
        st.subheader("최근 거래일 상세 정보")

        col6, col7, col8, col9 = st.columns(4)

        col6.metric(
            "시가",
            f"${recent['Open'].iloc[-1]:,.2f}"
        )

        col7.metric(
            "고가",
            f"${recent['High'].iloc[-1]:,.2f}"
        )

        col8.metric(
            "저가",
            f"${recent['Low'].iloc[-1]:,.2f}"
        )

        col9.metric(
            "종가",
            f"${current:,.2f}"
        )

        st.caption(
            "데이터 출처: Yahoo Finance (yfinance)"
        )

        st.caption(
            "시세는 실제 시장 가격보다 지연될 수 있습니다."
        )

    except Exception:
        st.error(
            "주가 정보를 불러오지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )