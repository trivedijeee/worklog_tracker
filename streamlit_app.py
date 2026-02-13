import streamlit as st
import pandas as pd
import os
import altair as alt
import numpy as np

CSV_FILE = "events.csv"

st.set_page_config(
    page_title="Worklog Pro Dashboard",
    page_icon="💻",
    layout="wide"
)

# =========================
# Modern Styling
# =========================
st.markdown("""
<style>
.main-title {
    font-size: 44px;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(90deg, #ff4b1f, #1fddff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-box {
    background: #111827;
    padding: 20px;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💻 Worklog Pro Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# =========================
# Load Data
# =========================
if not os.path.exists(CSV_FILE):
    st.error("❌ events.csv not found")
    st.stop()

df = pd.read_csv(CSV_FILE)

if df.empty:
    st.warning("⚠ No data available")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

# =========================
# Sidebar Filter
# =========================
st.sidebar.header("📅 Filter By Date")

min_date = df["date"].min()
max_date = df["date"].max()

selected_date = st.sidebar.date_input(
    "Select Date",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

# =========================
# Working Hours Function
# =========================
def calculate_working_hours(data):
    total_seconds = 0
    unlock_time = None

    data = data.sort_values("timestamp")

    for _, row in data.iterrows():
        if row["event_type"] == "screen_unlock":
            unlock_time = row["timestamp"]

        elif row["event_type"] == "screen_lock" and unlock_time is not None:
            total_seconds += (row["timestamp"] - unlock_time).total_seconds()
            unlock_time = None

    return round(total_seconds / 3600, 2)

# =========================
# Date-wise Hours
# =========================
date_hours_list = []

for date in sorted(df["date"].unique()):
    day_data = df[df["date"] == date]
    hours = calculate_working_hours(day_data)
    date_hours_list.append({
        "Date": pd.to_datetime(date),
        "Working Hours": hours
    })

date_hours_df = pd.DataFrame(date_hours_list)

# =========================
# Selected Day
# =========================
selected_day_data = df[df["date"] == selected_date]
selected_day_hours = calculate_working_hours(selected_day_data)

col1, col2 = st.columns(2)
col1.metric("📆 Selected Date", str(selected_date))
col2.metric("⏱ Working Hours", f"{selected_day_hours} hrs")

st.markdown("---")

# =========================
# Line Chart
# =========================
st.subheader("📈 Date-wise Working Hours")

max_hour = date_hours_df["Working Hours"].max()
y_limit = max_hour + 1

line_chart = alt.Chart(date_hours_df).mark_line(
    point=True,
    strokeWidth=3
).encode(
    x=alt.X("Date:T"),
    y=alt.Y(
        "Working Hours:Q",
        scale=alt.Scale(domain=[0, y_limit])
    ),
    tooltip=["Date", "Working Hours"]
).properties(height=350)

st.altair_chart(line_chart, use_container_width=True)

st.markdown("---")

# =========================
# Donut Chart With Center Text
# =========================
st.subheader("🟢 Daily Usage Breakdown (24 Hours)")

active = selected_day_hours
inactive = round(24 - active, 2)

donut_data = pd.DataFrame({
    "Category": ["Active", "Inactive"],
    "Hours": [active, inactive]
})

donut = alt.Chart(donut_data).mark_arc(innerRadius=90).encode(
    theta="Hours:Q",
    color=alt.Color(
        "Category:N",
        scale=alt.Scale(
            domain=["Active", "Inactive"],
            range=["#ff4b4b", "#e5e7eb"]
        )
    )
)

text = alt.Chart(pd.DataFrame({
    "text": [f"{active} hrs\nActive"]
})).mark_text(size=20, fontWeight="bold").encode(
    text="text:N"
)

st.altair_chart((donut + text).properties(height=400), use_container_width=True)

st.markdown("---")

# =========================
# Weekly Summary
# =========================
st.subheader("📊 Weekly Summary (Last 7 Days)")

last_7_days = date_hours_df.tail(7)

weekly_total = round(last_7_days["Working Hours"].sum(), 2)
weekly_avg = round(last_7_days["Working Hours"].mean(), 2)

col1, col2 = st.columns(2)
col1.metric("🗓 Total (7 Days)", f"{weekly_total} hrs")
col2.metric("📈 Daily Avg", f"{weekly_avg} hrs")

st.markdown("---")

# =========================
# Productivity Score
# =========================
st.subheader("⚡ Productivity Score")

# Score based on 8-hour ideal day
productivity_score = round((active / 8) * 100, 1)
productivity_score = min(productivity_score, 100)

st.metric("Today's Productivity", f"{productivity_score}%")

# =========================
# Animated Circular Gauge
# =========================
gauge_data = pd.DataFrame({
    "Category": ["Score", "Remaining"],
    "Value": [productivity_score, 100 - productivity_score]
})

gauge = alt.Chart(gauge_data).mark_arc(innerRadius=100).encode(
    theta="Value:Q",
    color=alt.Color(
        "Category:N",
        scale=alt.Scale(
            domain=["Score", "Remaining"],
            range=["#10b981", "#e5e7eb"]
        ),
        legend=None
    )
)

gauge_text = alt.Chart(pd.DataFrame({
    "text": [f"{productivity_score}%"]
})).mark_text(size=30, fontWeight="bold").encode(
    text="text:N"
)

st.altair_chart((gauge + gauge_text).properties(height=350), use_container_width=True)

st.markdown("---")

# =========================
# Logs Table
# =========================
st.subheader("📄 Logs For Selected Date")

st.dataframe(
    selected_day_data.sort_values("timestamp"),
    use_container_width=True
)

