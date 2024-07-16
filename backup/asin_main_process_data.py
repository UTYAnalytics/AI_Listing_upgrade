import sys
import time
import traceback
from ultis_scrap_helium_cerebro import (
    scrap_helium_asin_keyword,
)
from main_process_data import update_keyword_auto_listing
import json


def start_driver(driver, result, asin_subsets, download_dir):
    try:
        print("Running scrap_helium_asin_keyword for subsets:", asin_subsets)
        scrap_helium_asin_keyword(driver, result, asin_subsets, download_dir)
        update_keyword_auto_listing()
        time.sleep(10)
    except Exception as e:
        print(f"An error occurred in scrap_helium_asin_keyword: {e}")
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    driver = json.loads(sys.argv[1])
    result = json.loads(sys.argv[2])
    asin_subsets = json.loads(sys.argv[3])
    download_dir = sys.argv[4]
    start_driver(driver, result, asin_subsets, download_dir)
