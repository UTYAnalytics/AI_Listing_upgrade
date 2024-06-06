import re
import os
import time
import glob
import uuid
import psycopg2
import tempfile
import psycopg2
import traceback
import traceback
import numpy as np
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st
import psycopg2.extras
import plotly.graph_objs as go

from selenium import webdriver
from ai_listing import listing
from multiprocessing import Pool
from datetime import datetime
from supabase import create_client, Client
from config import config, format_header, get_newest_file, trigger_github_workflow
from ultis_sellersprite_reverse_asin import scrap_sellersprite_asin_keyword
from ultis_get_searchterm_smartsount import scrap_data_smartcount_relevant_product
from ultis_get_product_smartscount import (
    fetch_existing_relevant_asin,
    scrap_data_smartcount_product,
)
from ultis_scrap_helium_cerebro import (
    fetch_asin_tokeyword,
    captcha_solver,
    scrap_helium_asin_keyword,
)
from main_process_data import fetch_existing_relevant_asin_main, main
from plotly.subplots import make_subplots
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from st_aggrid import AgGrid, GridOptionsBuilder

pd.options.plotting.backend = "plotly"

## GLOBAL PARAMETERS
# Initialize Supabase client
supabase = config.supabase
db_config = config.get_database_config()

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1avXZgp1DIg7weP9GbDRrOH-T4SKvrfX-oJW4HE73aQE/export?format=csv&gid=0"

feature_map = {
    "STT": "id",
    "Tên": "name",
    "CUSTOMERS": "customer",
    "Asin liên quan": "asin",
    "NGÀY": "insert_date",
    "Pack": "pack",
    "Organic Keywords": "organic_keywords",
    "Auto Keywords": "keyword",
    "AI TITLE": "title",
    "AI DESCRIPTION": "description",
}
headers = [
    "id",
    "sys_run_date",
    "asin",
    "name",
    "customer",
    "insert_date",
    "keyword",
    "pack",
    "session_id",
    "organic_keywords",
    "title",
    "description",
]

# HTML and CSS for better visualization
clock_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500&display=swap');

.sidebar .block-container {
    background-color: #1e1e1e;
    padding: 0;
}

.clock {
    font-family: 'Orbitron', sans-serif;
    color: #00FF00;
    font-size: 30px;
    text-align: center;
    padding: 10px;
    background-color: #1e1e1e;
    border-radius: 10px;
    margin-top: 10px;
}

.date {
    font-family: 'Orbitron', sans-serif;
    color: #FFD700;
    font-size: 16px;
    text-align: center;
    padding: 10px;
    background-color: #1e1e1e;
    border-radius: 10px;
    margin-top: 10px;
}
</style>
"""


def set_page_info():
    st.set_page_config(
        layout="wide",
        page_title="MAIN PAGE",
        page_icon="./logo/UTY_logo_ORI.png",
    )
    new_title = (
        '<p style="font-family:sans-serif; font-size: 42px;">TỰ ĐỘNG HOÁ LISTING</p>'
    )
    st.markdown(new_title, unsafe_allow_html=True)
    st.text("")


# Function to get current date and time
def get_current_time():
    return time.strftime("%H:%M:%S"), time.strftime("%A, %B %d, %Y")


def read_doc():
    df = pd.read_csv(GOOGLE_SHEET_URL)
    return df


def upload_file(capture_key: bool = True):
    # st.title("Upload file", disabled=capture_key)
    file = st.file_uploader(
        "Upload file",
        accept_multiple_files=False,
        key="file_uploader_key",
        type=["csv"],
        help="File uploader for auto-listing",
        on_change=None,
        disabled=capture_key,
        label_visibility="hidden",
    )
    return file


def save_to_supabase(row, at_session):
    table = "auto_listing_table"
    row = row[headers].copy()
    row["sys_run_date"] = row["sys_run_date"].apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
    )
    # st.write(row)
    extract_columns = [col for col in headers if col != "id"]
    try:
        # Convert rows to list of dictionaries and handle NaN values
        rows_list = row.replace({np.nan: None}).to_dict(orient="records")
        # Insert the rows into the database using executemany
        rows_to_insert = [
            {column: row[column] for column in extract_columns} for row in rows_list
        ]
        response = supabase.table(f"{table}").insert(rows_to_insert).execute()
        # st.write(get_keyword_session(at_session))
        if hasattr(response, "error") and response.error is not None:
            raise Exception(f"Error inserting rows: {response.error}")
        st.success(f"Thêm vào database - Xong!")
    except Exception as e:
        st.error(f"Error with rows: {e}")


def execute(df):
    df_results = []
    with st.container():
        if len(df) != 0:
            if st.button("BẮT ĐẦU XỬ LÝ", key="exe_button"):
                df = df.rename(columns=feature_map)
                df["sys_run_date"] = datetime.now()
                # df["id"] = list(range(1, len(df) + 1))
                # df["id"].iloc[-1] = at_index
                # ctx = get_script_run_ctx()
                at_session = str(uuid.uuid4())
                df["session_id"] = at_session
                df = df[headers]
                st.success(f"Xử lý data - Xong !")
                save_to_supabase(df, at_session)
                user_asins = df["asin"]
                # get_asin_auto_listing_table()
                asin_to_keywords2 = [
                    asin1
                    for asin1 in user_asins
                    if asin1 not in fetch_existing_relevant_asin_main()
                ]
                # get_asin_auto_listing_table()
                if asin_to_keywords2:
                    with st.spinner("Processing..."):
                        success = False
                        while not success:
                            try:
                                # Trigger GitHub Actions workflow instead of local processing
                                trigger_github_workflow(asin_to_keywords2)
                                success = True
                                st.success(f"Completed triggering GitHub workflow for ASINs")
                            except Exception as e:
                                st.error(f"An error occurred: {e}")
                while True:
                    if not get_keyword_session(at_session).empty:
                        list_results, _ = listing(at_session)
                        df_results = pd.DataFrame(list_results)
                        break

                if not df_results.empty:
                    st.write(df_results)


def print_markdown(text):
    st.markdown(
        f'<p style="background-color:#ffffff;color:#33ff33;font-size:24px;border-radius:2%;">{text}</p>',
        unsafe_allow_html=True,
    )


def show_data(df_results):
    select = st.session_state.select_asin
    get_data = df_results.loc[df_results["asin"] == select]
    st.markdown("# Title")
    print_markdown(get_data["title"].values[0])
    st.markdown("# Description")
    print_markdown(get_data["description"].values[0])


def get_keyword_session(session_id):
    conn = None
    try:
        # Connect to your database
        conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
        )
        cur = conn.cursor()
        # Execute a query
        cur.execute(
            """
                SELECT id, sys_run_date, asin, name, customer, insert_date, keyword, pack, session_id, organic_keywords,title, description  FROM auto_listing_table a where session_id=%s
                """,
            (session_id,),
        )
        # Fetch all results
        df = pd.DataFrame(cur.fetchall(), columns=headers)
        # Convert list of tuples to list
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


@st.cache_data
def fetch_existing_asin_main():
    conn = None
    try:
        # Connect to your database
        conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
        )
        cur = conn.cursor()
        # Execute a query
        cur.execute(
            "SELECT id, sys_run_date, asin, name, customer, insert_date, keyword, pack, session_id, organic_keywords,title, description FROM auto_listing_table a"
        )
        # Fetch all results
        df_existed = pd.DataFrame(cur.fetchall(), columns=headers)
        # Convert list of tuples to list
        asins = list(df_existed["asin"].unique())
        return asins, df_existed
    except Exception as e:
        st.error(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def convert_datetime(date: str):
    date_converted = datetime.strptime(date, "%d/%m/%Y")
    return date_converted.strftime("%Y-%m-%d")


def load_google_data():
    st.markdown("## Load data từ GOOGLE SHEET")
    with st.spinner("Wait for it..."):
        df = read_doc()
        df["NGÀY"] = df["NGÀY"].apply(convert_datetime)

    if "CHECK" in df.columns:
        df = df.drop(columns=["CHECK"])
    st.success("DATA LOADED!", icon="✅")
    st.empty()
    return df


def display_database(df):
    list_date = df["sys_run_date"].unique()
    select_rows = pd.DataFrame([])
    select = st.selectbox(
        label="Chọn ngày nhập dữ liệu",
        options=list_date,
        key="select_date",
    )

    if select:
        st.session_state["selected_option"] = select
        get_date = df.loc[df["sys_run_date"] == st.session_state["selected_option"]]
        get_date = get_date[
            [
                "asin",
                "name",
                "customer",
                "pack",
                "organic_keywords",
                "keyword",
                "title",
                "description",
            ]
        ]
        select_rows = display_title_and_description(get_date)
        return select_rows
    else:
        return select_rows


def display_title_and_description(df):
    # Configure grid options using GridOptionsBuilder
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_pagination(enabled=True)
    builder.configure_selection(selection_mode="single", use_checkbox=False)
    grid_options = builder.build()

    # Display AgGrid

    return_value = AgGrid(df, gridOptions=grid_options, height=200)
    selected_rows = return_value["selected_rows"]
    return selected_rows


def call_app():
    set_page_info()
    st.sidebar.image("./logo/AMAZIN-CHOICES-logoTM.png", width=250)
    df = pd.DataFrame()
    file = upload_file(capture_key=False)
    if file:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            st.error("Kiểm tra lại định dạng file, phải là đuôi CSV")

    if len(df) != 0:
        st.dataframe(df)

    execute(df)


if __name__ == "__main__":

    call_app()
    placeholder = st.sidebar.empty()
    while True:
        # Get the current time and date
        current_time, current_date = get_current_time()
        # Render the HTML content in the sidebar
        placeholder.markdown(
            clock_style
            + f"""<div class="clock">{current_time}</div><div class="date">{current_date}</div>""",
            unsafe_allow_html=True,
        )

        # Wait for one second
        time.sleep(1)
