# SimFinFund.py (גרסה מלאה עם תיקון set_data_dir)
import simfin as sf
import pandas as pd
import os
from flask import Flask, render_template, url_for

# --- ייבוא פונקציית ההורדה ---
from Downloader import download_all_statements_for_ticker # ודא ששם הקובץ הוא downloader.py

# --- הגדרות קבועות ---
TARGET_TICKER = 'amzn'
TARGET_VARIANT = 'quarterly'
TARGET_MARKET = 'us'

# --- הגדרות API וספריות ---
API_KEY_FILE = 'simfin_api_key.txt'

def load_simfin_api_key():
    api_key = 'free'
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, 'r') as f:
                read_key = f.read().strip()
            if read_key:
                api_key = read_key
                print("SimFinFund.py: API key loaded from file.")
            else:
                print(f"SimFinFund.py: API key file is empty. Using 'free'.")
        except IOError:
            print(f"SimFinFund.py: Could not read API key file. Using 'free'.")
    else:
        print(f"SimFinFund.py: API key file not found. Using 'free'.")
    return api_key

api_key_to_set = load_simfin_api_key()
sf.set_api_key(api_key_to_set)

# --- הגדרת תיקיית המטמון של SimFin ---
simfin_data_directory = os.path.join(os.path.expanduser('~'), 'simfin_data')
os.makedirs(simfin_data_directory, exist_ok=True) 
sf.set_data_dir(simfin_data_directory)
print(f"SimFinFund.py: SimFin data directory set to: {simfin_data_directory}")

script_dir = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DATA_BASE_DIR = os.path.join(script_dir, 'Data')
os.makedirs(PROCESSED_DATA_BASE_DIR, exist_ok=True)
print(f"SimFinFund.py: Processed CSVs will be saved to: {PROCESSED_DATA_BASE_DIR}")

app = Flask(__name__)

# --- גלובלי לאחסון נתיבי קבצים או שגיאות ---
SAVED_FILE_PATHS = {
    'income': None,
    'balance': None,
    'cashflow': None
}
DOWNLOAD_ERRORS = {
    'income': None,
    'balance': None,
    'cashflow': None
}

def initialize_data():
    """Downloads data on startup and saves CSVs."""
    print(f"\nSimFinFund.py: --- Initializing data for {TARGET_TICKER} ---")
    
    all_statements_data = download_all_statements_for_ticker(
        ticker_symbol=TARGET_TICKER,
        variant=TARGET_VARIANT,
        market=TARGET_MARKET
    )

    statement_keys = ['income', 'balance', 'cashflow']
    human_readable_names = {
        'income': 'Income_Statement',
        'balance': 'Balance_Sheet',
        'cashflow': 'Cash_Flow_Statement'
    }

    for key in statement_keys:
        data_item = all_statements_data.get(key)
        if isinstance(data_item, pd.DataFrame) and not data_item.empty: # ודא שה-DataFrame לא ריק לפני שמירה
            file_statement_name = human_readable_names[key]
            file_name = f"{TARGET_TICKER}_{file_statement_name}_{TARGET_VARIANT}.csv"
            ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, TARGET_TICKER)
            os.makedirs(ticker_save_dir, exist_ok=True)
            save_path = os.path.join(ticker_save_dir, file_name)
            try:
                data_item.to_csv(save_path, index=True)
                SAVED_FILE_PATHS[key] = save_path
                DOWNLOAD_ERRORS[key] = None # נקה שגיאה קודמת אם הייתה
                print(f"SimFinFund.py: Saved {key} data to {save_path}")
            except Exception as e:
                DOWNLOAD_ERRORS[key] = f"Error saving {key} CSV: {e}"
                SAVED_FILE_PATHS[key] = None
                print(f"SimFinFund.py: {DOWNLOAD_ERRORS[key]}")
        elif isinstance(data_item, pd.DataFrame) and data_item.empty: # DataFrame ריק (לא נמצאו נתונים)
            DOWNLOAD_ERRORS[key] = f"No data found for {key} statement of {TARGET_TICKER} (empty DataFrame)."
            SAVED_FILE_PATHS[key] = None # אל תשמור קובץ ריק, תן לשגיאה להופיע
            print(f"SimFinFund.py: {DOWNLOAD_ERRORS[key]}")
        elif isinstance(data_item, dict) and "Error" in data_item:
            DOWNLOAD_ERRORS[key] = data_item.get("Details", "Unknown error from downloader.")
            SAVED_FILE_PATHS[key] = None
            print(f"SimFinFund.py: Error fetching {key} data: {DOWNLOAD_ERRORS[key]}")
        else: # מקרה לא צפוי
            DOWNLOAD_ERRORS[key] = f"Unexpected data type or no data returned for {key}."
            SAVED_FILE_PATHS[key] = None
            print(f"SimFinFund.py: {DOWNLOAD_ERRORS[key]}")

    print(f"SimFinFund.py: --- Data initialization complete ---")
    print(f"SimFinFund.py: Saved file paths: {SAVED_FILE_PATHS}")
    print(f"SimFinFund.py: Download errors: {DOWNLOAD_ERRORS}")

initialize_data()

# --- Flask Routes ---
@app.route('/')
def route_index():
    return render_template('index.html', ticker=TARGET_TICKER, variant=TARGET_VARIANT)

def render_statement_page(statement_key, page_title):
    file_path = SAVED_FILE_PATHS.get(statement_key)
    error_from_init = DOWNLOAD_ERRORS.get(statement_key) # שגיאה משלב ההורדה הראשונית
    
    data_html = None
    current_error_message = error_from_init # השתמש בשגיאה מההורדה כברירת מחדל
    current_info_message = None

    print(f"SimFinFund.py: Request for {page_title}. Expected file path: {file_path}, Initial error: {error_from_init}")

    if file_path and os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, index_col=0)
            if not df.empty:
                data_html = df.to_html(classes='table table-striped table-hover table-sm', border=0, index=True)
                current_error_message = None # אם הצלחנו לטעון, אין שגיאה להציג מהקריאה
                current_info_message = f"Data loaded from: {os.path.basename(file_path)}"
            else: # הקובץ קיים אך ריק
                current_info_message = f"The data file ({os.path.basename(file_path)}) was found but is empty. No data was available from SimFin during initialization."
                current_error_message = None # זו אינפורמציה, לא שגיאת קריאה
        except Exception as e:
            current_error_message = f"Error reading or processing CSV file {file_path}: {e}"
            print(f"SimFinFund.py: {current_error_message}")
            data_html = None # ודא שאין HTML אם יש שגיאת קריאה
    elif not file_path and not error_from_init: # אין קובץ וגם לא נרשמה שגיאה בהורדה - לא סביר
         current_info_message = f"Data file path for {page_title.lower()} was not recorded and no download error was noted."
    # אם file_path הוא None אבל error_from_init קיים, השגיאה הזו תוצג

    return render_template('statement_page.html',
                           ticker=TARGET_TICKER,
                           variant=TARGET_VARIANT,
                           statement_name=page_title,
                           data_html=data_html,
                           info_message=current_info_message,
                           error_message=current_error_message)

@app.route('/income')
def route_income():
    return render_statement_page('income', 'Income Statement')

@app.route('/balance')
def route_balance():
    return render_statement_page('balance', 'Balance Sheet')

@app.route('/cashflow')
def route_cashflow():
    return render_statement_page('cashflow', 'Cash Flow Statement')

if __name__ == '__main__':
    app.run(debug=True)