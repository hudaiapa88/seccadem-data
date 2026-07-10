#!/usr/bin/env python3
"""
Diyanet yearly prayer times scraper.
Source: ezanvakti.imsakiyem.com API (Diyanet data, full 365-day yearly)
Covers: Turkey (TR) — 81 provinces, ~869 districts
        Cyprus (CY) — 1 state, 11 districts

Output: v1/{country}/{il}/{ilce}/{year}.json (yearly file)
Usage:  python fetch_imsakiye.py 2026              # TR + CY
        python fetch_imsakiye.py 2026 TR --clean   # TR only, delete old monthly
        python fetch_imsakiye.py 2026 CY            # CY only
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "v1"
HEADERS = {"Accept": "application/json", "User-Agent": "Seccadem-Data/1.0"}
TIMEOUT = 15
RETRIES = 3
RATE_LIMIT = 2.0

EZANVAKTI_API = "https://ezanvakti.imsakiyem.com/api"

COUNTRY_CONFIG = {
    "TR": {"country_id": "2", "dir": "TR", "timezone": "Europe/Istanbul"},
    "CY": {"country_id": "1", "dir": "CY", "timezone": "Asia/Nicosia", "state_id": "751", "city": "kuzey-kibris"},
}

ADJUSTMENTS = {"sunrise": -7, "dhuhr": 5, "asr": 4, "maghrib": 6, "isha": -1}


def fetch_json(url, retries=5):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  429, wait {wait}s...", end=" ", flush=True)
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            print(f"  HTTP {e.code} for {url}")
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            print(f"  Error: {e}")
            return None
    return None


def clean_name(name):
    """Normalize Turkish characters to ASCII-safe lowercase."""
    tr_map = str.maketrans("İıÖÜÇĞŞöüçğş", "iouucgsoucgs")
    return name.translate(tr_map).lower().replace("i̇", "i").replace(" ", "-").replace("(", "").replace(")", "")


def parse_yearly(data, year, country_code, state_name, district_name):
    entries = data.get("data", [])
    if not entries:
        return None

    days = []
    for entry in entries:
        date_str = entry.get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.year != year:
            continue

        iso_date = f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        hijri_obj = entry.get("hijri_date", {})
        hijri = ""
        if hijri_obj and hijri_obj.get("year") and hijri_obj.get("day"):
            hijri = f"{hijri_obj['year']}-{hijri_obj.get('month', ''):02d}-{hijri_obj['day']:02d}"

        times = entry.get("times", {})
        days.append({
            "date": iso_date,
            "fajr": times.get("imsak", ""),
            "sunrise": times.get("gunes", ""),
            "dhuhr": times.get("ogle", ""),
            "asr": times.get("ikindi", ""),
            "maghrib": times.get("aksam", ""),
            "isha": times.get("yatsi", ""),
            "hijri": hijri,
        })

    if not days:
        return None
    days.sort(key=lambda x: x["date"])

    cfg = COUNTRY_CONFIG[country_code]
    return {
        "country": country_code,
        "city": clean_name(state_name) if country_code == "TR" else cfg.get("city", "kuzey-kibris"),
        "district": clean_name(district_name),
        "source": "diyanet",
        "method": "turkey",
        "madhab": "shafi",
        "year": year,
        "timezone": cfg["timezone"],
        "adjustments": ADJUSTMENTS,
        "days": days,
    }


def save_yearly_data(country_dir, il, ilce, year, data):
    city_dir = DATA_DIR / country_dir / il / ilce
    city_dir.mkdir(parents=True, exist_ok=True)
    filepath = city_dir / f"{year}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def clean_old_monthly_files(country_dir, il, ilce, year):
    city_dir = DATA_DIR / country_dir / il / ilce
    if not city_dir.exists():
        return 0
    removed = 0
    for f in city_dir.glob(f"{year}-*.json"):
        f.unlink()
        removed += 1
    return removed


def scrape_country(country_code, year, clean=False):
    cfg = COUNTRY_CONFIG[country_code]
    country_id = cfg["country_id"]
    country_dir = cfg["dir"]

    print(f"\n--- {country_code} via ezanvakti.imsakiyem.com ---")

    states_data = fetch_json(f"{EZANVAKTI_API}/locations/states?countryId={country_id}")
    if states_data is None:
        print("  Failed to fetch states!")
        return 0, 0, 0, 0

    states = states_data.get("data", []) if isinstance(states_data, dict) else states_data
    if not states:
        print("  No states found!")
        return 0, 0, 0, 0

    if "state_id" in cfg:
        states = [s for s in states if s.get("_id") == cfg["state_id"]] or states

    print(f"  Found {len(states)} states")

    total = 0
    skipped = 0
    failed = 0
    cleaned = 0
    district_count = 0

    for state in states:
        state_id = state.get("_id") or state.get("id")
        state_name = state.get("name_en") or state.get("name", "?")
        state_clean = clean_name(state_name)

        dist_data = fetch_json(f"{EZANVAKTI_API}/locations/districts?stateId={state_id}")
        if dist_data is None:
            print(f"  {state_name}: Failed to fetch districts")
            continue

        districts = dist_data.get("data", []) if isinstance(dist_data, dict) else dist_data
        if not districts:
            print(f"  {state_name}: No districts")
            continue

        district_count += len(districts)

        for d in districts:
            d_id = d.get("_id") or d.get("id")
            d_name = d.get("name_en") or d.get("name", "?")
            d_clean = clean_name(d_name)

            if country_code == "TR":
                il, ilce = state_clean, d_clean
            else:
                il, ilce = cfg.get("city", "kuzey-kibris"), d_clean

            output_path = DATA_DIR / country_dir / il / ilce / f"{year}.json"
            if output_path.exists():
                skipped += 1
                continue

            url = f"{EZANVAKTI_API}/prayer-times/{d_id}/yearly"
            data = fetch_json(url)
            if data is None:
                print(f"    FAIL: {state_name}/{d_name}")
                failed += 1
                continue

            result = parse_yearly(data, year, country_code, state_name, d_name)
            if result is None:
                print(f"    FAIL: {state_name}/{d_name} (no data for {year})")
                failed += 1
                continue

            save_yearly_data(country_dir, il, ilce, year, result)
            total += 1

            if clean:
                cleaned += clean_old_monthly_files(country_dir, il, ilce, year)

            time.sleep(RATE_LIMIT)

        print(f"  {state_name}: {len(districts)} districts processed")

    print(f"\n  {country_code}: {district_count} districts — saved={total}, skipped={skipped}, failed={failed}")
    return total, skipped, failed, cleaned


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    clean = "--clean" in sys.argv

    country_arg = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--"):
            country_arg = arg
            break
    countries = country_arg.split(",") if country_arg else ["TR", "CY"]

    print(f"\n{'='*60}")
    print(f"  Diyanet Yearly Scraper — Year {year}")
    print(f"  Source: ezanvakti.imsakiyem.com (Diyanet)")
    print(f"  Countries: {', '.join(countries)}")
    print(f"  Clean old monthly: {clean}")
    print(f"{'='*60}")

    grand_total = 0
    grand_skipped = 0
    grand_failed = 0
    grand_cleaned = 0

    for cc in countries:
        if cc not in COUNTRY_CONFIG:
            print(f"  Unknown country: {cc}")
            continue
        t, s, f, c = scrape_country(cc, year, clean)
        grand_total += t
        grand_skipped += s
        grand_failed += f
        grand_cleaned += c

    meta_dir = DATA_DIR / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta_path = meta_dir / "last-updated.json"

    existing = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing["diyanet_last_updated"] = datetime.now().isoformat() + "Z"
    existing["diyanet_year"] = year
    existing["diyanet_total_files"] = grand_total
    existing["diyanet_skipped"] = grand_skipped
    existing["diyanet_failed"] = grand_failed

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"  Saved:   {grand_total}")
    print(f"  Skipped: {grand_skipped} (already existed)")
    print(f"  Failed:  {grand_failed}")
    if clean:
        print(f"  Cleaned: {grand_cleaned} old monthly files")
    print(f"  Total files in repo: {grand_total + grand_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
