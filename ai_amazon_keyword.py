import tempfile
import psycopg2.extras
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pandas as pd
import psycopg2
from datetime import datetime
import numpy as np
from multiprocessing import Pool
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from config import config, get_newest_file
import glob

# Initialize Supabase client
supabase = config.supabase

# Get timezone offset and calculate current time in GMT+7
current_time_gmt7 = config.current_time_gmt7

# Path to your extension .crx, extension_id file
extension_path, extension_id = config.get_paths_config()

db_config = config.get_database_config()


def wait_for_download_complete(download_dir, keyword, timeout=60):
    """Wait for the file with the given keyword in the name to be fully downloaded in the directory."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            files = [
                f
                for f in glob.glob(os.path.join(download_dir, "*"))
                if keyword in f and not f.endswith(".crdownload")
            ]
            if files:
                latest_file = max(files, key=lambda f: os.path.getctime(f))
                return latest_file
        except Exception as e:
            print(f"Error occurred: {e}, retrying...")
        time.sleep(1)
    return None


def upsert_results(results):
    """Upsert results into the database"""
    conn = None
    try:
        # Connect to your database
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        for result in results:
            cur.execute(
                """
                UPDATE auto_listing_table
                SET keyword = %s
                WHERE id = %s AND session_id = %s
                """,
                (
                    result["keyword"],
                    result["id"],
                    result["session_id"],
                ),
            )
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def scrap_amazon_keyword(driver, df_keywords, keyword_list=[]):
    results = []

    for index, row in df_keywords.iterrows():
        keywords = row["organic_keywords"].split(", ")
        at_session = row["session_id"]
        for keyword in keywords:
            keyword_list.append(
                {"synonyms_keyword": keyword, "id": row["id"], "session_id": at_session}
            )

    datas_keyword = pd.DataFrame(keyword_list)

    for index, data_item in datas_keyword.iterrows():
        driver.get(f"https://www.amazon.com/s?k={data_item['synonyms_keyword']}")

        # Wait for the search input field to be visible
        search_box = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "twotabsearchtextbox"))
        )

        # Clear the search box and enter the keyword
        search_box.clear()
        search_box.send_keys(data_item["synonyms_keyword"])
        time.sleep(10)
        try:
            # Wait for the suggestions dropdown to be visible
            suggestions = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "nav-flyout-searchAjax"))
            )
            time.sleep(10)

            # Get all suggestion elements
            suggestion_elements = driver.find_elements(
                By.CLASS_NAME, "s-suggestion-container"
            )

            # Extract the text of each suggestion and combine them into a comma-separated string
            suggestion_texts = [element.text for element in suggestion_elements]
            combined_suggestions = ", ".join(suggestion_texts)

            print(
                f"Suggestions for {data_item['synonyms_keyword']}: {combined_suggestions}"
            )

            # Add result to the list
            result = {
                "id": data_item["id"],
                "session_id": data_item["session_id"],
                "keyword": combined_suggestions,
            }
            results.append(result)

        except Exception as e:
            print(f"Error while searching for {data_item['synonyms_keyword']}: {e}")

    # Upsert the results into the database
    upsert_results(results)
