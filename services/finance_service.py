"""
services/finance_service.py
────────────────────────────
Fetches real-time financial quotes using the **yfinance** library.
Includes robust fallback logic for cloud environments (Render/AWS) where
Yahoo Finance's `info` endpoint is heavily rate-limited or blocked (403).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

# ── custom session for cloud deployments ────────────────────────────
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# ── predefined assets ───────────────────────────────────────────────
ASSETS: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corp.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "NVDA": "NVIDIA Corp.",
    "META": "Meta Platforms Inc.",
    "BTC-USD": "Bitcoin (USD)",
    "ETH-USD": "Ethereum (USD)",
    "^GSPC": "S&P 500",
}


@dataclass
class FinanceData:
    """Immutable snapshot of a financial asset."""

    symbol: str
    name: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    market_cap: Optional[float]
    currency: str
    history: pd.DataFrame  # last 30 days OHLCV


def get_quote(symbol: str) -> Optional[FinanceData]:
    """Return the latest quote for *symbol* or ``None`` on failure."""
    try:
        ticker = yf.Ticker(symbol, session=_session)
        
        # 1. Fetch History FIRST (this endpoint is rarely blocked by Yahoo)
        try:
            hist = ticker.history(period="1mo")
        except Exception:
            hist = pd.DataFrame()
            
        if hist.empty:
            # If we can't even get history, the asset is unavailable or IP is totally banned
            return None
            
        # 2. Fetch Info (this is the one that causes 403 Forbidden in Cloud)
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
            
        # 3. Safe Extraction Logic with Fallbacks
        last_day = hist.iloc[-1]
        
        # Price fallback: info -> history's Close
        price = info.get("currentPrice", info.get("regularMarketPrice", None))
        if price is None:
            price = last_day["Close"]
            
        # Open fallback
        open_price = info.get("open", info.get("regularMarketOpen", None))
        if open_price is None:
            open_price = last_day["Open"]
            
        # High fallback
        high_price = info.get("dayHigh", info.get("regularMarketDayHigh", None))
        if high_price is None:
            high_price = last_day["High"]
            
        # Low fallback
        low_price = info.get("dayLow", info.get("regularMarketDayLow", None))
        if low_price is None:
            low_price = last_day["Low"]
            
        # Volume fallback
        volume = info.get("volume", info.get("regularMarketVolume", None))
        if volume is None:
            volume = last_day.get("Volume", 0.0)
            
        # Market Cap (only exists in info)
        market_cap = None
        if "marketCap" in info and info["marketCap"]:
            try:
                market_cap = float(info["marketCap"])
            except (ValueError, TypeError):
                pass
                
        currency = info.get("currency", "USD")
        name = info.get("shortName", ASSETS.get(symbol, symbol))

        return FinanceData(
            symbol=symbol,
            name=name,
            price=float(price or 0.0),
            open_price=float(open_price or 0.0),
            high_price=float(high_price or 0.0),
            low_price=float(low_price or 0.0),
            volume=float(volume or 0.0),
            market_cap=market_cap,
            currency=currency,
            history=hist
        )
    except Exception as e:
        print(f"Fatal error fetching {symbol}: {e}")
        return None
