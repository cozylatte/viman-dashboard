# app.py
# Viman Nagar Civic Dashboard (reads data.json produced by hourly GitHub Action)
# No placeholder manual issues. Everything comes from real sources stored in data.json.

import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import html

# -----------------------
# CONFIG - UPDATE THIS
# -----------------------
# Replace these with your GitHub username/repo
GITHUB_USER = "cozylatte"
REPO_NAME = "viman-dashboard"

# Raw URL to the data file produced by the GitHub Action (data/data.json)
DATA_RAW_URL = "https://raw.githubusercontent.com/cozylatte/viman-dashboard/main/data/data.json"

# Auto-refresh in browser every 60 minutes (3600000 ms)
st_autorefresh(interval=60 * 60 * 1000, key="frontend_autorefresh")

# Page
st.set_page_config(page_title="Viman Nagar Civic Dashboard", layout="wide")
st.title("🌆 Viman Nagar — Real-Time Civic Dashboard")
st.caption("Data (hourly) from free public sources. Back-end updates every hour; front-end auto-reloads every hour.")

# Sidebar filter
st.sidebar.header("Filters")
selected_categories = st.sidebar.multiselect(
    "Select categories to display",
    ["Garbage", "Streetlights", "Bus Delays", "Safety", "Social Media"],
    default=["Garbage", "Streetlights", "Bus Delays", "Safety", "Social Media"]
)

# -----------------------
# Fetch data.json from GitHub (raw)
# -----------------------
# Fetch data.json from GitHub (raw)
# -----------------------
@st.cache_data(ttl=300)  # cache for 5 minutes
def load_remote_data(url):
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
        if len(data) == 0:
            # Empty DataFrame with expected columns
            df = pd.DataFrame(columns=["Category", "Description", "Source", "lat", "lon", "timestamp"])
        else:
            df = pd.DataFrame(data)
            # Ensure all required columns exist
            for col in ["Category", "Description", "Source", "lat", "lon", "timestamp"]:
                if col not in df.columns:
                    df[col] = ""
        return df
    except Exception as e:
        st.error(f"Could not fetch data.json from GitHub: {e}")
        return pd.DataFrame(columns=["Category", "Description", "Source", "lat", "lon", "timestamp"])

df = load_remote_data(DATA_RAW_URL)

# Keep only Viman Nagar mentions (safety)
for col in ["Description", "Category", "Source"]:
    if col not in df.columns:
        df[col] = ""
        
df["Description"] = df["Description"].fillna("")
df["Category"] = df["Category"].fillna("Social Media")
df["Source"] = df["Source"].fillna("Unknown")

if not df.empty:
    df = df[df["Description"].str.lower().str.contains("viman nagar|vimannagar|viman_nagar|viman-nagar|viman")]
    df = df.reset_index(drop=True)

# UI: summary
st.subheader("📊 Live Issues Summary (Viman Nagar)")
if df.empty:
    st.info("No live Viman Nagar mentions found right now. Backend scrapers run hourly; please check back soon.")
else:
    summary = df["Category"].value_counts()
    fig = px.bar(x=summary.index, y=summary.values, labels={"x": "Category", "y": "Count"}, title="Issues by Category")
    st.plotly_chart(fig, use_container_width=True)

    # Map
    st.subheader("🗺️ Live Issues Map (Viman Nagar)")
    m = folium.Map(location=[18.5679, 73.9142], zoom_start=14)
    ICONS = {
        "Garbage": ("🗑️", "green"),
        "Streetlights": ("💡", "orange"),
        "Bus Delays": ("🚌", "blue"),
        "Safety": ("⚠️", "red"),
        "Social Media": ("🔔", "purple")
    }

    for idx, row in df.iterrows():
        cat = row.get("Category", "Social Media")
        if cat not in selected_categories:
            continue
        try:
            lat = float(row.get("lat", 18.5679))
            lon = float(row.get("lon", 73.9142))
        except:
            lat, lon = 18.5679, 73.9142

        popup_text = f"{ICONS.get(cat,('', 'gray'))[0]} <b>{cat}</b><br>{html.escape(str(row.get('Description')))}<br><i>Source: {row.get('Source')}</i>"
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=400),
            icon=folium.Icon(color=ICONS.get(cat,('', 'gray'))[1])
        ).add_to(m)

    st_folium(m, width=1200, height=600)

# Last updated
st.markdown(f"**Last updated (frontend):** {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

with st.expander("About this setup"):
    st.write("""
    - Backend: GitHub Actions runs scraper.py every hour and writes data/data.json to this repo.
    - Frontend: This Streamlit app reads the raw data.json from raw.githubusercontent.com and auto-refreshes every hour.
    - Result: The page will automatically reload in the browser (every 60 minutes) and the data source is updated on the backend every hour — the MLA always sees data at most 1 hour old.
    """)


