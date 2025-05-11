# SimFinFund.py
import simfin as sf
import pandas as pd
import os
from flask import Flask, render_template, request, url_for, redirect, flash, session

# --- ייבוא פונקציית ההורדה ---
from downloader import download_financial_statements 

# --- הגדרות API ---
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

simfin_data_directory = os.path.join(os.path.expanduser('~'), 'simfin_data')
os.makedirs(simfin_data_directory, exist_ok=True) 
sf.set_data_dir(simfin_data_directory)
print(f"SimFinFund.py: SimFin data directory set to: {simfin_data_directory}")

script_dir = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DATA_BASE_DIR = os.path.join(script_dir, 'Data')
os.makedirs(PROCESSED_DATA_BASE_DIR, exist_ok=True)
print(f"SimFinFund.py: Processed CSVs will be saved to: {PROCESSED_DATA_BASE_DIR}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_for_flask_sessions_CHANGE_ME_PLEASE' 

print("SimFinFund.py: Application starting. Data will be fetched on user request via ticker input.")

def get_statement_file_path(ticker, statement_type_key, variant):
    """Constructs the expected path for a statement's CSV file."""
    human_readable_names = {
        'income': 'Income_Statement',
        'balance': 'Balance_Sheet',
        'cashflow': 'Cash_Flow_Statement'
    }
    file_statement_name = human_readable_names.get(statement_type_key, f"Unknown_{statement_type_key}")
    file_name = f"{ticker}_{file_statement_name}_{variant}.csv"
    ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, ticker)
    return os.path.join(ticker_save_dir, file_name)

# --- Flask Routes ---
@app.route('/')
def route_home():
    current_ticker = session.get('current_ticker', '')
    api_key_status = get_api_key_status_for_display()
    return render_template('base_layout.html', 
                           page_title='ברוכים הבאים', 
                           current_ticker=current_ticker,
                           content_template='content_home.html',
                           api_key_status_display=api_key_status)

@app.route('/set_ticker', methods=['POST'])
def route_set_ticker():
    if request.method == 'POST':
        ticker = request.form.get('ticker_input', '').upper()
        if ticker:
            session['current_ticker'] = ticker
            print(f"SimFinFund.py: Ticker set to {ticker}. Attempting to download financial data...")
            
            download_results = download_financial_statements(ticker_symbol=ticker)
            
            session_data_status = {} 
            any_success = False

            variants_to_process = ['annual', 'quarterly']
            statement_keys_to_process = ['income', 'balance', 'cashflow']
            human_readable_names_for_file = {
                'income': 'Income_Statement', 
                'balance': 'Balance_Sheet', 
                'cashflow': 'Cash_Flow_Statement'
            }

            for variant in variants_to_process:
                for stmt_key in statement_keys_to_process:
                    result_key = f"{stmt_key}_{variant}"
                    data_item = download_results.get(result_key)
                    
                    if isinstance(data_item, pd.DataFrame) and not data_item.empty:
                        file_statement_name = human_readable_names_for_file[stmt_key]
                        file_name = f"{ticker}_{file_statement_name}_{variant}.csv"
                        ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, ticker)
                        os.makedirs(ticker_save_dir, exist_ok=True)
                        save_path = os.path.join(ticker_save_dir, file_name)
                        try:
                            data_item.to_csv(save_path, index=True)
                            session_data_status[result_key] = f"Saved: {os.path.basename(save_path)}"
                            any_success = True
                            print(f"SimFinFund.py: Saved {result_key} to {save_path}")
                        except Exception as e:
                            session_data_status[result_key] = f"Error saving CSV for {result_key}: {e}"
                            print(f"SimFinFund.py: Error saving CSV for {result_key}: {e}")
                    elif isinstance(data_item, dict) and "Error" in data_item:
                        session_data_status[result_key] = f"Error downloading {result_key}: {data_item['Details']}"
                        print(f"SimFinFund.py: {session_data_status[result_key]}")
                    else: 
                        session_data_status[result_key] = f"No data or unexpected format for {result_key}."
                        print(f"SimFinFund.py: {session_data_status[result_key]}")
            
            session['data_download_status'] = session_data_status

            if any_success:
                flash(f"נתונים עבור {ticker} הורדו ונשמרו (או נוסו להורדה).", "success")
            else:
                flash(f"הורדת הנתונים עבור {ticker} נכשלה. בדוק את הלוגים בשרת והודעות סטטוס.", "danger")
            
            return redirect(url_for('route_graphs_annual')) 
        else:
            flash("לא הוזן טיקר.", "warning")
    return redirect(url_for('route_home'))

def get_data_for_page(current_ticker, variant, statement_key_for_data):
    """Helper to load data for display pages from CSV."""
    file_path = get_statement_file_path(current_ticker, statement_key_for_data, variant)
    df = None
    error_message = None
    info_message = None
    
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, index_col=0) 
            if df.empty:
                info_message = f"קובץ הנתונים ({os.path.basename(file_path)}) נמצא אך הוא ריק."
                df = None 
        except Exception as e:
            error_message = f"שגיאה בקריאת קובץ נתונים ({os.path.basename(file_path)}): {e}"
    else:
        error_message = f"קובץ נתונים ({os.path.basename(file_path)}) עבור {current_ticker} ({variant}) לא נמצא. "
        error_message += "אנא בצע 'בחר מניה והמשך' כדי להוריד נתונים."
        download_status = session.get('data_download_status', {}).get(f"{statement_key_for_data}_{variant}")
        if download_status:
            error_message += f" (סטטוס הורדה: {download_status})"
            
    return df, error_message, info_message

@app.route('/graphs/annual')
def route_graphs_annual():
    current_ticker = session.get('current_ticker', None)
    api_key_status = get_api_key_status_for_display()
    page_title = 'גרפים שנתיים'
    if not current_ticker:
        flash("אנא בחר טיקר תחילה.", "warning")
        return redirect(url_for('route_home'))
    
    page_title = f'גרפים שנתיים עבור {current_ticker}'
    df_income, error_msg, info_msg = get_data_for_page(current_ticker, 'annual', 'income')

    graph_html_content = "<h4>נתוני דוח הכנסות (שנתי) - דוגמה:</h4>"
    if error_msg:
        graph_html_content = f"<p class='text-danger'>{error_msg}</p>"
    elif info_msg:
         graph_html_content = f"<p class='text-info'>{info_msg}</p>"
    elif df_income is not None:
        graph_html_content += f"<p>סה\"כ רשומות בדוח הכנסות שנתי: {len(df_income)}</p>"
        # כאן תוסיף לוגיקה ליצירת גרפים עם Plotly/Matplotlib מ-df_income
        graph_html_content += "<p><i>(בקרוב: גרף הכנסות ורווח נקי)</i></p>"
        graph_html_content += df_income.tail(3).to_html(classes='table table-sm table-bordered', border=0, index=True) # הצגת 3 שורות אחרונות
    else:
        graph_html_content += "<p>לא נטענו נתוני דוח הכנסות להצגת גרפים.</p>"
        
    return render_template('base_layout.html', 
                           page_title=page_title,
                           current_ticker=current_ticker,
                           content_template='content_graphs.html',
                           graph_type='Annual',
                           graph_content_for_template = graph_html_content,
                           api_key_status_display=api_key_status)

@app.route('/graphs/quarterly')
def route_graphs_quarterly():
    current_ticker = session.get('current_ticker', None)
    api_key_status = get_api_key_status_for_display()
    page_title = 'גרפים רבעוניים'
    if not current_ticker:
        flash("אנא בחר טיקר תחילה.", "warning")
        return redirect(url_for('route_home'))

    page_title = f'גרפים רבעוניים עבור {current_ticker}'
    df_income_q, error_msg_q, info_msg_q = get_data_for_page(current_ticker, 'quarterly', 'income')
    
    graph_html_content = "<h4>נתוני דוח הכנסות (רבעוני) - דוגמה:</h4>"
    if error_msg_q:
        graph_html_content = f"<p class='text-danger'>{error_msg_q}</p>"
    elif info_msg_q:
        graph_html_content = f"<p class='text-info'>{info_msg_q}</p>"
    elif df_income_q is not None:
        graph_html_content += f"<p>סה\"כ רשומות בדוח הכנסות רבעוני: {len(df_income_q)}</p>"
        graph_html_content += "<p><i>(בקרוב: גרף הכנסות ורווח נקי)</i></p>"
        graph_html_content += df_income_q.tail(3).to_html(classes='table table-sm table-bordered', border=0, index=True)
    else:
        graph_html_content += "<p>לא נטענו נתוני דוח הכנסות להצגת גרפים.</p>"
        
    return render_template('base_layout.html', 
                           page_title=page_title,
                           current_ticker=current_ticker,
                           content_template='content_graphs.html',
                           graph_type='Quarterly',
                           graph_content_for_template = graph_html_content,
                           api_key_status_display=api_key_status)

@app.route('/valuations')
def route_valuations():
    current_ticker = session.get('current_ticker', None)
    api_key_status = get_api_key_status_for_display()
    return render_template('base_layout.html', 
                           page_title='הערכות שווי',
                           current_ticker=current_ticker,
                           content_template='content_valuations.html',
                           api_key_status_display=api_key_status)

def get_api_key_status_for_display():
    """Helper function to get the API key status string for display."""
    if os.path.exists(API_KEY_FILE) and os.path.getsize(API_KEY_FILE) > 0:
        with open(API_KEY_FILE, 'r') as f:
            key_in_file = f.read().strip()
        if key_in_file.lower() == 'free':
            return "משתמש במפתח 'free' מהקובץ."
        else:
            return "מפתח API מותאם אישית נטען מהקובץ."
    else:
        return "קובץ מפתח לא קיים או ריק, משתמש ב-'free' כברירת מחדל."

@app.route('/update_api_key_action', methods=['POST']) # שינוי שם ה-route למניעת התנגשות
def route_update_api_key_action():
    if request.method == 'POST':
        new_api_key = request.form.get('api_key_input_modal', '').strip()
        try:
            if new_api_key:
                with open(API_KEY_FILE, 'w') as f:
                    f.write(new_api_key)
                sf.set_api_key(new_api_key) 
                session['api_key_status_display'] = get_api_key_status_for_display()
                flash('מפתח API עודכן בהצלחה!', 'success')
                print(f"SimFinFund.py: API key updated in {API_KEY_FILE}")
            else:
                if os.path.exists(API_KEY_FILE):
                    try: 
                        os.remove(API_KEY_FILE)
                        print(f"SimFinFund.py: API key file {API_KEY_FILE} removed.")
                    except Exception as e_rem:
                        print(f"SimFinFund.py: Could not remove API key file {API_KEY_FILE}: {e_rem}")
                sf.set_api_key('free') 
                session['api_key_status_display'] = get_api_key_status_for_display()
                flash('מפתח API נמחק/נוקה. האפליקציה תשתמש כעת בנתוני "free".', 'info')
                print(f"SimFinFund.py: API key cleared. Using 'free' data.")
        except Exception as e:
            session['api_key_status_display'] = f"שגיאה בעדכון: {e}" # עדכון ה-session גם במקרה של שגיאה
            flash(f'שגיאה בעדכון מפתח API: {e}', 'danger')
            print(f"SimFinFund.py: Error updating API key: {e}")
        
        return redirect(request.referrer or url_for('route_home'))
    # GET requests to this URL are not expected.
    return redirect(url_for('route_home'))

if __name__ == '__main__':
    app.run(debug=True)