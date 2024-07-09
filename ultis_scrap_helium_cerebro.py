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
from config import config
import glob

# Initialize Supabase client
supabase = config.supabase

# Get timezone offset and calculate current time in GMT+7
current_time_gmt7 = config.current_time_gmt7

# # Path to your extension .crx, extension_id file
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

def reuse_driver(driver_info):
    session_id = driver_info["session_id"]
    executor_url = driver_info["executor_url"]

    # Recreate the driver instance
    original_execute = webdriver.remote.webdriver.WebDriver.execute
    def new_command_execute(self, command, params=None):
        if command == "newSession":
            return {"sessionId": session_id, "status": 0, "value": None}
        return original_execute(self, command, params)
    webdriver.remote.webdriver.WebDriver.execute = new_command_execute
    driver = webdriver.Remote(command_executor=executor_url, desired_capabilities={})
    driver.session_id = session_id
    webdriver.remote.webdriver.WebDriver.execute = original_execute

    return driver

def scrap_helium_asin_keyword(driver_info, result, asin_subsets, download_dir):
    asin_parent, subsets = result["asin_parent"], asin_subsets
    driver = reuse_driver(driver_info)
    # Login process
    # try:
    # Open Helium10
    driver.get("https://members.helium10.com/cerebro?accountId=1544526096")
    wait = WebDriverWait(driver, 30)

    try:
        print("asininput")
        asin_input = WebDriverWait(driver, 3000000).until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    '//*[contains(@placeholder, "Enter up to ") and contains(@placeholder, " product identifiers for keyword comparison")]',
                )
            )
        )
        asin_input.clear()
        asin_input.send_keys(subsets)
        time.sleep(1)
        asin_input.send_keys(Keys.SPACE)
        
        print("Get Keyword Button")
        getkeyword_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-testid='getkeywords']")
            )
        )
        print("Get Keyword Button_click")
        getkeyword_button.click()
        time.sleep(1)

        timeout = 10
        try:
            popup_visible = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".sc-yRUbj.iYFpRQ"))
            )
            if popup_visible:
                run_new_search_button = driver.find_element(
                    By.CSS_SELECTOR, "button[data-testid='runnewsearch']"
                )
                run_new_search_button.click()
                print("Clicked on 'Run New Search'.")
        except TimeoutException:
            print("Popup not found within the timeout period.")
        # driver.get_screenshot_as_file("screenshot.png")
        element = WebDriverWait(driver, 60000).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[@data-testid='export']")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView();", element)

        print("Click Export data")
        export_data_button = driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='exportdata']"
        )
        driver.execute_script("arguments[0].click();", export_data_button)
        print("Clicked the '...as a CSV file' option.")
        data_testid = "csv"
        actions = ActionChains(driver)
        csv_option = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f'div[data-testid="{data_testid}"]')
            )
        )
        actions.move_to_element(csv_option).click().perform()

        print("newest_file")

        # Wait for the file with "US_AMAZON_cerebro" in its name to appear in the download directory
        newest_file_path = wait_for_download_complete(
            download_dir, "US_AMAZON_cerebro", timeout=60000
        )
        if newest_file_path:
            # driver.quit()
            data_df = pd.read_csv(newest_file_path)
            data_df = data_df.replace("-", None)
            data_df["sys_run_date"] = datetime.now().strftime("%Y-%m-%d")
        else:
            print("No files found in the specified directory.")

        columns_to_extract = [
            "Keyword Phrase",
            "ABA Total Click Share",
            "ABA Total Conv. Share",
            "Keyword Sales",
            "Cerebro IQ Score",
            "Search Volume",
            "Search Volume Trend",
            "H10 PPC Sugg. Bid",
            "H10 PPC Sugg. Min Bid",
            "H10 PPC Sugg. Max Bid",
            "Sponsored ASINs",
            "Competing Products",
            "CPR",
            "Title Density",
            "Organic",
            "Sponsored Product",
            "Amazon Recommended",
            "Editorial Recommendations",
            "Amazon Choice",
            "Highly Rated",
            "Sponsored Brand Header",
            "Sponsored Brand Video",
            "Top Rated From Our Brand",
            "Trending Now",
            "Sponsored Rank (avg)",
            "Sponsored Rank (count)",
            "Amazon Recommended Rank (avg)",
            "Amazon Recommended Rank (count)",
            "Position (Rank)",
            "Relative Rank",
            "Competitor Rank (avg)",
            "Ranking Competitors (count)",
            "Competitor Performance Score",
            "sys_run_date",
        ]
        # headers = [
        #     "keyword_phrase",
        #     "aba_total_click_share",
        #     "aba_total_conv_share",
        #     "keyword_sales",
        #     "cerebro_iq_score",
        #     "search_volume",
        #     "search_volume_trend",
        #     "h10_ppc_sugg_bid",
        #     "h10_ppc_sugg_min_bid",
        #     "h10_ppc_sugg_max_bid",
        #     "sponsored_asins",
        #     "competing_products",
        #     "cpr",
        #     "title_density",
        #     "organic",
        #     "sponsored_product",
        #     "amazon_recommended",
        #     "editorial_recommendations",
        #     "amazon_choice",
        #     "highly_rated",
        #     "sponsored_brand_header",
        #     "sponsored_brand_video",
        #     "top_rated_from_our_brand",
        #     "trending_now",
        #     "sponsored_rank_avg",
        #     "sponsored_rank_count",
        #     "amazon_recommended_rank_avg",
        #     "amazon_recommended_rank_count",
        #     "position_rank",
        #     "relative_rank",
        #     "competitor_rank_avg",
        #     "ranking_competitors_count",
        #     "competitor_performance_score",
        #     "sys_run_date",
        # ]
        headers = [
            "keyword_phrase",
            "aba_total_click_share",
            "aba_total_conv_share",
            "keyword_sales",
            "cerebro_iq_score",
            "search_volume",
            "search_volume_trend",
            "h10_ppc_sugg_bid",
            "h10_ppc_sugg_min_bid",
            "h10_ppc_sugg_max_bid",
            "sponsored_asins",
            "competing_products",
            "cpr",
            "title_density",
            "organic",
            "sponsored_product",
            "amazon_recommended",
            "editorial_recommendations",
            "amazon_choice",
            "highly_rated",
            "sponsored_brand_header",
            "sponsored_brand_video",
            "top_rated_from_our_brand",
            "trending_now",
            "amazon_rec_rank",
            "sponsored_rank",
            "organic_rank",
            "sys_run_date",
        ]
        print(data_df.columns)
        data = data_df
        # [columns_to_extract]
        data.columns = headers

        # Convert search_volume to numeric, forcing errors to NaN
        data["organic_rank"] = pd.to_numeric(data["organic_rank"], errors="coerce")
        # Apply the filters
        filtered_data = data

        # Insert ASIN and ASIN Parent columns
        filtered_data.insert(0, "asin", "")
        filtered_data.insert(0, "asin_parent", "")
        try:
            rows_list = filtered_data.replace({np.nan: None}).to_dict(orient="records")

            for row_dict in rows_list:
                row_dict["asin"] = str(subsets)
                row_dict["asin_parent"] = str(asin_parent)

            response = (
                supabase.table("reverse_product_lookup_helium_2")
                .upsert(rows_list)
                .execute()
            )

            if hasattr(response, "error") and response.error is not None:
                raise Exception(f"Error inserting rows: {response.error}")
            print("Rows inserted successfully")
        except Exception as e:
            print(f"Error with rows: {e}")
    except Exception as e:
        print(f"Error Final:{e}")
        traceback.print_exc()
    finally:
        driver.quit()
