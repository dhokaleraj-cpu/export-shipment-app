import io

import base64

import html

import sqlite3

import smtplib

import urllib.parse

from datetime import date, timedelta, datetime, datetime, datetime, datetime, datetime, datetime, datetime

from email.message import EmailMessage

from pathlib import Path


import pandas as pd

import streamlit as st

APP_VERSION = "SN 26.16"


# ---------------------------------------------------------------------------
# Persistent save message helper
# Keeps "Data saved successfully" visible after st.rerun().
# ---------------------------------------------------------------------------
if "_fsi_original_st_success" not in globals():
    _fsi_original_st_success = st.success

    def _fsi_persistent_success(message, *args, **kwargs):
        try:
            st.session_state["_fsi_flash_success"] = str(message)
        except Exception:
            pass
        return _fsi_original_st_success(message, *args, **kwargs)

    st.success = _fsi_persistent_success

def set_success_message(message="Data saved successfully."):
    try:
        st.session_state["_fsi_flash_success"] = str(message)
    except Exception:
        pass

def render_success_message():
    try:
        msg = st.session_state.pop("_fsi_flash_success", "")
        if msg:
            _fsi_original_st_success(msg)
    except Exception:
        pass

def rerun_with_success(message="Data saved successfully."):
    set_success_message(message)
    st.rerun()
# ---------------------------------------------------------------------------


import streamlit.components.v1 as components

from reportlab.lib import colors

from reportlab.lib.pagesizes import A4, landscape

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from db import get_connection, init_db, verify_user, hash_password

UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)

LOGO_PATH = Path("FSI_LOGO_new.png")

CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "JPY", "CNY"]

st.set_page_config(page_title="Export Shipment Management", layout="wide", initial_sidebar_state="collapsed")

# init_db is intentionally not run during module import/login screen.
# It is run once per logged-in session inside page_setup() to keep login fast.


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&display=swap');

/* GLOBAL DEVICE FRIENDLY UI - COVERAGE PLAN STYLE */
html, body, .stApp, [class*="css"] {
    font-family: Montserrat, Aptos, Arial, sans-serif !important;
}

.block-container {
    max-width: 100% !important;
    padding-left: clamp(0.55rem, 1.5vw, 1.25rem) !important;
    padding-right: clamp(0.55rem, 1.5vw, 1.25rem) !important;
    padding-top: 1.2rem !important;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
.sap-grid-card-title, .sap-subtitle, .input-section-title,
label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stFileUploader label {
    font-weight: 900 !important;
}

h1 { font-size: clamp(24px, 2.2vw, 34px) !important; }
h2 { font-size: clamp(21px, 1.8vw, 28px) !important; }
h3 { font-size: clamp(18px, 1.45vw, 23px) !important; }

.sap-grid-card, .sap-section-card, .card, .topbar {
    border-radius: 8px !important;
    padding: clamp(10px, 1.2vw, 16px) !important;
    margin-bottom: clamp(10px, 1.2vw, 16px) !important;
    overflow-x: auto !important;
}

.sap-grid-card-title, .sap-subtitle, .input-section-title {
    font-size: clamp(16px, 1.35vw, 22px) !important;
    line-height: 1.18 !important;
    font-weight: 900 !important;
    color: #003B73 !important;
}

div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
    overflow-x: auto !important;
}

div[data-testid="column"] {
    min-width: 0 !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    min-height: clamp(34px, 3.2vw, 44px) !important;
    font-size: clamp(12px, 1vw, 15px) !important;
}

div[data-testid="stButton"] > button {
    min-height: clamp(34px, 3.2vw, 44px) !important;
    font-size: clamp(12px, 1vw, 15px) !important;
    font-weight: 900 !important;
}

/* App title on every page: 20% smaller, bold Montserrat */
.fsi-app-title,
.main-title-center {
    font-family: Montserrat, Aptos, Arial, sans-serif !important;
    font-size: 40px !important; /* reduced 20% from 50px */
    line-height: 1.05 !important;
    font-weight: 900 !important;
    color: #1B6DB5 !important;
    letter-spacing: .25px !important;
}

/* Top module menu responsive */
.custom-module-title {
    font-size: clamp(15px, 1.5vw, 20px) !important;
    font-weight: 900 !important;
}
.menu-no-border-wrap + div button,
div[data-testid="stButton"] > button {
    white-space: normal !important;
}

/* Tablet and low-resolution laptop */
@media (max-width: 1366px) {
    .block-container {
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
    }
    .fsi-app-title,
    .main-title-center {
        font-size: 32px !important;
    }
    .topbar h1 {
        font-size: 24px !important;
    }
    .user-clock, .top-user-details {
        font-size: 14px !important;
        line-height: 1.35 !important;
    }
    .sap-grid-card-title, .sap-subtitle, .input-section-title {
        font-size: 16px !important;
    }
}

/* Mobile / narrow tablet */
@media (max-width: 760px) {
    .block-container {
        padding-left: 0.45rem !important;
        padding-right: 0.45rem !important;
    }
    .fsi-app-title,
    .main-title-center {
        font-size: 24px !important;
        line-height: 1.1 !important;
    }
    h1 { font-size: 22px !important; }
    h2 { font-size: 20px !important; }
    h3 { font-size: 17px !important; }
    .topbar {
        padding: 10px !important;
    }
    .sap-grid-card, .sap-section-card, .card {
        padding: 8px !important;
    }
}

/* Rajesh slogan footer on every page and login page */
.fsi-slogan-footer {
    width: 100%;
    text-align: center;
    font-family: Aptos, Arial, sans-serif;
    font-size: 13px;
    font-weight: 900;
    color: #003B73;
    padding: 8px 10px;
    margin-top: 14px;
    border-top: 1px solid #d9e2ec;
    background: rgba(255,255,255,0.92);
}
.fsi-login-slogan-footer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 8px;
    width: 100%;
    text-align: center;
    font-family: Aptos, Arial, sans-serif;
    font-size: 13px;
    font-weight: 900;
    color: #003B73;
    z-index: 9999;
}
@media (max-width: 760px) {
    .fsi-slogan-footer, .fsi-login-slogan-footer {
        font-size: 11px;
        padding-left: 8px;
        padding-right: 8px;
    }
}



/* ACTIVE EDITABLE FIELD HIGHLIGHT - applies only to entry/edit inputs, not KPI cards/data display */
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within,
div[data-testid="stMultiSelect"] div[data-baseweb="select"]:focus-within,
div[data-testid="stFileUploader"] section:focus-within {
    border: 2px solid #F59E0B !important;
    box-shadow: 0 0 0 4px rgba(245,158,11,.22) !important;
    background: #FFF7ED !important;
    border-radius: 10px !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    color: #0F172A !important;
    font-weight: 900 !important;
}


    /* Global password eye icon fix */
    div[data-testid="stTextInput"] span[data-testid="stIconMaterial"] {
        font-size: 0 !important;
        color: transparent !important;
    }
    div[data-testid="stTextInput"] span[data-testid="stIconMaterial"]::before {
        content: "👁" !important;
        font-size: 18px !important;
        color: #003B73 !important;
    }

</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>
/* LOW RESOLUTION LAPTOP COMFORT UPDATE */
@media (max-width: 1366px) {
    .block-container {
        max-width: 100% !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 1.0rem !important;
    }
    h1 { font-size: 28px !important; }
    h2 { font-size: 23px !important; }
    h3 { font-size: 19px !important; }
    .topbar {
        padding: 12px 16px !important;
        margin-top: 10px !important;
        margin-bottom: 12px !important;
    }
    .topbar h1,
    .main-title-center {
        font-size: 30px !important;
        line-height: 1.1 !important;
    }
    .top-nav-wrap {
        padding: 8px !important;
        margin-bottom: 12px !important;
    }
    .top-nav-title {
        font-size: 15px !important;
    }
    .top-nav-wrap [data-testid="stPageLink"] a,


    /* Keep Streamlit password visibility icon visible and not clipped */
    div[data-testid="stTextInput"] { overflow: visible !important; }
    div[data-testid="stTextInput"] > div { overflow: visible !important; }
    div[data-testid="stTextInput"] input[type="password"],
    div[data-testid="stTextInput"] input[type="text"] {
        padding-right: 44px !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stTextInput"] button,
    div[data-testid="stTextInput"] [role="button"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 36px !important;
        min-width: 36px !important;
        right: 4px !important;
        z-index: 5 !important;
    }


    /* Login password eye icon fix - hide text "visibility" and show only icon */
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        position: relative !important;
        overflow: visible !important;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] input[type="password"],
    div[data-testid="stTextInput"] div[data-baseweb="input"] input[type="text"] {
        padding-right: 52px !important;
    }
    div[data-testid="stTextInput"] button[aria-label*="password"],
    div[data-testid="stTextInput"] button[title*="password"],
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"],
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button {
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        margin-right: 4px !important;
        overflow: hidden !important;
        color: transparent !important;
        font-size: 0 !important;
        line-height: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stTextInput"] button[aria-label*="password"] *,
    div[data-testid="stTextInput"] button[title*="password"] *,
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"] *,
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button * {
        color: transparent !important;
        font-size: 0 !important;
        line-height: 0 !important;
        max-width: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stTextInput"] button[aria-label*="password"]::before,
    div[data-testid="stTextInput"] button[title*="password"]::before,
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"]::before,
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button::before {
        content: "👁" !important;
        color: #003B73 !important;
        font-size: 18px !important;
        line-height: 1 !important;
        display: block !important;
    }


    /* Global password eye icon fix - hide Material text and show eye icon only */
    div[data-testid="stTextInput"] button[aria-label*="password"],
    div[data-testid="stTextInput"] button[title*="password"],
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"],
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button {
        color: transparent !important;
        font-size: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stTextInput"] button[aria-label*="password"] *,
    div[data-testid="stTextInput"] button[title*="password"] *,
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"] *,
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button * {
        color: transparent !important;
        font-size: 0 !important;
        overflow: hidden !important;
    }
    div[data-testid="stTextInput"] button[aria-label*="password"]::before,
    div[data-testid="stTextInput"] button[title*="password"]::before,
    div[data-testid="stTextInput"] [role="button"][aria-label*="password"]::before,
    div[data-testid="stTextInput"] [data-testid*="InputAdornment"] button::before {
        content: "👁" !important;
        color: #003B73 !important;
        font-size: 18px !important;
        line-height: 1 !important;
    }

    div[data-testid="stButton"] > button {
        min-height: 34px !important;
        font-size: 13px !important;
        padding: 4px 8px !important;
    }
    label,
    .stTextInput label,
    .stSelectbox label,
    .stNumberInput label,
    .stDateInput label,
    .stFileUploader label,
    .shipment-grid-label {
        font-size: 13px !important;
        line-height: 1.15 !important;
    }
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        min-height: 36px !important;
        font-size: 13px !important;
    }
    .card, .sap-grid-card, .sap-section-card {
        padding: 10px !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {
        overflow-x: auto !important;
    }
}
@media (max-width: 1100px) {
    .block-container {
        padding-left: 0.45rem !important;
        padding-right: 0.45rem !important;
    }
    div[data-testid="column"] {
        min-width: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>
/* FINAL RESPONSIVE UI COMFORT FOR ALL PAGES */
@media (min-width: 1280px) {
    .block-container { max-width: 1540px !important; margin-left: auto !important; margin-right: auto !important; padding-left: 2rem !important; padding-right: 2rem !important; }
}
@media (min-width: 1920px) { .block-container { max-width: 1720px !important; } }
@media (max-width: 900px) {
    .block-container { padding-left: 0.8rem !important; padding-right: 0.8rem !important; padding-top: 1rem !important; }
    .topbar { padding: 14px 16px !important; margin-top: 10px !important; }
    .topbar h1 { font-size: 24px !important; }
    .main-title-center { font-size: 30px !important; }
    .user-clock { font-size: 14px !important; text-align:center !important; }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { overflow-x:auto !important; }
}
@media (max-width: 520px) {
    .main-title-center { font-size: 24px !important; }
    h1 { font-size: 26px !important; }
    h2 { font-size: 22px !important; }
    h3 { font-size: 19px !important; }
    .top-nav-wrap [data-testid="stPageLink"] a, div[data-testid="stButton"] > button { font-size: 15px !important; min-height: 42px !important; }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* WIDE SCREEN COMFORT FIX */
@media (min-width: 1400px) {
    .block-container {
        max-width: 1480px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
}
@media (min-width: 1900px) {
    .block-container {
        max-width: 1680px !important;
    }
}
.topbar, .sap-section-card, .sap-grid-card, .card {
    max-width: 100% !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Aptos:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stApp, div, span, p, label, input, button, textarea, select {
    font-family: Montserrat, Aptos, Arial, sans-serif !important;
}
.stApp {background:#f4f6f8;}
.block-container {padding-top: 3.2rem; max-width: 100%;}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {font-weight: 800 !important;}
.top-strip {
    display:flex; justify-content:space-between; align-items:center;
    background:#ffffff; border:1px solid #c9eef5; border-radius:10px;
    padding:10px 16px; margin-bottom:10px; box-shadow:0 1px 6px rgba(0,0,0,.08);
}
.logo-box {display:flex; align-items:center; gap:12px; font-weight:800; font-size:18px; color:#003b73;}
.logo-circle {
    width:52px; height:52px; border-radius:10px; background:#0b5cab; color:white;
    display:flex; align-items:center; justify-content:center; font-weight:900; font-size:22px;
}
.user-clock {text-align:right; font-weight:700; color:#003b73;}
.topbar {background:#f8fafc;color:#003b73;padding:22px 26px;border-radius:12px;margin-top:24px;margin-bottom:20px;border:1px solid #d9e2ec;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.topbar h1 {font-size:28px;margin:0;font-weight:800;}
.subtext {font-size:13px;opacity:.9;margin-top:4px;}
.card {background:white;padding:18px;border-radius:10px;box-shadow:0 1px 8px rgba(0,0,0,.10);border:1px solid #c9eef5;}
.kpi-head {color:white;padding:10px;text-align:center;font-weight:800;border-radius:4px 4px 0 0;}
.kpi-value {border:1px solid #d0d7e2;border-top:0;padding:18px;text-align:center;font-size:25px;font-weight:800;background:white;}
.green {background:#008a00;}.teal {background:#42b883;}.orange {background:#ff8c00;}.red {background:#b00020;}.blue {background:#0b5cab;}.yellow {background:#fff3b0;color:#111;}
.total-box {background:#fff3b0;border:1px solid #d9c35c;padding:12px;border-radius:8px;font-size:18px;font-weight:800;}
.footer {text-align:center;color:#687386;font-size:12px;margin-top:30px;font-weight:700;}
div[data-baseweb="tab-list"] {
    gap: 14px !important;
    background:#ffffff;
    padding:10px 14px;
    border-radius:12px;
    border:1px solid #dde3ea;
    box-shadow:0 1px 6px rgba(0,0,0,.06);
}
button[data-baseweb="tab"] {
    background:#eef3f7;
    border-radius:10px;
    color:#003b73;
    font-weight:800;
    padding-left:18px !important;
    padding-right:18px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background:#0b5cab;
    color:white;
}

h1 {font-size: 38px !important; font-weight: 900 !important;}
h2 {font-size: 30px !important; font-weight: 900 !important;}
h3 {font-size: 24px !important; font-weight: 850 !important;}
label, .stTextInput label, .stSelectbox label, .stNumberInput label, .stDateInput label {font-size:15px !important;font-weight:750 !important;color:#1f2937 !important;}


.main-title-center {
    text-align:center;
    font-family:Montserrat, Aptos, Arial, sans-serif !important;
    font-size:38px;
    line-height:1.1;
    font-weight:900;
    color:#003B73;
    letter-spacing:.8px;
    padding-top:16px;
}
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3 {
    font-family:Montserrat, Aptos, Arial, sans-serif !important;
    font-weight:900 !important;
}
.subtext, .topbar h1, .kpi-head, .total-box {
    font-family:Aptos, Arial, sans-serif !important;
    font-weight:900 !important;
}


/* V30 bold headings and titles */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stFileUploader label {
    font-family: Aptos, Arial, sans-serif !important;
    font-weight: 900 !important;
    color: #003B73 !important;
}
.coverage-dashboard-title {
    font-size: 26px;
    font-weight: 900;
    color:#003B73;
    padding: 12px 0;
}


/* V39 light/dark friendly UI improvements */
:root {
    --fsi-bg: #f8fafc;
    --fsi-card: #ffffff;
    --fsi-text: #111827;
    --fsi-muted: #475569;
    --fsi-primary: #003B73;
    --fsi-border: #cbd5e1;
    --fsi-input-bg: #ffffff;
}
@media (prefers-color-scheme: dark) {
    :root {
        --fsi-bg: #0f172a;
        --fsi-card: #111827;
        --fsi-text: #f8fafc;
        --fsi-muted: #cbd5e1;
        --fsi-primary: #93c5fd;
        --fsi-border: #64748b;
        --fsi-input-bg: #1f2937;
    }
}
.stApp {
    background: var(--fsi-bg) !important;
    color: var(--fsi-text) !important;
}
.card, .total-box {
    background: var(--fsi-card) !important;
    color: var(--fsi-text) !important;
    border: 1px solid var(--fsi-border) !important;
}
div[data-testid="stMarkdownContainer"], p, span, div {
    color: inherit;
}
label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stFileUploader label {
    font-family: Aptos, Arial, sans-serif !important;
    font-weight: 900 !important;
    font-size: 15px !important;
    color: var(--fsi-primary) !important;
    letter-spacing: .01em !important;
}
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] textarea,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background: var(--fsi-input-bg) !important;
    color: var(--fsi-text) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="input"] input {
    color: var(--fsi-text) !important;
}
div[data-testid="stFileUploader"] section {
    background: var(--fsi-input-bg) !important;
    border: 1px dashed var(--fsi-border) !important;
    border-radius: 12px !important;
}
div[data-testid="stFileUploader"] small {
    display: none !important;
}
div[data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
    color: var(--fsi-muted) !important;
    font-weight: 700 !important;
}
.input-section-title {
    font-size: 18px;
    font-weight: 900;
    color: var(--fsi-primary);
    margin: 12px 0 8px 0;
}


/* V40 equal KPI/card sizing and consistent field sizing */
.kpi-head {
    min-height: 64px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    font-size:18px !important;
    line-height:1.25 !important;
}
.kpi-value {
    min-height: 86px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
}
div[data-testid="column"] {
    min-width: 0 !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input,
div[data-baseweb="select"] > div {
    min-height: 44px !important;
}


/* V41 file uploader overlap fix */
div[data-testid="stFileUploader"] {
    max-width: 100% !important;
}
div[data-testid="stFileUploader"] section {
    min-height: 86px !important;
    padding: 14px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    overflow: hidden !important;
}
div[data-testid="stFileUploader"] section button {
    min-width: 118px !important;
    height: 44px !important;
    font-size: 0 !important;
    position: relative !important;
}
div[data-testid="stFileUploader"] section button::after {
    content: "Upload" !important;
    font-size: 16px !important;
    font-weight: 900 !important;
    color: var(--fsi-primary) !important;
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 16px !important;
    color: var(--fsi-muted) !important;
    font-weight: 700 !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] div:first-child {
    display: none !important;
}


/* V43 coverage product filter and login cleanup */
.coverage-product-filter-title {
    font-family: Aptos, Arial, sans-serif;
    font-size: 20px;
    font-weight: 900;
    color: var(--fsi-primary);
    background: rgba(147, 197, 253, 0.18);
    border: 1px solid var(--fsi-border);
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
    margin-bottom: 8px;
}
.coverage-kpi-product-card .kpi-head,
.coverage-kpi-product-card .kpi-value {
    text-align: center !important;
}
.login-logo-gap-fix {
    height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
}


/* Multipage top navigation: hide left sidebar and keep module links at the top */
section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
    display: none !important;
}
div[data-testid="collapsedControl"] {
    display: none !important;
}
.block-container {
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
}
.top-nav-wrap {
    background:#ffffff;
    border:1px solid #d9e2ec;
    border-radius:12px;
    box-shadow:0 1px 6px rgba(0,0,0,.06);
    padding:10px 12px;
    margin: 4px 0 18px 0;
}
.top-nav-title {
    font-weight:900;
    color:#003B73;
    font-size:15px;
    padding:0 4px 6px 4px;
}
.top-nav-wrap [data-testid="stPageLink"] a {
    background:#eef3f7 !important;
    color:#003B73 !important;
    border-radius:10px !important;
    border:1px solid #d9e2ec !important;
    min-height:42px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-weight:900 !important;
    text-decoration:none !important;
}
.top-nav-wrap [data-testid="stPageLink"] a:hover {
    background:#0b5cab !important;
    color:white !important;
}
.coverage-metric-card .metric-head {
    background:#ff8c00;
    color:#ffffff;
    padding:10px;
    text-align:center;
    font-weight:900;
    border-radius:4px 4px 0 0;
    min-height:64px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
    line-height:1.25;
}
.coverage-metric-card .metric-value {
    border:1px solid #d0d7e2;
    border-top:0;
    padding:18px;
    text-align:center;
    font-size:32px;
    font-weight:900;
    background:white;
    min-height:86px;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#111827;
}
.coverage-metric-card .metric-input-box {
    border:1px solid #d0d7e2;
    border-top:0;
    background:white;
    min-height:86px;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:14px;
}
.coverage-metric-card .metric-input-box div[data-baseweb="input"] > div,
.coverage-metric-card .metric-input-box input {
    min-height:58px !important;
    text-align:center !important;
    font-size:32px !important;
    font-weight:900 !important;
    color:#111827 !important;
    border:0 !important;
    box-shadow:none !important;
    background:white !important;
}


/* SAP-style business theme overrides */
.sap-section-card, .topbar {
    background:#ffffff !important;
    border:1px solid #d5dadd !important;
    border-radius:4px !important;
    box-shadow:0 1px 3px rgba(0,0,0,.12) !important;
}
.topbar {
    border-top:4px solid #0a6ed1 !important;
}
.topbar h1 {
    color:#0a3f7a !important;
    font-size:34px !important;
}
.top-nav-wrap {
    background:#f4f8fc !important;
    border:1px solid #c9d7e3 !important;
    border-radius:6px !important;
    box-shadow:0 1px 4px rgba(0,0,0,.08) !important;
}
.top-nav-title {
    color:#0a3f7a !important;
    letter-spacing:.04em !important;
    font-size:16px !important;
    font-weight:900 !important;
}
.top-nav-wrap [data-testid="stPageLink"] a {
    background:#ffffff !important;
    color:#0a3f7a !important;
    border:1px solid #b8cdda !important;
    border-radius:5px !important;
    min-height:40px !important;
    font-size:15px !important;
    font-weight:900 !important;
    text-transform:uppercase !important;
}
.top-nav-wrap [data-testid="stPageLink"] a:hover {
    background:#0a6ed1 !important;
    color:#ffffff !important;
}
.sap-toolbar {
    background:#f7fafd;
    border:1px solid #d5dadd;
    border-radius:4px;
    padding:12px;
    margin:10px 0 14px 0;
}
.sap-subtitle {
    font-size:18px;
    font-weight:900;
    color:#0a3f7a;
    border-left:5px solid #0a6ed1;
    padding-left:10px;
    margin:12px 0 10px 0;
}
.kpi-head, .coverage-metric-card .metric-head {
    border-radius:3px 3px 0 0 !important;
    letter-spacing:.01em;
}
.kpi-value, .coverage-metric-card .metric-value, .coverage-metric-card .metric-input-box {
    border-radius:0 0 3px 3px !important;
    background:#ffffff !important;
}
.sap-grid-note {
    background:#fff8e1;
    border:1px solid #f0d47a;
    border-radius:4px;
    padding:8px 10px;
    color:#5b3b00;
    font-weight:700;
}


/* Strong card styling for SAP-like KPI sections */
.sap-kpi-card {
    background:#ffffff;
    border:1px solid #c9d7e3;
    border-radius:6px;
    overflow:hidden;
    box-shadow:0 1px 4px rgba(0,0,0,.12);
    min-height:150px;
    margin-bottom:10px;
}
.sap-kpi-card .sap-kpi-head {
    color:#ffffff;
    padding:14px 10px;
    min-height:58px;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    font-family:Aptos, Arial, sans-serif;
    font-size:18px;
    line-height:1.18;
    font-weight:900;
    letter-spacing:.01em;
}
.sap-kpi-card .sap-kpi-value {
    background:#ffffff;
    min-height:90px;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    padding:14px 10px;
    font-family:Aptos, Arial, sans-serif;
    font-size:30px;
    line-height:1.15;
    font-weight:900;
    color:#111827;
}
.sap-kpi-card .sap-kpi-value.red-text { color:#b91c1c; }
.sap-kpi-card .sap-kpi-head.green { background:#008a00; }
.sap-kpi-card .sap-kpi-head.teal { background:#42b883; }
.sap-kpi-card .sap-kpi-head.orange { background:#ff8c00; }
.sap-kpi-card .sap-kpi-head.blue { background:#0b5cab; }
.sap-kpi-card .sap-kpi-head.red { background:#b00020; }
.sap-kpi-card .sap-kpi-head.yellow { background:#fff3b0; color:#111827; }
.sap-kpi-card .sap-kpi-head.sap-blue { background:#0a6ed1; }
.sap-grid-card {
    background:#ffffff;
    border:1px solid #c9d7e3;
    border-radius:6px;
    box-shadow:0 1px 4px rgba(0,0,0,.10);
    padding:14px;
    margin:10px 0 14px 0;
}
.sap-grid-card-title {
    color:#0a3f7a;
    font-size:18px;
    font-weight:900;
    margin-bottom:8px;
    border-left:5px solid #0a6ed1;
    padding-left:10px;
}
.sap-horizontal-grid div[data-testid="stDataFrame"],
.sap-horizontal-grid div[data-testid="stDataEditor"] {
    border:1px solid #c9d7e3;
    border-radius:6px;
}


.coverage-vertical-grid-note {
    background:#f4f8fc;
    border:1px solid #c9d7e3;
    border-radius:6px;
    padding:10px 12px;
    color:#0a3f7a;
    font-weight:800;
    margin-bottom:10px;
}

/* USER REQUESTED BLUE THEME - GLOBAL APP STYLE */
.stApp {
    background:#E3F2FF !important;
}

/* Borders for all input and selection fields */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea,
.stTimeInput input,
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] textarea,
div[data-testid="stDateInput"] input {
    border:2px solid #1A5E99 !important;
    border-radius:6px !important;
    background:#ffffff !important;
}

/* Highlight selected/focused fields */
.stTextInput input:focus,
.stNumberInput input:focus,
.stDateInput input:focus,
.stTextArea textarea:focus,
.stTimeInput input:focus,
div[data-baseweb="input"]:focus-within > div,
div[data-baseweb="select"]:focus-within > div,
div[data-baseweb="textarea"]:focus-within textarea,
div[data-testid="stDateInput"]:focus-within input {
    border:2px solid #1A5E99 !important;
    background:#1A5E99 !important;
    color:#ffffff !important;
    box-shadow:0 0 0 2px rgba(26,94,153,0.25) !important;
}

div[data-baseweb="select"]:focus-within span,
div[data-baseweb="input"]:focus-within input {
    color:#ffffff !important;
}

/* Border for result/KPI/cards */
.kpi-value,
.total-box,
.sap-kpi-value,
.sap-kpi-card,
.card,
.sap-grid-card,
.sap-section-card,
.coverage-metric-card .metric-value,
.coverage-metric-card .metric-input-box {
    border:2px solid #1A5E99 !important;
}

/* Border for tables/data editors/dataframes */
div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"],
.sap-horizontal-grid div[data-testid="stDataFrame"],
.sap-horizontal-grid div[data-testid="stDataEditor"] {
    border:2px solid #1A5E99 !important;
    border-radius:6px !important;
}

/* Light bold module menu */
.top-nav-wrap {
    background:#E3F2FF !important;
    border:2px solid #1A5E99 !important;
    border-radius:6px !important;
}
.top-nav-title {
    font-weight:900 !important;
    color:#1A5E99 !important;
}
.top-nav-wrap [data-testid="stPageLink"] a {
    background:#ffffff !important;
    color:#1A5E99 !important;
    border:2px solid #1A5E99 !important;
    font-weight:900 !important;
}
.top-nav-wrap [data-testid="stPageLink"] a:hover {
    background:#1A5E99 !important;
    color:#ffffff !important;
}


/* Coverage filter cards matching KPI style */
.coverage-filter-card-title {
    background:#FF8C00 !important;
    color:#ffffff !important;
    border:2px solid #1A5E99 !important;
    border-bottom:0 !important;
    border-radius:8px 8px 0 0 !important;
    padding:12px 10px !important;
    min-height:58px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:18px !important;
    line-height:1.18 !important;
    font-weight:900 !important;
    letter-spacing:.01em !important;
}
.coverage-filter-card-body {
    background:#ffffff !important;
    border:2px solid #1A5E99 !important;
    border-top:0 !important;
    border-radius:0 0 8px 8px !important;
    min-height:82px !important;
    padding:12px !important;
    margin-bottom:10px !important;
    box-shadow:0 1px 4px rgba(0,0,0,.10) !important;
}
.coverage-filter-card-body div[data-baseweb="select"] > div,
.coverage-filter-card-body div[data-baseweb="input"] > div {
    min-height:54px !important;
    font-size:18px !important;
    font-weight:800 !important;
    border:2px solid #1A5E99 !important;
    border-radius:6px !important;
    background:#ffffff !important;
}
.coverage-filter-spacer {
    height:0px !important;
}


/* Larger bold headers */
.coverage-filter-card-title,
.metric-head{
 font-size:27px !important;
 font-weight:900 !important;
 line-height:1.25 !important;
 letter-spacing:.5px !important;
}
.coverage-filter-card-title{
 min-height:78px !important;
 padding:18px 10px !important;
}
.coverage-metric-card .metric-head{
 min-height:78px !important;
 display:flex !important;
 align-items:center !important;
 justify-content:center !important;
}


/* FORCE GLOBAL BLUE UI */
.stApp { background:#E3F2FF !important; }
.block-container { background:#E3F2FF !important; }
div[data-testid="stAppViewContainer"] { background:#E3F2FF !important; }


/* FINAL CARD INPUT ALIGNMENT */
div[data-testid="stNumberInput"] input {
    text-align:center !important;
    font-size:30px !important;
    font-weight:900 !important;
}


/* DIRECT CARD PATCH GLOBAL */
.stApp, .block-container, div[data-testid="stAppViewContainer"] {
    background:#E3F2FF !important;
}
div[data-testid="stNumberInput"] input {
    text-align:center !important;
    font-size:26px !important;
    font-weight:900 !important;
    min-height:48px !important;
}


/* FINAL BLUE COMPACT COVERAGE CARD INPUTS */
.stApp, .block-container, div[data-testid="stAppViewContainer"] {
    background:#E3F2FF !important;
}
.stSelectbox div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div,
.stNumberInput input,
div[data-testid="stNumberInput"] input {
    min-height:44px !important;
    font-size:22px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.stNumberInput input,
div[data-testid="stNumberInput"] input {
    text-align:center !important;
}


/* Dashboard Coverage Product Filter Card */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    min-height:56px !important;
    border-radius:0 0 4px 4px !important;
    border:1px solid #cbd5e1 !important;
    border-top:0 !important;
    background:#eef2f7 !important;
    font-size:18px !important;
    font-weight:900 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    font-size:18px !important;
    font-weight:900 !important;
    color:#111827 !important;
}


/* FINAL MARKUP UI FIX - embedded card inputs */
.embedded-card-input-body div[data-testid="stSelectbox"],
.embedded-card-input-body div[data-testid="stNumberInput"] {
    margin:0 !important;
    padding:0 !important;
}
.embedded-card-input-body div[data-baseweb="select"] > div,
.embedded-card-input-body div[data-baseweb="input"] > div,
.embedded-card-input-body input {
    min-height:42px !important;
    height:42px !important;
    border:0 !important;
    border-radius:4px !important;
    background:#eef2f7 !important;
    box-shadow:none !important;
    font-size:16px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.embedded-card-input-body div[data-baseweb="select"] span {
    font-size:16px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.embedded-card-input-body div[data-testid="InputInstructions"],
.embedded-card-input-body label {
    display:none !important;
}


/* FINAL DASHBOARD PRODUCT FILTER CARD FIX */
.embedded-card-input-body {
    min-height:56px !important;
    height:56px !important;
    padding:6px !important;
    background:#ffffff !important;
}
.embedded-card-input-body div[data-testid="stSelectbox"] {
    margin:0 !important;
    padding:0 !important;
}
.embedded-card-input-body div[data-baseweb="select"] > div {
    min-height:42px !important;
    height:42px !important;
    border:0 !important;
    border-radius:4px !important;
    background:#eef2f7 !important;
    box-shadow:none !important;
    font-size:16px !important;
    font-weight:900 !important;
}
.embedded-card-input-body div[data-baseweb="select"] span {
    font-size:16px !important;
    font-weight:900 !important;
    color:#111827 !important;
}


/* FINAL COVERAGE PLAN INPUTS INSIDE CARDS */
.coverage-card-input-body {
    height:56px !important;
    min-height:56px !important;
    padding:6px !important;
    background:#ffffff !important;
}
.coverage-card-input-body div[data-testid="stSelectbox"],
.coverage-card-input-body div[data-testid="stNumberInput"] {
    margin:0 !important;
    padding:0 !important;
}
.coverage-card-input-body label,
.coverage-card-input-body div[data-testid="InputInstructions"] {
    display:none !important;
}
.coverage-card-input-body div[data-baseweb="select"] > div,
.coverage-card-input-body div[data-baseweb="input"] > div,
.coverage-card-input-body input {
    min-height:42px !important;
    height:42px !important;
    border:0 !important;
    border-radius:4px !important;
    background:#eef2f7 !important;
    box-shadow:none !important;
    font-size:16px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.coverage-card-input-body div[data-baseweb="select"] span {
    font-size:16px !important;
    font-weight:900 !important;
    color:#111827 !important;
}


/* FINAL FIX: Coverage Plan inputs inside grid cards */
.coverage-input-card-header + div[data-testid="stSelectbox"],
.coverage-input-card-header + div[data-testid="stNumberInput"] {
    margin-top:0 !important;
    margin-bottom:10px !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] label,
.coverage-input-card-header + div[data-testid="stNumberInput"] label,
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-testid="InputInstructions"],
.coverage-input-card-header + div[data-testid="stNumberInput"] div[data-testid="InputInstructions"] {
    display:none !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.coverage-input-card-header + div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
.coverage-input-card-header + div[data-testid="stNumberInput"] input {
    height:56px !important;
    min-height:56px !important;
    border:1px solid #cbd5e1 !important;
    border-top:0 !important;
    border-radius:0 0 4px 4px !important;
    background:#eef2f7 !important;
    box-shadow:none !important;
    font-size:18px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    font-size:18px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.coverage-input-card-header + div[data-testid="stNumberInput"] input {
    text-align:left !important;
    padding-left:16px !important;
}


/* FINAL OVERRIDES - latest approved UI */
.user-clock {
    text-align:right !important;
    font-weight:900 !important;
    color:#1f2937 !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:16px !important;
    line-height:1.55 !important;
}
.main-title-center {
    text-align:center !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:50px !important;
    line-height:1.0 !important;
    font-weight:900 !important;
    color:#1B6DB5 !important;
    letter-spacing:.3px !important;
    padding-top:6px !important;
}
.top-nav-wrap {
    background:#ffffff !important;
    border:2px solid #1B6DB5 !important;
    border-radius:12px !important;
    box-shadow:0 2px 8px rgba(27,109,181,.10) !important;
    padding:12px 14px !important;
}
.top-nav-title {
    font-family:Aptos, Arial, sans-serif !important;
    font-size:20px !important;
    font-weight:900 !important;
    color:#1B6DB5 !important;
    letter-spacing:.02em !important;
    padding:0 6px 8px 6px !important;
}
.top-nav-wrap [data-testid="stPageLink"] a {
    background:#F4F8FC !important;
    color:#1B6DB5 !important;
    border:2px solid #1B6DB5 !important;
    border-radius:10px !important;
    min-height:46px !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:20px !important;
    font-weight:900 !important;
    text-decoration:none !important;
    box-shadow:none !important;
}
.top-nav-wrap [data-testid="stPageLink"] a:hover {
    background:#1B6DB5 !important;
    color:#ffffff !important;
}
/* Dashboard product filter card with select inside the card */
.dashboard-product-card-header + div[data-testid="stSelectbox"] {
    margin-top:0 !important;
    margin-bottom:10px !important;
}
.dashboard-product-card-header + div[data-testid="stSelectbox"] label,
.dashboard-product-card-header + div[data-testid="stSelectbox"] div[data-testid="InputInstructions"] {
    display:none !important;
}
.dashboard-product-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    height:58px !important;
    min-height:58px !important;
    border:1px solid #cbd5e1 !important;
    border-top:0 !important;
    border-radius:0 0 8px 8px !important;
    background:#EEF2F7 !important;
    box-shadow:none !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:18px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.dashboard-product-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    font-family:Aptos, Arial, sans-serif !important;
    font-size:18px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
/* Coverage page input cards with values inside cards */
.coverage-input-card-header + div[data-testid="stSelectbox"],
.coverage-input-card-header + div[data-testid="stNumberInput"] {
    margin-top:0 !important;
    margin-bottom:10px !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] label,
.coverage-input-card-header + div[data-testid="stNumberInput"] label,
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-testid="InputInstructions"],
.coverage-input-card-header + div[data-testid="stNumberInput"] div[data-testid="InputInstructions"] {
    display:none !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.coverage-input-card-header + div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
.coverage-input-card-header + div[data-testid="stNumberInput"] input {
    height:70px !important;
    min-height:70px !important;
    border:1px solid #cbd5e1 !important;
    border-top:0 !important;
    border-radius:0 0 4px 4px !important;
    background:#EEF2F7 !important;
    box-shadow:none !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:24px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.coverage-input-card-header + div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    font-family:Aptos, Arial, sans-serif !important;
    font-size:24px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.coverage-input-card-header + div[data-testid="stNumberInput"] input {
    text-align:left !important;
    padding-left:16px !important;
}

</style>
""", unsafe_allow_html=True)

def fetch_all(query, params=()):
    from db import fetch_all as db_fetch_all
    return db_fetch_all(query, params)

@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_all(query, params=()):
    """Cached SELECT helper for master/dropdown and read-only dashboard data."""
    return fetch_all(query, params)

def clear_app_cache():
    try:
        st.cache_data.clear()
    except Exception:
        pass

def execute_query(query, params=()):
    from db import execute_query as db_execute_query
    return db_execute_query(query, params)

def ensure_runtime_columns():
    """Keep Supabase/PostgreSQL schema aligned with the latest app fields."""
    schema_updates = [
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS delivered_to_customer NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS wh_bank NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS bank_status NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS suggested_shipment_qty NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS next_shipment_date DATE",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS shipment_delivery_qty NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS two_months_inventory NUMERIC DEFAULT 0",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_coverage_plan_product_plan_date_unique ON coverage_plan_lines(product_id, plan_date)",
    ]
    for sql in schema_updates:
        try:
            execute_query(sql)
        except Exception:
            pass

def check_delete_password(password):
    user = st.session_state.get("user", {})
    username = user.get("username", "")
    return bool(verify_user(username, password))

def delete_record_with_password(table_name, record_id, password, details=""):
    if not check_delete_password(password):
        st.error("Wrong password. Delete cancelled.")
        return False
    try:
        execute_query("INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                      (table_name, record_id, st.session_state.user.get("username", ""), details))
    except Exception:
        pass
    execute_query(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    st.success("Record deleted successfully.")
    return True

def format_date_ddmmyyyy(value):
    """Display any YYYY-MM-DD/date/datetime value as DD-MM-YYYY."""
    if value in (None, ""):
        return ""
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y")
        text = str(value)[:10]
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return str(value)

def format_date_columns(rows):
    """Format all date-like columns for display only."""
    date_keys = ["date", "due", "plan_date", "shipment_date", "delivery_date", "payment_received_date", "payment_due_date", "next_shipment_date"]
    output = []
    for row in rows:
        new_row = dict(row)
        for k, v in list(new_row.items()):
            kl = str(k).lower()
            if any(x in kl for x in date_keys):
                new_row[k] = format_date_ddmmyyyy(v)
        output.append(new_row)
    return output

def cleanup_orphan_transactions():
    """Remove transaction rows linked to deleted primary records so edit modules stay refreshed."""
    try:
        execute_query("""
            DELETE FROM payments
            WHERE delivery_id NOT IN (SELECT id FROM customer_deliveries)
        """)
    except Exception:
        pass
    try:
        execute_query("""
            DELETE FROM customer_deliveries
            WHERE shipment_id NOT IN (SELECT id FROM shipments)
               OR box_id NOT IN (SELECT id FROM shipment_boxes)
               OR customer_id NOT IN (SELECT id FROM customers)
        """)
    except Exception:
        pass
    try:
        execute_query("""
            DELETE FROM shipment_boxes
            WHERE shipment_id NOT IN (SELECT id FROM shipments)
               OR product_id NOT IN (SELECT id FROM products)
        """)
    except Exception:
        pass

def save_upload(file, prefix):
    if not file:
        return None
    safe_name = file.name.replace("/", "_").replace("\\", "_")
    path = UPLOAD_DIR / f"{prefix}_{safe_name}"
    with open(path, "wb") as f:
        f.write(file.getbuffer())
    return str(path)





# --- Page-wise access controls ---
APP_PAGE_DEFINITIONS = [
    {"label": "Dashboard", "target": "pages/1_Dashboard.py", "key": "dashboard", "default_roles": ["user", "admin", "super_admin"]},
    {"label": "Masters", "target": "pages/2_Masters.py", "key": "masters", "default_roles": ["admin", "super_admin"]},
    {"label": "Shipment Entry", "target": "pages/3_Shipment_Entry.py", "key": "shipment", "default_roles": ["admin", "super_admin"]},
    {"label": "Last Shipments", "target": "pages/13_Last_Shipments.py", "key": "shipment_last", "default_roles": ["admin", "super_admin"]},
    {"label": "Edit Shipment", "target": "pages/14_Edit_Shipment.py", "key": "shipment_edit", "default_roles": ["admin", "super_admin"]},
    {"label": "Shipment Status", "target": "pages/16_Shipment_Status.py", "key": "shipment_status", "default_roles": ["admin", "super_admin"]},
    {"label": "Delivery", "target": "pages/4_Delivery_to_Customer.py", "key": "delivery", "default_roles": ["user", "admin", "super_admin"]},
    {"label": "Reprint Invoice", "target": "pages/10_Reprint_Invoice.py", "key": "delivery_reprint", "default_roles": ["admin", "super_admin"]},
    {"label": "FIFO Available Pallets", "target": "pages/11_FIFO_Available_Pallets.py", "key": "delivery_fifo", "default_roles": ["user", "admin", "super_admin"]},
    {"label": "Edit Delivery Invoice", "target": "pages/12_Edit_Delivery_Invoice.py", "key": "delivery_edit", "default_roles": ["admin", "super_admin"]},
    {"label": "Delivery Invoice List", "target": "pages/15_Delivery_Invoice_List.py", "key": "delivery_list", "default_roles": ["admin", "super_admin"]},
    {"label": "Payment", "target": "pages/5_Payment_Entry.py", "key": "payment", "default_roles": ["admin", "super_admin"]},
    {"label": "Payment Due", "target": "pages/18_Payment_Due.py", "key": "payment_due", "default_roles": ["admin", "super_admin"]},
    {"label": "Edit Payment", "target": "pages/19_Edit_Payment.py", "key": "payment_edit", "default_roles": ["admin", "super_admin"]},
    {"label": "Payment Received List", "target": "pages/20_Payment_Received_List.py", "key": "payment_list", "default_roles": ["admin", "super_admin"]},
    {"label": "Coverage Plan", "target": "pages/6_Coverage_Plan.py", "key": "coverage", "default_roles": ["user", "admin", "super_admin"]},
    {"label": "Admin", "target": "pages/7_Admin.py", "key": "admin", "default_roles": ["admin", "super_admin"]},
    {"label": "Reports", "target": "pages/8_Reports.py", "key": "reports", "default_roles": ["user", "admin", "super_admin"]},
    {"label": "Overdue", "target": "pages/9_Overdue_Notification.py", "key": "overdue", "default_roles": ["admin", "super_admin"]},
]

def ensure_page_access_table():
    """Create/upgrade page-wise permissions.

    Rights:
    - can_view: user can open/view the page.
    - can_add: user can add/save new records on the page.
    - can_edit: user can edit/modify existing records on the page.
    Legacy:
    - can_access is retained for compatibility.
    - can_modify is migrated into can_edit.
    """
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS user_page_access (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                page_key TEXT NOT NULL,
                can_access BOOLEAN DEFAULT TRUE,
                can_view BOOLEAN DEFAULT TRUE,
                can_add BOOLEAN DEFAULT TRUE,
                can_edit BOOLEAN DEFAULT TRUE,
                can_modify BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, page_key)
            )
        """)
    except Exception:
        pass
    for sql in [
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_view BOOLEAN DEFAULT TRUE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_add BOOLEAN DEFAULT TRUE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_edit BOOLEAN DEFAULT TRUE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "UPDATE user_page_access SET can_view=COALESCE(can_view, can_access, TRUE)",
        "UPDATE user_page_access SET can_add=COALESCE(can_add, can_edit, can_modify, can_access, TRUE)",
        "UPDATE user_page_access SET can_edit=COALESCE(can_edit, can_modify, can_access, TRUE)",
    ]:
        try:
            execute_query(sql)
        except Exception:
            pass

def get_page_definition_by_target(target):
    target = str(target or '').replace('\\', '/')
    for item in APP_PAGE_DEFINITIONS:
        if item['target'] == target:
            return item
    return None

def get_page_definition_by_key(page_key):
    for item in APP_PAGE_DEFINITIONS:
        if item['key'] == page_key:
            return item
    return None

def get_user_page_permissions(username):
    """Fast cached page permissions for normal users."""
    username = str(username or "")
    if not username:
        return {}
    cache_key = f"_page_permissions_cache_{username}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        ensure_page_access_table()
        rows = fetch_all(
            'SELECT page_key, can_view, can_add, can_edit, can_modify, can_access FROM user_page_access WHERE username=?',
            (username,)
        )
        result = {}
        for r in rows:
            can_view = r.get('can_view')
            can_add = r.get('can_add')
            can_edit = r.get('can_edit')
            can_modify = r.get('can_modify')
            legacy = r.get('can_access')
            result[str(r.get('page_key'))] = {
                'can_view': bool(legacy if can_view is None else can_view),
                # Preserve old behavior: previous Edit/Modify controls also grant Add unless Add is explicitly stored.
                'can_add': bool((can_edit if can_add is None else can_add) if legacy is None else (can_add if can_add is not None else legacy)),
                # New Edit means edit/modify existing records. Legacy Modify is merged into Edit.
                'can_edit': bool(legacy if can_edit is None and can_modify is None else (can_edit if can_edit is not None else can_modify)),
            }
        st.session_state[cache_key] = result
        return result
    except Exception:
        st.session_state[cache_key] = {}
        return {}


def _role_default_view(page_def, role):
    return role in page_def.get('default_roles', [])

def _role_default_add(page_def, role):
    # Default Add follows prior edit/save behavior.
    if role == 'super_admin':
        return True
    if role == 'admin':
        return page_def['key'] != 'admin'
    return False

def _role_default_edit(page_def, role):
    # User role can view assigned operational pages, but edit permissions default to admin/super_admin.
    if role == 'super_admin':
        return True
    if role == 'admin':
        return page_def['key'] != 'admin'
    return False

def can_user_access_page(page_def, user=None):
    if not page_def:
        return True
    user = user or st.session_state.get('user', {})
    role = user.get('role', '')
    username = user.get('username', '')
    if role == 'super_admin':
        return True
    perms = get_user_page_permissions(username)
    if page_def['key'] in perms:
        item = perms[page_def['key']]
        if isinstance(item, dict):
            return bool(item.get('can_view', False))
        return bool(item)
    return _role_default_view(page_def, role)

def can_user_add_page(page_def, user=None):
    if not page_def:
        return True
    user = user or st.session_state.get('user', {})
    role = user.get('role', '')
    username = user.get('username', '')
    if role == 'super_admin':
        return True
    perms = get_user_page_permissions(username)
    if page_def['key'] in perms:
        item = perms[page_def['key']]
        if isinstance(item, dict):
            return bool(item.get('can_add', False)) and bool(item.get('can_view', False))
        return bool(item)
    return _role_default_add(page_def, role)

def can_user_edit_page(page_def, user=None):
    if not page_def:
        return True
    user = user or st.session_state.get('user', {})
    role = user.get('role', '')
    username = user.get('username', '')
    if role == 'super_admin':
        return True
    perms = get_user_page_permissions(username)
    if page_def['key'] in perms:
        item = perms[page_def['key']]
        if isinstance(item, dict):
            return bool(item.get('can_edit', False))
        return bool(item)
    return _role_default_edit(page_def, role)

def current_user_can_edit(page_key=None):
    if page_key:
        page_def = get_page_definition_by_key(page_key)
    else:
        page_def = get_page_definition_by_target(detect_current_page_target())
    return can_user_edit_page(page_def)

def current_user_can_add(page_key=None):
    if page_key:
        page_def = get_page_definition_by_key(page_key)
    else:
        page_def = get_page_definition_by_target(detect_current_page_target())
    return can_user_add_page(page_def)

def get_allowed_nav_items(user=None):
    user = user or st.session_state.get('user', {})
    hidden_top_nav_keys = {'delivery_reprint', 'delivery_fifo', 'delivery_edit', 'delivery_list', 'shipment_last', 'shipment_edit', 'shipment_status', 'payment_due', 'payment_edit', 'payment_list'}
    return [
        (p['label'], p['target'])
        for p in APP_PAGE_DEFINITIONS
        if p.get('key') not in hidden_top_nav_keys and can_user_access_page(p, user)
    ]

def detect_current_page_target():
    import inspect
    from pathlib import Path as _Path
    try:
        for frame in inspect.stack():
            file_name = str(frame.filename).replace('\\', '/')
            if '/pages/' in file_name:
                return 'pages/' + _Path(file_name).name
    except Exception:
        pass
    return ''

def require_page_access_for_current_page():
    target = detect_current_page_target()
    if not target:
        return
    page_def = get_page_definition_by_target(target)
    if page_def and not can_user_access_page(page_def):
        st.error('You do not have permission to view this page. Contact the super admin.')
        st.stop()

def render_top_navigation():
    """Exact top module navigation with page-wise user controls.

    Supports both dict navigation items:
        {"target": "...", "label": "..."}
    and tuple/list navigation items:
        ("Label", "target") or ("target", "Label")
    """
    inject_exact_ui_css()
    user = st.session_state.get("user", {})
    nav_items = get_allowed_nav_items(user)
    st.markdown('<div class="exact-nav-card"><div class="exact-nav-title">MODULES</div>', unsafe_allow_html=True)

    if not nav_items:
        st.warning("No module access assigned. Contact Super Admin.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    def _nav_label_target(item):
        if isinstance(item, dict):
            return item.get("label") or item.get("name") or str(item.get("target") or ""), item.get("target") or item.get("page") or ""
        if isinstance(item, (tuple, list)):
            if len(item) >= 2:
                first = str(item[0])
                second = str(item[1])
                # Detect which side is target
                if first.endswith(".py") or first.startswith("pages/") or first == "app.py":
                    return second, first
                return first, second
            if len(item) == 1:
                return str(item[0]), str(item[0])
        return str(item), str(item)

    cols = st.columns(min(len(nav_items), 9))
    for i, item in enumerate(nav_items):
        label, target = _nav_label_target(item)
        with cols[i % len(cols)]:
            try:
                st.page_link(target, label=label)
            except Exception:
                # Fallback to a disabled-looking button if Streamlit cannot resolve a page target.
                st.button(label, disabled=True, key=f"nav_disabled_{i}_{label}")
    st.markdown('</div>', unsafe_allow_html=True)



def top_layout():
    inject_exact_ui_css()
    user = st.session_state.get("user", {"username": "-", "role": "-"})
    if LOGO_PATH.exists():
        logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" />'
    else:
        logo_html = '<div class="exact-app-logo-fallback">FSI</div>'

    st.markdown(
        f"""
        <div class="exact-app-header">
            <div class="exact-app-logo">{logo_html}</div>
            <div class="exact-title">EXPORT SHIPMENT<br>MONITORING SYSTEM</div>
            <div class="exact-user-box">
                User: {user.get('username', '-')}<br>
                Role: {user.get('role', '-')}<br>App Version: {APP_VERSION}<br>
                <span id="liveClock">{datetime.now().strftime('%d-%m-%Y %H:%M')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    render_top_navigation()


def show_header(title, subtitle="EXPORT SHIPMENT MONITORING SYSTEM"):
    inject_exact_ui_css()
    st.markdown(
        f"""
        <div class="exact-page-title-card">
            <h1>{title}</h1>
            <div class="exact-page-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    render_success_message()


def add_total_row(df):
    if df.empty:
        return df
    total_row = {}
    numeric_cols = df.select_dtypes(include="number").columns
    no_total_cols = {"unit_price", "price", "sale_unit_price"}
    for col in df.columns:
        col_key = str(col).lower().strip()
        if col in numeric_cols and col_key not in no_total_cols and "price" not in col_key:
            total_row[col] = df[col].sum()
        elif col == df.columns[0]:
            total_row[col] = "TOTAL"
        else:
            total_row[col] = ""
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

def style_total_row(df):
    def row_style(row):
        if str(row.iloc[0]).upper() == "TOTAL":
            return ["font-weight: 800; background-color: #fff3b0;" for _ in row]
        return ["" for _ in row]
    return df.style.apply(row_style, axis=1)

def style_fifo_balance(df):
    def style_cell(value, column_name):
        if str(column_name).lower() == "balance_qty":
            return "background-color: #d1fae5; color: #065f46; font-weight: 900;"
        return ""
    return df.style.apply(lambda row: [style_cell(row[col], col) for col in df.columns], axis=1)

def show_df(rows, key=None, total=False):
    rows = filter_rows_by_user_access(rows)
    rows = format_date_columns(rows)
    if key:
        df = filter_rows(rows, key)
    else:
        df = pd.DataFrame(rows)
    if total:
        df = add_total_row(df)
    if df.empty:
        st.info("No data available.")
    else:
        st.dataframe(style_total_row(df), width='stretch', hide_index=True)
    return df

def filter_rows(rows, key):
    rows = filter_rows_by_user_access(rows)
    rows = format_date_columns(rows)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No data available.")
        return df

    if "filter_key_counter" not in st.session_state:
        st.session_state.filter_key_counter = {}
    base_key = str(key)
    st.session_state.filter_key_counter[base_key] = st.session_state.filter_key_counter.get(base_key, 0) + 1
    unique_key = f"{base_key}_{st.session_state.filter_key_counter[base_key]}"

    with st.expander("Search / Multiple Field Filters", expanded=True):
        search = st.text_input("Global Search", key=f"global_search_{unique_key}")
        if search:
            mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            df = df[mask]

        f1, f2 = st.columns([1, 2])
        with f1:
            filter_cols = st.multiselect("Fields", list(df.columns), key=f"field_filter_cols_{unique_key}")
        with f2:
            for col in filter_cols:
                values = sorted([str(x) for x in df[col].dropna().unique().tolist()])
                selected_values = st.multiselect(f"Filter {col}", values, key=f"field_filter_{unique_key}_{col}")
                if selected_values:
                    df = df[df[col].astype(str).isin(selected_values)]

    if df.empty:
        st.info("No data available after filter.")
    return df

def show_filtered_df(rows, key, total=False):
    df = filter_rows(rows, key)
    if total:
        df = add_total_row(df)
    if not df.empty:
        st.dataframe(style_total_row(df), width='stretch', hide_index=True)
    return df

def show_fifo_df(rows, key):
    df = filter_rows(rows, key)
    if not df.empty:
        st.dataframe(style_fifo_balance(df), width='stretch', hide_index=True)
    return df

def get_notification_settings():
    rows = fetch_all("SELECT * FROM notification_settings WHERE id=1")
    return rows[0] if rows else {}

def send_email_message(to_email, subject, body):
    settings = get_notification_settings()
    if not settings or not settings.get("enable_email"):
        return False, "Email disabled"
    if not settings.get("sender_email") or not settings.get("app_password"):
        return False, "Sender email/app password not configured"
    msg = EmailMessage()
    msg["From"] = settings["sender_email"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.get("smtp_server") or "smtp.gmail.com", int(settings.get("smtp_port") or 587)) as smtp:
        smtp.starttls()
        smtp.login(settings["sender_email"], settings["app_password"])
        smtp.send_message(msg)
    return True, "Sent"

def notify_event(event_type, subject, body):
    recipients = fetch_all("""
        SELECT recipient_email FROM notification_recipients
        WHERE event_type=? AND is_active=true
    """, (event_type,))
    results = []
    for r in recipients:
        ok, msg = send_email_message(r["recipient_email"], subject, body)
        results.append(f'{r["recipient_email"]}: {msg}')
    return results

def quick_add_supplier():
    with st.expander("+ Add Supplier"):
        name = st.text_input("Supplier Name", key="quick_supplier_name")
        if st.button("Save Supplier", key="quick_supplier_save"):
            if name.strip():
                execute_query("INSERT INTO suppliers (supplier_name) VALUES (?) ON CONFLICT DO NOTHING", (name.strip(),))
                st.success("Supplier added. Refresh/reopen this module if not visible immediately.")

def quick_add_warehouse():
    with st.expander("+ Add Warehouse"):
        name = st.text_input("Warehouse Name", key="quick_warehouse_name")
        if st.button("Save Warehouse", key="quick_warehouse_save"):
            if name.strip():
                execute_query("INSERT INTO warehouses (warehouse_name) VALUES (?) ON CONFLICT DO NOTHING", (name.strip(),))
                st.success("Warehouse added. Refresh/reopen this module if not visible immediately.")

def quick_add_product():
    with st.expander("+ Add Product"):
        c1, c2, c3 = st.columns(3)
        with c1:
            code = st.text_input("Product Code", key="quick_product_code")
            name = st.text_input("Product Name", key="quick_product_name")
        with c2:
            unit = st.text_input("Unit", value="Nos", key="quick_product_unit")
            price = st.number_input("Price", min_value=0.0, key="quick_product_price")
        with c3:
            currency = st.selectbox("Currency", CURRENCIES, key="quick_product_currency")
        if st.button("Save Product", key="quick_product_save"):
            if code.strip() and name.strip():
                execute_query("""
                    INSERT INTO products (product_code, product_name, unit, unit_price, currency)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """, (code.strip(), name.strip(), unit, price, currency))
                st.success("Product added. Refresh/reopen this module if not visible immediately.")

def quick_add_customer():
    with st.expander("+ Add Customer"):
        name = st.text_input("Customer Name", key="quick_customer_name")
        email = st.text_input("Email", key="quick_customer_email")
        whatsapp = st.text_input("WhatsApp No", key="quick_customer_whatsapp")
        terms = fetch_all("SELECT * FROM payment_terms ORDER BY days")
        term_options = {"No Payment Term": None}
        for t in terms:
            term_options[f'{t["term_name"]} - {t["days"]} days'] = t["id"]
        selected_term = st.selectbox("Default Payment Term", list(term_options.keys()), key="quick_customer_payment_term")
        if st.button("Save Customer", key="quick_customer_save"):
            if name.strip():
                execute_query("""
                    INSERT INTO customers (customer_name, email, whatsapp_no, payment_term_id)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """, (name.strip(), email.strip(), whatsapp.strip(), term_options[selected_term]))
                st.success("Customer added. Refresh/reopen this module if not visible immediately.")

def quick_add_payment_term():
    with st.expander("+ Add Payment Term"):
        term = st.text_input("Term Name", key="quick_term_name")
        days = st.number_input("Days", min_value=0, step=1, key="quick_term_days")
        if st.button("Save Payment Term", key="quick_term_save"):
            if term.strip():
                execute_query("INSERT INTO payment_terms (term_name, days) VALUES (?, ?) ON CONFLICT DO NOTHING", (term.strip(), int(days)))
                st.success("Payment term added. Refresh/reopen this module if not visible immediately.")

def edit_button_column(rows, prefix):
    # The visual table shows Edit as last column; actual edit controls appear below for selected row.
    return [dict(r, Edit="Use edit selector below") for r in rows]


def _pdf_wrap_cell(value, style):
    """Wrap PDF table text safely."""
    try:
        safe = html.escape(str(value or "")).replace("\n", "<br/>")
        return Paragraph(safe, style)
    except Exception:
        return str(value or "")

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def to_pdf_bytes(df, title):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle("wrap", parent=styles["Normal"], fontName="Helvetica", fontSize=6.2, leading=7.0, wordWrap="CJK")
    head_style = ParagraphStyle("headwrap", parent=wrap_style, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
    title_style = styles["Title"]
    data = [[_pdf_wrap_cell(c, head_style) for c in list(df.columns)]]
    for row in df.astype(str).values.tolist():
        data.append([_pdf_wrap_cell(cell, wrap_style) for cell in row])
    available_width = landscape(A4)[0] - doc.leftMargin - doc.rightMargin
    col_count = max(len(df.columns), 1)
    table = Table(data, colWidths=[available_width / col_count] * col_count, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b5cab")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6.2),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ]))
    doc.build([Paragraph(title, title_style), Spacer(1,10), table])
    return output.getvalue()

def to_image_bytes(df, title):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        st.warning(f"Image export is unavailable on this server: {exc}")
        return b""
    fig, ax = plt.subplots(figsize=(12, max(3, len(df) * 0.35 + 1.5)))
    ax.axis("off")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    table = ax.table(cellText=df.astype(str).values, colLabels=df.columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    output = io.BytesIO()
    plt.savefig(output, format="png", bbox_inches="tight", dpi=180)
    plt.close(fig)
    return output.getvalue()

def export_buttons(df, report_name):
    if df.empty:
        return
    c1, c2 = st.columns(2)
    c1.download_button("Export Excel", to_excel_bytes(df), f"{report_name}.xlsx")
    c2.download_button("Export PDF", to_pdf_bytes(df, report_name), f"{report_name}.pdf")

def logo_data_uri():
    try:
        if LOGO_PATH.exists():
            data = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
            return f"data:image/png;base64,{data}"
    except Exception:
        pass
    return ""

def parse_date_for_input(value):
    try:
        if value:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return date.today()

def delivery_note_html(data):
    """Commercial invoice print layout inspired by the attached Excel delivery invoice sheet."""
    delivery_date = format_date_ddmmyyyy(data.get("delivery_date", ""))
    due_date = format_date_ddmmyyyy(data.get("payment_due_date", ""))
    po_date = format_date_ddmmyyyy(data.get("po_date", ""))

    items = data.get("items") or []
    if not items:
        qty = float(data.get("qty") or 0)
        unit_price = float(data.get("unit_price") or 0)
        amount = float(data.get("sale_amount") or (qty * unit_price))
        items = [{
            "product_code": data.get("product_code", ""),
            "product_name": data.get("product_name", ""),
            "pallet_no": data.get("pallet_no", ""),
            "box_no": data.get("box_no", ""),
            "qty": qty,
            "unit_price": unit_price,
            "currency": data.get("currency", ""),
            "amount": amount,
            "original_invoice_no": data.get("original_invoice_no", ""),
            "po_number": data.get("po_number", ""),
            "po_date": data.get("po_date", ""),
        }]

    total_qty = sum(float(i.get("qty") or 0) for i in items)
    total_amount = sum(float(i.get("amount") or 0) for i in items)
    currency = data.get("currency", "") or (items[0].get("currency", "") if items else "")
    original_invoice_no = data.get("original_invoice_no", "") or (items[0].get("original_invoice_no", "") if items else "")
    po_number = data.get("po_number", "") or (items[0].get("po_number", "") if items else "")
    po_date = format_date_ddmmyyyy(data.get("po_date", "") or (items[0].get("po_date", "") if items else ""))

    try:
        company_rows = fetch_all("SELECT * FROM company_settings WHERE id=1")
        company = company_rows[0] if company_rows else {}
    except Exception:
        company = {}

    company_name = company.get("company_name") or "Four Star Industries Private Limited"
    company_addr = company.get("address") or "Plant Address"
    company_phone = company.get("phone") or ""
    company_email = company.get("email") or ""
    bank_details = [
        "BANK DETAILS:",
        "BANK ACCOUNT NO : 004330150000003",
        "BANK IFSC CODE : BKID0000043",
        "BANK MICR CODE : 400013080",
        "BANK SWIFT CODE : BKIDINBBPPD",
    ]

    item_rows = ""
    for idx, item in enumerate(items, start=1):
        qty = float(item.get("qty") or 0)
        unit_price = float(item.get("unit_price") or 0)
        amount = float(item.get("amount") or 0)
        desc = f"{item.get('product_code', '')} {item.get('product_name', '')}".strip()
        item_rows += f"""
        <tr>
            <td class="center">{idx}</td>
            <td>{html.escape(desc)}</td>
            <td class="center">{html.escape(str(item.get("original_invoice_no", original_invoice_no)))}</td>
            <td class="right">{qty:,.3f}</td>
            <td class="right">{unit_price:,.4f}</td>
            <td class="right">{amount:,.3f}</td>
        </tr>
        """

    logo_src = logo_data_uri()
    logo_html = f'<img src="{logo_src}" class="logo">' if logo_src else '<div class="logo-text">FSI</div>'
    ship_to = data.get("ship_to", "") or "As per delivery instruction / purchase order"
    buyer = data.get("customer_name", "")

    return f"""
    <html>
    <head>
    <style>
    @page {{ size: A4 portrait; margin: 10mm; }}
    body {{ font-family: Aptos, Arial, sans-serif; color:#111827; margin:0; padding:0; font-size:11px; }}
    .sheet {{ width:100%; border-collapse:collapse; }}
    .sheet td, .sheet th {{ border:1px solid #111827; padding:6px; vertical-align:top; }}
    .no-border td {{ border:0; }}
    .title {{ font-size:22px; font-weight:900; text-align:right; color:#111827; }}
    .section-title {{ font-weight:900; background:#f3f4f6; color:#111827; }}
    .logo {{ max-width:155px; max-height:62px; }}
    .logo-text {{ font-size:32px; font-weight:900; color:#003B73; }}
    .bold {{ font-weight:900; }}
    .center {{ text-align:center; }}
    .right {{ text-align:right; }}
    .small {{ font-size:10px; line-height:1.35; }}
    .items th {{ background:#f3f4f6; font-weight:900; text-align:center; }}
    .total {{ font-weight:900; background:#fef3c7; }}
    .bank {{ line-height:1.55; }}
    .signature {{ height:54px; text-align:right; vertical-align:bottom !important; font-weight:900; }}
    .print-btn {{ position:fixed; top:10px; right:10px; padding:8px 12px; background:#1B6DB5; color:white; border:0; border-radius:6px; font-weight:800; }}
    @media print {{ .print-btn {{ display:none; }} body {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
    </style>
    </head>
    <body>
    <button class="print-btn" onclick="window.print()">Print</button>

    <table class="sheet">
        <tr>
            <td colspan="4" rowspan="2">{logo_html}<br><span class="bold">{html.escape(company_name)}</span><br><span class="small">{html.escape(str(company_addr))}<br>{html.escape(str(company_phone))} {html.escape(str(company_email))}</span></td>
            <td colspan="3" class="title">COMMERCIAL INVOICE</td>
        </tr>
        <tr>
            <td colspan="2" class="section-title">VOUCHER #</td>
            <td class="bold">{html.escape(str(data.get("delivery_invoice_no", "")))}</td>
        </tr>
        <tr>
            <td colspan="4" class="section-title">PLANT ADDRESS</td>
            <td colspan="2" class="section-title">DATE</td>
            <td>{delivery_date}</td>
        </tr>
        <tr>
            <td colspan="4">{html.escape(str(company_addr))}</td>
            <td colspan="2" class="section-title">PURCHASE ORDER #</td>
            <td>{html.escape(str(po_number))}</td>
        </tr>
        <tr>
            <td colspan="4"></td>
            <td colspan="2" class="section-title">PURCHASE ORDER DATE</td>
            <td>{po_date}</td>
        </tr>
        <tr>
            <td colspan="4" class="section-title">BUYER / BILL TO</td>
            <td colspan="3" class="section-title">SHIP TO</td>
        </tr>
        <tr>
            <td colspan="4" style="height:70px;"><span class="bold">{html.escape(str(buyer))}</span><br><span class="small">Customer address as per master / PO</span></td>
            <td colspan="3" style="height:70px;">{html.escape(str(ship_to))}</td>
        </tr>
        <tr>
            <td class="section-title">VEHICLE #</td>
            <td colspan="2" class="section-title">SHIP VIA</td>
            <td class="section-title">PAYMENT TERM</td>
            <td class="section-title">DUE DATE</td>
            <td colspan="2" class="section-title">ASN #</td>
        </tr>
        <tr>
            <td>{html.escape(str(data.get("vehicle_no", "")))}</td>
            <td colspan="2">{html.escape(str(data.get("ship_via", "Road")))}</td>
            <td>{html.escape(str(data.get("payment_term", "")))}</td>
            <td>{due_date}</td>
            <td colspan="2">{html.escape(str(data.get("asn_no", "")))}</td>
        </tr>
    </table>

    <table class="sheet items" style="margin-top:8px;">
        <tr>
            <th style="width:7%;">ITEM #</th>
            <th>DESCRIPTION</th>
            <th style="width:18%;">FSI ORIGINAL INVOICE #</th>
            <th style="width:12%;">QUANTITY<br>(PCS)</th>
            <th style="width:12%;">PRICE</th>
            <th style="width:14%;">AMOUNT</th>
        </tr>
        {item_rows}
        <tr>
            <td colspan="3" class="right total">SUBTOTAL</td>
            <td class="right total">{total_qty:,.3f}</td>
            <td></td>
            <td class="right total">{total_amount:,.3f}</td>
        </tr>
        <tr>
            <td colspan="5" class="right bold">TAX</td>
            <td class="right">0.00</td>
        </tr>
        <tr>
            <td colspan="5" class="right bold">OTHER</td>
            <td class="right">0.00</td>
        </tr>
        <tr>
            <td colspan="5" class="right total">TOTAL ({html.escape(str(currency))})</td>
            <td class="right total">{total_amount:,.3f}</td>
        </tr>
    </table>

    <table class="sheet" style="margin-top:8px;">
        <tr>
            <td colspan="4" class="section-title">PACKAGING DETAILS:</td>
            <td colspan="3" class="section-title">REFERENCES</td>
        </tr>
        <tr>
            <td colspan="4">{html.escape(str(data.get("packaging_details", "As per shipment packing details")))}</td>
            <td colspan="3">
                Original Invoice: <b>{html.escape(str(original_invoice_no))}</b><br>
                Shipment No: <b>{html.escape(str(data.get("shipment_no", "")))}</b><br>
                PO: <b>{html.escape(str(po_number))}</b> / <b>{po_date}</b>
            </td>
        </tr>
        <tr>
            <td colspan="4" class="bank">{'<br>'.join(html.escape(x) for x in bank_details)}</td>
            <td colspan="3" class="signature">Authorised Signatory</td>
        </tr>
    </table>
    </body>
    </html>
    """

def build_delivery_invoice_print_data(delivery_invoice_no):
    rows = fetch_all("""
        SELECT d.*, c.customer_name, c.address AS customer_address, c.phone AS customer_phone, c.email AS customer_email,
               s.shipment_no, s.invoice_no AS original_invoice_no,
               stm.ship_to_name, stm.ship_to_id, stm.addressline1 AS ship_to_addressline1, stm.addressline2 AS ship_to_addressline2, stm.addressline3 AS ship_to_addressline3,
               stm.vendor_gstin AS ship_to_vendor_gstin, stm.vendor_phone AS ship_to_vendor_phone, stm.vendor_email AS ship_to_vendor_email,
               b.product_id, s.warehouse_id, w.warehouse_name,
               p.product_code, p.product_name,
               COALESCE(d.po_number, s.po_number, p.po_number) AS po_number,
               COALESCE(d.po_date, s.po_date, p.po_date) AS po_date,
               b.pallet_no, b.box_no
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN ship_to_masters stm ON d.ship_to_master_id = stm.id
        WHERE d.delivery_invoice_no=?
        ORDER BY d.id
    """, (delivery_invoice_no,))
    rows = filter_rows_by_user_access(rows)
    if not rows:
        return None

    first = rows[0]
    items = []
    total_qty = 0
    total_amount = 0
    for r in rows:
        qty = float(r.get("delivered_qty") or 0)
        amount = float(r.get("sale_amount") or 0)
        total_qty += qty
        total_amount += amount
        items.append({
            "original_invoice_no": r.get("original_invoice_no", ""),
            "product_code": r.get("product_code", ""),
            "product_name": r.get("product_name", ""),
            "po_number": r.get("po_number", ""),
            "po_date": r.get("po_date", ""),
            "pallet_no": r.get("pallet_no", ""),
            "box_no": r.get("box_no", "") or "-",
            "qty": qty,
            "unit_price": float(r.get("unit_price") or 0),
            "currency": r.get("currency", ""),
            "amount": amount,
        })

    return {
        "customer_name": first.get("customer_name", ""),
        "customer_address": first.get("customer_address", ""),
        "customer_phone": first.get("customer_phone", ""),
        "customer_email": first.get("customer_email", ""),
        "ship_to_name": first.get("ship_to_name", ""),
        "ship_to_id": first.get("ship_to_id", ""),
        "ship_to_addressline1": first.get("ship_to_addressline1", ""),
        "ship_to_addressline2": first.get("ship_to_addressline2", ""),
        "ship_to_addressline3": first.get("ship_to_addressline3", ""),
        "ship_to_vendor_gstin": first.get("ship_to_vendor_gstin", ""),
        "ship_to_vendor_phone": first.get("ship_to_vendor_phone", ""),
        "ship_to_vendor_email": first.get("ship_to_vendor_email", ""),
        "vehicle_number": first.get("vehicle_number", ""),
        "asn_number": first.get("asn_number", ""),
        "asn_date": first.get("asn_date", ""),
        "packaging_details": first.get("packaging_details", ""),
        "shipment_no": first.get("shipment_no", ""),
        "original_invoice_no": first.get("original_invoice_no", ""),
        "delivery_invoice_no": delivery_invoice_no,
        "delivery_date": first.get("delivery_date", ""),
        "payment_term": f'{first.get("payment_terms_days", 0)} Days',
        "payment_due_date": first.get("payment_due_date", ""),
        "currency": first.get("currency", ""),
        "qty": total_qty,
        "sale_amount": total_amount,
        "po_number": first.get("po_number", ""),
        "po_date": first.get("po_date", ""),
        "items": items,
    }

def print_popup(html):
    components.html(f"""
    <script>
      const w = window.open('', '_blank', 'width=900,height=700');
      w.document.write(`{html}`);
      w.document.close();
      w.focus();
      setTimeout(() => w.print(), 500);
    </script>
    """, height=0)

def require_roles(allowed):
    """Role gate with page-wise Edit permission override."""
    user = st.session_state.get('user', {})
    role = user.get('role', '')
    if role in allowed or role == 'super_admin':
        return
    try:
        if current_user_can_edit():
            return
        page_def = get_page_definition_by_target(detect_current_page_target())
        if page_def and can_user_access_page(page_def, user):
            return
    except Exception:
        pass
    st.error("You do not have permission to access this module.")
    st.stop()


















def login_page():
    force_exact_login_page()

def overdue_rows():
    return fetch_all("""
        SELECT
            d.id AS delivery_id,
            d.delivery_invoice_no,
            c.customer_name,
            c.email,
            c.whatsapp_no,
            d.delivery_date,
            d.payment_due_date,
            d.sale_amount,
            COALESCE(SUM(p.payment_amount), 0) AS paid_amount,
            d.sale_amount - COALESCE(SUM(p.payment_amount), 0) AS pending_amount
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payments p ON d.id = p.delivery_id
        GROUP BY
            d.id,
            d.delivery_invoice_no,
            c.customer_name,
            c.email,
            c.whatsapp_no,
            d.delivery_date,
            d.payment_due_date,
            d.sale_amount
        HAVING
            d.sale_amount - COALESCE(SUM(p.payment_amount), 0) > 0
            AND d.payment_due_date < CURRENT_DATE
        ORDER BY d.payment_due_date
    """)
    return fetch_all("""
        SELECT d.id delivery_id, d.delivery_invoice_no, c.customer_name, c.email, c.whatsapp_no,
               d.delivery_date, d.payment_due_date, d.sale_amount,
               IFNULL(SUM(p.payment_amount),0) paid_amount,
               d.sale_amount - IFNULL(SUM(p.payment_amount),0) pending_amount
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payments p ON d.id = p.delivery_id
        GROUP BY d.id
        HAVING pending_amount > 0 AND date(d.payment_due_date) < date('now')
        ORDER BY d.payment_due_date
    """)

def whatsapp_link(phone, message):
    phone = str(phone or "").replace("+", "").replace(" ", "").replace("-", "")
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

def customer_form():
    require_roles(("admin", "super_admin"))
    st.subheader("Customer Master")
    terms = fetch_all("SELECT * FROM payment_terms ORDER BY days")
    term_options = {"No Payment Term": None}
    for t in terms:
        term_options[f'{t["term_name"]} - {t["days"]} days'] = t["id"]

    c1, c2 = st.columns(2)
    with c1:
        customer_name = st.text_input("Customer Name", key="customer_name")
        contact_person = st.text_input("Contact Person", key="customer_contact_person")
        email = st.text_input("Email", key="customer_email")
    with c2:
        phone = st.text_input("Phone", key="customer_phone")
        whatsapp_no = st.text_input("WhatsApp No", key="customer_whatsapp_no")
        address = st.text_area("Address", key="customer_address")
        selected_term = st.selectbox("Default Payment Term", list(term_options.keys()), key="customer_payment_term")

    if st.button("Save Customer Master", type="primary", key="save_customer_master"):
        try:
            execute_query("""
                INSERT INTO customers
                (customer_name, contact_person, email, phone, whatsapp_no, address, payment_term_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_name, contact_person, email, phone, whatsapp_no, address, term_options[selected_term]))
            st.success("Customer saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate customer found.")

    rows = fetch_all("""
        SELECT c.id, c.customer_name, c.contact_person, c.email, c.phone, c.whatsapp_no,
               pt.term_name AS payment_term, c.address
        FROM customers c
        LEFT JOIN payment_terms pt ON c.payment_term_id = pt.id
        ORDER BY c.id DESC
    """)
    show_filtered_df(edit_button_column(rows, "customers"), "master_customers", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader("Edit Customer Master")
        old_rows = fetch_all("SELECT * FROM customers ORDER BY id DESC")
        if old_rows:
            row_map = {f'{r["id"]} | {r["customer_name"]}': r for r in old_rows}
            selected = row_map[st.selectbox("Select Customer to Edit", list(row_map.keys()), key="edit_customer_select")]
            current_term_id = selected.get("payment_term_id")
            selected_term_label = "No Payment Term"
            for label, tid in term_options.items():
                if tid == current_term_id:
                    selected_term_label = label
                    break

            e1, e2 = st.columns(2)
            with e1:
                e_customer_name = st.text_input("Edit Customer Name", selected.get("customer_name") or "", key="edit_customer_name")
                e_contact_person = st.text_input("Edit Contact Person", selected.get("contact_person") or "", key="edit_customer_contact")
                e_email = st.text_input("Edit Email", selected.get("email") or "", key="edit_customer_email")
            with e2:
                e_phone = st.text_input("Edit Phone", selected.get("phone") or "", key="edit_customer_phone")
                e_whatsapp = st.text_input("Edit WhatsApp No", selected.get("whatsapp_no") or "", key="edit_customer_whatsapp")
                e_address = st.text_area("Edit Address", selected.get("address") or "", key="edit_customer_address")
                e_term = st.selectbox("Edit Default Payment Term", list(term_options.keys()), index=list(term_options.keys()).index(selected_term_label), key="edit_customer_term")

            if st.button("Update Customer", type="primary", key="update_customer_master"):
                execute_query("""
                    UPDATE customers
                    SET customer_name=?, contact_person=?, email=?, phone=?, whatsapp_no=?, address=?, payment_term_id=?
                    WHERE id=?
                """, (e_customer_name, e_contact_person, e_email, e_phone, e_whatsapp, e_address, term_options[e_term], selected["id"]))
                st.success("Customer updated successfully.")
                st.rerun()

def product_form():
    require_roles(("admin", "super_admin"))
    st.subheader("Product Master")

    c1, c2 = st.columns(2)
    with c1:
        product_code = st.text_input("Product Code", key="product_code")
        product_name = st.text_input("Product Name", key="product_name")
        program = st.text_input("Program", key="product_program")
        assy_plant = st.text_input("Assy Plant", key="product_assy_plant")
        unit = st.text_input("Unit", value="Nos", key="product_unit")
        po_number = st.text_input("PO Number", key="product_po_number")
    with c2:
        unit_price = st.number_input("Price", min_value=0.0, step=0.001, format="%.3f", key="product_unit_price")
        currency = st.selectbox("Currency", CURRENCIES, key="product_currency")
        weight = st.number_input("Weight", min_value=0.0, step=1.0, key="product_weight")
        lcr_weekly = st.number_input("LCR Weekly", min_value=0.0, step=1.0, key="product_lcr_weekly")
        mcr_weekly = st.number_input("MCR Weekly", min_value=0.0, step=1.0, key="product_mcr_weekly")
        po_date = st.date_input("PO Date", value=date.today(), key="product_po_date")
        two_months_inventory = lcr_weekly * 8
        st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {two_months_inventory:,.3f}</div>', unsafe_allow_html=True)

    if st.button("Save Product Master", type="primary", key="save_product_master"):
        try:
            execute_query("""
                INSERT INTO products
                (product_code, product_name, program, assy_plant, unit, unit_price, currency, weight,
                 lcr_weekly, mcr_weekly, two_months_inventory, po_number, po_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (product_code, product_name, program, assy_plant, unit, unit_price, currency, weight,
                  lcr_weekly, mcr_weekly, two_months_inventory, po_number, str(po_date)))
            st.success("Product saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate product code found.")

    rows = fetch_all("""
        SELECT id, product_code, product_name, program, assy_plant, unit, unit_price, currency,
               weight, lcr_weekly, mcr_weekly, two_months_inventory, po_number, po_date
        FROM products
        ORDER BY id DESC
    """)
    show_filtered_df(edit_button_column(rows, "products"), "master_products", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader("Edit Product Master")
        old_rows = fetch_all("SELECT * FROM products ORDER BY id DESC")
        if old_rows:
            row_map = {f'{r["id"]} | {r["product_code"]} | {r["product_name"]}': r for r in old_rows}
            selected_key = st.selectbox("Select Product Master Entry to Edit", list(row_map.keys()), key="edit_product_select")
            selected = row_map[selected_key]
            sid = selected["id"]

            e1, e2 = st.columns(2)
            with e1:
                e_product_code = st.text_input("Edit Product Code", selected.get("product_code") or "", key=f"edit_product_code_{sid}")
                e_product_name = st.text_input("Edit Product Name", selected.get("product_name") or "", key=f"edit_product_name_{sid}")
                e_program = st.text_input("Edit Program", selected.get("program") or "", key=f"edit_product_program_{sid}")
                e_assy_plant = st.text_input("Edit Assy Plant", selected.get("assy_plant") or "", key=f"edit_product_assy_plant_{sid}")
                e_unit = st.text_input("Edit Unit", selected.get("unit") or "Nos", key=f"edit_product_unit_{sid}")
                e_po_number = st.text_input("Edit PO Number", selected.get("po_number") or "", key=f"edit_product_po_number_{sid}")
            with e2:
                e_unit_price = st.number_input("Edit Price", min_value=0.0, value=float(selected.get("unit_price") or 0), step=0.001, format="%.3f", key=f"edit_product_unit_price_{sid}")
                current_currency = selected.get("currency") or "INR"
                e_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(current_currency) if current_currency in CURRENCIES else 0, key=f"edit_product_currency_{sid}")
                e_weight = st.number_input("Edit Weight", min_value=0.0, value=float(selected.get("weight") or 0), step=1.0, key=f"edit_product_weight_{sid}")
                e_lcr_weekly = st.number_input("Edit LCR Weekly", min_value=0.0, value=float(selected.get("lcr_weekly") or 0), step=1.0, key=f"edit_product_lcr_weekly_{sid}")
                e_mcr_weekly = st.number_input("Edit MCR Weekly", min_value=0.0, value=float(selected.get("mcr_weekly") or 0), step=1.0, key=f"edit_product_mcr_weekly_{sid}")
                e_po_date = st.date_input("Edit PO Date", value=parse_date_for_input(selected.get("po_date")), key=f"edit_product_po_date_{sid}")
                e_two_months_inventory = e_lcr_weekly * 8
                st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {e_two_months_inventory:,.3f}</div>', unsafe_allow_html=True)

            if st.button("Update Product Master", type="primary", key=f"update_product_master_{sid}"):
                try:
                    execute_query("""
                        UPDATE products
                        SET product_code=?, product_name=?, program=?, assy_plant=?, unit=?,
                            unit_price=?, currency=?, weight=?, lcr_weekly=?, mcr_weekly=?,
                            two_months_inventory=?, po_number=?, po_date=?
                        WHERE id=?
                    """, (e_product_code, e_product_name, e_program, e_assy_plant, e_unit,
                          e_unit_price, e_currency, e_weight, e_lcr_weekly, e_mcr_weekly,
                          e_two_months_inventory, e_po_number, str(e_po_date), sid))
                    st.success("Product updated successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Duplicate product code found.")

            st.divider()
            st.subheader("Delete Product Master")
            st.warning("Delete requires your login password.")
            delete_password = st.text_input("Password to Delete Product", type="password", key=f"delete_product_password_{sid}")
            if st.button("Delete Product", key=f"delete_product_btn_{sid}"):
                if delete_record_with_password("products", sid, delete_password, f"Product {selected.get('product_code')}"):
                    st.rerun()

    st.divider()
    st.subheader("Product Effective Price History")
    ensure_product_price_history_table()
    product_rows_for_price = fetch_all("SELECT id, product_code, product_name, unit_price, currency FROM products ORDER BY product_code")
    if product_rows_for_price:
        price_product_map = {
            f'{r["product_code"]} | {r.get("product_name") or ""}': r
            for r in product_rows_for_price
        }
        ph_selected_label = st.selectbox("Select Product for Price Period", list(price_product_map.keys()), key="price_history_product_select")
        ph_product = price_product_map[ph_selected_label]
        ph_c1, ph_c2, ph_c3, ph_c4 = st.columns(4)
        with ph_c1:
            ph_start = st.date_input("Start Date", value=date.today(), key="price_history_start_date")
        with ph_c2:
            ph_current = st.checkbox("Current Price / No End Date", value=True, key="price_history_current")
            ph_end = None if ph_current else st.date_input("End Date", value=date.today(), key="price_history_end_date")
        with ph_c3:
            ph_price = st.number_input("Effective Price", min_value=0.0, step=0.001, format="%.3f", value=float(ph_product.get("unit_price") or 0), key="price_history_price")
        with ph_c4:
            ph_currency = st.selectbox("Effective Currency", CURRENCIES, index=CURRENCIES.index(ph_product.get("currency") or "USD") if (ph_product.get("currency") or "USD") in CURRENCIES else 0, key="price_history_currency")

        ph_p1, ph_p2, ph_p3 = st.columns([1.2, 1.0, 1.8])
        with ph_p1:
            ph_po_number = st.text_input("PO Number", value=str(ph_product.get("po_number") or ""), key="price_history_po_number")
        with ph_p2:
            ph_po_date = st.date_input("PO Date", value=parse_date_for_input(ph_product.get("po_date")), key="price_history_po_date")
        with ph_p3:
            ph_po_copy_file = st.file_uploader("Attach PO Copy PDF", type=["pdf"], key="price_history_po_copy_pdf")
        ph_remarks = st.text_input("Price Remarks", key="price_history_remarks", placeholder="Example: 2026 current price")
        if st.button("Save Effective Price Period", type="primary", key="save_product_price_history"):
            if ph_end and ph_end < ph_start:
                st.error("End Date cannot be before Start Date.")
            else:
                price_history_po_copy_path = None
                try:
                    if ph_po_copy_file:
                        safe_po = str(ph_po_number or "PO").replace("/", "_").replace("\\", "_").replace(" ", "_")
                        price_history_po_copy_path = save_upload(ph_po_copy_file, f"product_price_po_{ph_product['id']}_{safe_po}")
                except Exception:
                    price_history_po_copy_path = None

                execute_query("""
                    INSERT INTO product_price_history
                    (product_id, currency, price, start_date, end_date, remarks, po_number, po_date, po_copy_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ph_product["id"], ph_currency, ph_price, str(ph_start), str(ph_end) if ph_end else None,
                    ph_remarks, ph_po_number.strip(), str(ph_po_date), price_history_po_copy_path
                ))
                # Also update product master price and PO reference if this is current/no-end price.
                if ph_current:
                    execute_query("UPDATE products SET unit_price=?, currency=?, po_number=?, po_date=? WHERE id=?", (ph_price, ph_currency, ph_po_number.strip(), str(ph_po_date), ph_product["id"]))
                st.success("Effective price period saved successfully.")
                st.rerun()

        ph_rows = fetch_all("""
            SELECT h.id, p.product_code, p.product_name, h.start_date, h.end_date, h.price, h.currency,
                   h.po_number, h.po_date, h.po_copy_path, h.remarks
            FROM product_price_history h
            JOIN products p ON p.id = h.product_id
            WHERE h.product_id=?
            ORDER BY h.start_date DESC, h.id DESC
        """, (ph_product["id"],))
        show_filtered_df(ph_rows, "product_price_history", total=False)

        st.divider()
        st.subheader("Edit Product Effective Price History")
        st.caption("Editing price history does not change existing shipment, delivery or payment transaction records.")

        if ph_rows:
            ph_edit_map = {
                f'{r.get("id")} | {r.get("product_code")} | {format_date_ddmmyyyy(r.get("start_date"))} to {format_date_ddmmyyyy(r.get("end_date")) if r.get("end_date") else "Current"} | {format_decimal_3(r.get("price"), r.get("currency"))} | PO {r.get("po_number") or "-"}': r
                for r in ph_rows
            }
            ph_edit_key = st.selectbox("Select Price History Record to Edit", list(ph_edit_map.keys()), key="edit_price_history_select")
            ph_edit = ph_edit_map[ph_edit_key]
            ph_edit_id = ph_edit.get("id")

            eh1, eh2, eh3, eh4 = st.columns(4)
            with eh1:
                e_ph_start = st.date_input("Edit Start Date", value=parse_date_for_input(ph_edit.get("start_date")), key=f"edit_ph_start_{ph_edit_id}")
            with eh2:
                e_ph_current = st.checkbox("Edit Current Price / No End Date", value=False if ph_edit.get("end_date") else True, key=f"edit_ph_current_{ph_edit_id}")
                e_ph_end = None if e_ph_current else st.date_input("Edit End Date", value=parse_date_for_input(ph_edit.get("end_date")), key=f"edit_ph_end_{ph_edit_id}")
            with eh3:
                e_ph_price = st.number_input("Edit Effective Price", min_value=0.0, value=float(ph_edit.get("price") or 0), step=0.001, format="%.3f", key=f"edit_ph_price_{ph_edit_id}")
            with eh4:
                current_edit_currency = ph_edit.get("currency") or ph_product.get("currency") or "USD"
                e_ph_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(current_edit_currency) if current_edit_currency in CURRENCIES else 0, key=f"edit_ph_currency_{ph_edit_id}")

            ep1, ep2, ep3 = st.columns([1.2, 1.0, 1.8])
            with ep1:
                e_ph_po_number = st.text_input("Edit PO Number", value=str(ph_edit.get("po_number") or ""), key=f"edit_ph_po_number_{ph_edit_id}")
            with ep2:
                e_ph_po_date = st.date_input("Edit PO Date", value=parse_date_for_input(ph_edit.get("po_date")), key=f"edit_ph_po_date_{ph_edit_id}")
            with ep3:
                e_ph_po_copy_file = st.file_uploader("Replace / Attach PO Copy PDF", type=["pdf"], key=f"edit_ph_po_copy_pdf_{ph_edit_id}")

            e_ph_remarks = st.text_input("Edit Price Remarks", value=str(ph_edit.get("remarks") or ""), key=f"edit_ph_remarks_{ph_edit_id}")

            existing_copy_path = ph_edit.get("po_copy_path")
            if existing_copy_path:
                existing_path_obj = Path(str(existing_copy_path))
                if existing_path_obj.exists():
                    try:
                        with open(existing_path_obj, "rb") as _existing_po:
                            st.download_button(
                                "Download Current PO Copy",
                                data=_existing_po.read(),
                                file_name=existing_path_obj.name,
                                mime="application/pdf",
                                key=f"download_current_po_copy_{ph_edit_id}"
                            )
                    except Exception:
                        st.caption(f"Current PO copy path: {existing_copy_path}")
                else:
                    st.caption(f"Current PO copy path saved but file not found: {existing_copy_path}")

            if st.button("Update Selected Price History Record", type="primary", key=f"update_price_history_{ph_edit_id}"):
                if e_ph_end and e_ph_end < e_ph_start:
                    st.error("End Date cannot be before Start Date.")
                else:
                    updated_po_copy_path = existing_copy_path
                    try:
                        if e_ph_po_copy_file:
                            safe_po = str(e_ph_po_number or "PO").replace("/", "_").replace("\\", "_").replace(" ", "_")
                            updated_po_copy_path = save_upload(e_ph_po_copy_file, f"product_price_po_edit_{ph_product['id']}_{ph_edit_id}_{safe_po}")
                    except Exception:
                        updated_po_copy_path = existing_copy_path

                    execute_query("""
                        UPDATE product_price_history
                        SET start_date=?, end_date=?, price=?, currency=?, remarks=?,
                            po_number=?, po_date=?, po_copy_path=?
                        WHERE id=?
                    """, (
                        str(e_ph_start), str(e_ph_end) if e_ph_end else None, e_ph_price, e_ph_currency, e_ph_remarks,
                        e_ph_po_number.strip(), str(e_ph_po_date), updated_po_copy_path, ph_edit_id
                    ))

                    # Only current/open price updates Product Master price/PO reference. Existing transactions are not updated.
                    if e_ph_current:
                        execute_query(
                            "UPDATE products SET unit_price=?, currency=?, po_number=?, po_date=? WHERE id=?",
                            (e_ph_price, e_ph_currency, e_ph_po_number.strip(), str(e_ph_po_date), ph_product["id"])
                        )

                    st.success("Price history record updated successfully. Existing shipment/delivery/payment transactions are unchanged.")
                    st.rerun()


        po_copy_rows = [r for r in (ph_rows or []) if r.get("po_copy_path")]
        if po_copy_rows:
            st.markdown("#### Download PO Copies")
            for rr in po_copy_rows:
                po_path = Path(str(rr.get("po_copy_path") or ""))
                if po_path.exists():
                    try:
                        with open(po_path, "rb") as _po_file:
                            st.download_button(
                                label=f"Download PO Copy - {rr.get('po_number') or rr.get('id')}",
                                data=_po_file.read(),
                                file_name=po_path.name,
                                mime="application/pdf",
                                key=f"download_price_history_po_{rr.get('id')}"
                            )
                    except Exception:
                        st.caption(f"PO copy saved but could not be read: {po_path}")
                else:
                    st.caption(f"PO copy file not found for history ID {rr.get('id')}: {po_path}")


def master_form(title, table, fields, allowed_roles=("admin", "super_admin")):
    require_roles(allowed_roles)
    st.subheader(title)
    values = {}
    cols = st.columns(2)
    for i, field in enumerate(fields):
        with cols[i % 2]:
            if field in ("days", "unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory", "shipment_time_days"):
                values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0 if field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 0, step=0.001 if field in ("unit_price",) else (1.0 if field in ("weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 1), key=f"{table}_{field}")
            elif field == "currency":
                values[field] = st.selectbox("Currency", CURRENCIES, key=f"{table}_{field}")
            else:
                values[field] = st.text_input(field.replace("_", " ").title(), key=f"{table}_{field}")
    if st.button(f"Save {title}", type="primary", key=f"save_{table}"):
        try:
            execute_query(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})", tuple(values.values()))
            st.success(f"{title} saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate value found. Please check unique fields.")
    show_filtered_df(edit_button_column(fetch_all(f"SELECT * FROM {table} ORDER BY id DESC"), table), f"master_{table}", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader(f"Edit {title}")
        rows = fetch_all(f"SELECT * FROM {table} ORDER BY id DESC")
        if rows:
            row_map = {f'{r["id"]} | ' + str(r.get(fields[0], "")): r for r in rows}
            selected = row_map[st.selectbox(f"Select {title} Entry to Edit", list(row_map.keys()), key=f"edit_select_{table}")]
            edit_values = {}
            ecols = st.columns(2)
            for i, field in enumerate(fields):
                with ecols[i % 2]:
                    if field in ("days", "shipment_time_days"):
                        edit_values[field] = st.number_input(field.replace("_", " ").title(), min_value=0, value=int(selected.get(field) or 0), step=1, key=f"edit_{table}_{field}")
                    elif field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory"):
                        edit_values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0, value=float(selected.get(field) or 0), step=0.001 if field == "unit_price" else 1.0, key=f"edit_{table}_{field}")
                    elif field == "currency":
                        current = selected.get(field) or "INR"
                        edit_values[field] = st.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(current) if current in CURRENCIES else 0, key=f"edit_{table}_{field}")
                    else:
                        edit_values[field] = st.text_input(field.replace("_", " ").title(), value=str(selected.get(field) or ""), key=f"edit_{table}_{field}")
            if st.button(f"Update {title}", type="primary", key=f"update_{table}"):
                set_clause = ", ".join([f"{f}=?" for f in fields])
                execute_query(f"UPDATE {table} SET {set_clause} WHERE id=?", tuple(edit_values.values()) + (selected["id"],))
                st.success(f"{title} updated successfully.")
                st.rerun()

            st.divider()
            st.subheader("Delete Master Entry")
            st.warning("Delete requires your login password.")
            delete_password = st.text_input("Password to Delete", type="password", key=f"delete_{table}_{selected['id']}")
            if st.button("Delete Selected Entry", key=f"delete_btn_{table}_{selected['id']}"):
                if delete_record_with_password(table, selected["id"], delete_password, f"{title}"):
                    st.rerun()

def transaction_selector(rows, key, label_field):
    data = []
    for r in rows:
        item = dict(r)
        item["Select"] = False
        data.append(item)
    if not data:
        st.info("No records available.")
        return None, pd.DataFrame()
    cols = ["Select"] + [c for c in data[0].keys() if c != "Select"]
    df = pd.DataFrame(format_date_columns(data))[cols]
    edited = st.data_editor(
        df,
        width='stretch',
        hide_index=True,
        key=key,
        column_config={"Select": st.column_config.CheckboxColumn("Select", default=False)},
        disabled=[c for c in cols if c != "Select"]
    )
    selected = None
    if "Select" in edited.columns:
        selected_rows = edited[edited["Select"] == True]
        if not selected_rows.empty:
            selected_id = int(selected_rows.iloc[0]["id"]) if "id" in selected_rows.columns else None
            if selected_id:
                selected = next((r for r in rows if int(r["id"]) == selected_id), None)
    return selected, edited

def reopen_record_message(record_type, record_id):
    st.info(f"Reopen in new window requested for {record_type} ID {record_id}. Streamlit opens secure edit forms inside the current app page; use the edit panel below for modification.")

def monday_of_date(value):
    if not value:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.strptime(value[:10], "%Y-%m-%d").date()
        else:
            dt = value
        return (dt - timedelta(days=dt.weekday())).isoformat()
    except Exception:
        return str(value)

def parse_db_date(value):
    """Return a Python date for YYYY-MM-DD/date/datetime values, otherwise None."""
    if value in (None, ""):
        return None
    try:
        if hasattr(value, "date") and not isinstance(value, date):
            return value.date()
        if hasattr(value, "strftime") and not isinstance(value, str):
            return value
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def normalize_coverage_plan_mondays(product_id):
    rows = fetch_all("""
        SELECT id, week_no, plan_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    """, (product_id,))
    if not rows:
        return
    first_date = rows[0].get("plan_date") or date.today().isoformat()
    first_monday = datetime.strptime(monday_of_date(first_date), "%Y-%m-%d").date()
    for i, row in enumerate(rows):
        monday_date = first_monday + timedelta(days=7*i)
        execute_query("""
            UPDATE coverage_plan_lines
            SET week_no=?, plan_date=?
            WHERE id=?
        """, (i + 1, monday_date.isoformat(), row["id"]))

def deduplicate_coverage_plan_dates(product_id):
    """Keep one row per product/date while preserving transaction quantities as much as possible."""
    dup_dates = fetch_all("""
        SELECT plan_date, COUNT(*) AS c
        FROM coverage_plan_lines
        WHERE product_id=? AND plan_date IS NOT NULL
        GROUP BY plan_date
        HAVING COUNT(*) > 1
    """, (product_id,))
    for d in dup_dates:
        plan_date = d.get("plan_date")
        rows = fetch_all("""
            SELECT *
            FROM coverage_plan_lines
            WHERE product_id=? AND plan_date=?
            ORDER BY id
        """, (product_id, plan_date))
        if len(rows) <= 1:
            continue
        keep = rows[0]
        extras = rows[1:]
        sum_customer_forecast = sum(float(r.get("customer_forecast") or 0) for r in rows)
        max_stock_at_wh = max(float(r.get("stock_at_wh") or 0) for r in rows)
        sum_shipment_delivery_qty = sum(float(r.get("shipment_delivery_qty") or 0) for r in rows)
        sum_delivered_to_customer = sum(float(r.get("delivered_to_customer") or 0) for r in rows)
        min_week_no = min(int(r.get("week_no") or 0) for r in rows if r.get("week_no") is not None)
        execute_query("""
            UPDATE coverage_plan_lines
            SET week_no=?, customer_forecast=?, stock_at_wh=?,
                shipment_delivery_qty=?, delivered_to_customer=?
            WHERE id=?
        """, (
            min_week_no, sum_customer_forecast, max_stock_at_wh,
            sum_shipment_delivery_qty, sum_delivered_to_customer, keep["id"]
        ))
        for r in extras:
            execute_query("DELETE FROM coverage_plan_lines WHERE id=?", (r["id"],))


def require_login():
    if "user" not in st.session_state or not st.session_state.get("user"):
        force_exact_login_page()
        render_slogan_footer(login=True)
        st.stop()


def render_slogan_footer(login=False):
    """Render developer slogan/footer."""
    cls = "fsi-login-slogan-footer" if login else "fsi-slogan-footer"
    st.markdown('<div class="' + cls + '">Developed by Rajesh Dhokale&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Connect : dhokaleraj@icloud.com</div>', unsafe_allow_html=True)

def footer_with_slogan():
    """Standard footer with developer slogan."""
    render_slogan_footer(login=False)

def page_setup(title=None, cleanup=False):
    inject_exact_ui_css()
    require_login()

    # Startup speed fix:
    # Do not run init_db() automatically during login or page load.
    # The cloud database already exists; repeated migrations/index checks make the app slow.
    # If migrations are ever required, run them separately from a maintenance script.
    st.session_state["_db_initialized_once"] = True

    require_page_access_for_current_page()
    top_layout()
    render_success_message()
    if "filter_key_counter" not in st.session_state:
        st.session_state.filter_key_counter = {}
    else:
        st.session_state.filter_key_counter = {}
    if cleanup:
        cleanup_orphan_transactions()
    if title:
        show_header(title)

def current_role():
    return st.session_state.user.get("role", "")

def clear_cache_after_write():
    clear_app_cache()
    for _k in list(st.session_state.keys()):
        if str(_k).startswith('_page_permissions_cache_'):
            del st.session_state[_k]


def render_big_card(title, value, header_bg="#FF8C00", value_bg="#FFFFFF", value_color="#111827"):
    """Inline-styled KPI/card. Does not depend on external CSS."""
    st.markdown(
        f"""
        <div style="border:2px solid #1A5E99;border-radius:8px;overflow:hidden;background:white;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.12);">
            <div style="background:{header_bg};color:white;min-height:78px;padding:18px 10px;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:27px;font-weight:900;line-height:1.25;letter-spacing:.5px;text-transform:uppercase;">
                {title}
            </div>
            <div style="background:{value_bg};color:{value_color};min-height:96px;padding:16px 10px;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;line-height:1.2;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_filter_card_start(title):
    """Inline-styled filter card header/body start."""
    st.markdown(
        f"""
        <div style="border:2px solid #1A5E99;border-radius:8px 8px 0 0;background:#FF8C00;color:white;min-height:78px;padding:18px 10px;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:27px;font-weight:900;line-height:1.25;letter-spacing:.5px;text-transform:uppercase;">
            {title}
        </div>
        <div style="border-left:2px solid #1A5E99;border-right:2px solid #1A5E99;border-bottom:2px solid #1A5E99;border-radius:0 0 8px 8px;background:white;min-height:96px;padding:16px;margin-bottom:18px;">
        """,
        unsafe_allow_html=True
    )

def render_filter_card_end():
    st.markdown("</div>", unsafe_allow_html=True)

def ui_spacer(height=60):
    st.markdown(f"<div style='height:{height}px;'></div>", unsafe_allow_html=True)

# === FINAL KPI CARD UI HELPERS ===
def render_dashboard_small_card(title, value, header_bg="#1A5E99", value_bg="#ffffff", value_color="#111827"):
    """Dashboard card: 20% smaller, no visible outer border, equal card size."""
    st.markdown(
        f"""
        <div style="
            width:100%;
            height:150px;
            border:0;
            border-radius:8px;
            overflow:hidden;
            background:white;
            margin-bottom:12px;
            box-shadow:0 1px 3px rgba(0,0,0,.10);
        ">
            <div style="
                background:{header_bg};
                color:#ffffff;
                height:78px;
                padding:8px 8px;
                display:flex;
                align-items:center;
                justify-content:center;
                text-align:center;
                font-family:Aptos, Arial, sans-serif;
                font-size:24px;
                line-height:1.15;
                font-weight:900;
                text-transform:uppercase;
            ">{title}</div>
            <div style="
                background:{value_bg};
                color:{value_color};
                height:72px;
                padding:8px 8px;
                display:flex;
                align-items:center;
                justify-content:center;
                text-align:center;
                font-family:Aptos, Arial, sans-serif;
                font-size:30px;
                line-height:1.1;
                font-weight:900;
            ">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_coverage_kpi_card(title, value, header_bg="#ff8c00", value_bg="#ffffff", value_color="#111827"):
    """Coverage KPI card matching attached Coverage Plan Table UI."""
    st.markdown(
        f"""
        <div style="
            width:100%;
            border:1px solid #cbd5e1;
            border-radius:4px;
            overflow:hidden;
            background:white;
            margin-bottom:16px;
        ">
            <div style="
                background:{header_bg};
                color:#ffffff;
                min-height:78px;
                padding:18px 10px;
                display:flex;
                align-items:center;
                justify-content:center;
                text-align:center;
                font-family:Aptos, Arial, sans-serif;
                font-size:24px;
                line-height:1.2;
                font-weight:900;
                letter-spacing:.2px;
                text-transform:uppercase;
            ">{title}</div>
            <div style="
                background:{value_bg};
                color:{value_color};
                min-height:108px;
                padding:22px 10px;
                display:flex;
                align-items:center;
                justify-content:center;
                text-align:center;
                font-family:Aptos, Arial, sans-serif;
                font-size:36px;
                line-height:1.2;
                font-weight:900;
            ">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_coverage_input_card_start(title, header_bg="#ff8c00"):
    """Coverage KPI card body that contains a Streamlit input inside the card."""
    st.markdown(
        f"""
        <div style="
            width:100%;
            border:1px solid #cbd5e1;
            border-bottom:0;
            border-radius:4px 4px 0 0;
            overflow:hidden;
            background:white;
            margin-bottom:0;
        ">
            <div style="
                background:{header_bg};
                color:#ffffff;
                min-height:78px;
                padding:18px 10px;
                display:flex;
                align-items:center;
                justify-content:center;
                text-align:center;
                font-family:Aptos, Arial, sans-serif;
                font-size:24px;
                line-height:1.2;
                font-weight:900;
                letter-spacing:.2px;
                text-transform:uppercase;
            ">{title}</div>
        </div>
        <div style="
            border-left:1px solid #cbd5e1;
            border-right:1px solid #cbd5e1;
            border-bottom:1px solid #cbd5e1;
            border-radius:0 0 4px 4px;
            background:#ffffff;
            min-height:108px;
            padding:22px 10px;
            display:flex;
            align-items:center;
            justify-content:center;
            margin-bottom:16px;
        ">
        """,
        unsafe_allow_html=True
    )

def render_coverage_input_card_end():
    st.markdown("</div>", unsafe_allow_html=True)

def render_coverage_filter_card_start(title):
    """Filter card header with the same Coverage Plan Table visual language."""
    st.markdown(
        f"""
        <div style="
            border:1px solid #cbd5e1;
            border-bottom:0;
            border-radius:4px 4px 0 0;
            background:#ff8c00;
            color:white;
            min-height:72px;
            padding:16px 10px;
            display:flex;
            align-items:center;
            justify-content:center;
            text-align:center;
            font-family:Aptos, Arial, sans-serif;
            font-size:24px;
            font-weight:900;
            line-height:1.2;
            text-transform:uppercase;
        ">{title}</div>
        <div style="
            border:1px solid #cbd5e1;
            border-top:0;
            border-radius:0 0 4px 4px;
            background:white;
            min-height:86px;
            padding:14px;
            margin-bottom:16px;
        ">
        """,
        unsafe_allow_html=True
    )

def render_coverage_filter_card_end():
    st.markdown("</div>", unsafe_allow_html=True)

def render_coverage_table_title(title="Coverage Plan Table"):
    st.markdown(
        f"""
        <div style="
            font-family:Aptos, Arial, sans-serif;
            font-size:32px;
            font-weight:900;
            color:#003B73;
            padding:6px 0 22px 0;
            line-height:1.2;
        ">{title}</div>
        """,
        unsafe_allow_html=True
    )
# === END FINAL KPI CARD UI HELPERS ===



def ship_to_form():
    """Ship To Master form used for Delivery Invoice print details."""
    st.subheader("Ship To Master")
    st.markdown(
        '<div class="sap-grid-note">Create Ship To addresses for delivery invoices. These fields are used in Delivery print layout.</div>',
        unsafe_allow_html=True
    )

    with st.form("ship_to_master_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            ship_to_name = st.text_input("Ship To Name", key="ship_to_name")
            ship_to_id = st.text_input("Ship To ID", key="ship_to_id")
            addressline1 = st.text_input("Addressline1", key="ship_to_addressline1")
            addressline2 = st.text_input("Addressline2", key="ship_to_addressline2")
        with c2:
            addressline3 = st.text_input("Addressline3", key="ship_to_addressline3")
            vendor_gstin = st.text_input("vendorGSTIN", key="ship_to_vendor_gstin")
            vendor_phone = st.text_input("vendorphone", key="ship_to_vendor_phone")
            vendor_email = st.text_input("vendoremail", key="ship_to_vendor_email")
            is_active = st.checkbox("Active", value=True, key="ship_to_is_active")

        submitted = st.form_submit_button("Save Ship To Master", type="primary", disabled=not current_user_can_edit('masters'))
        if submitted:
            if not ship_to_name.strip():
                st.error("Ship To Name is mandatory.")
            else:
                existing = fetch_all(
                    "SELECT id FROM ship_to_masters WHERE ship_to_name=? AND COALESCE(ship_to_id,'')=COALESCE(?, '') LIMIT 1",
                    (ship_to_name.strip(), ship_to_id.strip())
                )
                if existing:
                    execute_query("""
                        UPDATE ship_to_masters
                        SET addressline1=?, addressline2=?, addressline3=?, vendor_gstin=?,
                            vendor_phone=?, vendor_email=?, is_active=?
                        WHERE id=?
                    """, (
                        addressline1.strip(), addressline2.strip(), addressline3.strip(),
                        vendor_gstin.strip(), vendor_phone.strip(), vendor_email.strip(),
                        bool(is_active), existing[0]["id"]
                    ))
                    st.success("Ship To Master updated.")
                else:
                    execute_query("""
                        INSERT INTO ship_to_masters
                        (ship_to_name, ship_to_id, addressline1, addressline2, addressline3,
                         vendor_gstin, vendor_phone, vendor_email, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ship_to_name.strip(), ship_to_id.strip(), addressline1.strip(), addressline2.strip(),
                        addressline3.strip(), vendor_gstin.strip(), vendor_phone.strip(), vendor_email.strip(),
                        bool(is_active)
                    ))
                    st.success("Ship To Master saved.")
                clear_cache_after_write()
                st.rerun()

    rows = fetch_all("""
        SELECT id, ship_to_name, ship_to_id, addressline1, addressline2, addressline3,
               vendor_gstin, vendor_phone, vendor_email, is_active
        FROM ship_to_masters
        ORDER BY ship_to_name, ship_to_id
    """)
    if rows:
        show_filtered_df(rows, "ship_to_master_records", total=False)
    else:
        st.info("No Ship To records created yet.")


def user_can_edit_page(page_key):
    """Return True if current user can edit the given page. Super admin always can edit."""
    user = st.session_state.get("user") or {}
    username = user.get("username")
    role = user.get("role")
    if role == "super_admin":
        return True
    try:
        rows = fetch_all("SELECT can_edit FROM user_page_access WHERE username=? AND page_key=? LIMIT 1", (username, page_key))
        if rows:
            return bool(rows[0].get("can_edit"))
    except Exception:
        pass
    # default fallback
    if role == "admin":
        return page_key in ["masters", "shipment", "delivery", "payment", "coverage", "overdue"]
    if role == "user":
        return page_key in ["delivery"]
    return False


def require_page_view(page_key):
    """Allow page access based on Page Controls View rights, not only role."""
    page_def = get_page_definition_by_key(page_key)
    if page_def and not can_user_access_page(page_def):
        st.error("You do not have View permission for this module. Contact Super Admin.")
        st.stop()

def require_page_add(page_key):
    """Allow adding/saving new records based on Page Controls Add rights."""
    page_def = get_page_definition_by_key(page_key)
    if page_def and not can_user_access_page(page_def):
        st.error("You do not have View permission for this module. Contact Super Admin.")
        st.stop()
    if page_def and not can_user_add_page(page_def):
        st.error("You have View permission but not Add permission for this module. Contact Super Admin.")
        st.stop()

def require_page_edit(page_key):
    """Allow editing/modifying existing records based on Page Controls Edit rights."""
    page_def = get_page_definition_by_key(page_key)
    if page_def and not can_user_access_page(page_def):
        st.error("You do not have View permission for this module. Contact Super Admin.")
        st.stop()
    if page_def and not can_user_edit_page(page_def):
        st.error("You have View permission but not Edit permission for this module. Contact Super Admin.")
        st.stop()

def show_edit_permission_status(page_key):
    """Small helper to show current user's Add/Edit status."""
    add_status = "Add: Enabled" if current_user_can_add(page_key) else "Add: Disabled"
    edit_status = "Edit: Enabled" if current_user_can_edit(page_key) else "Edit: Disabled"
    st.caption(f"{add_status} | {edit_status}")


def searchable_selectbox(label, options, key, default_index=0, help_text=None):
    """Visible search box + selectbox for long edit lists."""
    options = list(options or [])
    if not options:
        st.warning(f"No options available for {label}.")
        return None
    search_value = st.text_input(
        f"Search {label}",
        key=f"{key}_search",
        placeholder="Type to search...",
        help=help_text,
    )
    if search_value:
        terms = [t.strip().lower() for t in str(search_value).split() if t.strip()]
        filtered = [opt for opt in options if all(term in str(opt).lower() for term in terms)]
    else:
        filtered = options
    if not filtered:
        st.warning("No matching records found. Showing all records.")
        filtered = options
    safe_index = default_index if 0 <= int(default_index or 0) < len(filtered) else 0
    return st.selectbox(label, filtered, index=safe_index, key=key)



st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&display=swap');

/* =========================================================
   EXACT UI VERSION - ALL PAGES
   ========================================================= */
:root{
    --fsi-blue:#1B6DB5;
    --fsi-blue-dark:#003B73;
    --fsi-bg:#F6F8FB;
    --fsi-card:#FFFFFF;
    --fsi-border:#CBD5E1;
    --fsi-soft:#EEF2F7;
    --fsi-text:#111827;
    --fsi-muted:#64748B;
    --fsi-green:#15803D;
    --fsi-red:#B72C24;
    --fsi-orange:#EE9337;
}

html, body, .stApp {
    background: var(--fsi-bg) !important;
}

html, body, .stApp, div, span, p, label, input, textarea, select, button {
    font-family: Aptos, Arial, sans-serif !important;
}

.block-container {
    max-width: 100% !important;
    padding-top: 0.80rem !important;
    padding-left: clamp(0.50rem, 1.3vw, 1.25rem) !important;
    padding-right: clamp(0.50rem, 1.3vw, 1.25rem) !important;
    padding-bottom: 1rem !important;
}

/* Hide sidebar for same clean app view */
section[data-testid="stSidebar"], div[data-testid="stSidebar"], div[data-testid="collapsedControl"]{
    display:none !important;
}

/* App title exact style */
.fsi-app-title,
.main-title-center,
.topbar-title-main {
    font-family: Montserrat, Aptos, Arial, sans-serif !important;
    font-size: 40px !important;
    line-height: 1.05 !important;
    font-weight: 900 !important;
    color: var(--fsi-blue) !important;
    letter-spacing: .25px !important;
    text-align:center !important;
}

/* Top header area */
.topbar,
.app-header-card,
.top-strip {
    background: var(--fsi-card) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,.08) !important;
    padding: 14px 18px !important;
    margin: 8px 0 14px 0 !important;
    color: var(--fsi-text) !important;
}

.topbar h1 {
    font-size: 28px !important;
    line-height: 1.15 !important;
    font-weight: 900 !important;
    color: var(--fsi-blue-dark) !important;
    margin: 0 !important;
}

.subtext {
    color: var(--fsi-muted) !important;
    font-size: 14px !important;
    font-weight: 800 !important;
}

/* Module menu exact card style */
.top-nav-wrap,
.modules-card {
    background: var(--fsi-card) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,.08) !important;
    padding: 12px !important;
    margin: 8px 0 18px 0 !important;
}

.top-nav-title,
.custom-module-title {
    color: var(--fsi-blue) !important;
    font-size: 20px !important;
    font-weight: 900 !important;
    letter-spacing: .02em !important;
    margin-bottom: 8px !important;
}

.top-nav-wrap [data-testid="stPageLink"] a,
.modules-card a,
div[data-testid="stButton"] > button {
    background: var(--fsi-soft) !important;
    color: var(--fsi-blue) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    min-height: 42px !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    text-decoration: none !important;
    box-shadow: none !important;
    white-space: normal !important;
}

.top-nav-wrap [data-testid="stPageLink"] a:hover,
div[data-testid="stButton"] > button:hover {
    background: var(--fsi-blue) !important;
    color: white !important;
}

/* Page heading card */
.page-title-card,
.sap-section-card,
.sap-grid-card,
.card {
    background: var(--fsi-card) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,.08) !important;
    padding: clamp(10px, 1.2vw, 16px) !important;
    margin-bottom: 14px !important;
    overflow-x: auto !important;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
.sap-grid-card-title,
.sap-subtitle,
.input-section-title,
.section-title {
    font-family: Aptos, Arial, sans-serif !important;
    font-weight: 900 !important;
    color: var(--fsi-blue-dark) !important;
}

h1 { font-size: clamp(24px, 2.0vw, 30px) !important; }
h2 { font-size: clamp(20px, 1.7vw, 26px) !important; }
h3 { font-size: clamp(17px, 1.35vw, 22px) !important; }

.sap-grid-card-title,
.sap-subtitle,
.input-section-title,
.section-title {
    font-size: clamp(16px, 1.35vw, 22px) !important;
    line-height: 1.18 !important;
    padding: 4px 0 8px 0 !important;
}

/* Labels and controls */
label,
[data-testid="stWidgetLabel"] p,
.stSelectbox label p,
.stTextInput label p,
.stNumberInput label p,
.stDateInput label p,
.stTextArea label p,
.stFileUploader label p,
.stMultiSelect label p {
    font-size: clamp(12px, 1vw, 15px) !important;
    line-height: 1.15 !important;
    font-weight: 900 !important;
    color: var(--fsi-blue-dark) !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    min-height: clamp(36px, 3.2vw, 44px) !important;
    font-size: clamp(12px, 1vw, 15px) !important;
    font-weight: 800 !important;
    color: var(--fsi-text) !important;
    background: var(--fsi-card) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

div[data-baseweb="select"] span {
    font-weight: 800 !important;
    color: var(--fsi-text) !important;
}

/* Search fields must look clear */
input[placeholder*="search" i],
input[placeholder*="Type to search" i] {
    background: #FFFFFF !important;
    border: 2px solid #D9E2EC !important;
}

/* Tables */
div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    overflow-x: auto !important;
}

/* KPI exact cards */
.kpi-head, .metric-head {
    background: var(--fsi-blue) !important;
    color: white !important;
    min-height: 48px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    font-size: 18px !important;
    line-height: 1.12 !important;
    font-weight: 900 !important;
    border-radius: 4px 4px 0 0 !important;
}

.kpi-value, .metric-value {
    min-height: 56px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    font-size: 24px !important;
    line-height: 1.12 !important;
    font-weight: 900 !important;
    background: white !important;
    color: var(--fsi-text) !important;
    border: 1px solid var(--fsi-border) !important;
    border-top:0 !important;
    border-radius: 0 0 4px 4px !important;
}

/* Prevent cramped columns */
div[data-testid="column"] {
    min-width: 0 !important;
}

/* File upload consistent */
div[data-testid="stFileUploader"] section {
    background:#FFFFFF !important;
    border:1px dashed var(--fsi-border) !important;
    border-radius:10px !important;
}

/* Footer */
.footer {
    text-align:center !important;
    color: var(--fsi-muted) !important;
    font-size: 12px !important;
    font-weight: 900 !important;
    margin-top: 26px !important;
}

/* Low resolution laptop */
@media (max-width: 1366px) {
    .block-container {
        padding-left: 0.60rem !important;
        padding-right: 0.60rem !important;
    }
    .fsi-app-title,
    .main-title-center,
    .topbar-title-main {
        font-size: 32px !important;
    }
    .top-nav-title,
    .custom-module-title {
        font-size: 17px !important;
    }
    .top-nav-wrap [data-testid="stPageLink"] a,
    div[data-testid="stButton"] > button {
        min-height: 36px !important;
        font-size: 13px !important;
        padding: 4px 8px !important;
    }
    .topbar h1 {
        font-size: 24px !important;
    }
}

/* Tablet and mobile */
@media (max-width: 760px) {
    .block-container {
        padding-left: 0.42rem !important;
        padding-right: 0.42rem !important;
    }
    .fsi-app-title,
    .main-title-center,
    .topbar-title-main {
        font-size: 24px !important;
    }
    .topbar, .top-nav-wrap, .sap-grid-card, .sap-section-card, .card {
        padding: 8px !important;
        margin-bottom: 10px !important;
    }
    h1 { font-size: 22px !important; }
    h2 { font-size: 19px !important; }
    h3 { font-size: 17px !important; }
}
</style>
""", unsafe_allow_html=True)



def inject_exact_ui_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&display=swap');

    :root{
        --fsi-blue:#1B6DB5;
        --fsi-blue-dark:#003B73;
        --fsi-bg:#F6F8FB;
        --fsi-card:#FFFFFF;
        --fsi-border:#CBD5E1;
        --fsi-soft:#EEF2F7;
        --fsi-text:#111827;
        --fsi-muted:#64748B;
        --fsi-green:#15803D;
        --fsi-red:#B72C24;
        --fsi-orange:#EE9337;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], .main {
        background: var(--fsi-bg) !important;
    }

    html, body, .stApp, div, span, p, label, input, textarea, select, button {
        font-family: Aptos, Arial, sans-serif !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
    }

    section[data-testid="stSidebar"], div[data-testid="stSidebar"], div[data-testid="collapsedControl"]{
        display:none !important;
    }

    .block-container {
        max-width: 100% !important;
        padding-top: 0.75rem !important;
        padding-left: clamp(0.50rem, 1.3vw, 1.25rem) !important;
        padding-right: clamp(0.50rem, 1.3vw, 1.25rem) !important;
        padding-bottom: 1rem !important;
    }

    .exact-app-header {
        width:100%;
        background:#FFFFFF;
        border:1px solid #CBD5E1;
        border-radius:10px;
        box-shadow:0 1px 4px rgba(15,23,42,.08);
        padding:14px 18px;
        margin:8px 0 14px 0;
        display:grid;
        grid-template-columns: 240px 1fr 260px;
        gap:12px;
        align-items:center;
        box-sizing:border-box;
    }

    .exact-app-logo {
        display:flex;
        align-items:center;
        justify-content:flex-start;
        min-width:0;
    }

    .exact-app-logo img {
        max-width:190px !important;
        width:190px !important;
        height:auto !important;
        display:block;
        object-fit:contain;
    }

    .exact-app-logo-fallback {
        width:130px;
        height:42px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:8px;
        border:1px solid #CBD5E1;
        background:#EAF3FC;
        color:#1B6DB5;
        font-weight:900;
        font-size:24px;
        font-family:Montserrat, Aptos, Arial, sans-serif !important;
    }

    .fsi-app-title,
    .main-title-center,
    .exact-title {
        font-family: Montserrat, Aptos, Arial, sans-serif !important;
        font-size: 40px !important;
        line-height: 1.05 !important;
        font-weight: 900 !important;
        color: #1B6DB5 !important;
        letter-spacing: .25px !important;
        text-align:center !important;
        margin:0 !important;
        padding:0 !important;
    }

    .exact-user-box {
        text-align:right;
        font-size:16px;
        line-height:1.35;
        font-weight:900;
        color:#111827;
        white-space:nowrap;
    }

    .exact-nav-card {
        background:#FFFFFF;
        border:1px solid #CBD5E1;
        border-radius:10px;
        box-shadow:0 1px 4px rgba(15,23,42,.08);
        padding:12px;
        margin:8px 0 18px 0;
    }

    .exact-nav-title,
    .top-nav-title,
    .custom-module-title {
        color:#1B6DB5 !important;
        font-size:20px !important;
        font-weight:900 !important;
        letter-spacing:.02em !important;
        margin:0 0 8px 0 !important;
        padding:0 !important;
        font-family:Aptos, Arial, sans-serif !important;
    }

    .exact-nav-card [data-testid="stPageLink"] a,
    .top-nav-wrap [data-testid="stPageLink"] a,
    div[data-testid="stButton"] > button {
        background:#EEF2F7 !important;
        color:#1B6DB5 !important;
        border:1px solid #CBD5E1 !important;
        border-radius:10px !important;
        min-height:42px !important;
        font-size:15px !important;
        font-weight:900 !important;
        text-decoration:none !important;
        box-shadow:none !important;
        white-space:normal !important;
        font-family:Aptos, Arial, sans-serif !important;
    }

    .exact-nav-card [data-testid="stPageLink"] a:hover,
    .top-nav-wrap [data-testid="stPageLink"] a:hover,
    div[data-testid="stButton"] > button:hover {
        background:#1B6DB5 !important;
        color:#FFFFFF !important;
    }

    .exact-page-title-card,
    .topbar {
        background:#FFFFFF !important;
        border:1px solid #CBD5E1 !important;
        border-radius:10px !important;
        box-shadow:0 1px 4px rgba(15,23,42,.08) !important;
        padding:14px 18px !important;
        margin:8px 0 14px 0 !important;
    }

    .exact-page-title-card h1,
    .topbar h1 {
        font-family:Aptos, Arial, sans-serif !important;
        font-size:30px !important;
        line-height:1.15 !important;
        font-weight:900 !important;
        color:#003B73 !important;
        margin:0 !important;
        padding:0 !important;
    }

    .exact-page-subtitle,
    .subtext {
        color:#64748B !important;
        font-size:14px !important;
        font-weight:800 !important;
        margin-top:4px !important;
    }

    .sap-grid-card,
    .sap-section-card,
    .card,
    .total-box {
        background:#FFFFFF !important;
        border:1px solid #CBD5E1 !important;
        border-radius:10px !important;
        box-shadow:0 1px 4px rgba(15,23,42,.08) !important;
        padding:clamp(10px, 1.2vw, 16px) !important;
        margin-bottom:14px !important;
        overflow-x:auto !important;
    }

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    .sap-grid-card-title,
    .sap-subtitle,
    .input-section-title,
    .section-title {
        font-family:Aptos, Arial, sans-serif !important;
        font-weight:900 !important;
        color:#003B73 !important;
    }

    h1 { font-size:clamp(24px, 2.0vw, 30px) !important; }
    h2 { font-size:clamp(20px, 1.7vw, 26px) !important; }
    h3 { font-size:clamp(17px, 1.35vw, 22px) !important; }

    .sap-grid-card-title,
    .sap-subtitle,
    .input-section-title,
    .section-title {
        font-size:clamp(16px, 1.35vw, 22px) !important;
        line-height:1.18 !important;
        padding:4px 0 8px 0 !important;
        margin:0 0 8px 0 !important;
    }

    label,
    [data-testid="stWidgetLabel"] p,
    .stSelectbox label p,
    .stTextInput label p,
    .stNumberInput label p,
    .stDateInput label p,
    .stTextArea label p,
    .stFileUploader label p,
    .stMultiSelect label p {
        font-size:clamp(12px, 1vw, 15px) !important;
        line-height:1.15 !important;
        font-weight:900 !important;
        color:#003B73 !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        min-height:clamp(36px, 3.2vw, 44px) !important;
        font-size:clamp(12px, 1vw, 15px) !important;
        font-weight:800 !important;
        color:#111827 !important;
        background:#FFFFFF !important;
        border:1px solid #CBD5E1 !important;
        border-radius:10px !important;
        box-shadow:none !important;
    }

    div[data-baseweb="select"] span {
        font-weight:800 !important;
        color:#111827 !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {
        border:1px solid #CBD5E1 !important;
        border-radius:10px !important;
        overflow-x:auto !important;
    }

    div[data-testid="column"] {
        min-width:0 !important;
    }

    .footer {
        text-align:center !important;
        color:#64748B !important;
        font-size:12px !important;
        font-weight:900 !important;
        margin-top:26px !important;
    }

    /* Exact login page */
    .exact-login-shell {
        min-height:100vh;
        background:#F6F8FB;
        display:flex;
        align-items:flex-start;
        justify-content:center;
        padding-top:28px;
        box-sizing:border-box;
    }

    .exact-login-card {
        width:min(520px, 94vw);
        background:#FFFFFF;
        border:1px solid #CBD5E1;
        border-radius:16px;
        box-shadow:0 8px 28px rgba(15,23,42,.08);
        padding:22px 32px 28px 32px;
        text-align:center;
        box-sizing:border-box;
    }

    .exact-login-logo img {
        width:190px !important;
        max-width:72% !important;
        height:auto !important;
        object-fit:contain;
        margin:0 auto 8px auto;
        display:block;
    }

    .exact-login-title {
        font-family:Montserrat, Aptos, Arial, sans-serif !important;
        font-size:30px !important;
        line-height:1.08 !important;
        font-weight:900 !important;
        color:#1B6DB5 !important;
        letter-spacing:.20px !important;
        margin:0 0 8px 0 !important;
    }

    .exact-login-card div[data-testid="stTextInput"] {
        max-width:280px !important;
        margin-left:auto !important;
        margin-right:auto !important;
    }

    .exact-login-card div[data-testid="stButton"] {
        max-width:280px !important;
        margin-left:auto !important;
        margin-right:auto !important;
    }

    .exact-login-card div[data-testid="stButton"] > button {
        width:100% !important;
        background:#1B6DB5 !important;
        color:white !important;
        border-radius:10px !important;
        min-height:46px !important;
    }

    @media (max-width:1366px) {
        .exact-app-header {
            grid-template-columns: 190px 1fr 220px;
            padding:12px 14px;
        }
        .exact-app-logo img { width:155px !important; }
        .fsi-app-title, .main-title-center, .exact-title {
            font-size:32px !important;
        }
        .exact-user-box {
            font-size:14px;
        }
        .exact-nav-title, .top-nav-title, .custom-module-title {
            font-size:17px !important;
        }
        .exact-nav-card [data-testid="stPageLink"] a,
        div[data-testid="stButton"] > button {
            min-height:36px !important;
            font-size:13px !important;
            padding:4px 8px !important;
        }
        .exact-page-title-card h1,
        .topbar h1 {
            font-size:24px !important;
        }
    }

    @media (max-width:760px) {
        .exact-app-header {
            grid-template-columns:1fr;
            text-align:center;
            gap:8px;
        }
        .exact-app-logo {
            justify-content:center;
        }
        .exact-app-logo img {
            width:130px !important;
        }
        .fsi-app-title, .main-title-center, .exact-title {
            font-size:24px !important;
        }
        .exact-user-box {
            text-align:center;
            font-size:13px;
        }
        .sap-grid-card, .sap-section-card, .card, .topbar, .exact-page-title-card, .exact-nav-card {
            padding:8px !important;
            margin-bottom:10px !important;
        }
        .exact-login-shell {
            padding-top:24px;
        }
        .exact-login-card {
            padding:20px 18px 24px 18px;
        }
        .exact-login-title {
            font-size:24px !important;
        }
    }
    

    /* ADMIN SCROLL AND SAVED-DATA VISIBILITY FIX */
    html, body, .stApp, [data-testid="stAppViewContainer"], section.main, .main {
        min-height: 100% !important;
        height: auto !important;
        overflow-y: auto !important;
        overscroll-behavior-y: auto !important;
    }
    div[data-testid="stVerticalBlock"], div[data-testid="stForm"], div[data-testid="stTabs"] {
        overflow: visible !important;
    }
    div[data-testid="stTabs"] [role="tabpanel"] {
        max-height: none !important;
        overflow: visible !important;
    }
    .block-container {
        padding-bottom: 5rem !important;
    }
    .fsi-login-slogan-footer {
        pointer-events: none !important;
    }
    .admin-saved-data-card {
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        background: #F8FAFC;
        padding: 12px 14px;
        margin: 10px 0 14px 0;
        font-family: Aptos, Arial, sans-serif;
        font-weight: 800;
        color: #0F172A;
    }
    .admin-saved-data-card b {
        color: #003B73;
    }



    /* ADMIN HEADER RESTORE / SIDEBAR CONTROL HIDE */
    div[data-testid="collapsedControl"],
    button[data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    .st-emotion-cache-1pbsqtx,
    .st-emotion-cache-1gwvy71 {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }

</style>
    """, unsafe_allow_html=True)




def force_exact_login_page():
    """Reliable top-centered login page using Streamlit columns, not open HTML wrappers."""
    inject_login_only_css()

    if LOGO_PATH.exists():
        logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" />'
    else:
        logo_html = '<div style="width:135px;height:44px;display:flex;align-items:center;justify-content:center;margin:0 auto 6px auto;border-radius:8px;border:1px solid #CBD5E1;background:#EAF3FC;color:#1B6DB5;font-family:Montserrat,Aptos,Arial,sans-serif;font-size:24px;font-weight:900;">FSI</div>'

    st.markdown(
        f"""
        <div class="login-top-card">
            {logo_html}
            <div class="login-top-title">EXPORT SHIPMENT<br>MONITORING SYSTEM</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    left, center, right = st.columns([0.9, 0.72, 0.9])
    with center:
        username = st.text_input("User Name", key="force_login_username")
        password = st.text_input("Password", type="password", key="force_login_password", placeholder="Enter password")
        if st.button("Login", type="primary", key="force_login_button"):
            user = verify_user(username, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")


def inject_login_only_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&display=swap');

    html, body, .stApp, [data-testid="stAppViewContainer"], .main {
        background: #F6F8FB !important;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="collapsedControl"],
    section[data-testid="stSidebar"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    .block-container {
        padding-top: 18px !important;
        margin-top: 0px !important;
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .login-top-card {
        width: min(520px, 94vw);
        margin: 0 auto 12px auto;
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 16px;
        box-shadow: 0 8px 28px rgba(15,23,42,.10);
        padding: 18px 26px 20px 26px;
        text-align: center;
        box-sizing: border-box;
    }

    .login-top-card img {
        width: 145px !important;
        max-width: 70% !important;
        height: auto !important;
        object-fit: contain !important;
        display: block !important;
        margin: 0 auto 6px auto !important;
    }

    .login-top-title {
        font-family: Montserrat, Aptos, Arial, sans-serif !important;
        font-size: 27px !important;
        line-height: 1.08 !important;
        font-weight: 900 !important;
        color: #1B6DB5 !important;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: .2px !important;
    }

    /* Login input column */
    div[data-testid="stTextInput"] label p {
        font-size: 14px !important;
        font-weight: 900 !important;
        color: #003B73 !important;
    }

    div[data-testid="stTextInput"] input {
        height: 42px !important;
        min-height: 42px !important;
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
        font-weight: 800 !important;
        color: #111827 !important;
    }

    div[data-testid="stButton"] > button {
        width: 100% !important;
        height: 44px !important;
        min-height: 44px !important;
        background: #1B6DB5 !important;
        color: white !important;
        border-radius: 10px !important;
        border: 0 !important;
        font-size: 16px !important;
        font-weight: 900 !important;
    }


    /* Password eye icon fix */
    div[data-testid="stTextInput"] button,
    div[data-testid="stTextInput"] [role="button"] {
        color: transparent !important;
        font-size: 0 !important;
    }

    div[data-testid="stTextInput"] button::before,
    div[data-testid="stTextInput"] [role="button"]::before {
        content: "👁" !important;
        color: #003B73 !important;
        font-size: 18px !important;
        line-height: 1 !important;
    }

    span[data-testid="stIconMaterial"] {
        font-size: 0 !important;
        color: transparent !important;
    }

    span[data-testid="stIconMaterial"]::before {
        content: "👁" !important;
        font-size: 18px !important;
        color: #003B73 !important;
    }

    @media (max-width: 760px) {
        .block-container {
            padding-top: 10px !important;
            padding-left: .5rem !important;
            padding-right: .5rem !important;
        }
        .login-top-card {
            padding: 16px 18px 18px 18px !important;
        }
        .login-top-card img {
            width: 115px !important;
        }
        .login-top-title {
            font-size: 22px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SAFE COMPATIBILITY OVERRIDES - Deep Admin Save Fix
# These definitions are intentionally placed at the end of common.py so they
# override older/missing helpers without disturbing existing app logic.
# -----------------------------------------------------------------------------

def searchable_selectbox(label, options, key=None, index=0, help=None):
    """Safe searchable selectbox fallback used across pages."""
    options = list(options or [])
    if not options:
        return None
    safe_index = index if isinstance(index, int) and 0 <= index < len(options) else 0
    return st.selectbox(label, options, index=safe_index, key=key, help=help)


def clear_cache_after_write():
    """Clear caches safely after DB writes. Never raises."""
    try:
        if "clear_permission_cache" in globals():
            clear_permission_cache()
    except Exception:
        pass
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass


def clear_app_cache():
    return clear_cache_after_write()


def require_page_view(page_key):
    """Backward-compatible page view guard. Super Admin always allowed."""
    try:
        user = st.session_state.get("user") or {}
        role = user.get("role")
        if role == "super_admin":
            return True
        username = user.get("username")
        if not username:
            st.stop()
        rows = fetch_all("SELECT can_access, can_view FROM user_page_access WHERE username=? AND page_key=?", (username, page_key))
        if rows:
            allowed = bool(rows[0].get("can_view", rows[0].get("can_access", False)))
        else:
            defaults = {
                "admin": {"dashboard", "masters", "shipment", "delivery", "payment", "coverage", "admin", "overdue"},
                "user": {"dashboard", "delivery", "coverage"},
            }
            allowed = page_key in defaults.get(role, set())
        if not allowed:
            st.error("You do not have View permission for this page. Contact Super Admin.")
            st.stop()
        return True
    except Exception:
        return True


def require_page_edit(page_key):
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return True
        rows = fetch_all("SELECT can_edit FROM user_page_access WHERE username=? AND page_key=?", (user.get("username"), page_key))
        return bool(rows and rows[0].get("can_edit"))
    except Exception:
        return False


def current_user_allowed_product_ids():
    """Product IDs allotted to current user. Empty list means all products."""
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return []
        username = user.get("username")
        if not username:
            return []
        rows = fetch_all("SELECT product_id FROM user_product_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE", (username,))
        return [int(r["product_id"]) for r in rows if r.get("product_id") is not None]
    except Exception:
        return []


def current_user_allowed_warehouse_ids():
    """Warehouse IDs allotted to current user. Empty list means all warehouses."""
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return []
        username = user.get("username")
        if not username:
            return []
        rows = fetch_all("SELECT warehouse_id FROM user_warehouse_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE", (username,))
        return [int(r["warehouse_id"]) for r in rows if r.get("warehouse_id") is not None]
    except Exception:
        return []


def filter_product_rows_for_current_user(rows, product_id_key="id"):
    ids = current_user_allowed_product_ids()
    if not ids:
        return rows
    allowed = set(ids)
    return [r for r in rows or [] if int(r.get(product_id_key) or 0) in allowed]


def filter_rows_by_user_access(rows, product_key="product_id", warehouse_key="warehouse_id"):
    try:
        product_ids = current_user_allowed_product_ids()
        warehouse_ids = current_user_allowed_warehouse_ids()
        product_set = set(product_ids)
        warehouse_set = set(warehouse_ids)
        result = []
        for r in rows or []:
            ok_product = True
            ok_warehouse = True
            if product_ids and product_key in r and r.get(product_key) is not None:
                ok_product = int(r.get(product_key) or 0) in product_set
            if warehouse_ids and warehouse_key in r and r.get(warehouse_key) is not None:
                ok_warehouse = int(r.get(warehouse_key) or 0) in warehouse_set
            if ok_product and ok_warehouse:
                result.append(r)
        return result
    except Exception:
        return rows


def access_notice():
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return
        product_ids = current_user_allowed_product_ids()
        wh_ids = current_user_allowed_warehouse_ids()
        part_msg = "All Part Numbers" if not product_ids else f"{len(product_ids)} allotted Part Number(s)"
        wh_msg = "All Warehouses" if not wh_ids else f"{len(wh_ids)} allotted Warehouse(s)"
        st.info(f"Data Access: {part_msg} | {wh_msg}")
    except Exception:
        pass


def render_slogan_footer(login=False):
    """Render centered developer slogan/footer."""
    cls = "fsi-login-slogan-footer" if login else "fsi-slogan-footer"
    st.markdown('<div class="' + cls + '"><span style="display:inline-block;text-align:center;width:100%;">Developed by Rajesh Dhokale&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;dhokaleraj@icloud.com&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;Copyrights to jrdhokale</span></div>', unsafe_allow_html=True)



# ---------------------------------------------------------------------------
# USER PRODUCT / WAREHOUSE DATA ACCESS HELPERS - CENTRAL LOGIC
# Blank access setup means full access. Assigned values restrict data everywhere.
# ---------------------------------------------------------------------------
def _safe_int_set(values):
    out = set()
    for v in values or []:
        try:
            out.add(int(v))
        except Exception:
            pass
    return out

def current_user_allowed_product_ids():
    """Product IDs allotted to current user. Empty list means all products."""
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return []
        username = user.get("username")
        if not username:
            return []
        rows = fetch_all(
            "SELECT product_id FROM user_product_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE",
            (username,),
        )
        return [int(r["product_id"]) for r in rows if r.get("product_id") is not None]
    except Exception:
        return []

def current_user_allowed_product_codes():
    """Product codes allotted to current user. Empty set means all products."""
    ids = current_user_allowed_product_ids()
    if not ids:
        return set()
    try:
        placeholders = ",".join(["?"] * len(ids))
        rows = fetch_all(f"SELECT id, product_code FROM products WHERE id IN ({placeholders})", tuple(ids))
        return {str(r.get("product_code")) for r in rows if r.get("product_code") not in (None, "")}
    except Exception:
        return set()

def current_user_allowed_warehouse_ids():
    """Warehouse IDs allotted to current user. Empty list means all warehouses."""
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return []
        username = user.get("username")
        if not username:
            return []
        rows = fetch_all(
            "SELECT warehouse_id FROM user_warehouse_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE",
            (username,),
        )
        return [int(r["warehouse_id"]) for r in rows if r.get("warehouse_id") is not None]
    except Exception:
        return []

def current_user_allowed_warehouse_names():
    """Warehouse names allotted to current user. Empty set means all warehouses."""
    ids = current_user_allowed_warehouse_ids()
    if not ids:
        return set()
    try:
        placeholders = ",".join(["?"] * len(ids))
        rows = fetch_all(f"SELECT id, warehouse_name FROM warehouses WHERE id IN ({placeholders})", tuple(ids))
        return {str(r.get("warehouse_name")) for r in rows if r.get("warehouse_name") not in (None, "")}
    except Exception:
        return set()

def get_user_access_scope():
    """Return current product/warehouse access scope for filters and KPIs."""
    return {
        "product_ids": current_user_allowed_product_ids(),
        "product_codes": current_user_allowed_product_codes(),
        "warehouse_ids": current_user_allowed_warehouse_ids(),
        "warehouse_names": current_user_allowed_warehouse_names(),
    }

def row_matches_user_access(row):
    """Check one row dict against product and warehouse access.

    If the row does not contain product/warehouse fields, it is allowed.
    If it contains product/warehouse fields, those fields must be in the allotted scope.
    """
    try:
        if not isinstance(row, dict):
            try:
                row = dict(row)
            except Exception:
                return True

        scope = get_user_access_scope()
        product_ids = _safe_int_set(scope.get("product_ids"))
        product_codes = {str(x) for x in scope.get("product_codes") or set()}
        warehouse_ids = _safe_int_set(scope.get("warehouse_ids"))
        warehouse_names = {str(x) for x in scope.get("warehouse_names") or set()}

        # Product check
        if product_ids or product_codes:
            product_keys_id = ["product_id", "Product ID", "productid", "pid"]
            product_keys_code = ["product_code", "Product Code", "Part Number", "part_number", "product", "PRODUCT"]
            has_product_field = False
            product_ok = False

            for k in product_keys_id:
                if k in row and row.get(k) not in (None, ""):
                    has_product_field = True
                    try:
                        if int(row.get(k)) in product_ids:
                            product_ok = True
                    except Exception:
                        pass

            for k in product_keys_code:
                if k in row and row.get(k) not in (None, ""):
                    has_product_field = True
                    val = str(row.get(k)).split("|")[0].strip()
                    if val in product_codes:
                        product_ok = True

            if has_product_field and not product_ok:
                return False

        # Warehouse check
        if warehouse_ids or warehouse_names:
            wh_keys_id = ["warehouse_id", "Warehouse ID", "wh_id"]
            wh_keys_name = ["warehouse_name", "Warehouse", "warehouse", "Warehouse Name"]
            has_wh_field = False
            wh_ok = False

            for k in wh_keys_id:
                if k in row and row.get(k) not in (None, ""):
                    has_wh_field = True
                    try:
                        if int(row.get(k)) in warehouse_ids:
                            wh_ok = True
                    except Exception:
                        pass

            for k in wh_keys_name:
                if k in row and row.get(k) not in (None, ""):
                    has_wh_field = True
                    if str(row.get(k)).strip() in warehouse_names:
                        wh_ok = True

            if has_wh_field and not wh_ok:
                return False

        return True
    except Exception:
        return True

def filter_rows_by_user_access(rows, product_key="product_id", warehouse_key="warehouse_id"):
    """Filter row dictionaries by allotted product and warehouse. Empty allotment means all."""
    try:
        return [r for r in (rows or []) if row_matches_user_access(r)]
    except Exception:
        return rows

def filter_product_rows_for_current_user(rows, product_id_key="id"):
    """Filter product rows by allotted part numbers. Empty allotment means all."""
    ids = current_user_allowed_product_ids()
    if not ids:
        return rows
    allowed = set(ids)
    return [r for r in rows or [] if int(r.get(product_id_key) or 0) in allowed]

def filter_warehouse_rows_for_current_user(rows, warehouse_id_key="id"):
    """Filter warehouse rows by allotted warehouses. Empty allotment means all."""
    ids = current_user_allowed_warehouse_ids()
    if not ids:
        return rows
    allowed = set(ids)
    return [r for r in rows or [] if int(r.get(warehouse_id_key) or 0) in allowed]

def access_notice():
    """Show current data scope to the logged-in user."""
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") == "super_admin":
            return
        product_ids = current_user_allowed_product_ids()
        wh_ids = current_user_allowed_warehouse_ids()
        part_msg = "All Part Numbers" if not product_ids else f"{len(product_ids)} allotted Part Number(s)"
        wh_msg = "All Warehouses" if not wh_ids else f"{len(wh_ids)} allotted Warehouse(s)"
        st.info(f"Data Access: {part_msg} | {wh_msg}")
    except Exception:
        pass

def make_in_clause(column_name, values):
    """Return SQL AND clause and params for values."""
    values = [v for v in (values or []) if v not in (None, "")]
    if not values:
        return "", ()
    placeholders = ",".join(["?"] * len(values))
    return f" AND {column_name} IN ({placeholders}) ", tuple(values)

def access_filter_clauses(product_column=None, warehouse_column=None, selected_product_ids=None, selected_warehouse_ids=None):
    """Build SQL clauses for selected filters + user scope.

    selected_* apply dashboard UI filters. User scope is already enforced by limiting selection lists,
    but this function also protects direct queries.
    """
    clauses = []
    params = []

    product_ids = selected_product_ids if selected_product_ids is not None else current_user_allowed_product_ids()
    warehouse_ids = selected_warehouse_ids if selected_warehouse_ids is not None else current_user_allowed_warehouse_ids()

    if product_column and product_ids:
        ph = ",".join(["?"] * len(product_ids))
        clauses.append(f" AND {product_column} IN ({ph}) ")
        params.extend(product_ids)
    if warehouse_column and warehouse_ids:
        ph = ",".join(["?"] * len(warehouse_ids))
        clauses.append(f" AND {warehouse_column} IN ({ph}) ")
        params.extend(warehouse_ids)

    return "".join(clauses), tuple(params)
# ---------------------------------------------------------------------------




def render_linked_data_card(title, items):
    """Render a compact card showing values already linked to the current selected field."""
    try:
        if not items:
            return
        parts = []
        if isinstance(items, dict):
            iterable = items.items()
        else:
            iterable = items
        for k, v in iterable:
            if v not in (None, ""):
                parts.append(f"<b>{html.escape(str(k))}:</b> {html.escape(str(v))}")
        if parts:
            st.markdown('<div class="admin-saved-data-card"><b>' + html.escape(str(title)) + '</b><br>' + " &nbsp; | &nbsp; ".join(parts) + '</div>', unsafe_allow_html=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Searchable selectbox compatibility override
# Accepts both index= and default_index= to support older/newer page calls.
# ---------------------------------------------------------------------------
def searchable_selectbox(label, options, key=None, index=0, default_index=None, help=None, **kwargs):
    options = list(options or [])
    if not options:
        return None
    if default_index is not None:
        index = default_index
    try:
        index = int(index)
    except Exception:
        index = 0
    if index < 0 or index >= len(options):
        index = 0
    return st.selectbox(label, options, index=index, key=key, help=help, **kwargs)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Searchable selectbox compatibility override for split pages.
# Accepts both index= and default_index=.
# ---------------------------------------------------------------------------
def searchable_selectbox(label, options, key=None, index=0, default_index=None, help=None, help_text=None, **kwargs):
    options = list(options or [])
    if not options:
        st.warning(f"No options available for {label}.")
        return None
    if default_index is not None:
        index = default_index
    try:
        index = int(index)
    except Exception:
        index = 0
    if index < 0 or index >= len(options):
        index = 0
    return st.selectbox(label, options, index=index, key=key, help=help or help_text, **kwargs)
# ---------------------------------------------------------------------------




def _render_module_subnav(title, active_key, items):
    allowed_items = []
    for key, label, target in items:
        try:
            page_def = get_page_definition_by_key(key)
            if page_def and can_user_access_page(page_def):
                allowed_items.append((key, label, target))
        except Exception:
            allowed_items.append((key, label, target))
    if not allowed_items:
        return
    st.markdown(
        f"""
        <div style="border:1px solid #d9e2ec;border-radius:14px;background:#ffffff;
                    padding:10px 12px;margin:8px 0 16px 0;box-shadow:0 2px 8px rgba(15,23,42,.06);">
            <div style="font-weight:900;color:#003B73;font-size:14px;margin-bottom:8px;">{title}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(len(allowed_items))
    for col, (key, label, target) in zip(cols, allowed_items):
        with col:
            if key == active_key:
                st.markdown(
                    f"<div style='background:#003B73;color:white;border-radius:10px;padding:9px 10px;text-align:center;font-weight:900;'>{label}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.page_link(target, label=label)

def render_shipment_subnav(active_key="shipment"):
    _render_module_subnav("Shipment", active_key, [
        ("shipment", "Shipment Entry", "pages/3_Shipment_Entry.py"),
        ("shipment_last", "Last Shipments", "pages/13_Last_Shipments.py"),
        ("shipment_edit", "Edit Shipment", "pages/14_Edit_Shipment.py"),
        ("shipment_status", "Shipment Status", "pages/16_Shipment_Status.py"),
    ])

def render_payment_subnav(active_key="payment"):
    _render_module_subnav("Payment", active_key, [
        ("payment", "Payment Entry", "pages/5_Payment_Entry.py"),
        ("payment_due", "Payment Due", "pages/18_Payment_Due.py"),
        ("payment_edit", "Edit Payment", "pages/19_Edit_Payment.py"),
    ])

# Export all helpers, including legacy underscore helpers used by pages.
__all__ = [name for name in globals() if not name.startswith('__')]




# Re-export helpers after SN26.05 appended functions.
__all__ = [name for name in globals() if not name.startswith('__')]

# ---------------------------------------------------------------------------
# SN 26.06 - 3 Decimal + Effective Price support
# ---------------------------------------------------------------------------

SN2606_DECIMAL_KEYWORDS = [
    "rate", "price", "amount", "sale", "value", "paid", "pending", "balance",
    "invoice_amount", "paid_amount", "pending_amount", "payment_received_amount",
    "unit_price", "average_price", "total_sale", "total_amount", "warehouse_stock_amount",
    "usd", "eur", "inr", "currency"
]

def format_decimal_3(value, currency=""):
    """Format app currency/rate/price/amount values to 3 decimals."""
    try:
        txt = f"{float(value or 0):,.3f}"
        return f"{txt} {currency}".strip()
    except Exception:
        return str(value or "")

def format_rate_price_amount_3decimals(df):
    """App-wide display helper: rate, price and amount fields as 3 decimals."""
    try:
        if df is None or not hasattr(df, "copy") or df.empty:
            return df
        out = df.copy()
        for col in out.columns:
            col_l = str(col).lower()
            if any(k in col_l for k in SN2606_DECIMAL_KEYWORDS):
                try:
                    out[col] = pd.to_numeric(out[col], errors="coerce").map(
                        lambda x: "" if pd.isna(x) else f"{float(x):.3f}"
                    )
                except Exception:
                    pass
        return out
    except Exception:
        return df

def _sn2606_should_format_number(label="", key=""):
    text = f"{label or ''} {key or ''}".lower()
    return any(k in text for k in SN2606_DECIMAL_KEYWORDS)

def _sn2606_patch_streamlit_decimals():
    """Patch Streamlit numeric widgets/data grids to use 3 decimals across the app."""
    try:
        if getattr(st, "_sn2606_decimal_patch_done", False):
            return

        st._sn2606_original_dataframe = st.dataframe
        st._sn2606_original_table = st.table
        st._sn2606_original_data_editor = st.data_editor
        st._sn2606_original_number_input = st.number_input

        def _patched_dataframe(data=None, *args, **kwargs):
            try:
                data = format_rate_price_amount_3decimals(data)
            except Exception:
                pass
            return st._sn2606_original_dataframe(data, *args, **kwargs)

        def _patched_table(data=None, *args, **kwargs):
            try:
                data = format_rate_price_amount_3decimals(data)
            except Exception:
                pass
            return st._sn2606_original_table(data, *args, **kwargs)

        def _patched_data_editor(data=None, *args, **kwargs):
            try:
                data = format_rate_price_amount_3decimals(data)
            except Exception:
                pass
            return st._sn2606_original_data_editor(data, *args, **kwargs)

        def _patched_number_input(label, *args, **kwargs):
            try:
                key = kwargs.get("key", "")
                if _sn2606_should_format_number(label, key):
                    kwargs.setdefault("format", "%.3f")
                    if "step" in kwargs:
                        try:
                            if float(kwargs.get("step") or 0) >= 1:
                                kwargs["step"] = 0.001
                        except Exception:
                            pass
                    else:
                        kwargs["step"] = 0.001
            except Exception:
                pass
            return st._sn2606_original_number_input(label, *args, **kwargs)

        st.dataframe = _patched_dataframe
        st.table = _patched_table
        st.data_editor = _patched_data_editor
        st.number_input = _patched_number_input
        st._sn2606_decimal_patch_done = True
    except Exception:
        pass

_sn2606_patch_streamlit_decimals()

def get_effective_product_price(product_id, effective_date=None):
    """Return product price/currency effective on a date.

    Price history table supports:
    start_date, end_date, price, currency.
    If no history row matches, returns Product Master unit_price/currency.
    """
    try:
        effective_date = effective_date or date.today()
        rows = fetch_all("""
            SELECT price, currency
            FROM product_price_history
            WHERE product_id=?
              AND start_date <= ?::date
              AND (end_date IS NULL OR end_date >= ?::date)
            ORDER BY start_date DESC, id DESC
            LIMIT 1
        """, (product_id, str(effective_date), str(effective_date)))
        if rows:
            return float(rows[0].get("price") or 0), (rows[0].get("currency") or "")
    except Exception:
        pass
    try:
        rows = fetch_all("SELECT unit_price, currency FROM products WHERE id=?", (product_id,))
        if rows:
            return float(rows[0].get("unit_price") or 0), (rows[0].get("currency") or "")
    except Exception:
        pass
    return 0.0, ""

def ensure_product_price_history_table():
    """Non-destructive table creation for product effective price history."""
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS product_price_history (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL,
                currency TEXT,
                price NUMERIC(18,6) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        execute_query("CREATE INDEX IF NOT EXISTS idx_product_price_history_product_dates ON product_price_history(product_id, start_date, end_date)")
        execute_query("ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_number TEXT")
        execute_query("ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_date DATE")
        execute_query("ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_copy_path TEXT")
    except Exception:
        pass


# SN 26.09 image export button removed from export buttons.


# SN 26.13 effective price decimal verification: shipment_common, delivery_common, shipment/delivery print layouts use 3 decimals.


# SN 26.14 final export refresh - include effective price helpers in from common import *.

# ---------------------------------------------------------------------------
# SN 26.15 - Shipment Delivered to WH / In Transit status support
# ---------------------------------------------------------------------------

def ensure_shipment_status_columns():
    """Non-destructive shipment status columns for warehouse receipt tracking."""
    try:
        execute_query("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_status TEXT DEFAULT 'In Transit'")
        execute_query("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS warehouse_delivery_date DATE")
        execute_query("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_status_updated_at TIMESTAMP")
        execute_query("CREATE INDEX IF NOT EXISTS idx_shipments_status_wh_date ON shipments(shipment_status, warehouse_delivery_date)")
    except Exception:
        pass

def render_tuesday_shipment_status_popup():
    """Every Tuesday reminder to update in-transit shipment status."""
    try:
        if date.today().weekday() != 1:
            return
        ensure_shipment_status_columns()
        rows = fetch_all("""
            SELECT s.id, s.shipment_no, s.invoice_no, s.shipment_date,
                   COALESCE(s.shipment_status,'In Transit') AS shipment_status,
                   s.warehouse_delivery_date,
                   w.warehouse_name,
                   c.customer_name
            FROM shipments s
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE COALESCE(s.shipment_status,'In Transit') <> 'Delivered'
            ORDER BY s.shipment_date DESC NULLS LAST, s.id DESC
            LIMIT 50
        """)
        if rows:
            st.warning("Tuesday Reminder: Please update shipment status for In Transit shipments.")
            with st.expander("Tuesday Shipment Status Update Pending", expanded=True):
                st.dataframe(pd.DataFrame(format_date_columns(rows)), width="stretch", hide_index=True)
    except Exception:
        pass

__all__ = [name for name in globals() if not name.startswith("__")]
