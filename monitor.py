from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import datetime
import requests
import json
import csv
import re
from dotenv import load_dotenv

# Load .env
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

CONFIG_FILE = 'config.json'
LOG_DIR = 'logs'
TARGET_URL = "https://eplus.jp/sf/detail/2052790001"

# Track notified statuses to prevent spam
notified_statuses = {}

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("LINE Token not found, skipping notification.")
        return

    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    data = {
        'messages': [{'type': 'text', 'text': message}]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"LINE Notification Sent: {message.splitlines()[0]}...")
    except Exception as e:
        print(f"Failed to send LINE: {e}")

def save_log_csv(status_data):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_path = os.path.join(LOG_DIR, f"{today_str}.csv")
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    
    # status_data is a dict { "date_name": "status" }
    fieldnames = ["Timestamp"] + sorted(status_data.keys())
    
    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(fieldnames)
            
            row = [timestamp]
            for key in fieldnames[1:]:
                row.append(status_data.get(key, "-"))
            writer.writerow(row)
    except Exception as e:
        print(f"Log error: {e}")

def check_tickets():
    config = load_config()
    target_tickets = config.get('target_tickets', [])
    if not target_tickets:
        print("No target tickets configured.")
        return

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'--user-data-dir={os.getcwd()}/chrome_data')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Checking eplus page...")
        driver.get(TARGET_URL)
        time.sleep(5) # Wait for page load

        articles = driver.find_elements(By.CLASS_NAME, 'block-ticket-article')
        print(f"DEBUG: Found {len(articles)} articles.")
        
        current_status_map = {}
        messages = []

        for article in articles:
            article_class = article.get_attribute('class')
            
            for target in target_tickets:
                target_id = target['id']
                if target_id in article_class:
                    # Found matching date/performance
                    
                    # Look for ticket blocks
                    ticket_blocks = article.find_elements(By.CLASS_NAME, 'block-ticket')
                    
                    for block in ticket_blocks:
                        try:
                            title_el = block.find_element(By.CLASS_NAME, 'block-ticket__title')
                            status_el = block.find_element(By.CLASS_NAME, 'ticket-status')
                            
                            # Use textContent
                            title_text = title_el.get_attribute("textContent").strip()
                            status_text = status_el.get_attribute("textContent").strip()
                            
                            # Clean up
                            title_text = re.sub(r'\s+', ' ', title_text)
                            status_text = re.sub(r'\s+', ' ', status_text)
                            
                            # Filter by keywords if configured
                            keywords = target.get('keywords', [])
                            if keywords:
                                if not any(k in title_text for k in keywords):
                                    continue 
                            
                            unique_key = f"{target['name']} [{title_text}]"
                            current_status_map[unique_key] = status_text
                            
                            print(f"Found: {unique_key} -> {status_text}")

                            # Determine availability
                            # Positive phrases
                            is_available = any(x in status_text for x in ["受付中", "販売中", "残りわずか", "空席あり"])
                            
                            prev_status = notified_statuses.get(unique_key)
                            
                            # Notify logic
                            if is_available:
                                # If it's available, notify if it wasn't available before OR we haven't tracked it yet
                                if prev_status != status_text:
                                    messages.append(f"【AVAILABLE】\n{unique_key}\nStatus: {status_text}\nLink: {TARGET_URL}")
                                    notified_statuses[unique_key] = status_text
                            else:
                                # Not available, just update status
                                notified_statuses[unique_key] = status_text
                                
                        except Exception as inner_e:
                            print(f"Error parsing ticket block: {inner_e}")
                            continue

        if messages:
            send_line_message("\n\n".join(messages))
        
        if current_status_map:
            save_log_csv(current_status_map)
        else:
            print("No matching tickets found on page.")

    except Exception as e:
        print(f"Error during check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

def main():
    print("Starting HORMONE-Ticket Monitor...")
    print(f"Target URL: {TARGET_URL}")
    
    # Run once immediately
    check_tickets()
    
    while True:
        try:
            config = load_config()
            interval = config.get('check_interval', 300)
            time.sleep(interval)
            check_tickets()
        except KeyboardInterrupt:
            print("Stopping...")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
