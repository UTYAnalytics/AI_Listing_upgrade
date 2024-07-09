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


asins = []


def scrap_helium_keyword_3asin(
    driver,
    keyword_inputs,
    username="greatwallpurchasingdept@thebargainvillage.com",
    password="qz6EvRm65L3HdjM2!!@#$",
):

    # Login process
    try:
        # Open Helium10
        driver.get("https://members.helium10.com/magnet?accountId=1544526096")
        wait = WebDriverWait(driver, 30)
        print("login")
        username_field = wait.until(
            EC.visibility_of_element_located((By.ID, "loginform-email"))
        )
        username_field.send_keys(username)
        password_field = driver.find_element(By.ID, "loginform-password")
        password_field.send_keys(password)
        # Find the button by its class name (assuming class name is unique enough here)
        status_ready = False
        status_login = False
        while not status_login:
            while not status_ready:
                try:
                    status_element = wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, "div.cm-addon-inner span")
                        )
                    )
                    status_text = status_element.text
                    if status_text == "Ready!":
                        print("Status: Ready")
                        status_ready = True
                    elif status_text == "In Process...":
                        print("Status: In Progress")
                    else:
                        print("Status: Unknown -", status_text)
                        time.sleep(1)
                except:
                    print("Error checking status")
                    time.sleep(1)
                    login_button = WebDriverWait(driver, 3000000).until(
                        EC.visibility_of_element_located(
                            (By.CLASS_NAME, "btn-secondary")
                        )
                    )
                    driver.execute_script("arguments[0].click();", login_button)
                if status_ready == True:
                    status_login = True
                else:
                    try:
                        # Wait up to 10 seconds for the element to be present and visible
                        element = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (
                                    By.XPATH,
                                    "//a[@title='Dashboard' and @href='https://members.helium10.com/?accountId=1544526096']",
                                )
                            )
                        )
                        print("Element is visible")
                        status_login = True
                    except:
                        print("Element not visible")
        time.sleep(2)
        login_button = WebDriverWait(driver, 3000000).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "btn-secondary"))
        )
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(2)
    except Exception as e:
        print(f"Error during login: {e}")
        traceback.print_exc()
        return

    # driver.refresh("https://members.helium10.com/cerebro?accountId=1544526096")
    # time.sleep(5)
    try:
        print("keywordinput")
        keyword_input = WebDriverWait(driver, 3000000).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'div[data-value="0"]')
            )
        )
        # keyword_input.clear()
        keyword_input.send_keys(keyword_inputs)
        time.sleep(1)
        keyword_input.send_keys(Keys.RETURN)

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
        # Define the XPath to locate the button element
        element_scroll = WebDriverWait(driver, 600000000).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".sc-kMdmNJ"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", element_scroll)

        print("Click View Top Products")
        time.sleep(5)
        view_product_button_xpath = (
            '//button[@data-testid="viewproductsfrequentlyboughttogether"]'
        )
        # Find the button element
        view_product_button_element = WebDriverWait(driver, 600000000).until(
            EC.visibility_of_element_located((By.XPATH, view_product_button_xpath))
        )
        # Click the button
        view_product_button_element.click()

        # Wait for the specific element to be present
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sc-jnlcPO")))

        # Find all elements with the desired class
        products = driver.find_elements(By.CLASS_NAME, "sc-kdHfKP")

        for product in products:
            try:
                # Extract the product code from the second 'sc-cSxRuM' within the 'sc-egTsrv' class
                sc_egTsrv_element = product.find_element(By.CLASS_NAME, "sc-egTsrv")
                sc_cSxRuM_elements = sc_egTsrv_element.find_elements(
                    By.CLASS_NAME, "sc-cSxRuM"
                )

                if len(sc_cSxRuM_elements) > 1:
                    product_code = sc_cSxRuM_elements[1].text
                    asins.append(product_code)

            except Exception as e:
                print(f"An error occurred: {e}")
        # Create the desired JSON structure
        output = {
            "keyword_parent": keyword_inputs,
            "asin_parent": ", ".join(asins),
            "subsets": asins,
        }

        return output
    except Exception as e:
        print(f"Error Final:{e}")
        traceback.print_exc()
