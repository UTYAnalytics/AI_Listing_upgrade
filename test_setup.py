import tempfile
import psycopg2
from psycopg2 import OperationalError
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime, timedelta
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config import config

# Logging function
def log_message(message):
    print(f"{datetime.now()}: {message}")

# Database connection test
def test_database_connection(db_config):
    try:
        conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"]
        )
        log_message("Database connection successful")
        conn.close()
    except OperationalError as e:
        log_message(f"Database connection failed: {e}")

# Selenium setup and test
def test_selenium_setup():
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        driver.get("https://app.smartscout.com/sessions/signin")
        log_message("Selenium setup successful")
        driver.quit()
    except Exception as e:
        log_message(f"Selenium setup failed: {e}")

# Main function to run tests
if __name__ == "__main__":
    # Example database configuration
    db_config = config.get_database_config()

    # Test database connection
    test_database_connection(db_config)

    # Test Selenium setup
    test_selenium_setup()
