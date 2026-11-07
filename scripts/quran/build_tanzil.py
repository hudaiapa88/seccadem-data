#!/usr/bin/env python3
"""Builds the Arabic Quran text, search text and metadata from Tanzil.

Source: Tanzil Project (https://tanzil.net), Creative Commons Attribution 3.0.
The text is copied verbatim (Tanzil does not allow changes) and the Tanzil
copyright block is kept inside every output file.

Outputs (quran/v1/):
  quran_uthmani.json.gz  Uthmani text (pause marks + sajdah signs, Madina style)
  quran_search.json.gz   "simple-clean" text (no diacritics), for search only
  quran_meta.json        114 surahs + juz / hizb quarter / page / sajdah / manzil
                         boundaries + localized surah names (QuranEnc)

Usage: python scripts/quran/build_tanzil.py [--offline]
  --offline  reuse build/quran_raw/* instead of downloading again.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quran_common import (  # noqa: E402
    AYAH_COUNT,
    CACHE_DIR,
    JUZ_COUNT,
    PAGE_COUNT,
    QURAN_DIR,
    SURAH_COUNT,
    fetch,
    fetch_json,
    write_gz_json,
    write_json,
)

TANZIL_DOWNLOAD = "https://tanzil.net/pub/download/index.php"
# Same options as the tanzil.net/download form defaults: pause marks, sajdah
# signs, superscript alef, tatweel. No rub-el-hizb sign (boundaries live in meta).
UTHMANI_QUERY = "quranType=uthmani&outType=xml&marks=true&sajdah=true&alef=true&tatweel=true&agree=true"
CLEAN_QUERY = "quranType=simple-clean&outType=xml&agree=true"
META_URL = "https://tanzil.net/res/text/metadata/quran-data.xml"
SOWAR_NAMES_URL = "https://quranenc.com/api/v1/translations/sowar_names?iso_code={lang}"

UI_LANGS = ["ar", "bn", "de", "en", "es", "fa", "fr", "hi", "id", "ms", "nl", "ru", "tr", "ur"]

# Known per-surah ayah counts (Hafs, Kufan count) used as an independent check.
EXPECTED_AYAHS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53,
    89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12,
    12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26,
    30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]

# Verbatim reference ayahs (Tanzil Uthmani 1.1 with pause marks) for spot checks.
FATIHA_1 = (
    "بِسْمِ ٱللَّهِ "
    "ٱلرَّحْمَـٰنِ "
    "ٱلرَّحِيمِ"
)
IKHLAS = [
    "قُلْ هُوَ ٱللَّهُ "
    "أَحَدٌ",
    "ٱللَّهُ ٱلصَّمَدُ",
    "لَمْ يَلِدْ وَلَمْ "
    "يُولَدْ",
    "وَلَمْ يَكُن لَّهُۥ "
    "كُفُوًا أَحَدٌۢ",
]


def cached(name: str, url: str, offline: bool) -> bytes:
    path = CACHE_DIR / name
    if offline and path.exists():
        return path.read_bytes()
    data = fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def copyright_block(xml_bytes: bytes) -> str:
    text = xml_bytes.decode("utf-8")
    match = re.search(r"<!--(.*?)-->", text, re.S)
    if not match:
        raise SystemExit("Tanzil copyright block not found")
    return match.group(1).strip("\n")


def parse_text(xml_bytes: bytes) -> tuple[list[list[str]], list[str | None]]:
    root = ET.fromstring(xml_bytes)
    suras: list[list[str]] = []
    bismillah: list[str | None] = []
    for sura in root.findall("sura"):
        ayahs = sura.findall("aya")
        suras.append([a.attrib["text"] for a in ayahs])
        bismillah.append(ayahs[0].attrib.get("bismillah"))
    return suras, bismillah


def parse_meta(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)

    def rows(group: str, item: str, fields: tuple[str, ...]) -> list[dict]:
        out = []
        for node in root.find(group).findall(item):
            out.append({f: int(node.attrib[f]) for f in fields})
        return out

    suras = []
    for node in root.find("suras").findall("sura"):
        a = node.attrib
        suras.append(
            {
                "number": int(a["index"]),
                "ayahs": int(a["ayas"]),
                "start": int(a["start"]),
                "nameArabic": a["name"],
                "nameTransliterated": a["tname"],
                "nameEnglish": a["ename"],
                "revelation": "meccan" if a["type"] == "Meccan" else "medinan",
                "revelationOrder": int(a["order"]),
                "rukus": int(a["rukus"]),
            }
        )
    sajdas = []
    for node in root.find("sajdas").findall("sajda"):
        a = node.attrib
        sajdas.append({"surah": int(a["sura"]), "ayah": int(a["aya"]), "type": a["type"]})

    def ref(r: dict) -> dict:
        return {"surah": r["sura"], "ayah": r["aya"]}

    return {
        "license": root.attrib.get("license"),
        "copyright": root.attrib.get("copyright"),
        "surahs": suras,
        "juz": [ref(r) for r in rows("juzs", "juz", ("index", "sura", "aya"))],
        "hizbQuarters": [ref(r) for r in rows("hizbs", "quarter", ("index", "sura", "aya"))],
        "manzil": [ref(r) for r in rows("manzils", "manzil", ("index", "sura", "aya"))],
        "pages": [ref(r) for r in rows("pages", "page", ("index", "sura", "aya"))],
        "sajdas": sajdas,
    }


def verify(suras, bismillah, clean, meta) -> None:
    errors = []
    if len(suras) != SURAH_COUNT:
        errors.append(f"surah count {len(suras)}")
    total = sum(len(s) for s in suras)
    if total != AYAH_COUNT:
        errors.append(f"ayah count {total}")
    for i, (s, expected) in enumerate(zip(suras, EXPECTED_AYAHS), start=1):
        if len(s) != expected:
            errors.append(f"surah {i}: {len(s)} ayahs, expected {expected}")
        if meta["surahs"][i - 1]["ayahs"] != expected:
            errors.append(f"meta surah {i} ayahs mismatch")
        if len(clean[i - 1]) != len(s):
            errors.append(f"search text surah {i} ayah count mismatch")
        if any(not a.strip() for a in s):
            errors.append(f"surah {i}: empty ayah")
    if suras[0][0] != FATIHA_1:
        errors.append("Fatiha 1:1 differs")
    if suras[111] != IKHLAS:
        errors.append("Ikhlas differs")
    if bismillah[0] is not None or bismillah[8] is not None:
        errors.append("bismillah attribute present on surah 1 or 9")
    if sum(1 for b in bismillah if b) != 112:
        errors.append("expected 112 bismillah attributes")
    if len(meta["juz"]) != JUZ_COUNT:
        errors.append("juz count")
    if len(meta["pages"]) != PAGE_COUNT:
        errors.append("page count")
    if len(meta["hizbQuarters"]) != 240:
        errors.append("hizb quarter count")
    if len(meta["sajdas"]) != 15:
        errors.append("sajda count")
    sajda_sign = "۩"
    signs = sum(a.count(sajda_sign) for s in suras for a in s)
    if signs != 15:
        errors.append(f"sajdah signs in text: {signs}")
    if errors:
        raise SystemExit("Tanzil verification failed:\n  " + "\n  ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    uthmani_xml = cached("tanzil_uthmani.xml", f"{TANZIL_DOWNLOAD}?{UTHMANI_QUERY}", args.offline)
    clean_xml = cached("tanzil_simple_clean.xml", f"{TANZIL_DOWNLOAD}?{CLEAN_QUERY}", args.offline)
    meta_xml = cached("tanzil_quran_data.xml", META_URL, args.offline)

    suras, bismillah = parse_text(uthmani_xml)
    clean, _ = parse_text(clean_xml)
    meta = parse_meta(meta_xml)
    verify(suras, bismillah, clean, meta)

    version_match = re.search(r"Version ([0-9.]+)", copyright_block(uthmani_xml))
    version = version_match.group(1) if version_match else None

    names: dict[str, dict[str, str]] = {}
    for lang in UI_LANGS:
        raw = cached(f"sowar_names_{lang}.json", SOWAR_NAMES_URL.format(lang=lang), args.offline)
        data = json.loads(raw.decode("utf-8"))
        names[lang] = {str(k): v for k, v in data.items()}
        if len(names[lang]) != SURAH_COUNT:
            raise SystemExit(f"sowar_names {lang}: {len(names[lang])} entries")
    for s in meta["surahs"]:
        s["names"] = {lang: names[lang][str(s["number"])] for lang in UI_LANGS}

    attribution = {
        "source": "Tanzil Project",
        "url": "https://tanzil.net",
        "license": "CC BY 3.0",
        "licenseUrl": "https://creativecommons.org/licenses/by/3.0/",
        "note": "Verbatim copy; changing the text is not allowed. Check updates at https://tanzil.net/updates/",
    }

    uthmani = {
        "format": 1,
        "edition": "uthmani",
        "version": version,
        "options": {"pauseMarks": True, "sajdahSigns": True, "superscriptAlef": True, "tatweel": True, "rubElHizb": False},
        **attribution,
        "copyright": copyright_block(uthmani_xml),
        "bismillah": bismillah,
        "surahs": suras,
    }
    search = {
        "format": 1,
        "edition": "simple-clean",
        "version": version,
        **attribution,
        "copyright": copyright_block(clean_xml),
        "surahs": clean,
    }
    meta_out = {
        "format": 1,
        "metadataSource": {
            "source": "Tanzil Project",
            "url": META_URL,
            "license": "CC BY 3.0",
            "copyright": meta.pop("copyright"),
        },
        "surahNamesSource": {
            "source": "QuranEnc.com",
            "url": "https://quranenc.com/api/v1/translations/sowar_names",
        },
        "counts": {"surahs": SURAH_COUNT, "ayahs": AYAH_COUNT, "pages": PAGE_COUNT, "juz": JUZ_COUNT},
        **{k: v for k, v in meta.items() if k != "license"},
    }

    write_gz_json(QURAN_DIR / "quran_uthmani.json.gz", uthmani)
    write_gz_json(QURAN_DIR / "quran_search.json.gz", search)
    write_json(QURAN_DIR / "quran_meta.json", meta_out, pretty=False)
    print(f"Tanzil {version}: {sum(len(s) for s in suras)} ayahs, {len(suras)} surahs - OK")


if __name__ == "__main__":
    main()
