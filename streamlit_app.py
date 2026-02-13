import streamlit as st
import pandas as pd
import os
import altair as alt
import datetime
import time

CSV_FILE = "events.csv"

st.set_page_config(
    page_title="Worklog Ultimate Dashboard",
    page_icon="💻",
    layout="wide"
)

# =========================
# Auto Refresh Every 30 Seconds
# =========================
st.markdown(
    """
    <meta http-equiv="refresh" content="30">
    """,
    unsafe_allow_html=True
)

# =========================
# Animated Loading Bar
# =========================
progress = st.progress(0)
for i in range(100):
    time.sleep(0.005)
    progress.progress(i + 1)

# =========================
# UI Styling
# =========================
st.markdown("""
<style>
.main-title {
    font-size: 44px;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(90deg, #22c55e, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💻 Worklog Ultimate Dashboard</div>', unsafe_allow_html=True)
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

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"])
df["date"] = df["timestamp"].dt.date

# =========================
# Sidebar Filter
# =========================
st.sidebar.header("📅 Select Date")

min_date = df["date"].min()
max_date = df["date"].max()

selected_date = st.sidebar.date_input(
    "Choose Date",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

# =========================
# 🔥 IMPROVED Working Hours Function
# =========================
def calculate_working_hours(data):
    if data.empty:
        return 0

    total_seconds = 0
    unlock_time = None
    data = data.sort_values("timestamp")

    selected_day = pd.to_datetime(data["date"].iloc[0])
    day_start = pd.Timestamp.combine(selected_day, datetime.time.min)
    day_end = day_start + pd.Timedelta(days=1)
    now = pd.Timestamp.now()

    for _, row in data.iterrows():
        event_time = row["timestamp"]

        # Ignore future timestamps
        if event_time > now:
            continue

        if row["event_type"] == "screen_unlock":
            unlock_time = max(event_time, day_start)

        elif row["event_type"] == "screen_lock" and unlock_time is not None:
            lock_time = min(event_time, day_end)

            if lock_time > unlock_time:
                total_seconds += (lock_time - unlock_time).total_seconds()

            unlock_time = None

    # If still unlocked → count till now
    if unlock_time is not None:
        effective_end = min(now, day_end)

        if effective_end > unlock_time:
            total_seconds += (effective_end - unlock_time).total_seconds()

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
    x="Date:T",
    y=alt.Y("Working Hours:Q", scale=alt.Scale(domain=[0, y_limit])),
    tooltip=["Date", "Working Hours"]
).properties(height=350)

st.altair_chart(line_chart, use_container_width=True)

st.markdown("---")

# =========================
# 24-Hour Circular Timeline (FIXED for ongoing session)
# =========================
st.subheader("🕒 Daily Activity Timeline (24 Hours)")

selected_day = pd.to_datetime(selected_date)
day_start = pd.Timestamp.combine(selected_day, datetime.time.min)
day_end = day_start + pd.Timedelta(hours=24)
now = pd.Timestamp.now()

day_data = selected_day_data.sort_values("timestamp")

segments = []
current_time = day_start
status = "Inactive"

for _, row in day_data.iterrows():
    event_time = row["timestamp"]

    if event_time > current_time:
        segments.append({
            "start": current_time,
            "end": event_time,
            "status": status
        })

    if row["event_type"] == "screen_unlock":
        status = "Active"
    elif row["event_type"] == "screen_lock":
        status = "Inactive"

    current_time = event_time

# 🔥 FIX: If still active today
if selected_date == now.date() and status == "Active":
    day_end = min(day_end, now)

if current_time < day_end:
    segments.append({
        "start": current_time,
        "end": day_end,
        "status": status
    })

timeline_data = []

for seg in segments:
    duration = (seg["end"] - seg["start"]).total_seconds() / 3600
    timeline_data.append({
        "Status": seg["status"],
        "Duration": duration,
        "TimeRange": f"{seg['start'].strftime('%I:%M %p')} - {seg['end'].strftime('%I:%M %p')}"
    })

timeline_df = pd.DataFrame(timeline_data)

timeline_chart = alt.Chart(timeline_df).mark_arc(innerRadius=120).encode(
    theta="Duration:Q",
    color=alt.Color(
        "Status:N",
        scale=alt.Scale(
            domain=["Active", "Inactive"],
            range=["#22c55e", "#e5e7eb"]
        ),
        legend=None
    ),
    tooltip=["Status", "TimeRange", alt.Tooltip("Duration:Q", format=".2f")]
).properties(height=500)

center_text = alt.Chart(pd.DataFrame({
    "text": [f"{selected_day_hours} hrs Active"]
})).mark_text(size=24, fontWeight="bold").encode(text="text:N")

st.altair_chart(timeline_chart + center_text, use_container_width=True)

st.markdown("---")

# =========================
# Weekly Summary
# =========================
st.subheader("📊 Weekly Summary")

last_7_days = date_hours_df.tail(7)
weekly_total = round(last_7_days["Working Hours"].sum(), 2)
weekly_avg = round(last_7_days["Working Hours"].mean(), 2)

col1, col2 = st.columns(2)
col1.metric("Total (7 Days)", f"{weekly_total} hrs")
col2.metric("Daily Avg", f"{weekly_avg} hrs")

st.markdown("---")

# =========================
# Productivity Gauge
# =========================
st.subheader("⚡ Productivity Score")

productivity_score = round((selected_day_hours / 8) * 100, 1)
productivity_score = min(productivity_score, 100)

gauge_data = pd.DataFrame({
    "Category": ["Score", "Remaining"],
    "Value": [productivity_score, 100 - productivity_score]
})

gauge = alt.Chart(gauge_data).mark_arc(innerRadius=120).encode(
    theta="Value:Q",
    color=alt.Color(
        "Category:N",
        scale=alt.Scale(
            domain=["Score", "Remaining"],
            range=["#16a34a", "#e5e7eb"]
        ),
        legend=None
    )
)

gauge_text = alt.Chart(pd.DataFrame({
    "text": [f"{productivity_score}%"]
})).mark_text(size=32, fontWeight="bold").encode(text="text:N")

st.altair_chart(gauge + gauge_text, use_container_width=True)

st.markdown("---")

# =========================
# Logs Table
# =========================
st.subheader("📄 Logs For Selected Date")

st.dataframe(selected_day_data.sort_values("timestamp"), use_container_width=True)
