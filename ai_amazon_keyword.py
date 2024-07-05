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
import traceback
from multiprocessing import Pool
from selenium.common.exceptions import TimeoutException
import traceback
from selenium.webdriver.common.action_chains import ActionChains
from config import config, get_newest_file
import glob

# Initialize Supabase client
supabase = config.supabase

# Get timezone offset and calculate current time in GMT+7
current_time_gmt7 = config.current_time_gmt7

# # Path to your extension .crx, extension_id file
extension_path, extension_id = config.get_paths_config()

db_config = config.get_database_config()


def captcha_solver(driver, chrome_options, API="7f97e318653cc85d2d7bc5efdfb1ea9f"):
    # Create a temporary Chrome user data directory
    user_data_dir = os.path.join(os.getcwd(), "temp_user_data_dir")
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_extension(extension_path)
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    # Navigate to the extension's URL
    extension_url = f"chrome-extension://{extension_id}/popup.html"  # Replace 'popup.html' with your extension's specific page if different
    driver.get(extension_url)

    # Interact with the extension's elements
    try:
        # Example: Input text into a text field
        wait = WebDriverWait(driver, 10)
        input_field = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input#client-key-input")
            )
        )

        # Enter text into the input field
        input_text = API
        input_field.clear()
        input_field.send_keys(input_text)

        # Wait for the save button to be clickable, then click it
        save_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#client-key-save-btn"))
        )
        save_button.click()
        time.sleep(1)
        # Interact with the radio buttons
        token_radio_button = wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, "ant-radio-button-wrapper"))
        )
        token_radio_button.click()
    except Exception as e:
        # raise Exception
        print("Error during captcha:", e)


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


def scrap_amazon_keyword(driver, at_session, df_keywords, keyword_list=[]):
    for index, row in df_keywords.iterrows():
        keywords = row["Organic Keywords"].split(", ")
        for keyword in keywords:
            keyword_list.append({"synonyms_keyword": keyword})
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
        try:
            # Wait for the suggestions dropdown to be visible
            suggestions = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "nav-flyout-searchAjax"))
            )
            time.sleep(2)

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

        except Exception as e:
            print(f"Error while searching for {data_item['synonyms_keyword']}: {e}")
