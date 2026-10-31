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
from selenium.common.exceptions import TimeoutException

# ================= CONFIGURATION =================
EXCEL_FILE = 'Customer Details for QA Format.xlsx'
OUTPUT_EXCEL_FILE = 'Customer Details for QA Format_with_errors.xlsx'
SF_LOGIN_URL = 'https://tpss.my.site.com/DealerPortal/s/login/'
USERNAME = 'adityasolartps@gmail.com'  # <-- REPLACE WITH ACTUAL USERNAME
PASSWORD = 'hhhh@8888'                 # <-- REPLACE WITH ACTUAL PASSWORD
# =================================================

# Columns used for validation
COL_EMAIL = 'Asset Email'
COL_PHONE = 'Contact Mobile'   
COL_ALT_PHONE = 'Contact Phone'  


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
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Username')]"))
        ).send_keys(USERNAME)
        
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
    if pd.isna(value) or value == '':
        return ""
    try:
        return pd.to_datetime(value).strftime('%d/%m/%Y')
    except:
        return str(value)


def search_asset(driver, asset_no):
    """Returns True if found, False if not found."""
    try:
        search_icon = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'search-trigger')] | //button[@title='Search']"))
        )
        driver.execute_script("arguments[0].click();", search_icon)
        time.sleep(1)

        search_input = driver.switch_to.active_element
        search_input.send_keys(asset_no)
        time.sleep(1)
        search_input.send_keys(Keys.ENTER)
        print(f" -> Searching for {asset_no}...")

        time.sleep(3) # Give Salesforce's dynamic search results a moment to populate

        # Target the link specifically under the "Assets" section
        xpath_asset_link = f"//*[(text()='Assets' or @title='Assets')]/following::a[@title='{asset_no}' or text()='{asset_no}'][1]"
        
        try:
            # Try the strict "Assets only" path first
            asset_link = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, xpath_asset_link))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", asset_link)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", asset_link)
        except:
            # Fallback if there's no header (e.g., only 1 result system-wide)
            fallback_xpath = f"//a[@title='{asset_no}'] | //a[text()='{asset_no}']"
            asset_link = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, fallback_xpath))
            )
            driver.execute_script("arguments[0].click();", asset_link)

        # Confirm we landed on the actual record page by waiting for the Edit button
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@name='Edit'] | //button[text()='Edit']"))
        )
        return True

    except Exception:
        print(f" [!] Search Failed: Asset '{asset_no}' could not be found or clicked.")
        return False


def fill_text_field(driver, label_text, value, clear_first=True):
    if value is None:
        value = ""
    try:
        xpath = (
            f"//label[contains(text(),'{label_text}')]/following-sibling::div//input | "
            f"//label[contains(text(),'{label_text}')]/following-sibling::div//textarea"
        )
        field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
        time.sleep(0.3)

        if clear_first:
            try:
                driver.execute_script("arguments[0].value = '';", field)
                field.clear()
                field.click()
                field.send_keys(Keys.CONTROL + "a")
                field.send_keys(Keys.BACKSPACE)
            except:
                pass
            time.sleep(0.3)

        field.send_keys(str(value))
        print(f" -> Set '{label_text}' to '{value}'")
    except Exception as e:
        raise Exception(f"Failed to fill '{label_text}': {e}")


def select_dropdown(driver, label_text, value, is_optional=False, wait_for_manual=False):
    try:
        print(f" ...Setting '{label_text}' to '{value}'")
        time.sleep(0.5)

        xpath_btn = f"//label[contains(normalize-space(),'{label_text}')]/following-sibling::div//button"
        if not driver.find_elements(By.XPATH, xpath_btn):
            xpath_btn = f"//button[contains(@aria-label, '{label_text}')]"

        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(0.5)

        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)

        xpath_opt = (
            f"//lightning-base-combobox-item[@data-value='{value}'] | "
            f"//lightning-base-combobox-item//span[@title='{value}'] | "
            f"//span[text()='{value}']"
        )

        try:
            option = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.XPATH, xpath_opt)))
        except:
            if not is_optional and not wait_for_manual:
                print(" ...List didn't open? Retrying click...")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                option = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, xpath_opt)))
            elif wait_for_manual:
                raise Exception("Manual Intervention Triggered")
            else:
                raise Exception("Optional skip")

        driver.execute_script("arguments[0].click();", option)
        time.sleep(0.5)

        try:
            driver.find_element(By.XPATH, "//div[contains(@class, 'modal-body')] | //h2").click()
        except:
            driver.find_element(By.TAG_NAME, "body").click()

        print(f" -> [✓] Locked value: {value}")

    except Exception as e:
        if wait_for_manual:
            print(f"\n ⚠️ [MANUAL ACTION REQUIRED] Failed to auto-select '{value}' in '{label_text}'.")
            input(f" 👉 PLEASE SELECT IT MANUALLY IN THE BROWSER, then press ENTER here to continue... ")
            print(f" -> Resuming script...")
        elif is_optional:
            print(f" [!] SKIPPING '{label_text}' (As requested, proceeding...)")
        else:
            raise Exception(f"Failed to select '{value}' in '{label_text}': {e}")


# ========== VALIDATION HELPERS ==========

def validate_row(row_index: int, row: pd.Series, error_log: list, error_flags: dict):
    row_display = row_index + 2  
    
    email = str(row.get(COL_EMAIL, '')).strip()
    if email and " " in email:
        error_log.append(f"Row {row_display} [{COL_EMAIL}]: Contains spaces -> '{email}'")
        error_flags[row_index] = True

    for col in [COL_PHONE, COL_ALT_PHONE]:
        if col in row:
            raw_val = str(row.get(col, '')).strip()
            if raw_val.endswith('.0'):
                raw_val = raw_val[:-2]
                
            if raw_val:
                if " " in raw_val:
                    error_log.append(f"Row {row_display} [{col}]: Contains spaces -> '{raw_val}'")
                    error_flags[row_index] = True
                
                digits_only = ''.join(ch for ch in raw_val if ch.isdigit())
                if digits_only and len(digits_only) != 10:
                    error_log.append(f"Row {row_display} [{col}]: Mobile length is {len(digits_only)} instead of 10 -> '{raw_val}'")
                    error_flags[row_index] = True

def highlight_errors_and_save(df: pd.DataFrame, error_flags: dict):
    try:
        def row_style(row):
            if error_flags.get(row.name, False):
                return ['background-color: #FFB3B3'] * len(row) 
            return [''] * len(row)

        styled = df.style.apply(row_style, axis=1)
        styled.to_excel(OUTPUT_EXCEL_FILE, engine='openpyxl', index=False)
        print(f"\n[✓] Error-highlighted Excel saved as: {OUTPUT_EXCEL_FILE}")
    except Exception as e:
        print(f"\n[WARNING] Could not save highlighted Excel file: {e}")


# ========== MAIN PROCESSING ==========

def process_records(driver):
    print("\n=== READING & VALIDATING EXCEL DATA ===")
    df = pd.read_excel(EXCEL_FILE).fillna('')
    
    error_log = []     
    error_flags = {}    

    for index, row in df.iterrows():
        validate_row(index, row, error_log, error_flags)

    total_errors = len(error_log)
    
    if total_errors > 0:
        print("\n" + "="*50)
        print(f" ERROR SUMMARY: {total_errors} ISSUES DETECTED ")
        print("="*50)
        for err in error_log:
            print(f"- {err}")
        print("="*50)
        
        print("\n⚠️ ACTION REQUIRED")
        choice = input(f"Do you want to SKIP these {len(error_flags)} errored rows and process the remaining valid data? (y/n): ")
        if choice.strip().lower() != 'y':
            print("\nOperation aborted by user. Exiting script...")
            highlight_errors_and_save(df, error_flags)
            return
        else:
            print("\nProceeding with valid data. Errored rows will be skipped.")
    else:
        print("\n[✓] Data is clean. No pre-validation errors found. Proceeding with all rows.")

    print("\n=== STARTING SALESFORCE AUTOMATION ===")
    processed_count = 0
    skipped_count = 0

    for index, row in df.iterrows():
        asset_no = str(row.get('Asset No.', '')).strip()
        if not asset_no:
            continue

        if error_flags.get(index, False):
            skipped_count += 1
            print(f"\n--- ⏭️ SKIPPING ROW {index + 2}: Asset {asset_no} (Pre-Validation Error) ---")
            continue

        print(f"\n--- ⚡ Processing row {index + 2}: Asset {asset_no} ---")

        try:
            driver.get("https://tpss.my.site.com/DealerPortal/s/")
            time.sleep(3)
        except:
            pass 

        try:
            found = search_asset(driver, asset_no)
            if not found:
                print(f"--- ⏭️ SKIPPING ROW {index + 2}: Asset {asset_no} (Not Found in Salesforce) ---")
                error_flags[index] = True 
                skipped_count += 1
                continue 

            edit_btn = driver.find_element(By.XPATH, "//button[@name='Edit'] | //button[text()='Edit']")
            driver.execute_script("arguments[0].click();", edit_btn)
            time.sleep(5)

            cust_name = str(row.get('Customer Name', '')).strip()
            fill_text_field(driver, "Asset Name", cust_name, clear_first=True)

            fill_text_field(driver, "I & C Date", format_date(row.get('Date of Release', '')))
            fill_text_field(driver, "Installation Date", format_date(row.get('Date of Installation', '')))

            select_dropdown(driver, "Existing Opportunity available", "No", wait_for_manual=True)
            select_dropdown(driver, "Roof type", "CP Supplied –Customized Elevated Structure")
            select_dropdown(driver, "PM Surya Ghar Yojana", "Yes", is_optional=True)
            select_dropdown(driver, "Region", "West")
            select_dropdown(driver, "TPSSL Scope", "Supply without structure")

            fill_text_field(driver, "District", "Nashik")
            fill_text_field(driver, "Street Details", row.get('Address', ''))

            pincode = str(row.get('Pincode', '')).split('.')[0]
            fill_text_field(driver, "Pincode", pincode, clear_first=True)

            select_dropdown(driver, "Type of Installation", "Roof Top-Grid Tied")

            mobile_raw = str(row.get('Contact Mobile', '')).split('.')[0]
            fill_text_field(driver, "Contact Mobile", mobile_raw)

            fill_text_field(driver, "Contact Name", cust_name)
            fill_text_field(driver, "Asset Email", row.get('Asset Email', ''))

            save_btn = driver.find_element(By.XPATH, "//button[@name='SaveEdit'] | //button[text()='Save']")
            driver.execute_script("arguments[0].click();", save_btn)

            WebDriverWait(driver, 15).until(EC.invisibility_of_element_located((By.CLASS_NAME, "modal-container")))
            print(" [✓] Saved Successfully.")
            processed_count += 1

        except Exception as e:
            print(f"\n🛑 [ERROR] Failed processing Asset {asset_no}. Skipping to next.")
            print(f"Error details: {e}")
            error_flags[index] = True 
            skipped_count += 1
            continue

    print("\n=== RUN COMPLETE ===")
    print(f"Total rows skipped due to errors (Data validation, Not Found, or Glitches): {skipped_count}")
    print(f"Total rows processed successfully: {processed_count}")
    
    print("\nGenerating final Excel file with all errors highlighted...")
    highlight_errors_and_save(df, error_flags)


def main():
    driver = setup_driver()
    login(driver)
    process_records(driver)
    print("\nAll tasks completed.")
    driver.quit()


if __name__ == "__main__":
    main()