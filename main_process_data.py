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
from ultis_jungle_Scout_keyword import(keyword_to_keyword)

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
            FROM keyword_to_jungle_scount
            WHERE sys_run_date = (SELECT MAX(sys_run_date) FROM keyword_to_jungle_scount)
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
        # cur.execute(
        #     """-- Step 1: Create a CTE to concatenate keyword phrases grouped by asin_parent
        #         WITH keyword_phrases AS (
        #             SELECT 
        #                 asin_parent,
        #                 STRING_AGG(keyword_phrase, ', ') AS concatenated_keywords
        #             FROM 
        #                 reverse_product_lookup_helium_2
        #             where organic_rank between 1 and 20
        #             GROUP BY 
        #                 asin_parent
        #         )

        #         -- Step 2: Update the auto_listing_table with the concatenated keyword phrases using LEFT JOIN
        #         UPDATE 
        #             auto_listing_table alt
        #         SET 
        #             keyword = kp.concatenated_keywords
        #         FROM 
        #             keyword_phrases kp
        #         WHERE 
        #             alt.keyword IS NULL
        #             AND kp.asin_parent = alt.asin;

        #         """
        # )
        cur.execute(
            """WITH keyword_phrases AS (
        SELECT 
            keyword_parent,
            STRING_AGG(name, ', ') AS concatenated_keywords
        FROM 
            keyword_to_jungle_scount
        where sys_run_date=(select max(sys_run_date) from keyword_to_jungle_scount)
        GROUP BY 
            keyword_parent
    )
    UPDATE 
        auto_listing_table alt
    SET 
        keyword = kp.concatenated_keywords
    FROM 
        keyword_phrases kp
    WHERE 
         kp.keyword_parent = alt.name;"""
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


def start_driver(keywords):
    # chrome_service = Service(ChromeDriverManager().install())
    # driver = webdriver.Chrome(options=chrome_options)
    # try:
    print("process_data")
    keyword_to_keyword(keywords)
    update_keyword_auto_listing()
    time.sleep(10)
    # finally:
        # driver.quit()


def main(keywords):
    try:
        start_driver(keywords)
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":

    print(sys.argv[1])
    keyword_list = sys.argv[1]
    success = main(keyword_list)
    if not success:
        sys.exit(1)