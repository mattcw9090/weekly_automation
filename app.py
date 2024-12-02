from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
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

app = Flask(__name__, static_folder='static')


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


def selenium_buy_credits_task(credits_list):
    """
    Handles multiple buy credit actions grouped into tabs within a single browser window.
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Load Google cookies
        driver.get("https://www.google.com")
        driver.delete_all_cookies()
        load_cookies(driver, "google_cookies.json")
        driver.refresh()
        print("[Main] Loaded Google cookies and refreshed.")

        # Load PBA cookies
        driver.get("https://pba.yepbooking.com.au")
        driver.delete_all_cookies()
        load_cookies(driver, "pba_cookies.json")
        driver.refresh()
        print("[Main] Loaded PBA cookies and refreshed.")

        # Open a new tab for each booking
        for idx, credit in enumerate(credits_list):
            if idx > 0:
                driver.execute_script("window.open('');")
                print(f"[Tab {idx + 1}] Opened a new tab.")

            # Switch to the newly opened tab
            driver.switch_to.window(driver.window_handles[idx])
            print(f"[Tab {idx + 1}] Switched to tab {idx + 1}.")

            # Initialize WebDriverWait for each tab
            wait = WebDriverWait(driver, 50)

            try:
                # Navigate to the credit list page
                driver.get("https://pba.yepbooking.com.au/user.php?tab=credit-list")
                print(f"[Tab {idx + 1}] Navigated to credit list page.")

                # Wait for the credit select dropdown
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
                print(f"[Tab {idx + 1}] Clicked on 'Credit top up' button.")

                # Select the payment type radio button
                payment_type_radio = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "input.paymentTypeCheck[type='radio'][value='PAYPAL']"))
                )
                payment_type_radio.click()
                print(f"[Tab {idx + 1}] Selected 'Paypal' payment option.")

                # Click the "Pay now" button
                pay_now_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paymentButton[title='Pay now']"))
                )
                pay_now_button.click()
                print(f"[Tab {idx + 1}] Clicked on 'Pay now' button.")

                # Load Paypal Cookies
                load_cookies(driver, "paypal_cookies.json")
                driver.refresh()
                print(f"[Tab {idx + 1}] Loaded Paypal cookies and refreshed.")

                # Click the "Complete Purchase" button
                complete_purchase_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "payment-submit-btn"))
                )
                complete_purchase_button.click()
                print(f"[Tab {idx + 1}] Clicked on 'Complete Purchase' button.")

                # Click the "Return to Seller" button
                return_to_seller_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "button.donepage-return-to-merchant-button.xo-member-2vilsm-button-button-Button-css-buttonStyles-buttonStyles"))
                )
                return_to_seller_button.click()
                print(f"[Tab {idx + 1}] Clicked on 'Return to Seller' button.")

            except Exception as e:
                print(f"[Tab {idx + 1}] An error occurred during booking: {e}")

        # Keep the browser open indefinitely for manual inspection
        print("All tabs processed successfully. Browser will remain open for manual inspection.")
        try:
            while True:
                time.sleep(5000)  # Keeps the script running indefinitely until manually stopped
        except KeyboardInterrupt:
            print("Manual interruption received. Closing browser.")

    except Exception as e:
        print(f"An error occurred during grouped booking: {e}")
    finally:
        driver.quit()
        print("Browser closed.")


def selenium_book_court_task(startingWeek, dayOfWeek, courtLocation, courtType, sessionStart, sessionEnd):
    """
    Handles court booking action
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Load Google cookies
        driver.get("https://www.google.com")
        driver.delete_all_cookies()
        load_cookies(driver, "google_cookies.json")
        driver.refresh()
        print("[Main] Loaded Google cookies and refreshed.")

        # Load PBA cookies
        driver.get("https://pba.yepbooking.com.au")
        driver.delete_all_cookies()
        load_cookies(driver, "pba_cookies.json")
        driver.refresh()
        print("[Main] Loaded PBA cookies and refreshed.")

        wait = WebDriverWait(driver, 50)

        # Select the appropriate court button based on the input
        if courtLocation == "PBA Canningvale" and courtType == "Hebat Court":
            button = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-11")))
        elif courtLocation == "PBA Canningvale" and courtType == "Super Court":
            button = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-9")))
        elif courtLocation == "PBA Malaga":
            button = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-1")))
        else:
            raise ValueError("Invalid court location or type provided.")

        button.click()
        print(f"[Main] Selected court button for {courtLocation} - {courtType}.")

        # Calculate the booking date based on startingWeek and dayOfWeek
        day_of_week_mapping = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6
        }

        starting_week_date = datetime.strptime(startingWeek, "%Y-%m-%d")
        target_date = starting_week_date + timedelta(days=day_of_week_mapping[dayOfWeek])
        booking_date = target_date.strftime("%Y-%m-%d")
        print(f"[Main] Calculated booking date: {booking_date}")

        # Handle modal if it appears
        try:
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-dialog")))
            close_button = modal.find_element(By.CSS_SELECTOR, "button.ui-dialog-titlebar-close")
            close_button.click()
            print("[Main] Closed the modal dialog box.")
        except:
            print("[Main] No modal dialog appeared or error handling modal")

        # Navigate to the correct month and year on the calendar
        try:
            # Extract target month and year from booking_date
            target_month = target_date.strftime("%B")
            target_year = target_date.strftime("%Y")

            while True:
                # Find the calendar's current month and year
                calendar_header = driver.find_element(By.CLASS_NAME, "ui-datepicker-header")
                displayed_month = calendar_header.find_element(By.CLASS_NAME, "ui-datepicker-month").text
                displayed_year = calendar_header.find_element(By.CLASS_NAME, "ui-datepicker-year").text

                if displayed_month == target_month and displayed_year == target_year:
                    print("[Main] Calendar is displaying the correct month and year.")
                    break  # Exit the loop if the calendar displays the correct month and year

                # Determine whether to navigate forward or backward
                if int(displayed_year) < int(target_year) or (displayed_year == target_year and
                                                              list(calendar.month_name).index(displayed_month) <
                                                              list(calendar.month_name).index(target_month)):
                    next_button = calendar_header.find_element(By.CLASS_NAME, "ui-datepicker-next")
                    next_button.click()
                    print("[Main] Navigated to the next month.")
                else:
                    prev_button = calendar_header.find_element(By.CLASS_NAME, "ui-datepicker-prev")
                    prev_button.click()
                    print("[Main] Navigated to the previous month.")

                # Add a short wait to allow the calendar to update
                time.sleep(0.5)

        except Exception as e:
            print(f"An error occurred while navigating the calendar: {e}")

        try:
            while True:
                time.sleep(5000)  # Keeps the script running indefinitely until manually stopped
        except KeyboardInterrupt:
            print("Manual interruption received. Closing browser.")

    except Exception as e:
        print(f"An error occurred during court booking: {e}")
    finally:
        driver.quit()
        print("Browser closed.")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/buy-credits', methods=['POST'])
def buy_credits():
    data = request.get_json()
    if not data:
        return "Invalid data received.", 400

    # Extract data from the request
    creditsToBuy = data.get('creditsToBuy')

    # For debugging purposes, print the received data
    print("Received booking request:")
    print(f"Credits to Buy: {creditsToBuy}")

    # Parse the credits to buy
    credits_lines = re.sub(r'<[^>]*>', '\n', creditsToBuy).split('\n')

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
    threading.Thread(target=selenium_buy_credits_task, args=(credits_list,)).start()

    print(f"Started buying process for {len(credits_list)} credits.")

    return f"Buying credits in progress!"


@app.route('/book-court', methods=['POST'])
def book_court():
    data = request.get_json()
    if not data:
        return "Invalid data received.", 400

    # Extract data from the request
    startingWeek = data.get('startingWeek')
    dayOfWeek = data.get('dayOfWeek')
    courtLocation = data.get('courtLocation')
    courtType = data.get('courtType')
    sessionStart = data.get('sessionStart')
    sessionEnd = data.get('sessionEnd')

    # For debugging purposes, print the received data
    print("Received book court request:")
    print(f"Starting Week: {startingWeek}")
    print(f"Day of Week: {dayOfWeek}")
    print(f"Court Location: {courtLocation}")
    print(f"Court Type: {courtType}")
    print(f"Session Start: {sessionStart}")
    print(f"Session End: {sessionEnd}")

    # Run all bookings in grouped tabs
    selenium_book_court_task(startingWeek, dayOfWeek, courtLocation, courtType, sessionStart, sessionEnd)

    return f"Booking court in progress!"


if __name__ == '__main__':
    app.run(debug=True)
