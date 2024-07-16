import sys
import tempfile
import psycopg2.extras
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import psycopg2
import traceback

from config import config
from ultis_scrap_helium_cerebro import (
    scrap_helium_asin_keyword,
)
from ultis_helium_magnet import (
    captcha_solver,
    scrap_helium_keyword_3asin,
)
import json

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


def fetch_existing_relevant_asin_main(var):
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
        # Determine the column to fetch based on the input variable
        if var == "asin":
            column_to_fetch = "asin_parent"
        elif var == "keyword":
            column_to_fetch = "keyword_parent"
        else:
            print(f"Invalid input: {var}. Expected 'asin' or 'keyword'.")
            return []

        # Execute a query
        query = f"""
            SELECT DISTINCT {column_to_fetch}
            FROM reverse_product_lookup_helium_2
            WHERE sys_run_date = (SELECT MAX(sys_run_date) FROM reverse_product_lookup_helium_2)
        """
        cur.execute(query)

        # Fetch all results
        results = cur.fetchall()
        # Convert list of tuples to list
        results_list = [item[0] for item in results]
        return results_list

    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def fetch_existing_relevant_keyword_main(at_session):
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
            """SELECT distinct organic_keywords FROM auto_listing_table where keyword is not null and session_id=%s
                """,
            (at_session,),
        )

        # Fetch all results
        keywords = cur.fetchall()
        # Convert list of tuples to list
        keywords = [item[0] for item in keywords]
        return keywords
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
                    where organic_rank between 1 and 20
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


def clear_session_and_refresh(driver):
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")


def start_driver(keyword):
    # chrome_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(options=chrome_options)
    try:
        print("captcha_solver")
        captcha_solver(driver, chrome_options)
        print("process_data")
        result = scrap_helium_keyword_3asin(driver, keyword)
        asin_subsets = result["subsets"]
        time.sleep(10)
        return driver, result, asin_subsets, download_dir
    except Exception as e:
        print(f"An error occurred in scrap_helium_keyword_3asin: {e}")
        traceback.print_exc()
        raise


def main(keywords):
    try:
        driver, result, asin_subsets, download_dir = start_driver(keywords)
        driver_info = {
            "session_id": driver.session_id,
            "executor_url": driver.command_executor._url,
        }
        return True, driver_info, result, asin_subsets, download_dir
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":

    # print(sys.argv[1])
    # keyword_input = sys.argv[1]
    success, driver, result, asin_subsets, download_dir = main("healthy bundle")
    if success:
        output = {
            "driver": driver,
            "result": result,
            "asin_subsets": asin_subsets,
            "download_dir": download_dir,
        }
        print(json.dumps(output))  # Output the subsets as JSON
    # else:
    #     sys.exit(1)
