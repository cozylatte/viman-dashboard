# ============================================================
# 🌆 Viman Nagar — Real-Time Civic Dashboard
# Author: Aarushi Chottani
# Updated UI, IST timezone fix, safe GitHub JSON fetch, frontend auto-refresh
# ============================================================

import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# ----------------------
# PAGE SETTINGS
# ----------------------
st.set_page_config(
    page_title="Viman Nagar Civic Dashboard",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------
# FRONTEND AUTO REFRESH
# ----------------------
st_autorefresh(interval=3600000, key="frontend_autorefresh")  # Refresh every 1 hour

# ----------------------
# HEADER (White Color)
# ----------------------
st.markdown(
    """
    <h1 style='text-align:center; color: #FFFFFF;'>🌆 Viman Nagar Civic Dashboard</h1>
    <p style='text-align:center; color: #555;'>Data (updated hourly) from public sources. Auto-refresh enabled.</p>
    """,
    unsafe_allow_html=True
)

# ----------------------
# SIDEBAR FILTERS
# ----------------------
st.sidebar.title("Filters 🧭")
selected_categories = st.sidebar.multiselect(
    "Select Issue Categories:",
    options=["Traffic", "Garbage", "Streetlights", "Bus Delays", "Safety"],
    default=["Traffic", "Garbage", "Streetlights", "Bus Delays", "Safety"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.info(
    """
    Backend scrapers run hourly and update GitHub.
    Frontend dashboard auto-refreshes every hour.
    Showing Viman Nagar-specific civic issues.
    """
)

# ----------------------
# LOAD DATA FROM GITHUB
# ----------------------
DATA_RAW_URL = "https://raw.githubusercontent.com/cozylatte/viman-dashboard/main/data/data.json"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_remote_data(url):
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()

        if len(data) == 0:
            return pd.DataFrame(columns=["Category", "Description", "Source", "lat", "lon", "timestamp"])

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

# ----------------------
# FILTER ONLY VIMAN NAGAR MENTIONS
# ----------------------
if not df.empty:
    df["Description"] = df["Description"].fillna("")
    df["Category"] = df["Category"].fillna("Social Media")
    df["Source"] = df["Source"].fillna("Unknown")

    df = df[
        df["Description"].str.lower().str.contains(
            "viman nagar|vimannagar|viman-nagar|viman_nagar|viman"
        )
    ]

    df = df.reset_index(drop=True)

# ----------------------
# TABS
# ----------------------
tab1, tab2 = st.tabs(["📊 Summary", "🗺️ Map View"])

# ----------------------
# SUMMARY TAB
# ----------------------
with tab1:
    st.subheader("Live Issues Summary (Viman Nagar)")

    if df.empty:
        st.info("No live mentions found right now. Backend scrapers run hourly.")
    else:
        total_issues = len(df)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Issues", total_issues)
        col2.metric("Traffic", len(df[df["Category"] == "Traffic"]))
        col3.metric("Garbage", len(df[df["Category"] == "Garbage"]))
        col4.metric("Streetlights", len(df[df["Category"] == "Streetlights"]))
        col5.metric("Safety", len(df[df["Category"] == "Safety"]))

        # Category bar chart
        summary = df["Category"].value_counts()
        fig = px.bar(
            x=summary.index,
            y=summary.values,
            labels={"x": "Category", "y": "Count"},
            title="Issues by Category",
            color=summary.index,
            color_discrete_map={
                "Traffic": "red",
                "Garbage": "orange",
                "Streetlights": "green",
                "Bus Delays": "purple",
                "Safety": "darkred"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------------------
# MAP TAB
# ----------------------
with tab2:
    st.subheader("Real-Time Map")

    m = folium.Map(location=[18.567, 73.914], zoom_start=14, tiles="CartoDB positron")

    emoji_map = {
        "Traffic": "🚦",
        "Garbage": "🗑️",
        "Streetlights": "💡",
        "Bus Delays": "🚌",
        "Safety": "⚠️"
    }

    color_map = {
        "Traffic": "red",
        "Garbage": "orange",
        "Streetlights": "green",
        "Bus Delays": "purple",
        "Safety": "darkred"
    }

    for _, row in df.iterrows():
        if row["Category"] in selected_categories:
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=f"{emoji_map.get(row['Category'], '')} {row['Description']}",
                icon=folium.Icon(color=color_map.get(row["Category"], "blue"))
            ).add_to(m)

    st_folium(m, width=1280, height=600)

# ----------------------
# FOOTER CREDITS
# ----------------------
st.markdown(
    """
    <div style="text-align:center; margin-top:40px; color:#888;">
        Made with ❤️ by <b>Aarushi Chottani</b>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------
# LAST UPDATED — IST FIX
# ----------------------
ist = pytz.timezone("Asia/Kolkata")
st.markdown(f"**Last updated (frontend):** {datetime.now(ist).strftime('%d %B %Y, %I:%M %p')}")

