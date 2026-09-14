# Data sources and station choice

## Selected site

**River Wensum at Fakenham — NRFA station 34011**

The National River Flow Archive describes this as a 161.9 km² Chalk catchment with mainly permeable soils and a muted flood response. It is an NHMP index site and belongs to the UK Benchmark Network, which makes its metadata unusually useful for interpreting long records. The benchmark assessment nevertheless assigns low flows a caution score because groundwater abstraction is present but its influence has not been quantified. That qualification is central to the study: results will describe the observed flow series and will not be presented as an unmodified climate signal.

Station information: https://nrfa.ceh.ac.uk/data/station/info/34011  
Benchmark and trends information: https://nrfa.ceh.ac.uk/data/station/trends/34011

## Primary time series

The preferred source is the Environment Agency Hydrology Data API:

https://environment.data.gov.uk/hydrology/doc/reference

The API provides historic and recent river flow, level, rainfall and groundwater observations. It includes daily mean flow in m³/s, distinguishes qualified from measured observations, exposes station and measure metadata, and returns JSON or CSV. API responses identify the Environment Agency as publisher and Open Government Licence 3.0 as the applicable licence.

The download script will first resolve the Hydrology API station whose `nrfaStationID` is `34011`, select a qualified daily mean-flow measure, and then request only the required period. The raw response metadata, request URL, retrieval timestamp and a file checksum will be recorded alongside the download.

Licence: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

## Secondary checks

NRFA station metadata will be used to verify catchment area, station history, known artificial influences and documented gaps. The NRFA provides full-period daily flows, but download requires acceptance of the NRFA data licence. Those values will not be copied into the repository unless that licence has been reviewed and the repository treatment is demonstrably compliant.

NRFA access guidance: https://nrfa.ceh.ac.uk/data/use-nrfa-data/data-access

## Hydrological context

Environment Agency water-situation reporting combines rainfall, soil moisture deficit, river flows, groundwater levels and reservoir storage when assessing water resources. The single-station analysis here therefore represents hydrological drought at one gauge, not the operational drought status of an Anglian Water resource zone.

National water-situation reports: https://www.gov.uk/government/publications/water-situation-national-monthly-reports-for-england-2026  
Drought-management framework: https://www.gov.uk/government/publications/drought-management-for-england/drought-how-it-is-managed-in-england

## Regional precipitation context

The Met Office HadUKP South East England precipitation series (HadSEEP) supplies daily regional totals from 1931. It is freely downloadable under the Open Government Licence. The analysis uses values only through 31 December 2023 and records the source URL, retrieval time and SHA-256 checksum in `data/provenance/hydroclimate_context.json`.

HadSEEP is not a Wensum catchment rainfall series. It is retained as a broad, long-record precipitation comparator because the local Environment Agency gauges screened for 1992–2023 had insufficient accepted coverage: the Fakenham gauge supplied 29.6%, and no screened daily series exceeded 37.1%. Those gaps were not infilled. Catchment-average HadUK-Grid precipitation would be a stronger spatial representation, but full-resolution archive access requires a registered CEDA account; it is therefore identified as a possible later refinement rather than silently substituted.

Dataset and documentation: https://www.metoffice.gov.uk/hadobs/hadukp/  
Licence terms: https://www.metoffice.gov.uk/hadobs/hadukp/terms_and_conditions.html  
Citation: Alexander, L. V. and Jones, P. D. (2001), *Updated precipitation series for the U.K. and discussion of recent extremes*, Atmospheric Science Letters.

## Groundwater context

The nearby Environment Agency borehole labelled `Great Ryburg` (WISKI `TF92_671`) monitors the Chalk aquifer approximately 4.65 km from the Fakenham river gauge. Its qualified dipped-level measure is reported in metres above Ordnance Datum. The downloaded record contains 732 irregular readings from September 1952 to May 2024; the event analysis accepts 696 `Good` or `Estimated` observations through 2023. The median interval between accepted readings is 28 days, but longer gaps occur.

Station record: https://environment.data.gov.uk/hydrology/id/stations/995ca9a8-3dac-4e18-be65-9273a7bb0390  
Licence: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

The borehole is used as a nearby groundwater indicator, not as a catchment-wide groundwater level. No groundwater value is inferred when an accepted reading is more than 45 days from a drought start.

## Quality gates before analysis

- Confirm that the API station and measure resolve to Fakenham and daily mean flow.
- Prefer qualified observations and document any period available only as measured data.
- Quantify missingness by year and inspect runs of consecutive missing days.
- Confirm units and timestamps from API metadata rather than assuming them.
- Keep the unaltered response outside version control; publish only a retrieval script, provenance record and derived non-sensitive results.
- Treat abstraction, manual gate operation and changes in gauging performance as potential non-climatic influences.

Sources checked 14 September 2026.
