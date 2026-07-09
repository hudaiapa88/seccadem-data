#!/usr/bin/env python3
"""
Diyanet API scraper — fetches prayer times for Turkey (TR) and Cyprus (CY).
Source: https://ezanvakti.emushaf.net
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_URL = "https://ezanvakti.emushaf.net"
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "v1"
HEADERS = {"Accept": "application/json", "User-Agent": "Seccadem-Data/1.0"}
TIMEOUT = 15
RATE_LIMIT = 1.0  # seconds between requests (Diyanet rate limits aggressively)

# Turkey ulkeId = 2, Cyprus (TR) ulkeId = 3
COUNTRY_MAP = {
    "TR": {"ulke_id": "2", "dir": "TR", "timezone": "Europe/Istanbul"},
    "CY": {"ulke_id": "3", "dir": "CY", "timezone": "Asia/Nicosia"},
}

ADJUSTMENTS = {"sunrise": -7, "dhuhr": 5, "asr": 4, "maghrib": 6, "isha": -1}


def fetch_json(url, retries=3):
    """Fetch JSON from URL with retry on rate limit."""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...", end=" ")
                time.sleep(wait)
                continue
            print(f"  HTTP {e.code} for {url}")
            return None
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return None
    return None


def fetch_cities(ulke_id):
    """Fetch all cities for a country."""
    url = f"{BASE_URL}/sehirler?ulke={ulke_id}"
    data = fetch_json(url)
    if data is None:
        print(f"  Failed to fetch cities for ulke={ulke_id}")
        return []
    return data


def fetch_districts(sehir_id):
    """Fetch all districts for a city."""
    url = f"{BASE_URL}/ilceler?sehir={sehir_id}"
    data = fetch_json(url)
    if data is None:
        return []
    return data


def fetch_vakitler(ilce_id):
    """Fetch prayer times for a district (full year)."""
    url = f"{BASE_URL}/vakitler/{ilce_id}"
    data = fetch_json(url)
    if data is None:
        return []
    return data


def parse_vakitler(vakitler, year, month):
    """Filter vakitler for a specific year/month and convert to our schema."""
    days = []
    for entry in vakitler:
        # MiladiTarihUzunIso8601 format: "2026-07-01T00:00:00+03:00"
        date_str = entry.get("MiladiTarihUzunIso8601", "")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if dt.year != year or dt.month != month:
            continue

        days.append({
            "date": f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}",
            "fajr": entry.get("Imsak", ""),
            "sunrise": entry.get("Gunes", ""),
            "dhuhr": entry.get("Ogle", ""),
            "asr": entry.get("Ikindi", ""),
            "maghrib": entry.get("Aksam", ""),
            "isha": entry.get("Yatsi", ""),
        })

    return days


def save_month_data(country_dir, city_name, year, month, data):
    """Save a month's data as JSON."""
    city_dir = DATA_DIR / country_dir / city_name
    city_dir.mkdir(parents=True, exist_ok=True)
    filepath = city_dir / f"{year}-{month:02d}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def scrape_country(country_code, year, months=None):
    """Scrape all cities/districts for a country."""
    cfg = COUNTRY_MAP[country_code]
    if months is None:
        months = list(range(1, 13))

    print(f"\n{'='*60}")
    print(f"  Scraping {country_code} ({cfg['dir']}) — Year {year}")
    print(f"{'='*60}")

    cities = fetch_cities(cfg["ulke_id"])
    if not cities:
        print(f"  No cities found for {country_code}")
        return

    print(f"  Found {len(cities)} cities")

    total_files = 0
    for city in cities:
        city_name_en = city.get("SehirAdiEn", "").lower().replace(" ", "-").replace("ı", "i")
        sehir_id = str(city["SehirID"])

        if not city_name_en:
            continue

        print(f"\n  City: {city_name_en} (id={sehir_id})")

        districts = fetch_districts(sehir_id)
        if not districts:
            print(f"    No districts found, skipping")
            continue

        print(f"    {len(districts)} districts")

        for district in districts:
            ilce_name = district.get("IlceAdiEn", district.get("IlceAdi", "")).lower().replace(" ", "-").replace("ı", "i")
            ilce_id = str(district["IlceID"])

            if not ilce_name:
                continue

            # Use city/district naming: TR/istanbul/fatih/2026-07.json
            city_dir = city_name_en
            district_dir = f"{city_dir}/{ilce_name}"

            # Fetch all vakitler at once (API returns full year)
            vakitler = fetch_vakitler(ilce_id)
            if not vakitler:
                print(f"    {ilce_name}: No vakitler")
                continue

            for month in months:
                days = parse_vakitler(vakitler, year, month)
                if not days:
                    continue

                data = {
                    "country": country_code,
                    "city": ilce_name,
                    "district": ilce_name,
                    "parent_city": city_name_en,
                    "source": "diyanet",
                    "method": "turkey",
                    "madhab": "shafi",
                    "year": year,
                    "month": month,
                    "timezone": cfg["timezone"],
                    "adjustments": ADJUSTMENTS,
                    "days": days,
                }

                filepath = save_month_data(cfg["dir"], f"{city_name_en}/{ilce_name}", year, month, data)
                total_files += 1

            print(f"    {ilce_name}: {len(months)} months saved")
            time.sleep(RATE_LIMIT)

    print(f"\n  Total files: {total_files}")
    return total_files


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    countries = sys.argv[2].split(",") if len(sys.argv) > 2 else ["TR", "CY"]

    total = 0
    for country in countries:
        total += scrape_country(country, year) or 0

    # Update last-updated.json
    meta_dir = DATA_DIR / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_dir / "last-updated.json", "w", encoding="utf-8") as f:
        json.dump({
            "last_updated": datetime.now().isoformat() + "Z",
            "year": year,
            "countries": countries,
            "total_files": total,
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Done! {total} files saved for {year}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
