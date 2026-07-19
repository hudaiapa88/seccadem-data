#!/usr/bin/env python3
"""
generate_index.py — Scan v1/ directory and produce prayer_cities_index.json

Output schema:
{
  "version": 1,
  "generated_at": "2026-01-15T12:00:00Z",
  "countries": {
    "TR": {
      "cities": {
        "istanbul": {
          "districts": ["arnavutkoy", "avcilar", ...],
          "lat": 41.0082, "lng": 28.9784
        },
        ...
      }
    },
    "CY": { ... },
    ...
  }
}

Coordinates are extracted from the first day's JSON metadata if available,
otherwise left as null.

Usage:
  python scripts/generate_index.py
  # Output: prayer_cities_index.json (in repo root)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def extract_coords(json_path):
    """Try to extract lat/lng from a prayer data JSON file."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Try top-level fields
        lat = data.get("latitude") or data.get("lat")
        lng = data.get("longitude") or data.get("lng")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
        # Try nested coordinates object
        coords = data.get("coordinates")
        if coords and isinstance(coords, dict):
            lat = coords.get("lat") or coords.get("latitude")
            lng = coords.get("lon") or coords.get("lng") or coords.get("longitude")
            if lat is not None and lng is not None:
                return float(lat), float(lng)
    except Exception:
        pass
    return None, None


def scan_country(country_dir):
    """Scan a country directory and return its city/district structure.

    Supports two layouts:
      1. v1/{country}/{city}/{district}/{year}.json  (e.g. TR, CY)
      2. v1/{country}/{city}/{year}.json              (e.g. AL, AE, AF)
    """
    cities = {}
    for city_dir in sorted(country_dir.iterdir()):
        if not city_dir.is_dir():
            continue
        city_name = city_dir.name
        districts = []
        lat, lng = None, None

        # Check if this city has year.json files directly (layout 2)
        direct_jsons = list(city_dir.glob("*.json"))
        if direct_jsons:
            # Layout 2: v1/{country}/{city}/{year}.json — no districts
            if lat is None:
                lat, lng = extract_coords(direct_jsons[0])
            city_entry = {"districts": []}
            if lat is not None:
                city_entry["lat"] = lat
            if lng is not None:
                city_entry["lng"] = lng
            cities[city_name] = city_entry
            continue

        # Layout 1: v1/{country}/{city}/{district}/{year}.json
        for district_dir in sorted(city_dir.iterdir()):
            if not district_dir.is_dir():
                continue
            district_name = district_dir.name
            json_files = list(district_dir.glob("*.json"))
            if not json_files:
                continue
            districts.append(district_name)
            if lat is None:
                lat, lng = extract_coords(json_files[0])

        if districts:
            city_entry = {"districts": districts}
            if lat is not None:
                city_entry["lat"] = lat
            if lng is not None:
                city_entry["lng"] = lng
            cities[city_name] = city_entry

    return cities if cities else None


def main():
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    v1_dir = repo_root / "v1"

    if not v1_dir.exists():
        print(f"Error: {v1_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    countries = {}
    for country_dir in sorted(v1_dir.iterdir()):
        if not country_dir.is_dir():
            continue
        if country_dir.name.startswith("_"):
            continue  # skip _meta etc.
        country_code = country_dir.name.upper()
        cities = scan_country(country_dir)
        if cities:
            countries[country_code] = {"cities": cities}

    index = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "countries": countries,
    }

    output_path = repo_root / "prayer_cities_index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    total_cities = sum(
        len(c.get("cities", {})) for c in countries.values()
    )
    total_districts = sum(
        len(city.get("districts", []))
        for c in countries.values()
        for city in c.get("cities", {}).values()
    )

    print(f"Generated {output_path}")
    print(f"  Countries: {len(countries)}")
    print(f"  Cities:    {total_cities}")
    print(f"  Districts: {total_districts}")


if __name__ == "__main__":
    main()
