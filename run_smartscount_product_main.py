def run_smartscout_tasks(asin):
    chrome_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    try:
        smartscouts_next_login(driver, username, password)
        scrap_data_smartcount_product(driver, asin, download_dir)
    finally:
        driver.quit()