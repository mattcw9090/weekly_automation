from flask import Flask, render_template, request, jsonify
import json
import time
import re
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

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
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error adding cookie: {e}")

def selenium_booking_task_grouped(credits_list):
    """
    Handles multiple booking actions grouped into tabs within a single browser window.
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Uncomment the next line to run headless
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Load initial page to set domain for cookies
        driver.get("https://www.google.com")
        driver.delete_all_cookies()
        load_cookies(driver, "google_cookies.json")
        driver.refresh()

        # Load PBA cookies
        driver.get("https://pba.yepbooking.com.au")
        driver.delete_all_cookies()
        load_cookies(driver, "pba_cookies.json")
        driver.refresh()

        print("Cookies loaded successfully.")

        # Open a new tab for each booking
        for idx, credit in enumerate(credits_list):
            if idx > 0:
                # Open a new tab
                driver.execute_script("window.open('');")
            # Switch to the newly opened tab
            driver.switch_to.window(driver.window_handles[idx])
            print(f"Switched to tab {idx + 1}")

            # Perform booking action in this tab
            try:
                # Navigate to the credit list page
                driver.get("https://pba.yepbooking.com.au/user.php?tab=credit-list")
                wait = WebDriverWait(driver, 30)

                # Select the correct credit amount based on price
                dropdown = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "paymentCreditSelect")))
                select = Select(dropdown)
                option_found = False

                for option in select.options:
                    option_text = option.text
                    price_match = re.search(r'Price: \$([\d.]+)', option_text)
                    if price_match:
                        option_price = float(price_match.group(1))
                        if option_price == credit['amount']:
                            select.select_by_value(option.get_attribute('value'))
                            option_found = True
                            print(f"[Tab {idx + 1}] Selected option: {option_text}")
                            break

                if not option_found:
                    print(f"[Tab {idx + 1}] Could not find option for amount ${credit['amount']:.2f}")
                    continue

                # Click the "Credit top up" button
                credit_top_up_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paymentCreditLink[title='Credit top up']"))
                )
                credit_top_up_button.click()
                print(f"[Tab {idx + 1}] Clicked on 'Credit top up'.")

                # Select the payment type radio button
                payment_type_radio = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input.paymentTypeCheck[type='radio'][value='STRIPE']"))
                )
                payment_type_radio.click()
                print(f"[Tab {idx + 1}] Selected 'Stripe' payment option.")

                # Click the "Pay now" button
                pay_now_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paymentButton[title='Pay now']"))
                )
                pay_now_button.click()
                print(f"[Tab {idx + 1}] Clicked on 'Pay now' button.")

            except Exception as e:
                print(f"[Tab {idx + 1}] An error occurred during booking: {e}")

        time.sleep(500)
        print("All tabs processed successfully.")

    except Exception as e:
        print(f"An error occurred during grouped booking: {e}")
    finally:
        driver.quit()
        print("Browser closed.")

@app.route('/')
def index():
    return render_template('index.html')  # Assumes index.html is in the templates folder

@app.route('/book', methods=['POST'])
def book():
    data = request.get_json()
    if not data:
        return "Invalid data received.", 400

    # Extract data from the request
    studentName = data.get('studentName')
    dayOfWeek = data.get('dayOfWeek')
    courtLocation = data.get('courtLocation')
    courtType = data.get('courtType')
    sessionStart = data.get('sessionStart')
    sessionEnd = data.get('sessionEnd')
    creditsToBook = data.get('creditsToBook')

    # For debugging purposes, print the received data
    print("Received booking request for:")
    print(f"Student Name: {studentName}")
    print(f"Day of Week: {dayOfWeek}")
    print(f"Court Location: {courtLocation}")
    print(f"Court Type: {courtType}")
    print(f"Session Start: {sessionStart}")
    print(f"Session End: {sessionEnd}")
    print(f"Credits to Book: {creditsToBook}")

    # Parse the credits to book
    credits_lines = re.sub(r'<[^>]*>', '\n', creditsToBook).split('\n')

    credits_list = []
    for line in credits_lines:
        match = re.match(r'(\d+)x \$([\d.]+)', line.strip())
        if match:
            times = int(match.group(1))
            amount = float(match.group(2))
            for _ in range(times):
                credits_list.append({'amount': amount})
        else:
            print(f"Could not parse line: {line.strip()}")

    # Run all bookings in grouped tabs
    threading.Thread(target=selenium_booking_task_grouped, args=(credits_list,)).start()

    print(f"Started booking process for {len(credits_list)} credits.")

    return f"Booking for {studentName} is being processed in grouped tabs!"

if __name__ == '__main__':
    app.run(debug=True)
