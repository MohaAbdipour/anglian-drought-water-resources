"""Download regional precipitation and nearby Chalk groundwater context data."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROVENANCE_DIR = ROOT / "data" / "provenance"

GROUNDWATER_GUID = "995ca9a8-3dac-4e18-be65-9273a7bb0390"
GROUNDWATER_MEASURE = f"{GROUNDWATER_GUID}-gw-dipped-i-mAOD-qualified"
URLS = {
    "hadseep_daily": (
        "https://hadleyserver.metoffice.gov.uk/hadobs/hadukp/data/daily/"
        "HadSEEP_daily_totals.txt"
    ),
    "groundwater_station": (
        "https://environment.data.gov.uk/hydrology/id/stations/"
        f"{GROUNDWATER_GUID}.json"
    ),
    "groundwater_measure": (
        "https://environment.data.gov.uk/hydrology/id/measures/"
        f"{GROUNDWATER_MEASURE}.json"
    ),
    "groundwater_readings": (
        "https://environment.data.gov.uk/hydrology/id/measures/"
        f"{GROUNDWATER_MEASURE}/readings.json?_limit=100000"
    ),
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


def main() -> None:
    payloads = {name: fetch(url) for name, url in URLS.items()}
    rainfall_text = payloads["hadseep_daily"].decode("utf-8")
    rainfall_rows = [line for line in rainfall_text.splitlines() if line[:4].isdigit()]
    if not rainfall_text.startswith("Daily South East England precipitation (mm)."):
        raise RuntimeError("The HadSEEP response header was not recognised")
    if len(rainfall_rows) < 30_000:
        raise RuntimeError("The HadSEEP response was unexpectedly short")

    station_document = json.loads(payloads["groundwater_station"])
    station_items = station_document.get("items", [])
    if len(station_items) != 1:
        raise RuntimeError("Expected one groundwater station description")
    station = station_items[0]
    if station.get("stationGuid") != GROUNDWATER_GUID or station.get("aquifer") != "Chalk":
        raise RuntimeError("The groundwater station identity or aquifer did not match")

    measure_document = json.loads(payloads["groundwater_measure"])
    measure_items = measure_document.get("items", [])
    if len(measure_items) != 1:
        raise RuntimeError("Expected one groundwater measure description")
    measure = measure_items[0]
    if measure.get("unitName") != "mAOD" or measure.get("observationType", {}).get("label") != "Qualified":
        raise RuntimeError("The groundwater unit or qualification did not match")

    readings_document = json.loads(payloads["groundwater_readings"])
    readings = readings_document.get("items", [])
    if not readings:
        raise RuntimeError("The groundwater response contained no readings")

    raw_names = {
        "hadseep_daily": "hadseep_daily.txt",
        "groundwater_station": "great_ryburg_station.json",
        "groundwater_measure": "great_ryburg_measure.json",
        "groundwater_readings": "great_ryburg_readings.json",
    }
    for name, content in payloads.items():
        write_bytes(RAW_DIR / raw_names[name], content)

    provenance = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "rainfall": {
            "dataset": "HadUKP South East England precipitation (HadSEEP)",
            "publisher": "Met Office Hadley Centre",
            "unit": "mm",
            "licence_name": "Open Government Licence",
            "licence_page": "https://www.metoffice.gov.uk/hadobs/hadukp/terms_and_conditions.html",
            "citation": (
                "Alexander, L.V. and Jones, P.D. (2001), Updated precipitation series "
                "for the U.K. and discussion of recent extremes, Atmospheric Science Letters."
            ),
            "row_count": len(rainfall_rows),
            "first_date": rainfall_rows[0].split()[0],
            "last_date": rainfall_rows[-1].split()[0],
            "scope_note": "Regional areal precipitation context; not catchment-average rainfall.",
        },
        "groundwater": {
            "publisher": readings_document.get("meta", {}).get("publisher"),
            "licence_name": readings_document.get("meta", {}).get("licenseName"),
            "licence_url": readings_document.get("meta", {}).get("license"),
            "api_version": readings_document.get("meta", {}).get("version"),
            "station_label_as_published": station.get("label"),
            "station_guid": station.get("stationGuid"),
            "wiski_id": station.get("wiskiID"),
            "aquifer": station.get("aquifer"),
            "borehole_depth_m": station.get("boreholeDepth"),
            "datum_mAOD": station.get("datum"),
            "date_opened": station.get("dateOpened"),
            "latitude": station.get("lat"),
            "longitude": station.get("long"),
            "measure_id": GROUNDWATER_MEASURE,
            "unit": measure.get("unitName"),
            "observation_type": measure.get("observationType", {}).get("label"),
            "row_count": len(readings),
            "first_date": readings[0].get("date"),
            "last_date": readings[-1].get("date"),
        },
        "requests": {
            name: {
                "url": URLS[name],
                "raw_file": f"data/raw/{raw_names[name]}",
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for name, content in payloads.items()
        },
    }
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    (PROVENANCE_DIR / "hydroclimate_context.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Downloaded {len(rainfall_rows):,} regional rainfall days and "
        f"{len(readings):,} Chalk groundwater readings."
    )


if __name__ == "__main__":
    main()

