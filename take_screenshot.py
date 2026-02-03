from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time

TARGET_URL = "https://eplus.jp/sf/detail/2052790001"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1280,1600')
options.add_argument(f'--user-data-dir={os.getcwd()}/chrome_data')

driver = webdriver.Chrome(options=options)
try:
    print(f"Accessing {TARGET_URL}...")
    driver.get(TARGET_URL)
    time.sleep(5)
    
    save_path = os.path.join(IMAGE_DIR, "top_page.png")
    driver.save_screenshot(save_path)
    print(f"Screenshot saved to {save_path}")
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()
