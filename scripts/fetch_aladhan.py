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


def save_yearly_data(country_code, city_name, year, data):
    """Save yearly data as JSON."""
    city_dir = DATA_DIR / country_code / city_name
    city_dir.mkdir(parents=True, exist_ok=True)
    filepath = city_dir / f"{year}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def clean_old_monthly_files(country_code, city_name, year):
    """Remove old monthly files for this city."""
    city_dir = DATA_DIR / country_code / city_name
    if not city_dir.exists():
        return 0

    removed = 0
    for f in city_dir.glob(f"{year}-*.json"):
        f.unlink()
        removed += 1
    return removed


def scrape_country(country_code, country_info, year, clean=False):
    """Scrape all cities for a country via Aladhan — yearly file."""

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

        # Check if yearly file already exists (idempotent)
        output_path = DATA_DIR / country_code / city_name / f"{year}.json"
        if output_path.exists():
            continue

        print(f"    {city_name} ({lat}, {lon})...", end=" ", flush=True)

        all_days = []
        for month in range(1, 13):
            days = fetch_aladhan_month(lat, lon, method_id, year, month)
            if not days:
                print(f"M{month} fail", end=" ")
                continue
            all_days.extend(days)
            time.sleep(RATE_LIMIT)

        if not all_days:
            print("FAIL (no data)")
            continue

        # Sort by date
        all_days.sort(key=lambda x: x["date"])

        data = {
            "country": country_code,
            "city": city_name,
            "source": source,
            "method": method,
            "madhab": madhab,
            "year": year,
            "timezone": timezone,
            "coordinates": {"lat": lat, "lon": lon},
        }

        if adjustments:
            data["adjustments"] = adjustments
        if fajr_angle:
            data["fajr_angle"] = fajr_angle
        if isha_angle:
            data["isha_angle"] = isha_angle

        data["days"] = all_days

        save_yearly_data(country_code, city_name, year, data)
        total_files += 1

        if clean:
            cleaned = clean_old_monthly_files(country_code, city_name, year)
            if cleaned:
                print(f"(cleaned {cleaned} monthly)", end=" ")

        print(f"OK ({len(all_days)} days)")

    return total_files


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    # Optional: filter countries
    country_filter = sys.argv[2].split(",") if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    clean = "--clean" in sys.argv

    countries = load_cities()
    if country_filter:
        countries = {k: v for k, v in countries.items() if k in country_filter}

    if not countries:
        print("No countries to scrape")
        return

    print(f"\n{'='*60}")
    print(f"  Aladhan Scraper — Year {year} (yearly files)")
    print(f"  Countries: {', '.join(countries.keys())}")
    print(f"  Clean old monthly: {clean}")
    print(f"{'='*60}")

    total = 0
    for code, info in countries.items():
        total += scrape_country(code, info, year, clean)

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
    print(f"  Done! {total} yearly files saved for {year}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
