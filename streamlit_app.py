from pathlib import Path
import json

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parent
DASHBOARD_PATH = ROOT / "dashboard" / "when-to-leave-nyc-dashboard.html"
APP_DATA_PATH = ROOT / "dashboard" / "data" / "app_data.js"

st.set_page_config(
    page_title="When to Leave NYC",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      #MainMenu, footer, header { visibility: hidden; }
      [data-testid="stAppViewContainer"] { background: #07111f; }
      [data-testid="stMainBlockContainer"] {
        max-width: 100%;
        padding: 0;
      }
      [data-testid="stVerticalBlock"] { gap: 0; }
      .stApp { overflow-x: hidden; }
      iframe {
        border: 0 !important;
        width: 100% !important;
        background: #07111f;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_app_data() -> dict:
    raw = APP_DATA_PATH.read_text(encoding="utf-8").strip()
    prefix = "window.APP_DATA="
    if not raw.startswith(prefix):
        raise ValueError("dashboard/data/app_data.js has an unexpected format")
    return json.loads(raw[len(prefix):].rstrip(";"))


def build_map_html(app_data: dict) -> str:
    zones = [
        {
            "id": zone["id"],
            "name": zone["name"],
            "lat": zone["lat"],
            "lon": zone["lon"],
            "trips": zone.get("trips", 0),
            "avg": zone.get("avg", 0),
            "p80": zone.get("p80", 0),
            "lateRate": zone.get("lateRate", 0),
        }
        for zone in app_data["zones"]
    ]
    airports = app_data["airports"]

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(8, 19, 34, 0.94);
      --border: rgba(148, 163, 184, 0.22);
      --text: #f4f7fb;
      --muted: #9fb0c3;
      --teal: #35d0ba;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{ padding: 18px 20px 22px; }}
    .heading {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .eyebrow {{
      color: var(--teal);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .14em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    h2 {{ margin: 0; font-size: clamp(24px, 3vw, 38px); line-height: 1.05; }}
    .sub {{ margin: 8px 0 0; color: var(--muted); font-size: 14px; max-width: 760px; }}
    .airport-switch {{
      display: flex;
      gap: 8px;
      padding: 5px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: rgba(13, 27, 42, .8);
    }}
    .airport-button {{
      border: 0;
      border-radius: 10px;
      background: transparent;
      color: var(--muted);
      padding: 10px 16px;
      font-weight: 800;
      cursor: pointer;
    }}
    .airport-button.active {{ color: #041414; background: var(--teal); }}
    .map-shell {{
      position: relative;
      border: 1px solid var(--border);
      border-radius: 22px;
      overflow: hidden;
      box-shadow: 0 18px 60px rgba(0,0,0,.35);
    }}
    #map {{ height: 590px; width: 100%; background: #0d1b2a; }}
    .map-card {{
      position: absolute;
      z-index: 700;
      left: 16px;
      bottom: 16px;
      width: min(360px, calc(100% - 32px));
      padding: 15px;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: var(--panel);
      backdrop-filter: blur(12px);
      box-shadow: 0 12px 35px rgba(0,0,0,.35);
    }}
    .map-card-title {{ font-size: 17px; font-weight: 850; margin: 0 0 3px; }}
    .map-card-airport {{ color: var(--teal); font-size: 13px; font-weight: 750; margin-bottom: 12px; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
    .stat {{
      padding: 9px 8px;
      background: rgba(15, 31, 49, .85);
      border-radius: 11px;
      border: 1px solid rgba(148,163,184,.12);
    }}
    .stat b {{ display: block; font-size: 16px; }}
    .stat span {{ color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .07em; }}
    .map-note {{ color: var(--muted); font-size: 11px; margin-top: 10px; line-height: 1.45; }}
    .legend {{
      position: absolute;
      z-index: 700;
      right: 16px;
      bottom: 16px;
      padding: 11px 13px;
      border: 1px solid var(--border);
      border-radius: 13px;
      background: var(--panel);
      font-size: 11px;
      line-height: 1.8;
    }}
    .dot {{ display: inline-block; width: 9px; height: 9px; margin-right: 7px; border-radius: 50%; }}
    .leaflet-control-zoom a {{
      background: #0d1b2a !important;
      color: #f4f7fb !important;
      border-color: rgba(148,163,184,.25) !important;
    }}
    .leaflet-popup-content-wrapper, .leaflet-popup-tip {{ background: #0d1b2a; color: #f4f7fb; }}
    .popup-title {{ font-weight: 850; font-size: 15px; margin-bottom: 7px; }}
    .popup-row {{ display: flex; justify-content: space-between; gap: 18px; color: #b8c6d6; margin: 4px 0; }}
    .popup-row b {{ color: #fff; }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 14px 10px 18px; }}
      .heading {{ align-items: flex-start; flex-direction: column; }}
      .airport-switch {{ width: 100%; }}
      .airport-button {{ flex: 1; }}
      #map {{ height: 620px; }}
      .legend {{ display: none; }}
      .map-card {{ left: 10px; bottom: 10px; width: calc(100% - 20px); }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="heading">
      <div>
        <div class="eyebrow">Geographic Explorer</div>
        <h2>NYC airport travel map</h2>
        <p class="sub">Click a Manhattan TLC taxi-zone centroid, inspect historical behavior, and switch between JFK and LaGuardia.</p>
      </div>
      <div class="airport-switch">
        <button id="JFK-button" class="airport-button active" onclick="setAirport('JFK')">JFK</button>
        <button id="LGA-button" class="airport-button" onclick="setAirport('LGA')">LaGuardia</button>
      </div>
    </div>

    <div class="map-shell">
      <div id="map"></div>
      <div class="map-card">
        <div id="selected-zone" class="map-card-title">Midtown Center</div>
        <div id="selected-airport" class="map-card-airport">Route to JFK</div>
        <div class="stats">
          <div class="stat"><b id="avg-duration">—</b><span>Avg duration</span></div>
          <div class="stat"><b id="p80-duration">—</b><span>80th percentile</span></div>
          <div class="stat"><b id="late-risk">—</b><span>Late-trip rate</span></div>
        </div>
        <div id="trip-count" class="map-note">Historical evidence loads from the project dataset.</div>
        <div class="map-note">Map points are official TLC zone centroids. Dashed lines show origin-to-airport direction, not live road routing.</div>
      </div>
      <div class="legend">
        <div><span class="dot" style="background:#35d0ba"></span>Selected pickup</div>
        <div><span class="dot" style="background:#5aa7ff"></span>Lower historical risk</div>
        <div><span class="dot" style="background:#f5b942"></span>Moderate historical risk</div>
        <div><span class="dot" style="background:#ff6b6b"></span>Higher historical risk</div>
        <div><span class="dot" style="background:#ffffff"></span>Airport</div>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const zones = {json.dumps(zones, separators=(",", ":"))};
    const airports = {json.dumps(airports, separators=(",", ":"))};

    const map = L.map('map', {{ zoomControl: true, scrollWheelZoom: true }}).setView([40.745, -73.94], 11);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    }}).addTo(map);

    let selectedAirport = 'JFK';
    let selectedZone = zones.find(z => z.id === 161) || zones[0];
    let routeLine = null;
    let selectedRing = null;
    const zoneLayers = new Map();

    function riskColor(rate) {{
      if (rate >= 0.28) return '#ff6b6b';
      if (rate >= 0.16) return '#f5b942';
      return '#5aa7ff';
    }}

    function popupHtml(zone) {{
      return `
        <div class="popup-title">${{zone.name}}</div>
        <div class="popup-row"><span>Historical trips</span><b>${{zone.trips.toLocaleString()}}</b></div>
        <div class="popup-row"><span>Average</span><b>${{zone.avg.toFixed(1)}} min</b></div>
        <div class="popup-row"><span>P80</span><b>${{zone.p80.toFixed(1)}} min</b></div>
        <div class="popup-row"><span>Late-trip rate</span><b>${{(zone.lateRate * 100).toFixed(1)}}%</b></div>
      `;
    }}

    zones.forEach(zone => {{
      const marker = L.circleMarker([zone.lat, zone.lon], {{
        radius: Math.max(4.5, Math.min(10, 4.5 + Math.log10(zone.trips + 1) * 1.45)),
        color: '#07111f',
        weight: 1.5,
        fillColor: riskColor(zone.lateRate),
        fillOpacity: 0.9
      }}).addTo(map);
      marker.bindTooltip(zone.name, {{ direction: 'top', opacity: 0.95 }});
      marker.bindPopup(popupHtml(zone));
      marker.on('click', () => selectZone(zone));
      zoneLayers.set(zone.id, marker);
    }});

    Object.entries(airports).forEach(([code, airport]) => {{
      L.circleMarker([airport.lat, airport.lon], {{
        radius: 9,
        color: '#07111f',
        weight: 2,
        fillColor: '#ffffff',
        fillOpacity: 1
      }}).addTo(map).bindTooltip(`${{code}} · ${{airport.name}}`, {{ direction: 'top' }});
    }});

    function drawSelection() {{
      const airport = airports[selectedAirport];
      if (routeLine) routeLine.remove();
      if (selectedRing) selectedRing.remove();

      routeLine = L.polyline(
        [[selectedZone.lat, selectedZone.lon], [airport.lat, airport.lon]],
        {{ color: '#35d0ba', weight: 3, opacity: 0.9, dashArray: '8 9' }}
      ).addTo(map);

      selectedRing = L.circleMarker([selectedZone.lat, selectedZone.lon], {{
        radius: 14,
        color: '#35d0ba',
        weight: 3,
        fillColor: '#35d0ba',
        fillOpacity: 0.18
      }}).addTo(map);

      document.getElementById('selected-zone').textContent = selectedZone.name;
      document.getElementById('selected-airport').textContent = `Route to ${{airport.name}}`;
      document.getElementById('avg-duration').textContent = `${{selectedZone.avg.toFixed(1)}} min`;
      document.getElementById('p80-duration').textContent = `${{selectedZone.p80.toFixed(1)}} min`;
      document.getElementById('late-risk').textContent = `${{(selectedZone.lateRate * 100).toFixed(1)}}%`;
      document.getElementById('trip-count').textContent = `${{selectedZone.trips.toLocaleString()}} historical trips are represented for this pickup zone.`;

      map.fitBounds(routeLine.getBounds(), {{
        paddingTopLeft: [40, 45],
        paddingBottomRight: [40, 220],
        maxZoom: 12
      }});
    }}

    function selectZone(zone) {{
      selectedZone = zone;
      drawSelection();
      const layer = zoneLayers.get(zone.id);
      if (layer) layer.openPopup();
    }}

    function setAirport(code) {{
      selectedAirport = code;
      document.querySelectorAll('.airport-button').forEach(button => button.classList.remove('active'));
      document.getElementById(`${{code}}-button`).classList.add('active');
      drawSelection();
    }}

    drawSelection();
    setTimeout(() => map.invalidateSize(), 250);
  </script>
</body>
</html>
"""


for required_path in (DASHBOARD_PATH, APP_DATA_PATH):
    if not required_path.exists():
        st.error(
            "Required dashboard file not found at "
            f"`{required_path.relative_to(ROOT)}`."
        )
        st.stop()

try:
    app_data = load_app_data()
    dashboard_html = DASHBOARD_PATH.read_text(encoding="utf-8")
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"The dashboard could not be loaded: {exc}")
    st.stop()

components.html(dashboard_html, height=1600, scrolling=True)
components.html(build_map_html(app_data), height=720, scrolling=False)
