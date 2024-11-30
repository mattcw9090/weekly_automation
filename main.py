import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# Function to load cookies from a file
def load_cookies(driver, cookie_file):
    with open(cookie_file, "r") as file:
        cookies = json.load(file)

    for cookie in cookies:
        # Adjust cookie domain if necessary
        if 'domain' in cookie and cookie['domain'].startswith('.'):
            cookie['domain'] = cookie['domain'][1:]  # Remove leading dot

        # Fix invalid sameSite values for Selenium
        if 'sameSite' in cookie:
            if cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                del cookie['sameSite']

        # Add the cookie to the browser
        driver.add_cookie(cookie)


try:
    # Step 1: Load Google cookies
    print("Loading Google cookies...")
    driver.get("https://www.google.com")  # Navigate to Google's domain to set context
    driver.delete_all_cookies()  # Clear any existing cookies
    load_cookies(driver, "google_cookies.json")
    driver.refresh()  # Refresh to apply cookies
    print("Google cookies loaded successfully!")

    # Step 2: Load PBA cookies
    print("Loading PBA cookies...")
    driver.get("https://pba.yepbooking.com.au")  # Navigate to PBA's domain to set context
    driver.delete_all_cookies()  # Clear any existing cookies
    load_cookies(driver, "pba_cookies.json")
    driver.refresh()  # Refresh to apply cookies
    print("PBA cookies loaded successfully!")

    time.sleep(5)

finally:
    # Close the browser
    driver.quit()
    print("Browser closed.")
