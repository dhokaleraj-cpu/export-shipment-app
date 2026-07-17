import streamlit as st
from datetime import datetime

st.set_page_config(page_title="System Check", layout="wide")

st.title("System Check")
st.code("SYSTEM_CHECK_VERSION = 2026-07-13-CLOUD-SAFE-START")

st.write("This page checks whether common.py can import successfully.")

if st.button("Run common.py import check", type="primary"):
    try:
        import common
        st.success("common.py imported successfully.")
        st.write("Import time:", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        st.write("Available user session:", bool(st.session_state.get("user")))
    except Exception as exc:
        st.error("common.py import failed.")
        st.exception(exc)

if st.button("Run Reports file verification", type="secondary"):
    try:
        from pathlib import Path
        report_path = Path("pages/8_Reports.py")
        txt = report_path.read_text(encoding="utf-8", errors="ignore")
        st.write("Reports file exists:", report_path.exists())
        st.write("REPORTS_DEPLOY_VERSION present:", "REPORTS_DEPLOY_VERSION" in txt)
        st.write("Old bad line 66 present:", "return fetch_all(sql, tuple(base_params) + tuple(access_params))" in txt)
        st.write("Old bad tuple present:", "(invoice_filter, invoice_filter, delivery_invoice_filter" in txt)
        st.write("Question mark placeholders present:", "?" in txt)
        st.write("PostgreSQL %s placeholders present:", "%s" in txt)
    except Exception as exc:
        st.exception(exc)
