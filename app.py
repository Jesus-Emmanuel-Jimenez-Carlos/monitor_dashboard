"""
app.py — Monitor Dashboard
────────────────────────────
Streamlit application that displays real-time weather and finance data,
persists snapshots to a local SQLite database, and renders interactive
Plotly charts.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database.models import (
    FinanceLog,
    SessionLocal,
    WeatherLog,
    init_db,
)
from services.finance_service import ASSETS, FinanceData, get_quote
from services.weather_service import CITIES, WeatherData, get_weather

# ── page config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── global ──────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── main background ─────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }

    /* ── sidebar ─────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e0e0ff;
    }

    /* ── metric cards ────────────────────────────── */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px 24px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
    }
    div[data-testid="stMetric"] label {
        color: #a5b4fc !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.08em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* ── buttons ──────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.6rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: all 0.25s ease;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        background: linear-gradient(135deg, #818cf8 0%, #a78bfa 100%);
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* ── tabs ─────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.04);
        border-radius: 10px 10px 0 0;
        color: #a5b4fc;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.06);
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #c7d2fe !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }

    /* ── divider ──────────────────────────────────── */
    hr {
        border-color: rgba(255,255,255,0.06);
    }

    /* ── headings ─────────────────────────────────── */
    h1, h2, h3 {
        color: #e0e7ff !important;
    }

    /* ── success / info / warning boxes ───────────── */
    .stAlert {
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── initialise database ────────────────────────────────────────────
init_db()


# ════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("# 📊 Monitor Dashboard")
    st.markdown("---")

    # ── weather controls ────────────────────────────────────────────
    st.markdown("### 🌤️ Clima")
    selected_city = st.selectbox(
        "Ciudad",
        options=list(CITIES.keys()),
        index=0,
        help="Selecciona una ciudad para consultar el clima actual.",
    )
    fetch_weather = st.button("🔄  Actualizar clima", use_container_width=True)
    save_weather = st.button("💾  Guardar clima en DB", use_container_width=True)

    st.markdown("---")

    # ── finance controls ────────────────────────────────────────────
    st.markdown("### 💹 Finanzas")
    selected_asset = st.selectbox(
        "Activo",
        options=list(ASSETS.keys()),
        format_func=lambda s: f"{s}  —  {ASSETS[s]}",
        index=0,
        help="Selecciona un activo financiero para consultar su cotización.",
    )
    fetch_finance = st.button("🔄  Actualizar cotización", use_container_width=True)
    save_finance = st.button("💾  Guardar cotización en DB", use_container_width=True)

    st.markdown("---")

    # ── history controls ────────────────────────────────────────────
    st.markdown("### 🗄️ Historial")
    show_weather_history = st.button(
        "📋  Ver historial clima", use_container_width=True
    )
    show_finance_history = st.button(
        "📋  Ver historial finanzas", use_container_width=True
    )


# ════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════

def _plotly_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply a consistent dark theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title, font=dict(size=18, color="#e0e7ff")),
        font=dict(family="Inter, sans-serif", color="#a5b4fc"),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c7d2fe"),
        ),
    )
    return fig


# ════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ════════════════════════════════════════════════════════════════════

st.markdown("# 📊 Monitor Dashboard")
st.markdown(
    "*Panel de monitoreo en tiempo real — clima y finanzas*"
)
st.markdown("---")

tab_weather, tab_finance, tab_history = st.tabs(
    ["🌤️  Clima", "💹  Finanzas", "🗄️  Historial"]
)


# ── WEATHER TAB ─────────────────────────────────────────────────────
with tab_weather:
    weather_data: WeatherData | None = None

    if fetch_weather or "weather_cache" not in st.session_state:
        with st.spinner("Consultando Open-Meteo…"):
            weather_data = get_weather(selected_city)
            if weather_data:
                st.session_state["weather_cache"] = weather_data
    else:
        weather_data = st.session_state.get("weather_cache")

    if weather_data:
        st.markdown(f"## {weather_data.description}")
        st.markdown(
            f"**{weather_data.city}**  ·  "
            f"`{weather_data.latitude:.4f}, {weather_data.longitude:.4f}`"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("🌡️ Temperatura", f"{weather_data.temperature_c:.1f} °C")
        col2.metric("💧 Humedad", f"{weather_data.humidity_pct:.0f} %")
        col3.metric("💨 Viento", f"{weather_data.wind_speed_kmh:.1f} km/h")

        # ── gauge chart ─────────────────────────────────────────────
        st.markdown("---")
        gcol1, gcol2 = st.columns(2)

        with gcol1:
            fig_temp = go.Figure(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=weather_data.temperature_c,
                    title={"text": "Temperatura (°C)", "font": {"color": "#e0e7ff"}},
                    number={"font": {"color": "#ffffff"}},
                    gauge=dict(
                        axis=dict(range=[-10, 50], tickcolor="#a5b4fc"),
                        bar=dict(color="#6366f1"),
                        bgcolor="rgba(0,0,0,0)",
                        steps=[
                            {"range": [-10, 10], "color": "rgba(59,130,246,0.25)"},
                            {"range": [10, 25], "color": "rgba(34,197,94,0.25)"},
                            {"range": [25, 35], "color": "rgba(251,191,36,0.25)"},
                            {"range": [35, 50], "color": "rgba(239,68,68,0.25)"},
                        ],
                        threshold=dict(
                            line=dict(color="#f43f5e", width=3),
                            thickness=0.8,
                            value=weather_data.temperature_c,
                        ),
                    ),
                )
            )
            _plotly_layout(fig_temp)
            fig_temp.update_layout(height=320)
            st.plotly_chart(fig_temp, use_container_width=True)

        with gcol2:
            fig_hum = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=weather_data.humidity_pct,
                    title={"text": "Humedad (%)", "font": {"color": "#e0e7ff"}},
                    number={"font": {"color": "#ffffff"}},
                    gauge=dict(
                        axis=dict(range=[0, 100], tickcolor="#a5b4fc"),
                        bar=dict(color="#06b6d4"),
                        bgcolor="rgba(0,0,0,0)",
                        steps=[
                            {"range": [0, 30], "color": "rgba(251,191,36,0.2)"},
                            {"range": [30, 60], "color": "rgba(34,197,94,0.2)"},
                            {"range": [60, 100], "color": "rgba(59,130,246,0.2)"},
                        ],
                    ),
                )
            )
            _plotly_layout(fig_hum)
            fig_hum.update_layout(height=320)
            st.plotly_chart(fig_hum, use_container_width=True)

        # ── save to db ─────────────────────────────────────────────
        if save_weather and weather_data:
            session = SessionLocal()
            try:
                record = WeatherLog(
                    city=weather_data.city,
                    latitude=weather_data.latitude,
                    longitude=weather_data.longitude,
                    temperature_c=weather_data.temperature_c,
                    humidity_pct=weather_data.humidity_pct,
                    wind_speed_kmh=weather_data.wind_speed_kmh,
                    weather_description=weather_data.description,
                )
                session.add(record)
                session.commit()
                st.success("✅ Datos del clima guardados en la base de datos.")
            except Exception as exc:
                session.rollback()
                st.error(f"Error al guardar: {exc}")
            finally:
                session.close()
    else:
        st.info("Selecciona una ciudad y presiona **Actualizar clima** en la barra lateral.")


# ── FINANCE TAB ─────────────────────────────────────────────────────
with tab_finance:
    finance_data: FinanceData | None = None

    if fetch_finance or "finance_cache" not in st.session_state:
        with st.spinner("Consultando yfinance…"):
            finance_data = get_quote(selected_asset)
            if finance_data:
                st.session_state["finance_cache"] = finance_data
    else:
        finance_data = st.session_state.get("finance_cache")

    if finance_data:
        st.markdown(f"## {finance_data.name}  `{finance_data.symbol}`")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Precio", f"{finance_data.price:,.2f} {finance_data.currency}")
        m2.metric("📈 Apertura", f"{finance_data.open_price:,.2f}")
        m3.metric(
            "🔺 Máximo / 🔻 Mínimo",
            f"{finance_data.high_price:,.2f} / {finance_data.low_price:,.2f}",
        )
        m4.metric(
            "📊 Volumen",
            f"{finance_data.volume:,.0f}" if finance_data.volume else "N/A",
        )

        if finance_data.market_cap:
            st.markdown(
                f"**Market Cap:** `{finance_data.market_cap:,.0f} {finance_data.currency}`"
            )

        # ── candlestick chart ───────────────────────────────────────
        if not finance_data.history.empty:
            st.markdown("---")
            hist = finance_data.history.reset_index()

            fig_candle = go.Figure(
                go.Candlestick(
                    x=hist["Date"],
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    increasing_line_color="#22c55e",
                    decreasing_line_color="#ef4444",
                    increasing_fillcolor="rgba(34,197,94,0.35)",
                    decreasing_fillcolor="rgba(239,68,68,0.35)",
                )
            )
            _plotly_layout(fig_candle, title=f"📈 {finance_data.symbol} — Último mes")
            fig_candle.update_layout(
                xaxis_rangeslider_visible=False, height=420
            )
            st.plotly_chart(fig_candle, use_container_width=True)

            # ── volume bar chart ────────────────────────────────────
            fig_vol = px.bar(
                hist,
                x="Date",
                y="Volume",
                color_discrete_sequence=["#8b5cf6"],
            )
            _plotly_layout(fig_vol, title=f"📊 Volumen — {finance_data.symbol}")
            fig_vol.update_layout(height=280)
            st.plotly_chart(fig_vol, use_container_width=True)

        # ── save to db ─────────────────────────────────────────────
        if save_finance and finance_data:
            session = SessionLocal()
            try:
                record = FinanceLog(
                    symbol=finance_data.symbol,
                    price=finance_data.price,
                    open_price=finance_data.open_price,
                    high_price=finance_data.high_price,
                    low_price=finance_data.low_price,
                    volume=finance_data.volume,
                    market_cap=finance_data.market_cap,
                    currency=finance_data.currency,
                )
                session.add(record)
                session.commit()
                st.success("✅ Cotización guardada en la base de datos.")
            except Exception as exc:
                session.rollback()
                st.error(f"Error al guardar: {exc}")
            finally:
                session.close()
    else:
        st.info(
            "Selecciona un activo y presiona **Actualizar cotización** en la barra lateral."
        )


# ── HISTORY TAB ─────────────────────────────────────────────────────
with tab_history:
    st.markdown("## 🗄️ Registros almacenados")

    session = SessionLocal()

    if show_weather_history:
        st.session_state["show_wh"] = True
    if show_finance_history:
        st.session_state["show_fh"] = True

    # ── weather history ─────────────────────────────────────────────
    if st.session_state.get("show_wh"):
        st.markdown("### 🌤️ Historial del clima")
        records = (
            session.query(WeatherLog)
            .order_by(WeatherLog.recorded_at.desc())
            .limit(100)
            .all()
        )
        if records:
            df_w = pd.DataFrame(
                [
                    {
                        "ID": r.id,
                        "Ciudad": r.city,
                        "Temp (°C)": r.temperature_c,
                        "Humedad (%)": r.humidity_pct,
                        "Viento (km/h)": r.wind_speed_kmh,
                        "Descripción": r.weather_description,
                        "Fecha": r.recorded_at,
                    }
                    for r in records
                ]
            )
            st.dataframe(df_w, use_container_width=True, hide_index=True)

            # line chart of temperature over time
            if len(df_w) > 1:
                fig_wh = px.line(
                    df_w.sort_values("Fecha"),
                    x="Fecha",
                    y="Temp (°C)",
                    color="Ciudad",
                    markers=True,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                _plotly_layout(fig_wh, title="Temperatura registrada a lo largo del tiempo")
                st.plotly_chart(fig_wh, use_container_width=True)
        else:
            st.warning("No hay registros de clima guardados todavía.")

    # ── finance history ─────────────────────────────────────────────
    if st.session_state.get("show_fh"):
        st.markdown("### 💹 Historial de finanzas")
        records = (
            session.query(FinanceLog)
            .order_by(FinanceLog.recorded_at.desc())
            .limit(100)
            .all()
        )
        if records:
            df_f = pd.DataFrame(
                [
                    {
                        "ID": r.id,
                        "Símbolo": r.symbol,
                        "Precio": r.price,
                        "Apertura": r.open_price,
                        "Máximo": r.high_price,
                        "Mínimo": r.low_price,
                        "Volumen": r.volume,
                        "Moneda": r.currency,
                        "Fecha": r.recorded_at,
                    }
                    for r in records
                ]
            )
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            if len(df_f) > 1:
                fig_fh = px.line(
                    df_f.sort_values("Fecha"),
                    x="Fecha",
                    y="Precio",
                    color="Símbolo",
                    markers=True,
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                )
                _plotly_layout(fig_fh, title="Precio registrado a lo largo del tiempo")
                st.plotly_chart(fig_fh, use_container_width=True)
        else:
            st.warning("No hay registros de finanzas guardados todavía.")

    session.close()


# ── footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.8rem;'>"
    "Monitor Dashboard &copy; 2026 &mdash; Built with Streamlit, Plotly, SQLAlchemy &amp; yfinance"
    "</div>",
    unsafe_allow_html=True,
)
