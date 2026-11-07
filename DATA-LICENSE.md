# Data licensing

The MIT license in `LICENSE` covers the code only. Each data set in this
repository has its own terms, listed below. If a data set is not listed as
licensed by Seccadem, **no license is granted by Seccadem** and the rights of
the original source apply.

| Data | Path | Origin | Terms |
|---|---|---|---|
| City index and city list | `prayer_cities_index.json`, `cities.json` | Compiled by Seccadem | CC BY 4.0, attribution "Seccadem" |
| Calculation method table | `methods.json` | Compiled by Seccadem from published method parameters | CC BY 4.0, attribution "Seccadem" |
| Prayer times, source `diyanet` | `v1/TR/**`, `v1/CY/**` | Times published by the Presidency of Religious Affairs of Türkiye (Diyanet), collected through a third-party mirror | **Not licensed by Seccadem.** Rights remain with the original publisher. Provided for interoperability of the Seccadem app only |
| Prayer times, source `aladhan` | `v1/**` (files with `"source": "aladhan"`) | Calculated by the AlAdhan API | **Not licensed by Seccadem.** AlAdhan terms apply |
| Prayer times, source `jakim` | `v1/MY/**` | Published by JAKIM (e-solat.gov.my) | **Not licensed by Seccadem.** JAKIM terms apply |
| Prayer times, source `kemenag` | `v1/ID/**` | Published by Kemenag, collected through api.myquran.com | **Not licensed by Seccadem.** Original publisher's terms apply |
| Qur'an Arabic text | `quran/v1/quran_uthmani.json.gz`, `quran/v1/quran_search.json.gz` | Tanzil Project (https://tanzil.net), Uthmani and Simple Clean v1.1 | CC BY 3.0. Verbatim copy, changing the text is not allowed; name Tanzil Project and link to tanzil.net; the Tanzil copyright block is kept inside each file |
| Qur'an metadata | `quran/v1/quran_meta.json` | Tanzil Project `quran-data.xml` (surahs, juz, hizb, manzil, pages, sajdas); localised surah names from QuranEnc.com (`translations/sowar_names`) | Tanzil metadata: CC BY 3.0, attribution "Tanzil Project". Surah names: QuranEnc.com terms (see Qur'an translations) |
| Qur'an translations | `quran/v1/translations/*.json.gz`, `manifest.json` | QuranEnc.com, one file per translation (list below) | **Not licensed by Seccadem.** QuranEnc.com terms: no modification, addition or deletion; name the publisher and QuranEnc.com; state and keep the version number; follow new versions; no inappropriate ads next to the text |
| Adhan recordings | `audio/adhan/*.mp3` | Wikimedia Commons: `istanbul_commons_cc0.mp3` (Viceskeeni2), `konya_vandervaart_ccby3.mp3` (Frans van der Vaart), `malmo_fajr_icm_ccby3.mp3` (Islamic Center Malmö) | Istanbul: CC0 1.0. Konya and Malmö: CC BY 3.0, credit the author, note the changes (audio extracted, normalised, MP3). Details: [`audio/adhan/LICENSE.md`](audio/adhan/LICENSE.md) |

## Qur'an translations (QuranEnc.com)

Each file is stored exactly as returned by the QuranEnc API
(`scripts/quran/fetch_quranenc.py`); `manifest.json` records translator,
publisher, version, date and SHA-256. `scripts/quran/check_quranenc_versions.py`
runs monthly and reports new versions. Translations that publish no version
number are not shipped (QuranEnc term 3).

| Language | Key | Translator | Publisher | Version |
|---|---|---|---|---|
| bn | [`bengali_zakaria`](https://quranenc.com/en/browse/bengali_zakaria) | Dr. Abu Bakr Muhammad Zakaria | King Fahd Glorious Qur'an Printing Complex | 1.1.1 (2021-05-22) |
| de | [`german_rwwad`](https://quranenc.com/en/browse/german_rwwad) | Rowwad Translation Center | Rowwad Translation Center | 1.0.16 (2026-11-01) |
| en | [`english_rwwad`](https://quranenc.com/en/browse/english_rwwad) | Rowwad Translation Center | Rowwad Translation Center | 1.0.20 (2026-10-20) |
| es | [`spanish_montada_eu`](https://quranenc.com/en/browse/spanish_montada_eu) | Noor International Center | Noor International Center | 1.0.1 (2025-06-25) |
| fa | [`persian_ih`](https://quranenc.com/en/browse/persian_ih) | Rowwad Translation Center | Rowwad Translation Center | 1.1.3 (2026-02-23) |
| fr | [`french_montada`](https://quranenc.com/en/browse/french_montada) | Dr. Nabil Rudwan | Noor International Center | 1.0.0 (2025-06-24) |
| hi | [`hindi_omari`](https://quranenc.com/en/browse/hindi_omari) | Azizul Haq Al-Omari | QuranEnc.com | 1.1.5 (2025-08-05) |
| id | [`indonesian_affairs`](https://quranenc.com/en/browse/indonesian_affairs) | Indonesian Ministry of Religious Affairs | Indonesian Ministry of Religious Affairs | 1.0.1 (2025-06-23) |
| ms | [`malay_basumayyah`](https://quranenc.com/en/browse/malay_basumayyah) | Abdullah Basumayyah | QuranEnc.com | 1.0.0 (2021-01-27) |
| nl | [`dutch_center`](https://quranenc.com/en/browse/dutch_center) | Dutch Islamic Center | Dutch Islamic Center / Rowwad Translation Center | 2.0.10 (2025-11-19) |
| ru | [`russian_rwwad`](https://quranenc.com/en/browse/russian_rwwad) | Rowwad Translation Center | Rowwad Translation Center | 1.0.1 (2026-03-29) |
| tr | [`turkish_rwwad`](https://quranenc.com/en/browse/turkish_rwwad) | Rowwad Translation Center | Rowwad Translation Center | 1.0.4 (2025-09-28) |
| ur | [`urdu_junagarhi`](https://quranenc.com/en/browse/urdu_junagarhi) | Muhammad Ibrahim Junagarhi | Rowwad Translation Center (supervision) | 1.1.3 (2025-08-13) |

## Phase-out

The Seccadem app is moving to on-device calculation (the MIT-licensed `adhan`
library with each country's official method parameters). Third-party prayer
time files will be removed from this repository once app versions that depend
on them are no longer supported. New third-party data will not be added.

## Content added in the future

Any future data set must state its source, licence, version and required
attribution in this file before it is published. Only public-domain data,
openly licensed data that allows commercial use, or data whose terms allow
redistribution without separate permission may be added.

## Contact

If you are a rights holder and want a file removed, open an issue in this
repository and it will be removed.
