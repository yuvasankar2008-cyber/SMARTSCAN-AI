# SMARTSCAN AI upgrade notes

## Added
- Compact live progress panel below the radar and Mission Control row.
- Improved hero KPI labels and metric definitions.
- Recorded-observation heatmap with explicit not-observed cells.
- Synthetic scenario profile comparison against the stationary reference.
- Descriptive latest-event explanation panel.
- Session-only experiment snapshots.
- Guided demo walkthrough.
- Updated pitch deck copy to remove unverified performance and deployment claims.

## Preserved
- Existing Streamlit entry point and folder structure.
- Existing simulation engine and simulation controls.
- Existing radar rendering and CSV export.
- Existing dark theme and pitch deck navigation.

## Important metric notes
- Synthetic Pd = observed active events / all synthetic active events.
- Pfa = false-positive predictions / inactive selected-scan observations; predictions use the prior Laplace-smoothed activity rate.
- Mean intercept rate = active episodes observed at least once / all contiguous active episodes started.
- Average intercept time error = mean absolute rounds between episode start and first observation.
- Correct prediction percentage = correct active/inactive scan predictions / all selected-scan predictions.
- Observed active yield = active observations / total observations; it is not accuracy.
- Scenario comparison compares expected synthetic activity profiles, not scheduling algorithms.
- Experiment snapshots remain in the current Streamlit session only.

## Run
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
