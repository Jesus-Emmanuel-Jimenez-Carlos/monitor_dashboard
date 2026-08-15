"""
services/weather_service.py
────────────────────────────
Fetches current weather data from the **Open-Meteo** free API.

Open-Meteo requires no API key and offers generous rate limits,
making it ideal for demo / personal dashboards.

Reference: https://open-meteo.com/en/docs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

# ── WMO weather-code descriptions (subset) ──────────────────────────
_WMO_CODES: dict[int, str] = {
    0: "Cielo despejado ☀️",
    1: "Mayormente despejado 🌤️",
    2: "Parcialmente nublado ⛅",
    3: "Nublado ☁️",
    45: "Niebla 🌫️",
    48: "Niebla con escarcha 🌫️❄️",
    51: "Llovizna ligera 🌦️",
    53: "Llovizna moderada 🌧️",
    55: "Llovizna intensa 🌧️",
    61: "Lluvia ligera 🌦️",
    63: "Lluvia moderada 🌧️",
    65: "Lluvia intensa 🌧️💧",
    71: "Nevada ligera 🌨️",
    73: "Nevada moderada 🌨️",
    75: "Nevada intensa ❄️",
    80: "Chubascos ligeros 🌦️",
    81: "Chubascos moderados 🌧️",
    82: "Chubascos violentos ⛈️",
    95: "Tormenta ⛈️",
    96: "Tormenta con granizo ligero ⛈️🧊",
    99: "Tormenta con granizo fuerte ⛈️🧊",
}

# ── predefined cities ───────────────────────────────────────────────
CITIES: dict[str, tuple[float, float]] = {
    "Ciudad de México": (19.4326, -99.1332),
    "Guadalajara": (20.6597, -103.3496),
    "Monterrey": (25.6866, -100.3161),
    "Buenos Aires": (-34.6037, -58.3816),
    "Madrid": (40.4168, -3.7038),
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Tokyo": (35.6762, 139.6503),
    "São Paulo": (-23.5505, -46.6333),
    "Berlin": (52.5200, 13.4050),
}


@dataclass
class WeatherData:
    """Immutable snapshot of current weather."""

    city: str
    latitude: float
    longitude: float
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    weather_code: int
    description: str


def get_weather(city: str) -> Optional[WeatherData]:
    """Return current weather for *city* or ``None`` on failure.

    Parameters
    ----------
    city:
        Must be a key present in :pydata:`CITIES`.
    """
    coords = CITIES.get(city)
    if coords is None:
        return None

    lat, lon = coords
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&current=relative_humidity_2m"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    current = data.get("current_weather", {})
    current_extra = data.get("current", {})

    code = current.get("weathercode", 0)
    return WeatherData(
        city=city,
        latitude=lat,
        longitude=lon,
        temperature_c=current.get("temperature", 0.0),
        humidity_pct=current_extra.get("relative_humidity_2m", 0.0),
        wind_speed_kmh=current.get("windspeed", 0.0),
        weather_code=code,
        description=_WMO_CODES.get(code, f"Código WMO {code}"),
    )
