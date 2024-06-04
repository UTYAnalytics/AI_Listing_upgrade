from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Path to your ChromeDriver executable
driver_path = 'path/to/chromedriver'  # Replace with the actual path to your chromedriver

# Chrome options to handle browser shutdown issues
options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--headless")  # Uncomment to run in headless mode if needed

# Initialize WebDriver
try:
    driver = webdriver.Chrome(executable_path=driver_path, options=options)
    driver.set_window_size(1920, 1080)  # Set window size if needed

    # Open a website to test the connection
    driver.get("https://www.google.com")

    # Find an element (e.g., the search box) and interact with it
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys("Selenium WebDriver")
    search_box.send_keys(Keys.RETURN)

    # Wait for the results to load and display the title
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "result-stats")))
    print(driver.title)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Ensure the browser is closed properly
    driver.quit()
