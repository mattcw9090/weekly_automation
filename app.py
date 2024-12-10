from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import time
import re
import threading
import os
import urllib.parse
import webbrowser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

app = Flask(__name__, static_folder='static')

# Global Constants
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
DAY_OF_WEEK_MAPPING = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}
TIMEZONE = 'Australia/Perth'


# Helper Functions
def load_json(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def save_json(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Configuration saved to {file_path}")
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False


def get_calendar_service():
    creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
    return build('calendar', 'v3', credentials=creds)


def click_element_with_retry(driver, element, retries=3, delay=1):
    for attempt in range(retries):
        try:
            element.click()
            print(f"Clicked on element: {element.get_attribute('title') or element.tag_name}")
            return True
        except StaleElementReferenceException:
            print("StaleElementReferenceException encountered. Retrying...")
            time.sleep(delay)
        except Exception as e:
            print(f"Unexpected error while clicking: {e}")
            time.sleep(delay)
    print("Failed to click the element after retries.")
    return False


# Google Calendar Integration
def add_event_to_calendar(starting_week, student_name, day_of_week, court_location, session_start, session_end):
    service = get_calendar_service()
    starting_date = datetime.strptime(starting_week, "%Y-%m-%d")
    booking_date = starting_date + timedelta(days=DAY_OF_WEEK_MAPPING[day_of_week])

    start_time = datetime.combine(booking_date, datetime.strptime(session_start, '%H:%M').time())
    end_time = datetime.combine(booking_date, datetime.strptime(session_end, '%H:%M').time())

    event = {
        'summary': f'Coaching Session for {student_name} at {court_location}',
        'location': court_location,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': TIMEZONE},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': TIMEZONE},
        'reminders': {'useDefault': True},
    }

    try:
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event_result.get('htmlLink')}")
        return f"Event created: {event_result.get('htmlLink')}"
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"An error occurred: {e}"


# Flask Routes for Configuration
@app.route('/config')
def get_config():
    config = load_json('config.json')
    if config is not None:
        return jsonify(config)
    return jsonify({'error': 'Config file not found or invalid.'}), 404


@app.route('/save-config', methods=['POST'])
def save_config():
    config_data = request.get_json()
    if not config_data:
        return jsonify({"error": "Invalid data received."}), 400
    if save_json('config.json', config_data):
        return jsonify({"message": "Configuration saved successfully."}), 200
    return jsonify({"error": "Failed to save configuration."}), 500


# Flask Route to Add Event to Calendar
@app.route('/add-to-calendar', methods=['POST'])
def add_to_calendar():
    data = request.get_json()
    required_fields = ['startingWeek', 'studentName', 'dayOfWeek', 'courtLocation', 'sessionStart', 'sessionEnd']
    if not data or not all(field in data for field in required_fields):
        return "Missing required fields.", 400
    threading.Thread(target=add_event_to_calendar, args=(
        data['startingWeek'], data['studentName'], data['dayOfWeek'], data['courtLocation'],
        data['sessionStart'], data['sessionEnd']
    )).start()
    return "Adding event to calendar in progress!", 200


# Selenium Setup
def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def load_cookies(driver, url, cookie_file):
    try:
        driver.get(url)
        driver.delete_all_cookies()
        cookies = load_json(cookie_file)
        if not cookies:
            print(f"No cookies found in {cookie_file}.")
            return
        for cookie in cookies:
            cookie['domain'] = cookie.get('domain', '').lstrip('.')
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                del cookie['sameSite']
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        driver.refresh()
        print(f"Loaded cookies from {cookie_file} and refreshed {url}.")
    except Exception as e:
        print(f"Error loading cookies from {cookie_file}: {e}")


# Selenium Tasks
def selenium_buy_credits_task(credits_list):
    driver = get_chrome_driver()
    try:
        # Load necessary cookies
        load_cookies(driver, "https://www.google.com", "google_cookies.json")
        load_cookies(driver, "https://www.paypal.com.au", "paypal_cookies.json")
        load_cookies(driver, "https://pba.yepbooking.com.au", "pba_cookies.json")

        # Pre-compile the regex pattern for efficiency
        price_pattern = re.compile(r'Price: \$([\d.]+)')

        for idx, credit in enumerate(credits_list):
            # Open a new tab for each credit after the first one
            if idx > 0:
                driver.execute_script("window.open('');")

            # Switch to the current tab
            driver.switch_to.window(driver.window_handles[idx])
            wait = WebDriverWait(driver, 60)

            try:
                # Navigate to the credit list page
                driver.get("https://pba.yepbooking.com.au/user.php?tab=credit-list")

                # Locate and interact with the payment credit dropdown
                dropdown = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "paymentCreditSelect")))
                select = Select(dropdown)

                # Find the option that matches the credit amount
                selected_option = next(
                    (
                        option for option in select.options
                        if (match := price_pattern.search(option.text)) and float(match.group(1)) == credit['amount']
                    ),
                    None
                )

                if selected_option:
                    select.select_by_value(selected_option.get_attribute('value'))
                else:
                    # Skip to the next credit if no matching option is found
                    continue

                # Proceed with the payment steps
                wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paymentCreditLink[title='Top up credit']"))).click()
                wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input.paymentTypeCheck[type='radio'][value='PAYPAL']"))).click()
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.paymentButton[title='Pay now']"))).click()

                # Load PayPal cookies and complete the purchase
                wait.until(EC.element_to_be_clickable((By.ID, "payment-submit-btn"))).click()
                wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.donepage-return-to-merchant-button"))).click()

            except Exception:
                # Handle exceptions for the current tab and continue with the next
                continue

        # Keep the browser open for manual inspection after processing all credits
        while True:
            time.sleep(5000)
    finally:
        # Ensure the browser is closed upon completion or error
        driver.quit()


def selenium_book_court_task(starting_week, day_of_week, court_location, court_type, session_start, session_end):
    driver = get_chrome_driver()
    try:
        load_cookies(driver, "https://www.google.com", "google_cookies.json")
        load_cookies(driver, "https://pba.yepbooking.com.au", "pba_cookies.json")

        wait = WebDriverWait(driver, 60)
        court_button_ids = {
            ("PBA Canningvale", "Hebat Court"): "ui-id-11",
            ("PBA Canningvale", "Super Court"): "ui-id-9",
            ("PBA Malaga", None): "ui-id-1"
        }
        button_id = court_button_ids.get((court_location, court_type)) or court_button_ids.get((court_location, None))
        if not button_id:
            raise ValueError("Invalid court location or type provided.")
        wait.until(EC.element_to_be_clickable((By.ID, button_id))).click()

        starting_date = datetime.strptime(starting_week, "%Y-%m-%d")
        booking_date = starting_date + timedelta(days=DAY_OF_WEEK_MAPPING[day_of_week])

        # Navigate to the correct month and year on the calendar
        target_month_year = booking_date.strftime("%B %Y")
        while True:
            displayed_month_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-month")))
            displayed_year_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-year")))
            displayed_month = displayed_month_element.text
            displayed_year = displayed_year_element.text
            current_display = f"{displayed_month} {displayed_year}"
            if current_display == target_month_year:
                break
            elif datetime.strptime(current_display, "%B %Y") < booking_date:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ui-datepicker-next"))).click()
            else:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ui-datepicker-prev"))).click()
            # Wait for the calendar to update
            time.sleep(1)  # Allow calendar to update
            wait.until(EC.staleness_of(displayed_month_element))

        # Select the booking day
        target_day = booking_date.day
        try:
            day_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//td[@data-handler='selectDay']/a[text()='{target_day}']")))
            day_element.click()
        except Exception:
            return

        # Timeblock selection
        try:
            schema_wrapper = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'schemaWrapper')))

            desired_start = datetime.strptime(session_start, '%H:%M')
            desired_end = datetime.strptime(session_end, '%H:%M')

            booking_successful = False
            rows = schema_wrapper.find_elements(By.XPATH, ".//tr[starts-with(@class, 'trSchemaLane_')]")

            for row in rows:
                try:
                    if not row.is_displayed():
                        continue

                    time_blocks = row.find_elements(By.XPATH, ".//td/div[@class='divHour']/a")

                    available_blocks = {}
                    for block in time_blocks:
                        title = block.get_attribute('title')
                        if "Available" in title:
                            try:
                                block_time_str = title.split('–')[0].strip()
                                block_time = datetime.strptime(block_time_str, '%I:%M%p')
                                available_blocks[block_time] = block
                            except ValueError:
                                continue

                    blocks_to_click = []
                    current_time = desired_start
                    while current_time < desired_end:
                        block = available_blocks.get(current_time)
                        if block:
                            blocks_to_click.append(block)
                            current_time += timedelta(minutes=30)
                        else:
                            break

                    if current_time >= desired_end:
                        for block in blocks_to_click:
                            if not click_element_with_retry(driver, block):
                                break
                        booking_successful = True
                        break
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue

            if not booking_successful:
                return

            # Proceed with booking
            try:
                continue_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@class, 'showRecapDialog') and contains(@title, 'Continue')]")))
                continue_button.click()
            except Exception:
                return

            try:
                book_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@class, 'ui-state-default') and contains(text(), 'Book')]")))
                book_button.click()
            except Exception:
                return

        except Exception:
            pass

        # Keep the browser open for manual inspection
        try:
            while True:
                time.sleep(5000)
        except KeyboardInterrupt:
            pass

    except Exception:
        pass
    finally:
        driver.quit()


def selenium_message_student_task(contact_pref, contact_info, student_name, court_location, day_of_week, start_time,
                                  end_time):
    message = f"Hey {student_name}, are you down to train at {court_location}, on {day_of_week} from {datetime.strptime(start_time, '%H:%M').strftime('%I:%M %p')} to {datetime.strptime(end_time, '%H:%M').strftime('%I:%M %p')}?"

    if contact_pref == "Instagram":
        driver = get_chrome_driver()
        try:
            load_cookies(driver, "https://www.instagram.com/", "instagram_cookies.json")
            instagram_handle = contact_info.lstrip('@')
            driver.get(f"https://www.instagram.com/{instagram_handle}/")
            print(f"Navigated to Instagram handle: {instagram_handle}")

            wait = WebDriverWait(driver, 30)
            try:
                message_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Message']")))
                message_button.click()
                print("Clicked on the 'Message' button.")
            except TimeoutException:
                print("Message button not found.")
                return

            try:
                not_now_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']")))
                not_now_button.click()
                print("Clicked on 'Not Now' button.")
            except TimeoutException:
                print("'Not Now' button not found.")

            try:
                message_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@aria-label='Message' and @contenteditable='true']"))
                )
                driver.execute_script("arguments[0].focus();", message_input)
                message_input.send_keys(message)
                print(f"Typed the message: {message}")

                time.sleep(500)
            except Exception as e:
                print(f"Failed to send message: {e}")

        except Exception as e:
            print(f"An error occurred during Instagram messaging: {e}")
        finally:
            driver.quit()
            print("Browser closed.")

    elif contact_pref == "WhatsApp":
        try:
            phone_number = contact_info.strip()
            if not phone_number.startswith('+'):
                print("Invalid phone number format. Must start with '+'.")
                return
            phone_number_for_url = phone_number.replace('+', '')
            message_encoded = urllib.parse.quote(message)
            url = f"https://wa.me/{phone_number_for_url}?text={message_encoded}"
            webbrowser.open(url)
            print(f"Opened WhatsApp chat for {phone_number} with pre-filled message.")
            print("Please review the message and click 'Send' in WhatsApp Web to send the message.")
        except Exception as e:
            print(f"Error during WhatsApp messaging: {e}")
    else:
        print(f"Unsupported contact preference: {contact_pref}")


# Flask Routes for Selenium Tasks
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/students')
def get_students():
    students = load_json('students.json')
    if students is not None:
        return jsonify(students)
    return jsonify({'error': 'Students data not found or invalid.'}), 404


@app.route('/buy-credits', methods=['POST'])
def buy_credits():
    data = request.get_json()
    credits_to_buy = data.get('creditsToBuy') if data else None
    if not credits_to_buy:
        return "Invalid data received.", 400

    print("Received booking request:")
    print(f"Credits to Buy: {credits_to_buy}")

    credits_list = []
    for line in re.sub(r'<[^>]*>', '\n', credits_to_buy).split('\n'):
        match = re.match(r'(\d+)x \$([\d.]+)', line.strip())
        if match:
            times, amount = int(match.group(1)), float(match.group(2))
            credits_list.extend([{'amount': amount} for _ in range(times)])
        else:
            print(f"Could not parse line: {line.strip()}")

    threading.Thread(target=selenium_buy_credits_task, args=(credits_list,)).start()
    print(f"Started buying process for {len(credits_list)} credits.")
    return "Buying credits in progress!", 200


@app.route('/book-court', methods=['POST'])
def book_court():
    data = request.get_json()
    required_fields = ['startingWeek', 'dayOfWeek', 'courtLocation', 'courtType', 'sessionStart', 'sessionEnd']
    if not data or not all(field in data for field in required_fields):
        return "Missing required fields.", 400

    print("Received book court request:")
    for field in required_fields:
        print(f"{field}: {data.get(field)}")

    threading.Thread(target=selenium_book_court_task, args=(
        data['startingWeek'], data['dayOfWeek'], data['courtLocation'],
        data['courtType'], data['sessionStart'], data['sessionEnd']
    )).start()
    return "Booking court in progress!", 200


@app.route('/message-student', methods=['POST'])
def message_student():
    data = request.get_json()
    required_fields = ['contactPreference', 'contactInfo', 'studentName', 'courtLocation', 'dayOfWeek', 'startTime',
                       'endTime']
    if not data or not all(field in data for field in required_fields):
        return "Missing required fields.", 400

    print("Received message student request:")
    for field in required_fields:
        print(f"{field}: {data.get(field)}")

    threading.Thread(target=selenium_message_student_task, args=(
        data['contactPreference'], data['contactInfo'], data['studentName'],
        data['courtLocation'], data['dayOfWeek'], data['startTime'], data['endTime']
    )).start()
    return f"Messaging student via {data['contactPreference']} in progress!", 200


if __name__ == '__main__':
    app.run(debug=True)
