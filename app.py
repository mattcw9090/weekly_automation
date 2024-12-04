from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import time
import re
import threading
import os
import urllib
import webbrowser
import pywhatkit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

app = Flask(__name__, static_folder='static')

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


# Get Google Calendar service
def get_calendar_service():
    creds = None
    # Check if token.pickle exists
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If credentials are invalid or not available, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)


# Add event to Google Calendar
def add_event_to_calendar(startingWeek, dayOfWeek, courtLocation, sessionStart, sessionEnd):
    service = get_calendar_service()

    # Calculate the booking date
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
    booking_date = starting_week_date + timedelta(days=day_of_week_mapping[dayOfWeek])

    # Calculate start and end datetime
    session_start_time = datetime.strptime(sessionStart, '%H:%M').time()
    session_end_time = datetime.strptime(sessionEnd, '%H:%M').time()

    event_start_datetime = datetime.combine(booking_date, session_start_time)
    event_end_datetime = datetime.combine(booking_date, session_end_time)

    # Define the event details
    event = {
        'summary': f'Coaching Session at {courtLocation}',
        'location': courtLocation,
        'description': '',
        'start': {
            'dateTime': event_start_datetime.isoformat(),
            'timeZone': 'Australia/Perth',  # Adjust for your time zone
        },
        'end': {
            'dateTime': event_end_datetime.isoformat(),
            'timeZone': 'Australia/Perth',
        },
        'reminders': {
            'useDefault': True,
        },
    }

    try:
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event_result.get('htmlLink')}")
        return f"Event created: {event_result.get('htmlLink')}"
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"An error occurred: {e}"


# Flask route to add an event to the calendar
@app.route('/add-to-calendar', methods=['POST'])
def add_to_calendar():
    data = request.get_json()
    if not data:
        return "Invalid data received.", 400

    # Extract data from the request
    startingWeek = data.get('startingWeek')
    dayOfWeek = data.get('dayOfWeek')
    courtLocation = data.get('courtLocation')
    sessionStart = data.get('sessionStart')
    sessionEnd = data.get('sessionEnd')

    # Validate data
    if not all([startingWeek, dayOfWeek, courtLocation, sessionStart, sessionEnd]):
        return "Missing required fields.", 400

    # Run the API function in a separate thread
    thread = threading.Thread(target=add_event_to_calendar, args=(
        startingWeek, dayOfWeek, courtLocation, sessionStart, sessionEnd))
    thread.start()

    return f"Adding event to calendar in progress!"


def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Ensure ChromeDriver compatibility with the installed browser version
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )


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


def load_and_refresh_cookies(driver, url, cookie_file):
    driver.get(url)
    driver.delete_all_cookies()
    load_cookies(driver, cookie_file)
    driver.refresh()
    print(f"[Main] Loaded cookies from {cookie_file} and refreshed {url}.")


def selenium_buy_credits_task(credits_list):
    """
    Handles multiple buy credit actions grouped into tabs within a single browser window.
    """
    driver = get_chrome_driver()

    try:
        load_and_refresh_cookies(driver, "https://www.google.com", "google_cookies.json")
        load_and_refresh_cookies(driver, "https://pba.yepbooking.com.au", "pba_cookies.json")

        # Open a new tab for each booking
        for idx, credit in enumerate(credits_list):
            if idx > 0:
                driver.execute_script("window.open('');")
                print(f"[Tab {idx + 1}] Opened a new tab.")

            # Switch to the newly opened tab
            driver.switch_to.window(driver.window_handles[idx])
            print(f"[Tab {idx + 1}] Switched to tab {idx + 1}.")

            # Initialize WebDriverWait for each tab
            wait = WebDriverWait(driver, 60)

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
    driver = get_chrome_driver()

    try:
        load_and_refresh_cookies(driver, "https://www.google.com", "google_cookies.json")
        load_and_refresh_cookies(driver, "https://pba.yepbooking.com.au", "pba_cookies.json")

        wait = WebDriverWait(driver, 60)

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
        booking_date = starting_week_date + timedelta(days=day_of_week_mapping[dayOfWeek])
        print(f"[Main] Calculated booking date: {booking_date.strftime('%Y-%m-%d')}")

        # Handle modal if it appears
        try:
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-dialog")))
            close_button = modal.find_element(By.CSS_SELECTOR, "button.ui-dialog-titlebar-close")
            close_button.click()
            print("[Main] Closed the modal dialog box.")
        except:
            print("[Main] No modal dialog appeared or error handling modal")

        # Navigate to the correct month and year on the calendar
        target_month = booking_date.strftime("%B")
        target_year = booking_date.strftime("%Y")
        target_month_number = int(booking_date.strftime("%m"))

        while True:
            displayed_month_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-month")))
            displayed_month = displayed_month_element.text
            displayed_year_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-year")))
            displayed_year = displayed_year_element.text

            displayed_month_number = datetime.strptime(displayed_month, '%B').month

            if displayed_month == target_month and displayed_year == target_year:
                print("[Main] Calendar is displaying the correct month and year.")
                break

            if int(displayed_year) < int(target_year) or (
                    int(displayed_year) == int(target_year) and displayed_month_number < target_month_number):
                next_button = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "ui-datepicker-next")))
                next_button.click()
                print("[Main] Navigated to the next month.")
            else:
                prev_button = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "ui-datepicker-prev")))
                prev_button.click()
                print("[Main] Navigated to the previous month.")

            # Wait for the calendar to refresh
            wait.until(EC.staleness_of(displayed_month_element))

        # Extract the day of the booking_date
        target_day = booking_date.day

        for attempt in range(3):
            try:
                day_xpath = f"//td[@data-handler='selectDay']/a[text()='{target_day}']"
                day_element = wait.until(EC.element_to_be_clickable((By.XPATH, day_xpath)))
                day_element.click()
                print(f"[Main] Successfully selected the day: {target_day}")
                break
            except StaleElementReferenceException:
                print("[Main] Retrying due to stale element reference...")
                time.sleep(2)
        else:
            print(f"[Main] Failed to select the day after 3 attempts.")

        # Helper function to click element with retry mechanism
        def click_element_with_retry(driver, element, retries=3, delay=1):
            for attempt in range(retries):
                try:
                    element.click()
                    print(
                        f"[Main] Clicked on element: {element.get_attribute('title') if element.get_attribute('title') else element.tag_name}")
                    return True
                except StaleElementReferenceException:
                    print("[Main] Retrying due to stale element reference...")
                    time.sleep(delay)
                except Exception as e:
                    print(f"[Main] Unexpected error occurred while clicking: {e}")
                    time.sleep(delay)
            print(f"[Main] Failed to click the element after {retries} attempts.")
            return False

        # Timeblock selection code
        time.sleep(1)
        try:
            # Wait for the schedule wrapper to appear
            schema_wrapper = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'schemaWrapper')))
            print("[Main] Schedule loaded.")

            # Parse session start and end times into datetime objects
            desired_start_time = datetime.strptime(sessionStart, '%H:%M')
            desired_end_time = datetime.strptime(sessionEnd, '%H:%M')

            # Flag to indicate if booking was successful
            booking_successful = False

            for attempt in range(3):
                try:
                    # Refresh row elements to avoid stale element references
                    row_elements = schema_wrapper.find_elements(By.XPATH, ".//tr[starts-with(@class, 'trSchemaLane_')]")

                    for row in row_elements:
                        # Retry mechanism for each row
                        for row_attempt in range(3):
                            try:
                                time_blocks = row.find_elements(By.XPATH, ".//td/div[@class='divHour']/a")
                                available_time_blocks = {}

                                for block in time_blocks:
                                    # Extract the title attribute containing the time range and availability
                                    title = block.get_attribute('title')
                                    match = re.match(r"(\d{1,2}:\d{2}[ap]m)[–-](\d{1,2}:\d{2}[ap]m) - Available", title)
                                    if match:
                                        block_start_str = match.group(1)
                                        block_end_str = match.group(2)
                                        block_start_time = datetime.strptime(block_start_str, '%I:%M%p')
                                        block_end_time = datetime.strptime(block_end_str, '%I:%M%p')

                                        # Check if this block is within the desired time range
                                        if desired_start_time <= block_start_time < desired_end_time:
                                            available_time_blocks[block_start_time] = block

                                # Check for required consecutive time blocks
                                current_time = desired_start_time
                                blocks_to_click = []

                                while current_time < desired_end_time:
                                    block_element = available_time_blocks.get(current_time)
                                    if block_element:
                                        blocks_to_click.append(block_element)
                                        current_time += timedelta(minutes=30)
                                    else:
                                        print(
                                            f"[Main] Missing time block at {current_time.strftime('%I:%M%p')} in row {row.get_attribute('class')}")
                                        break

                                if current_time >= desired_end_time:
                                    # Found all required blocks in this row
                                    print(f"[Main] Found required time blocks in row {row.get_attribute('class')}")
                                    booking_successful = True

                                    # Click each block, refreshing before each click
                                    for block_element in blocks_to_click:
                                        if not click_element_with_retry(driver, block_element):
                                            booking_successful = False
                                            print(
                                                "[Main] Failed to click one of the required blocks due to stale element.")
                                            break

                                    # Exit row loop after successful booking
                                    if booking_successful:
                                        break

                            except StaleElementReferenceException:
                                print("[Main] Retrying current row due to stale element reference...")
                                time.sleep(2)
                                continue  # Retry the current row up to 3 times

                            # If successful, break out of retry loop for the current row
                            if booking_successful:
                                break

                        # If booking was successful, break out of the row processing loop
                        if booking_successful:
                            break

                    # If booking was successful, break out of the main retry loop
                    if booking_successful:
                        break
                    else:
                        print("[Main] Retrying entire row selection due to missing required blocks.")
                        time.sleep(2)

                except StaleElementReferenceException:
                    print("[Main] Retrying entire schedule loading due to stale element reference...")
                    time.sleep(2)

            if not booking_successful:
                print("[Main] Could not find the required consecutive time blocks in any row.")
                # Handle accordingly, e.g., raise an exception or return

            # Proceed with the booking as per your website's flow
            if booking_successful:
                print("[Main] Consecutive Timeblock Selection Successful.")

                # Wait and click on the "Continue" button
                time.sleep(1)
                continue_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@class, 'showRecapDialog') and contains(@title, 'Continue')]")))
                click_element_with_retry(driver, continue_button)
                print("[Main] Clicked on 'Continue' button.")

                # Wait and click on the "BOOK" button
                book_button = wait.until(EC.element_to_be_clickable((By.XPATH,
                                                                     "//a[contains(@class, 'ui-state-default') and contains(@href, '#') and contains(text(), 'Book')]")))
                click_element_with_retry(driver, book_button)
                print("[Main] Clicked on 'BOOK' button.")

        except Exception as e:
            print(f"[Main] An error occurred while selecting timeblocks: {e}")

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


def selenium_message_student_task(contactPreference, contactInfo, studentName, courtLocation, dayOfWeek, startTime,
                                  endTime):
    """
    Handles opening the messaging platform and sending a message to the student on Instagram or WhatsApp.
    """

    # Convert start and end times to 12-hour format with AM/PM
    start_time_12hr = datetime.strptime(startTime, '%H:%M').strftime('%I:%M %p')
    end_time_12hr = datetime.strptime(endTime, '%H:%M').strftime('%I:%M %p')

    # Craft the message
    message = (
        f"Hey {studentName}, are you down to train at {courtLocation}, "
        f"on {dayOfWeek} from {start_time_12hr} to {end_time_12hr}?"
    )

    if contactPreference == "Instagram":
        driver = get_chrome_driver()
        try:
            url = "https://www.instagram.com/"
            cookie_file = "instagram_cookies.json"

            # Inject cookies
            load_and_refresh_cookies(driver, url, cookie_file)

            # Remove the '@' from the contactInfo if it exists
            instagram_handle = contactInfo.lstrip('@')
            instagram_handle_url = f"https://www.instagram.com/{instagram_handle}/"

            # Navigate to the Instagram handle's page
            driver.get(instagram_handle_url)
            print(f"Navigated to Instagram handle: {instagram_handle_url}")

            wait = WebDriverWait(driver, 30)

            # Wait for the "Message" button to be clickable and click it
            try:
                message_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[text()='Message']"))
                )
                message_button.click()
                print(f"Clicked on the 'Message' button for {instagram_handle}.")
            except Exception as e:
                print(f"Could not find or click the 'Message' button: {e}")
                return

            # Click on the "Not Now" button if it appears
            try:
                not_now_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']"))
                )
                not_now_button.click()
                print("Clicked on 'Not Now' button.")
            except Exception as e:
                print(f"Could not find or click the 'Not Now' button: {e}")

            # Wait for the specific message input box and type the message
            try:
                message_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@aria-label='Message' and @role='textbox']")
                    )
                )
                # Type the message
                message_input.click()
                message_input.send_keys(message)
                print(f"Typed the message: {message}")

                # Find and click the send button
                send_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(@class, '_abl-')]")
                    )
                )
                send_button.click()
                print("Message sent successfully.")
            except Exception as e:
                print(f"Could not find the message input box or send the message: {e}")

        except Exception as e:
            print(f"An error occurred during messaging: {e}")
        finally:
            driver.quit()
            print("Browser closed.")

    elif contactPreference == "WhatsApp":
        try:
            phone_number = contactInfo.strip()
            if not phone_number.startswith('+'):
                print("Invalid phone number format. Must start with '+'.")
                return

            # Remove '+' for the URL format
            phone_number_for_url = phone_number.replace('+', '')
            message_encoded = urllib.parse.quote(message)
            url = f"https://wa.me/{phone_number_for_url}?text={message_encoded}"
            webbrowser.open(url)
            print(f"Opened WhatsApp chat for {phone_number} with pre-filled message.")
            print("Please review the message and click 'Send' in WhatsApp Web to send the message.")

        except Exception as e:
            print(f"Error during WhatsApp messaging: {e}")

    else:
        print(f"Unsupported contact preference: {contactPreference}")
        return


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/students')
def get_students():
    with open('students.json', 'r') as f:
        students_data = json.load(f)
    return jsonify(students_data)


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

    # Run the booking task in a separate thread
    threading.Thread(target=selenium_book_court_task, args=(
        startingWeek, dayOfWeek, courtLocation, courtType, sessionStart, sessionEnd)).start()

    return f"Booking court in progress!"


@app.route('/message-student', methods=['POST'])
def message_student():
    data = request.get_json()
    if not data:
        return "Invalid data received.", 400

    # Extract data from the request
    contactPreference = data.get('contactPreference')
    contactInfo = data.get('contactInfo')
    studentName = data.get('studentName')
    courtLocation = data.get('courtLocation')
    dayOfWeek = data.get('dayOfWeek')
    startTime = data.get('startTime')
    endTime = data.get('endTime')

    # Ensure all required fields are provided
    if not all([contactPreference, contactInfo, studentName, courtLocation, dayOfWeek, startTime, endTime]):
        return "Missing required fields.", 400

    # For debugging purposes, print the received data
    print("Received message student request:")
    print(f"Contact Preference: {contactPreference}")
    print(f"Contact Info: {contactInfo}")
    print(f"Student Name: {studentName}")
    print(f"Court Location: {courtLocation}")
    print(f"Day of Week: {dayOfWeek}")
    print(f"Start Time: {startTime}")
    print(f"End Time: {endTime}")

    # Run the messaging task in a separate thread
    threading.Thread(target=selenium_message_student_task, args=(
        contactPreference, contactInfo, studentName, courtLocation, dayOfWeek, startTime, endTime)).start()

    return f"Messaging student via {contactPreference} in progress!"


if __name__ == '__main__':
    app.run(debug=True)
