# Low-flow droughts in the upper River Wensum

This study examines how the duration and accumulated flow deficit of hydrological droughts have varied at the River Wensum at Fakenham (NRFA station 34011). The catchment is a useful Anglian case because it is groundwater influenced and has a long flow record, while the documented influence of groundwater abstraction makes interpretation of low-flow changes scientifically non-trivial.

## Question

How have observed low-flow drought characteristics at Fakenham varied through the available record, and how sensitive are the identified events to the choice of low-flow threshold?

The analysis remains deliberately narrow: one gauging station, observed daily mean river flow, regional precipitation context and one nearby Chalk borehole. It distinguishes a change in the gauged record from a change caused by climate; the latter cannot be inferred without accounting for abstraction and other artificial influences.

## Analytical design

![Study workflow from observations to qualified inference](docs/figures/study_workflow.svg)

1. Retrieve qualified daily mean flow from the Environment Agency Hydrology API and retain the request metadata and checksum.
2. Audit completeness by calendar year and water year before calculating drought statistics.
3. Define events using a 1991–2020 Q90 threshold, with Q80 and Q95 sensitivity cases. Here Q90 is the flow equalled or exceeded on 90% of accepted reference-period days.
4. Calculate event duration, minimum flow and cumulative deficit volume, and test the effect of pooling brief interruptions.
5. Compare frequency and severity across equal record periods after applying an annual coverage screen and quantify sampling uncertainty using a block bootstrap.
6. Compare event onset with seasonally matched regional precipitation and nearby Chalk groundwater levels while retaining the spatial and temporal limitations of those indicators.

## Record and quality control

The Environment Agency qualified daily mean-flow record has been retrieved and its identity, units, temporal coverage and quality flags checked. The analysis uses completed observations through 2023 and distinguishes accepted (`Good` or `Estimated`) values from a good-only sensitivity case. The audit is summarised in [docs/record-audit.md](docs/record-audit.md).

## Initial evidence

The 1991–2020 flow-duration curve gives Q90 = 0.274 m³/s. A good-only sensitivity calculation gives 0.273 m³/s, indicating that estimated observations have little effect on the selected threshold. The event analysis identifies pronounced low-flow sequences in 1976, 1991–92, 1996, 2011 and 2022, but incomplete years and the documented abstraction influence prevent a simple climatic attribution.

![Annual Q90 low-flow exposure and deficit](docs/figures/annual_q90_deficit.png)

The calculations, sensitivity results and interpretation limits are set out in [docs/preliminary-findings.md](docs/preliminary-findings.md).

## Comparison through time

Across three equal 19-year segments, mean annual days below Q90 were 12.8, 31.4 and 30.4 after excluding years with less than 95% accepted coverage. The latest-minus-earliest difference is +15.7 days per year, but its three-year block-bootstrap interval spans −7.4 to +40.8 days. The record therefore suggests more frequent low-flow exposure after the mid-1980s without establishing a clear early-to-late difference.

![Coverage-screened comparison across three periods](docs/figures/period_comparison.png)

See [docs/period-comparison.md](docs/period-comparison.md) for the uncertainty calculation and interpretation.

## Rainfall and groundwater context

The event record was compared with seasonally matched antecedent precipitation and nearby Chalk groundwater levels. Of 123 uncensored Q90 events, 39 began after a 180-day regional rainfall total below the 20th percentile. Groundwater observations within ±45 days were available for 93 events, of which 21 were below their monthly 20th percentile. The major events show different combinations of rainfall and groundwater state, so the evidence does not support a single climatic explanation.

![Rainfall–groundwater state at Q90 event onset](docs/figures/hydroclimate_state_space.png)

The rainfall series is a broad South East England comparator rather than catchment-average precipitation, and the groundwater series is one irregularly sampled nearby borehole. The calculation and its limits are described in [docs/hydroclimate-context.md](docs/hydroclimate-context.md); comparative hydrographs for the 1976, 1991, 1996, 2011 and 2022 episodes are shown in [docs/preliminary-findings.md](docs/preliminary-findings.md).

## Scientific conclusion

The record supports a cautious conclusion: low-flow exposure was greater in the two later 19-year periods than in 1967–1985, but uncertainty in the early-to-late contrast remains wide and includes zero. Major events also occupy different rainfall–groundwater states. The evidence therefore characterises variation in observed drought behaviour without establishing a climate-driven trend.

The integrated interpretation, quantitative evidence and remaining limits are summarised in [docs/scientific-synthesis.md](docs/scientific-synthesis.md).

## Analysis sequence

With [uv](https://docs.astral.sh/uv/) installed, the complete local calculation is run as follows:

```text
uv sync
uv run python scripts/download_ea_flow.py
uv run python scripts/download_context_data.py
uv run python scripts/audit_flow_record.py
uv run python scripts/analyse_droughts.py
uv run python scripts/compare_periods.py
uv run python scripts/analyse_hydroclimate_context.py
uv run python scripts/make_scientific_figures.py
uv run python scripts/make_workflow_schematic.py
uv run python -m unittest discover -s tests -v
```

Internet access is required only for the two download commands. Raw downloads remain under `data/raw/` and are excluded from version control.

## Data and licensing

The analytical inputs are Environment Agency river-flow and groundwater observations and Met Office HadUKP regional precipitation, all published under the Open Government Licence. Downloaded source files are excluded from version control; scripts, provenance metadata and derived results are retained. NRFA station information is used only for catchment and gauging context; no NRFA time series is redistributed.

Detailed provenance and the station-selection rationale are recorded in [docs/data-sources.md](docs/data-sources.md).

## Licence and attribution

The analysis code is available under the [MIT License](LICENSE). Environment Agency and Met Office observations retain their respective Open Government Licence terms. Required acknowledgements, the HadUKP citation and the distinction between code and data licensing are set out in [ATTRIBUTION.md](ATTRIBUTION.md). No NRFA time series or catchment-boundary download is included.
