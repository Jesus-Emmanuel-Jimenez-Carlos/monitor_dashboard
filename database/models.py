"""
database/models.py
──────────────────
SQLAlchemy ORM models backed by a local SQLite database.

Tables
------
- WeatherLog : stores weather snapshots fetched from Open-Meteo.
- FinanceLog : stores financial quotes fetched via yfinance.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ── engine & session ────────────────────────────────────────────────
DATABASE_URL = "sqlite:///monitor_dashboard.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── models ──────────────────────────────────────────────────────────
class WeatherLog(Base):
    """Persists a single weather observation."""

    __tablename__ = "weather_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(120), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    wind_speed_kmh = Column(Float)
    weather_description = Column(String(255))
    recorded_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherLog(city={self.city!r}, "
            f"temp={self.temperature_c}°C, "
            f"recorded_at={self.recorded_at})>"
        )


class FinanceLog(Base):
    """Persists a single financial-asset snapshot."""

    __tablename__ = "finance_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(Float)
    market_cap = Column(Float)
    currency = Column(String(10))
    recorded_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<FinanceLog(symbol={self.symbol!r}, "
            f"price={self.price}, "
            f"recorded_at={self.recorded_at})>"
        )


# ── table creation helper ──────────────────────────────────────────
def init_db() -> None:
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
