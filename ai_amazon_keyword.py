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
import traceback

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
                WHERE organic_keywords = %s AND session_id = %s
                """,
                (
                    result["keyword"],
                    result["organic_keywords"],
                    result["session_id"],
                ),
            )
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def scrap_amazon_keyword(driver, df_keywords):
    for index, row in df_keywords.iterrows():
        results = []
        all_suggestions = set()  # Use a set to collect suggestions and avoid duplicates
        keywords = row["organic_keywords"].split(", ")
        at_session = row["session_id"]
        keyword_list = [
            {"synonyms_keyword": keyword, "session_id": at_session}
            for keyword in keywords
        ]

        datas_keyword = pd.DataFrame(keyword_list)

        for index, data_item in datas_keyword.iterrows():
            driver.get(f"https://www.amazon.com")
            print(
                f"Navigated to https://www.amazon.com/s?k={data_item['synonyms_keyword']}"
            )
            try:
                # Wait for the search input field to be visible
                search_box = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.NAME, "field-keywords"))
                )

                # Clear the search box and enter the keyword
                search_box.clear()
                search_box.send_keys(data_item["synonyms_keyword"])
                time.sleep(10)
                # Define the CSS selector for the element
                # Print the page source for debugging
                print(driver.page_source)
                css_selector = "#nav-flyout-searchAjax .two-pane-results-container"
                suggestions = WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
                )

                # Get all suggestion elements
                suggestion_elements = suggestions.find_elements(
                    By.CLASS_NAME, "s-suggestion-container"
                )

                # Extract the text of each suggestion and collect them
                suggestion_texts = [element.text for element in suggestion_elements]
                all_suggestions.update(
                    suggestion_texts
                )  # Add suggestions to the set to avoid duplicates

                print(
                    f"Suggestions for {data_item['synonyms_keyword']}: {', '.join(suggestion_texts)}"
                )

            except Exception as e:
                print(f"Error while searching for {data_item['synonyms_keyword']}: {e}")
                traceback.print_exc()

        # Combine all collected suggestions into a single comma-separated string without duplicates
        combined_suggestions = ", ".join(
            sorted(all_suggestions)
        )  # Sort to maintain consistent order

        # Add result to the list
        result = {
            "session_id": row["session_id"],
            "organic_keywords": row["organic_keywords"],
            "keyword": combined_suggestions,
        }
        results.append(result)

        print("Upserting data keywords")
        # Upsert the results into the database
        upsert_results(results)
