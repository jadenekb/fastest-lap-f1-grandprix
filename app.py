# app.py (v3.4) — cleaned: no peak accel, lap times shown, legend fixed, sectors correct
import os
import streamlit as st
import fastf1
from datetime import timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ensure cache folder exists
os.makedirs("f1_cache", exist_ok=True)
fastf1.Cache.enable_cache("f1_cache")

st.set_page_config(page_title="F1 Lap Telemetry Comparison", layout="centered")
st.title("🏁 F1 Lap Telemetry Comparison")

# helpers
def format_laptime(td: timedelta):
    total_ms = td.total_seconds() * 1000
    minutes = int(total_ms // 60000)
    seconds = int((total_ms % 60000) // 1000)
    milliseconds = int(total_ms % 1000)
    return f"{minutes}:{seconds:02}.{milliseconds:03}"

# UI inputs
year = st.number_input("Year", min_value=2018, max_value=2025, value=2024, step=1)
gp = st.text_input("Grand Prix (e.g. Monza)", "Monza")

# Session selector dropdown
session_type = st.selectbox(
    "Select Session Type:",
    ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"],
    index=4  # Default: Race
)

driver1 = st.text_input("Driver 1 Code (e.g. VER)", "VER").upper().strip()
driver2 = st.text_input("Driver 2 Code (e.g. HAM)", "HAM").upper().strip()

if st.button("Compare Fastest Laps"):
    try:
        # load session (race session default 'R' — change to 'Q' or others if you prefer)
        # Map human-friendly names to FastF1 session codes
        session_map = {
                        "Practice 1": "FP1",
                         "Practice 2": "FP2",
                         "Practice 3": "FP3",
                        "Qualifying": "Q",
                         "Race": "R"
                        }
        session = fastf1.get_session(year, gp, session_map[session_type])

        session.load()

        # team color function compatibility
        try:
            from fastf1.plotting import get_team_color
            def team_color(team):
                return get_team_color(team, session)
        except Exception:
            from fastf1.plotting import team_color as _tc
            def team_color(team):
                return _tc(team)

        # get fastest laps
        laps_d1 = session.laps.pick_driver(driver1)
        laps_d2 = session.laps.pick_driver(driver2)
        if laps_d1.empty or laps_d2.empty:
            raise ValueError("One or both drivers have no laps in this session.")

        lap1 = laps_d1.pick_fastest()
        lap2 = laps_d2.pick_fastest()

        # telemetry
        tel1 = lap1.get_car_data().add_distance()
        tel2 = lap2.get_car_data().add_distance()

        # convert distance to km for plot x-axis
        tel1['Distance_km'] = tel1['Distance'] / 1000.0
        tel2['Distance_km'] = tel2['Distance'] / 1000.0

        # Prepare lap time metrics
        lap1_time = lap1['LapTime']
        lap2_time = lap2['LapTime']
        delta_td = (lap1_time - lap2_time) if lap1_time > lap2_time else (lap2_time - lap1_time)
        loser = driver1 if lap1_time > lap2_time else driver2
        delta_text = f"{loser} +{format_laptime(delta_td)}"

        c1 = team_color(lap1['Team'])
        c2 = team_color(lap2['Team'])

        # Build Plotly figure — both continuous solid lines
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=tel1['Distance_km'], y=tel1['Speed'],
            mode='lines',
            name=f"{driver1} ({lap1['Team']})",
            line=dict(color=c1, width=3),
            hovertemplate="<b>%{text}</b><br>Distance: %{x:.2f} km<br>Speed: %{y:.0f} km/h<extra></extra>",
            text=[driver1]*len(tel1)
        ))

        fig.add_trace(go.Scatter(
            x=tel2['Distance_km'], y=tel2['Speed'],
            mode='lines',
            name=f"{driver2} ({lap2['Team']})",
            line=dict(color=c2, width=3),
            hovertemplate="<b>%{text}</b><br>Distance: %{x:.2f} km<br>Speed: %{y:.0f} km/h<extra></extra>",
            text=[driver2]*len(tel2)
        ))

        # Compute sector cumulative times (Sector1Time, Sector2Time, Sector3Time are timedeltas)
        # Sector1Time = time for S1, Sector2Time = time for S2, etc. -> cumulative: s1, s1+s2, s1+s2+s3
        s1 = lap1['Sector1Time'].total_seconds()
        s2 = s1 + lap1['Sector2Time'].total_seconds()
        s3 = s2 + lap1['Sector3Time'].total_seconds()

        # compute lap-relative time column for tel1 (seconds since lap start)
        tel1['LapTime_s'] = (tel1['Time'] - tel1['Time'].iloc[0]).dt.total_seconds()

        # find distances at the end of S1 and S2 (use tel1 as reference)
        sector_times = [s1, s2]  # we usually mark end of S1 and end of S2
        sector_distances_km = []
        for t in sector_times:
            # find index closest to that lap-relative time
            idx = (np.abs(tel1['LapTime_s'] - t)).idxmin()
            sector_distances_km.append(tel1.loc[idx, 'Distance_km'])

        # draw vertical lines for sectors
        for i, dist_km in enumerate(sector_distances_km, start=1):
            fig.add_vline(x=dist_km, line=dict(color="white", width=1, dash="dot"),
                          annotation_text=f"S{i}", annotation_position="top left", opacity=0.7)

        fig.update_layout(
            title=f"Fastest Lap Comparison — {year} {gp} {session_type}",
            xaxis_title="Distance (km)",
            yaxis_title="Speed (km/h)",
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01)
        )

        # Show lap times and delta as metrics
        col1, col2, col3 = st.columns([1,1,1])
        col1.metric(f"{driver1} Lap Time", format_laptime(lap1_time))
        col2.metric(f"{driver2} Lap Time", format_laptime(lap2_time))
        col3.metric("Δ Lap Time", delta_text)

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
