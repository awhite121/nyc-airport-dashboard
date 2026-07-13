# When to Leave NYC

A complete interactive decision-support dashboard for Manhattan taxi trips to JFK and LaGuardia.

## What works

- Clickable map of all 63 Manhattan pickup taxi-zone centroids
- JFK / LGA airport selection
- Flight date, departure time, domestic/international, passengers, and planning style controls
- Iterative leave-by recommendation based on the modeled departure hour
- Expected duration, p80, p90, slow-trip probability, road budget, and historical evidence
- Alternative departure windows
- Hourly, weekday, airport, zone-ranking, heatmap, and spatial analytics
- Deployed-model performance, feature influence, threshold tradeoff, original project benchmarks, and limitations
- Responsive desktop/mobile layout

## Fastest way to open it

Open `when-to-leave-nyc-dashboard.html`. It contains the CSS, JavaScript, and prediction data in one file and does not need a server.

## Run the project folder

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Data and modeling

The app uses the supplied 43,079-row cleaned dataset of August 2025 Manhattan-to-JFK/LGA yellow-taxi trips. The build script trains gradient-boosted duration, quantile, and late-risk models with a chronological 80/20 holdout, then pre-scores 21,168 zone/airport/weekday/hour scenarios for instant static deployment.

`data/app_data.json` documents the generated predictions, historical aggregates, model metrics, original benchmark results, and map centroids.

## Rebuild the prediction layer

The build script currently points to the supplied project dataset path in this packaged workspace. Update `ROOT` at the top of `scripts/build_app_data.py` when moving the source data elsewhere, then run:

```bash
python3 scripts/build_app_data.py
```

Required Python packages: pandas, numpy, scikit-learn, lightgbm.

## Deployment

The folder is static and can be deployed to Vercel, Netlify, GitHub Pages, Cloudflare Pages, or any basic web server. No API keys or backend are required.
