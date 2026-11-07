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
