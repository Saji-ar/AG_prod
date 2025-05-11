import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
    else:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            "service_account.json", scope
        )
    return gspread.authorize(credentials)

@st.cache_data(ttl=30)
def load_ws_df(spreadsheet_name, worksheet_name):
    client = get_gspread_client()
    ws = client.open(spreadsheet_name).worksheet(worksheet_name)
    return pd.DataFrame(ws.get_all_records())

@st.cache_data(ttl=30)
def load_sheet_df(sheet_name):
    client = get_gspread_client()
    ws = client.open(sheet_name).sheet1
    return pd.DataFrame(ws.get_all_records())
