#!/usr/bin/env python3
"""
Validate all JSON files against the expected schema.
Usage: python validate.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "v1"
REQUIRED_FIELDS = ["country", "city", "source", "method", "madhab", "year", "month", "timezone", "days"]
DAY_FIELDS = ["date", "fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
TIME_PATTERN = __import__("re").compile(r"^\d{2}:\d{2}$")
DATE_PATTERN = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_file(filepath):
    """Validate a single JSON file. Returns list of errors."""
    errors = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing field: {field}")

    if errors:
        return errors

    # Check year/month match filename
    filename = filepath.stem  # "2026-07"
    expected_ym = f"{data['year']}-{data['month']:02d}"
    if filename != expected_ym:
        errors.append(f"Filename {filename} doesn't match year-month {expected_ym}")

    # Check days array
    days = data.get("days", [])
    if not days:
        errors.append("No days data")
        return errors

    if len(days) < 1 or len(days) > 31:
        errors.append(f"Unexpected day count: {len(days)} (expected 1-31)")

    for i, day in enumerate(days):
        for field in DAY_FIELDS:
            if field not in day:
                errors.append(f"Day {i}: missing {field}")
                break

        if "date" in day and not DATE_PATTERN.match(day["date"]):
            errors.append(f"Day {i}: bad date format '{day['date']}'")

        for tf in ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]:
            if tf in day and day[tf] and not TIME_PATTERN.match(day[tf]):
                errors.append(f"Day {i}: bad {tf} format '{day[tf]}'")
                break

        # Check time ordering
        if all(day.get(f) for f in DAY_FIELDS[1:]):
            try:
                times = {f: int(day[f].split(":")[0]) * 60 + int(day[f].split(":")[1])
                         for f in ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]}
                if not (times["fajr"] < times["sunrise"] < times["dhuhr"]):
                    errors.append(f"Day {i}: fajr < sunrise < dhuhr violated")
                if not (times["dhuhr"] <= times["asr"]):
                    errors.append(f"Day {i}: dhuhr <= asr violated")
                if not (times["asr"] < times["maghrib"]):
                    errors.append(f"Day {i}: asr < maghrib violated")
            except (ValueError, IndexError):
                pass

    return errors


def main():
    if not DATA_DIR.exists():
        print("v1/ directory not found")
        sys.exit(1)

    json_files = list(DATA_DIR.rglob("*.json"))
    # Exclude _meta files
    json_files = [f for f in json_files if "_meta" not in str(f)]

    if not json_files:
        print("No data files found")
        sys.exit(1)

    print(f"\nValidating {len(json_files)} files...\n")

    errors_count = 0
    ok_count = 0

    for filepath in sorted(json_files):
        rel = filepath.relative_to(REPO_ROOT)
        errors = validate_file(filepath)

        if errors:
            errors_count += 1
            print(f"FAIL  {rel}")
            for e in errors[:3]:
                print(f"      - {e}")
            if len(errors) > 3:
                print(f"      ... and {len(errors) - 3} more")
        else:
            ok_count += 1

    print(f"\n{'='*40}")
    print(f"  OK:   {ok_count}")
    print(f"  FAIL: {errors_count}")
    print(f"  Total: {len(json_files)}")
    print(f"{'='*40}")

    if errors_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
