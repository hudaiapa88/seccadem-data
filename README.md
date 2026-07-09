# Seccadem Data

Offline prayer times data for 65+ Islamic countries, sourced from Diyanet (Turkey), Aladhan, JAKIM (Malaysia), and Kemenag (Indonesia).

## Usage

### Raw GitHub URL
```
https://raw.githubusercontent.com/seccadem/seccadem-data/main/v1/TR/istanbul/2026-07.json
```

### jsDelivr CDN (faster, cached)
```
https://cdn.jsdelivr.net/gh/seccadem/seccadem-data@main/v1/TR/istanbul/2026-07.json
```

## Schema

See [`schema.json`](schema.json) for the full JSON schema.

```json
{
  "country": "TR",
  "city": "istanbul",
  "source": "diyanet",
  "method": "turkey",
  "madhab": "shafi",
  "year": 2026,
  "month": 7,
  "timezone": "Europe/Istanbul",
  "coordinates": {"lat": 41.0082, "lon": 28.9784},
  "adjustments": {"sunrise": -7, "dhuhr": 5, "asr": 4, "maghrib": 6, "isha": -1},
  "days": [
    {
      "date": "2026-07-01",
      "fajr": "03:33",
      "sunrise": "05:34",
      "dhuhr": "13:09",
      "asr": "16:58",
      "maghrib": "20:36",
      "isha": "22:31"
    }
  ]
}
```

## Data Sources

| Source | Countries | Method |
|--------|-----------|--------|
| Diyanet (ezanvakti.emushaf.net) | TR, CY | Ground truth API |
| Aladhan (api.aladhan.com) | 63 countries | Calculation method per country |
| JAKIM (e-solat.gov.my) | MY | Official Malaysian source |
| Kemenag (api.myquran.com) | ID | Official Indonesian source |

## Languages Covered

This data covers Islamic countries that speak the 14 languages supported by the Seccadem app:

`tr, en, ar, de, es, fr, id, ms, nl, ru, bn, fa, hi, ur`

## License

MIT
