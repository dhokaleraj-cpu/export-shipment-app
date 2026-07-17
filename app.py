import streamlit as st
from datetime import datetime

SAFE_START_VERSION = "2026-07-13-CLOUD-SAFE-START-NO-COMMON-IMPORT"

st.set_page_config(
    page_title="Export Shipment Monitoring System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding-top: 1rem !important; }
.safe-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 18px 22px;
    margin: 10px 0 18px 0;
    box-shadow: 0 6px 18px rgba(15,23,42,.08);
}
.safe-title {
    font-size: 28px;
    font-weight: 900;
    color: #003B73;
    margin-bottom: 6px;
}
.safe-sub {
    font-size: 15px;
    color: #334155;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="safe-card">
        <div class="safe-title">EXPORT SHIPMENT MONITORING SYSTEM</div>
        <div class="safe-sub">Cloud Safe Start Loaded Successfully</div>
        <div class="safe-sub">Version: {SAFE_START_VERSION}</div>
        <div class="safe-sub">Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.success("If this page is visible, Streamlit Cloud deployment is working and the main loading issue is inside common.py/page import/runtime.")
st.info("Use the left side pages menu to open Dashboard, Reports, Delivery, Shipment, Payment, etc.")

st.warning(
    "If this safe-start page is NOT visible after push and reboot, Streamlit Cloud is still running old files or old build cache. "
    "In that case reboot the app and confirm GitHub has this exact app.py."
)

st.code(SAFE_START_VERSION)
