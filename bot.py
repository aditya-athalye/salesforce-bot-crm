import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# ================= CONFIGURATION =================
EXCEL_FILE = 'Customer Details for QA Format.xlsx'
SF_LOGIN_URL = 'https://tpss.my.site.com/DealerPortal/s/login/'
USERNAME = 'USERNAME_HERE'  # <-- REPLACE WITH ACTUAL USERNAME
PASSWORD = 'PASSWORD_HERE'  # <-- REPLACE WITH ACTUAL PASSWORD
# =================================================

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def login(driver):
    print("Logging in...")
    driver.get(SF_LOGIN_URL)
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Username')]"))).send_keys(USERNAME)
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(PASSWORD + Keys.ENTER)
        
        print("Waiting for Dashboard...")
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'search-trigger')] | //button[@title='Search']"))
        )
        print("[✓] Login Successful.")
        time.sleep(3)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Login Failed: {e}")
        input("Press Enter to close browser...")
        driver.quit()
        exit()

def format_date(value):
    if pd.isna(value) or value == '': return ""
    try: return pd.to_datetime(value).strftime('%d/%m/%Y')
    except: return str(value)

def search_asset(driver, asset_no):
    search_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'search-trigger')] | //button[@title='Search']"))
    )
    driver.execute_script("arguments[0].click();", search_icon)
    time.sleep(1)

    search_input = driver.switch_to.active_element
    search_input.send_keys(asset_no)
    time.sleep(1)
    search_input.send_keys(Keys.ENTER)
    print(f"   -> Searching for {asset_no}...")

    asset_link = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, f"//a[@title='{asset_no}'] | //a[text()='{asset_no}']"))
    )
    driver.execute_script("arguments[0].click();", asset_link)
    
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@name='Edit'] | //button[text()='Edit']"))
    )

def fill_text_field(driver, label_text, value, clear_first=True):
    if value is None: value = ""
    try:
        xpath = f"//label[contains(text(),'{label_text}')]/following-sibling::div//input | //label[contains(text(),'{label_text}')]/following-sibling::div//textarea"
        field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
        time.sleep(0.3)
        
        if clear_first:
            # TRIPLE-THREAT CLEARING: Ensures Asset Name and Pincode are fully wiped
            try:
                driver.execute_script("arguments[0].value = '';", field)
                field.clear()
                field.click()
                field.send_keys(Keys.CONTROL + "a")
                field.send_keys(Keys.BACKSPACE)
            except: pass
            time.sleep(0.3)
        
        field.send_keys(str(value))
        print(f"      -> Set '{label_text}' to '{value}'")
    except Exception as e:
        print(f"\n🛑 [ERROR] Failed to fill '{label_text}'")
        print(f"Details: {e}")
        input("BOT PAUSED: Press Enter to quit...")
        driver.quit()
        exit()

def select_dropdown(driver, label_text, value, is_optional=False, wait_for_manual=False):
    """
    Selects a dropdown.
    - wait_for_manual=True: Pauses the bot and lets the user click it instead of crashing.
    - is_optional=True: Skips entirely without pausing if it fails.
    """
    try:
        print(f"      ...Setting '{label_text}' to '{value}'")
        time.sleep(0.5)
        
        xpath_btn = f"//label[contains(normalize-space(),'{label_text}')]/following-sibling::div//button"
        if not driver.find_elements(By.XPATH, xpath_btn):
            xpath_btn = f"//button[contains(@aria-label, '{label_text}')]"

        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(0.5)

        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
        
        # Look for option based on value or data-value
        xpath_opt = f"//lightning-base-combobox-item[@data-value='{value}'] | //lightning-base-combobox-item//span[@title='{value}'] | //span[text()='{value}']"
        
        try:
            option = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.XPATH, xpath_opt)))
        except:
            if not is_optional and not wait_for_manual:
                print("         ...List didn't open? Retrying click...")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                option = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, xpath_opt)))
            elif wait_for_manual:
                raise Exception("Manual Intervention Triggered")
            else:
                raise Exception("Optional skip")

        driver.execute_script("arguments[0].click();", option)
        time.sleep(0.5)

        # Close the dropdown list
        try:
            driver.find_element(By.XPATH, "//div[contains(@class, 'modal-body')] | //h2").click()
        except:
            driver.find_element(By.TAG_NAME, "body").click()
            
        print(f"      -> [✓] Locked value: {value}")

    except Exception as e:
        if wait_for_manual:
            # ====================================================
            # MANUAL FALLBACK TRIGGERED
            # ====================================================
            print(f"\n      ⚠️ [MANUAL ACTION REQUIRED] Failed to auto-select '{value}' in '{label_text}'.")
            input(f"      👉 PLEASE SELECT IT MANUALLY IN THE BROWSER, then press ENTER here to continue... ")
            print(f"      -> Resuming script...")
        elif is_optional:
            print(f"      [!] SKIPPING '{label_text}' (As requested, proceeding...)")
        else:
            print(f"\n🛑 [ERROR] Failed to select '{value}' in '{label_text}'")
            print(f"Details: {e}")
            input("BOT PAUSED: Press Enter to quit...")
            driver.quit()
            exit()

def process_records(driver):
    df = pd.read_excel(EXCEL_FILE).fillna('')
    
    for index, row in df.iterrows():
        asset_no = str(row.get('Asset No.', '')).strip()
        if not asset_no: continue

        print(f"\n--- Processing {index + 1}: {asset_no} ---")
        
        if "DealerPortal/s/" not in driver.current_url:
            driver.get("https://tpss.my.site.com/DealerPortal/s/")
            time.sleep(3)

        try:
            search_asset(driver, asset_no)
            
            edit_btn = driver.find_element(By.XPATH, "//button[@name='Edit'] | //button[text()='Edit']")
            driver.execute_script("arguments[0].click();", edit_btn)
            time.sleep(5) 
            
            # ==========================================
            #         15-STEP EDITING SEQUENCE
            # ==========================================
            
            cust_name = str(row.get('Customer Name', '')).strip()
            fill_text_field(driver, "Asset Name", cust_name, clear_first=True)

            fill_text_field(driver, "I & C Date", format_date(row.get('Date of Release', '')))
            fill_text_field(driver, "Installation Date", format_date(row.get('Date of Installation', '')))

            # COMPULSORY WITH MANUAL FALLBACK: Existing Opportunity available
            select_dropdown(driver, "Existing Opportunity available", "No", wait_for_manual=True)

            select_dropdown(driver, "Roof type", "CP Supplied –Customized Elevated Structure")

            # OPTIONAL: PM Surya Ghar Yojana
            select_dropdown(driver, "PM Surya Ghar Yojana", "Yes", is_optional=True)

            select_dropdown(driver, "Region", "West")
            select_dropdown(driver, "TPSSL Scope", "Supply without structure")

            fill_text_field(driver, "District", "Nashik")
            fill_text_field(driver, "Street Details", row.get('Address', ''))

            pincode = str(row.get('Pincode', '')).split('.')[0]
            fill_text_field(driver, "Pincode", pincode, clear_first=True)

            select_dropdown(driver, "Type of Installation", "Roof Top-Grid Tied")

            mobile = str(row.get('Contact Mobile', '')).split('.')[0]
            fill_text_field(driver, "Contact Mobile", mobile)

            fill_text_field(driver, "Contact Name", cust_name)
            fill_text_field(driver, "Asset Email", row.get('Asset Email', ''))
            
            # Save
            save_btn = driver.find_element(By.XPATH, "//button[@name='SaveEdit'] | //button[text()='Save']")
            driver.execute_script("arguments[0].click();", save_btn)
            
            WebDriverWait(driver, 15).until(EC.invisibility_of_element_located((By.CLASS_NAME, "modal-container")))
            print("   [✓] Saved Successfully.")
            
        except Exception as e:
            print(f"\n🛑 [CRITICAL FAILURE] on Asset {asset_no}")
            print(f"Error: {e}")
            input("BOT PAUSED: Press Enter to close...")
            driver.quit()
            exit()

def main():
    driver = setup_driver()
    login(driver)
    process_records(driver)
    print("\nAll tasks completed.")
    driver.quit()

if __name__ == "__main__":
    main()