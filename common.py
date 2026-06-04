import io

import base64

import html

import sqlite3

import smtplib

import urllib.parse

from datetime import date, timedelta, datetime, datetime, datetime, datetime, datetime, datetime, datetime

from email.message import EmailMessage

from pathlib import Path

import matplotlib.pyplot as plt

import pandas as pd

import streamlit as st

import streamlit.components.v1 as components

from reportlab.lib import colors

from reportlab.lib.pagesizes import A4, landscape

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from db import get_connection, init_db, verify_user, hash_password

UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)

LOGO_PATH = Path("FSI_LOGO_new.png")

CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "JPY", "CNY"]

st.set_page_config(page_title="Export Shipment Management", layout="wide", initial_sidebar_state="collapsed")

init_db()

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
    font-family: Aptos, Arial, sans-serif !important;
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
    font-family:Aptos, Arial, sans-serif !important;
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
    font-family:Aptos, Arial, sans-serif !important;
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




def render_top_navigation():
    """Custom top module navigation with no menu-bar border and active page highlight."""
    import inspect
    from pathlib import Path as _Path

    user_role = st.session_state.get("user", {}).get("role", "")

    nav_items = [
        ("Dashboard", "pages/1_Dashboard.py"),
        ("Masters", "pages/2_Masters.py"),
        ("Shipment Entry", "pages/3_Shipment_Entry.py"),
        ("Delivery", "pages/4_Delivery_to_Customer.py"),
        ("Payment", "pages/5_Payment_Entry.py"),
        ("Coverage Plan", "pages/6_Coverage_Plan.py"),
        ("Reports", "pages/8_Reports.py"),
        ("Overdue", "pages/9_Overdue_Notification.py"),
    ]

    if user_role in ("admin", "super_admin"):
        nav_items.insert(6, ("Admin", "pages/7_Admin.py"))

    if user_role == "user":
        nav_items = [
            ("Dashboard", "pages/1_Dashboard.py"),
            ("Delivery", "pages/4_Delivery_to_Customer.py"),
            ("Coverage Plan", "pages/6_Coverage_Plan.py"),
            ("Reports", "pages/8_Reports.py"),
        ]

    # Detect current Streamlit page from the running page script.
    current_file = ""
    try:
        for frame in inspect.stack():
            file_name = str(frame.filename).replace("\\", "/")
            if "/pages/" in file_name:
                current_file = "pages/" + _Path(file_name).name
                break
        if not current_file:
            current_file = "pages/1_Dashboard.py"
    except Exception:
        current_file = "pages/1_Dashboard.py"

    st.markdown("""
    <style>
    .custom-module-title {
        font-family:Aptos, Arial, sans-serif;
        font-size:20px;
        font-weight:900;
        color:#1B6DB5;
        padding:10px 0 10px 0;
    }

    /* Remove menu bar border/background */
    .menu-no-border-wrap {
        background:transparent !important;
        border:0 !important;
        box-shadow:none !important;
        padding:0 !important;
        margin:8px 0 18px 0 !important;
    }

    /* Normal module buttons */
    div[data-testid="stButton"] > button {
        width:100% !important;
        min-height:48px !important;
        background:#F4F8FC !important;
        color:#1B6DB5 !important;
        border:0 !important;
        border-radius:10px !important;
        font-family:Aptos, Arial, sans-serif !important;
        font-size:20px !important;
        font-weight:900 !important;
        box-shadow:none !important;
    }

    div[data-testid="stButton"] > button:hover {
        background:#DCEEFF !important;
        color:#1B6DB5 !important;
        border:0 !important;
    }

    /* Active module button */
    div[data-testid="stButton"] > button[kind="primary"] {
        background:#1B6DB5 !important;
        color:#ffffff !important;
        border:0 !important;
        box-shadow:0 2px 8px rgba(27,109,181,.25) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background:#145A96 !important;
        color:#ffffff !important;
        border:0 !important;
    }
    </style>
    <div class="menu-no-border-wrap">
        <div class="custom-module-title">MODULES</div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(len(nav_items))
    for col, (label, target) in zip(cols, nav_items):
        is_active = (target == current_file)
        with col:
            if st.button(
                label,
                key=f"top_nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.switch_page(target)


def top_layout():
    user = st.session_state.get("user", {"username": "-", "role": "-"})
    c1, c2, c3 = st.columns([2.4, 4.8, 2.4])

    with c1:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=False, width=430)
        else:
            st.markdown('<div class="logo-circle">FSI</div>', unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div style="
            width:100%;
            text-align:center;
            font-family:Aptos, Arial, sans-serif;
            font-size:50px;
            line-height:1.05;
            font-weight:950;
            color:#1B6DB5;
            letter-spacing:.4px;
            padding-top:4px;
            margin:0 auto;
        ">
            EXPORT SHIPMENT<br>MONITORING SYSTEM
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="
            text-align:left;
            font-family:Aptos, Arial, sans-serif;
            font-size:21px;
            line-height:1.55;
            font-weight:900;
            color:#111827;
            padding-top:18px;
        ">
            <b>User: {user["username"]}</b><br>
            <b>Role: {user["role"]}</b><br>
            <b>Module: Export Shipment</b><br>
            <span id="liveClock" style="font-weight:900;"></span>
        </div>
        <script>
        function updateClock(){{
            const now = new Date();
            const els = window.parent.document.querySelectorAll('#liveClock');
            els.forEach(el => el.innerHTML = now.toLocaleString());
        }}
        setInterval(updateClock, 1000); updateClock();
        </script>
        """, unsafe_allow_html=True)

    st.divider()
    render_top_navigation()


def show_header(title, subtitle="EXPORT SHIPMENT MONITORING SYSTEM"):
    st.markdown(f'<div class="topbar"><h1>{title}</h1><div class="subtext">{subtitle}</div></div>', unsafe_allow_html=True)

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
        st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
    return df

def filter_rows(rows, key):
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
        st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
    return df

def show_fifo_df(rows, key):
    df = filter_rows(rows, key)
    if not df.empty:
        st.dataframe(style_fifo_balance(df), use_container_width=True, hide_index=True)
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

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def to_pdf_bytes(df, title):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b5cab")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    doc.build([Paragraph(title, styles["Title"]), Spacer(1,10), table])
    return output.getvalue()

def to_image_bytes(df, title):
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
    c1, c2, c3 = st.columns(3)
    c1.download_button("Export Excel", to_excel_bytes(df), f"{report_name}.xlsx")
    c2.download_button("Export PDF", to_pdf_bytes(df, report_name), f"{report_name}.pdf")
    c3.download_button("Export Image", to_image_bytes(df, report_name), f"{report_name}.png")

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

    item_rows = ""
    for idx, item in enumerate(items, start=1):
        qty = float(item.get("qty") or 0)
        unit_price = float(item.get("unit_price") or 0)
        amount = float(item.get("amount") or 0)
        item_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{item.get("original_invoice_no", original_invoice_no)}</td>
          <td>{item.get("po_number", po_number)}</td>
          <td>{format_date_ddmmyyyy(item.get("po_date", po_date))}</td>
          <td>{item.get("product_code", "")}</td>
          <td>{item.get("product_name", "")}</td>
          <td>{item.get("pallet_no", "")}</td>
          <td>{item.get("box_no", "")}</td>
          <td class="right">{qty:,.2f}</td>
          <td class="right">{unit_price:,.4f}</td>
          <td>{item.get("currency", currency)}</td>
          <td class="right">{amount:,.2f}</td>
        </tr>
        """

    logo_src = logo_data_uri()
    logo_html = f'<img src="{logo_src}" style="max-width:180px;max-height:70px;">' if logo_src else ''
    return f"""
    <html>
    <head>
    <style>
    @page {{ size: A4 portrait; margin: 12mm; }}
    body {{ font-family: Aptos, Arial, sans-serif; color:#111827; padding: 0; }}
    .invoice-title {{ font-size:28px; font-weight:900; color:#003B73; text-align:right; }}
    .company {{ font-size:22px; font-weight:900; color:#003B73; }}
    .small {{ font-size:12px; color:#374151; }}
    .box {{ border:1px solid #111827; padding:9px; margin-top:9px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .detail-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:5px 12px; }}
    .detail-cell {{ border-bottom:1px dotted #9ca3af; padding:2px 0; }}
    table {{ width:100%; border-collapse:collapse; margin-top:14px; font-size:10.5px; }}
    th {{ background:#e5e7eb; color:#111827; font-weight:900; border:1px solid #111827; padding:5px; }}
    td {{ border:1px solid #111827; padding:5px; }}
    .right {{ text-align:right; }}
    .total-row td {{ font-weight:900; background:#fef3c7; }}
    .footer {{ margin-top:35px; display:grid; grid-template-columns:1fr 1fr; gap:25px; }}
    .sign {{ border-top:1px solid #111827; padding-top:8px; text-align:center; font-weight:900; }}
    
.coverage-vertical-grid-note {
    background:#f4f8fc;
    border:1px solid #c9d7e3;
    border-radius:6px;
    padding:10px 12px;
    color:#0a3f7a;
    font-weight:800;
    margin-bottom:10px;
}
</style>
    </head>
    <body>
      <div class="grid">
        <div>
          {logo_html}
          <div class="company">FOUR STAR INDUSTRIES PVT. LTD.</div>
          <div class="small">Export Shipment Monitoring System</div>
        </div>
        <div class="invoice-title">COMMERCIAL INVOICE</div>
      </div>

      <div class="grid">
        <div class="box">
          <b>BILL TO / CUSTOMER</b><br>
          {data.get("customer_name", "")}<br>
          <span class="small">Ship To / Customer delivery location as per purchase order</span>
        </div>
        <div class="box">
          <b>INVOICE DETAILS</b><br>
          <div class="detail-grid">
            <div class="detail-cell">Delivery Invoice No: <b>{data.get("delivery_invoice_no", "")}</b></div>
            <div class="detail-cell">Delivery Date: <b>{delivery_date}</b></div>
            <div class="detail-cell">Original Invoice No: <b>{original_invoice_no}</b></div>
            <div class="detail-cell">Shipment No: <b>{data.get("shipment_no", "")}</b></div>
            <div class="detail-cell">PO Number: <b>{po_number}</b></div>
            <div class="detail-cell">PO Date: <b>{po_date}</b></div>
            <div class="detail-cell">Payment Term: <b>{data.get("payment_term", "")}</b></div>
            <div class="detail-cell">Due Date: <b>{due_date}</b></div>
          </div>
        </div>
      </div>

      <table>
        <tr>
          <th>Item</th><th>Original Invoice No</th><th>PO No</th><th>PO Date</th><th>Product Code</th><th>Description</th>
          <th>Pallet No</th><th>Box No</th><th class="right">Qty</th>
          <th class="right">Unit Price</th><th>Currency</th><th class="right">Amount</th>
        </tr>
        {item_rows}
        <tr class="total-row">
          <td colspan="8" class="right">TOTAL</td>
          <td class="right">{total_qty:,.2f}</td>
          <td></td><td>{currency}</td>
          <td class="right">{total_amount:,.2f}</td>
        </tr>
      </table>

      <div class="box">
        <b>References:</b><br>
        Original Invoice Number: <b>{original_invoice_no}</b><br>
        Shipment Number: <b>{data.get("shipment_no", "")}</b><br>
        PO Number / Date: <b>{po_number}</b> / <b>{po_date}</b>
      </div>

      <div class="footer">
        <div class="sign">Prepared By</div>
        <div class="sign">Authorized Signatory</div>
      </div>
    </body>
    </html>
    """

def build_delivery_invoice_print_data(delivery_invoice_no):
    rows = fetch_all("""
        SELECT d.*, c.customer_name, s.shipment_no, s.invoice_no AS original_invoice_no,
               p.product_code, p.product_name,
               COALESCE(d.po_number, s.po_number, p.po_number) AS po_number,
               COALESCE(d.po_date, s.po_date, p.po_date) AS po_date,
               b.pallet_no, b.box_no
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        WHERE d.delivery_invoice_no=?
        ORDER BY d.id
    """, (delivery_invoice_no,))
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
    if st.session_state.user["role"] not in allowed:
        st.error("You do not have permission to access this module.")
        st.stop()
















def login_page():
    """Top-aligned login page with logo and title centered on the same axis."""
    st.markdown("""
    <style>
    /* LOGIN PAGE - TOP ALIGNED CLEAN DESIGN */
    html, body, .stApp, [data-testid="stAppViewContainer"], .main {
        background: #ffffff !important;
    }

    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
        background: #ffffff !important;
    }

    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
    }

    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"] {
        display: none !important;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0rem !important;
    }

    .login-page-top-wrap {
        width: 100% !important;
        min-height: auto !important;
        display: flex !important;
        align-items: flex-start !important;
        justify-content: center !important;
        padding-top: 42px !important;
        box-sizing: border-box !important;
    }

    .login-card-top {
        width: min(460px, 94vw) !important;
        background: #ffffff !important;
        border-radius: 18px !important;
        padding: 0 28px 28px 28px !important;
        text-align: center !important;
        box-shadow: none !important;
        border: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: flex-start !important;
    }

    .login-logo-row {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 0 auto 18px auto !important;
        text-align: center !important;
    }

    .login-logo-img {
        width: 310px !important;
        max-width: 100% !important;
        height: auto !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    .login-title-final {
        width: 100% !important;
        font-family: Aptos, Arial, sans-serif !important;
        font-size: 17px !important;      /* increased by 20% from 14px */
        line-height: 1.35 !important;
        font-weight: 950 !important;
        color: #003B73 !important;
        text-align: center !important;
        margin: 0 auto 30px auto !important;
        letter-spacing: .55px !important;
        text-transform: uppercase !important;
    }

    .login-fields-area {
        width: 100% !important;
        max-width: 440px !important;
        margin: 0 auto !important;
        text-align: center !important;
    }

    .login-side-label {
        font-family: Aptos, Arial, sans-serif !important;
        font-size: 16px !important;
        font-weight: 850 !important;
        color: #2f3542 !important;
        text-align: right !important;
        padding-top: 11px !important;
        white-space: nowrap !important;
    }

    .login-row-gap {
        height: 20px !important;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stTextInput"] label p,
    div[data-testid="stWidgetLabel"] p {
        display: none !important;
    }

    div[data-testid="stTextInput"] {
        width: 208px !important;
        max-width: 208px !important;
        min-width: 208px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        text-align: center !important;
    }

    div[data-testid="stTextInput"] div[data-baseweb="input"],
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stTextInput"] input {
        width: 208px !important;
        max-width: 208px !important;
        min-width: 208px !important;
        min-height: 46px !important;
        border: 0 !important;
        border-radius: 12px !important;
        background: #EEF2F7 !important;
        box-shadow: inset 0 0 0 1px rgba(203, 213, 225, 0.35) !important;
        font-family: Aptos, Arial, sans-serif !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        color: #111827 !important;
        text-align: center !important;
    }

    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within > div,
    div[data-testid="stTextInput"] input:focus {
        border: 2px solid #1B6DB5 !important;
        background: #ffffff !important;
        color: #111827 !important;
        box-shadow: 0 0 0 3px rgba(27,109,181,.14) !important;
    }

    div[data-testid="stButton"] {
        width: 208px !important;
        max-width: 208px !important;
        min-width: 208px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 26px !important;
    }

    div[data-testid="stButton"] > button {
        width: 208px !important;
        max-width: 208px !important;
        min-height: 50px !important;
        border-radius: 12px !important;
        background: #FF4B4B !important;
        color: #ffffff !important;
        border: none !important;
        font-family: Aptos, Arial, sans-serif !important;
        font-size: 16px !important;
        font-weight: 900 !important;
        box-shadow: 0 6px 16px rgba(255, 75, 75, 0.22) !important;
    }

    div[data-testid="stButton"] > button:hover {
        background: #E53E3E !important;
        color: #ffffff !important;
    }

    @media (max-width: 640px) {
        .login-page-top-wrap {
            padding-top: 28px !important;
        }

        .login-card-top {
            width: 94vw !important;
            padding: 0 14px 24px 14px !important;
            border: 0 !important;
        }

        .login-title-final {
            font-size: 15px !important;
            margin-bottom: 24px !important;
        }

        .login-fields-area {
            max-width: 280px !important;
        }

        .login-side-label {
            text-align: center !important;
            padding-top: 0 !important;
            padding-bottom: 6px !important;
            font-size: 15px !important;
        }

        div[data-testid="stTextInput"],
        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stButton"],
        div[data-testid="stButton"] > button {
            width: 80vw !important;
            max-width: 280px !important;
            min-width: 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-page-top-wrap"><div class="login-card-top">', unsafe_allow_html=True)

    if LOGO_PATH.exists():
        logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        st.markdown(
            f'<div class="login-logo-row"><img class="login-logo-img" src="data:image/png;base64,{logo_b64}" /></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="login-logo-row"><div style="font-size:36px;font-weight:950;color:#003B73;text-align:center;">FSI</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        '<div class="login-title-final">EXPORT SHIPMENT<br>MONITORING SYSTEM</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-fields-area">', unsafe_allow_html=True)

    u_sp1, u_label_col, u_input_col, u_sp2 = st.columns([0.50, 0.46, 0.70, 0.50])
    with u_label_col:
        st.markdown('<div class="login-side-label">User Name</div>', unsafe_allow_html=True)
    with u_input_col:
        username = st.text_input("User Name", key="login_username", label_visibility="collapsed")

    st.markdown('<div class="login-row-gap"></div>', unsafe_allow_html=True)

    p_sp1, p_label_col, p_input_col, p_sp2 = st.columns([0.50, 0.46, 0.70, 0.50])
    with p_label_col:
        st.markdown('<div class="login-side-label">Password</div>', unsafe_allow_html=True)
    with p_input_col:
        password = st.text_input("Password", type="password", key="login_password", label_visibility="collapsed")

    b_sp1, b_mid, b_sp2 = st.columns([1, 0.70, 1])
    with b_mid:
        if st.button("Login", type="primary", key="login_button"):
            user = verify_user(username, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.markdown('</div></div></div>', unsafe_allow_html=True)



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
        unit_price = st.number_input("Price", min_value=0.0, step=1.0, key="product_unit_price")
        currency = st.selectbox("Currency", CURRENCIES, key="product_currency")
        weight = st.number_input("Weight", min_value=0.0, step=1.0, key="product_weight")
        lcr_weekly = st.number_input("LCR Weekly", min_value=0.0, step=1.0, key="product_lcr_weekly")
        mcr_weekly = st.number_input("MCR Weekly", min_value=0.0, step=1.0, key="product_mcr_weekly")
        po_date = st.date_input("PO Date", value=date.today(), key="product_po_date")
        two_months_inventory = lcr_weekly * 8
        st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {two_months_inventory:,.2f}</div>', unsafe_allow_html=True)

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
                e_unit_price = st.number_input("Edit Price", min_value=0.0, value=float(selected.get("unit_price") or 0), step=1.0, key=f"edit_product_unit_price_{sid}")
                current_currency = selected.get("currency") or "INR"
                e_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(current_currency) if current_currency in CURRENCIES else 0, key=f"edit_product_currency_{sid}")
                e_weight = st.number_input("Edit Weight", min_value=0.0, value=float(selected.get("weight") or 0), step=1.0, key=f"edit_product_weight_{sid}")
                e_lcr_weekly = st.number_input("Edit LCR Weekly", min_value=0.0, value=float(selected.get("lcr_weekly") or 0), step=1.0, key=f"edit_product_lcr_weekly_{sid}")
                e_mcr_weekly = st.number_input("Edit MCR Weekly", min_value=0.0, value=float(selected.get("mcr_weekly") or 0), step=1.0, key=f"edit_product_mcr_weekly_{sid}")
                e_po_date = st.date_input("Edit PO Date", value=parse_date_for_input(selected.get("po_date")), key=f"edit_product_po_date_{sid}")
                e_two_months_inventory = e_lcr_weekly * 8
                st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {e_two_months_inventory:,.2f}</div>', unsafe_allow_html=True)

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

def master_form(title, table, fields, allowed_roles=("admin", "super_admin")):
    require_roles(allowed_roles)
    st.subheader(title)
    values = {}
    cols = st.columns(2)
    for i, field in enumerate(fields):
        with cols[i % 2]:
            if field in ("days", "unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory", "shipment_time_days"):
                values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0 if field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 0, step=1.0 if field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 1, key=f"{table}_{field}")
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
                        edit_values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0, value=float(selected.get(field) or 0), step=1.0, key=f"edit_{table}_{field}")
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
        use_container_width=True,
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
        login_page()
        st.stop()



def page_setup(title=None, cleanup=False):
    require_login()
    top_layout()
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

