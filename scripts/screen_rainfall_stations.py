"""Screen nearby Environment Agency daily-rainfall series for usable coverage."""

from __future__ import annotations

import csv
import json
import math
import time
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "rainfall_station_screen.csv"
FLOW_LAT = 52.827341
FLOW_LONG = 0.847451
START = date(1992, 1, 1)
END = date(2023, 12, 31)
EXPECTED_DAYS = (END - START).days + 1
SEARCH_URL = (
    "https://environment.data.gov.uk/hydrology/id/stations.json?"
    "lat=52.827341&long=0.847451&dist=30&observedProperty=rainfall&_limit=100"
)


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "wensum-drought-study/0.1"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def distance_km(lat: float, long: float) -> float:
    radius = 6371.0088
    lat1, lat2 = math.radians(FLOW_LAT), math.radians(lat)
    delta_lat = lat2 - lat1
    delta_long = math.radians(long - FLOW_LONG)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_long / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(haversine))


def main() -> None:
    stations = fetch_json(SEARCH_URL).get("items", [])
    rows = []
    for station in stations:
        measures = [
            measure["@id"].rsplit("/", 1)[-1]
            for measure in station.get("measures", [])
            if measure["@id"].endswith("rainfall-t-86400-mm-qualified")
        ]
        if len(measures) != 1:
            continue
        measure_id = measures[0]
        readings_url = (
            "https://environment.data.gov.uk/hydrology/id/measures/"
            f"{measure_id}/readings.json?_limit=100000"
        )
        readings = fetch_json(readings_url).get("items", [])
        selected = [
            item for item in readings if START <= date.fromisoformat(item["date"]) <= END
        ]
        numeric = [item for item in selected if isinstance(item.get("value"), (int, float))]
        accepted = [
            item
            for item in numeric
            if item.get("completeness") == "Complete"
            and item.get("quality") in {"Good", "Estimated"}
        ]
        rows.append(
            {
                "station": station.get("label"),
                "station_guid": station.get("stationGuid"),
                "wiski_id": station.get("wiskiID"),
                "distance_from_fakenham_km": round(
                    distance_km(float(station["lat"]), float(station["long"])), 3
                ),
                "date_opened": station.get("dateOpened"),
                "measure_id": measure_id,
                "record_start": readings[0].get("date") if readings else "",
                "record_end": readings[-1].get("date") if readings else "",
                "selected_period_rows": len(selected),
                "numeric_coverage_pct": round(100 * len(numeric) / EXPECTED_DAYS, 3),
                "accepted_coverage_pct": round(100 * len(accepted) / EXPECTED_DAYS, 3),
                "accepted_days": len(accepted),
            }
        )
        time.sleep(0.05)

    rows.sort(key=lambda row: (-float(row["accepted_coverage_pct"]), float(row["distance_from_fakenham_km"])))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Screened {len(rows)} nearby daily-rainfall series; best accepted coverage is {rows[0]['accepted_coverage_pct']}%.")


if __name__ == "__main__":
    main()

