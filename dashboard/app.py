"""
Document Intelligence Pipeline -- Dashboard
Run with: streamlit run dashboard/app.py
"""

import sqlite3
import json
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Document Intelligence Dashboard", layout="wide")
st.title("📄 Document Intelligence Pipeline")
st.caption("OCR Agent → Extraction Agent (LLM) → Validation Agent → this dashboard")

db_path = st.sidebar.text_input("Database file", "pipeline_results.db")

try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM documents", conn)
    conn.close()
except Exception as e:
    st.error(f"Could not load {db_path}: {e}")
    st.stop()

if df.empty:
    st.warning("No documents processed yet. Run orchestrator.py first.")
    st.stop()

# --- Top-level KPIs ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Documents processed", len(df))
col2.metric("Valid rate", f"{df['is_valid'].mean() * 100:.1f}%")
col3.metric("Avg OCR confidence", f"{df['ocr_avg_confidence'].mean():.2f}")
col4.metric("Avg validation pass rate", f"{df['validation_pass_rate'].mean() * 100:.1f}%")

st.divider()

# --- Charts ---
c1, c2 = st.columns(2)

with c1:
    fig = px.histogram(df, x="ocr_avg_confidence", nbins=20,
                        title="OCR Confidence Distribution")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    method_counts = df["extraction_method"].value_counts().reset_index()
    method_counts.columns = ["method", "count"]
    fig2 = px.pie(method_counts, names="method", values="count",
                  title="Extraction Method Used (LLM vs Rule-based Fallback)")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Validation issues (flagged documents)")
flagged = df[df["is_valid"] == 0]
if not flagged.empty:
    for _, row in flagged.iterrows():
        issues = json.loads(row["validation_issues"])
        with st.expander(f"{row['image_path']} — {row['vendor_name']}"):
            for issue in issues:
                st.write(f"- {issue}")
else:
    st.success("No flagged documents.")

st.subheader("All processed documents")
st.dataframe(
    df[["image_path", "vendor_name", "date", "total", "extraction_method",
        "is_valid", "ocr_avg_confidence"]],
    use_container_width=True,
)

st.caption(
    "Tip: export this table (Streamlit's download button on the dataframe, "
    "or `SELECT * FROM documents` in any SQLite browser) to a CSV for the "
    "Power BI version of this dashboard."
)

