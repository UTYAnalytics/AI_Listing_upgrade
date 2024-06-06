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
import numpy as np
import pandas as pd
import streamlit as st
import psycopg2.extras
import plotly.graph_objs as go
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import streamlit.components.v1 as components

SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
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
def set_page_info():
    st.set_page_config(
        layout="wide",
        page_title="DỮ LIỆU TRÊN DATABASE",
        page_icon="/logo/UTY_logo_ORI.png",
    )
    new_title = (
        '<p style="font-family:sans-serif; font-size: 42px;">DỮ LIỆU TRÊN DATABASE</p>'
    )
    st.markdown(new_title, unsafe_allow_html=True)
    st.text("")



@st.cache_data(ttl=60)
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

def display_database(df):
    list_date = df['sys_run_date'].unique()
    select_rows = pd.DataFrame([])
    select = st.selectbox(label="Chọn ngày nhập dữ liệu", 
                                          options = list_date,
                                          key="select_date",)
    
    if select:
        st.session_state['selected_option'] = select
        get_date = df.loc[df['sys_run_date']==st.session_state['selected_option']]
        save_as(get_date)
        get_date = get_date[["asin", "name", "customer","pack", "organic_keywords", "keyword", "title","description" ]]
        select_rows = display_title_and_description(get_date)
        return select_rows


def save_as(df):
    csv_data = df.to_csv(index=False)

    js = (
        """
    <button type="button" id="picker">Download</button>

    <script>

    async function run() {
        console.log("Running")
    const handle = await showSaveFilePicker({
        suggestedName: 'data.csv',
        types: [{
            description: 'CSV Data',
            accept: {'text/plain': ['.csv']},
        }],
    });
    """
        + f"const blob = new Blob([`{csv_data}`]);"
        + """

    const writableStream = await handle.createWritable();
    await writableStream.write(blob);
    await writableStream.close();
    }

    document.getElementById("picker").onclick = run
    console.log("Done")
    </script>

    """
    )

    components.html(js, height=30)

def display_title_and_description(df):
    # Configure grid options using GridOptionsBuilder
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_pagination(enabled=True)
    builder.configure_selection(selection_mode='single', use_checkbox=False)
    grid_options = builder.build()

    # Display AgGrid
    
    return_value = AgGrid(df, gridOptions=grid_options, height=300)
    selected_rows = return_value["selected_rows"]
    return selected_rows


def run():
    set_page_info()
    st.sidebar.image("./logo/AMAZIN-CHOICES-logoTM.png", width=250)
    selected_rows = None
    list_asin, df_existed = fetch_existing_asin_main()

    col1, col2 = st.columns([2, 2])

    with col1:
        selected_rows = display_database(df_existed)
        

    with col2:
        if selected_rows is not None:
            st.markdown("### ASIN: ")
            st.markdown(selected_rows['asin'].values[0])
            st.markdown("### Title: ")
            st.markdown(selected_rows['title'].values[0])
            st.markdown("### Description: ")
            st.markdown(selected_rows['description'].values[0])
if __name__ == "__main__":
    run()

