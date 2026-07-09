#!/usr/bin/env python3
"""
Aladhan API scraper — fetches prayer times for 63+ countries.
Source: https://api.aladhan.com/v1/calendar
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_URL = "https://api.aladhan.com/v1/calendar"
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "v1"
HEADERS = {"Accept": "application/json", "User-Agent": "Seccadem-Data/1.0"}
TIMEOUT = 15
RATE_LIMIT = 0.5  # seconds between requests


def fetch_json(url):
    """Fetch JSON from URL with error handling."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}")
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def load_cities():
    """Load cities.json and return countries that use aladhan/jakim/kemenag."""
    cities_path = REPO_ROOT / "cities.json"
    with open(cities_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    for code, info in data["countries"].items():
        source = info.get("source", "aladhan")
        if source in ("aladhan", "jakim", "kemenag"):
            result[code] = info
    return result


def fetch_aladhan_month(lat, lon, method_id, year, month):
    """Fetch one month of prayer times from Aladhan API."""
    url = f"{BASE_URL}?latitude={lat}&longitude={lon}&method={method_id}&month={month}&year={year}"
    data = fetch_json(url)
    if data is None or data.get("code") != 200:
        return []

    timings = data.get("data", [])
    days = []
    for entry in timings:
        date_obj = entry.get("date", {})
        date_str = date_obj.get("gregorian", {}).get("date", "")  # "01-07-2026"
        if not date_str:
            continue

        # Parse date — format varies, try DD-MM-YYYY
        try:
            parts = date_str.split("-")
            if len(parts) == 3:
                d, m, y = parts
                iso_date = f"{y}-{m}-{d}"
            else:
                iso_date = date_str
        except Exception:
            iso_date = date_str

        t = entry.get("timings", {})
        # Times come as "03:33 (EET)" — strip timezone
        def clean_time(s):
            return s.split(" ")[0].strip() if s else ""

        days.append({
            "date": iso_date,
            "fajr": clean_time(t.get("Fajr", "")),
            "sunrise": clean_time(t.get("Sunrise", "")),
            "dhuhr": clean_time(t.get("Dhuhr", "")),
            "asr": clean_time(t.get("Asr", "")),
            "maghrib": clean_time(t.get("Maghrib", "")),
            "isha": clean_time(t.get("Isha", "")),
        })

    return days


def save_month_data(country_code, city_name, year, month, data):
    """Save a month's data as JSON."""
    city_dir = DATA_DIR / country_code / city_name
    city_dir.mkdir(parents=True, exist_ok=True)
    filepath = city_dir / f"{year}-{month:02d}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def scrape_country(country_code, country_info, year, months=None):
    """Scrape all cities for a country via Aladhan."""
    if months is None:
        months = list(range(1, 13))

    source = country_info.get("source", "aladhan")
    method = country_info.get("method", "mwl")
    madhab = country_info.get("madhab", "shafi")
    timezone = country_info.get("timezone", "UTC")
    method_id = country_info.get("aladhan_method_id", 1)
    adjustments = country_info.get("adjustments", {})
    fajr_angle = country_info.get("fajr_angle")
    isha_angle = country_info.get("isha_angle")
    cities = country_info.get("cities", [])

    if not cities:
        print(f"  No cities for {country_code}")
        return 0

    print(f"\n  {country_code} ({country_info.get('name', '')}) — {len(cities)} cities, method={method} (id={method_id})")

    total_files = 0
    for city in cities:
        city_name = city["name"]
        lat = city["lat"]
        lon = city["lon"]

        print(f"    {city_name} ({lat}, {lon})...", end=" ")

        success = 0
        for month in months:
            days = fetch_aladhan_month(lat, lon, method_id, year, month)
            if not days:
                print(f"M{month} fail", end=" ")
                continue

            data = {
                "country": country_code,
                "city": city_name,
                "source": source,
                "method": method,
                "madhab": madhab,
                "year": year,
                "month": month,
                "timezone": timezone,
                "coordinates": {"lat": lat, "lon": lon},
            }

            if adjustments:
                data["adjustments"] = adjustments
            if fajr_angle:
                data["fajr_angle"] = fajr_angle
            if isha_angle:
                data["isha_angle"] = isha_angle

            data["days"] = days

            save_month_data(country_code, city_name, year, month, data)
            success += 1
            time.sleep(RATE_LIMIT)

        total_files += success
        print(f"{success}/{len(months)} months")

    return total_files


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    # Optional: filter countries
    country_filter = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    # Optional: filter months (1-12)
    months = list(range(1, 13))

    countries = load_cities()
    if country_filter:
        countries = {k: v for k, v in countries.items() if k in country_filter}

    if not countries:
        print("No countries to scrape")
        return

    print(f"\n{'='*60}")
    print(f"  Aladhan Scraper — Year {year}")
    print(f"  Countries: {', '.join(countries.keys())}")
    print(f"{'='*60}")

    total = 0
    for code, info in countries.items():
        total += scrape_country(code, info, year, months)

    # Update last-updated.json
    meta_dir = DATA_DIR / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    last_updated_path = meta_dir / "last-updated.json"

    existing = {}
    if last_updated_path.exists():
        with open(last_updated_path, "r") as f:
            existing = json.load(f)

    existing["aladhan_last_updated"] = datetime.now().isoformat() + "Z"
    existing["aladhan_year"] = year
    existing["aladhan_total_files"] = total

    with open(last_updated_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Done! {total} files saved for {year}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
