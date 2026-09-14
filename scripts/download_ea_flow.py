"""Download the qualified daily mean-flow record for the Wensum at Fakenham."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROVENANCE_DIR = ROOT / "data" / "provenance"

STATION_ID = "34011"
STATION_GUID = "0b351234-b489-40c7-a846-def749d91f74"
MEASURE_ID = f"{STATION_GUID}-flow-m-86400-m3s-qualified"
BASE_URL = "https://environment.data.gov.uk/hydrology"
URLS = {
    "station": f"{BASE_URL}/id/stations.json?search=Fakenham",
    "measure": f"{BASE_URL}/id/measures/{MEASURE_ID}.json",
    "readings": f"{BASE_URL}/id/measures/{MEASURE_ID}/readings.json?_limit=100000",
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "wensum-drought-study/0.1"})
    with urlopen(request, timeout=120) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status} for {url}")
        return response.read()


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def parse(content: bytes, label: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"The {label} response was not valid JSON") from error


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    payloads = {name: fetch(url) for name, url in URLS.items()}
    documents = {name: parse(content, name) for name, content in payloads.items()}

    station_matches = [
        item
        for item in documents["station"].get("items", [])
        if item.get("nrfaStationID") == STATION_ID
    ]
    if len(station_matches) != 1:
        raise RuntimeError(f"Expected one NRFA {STATION_ID} station; found {len(station_matches)}")
    station = station_matches[0]
    if station.get("stationGuid") != STATION_GUID or station.get("riverName") != "River Wensum":
        raise RuntimeError("The station identity did not match the expected Fakenham gauge")

    measure_items = documents["measure"].get("items", [])
    if len(measure_items) != 1:
        raise RuntimeError(f"Expected one measure description; found {len(measure_items)}")
    measure = measure_items[0]
    checks = {
        "notation": MEASURE_ID,
        "parameter": "flow",
        "period": 86400,
        "periodName": "daily",
        "valueType": "mean",
        "unitName": "m3/s",
    }
    for field, expected in checks.items():
        if measure.get(field) != expected:
            raise RuntimeError(
                f"Measure field {field!r} was {measure.get(field)!r}, expected {expected!r}"
            )
    if measure.get("observationType", {}).get("label") != "Qualified":
        raise RuntimeError("The selected measure is not labelled as qualified")

    readings = documents["readings"].get("items", [])
    if not readings:
        raise RuntimeError("The readings response contained no observations")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        write_bytes(RAW_DIR / f"fakenham_{name}.json", content)

    provenance = {
        "retrieved_at_utc": retrieved_at,
        "publisher": documents["readings"].get("meta", {}).get("publisher"),
        "licence_name": documents["readings"].get("meta", {}).get("licenseName"),
        "licence_url": documents["readings"].get("meta", {}).get("license"),
        "api_version": documents["readings"].get("meta", {}).get("version"),
        "station": {
            "label": station.get("label"),
            "river_name": station.get("riverName"),
            "nrfa_station_id": station.get("nrfaStationID"),
            "ea_station_reference": station.get("stationReference"),
            "wiski_id": station.get("wiskiID"),
            "station_guid": station.get("stationGuid"),
            "date_opened": station.get("dateOpened"),
            "latitude": station.get("lat"),
            "longitude": station.get("long"),
        },
        "measure": {
            "id": MEASURE_ID,
            "label": measure.get("label"),
            "parameter": measure.get("parameter"),
            "period_seconds": measure.get("period"),
            "value_type": measure.get("valueType"),
            "unit": measure.get("unitName"),
            "observation_type": measure.get("observationType", {}).get("label"),
        },
        "record": {
            "row_count": len(readings),
            "first_date": readings[0].get("date"),
            "last_date": readings[-1].get("date"),
        },
        "requests": {
            name: {
                "url": URLS[name],
                "raw_file": f"data/raw/fakenham_{name}.json",
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for name, content in payloads.items()
        },
    }
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    output = PROVENANCE_DIR / "fakenham_daily_mean_flow.json"
    output.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(
        f"Downloaded {len(readings):,} qualified daily-flow rows "
        f"({readings[0].get('date')} to {readings[-1].get('date')})."
    )


if __name__ == "__main__":
    main()

