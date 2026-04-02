"""
CropSentinel AI  -  utils/geo_context.py
Geo-context engine: reverse-geocoding + Indian seasonal crop disease calendar.
"""

import logging
from datetime import datetime

from geopy.geocoders import Nominatim

logger = logging.getLogger("GeoContext")


class GeoContextEngine:
    """
    Resolves latitude/longitude to a human-readable region name and
    enriches it with Indian agro-meteorological seasonal context.
    """

    def __init__(self):
        self.geolocator = Nominatim(user_agent="cropsentinel_ai_v4")
        logger.info("GeoContextEngine initialised.")

    def get_context(self, lat, lon, timestamp_str) -> dict:
        """
        Build a rich geo-context dict for the given coordinates and timestamp.

        Parameters
        ----------
        lat : float or None
        lon : float or None
        timestamp_str : str or None  (ISO 8601 or any datetime parseable format)

        Returns
        -------
        dict with keys:
          region_name, season, humidity_estimate, rainfall_context,
          seasonal_risk, risk_note, disease_calendar, timestamp_str, month
        """

        if lat is None or lon is None:
            region_name = "Location not provided"
        else:
            try:
                location = self.geolocator.reverse(
                    f"{lat},{lon}", timeout=3, language="en"
                )
                addr = location.raw.get("address", {})
                parts = [
                    addr.get("city") or addr.get("town") or addr.get("village"),
                    addr.get("state"),
                    addr.get("country"),
                ]
                region_name = ", ".join(p for p in parts if p)
                if not region_name:
                    region_name = f"Region ({lat:.2f}°N, {lon:.2f}°E)"
            except Exception as e:
                logger.warning(f"Reverse geocoding failed: {e}")
                try:
                    region_name = f"Region ({lat:.2f}°N, {lon:.2f}°E)"
                except Exception:
                    region_name = "Unknown region"

        dt = None
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str)
            except Exception:
                try:
                    from dateutil import parser as dateutil_parser
                    dt = dateutil_parser.parse(timestamp_str)
                except Exception:
                    pass
        if dt is None:
            dt = datetime.now()

        month = dt.month
        timestamp_display = dt.strftime("%B %d, %Y at %I:%M %p")

        hour = dt.hour
        if 5 <= hour < 9:
            time_context = "Early Morning - ideal spraying window"
        elif 9 <= hour < 16:
            time_context = "Midday - Avoid spraying, high evaporation rate"
        elif 16 <= hour < 19:
            time_context = "Late Afternoon - acceptable spraying window"
        else:
            time_context = "Night - spraying not recommended"

        if month in [12, 1, 2]:
            season           = "Winter (Rabi Season)"
            humidity         = 55
            rainfall         = "Low  -  dry season (20-40mm/month)"
            seasonal_risk    = "MODERATE"
            risk_note        = (
                "Powdery Mildew and Rust diseases more prevalent in cool dry conditions."
            )
            calendar = {
                "Apple":  "MODERATE  -  Apple Scab and Cedar Rust elevated",
                "Tomato": "LOW  -  Reduced disease pressure in winter",
                "Grape":  "MODERATE  -  Downy Mildew risk in late winter",
            }

        elif month in [3, 4, 5]:
            season           = "Pre-Summer / Zaid Season"
            humidity         = 35
            rainfall         = "Very low  -  irrigation dependent (10-20mm/month)"
            seasonal_risk    = "LOW"
            risk_note        = (
                "Reduced fungal risk. Watch for bacterial diseases and heat stress."
            )
            calendar = {
                "Apple":  "HIGH  -  Apple Scab peaks in spring",
                "Tomato": "MODERATE  -  Bacterial diseases under heat stress",
                "Grape":  "LOW  -  Dry conditions limit fungal spread",
            }

        elif month in [6, 7, 8, 9]:
            season           = "South-West Monsoon (Kharif Season)"
            humidity         = 82
            rainfall         = "High  -  SW Monsoon active (150-300mm/month)"
            seasonal_risk    = "CRITICAL"
            risk_note        = (
                "High humidity accelerates fungal spore spread. Late Blight, "
                "Downy Mildew, and Anthracnose peak during this season."
            )
            calendar = {
                "Apple":  "MODERATE  -  Cedar Rust and Scab risk elevated",
                "Tomato": "CRITICAL  -  Late Blight and Early Blight peak Jun-Sep",
                "Grape":  "HIGH  -  Downy Mildew and Leaf Blight critical risk",
            }

        else:  # month in [10, 11]
            season           = "Post-Monsoon / North-East Monsoon"
            humidity         = 68
            rainfall         = "Moderate  -  retreating monsoon (60-100mm/month)"
            seasonal_risk    = "MODERATE-HIGH"
            risk_note        = (
                "Residual moisture creates conditions for continued fungal spread. "
                "Monitor closely."
            )
            calendar = {
                "Apple":  "LOW  -  Post-harvest season",
                "Tomato": "HIGH  -  Late Blight risk persists with residual moisture",
                "Grape":  "MODERATE  -  Continued fungal risk in post-monsoon humidity",
            }

        return {
            "region_name":       region_name,
            "season":            season,
            "humidity_estimate": humidity,
            "rainfall_context":  rainfall,
            "seasonal_risk":     seasonal_risk,
            "risk_note":         risk_note,
            "disease_calendar":  calendar,
            "timestamp_str":     timestamp_display,
            "time_context":      time_context,
            "month":             month,
        }
