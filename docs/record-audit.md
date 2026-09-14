# Initial flow-record audit

## Result

The Environment Agency Hydrology API returned 22,029 qualified daily mean-flow records for the River Wensum at Fakenham, spanning 1 May 1966 to 12 September 2026. The series contains no duplicate dates. There are 21 dates absent from the returned date index and 181 returned dates with no numeric value. Units, period, statistic and observation type were checked against the measure metadata: daily mean flow in m³/s, labelled **Qualified**.

Quality flags are not uniform. The download contains 20,611 `Good`, 619 `Estimated`, 99 `Suspect`, 519 `Unchecked` and 181 `Missing` records. An estimated value is not the same as a missing value, so the audit reports three separate measures:

- **numeric coverage** — any returned numeric flow;
- **accepted coverage** — complete records flagged `Good` or `Estimated`;
- **good-only coverage** — the stricter subset used for sensitivity testing.

The proposed 1991–2020 threshold reference period has a complete daily date index. Accepted coverage is 96.797%; good-only coverage is 94.205%. Its final suitability is determined from the distribution of rejected and missing values, not from row count alone. Annual and water-year tables in `outputs/` retain each coverage definition.

## Analysis boundary

The initial event analysis will end on 31 December 2023. Most values from 2024 onward are `Unchecked`, the 2025 date index has an 18-day gap, and 2026 is an incomplete current year. These recent observations can be revisited after the Environment Agency quality status changes, but they will not be mixed into the first comparison of completed periods.

Earlier years with missing, suspect or incomplete records will be screened explicitly. Events adjacent to gaps will be marked as censored rather than assigned artificial start dates, end dates or deficit volumes. Results will be recalculated both with accepted values and with good-only values to show whether estimates affect the main conclusions.

## Interpretation constraint

This audit establishes data coverage, not hydrometric naturalness. NRFA identifies an unquantified groundwater-abstraction influence at low flows. Consequently, temporal changes in the gauge record cannot be attributed to climate without additional evidence or a suitable naturalised-flow series.
