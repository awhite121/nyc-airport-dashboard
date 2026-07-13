# Interactive dashboard

The completed app is in `dashboard/`.

Open `dashboard/when-to-leave-nyc-dashboard.html` for the self-contained version, or serve `dashboard/` as a static site.

The complete supplied modeling data, notebooks, source package, reports, model benchmarks, and the new interactive app are all included in this project.

To regenerate app predictions from the included dataset:

```bash
cd dashboard
python3 scripts/build_app_data.py
```
