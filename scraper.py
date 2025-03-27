# Importing libraries
import os
import time
import pandas as pd
import schedule
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver
import threading
import requests

# Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# File to store previous holders data
previous_data_file = ""

# Initialize URL (example DexScreener coin url)
url = "https://dexscreener.com/solana/9kgswjrkczs3ebukvbkbgdwj8bwtdwzzqxkufdhaps2a"

# Sends a message to the Telegram bot with basic retry logic
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    # Retrying to send if fails
    for attempt in range(3):  
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"Connection error: Failed to send message to Telegram (Attempt {attempt+1}/3)")
            time.sleep(5)
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error: {http_err}")
            return None
        except requests.exceptions.Timeout:
            print(f"Timeout error: Telegram request took too long (Attempt {attempt+1}/3)")
            time.sleep(5)
        except Exception as e:
            print(f"Unknown error while sending Telegram message: {e}")
            return None

    print("Failed to send message to Telegram after 3 attempts.")
    return None

# Stopping the script with keyboard
def stop_script():
    while True:
        user_input = input("Press 'q' and ENTER to stop the script: ").strip().lower()
        if user_input == "q":
            print("[!] Stopping the script...")
            os._exit(0)  # Exits the program

# Function to load previous data
def load_previous_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()

# Function to convert M, B, T suffixes into numeric values
def convert_to_number(value):
    if isinstance(value, float) or isinstance(value, int):
        return value

    value = str(value).upper().replace(',', '').strip()

    if value.endswith("M"):
        return float(value[:-1]) * 1_000_000
    elif value.endswith("B"):
        return float(value[:-1]) * 1_000_000_000
    elif value.endswith("T"):
        return float(value[:-1]) * 1_000_000_000_000
    else:
        return float(value)

# Function to compare old and new data
def compare_data(old_df, new_df):
    if old_df.empty:
        print("No previous data found. Saving current data as baseline.")
        new_df.to_csv(previous_data_file, index=False)
        return
    
    old_df["AMOUNT"] = old_df["AMOUNT"].apply(convert_to_number)
    new_df["AMOUNT"] = new_df["AMOUNT"].apply(convert_to_number)

    # New addresses & old aadresses
    new_addresses = set(new_df["ADDRESS"]) - set(old_df["ADDRESS"])
    removed_addresses = set(old_df["ADDRESS"]) - set(new_df["ADDRESS"])
    
    # Find changes in amount
    changes = []
    for _, new_row in new_df.iterrows():
        address = new_row["ADDRESS"]
        if address in old_df["ADDRESS"].values:
            old_row = old_df[old_df["ADDRESS"] == address].iloc[0]
            old_amount = old_row["AMOUNT"]
            new_amount = new_row["AMOUNT"]
            if old_amount != new_amount:
                changes.append((address, old_amount, new_amount))

    #Telegramming
    telegram_message = ""

    if new_addresses:
        telegram_message += f"📥 <b>New Addresses Added ({len(new_addresses)}):</b>\n"
        for addr in new_addresses:
            telegram_message += f"🔹 {addr}\n"

    if removed_addresses:
        telegram_message += f"\n🗑️ <b>Addresses Removed ({len(removed_addresses)}):</b>\n"
        for addr in removed_addresses:
            telegram_message += f"❌ {addr}\n"

    if changes:
        telegram_message += "\n🔄 <b>Holders with Updated Amounts:</b>\n"
        for address, old_amount, new_amount in changes:
            telegram_message += f"📌 {address}: {old_amount}% → {new_amount}%\n"

    if telegram_message:
        send_telegram_message(telegram_message)
        print("Changes sent to Telegram")
        time.sleep(5)
    else:
        send_telegram_message("✅ No changes detected in holders data.")
        print("No changes detected, message sent to Telegram.")
        time.sleep(5)

    # Save the updated data for next comparison
    new_df.to_csv(previous_data_file, index=False)

# Function to scrape and compare data from website
def scrape_and_compare():
    print("\n[+] Running Scraper...")

    # Initialize Driver
    # Headless mode: driver = Driver(uc=True, headless=True) # <- Doesn't open web browers, runs scraping in background
    driver = Driver(uc=True)
    driver.maximize_window() # Helps with finding html elements
    driver.get(url)

    time.sleep(5) # Page could load for longer than expected so let's wait 5 seconds
    # Wait for the "Holders" button and click it
    try:
        buttons = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'custom-tv0t33'))
        )
        for button in buttons:
            if "Holders" in button.text:
                button.click()
                break
    except Exception as e:
        print("Error: Could not find the 'Holders' button. Check the class name or page load issue.")
        driver.quit()
        return

    # Extract Data
    try:
        data = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'custom-14iqb65'))
        )
        data = data.text.split('\n')

        wallet_links = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'custom-1hhf88o'))
        )
        wallet_urls = [wallet.get_attribute("href") for wallet in wallet_links]
    except Exception as e:
        print("Error: Could not scrape data. Retrying in next cycle.")
        driver.quit()
        return

    driver.quit() # Close browser

    # Data processing
    cleaned_data = [item.replace("🏦", "").replace("999.9M", "").strip() for item in data]
    cleaned_data = [item for item in cleaned_data if item]  # Remove empty values

    columns = cleaned_data[:5]
    rows = []
    current_row = []

    for item in cleaned_data[5:]:  # Start from index 5 to skip column headers
        if item.startswith('#'):  # Detect a new row by rank number
            if current_row:
                current_row = current_row[:5]
                rows.append(current_row)
            current_row = [item]  # Start a new row
        else:
            current_row.append(item)

    if current_row:
        current_row = current_row[:5]
        rows.append(current_row)

    df = pd.DataFrame(rows, columns=columns)
    df = df.iloc[1:-1].reset_index(drop=True)  # Remove first and last row
    df = df.assign(EXP=wallet_urls)

    print("[+] Scraping complete. Comparing data...")

    # Load & compare
    old_df = load_previous_data(previous_data_file)
    compare_data(old_df, df)

    print("[+] Done. Waiting for next run...")

# Schedule the task
threading.Thread(target=stop_script, daemon=True).start()
schedule.every(20).seconds.do(scrape_and_compare)

print("[*] Background scraper started...")

# Script running indefinitely
while True:
    schedule.run_pending()
