"""
services/finance_service.py
────────────────────────────
Fetches real-time financial quotes using the **yfinance** library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf

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
    """Return the latest quote for *symbol* or ``None`` on failure.

    Parameters
    ----------
    symbol:
        Yahoo Finance ticker (e.g. ``"AAPL"``, ``"BTC-USD"``).
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        hist = ticker.history(period="1mo")

        price = info.get(
            "currentPrice",
            info.get("regularMarketPrice", info.get("previousClose", 0.0)),
        )

        return FinanceData(
            symbol=symbol,
            name=info.get("shortName", ASSETS.get(symbol, symbol)),
            price=float(price or 0.0),
            open_price=float(info.get("open", info.get("regularMarketOpen", 0.0)) or 0.0),
            high_price=float(info.get("dayHigh", info.get("regularMarketDayHigh", 0.0)) or 0.0),
            low_price=float(info.get("dayLow", info.get("regularMarketDayLow", 0.0)) or 0.0),
            volume=float(info.get("volume", info.get("regularMarketVolume", 0.0)) or 0.0),
            market_cap=float(info["marketCap"]) if info.get("marketCap") else None,
            currency=info.get("currency", "USD"),
            history=hist if not hist.empty else pd.DataFrame(),
        )
    except Exception:
        return None
