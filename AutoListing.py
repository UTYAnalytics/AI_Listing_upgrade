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
from datetime import datetime, timedelta
from supabase import create_client, Client
from config import config, format_header, get_newest_file
from ultis_sellersprite_reverse_asin import scrap_sellersprite_asin_keyword
from ultis_get_searchterm_smartsount import scrap_data_smartcount_relevant_product
from ultis_get_product_smartscount import fetch_existing_relevant_asin, scrap_data_smartcount_product
from ultis_scrap_helium_cerebro import fetch_asin_tokeyword, captcha_solver, scrap_helium_asin_keyword

from plotly.subplots import make_subplots
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx

from st_aggrid import AgGrid, GridOptionsBuilder

pd.options.plotting.backend = "plotly"

## GLOBAL PARAMETERS
SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# Initialize Supabase client
supabase = config.supabase

# Get timezone offset and calculate current time in GMT+7
current_time_gmt7 = config.current_time_gmt7

# Get Selenium configuration
chrome_options_list = config.get_selenium_config()

# # Path to your extension .crx, extension_id file
extension_path, extension_id = config.get_paths_config()

db_config = config.get_database_config()

username, password = config.get_smartscount()

# Create a temporary directory for downloads
with tempfile.TemporaryDirectory() as download_dir:
    # Chrome options
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    for option in chrome_options_list:
        chrome_options.add_argument(option)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    chrome_options.add_extension(os.path.join(dir_path, extension_path))


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


def read_doc():
    df = pd.read_csv(GOOGLE_SHEET_URL)
    return df


def upload_file(capture_key: bool = True):
    # st.title("Upload file", disabled=capture_key)
    file = st.file_uploader(
        "Upload file",
        accept_multiple_files=False,
        key="file_uploader_key",
        type=["csv", "xlsx"],
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
                                success = main(asin_to_keywords2)
                                if success:
                                    # formatted_results = listing(at_session)
                                    # st.markdown(
                                    #     f"""
                                    #         <div style="width: 1500px; height: 3000px; overflow-y: scroll; background-color: #f0f0f0; border: 1px solid #ccc; padding: 10px;">
                                    #             {formatted_results}
                                    #         </div>
                                    #         """,
                                    #     unsafe_allow_html=True,
                                    # )
                                    st.success(f"Completed getting Keywords")
                                else:
                                    st.error("An error occurred during the process.")
                            except Exception as e:
                                st.error(f"An error occurred: {e}")
                while True:
                    if not get_keyword_session(at_session).empty:
                        # formatted_results = listing(at_session)
                        # st.markdown(
                        #     f"""
                        #     <div style="width: 1400px; height: 3000px; overflow-y: scroll; background-color: #f0f0f0; border: 1px solid #ccc; padding: 10px;">
                        #         {formatted_results}
                        #     </div>
                        #     """,
                        #     unsafe_allow_html=True,
                        # )
                        # break
                        list_results, _ = listing(at_session)
                        df_results = pd.DataFrame(list_results)
                        break


                if not df_results.empty:
                    st.write(df_results)


def get_keyword_session(session_id):
    conn = None
    try:
        # Connect to your database
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.sxoqzllwkjfluhskqlfl",
            password="5giE*5Y5Uexi3P2",
            host="aws-0-us-west-1.pooler.supabase.com",
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
            dbname="postgres",
            user="postgres.sxoqzllwkjfluhskqlfl",
            password="5giE*5Y5Uexi3P2",
            host="aws-0-us-west-1.pooler.supabase.com",
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
    list_date = df['sys_run_date'].unique()
    select_rows = pd.DataFrame([])
    select = st.selectbox(label="Chọn ngày nhập dữ liệu", 
                                          options = list_date,
                                          key="select_date",)
    
    if select:
        st.session_state['selected_option'] = select
        get_date = df.loc[df['sys_run_date']==st.session_state['selected_option']]
        get_date = get_date[["asin", "name", "customer","pack", "organic_keywords", "keyword", "title","description" ]]
        select_rows = display_title_and_description(get_date)
        return select_rows
    else:
        return select_rows

def display_title_and_description(df):
    # Configure grid options using GridOptionsBuilder
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_pagination(enabled=True)
    builder.configure_selection(selection_mode='single', use_checkbox=False)
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
        df = pd.read_csv(file)

    if len(df) != 0:
        st.dataframe(df)

    execute(df)


def fetch_existing_relevant_asin_main():
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
        cur.execute("SELECT distinct asin FROM reverse_product_lookup_helium_2")

        # Fetch all results
        asins = cur.fetchall()
        # Convert list of tuples to list
        asins = [item[0] for item in asins]
        return asins
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_asin_auto_listing_table():
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
            "SELECT distinct asin FROM auto_listing_table a where a.keyword is null",
        )

        # Fetch all results
        asins = cur.fetchall()
        # Convert list of tuples to list
        asins = [item[0] for item in asins]
        return asins
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def update_keyword_auto_listing():
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
            """-- Step 1: Create a CTE to concatenate keyword phrases grouped by asin_parent
                WITH keyword_phrases AS (
                    SELECT 
                        asin_parent,
                        STRING_AGG(keyword_phrase, ', ') AS concatenated_keywords
                    FROM 
                        reverse_product_lookup_helium_2
                    GROUP BY 
                        asin_parent
                )

                -- Step 2: Update the auto_listing_table with the concatenated keyword phrases using LEFT JOIN
                UPDATE 
                    auto_listing_table alt
                SET 
                    keyword = kp.concatenated_keywords
                FROM 
                    keyword_phrases kp
                WHERE 
                    alt.keyword IS NULL
                    AND kp.asin_parent = alt.asin;

                """
        )
        # Commit the transaction
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def smartscouts_next_login(driver, username=username, password=password):
    driver.get("https://app.smartscout.com/sessions/signin")
    wait = WebDriverWait(driver, 30)
    # Login process
    try:
        username_field = wait.until(
            EC.visibility_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(username)

        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)
    except Exception as e:
        # raise Exception
        print("Error during login:", e)


def clear_session_and_refresh(driver):
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")


def start_driver(asin):
    chrome_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    try:
        captcha_solver(driver, chrome_options)
        scrap_helium_asin_keyword(driver, fetch_asin_tokeyword(asin), download_dir)
        driver.quit()
        update_keyword_auto_listing()
        time.sleep(10)
    finally:
        driver.quit()


def main(asins):
    try:
        with Pool(processes=3) as pool:
            pool.map(start_driver, asins)
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    

    call_app()
