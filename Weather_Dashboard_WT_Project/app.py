import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

@app.after_request
def disable_page_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

def get_json(url, params, timeout=12):
    full_url = url + "?" + urlencode(params, doseq=True)
    req = Request(
        full_url,
        headers={
            "User-Agent": "WeatherDashboardWT/1.0",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def weather_label(code):
    code = int(code or 0)
    table = {
        0: ("Clear sky", "clear"),
        1: ("Mainly clear", "clear"),
        2: ("Partly cloudy", "cloudy"),
        3: ("Overcast", "cloudy"),
        45: ("Fog", "fog"),
        48: ("Rime fog", "fog"),
        51: ("Light drizzle", "rain"),
        53: ("Drizzle", "rain"),
        55: ("Heavy drizzle", "rain"),
        56: ("Freezing drizzle", "rain"),
        57: ("Heavy freezing drizzle", "rain"),
        61: ("Light rain", "rain"),
        63: ("Rain", "rain"),
        65: ("Heavy rain", "rain"),
        66: ("Freezing rain", "rain"),
        67: ("Heavy freezing rain", "rain"),
        71: ("Light snow", "snow"),
        73: ("Snow", "snow"),
        75: ("Heavy snow", "snow"),
        77: ("Snow grains", "snow"),
        80: ("Light showers", "rain"),
        81: ("Showers", "rain"),
        82: ("Heavy showers", "storm"),
        85: ("Snow showers", "snow"),
        86: ("Heavy snow showers", "snow"),
        95: ("Thunderstorm", "storm"),
        96: ("Thunderstorm with hail", "storm"),
        99: ("Severe thunderstorm", "storm"),
    }
    return table.get(code, ("Weather", "cloudy"))

def geocode_city(city):
    data = get_json(
        GEOCODE_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results") or []
    if not results:
        return None
    item = results[0]
    return {
        "name": item.get("name"),
        "admin1": item.get("admin1"),
        "country": item.get("country"),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "timezone": item.get("timezone"),
    }

def forecast(lat, lon):
    current_vars = [
        "temperature_2m",
        "relative_humidity_2m",
        "apparent_temperature",
        "is_day",
        "precipitation",
        "rain",
        "weather_code",
        "cloud_cover",
        "pressure_msl",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
    ]
    hourly_vars = [
        "temperature_2m",
        "apparent_temperature",
        "precipitation_probability",
        "weather_code",
        "wind_speed_10m",
        "relative_humidity_2m",
    ]
    daily_vars = [
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "apparent_temperature_max",
        "apparent_temperature_min",
        "sunrise",
        "sunset",
        "uv_index_max",
        "precipitation_probability_max",
        "wind_speed_10m_max",
    ]
    return get_json(
        FORECAST_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join(current_vars),
            "hourly": ",".join(hourly_vars),
            "daily": ",".join(daily_vars),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
            "forecast_days": 7,
        },
    )

def air_quality(lat, lon):
    try:
        return get_json(
            AIR_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
                "timezone": "auto",
            },
            timeout=8,
        )
    except Exception:
        return {}

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/search")
def search():
    city = (request.args.get("city") or "").strip()
    if len(city) < 2:
        return jsonify({"error": "Enter at least 2 characters."}), 400
    try:
        data = get_json(
            GEOCODE_URL,
            {"name": city, "count": 6, "language": "en", "format": "json"},
        )
        return jsonify(data.get("results") or [])
    except Exception:
        return jsonify({"error": "Location search is temporarily unavailable."}), 502

@app.get("/api/weather")
def api_weather():
    city = (request.args.get("city") or "").strip()
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    try:
        if city:
            location = geocode_city(city)
            if not location:
                return jsonify({"error": "City not found. Try another spelling."}), 404
            lat, lon = location["latitude"], location["longitude"]
        elif lat is not None and lon is not None:
            location = {
                "name": "Current location",
                "admin1": None,
                "country": None,
                "latitude": lat,
                "longitude": lon,
                "timezone": None,
            }
        else:
            location = geocode_city("Ahmedabad")
            lat, lon = location["latitude"], location["longitude"]

        wx = forecast(lat, lon)
        aq = air_quality(lat, lon)

        current = wx.get("current") or {}
        label, theme = weather_label(current.get("weather_code"))

        daily = wx.get("daily") or {}
        codes = daily.get("weather_code") or []
        daily_labels = [weather_label(c)[0] for c in codes]
        daily_themes = [weather_label(c)[1] for c in codes]

        result = {
            "location": location,
            "timezone": wx.get("timezone"),
            "timezone_abbreviation": wx.get("timezone_abbreviation"),
            "elevation": wx.get("elevation"),
            "current": current,
            "current_units": wx.get("current_units") or {},
            "condition": label,
            "theme": theme,
            "hourly": wx.get("hourly") or {},
            "hourly_units": wx.get("hourly_units") or {},
            "daily": daily,
            "daily_units": wx.get("daily_units") or {},
            "daily_labels": daily_labels,
            "daily_themes": daily_themes,
            "air_quality": aq.get("current") or {},
            "air_quality_units": aq.get("current_units") or {},
        }
        return jsonify(result)
    except (HTTPError, URLError, TimeoutError):
        return jsonify({"error": "Weather service is temporarily unavailable. Please try again."}), 502
    except Exception:
        return jsonify({"error": "Could not load weather data."}), 500

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
