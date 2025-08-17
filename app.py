# app.py
import streamlit as st
import pandas as pd
import glob, os, json
from cleaner import run_cleaner

st.set_page_config(page_title="Proton Mail Cleaner", layout="wide")
st.title("📬 Proton Mail Cleaner Dashboard")

# --- Sidebar ---
st.sidebar.header("Settings")

interval = st.sidebar.slider("Auto-refresh interval (seconds)", 10, 300, 60)
autorefresh = st.sidebar.checkbox("Enable Auto-refresh", value=True)

# Manual run button
if st.sidebar.button("⚡ Run Cleaner Now"):
    st.info("Running cleaner… this may take a moment.")
    try:
        path = run_cleaner()
        st.success(f"Cleaner finished. Report saved: {os.path.basename(path)}")
    except Exception as e:
        st.error(f"Cleaner failed: {e}")

# --- Status Notification ---
status_path = "reports/status.json"
status = None

if os.path.exists(status_path):
    try:
        with open(status_path, "r") as f:
            status = json.load(f)
    except json.JSONDecodeError:
        st.warning("⚠️ Status file is corrupted or incomplete.")

# Reset button
if st.sidebar.button("♻️ Reset Status File"):
    try:
        if os.path.exists(status_path):
            os.remove(status_path)
            st.sidebar.success("Status file cleared. It will regenerate on next cleaner run.")
        status = None
    except Exception as e:
        st.sidebar.error(f"Failed to reset: {e}")

if status:
    st.sidebar.markdown("### 🟢 Cleaner Status")
    st.sidebar.write(f"**Last Run:** {status['last_run']}")
    st.sidebar.write(f"**Total Emails:** {status['total']}")
    st.sidebar.write(f"**Archived:** {status['archived']}")
    st.sidebar.write(f"**Trashed:** {status['trashed']}")
    st.sidebar.write(f"**Report:** {os.path.basename(status['report'])}")

    st.success(
        f"✅ Cleaner last ran at {status['last_run']} → "
        f"Reviewed {status['total']} | Archived {status['archived']} | Trashed {status['trashed']}"
    )
else:
    st.warning("⚠️ No valid status available — run the cleaner.")

# --- Load reports ---
files = sorted(glob.glob("reports/report_*.csv"))
if not files:
    st.error("❌ No reports found. Run the cleaner first.")
    st.stop()

# Load all non-empty CSVs
dfs = [pd.read_csv(f) for f in files if os.path.getsize(f) > 0]
if not dfs:  # all empty
    st.warning("⚠️ Reports exist but contain no data.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

if df.empty:
    st.info("📭 No emails were found in the last run.")
    st.stop()

# --- Filters ---
df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
cats = st.sidebar.multiselect(
    "Categories",
    df["Category"].dropna().unique(),
    default=df["Category"].dropna().unique()
)
df = df[df["Category"].isin(cats)]

if df.empty:
    st.warning("📭 No emails match the selected filters.")
    st.stop()

# --- Summary ---
st.subheader("📊 Summary (All Reports)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", len(df))
col2.metric("Archived", (df["Action"] == "archive").sum())
col3.metric("Trashed", (df["Action"] == "trash").sum())
col4.metric("Kept", (df["Action"] == "keep").sum())

# --- Trends ---
st.subheader("📈 Trends over days")
trend_df = df.dropna(subset=["Date"])
if not trend_df.empty:
    trend = trend_df.groupby(trend_df["Date"].dt.date)["Action"].value_counts().unstack().fillna(0)
    st.line_chart(trend)
else:
    st.info("⚠️ No valid dates available to plot trends.")

# --- Largest Emails ---
st.subheader("📦 Largest Emails")
if not df.empty:
    largest = df.sort_values("SizeMB", ascending=False).head(10)
    st.table(largest[["Date", "From", "Subject", "SizeMB"]])
else:
    st.info("No emails available to show largest list.")

# --- Unsubscribe Links ---
st.subheader("🔗 Unsubscribe Links")
unsubs = df[df["Unsubscribe"].notna()][["From", "Subject", "Unsubscribe"]].drop_duplicates()
if not unsubs.empty:
    st.table(unsubs.head(20))
else:
    st.info("No unsubscribe links found.")

# --- Data Explorer ---
st.subheader("🔍 Detailed Table")
st.dataframe(df, use_container_width=True)

# --- Export ---
if not df.empty:
    # Use BytesIO for proper Excel export
    import io
    buffer = io.BytesIO()

    # 🔧 Drop timezone info to avoid Excel error
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.tz_localize(None)

    df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "⬇️ Download filtered data (Excel)",
        buffer.getvalue(),
        "export.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )