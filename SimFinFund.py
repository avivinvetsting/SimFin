# SimFinFund.py (עם שימוש ב-DataFrame מה-session לגרפים)
import simfin as sf
import pandas as pd
import os
from flask import Flask, render_template, request, url_for, redirect, flash, session
import plotly.express as px
import plotly.graph_objects as go

# --- ייבוא פונקציית ההורדה ---
from downloader import download_financial_statements 

# --- הגדרות API (כמו קודם) ---
API_KEY_FILE = 'simfin_api_key.txt'
def load_simfin_api_key():
    # ... (כמו קודם) ...
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
app.config['SECRET_KEY'] = 'your_very_secret_key_for_flask_sessions_CHANGE_ME_PLEASE_AGAIN_AND_AGAIN' 

print("SimFinFund.py: Application starting. Data will be fetched on user request via ticker input.")





# --- פונקציית עזר ליצירת גרפים (כמו קודם, עם שיפור קטן) ---
def create_timeseries_chart(df, y_column, title, x_column_name_in_df=None, y_axis_title=None, chart_type='bar'):
    print(f"\n--- Attempting to create chart: '{title}' ---")
    print(f"Input DataFrame for '{title}' (head):")
    if df is None:
        print("DataFrame is None.")
        return f"<p class='text-warning'>Chart '{title}': Input DataFrame is None.</p>"
    if df.empty:
        print("DataFrame is empty.")
        return f"<p class='text-warning'>Chart '{title}': Input DataFrame is empty.</p>"
    
    print(df.head(3)) # הדפס רק 3 שורות ראשונות
    print(f"Index type for '{title}': {type(df.index)}")
    if isinstance(df.index, pd.DatetimeIndex):
        print(f"Index is DatetimeIndex. Is sorted: {df.index.is_monotonic_increasing or df.index.is_monotonic_decreasing}")

    # אם האינדקס הוא התאריכים
    x_data = None
    x_label = None

    if x_column_name_in_df is None: 
        x_data = df.index
        x_label = df.index.name if df.index.name else 'Date'
        # ודא שהאינדקס הוא DatetimeIndex וממוין
        if not isinstance(df.index, pd.DatetimeIndex):
            print(f"Chart '{title}': Index is not DatetimeIndex, attempting conversion...")
            try:
                df_temp_for_chart = df.copy()
                df_temp_for_chart.index = pd.to_datetime(df_temp_for_chart.index, errors='coerce')
                df_temp_for_chart = df_temp_for_chart[df_temp_for_chart.index.notna()]
                if not df_temp_for_chart.empty:
                    df_temp_for_chart = df_temp_for_chart.sort_index()
                    x_data = df_temp_for_chart.index
                    df = df_temp_for_chart # עדכן את df לזה עם האינדקס המתוקן
                    print(f"Chart '{title}': Index converted to DatetimeIndex and sorted.")
                else:
                    print(f"Chart '{title}': Index conversion failed or resulted in empty data. Using original index as string.")
                    x_data = df.index.astype(str) # התייחס לאינדקס כמחרוזת אם ההמרה נכשלה
            except Exception as e:
                print(f"Chart '{title}': Error converting index to datetime: {e}. Using original index as string.")
                x_data = df.index.astype(str)
        elif not (df.index.is_monotonic_increasing or df.index.is_monotonic_decreasing):
            print(f"Chart '{title}': DatetimeIndex is not sorted. Sorting...")
            df = df.sort_index() # מיין אם הוא כבר DatetimeIndex אבל לא ממוין
            x_data = df.index
            
    else: # שימוש בעמודה כשציר X
        if x_column_name_in_df not in df.columns:
            print(f"Chart '{title}': X-axis column '{x_column_name_in_df}' not in DataFrame.")
            return f"<p class='text-danger'>Error: X-axis column '{x_column_name_in_df}' not found for chart '{title}'.</p>"
        x_data = df[x_column_name_in_df]
        x_label = x_column_name_in_df
        if pd.api.types.is_datetime64_any_dtype(df[x_column_name_in_df]):
             df = df.sort_values(by=x_column_name_in_df)
             x_data = df[x_column_name_in_df]

    if y_column not in df.columns:
        print(f"Chart '{title}': Y-axis column '{y_column}' not in DataFrame. Available columns: {df.columns.tolist()}")
        return f"<p class='text-danger'>Error: Column '{y_column}' not found for chart '{title}'.</p>"

    # הדפס את הנתונים הספציפיים שייכנסו לגרף
    print(f"Data for Y-axis '{y_column}' in chart '{title}' (first 5 values):")
    print(df[y_column].head().to_string())
    print(f"Data type of Y-axis '{y_column}': {df[y_column].dtype}")


    try:
        df_for_chart = df.copy()
        # נסה להמיר את עמודת ה-Y למספר, גם אם היא כבר אמורה להיות מספרית, כדי לוודא
        df_for_chart[y_column] = pd.to_numeric(df_for_chart[y_column], errors='coerce')
        # הסר שורות שבהן ערך ה-Y הוא NaN לאחר ההמרה
        df_cleaned = df_for_chart.dropna(subset=[y_column])
        
        if df_cleaned.empty:
            print(f"Chart '{title}': DataFrame became empty after coercing/dropping NaNs for y-column '{y_column}'.")
            return f"<p class='text-info'>No valid numeric data to display for '{y_column}' in chart '{title}'.</p>"
    except Exception as e:
        print(f"Chart '{title}': Error converting y-column '{y_column}' to numeric: {e}")
        return f"<p class='text-danger'>Error processing numeric data for chart '{title}'.</p>"

    print(f"Chart '{title}': Successfully prepared data for plotting. X data type: {type(x_data)}, Y data (cleaned) head:")
    print(df_cleaned[[y_column]].head())


    try:
        if chart_type == 'bar':
            fig = px.bar(df_cleaned, x=x_data, y=y_column, title=title,
                           labels={y_column: y_axis_title if y_axis_title else y_column, x_label: x_label})
        elif chart_type == 'line':
            fig = px.line(df_cleaned, x=x_data, y=y_column, title=title,
                            labels={y_column: y_axis_title if y_axis_title else y_column, x_label: x_label}, markers=True)
        else: 
            print(f"Chart '{title}': Unsupported chart type: {chart_type}")
            return None
        
        fig.update_layout(yaxis_title=y_axis_title if y_axis_title else y_column, xaxis_title=x_label,
                          yaxis_tickformat=',.0f', height=450, margin=dict(l=20, r=20, t=50, b=20))
        
        # אם ציר ה-X הוא תאריכי, נסה לפרמט אותו
        if isinstance(x_data, pd.DatetimeIndex) or pd.api.types.is_datetime64_any_dtype(x_data):
             fig.update_xaxes(tickformat='%Y-%m-%d', type='category') # 'category' יכול לעזור עם תאריכים לא רציפים או אם יש מעט נקודות
        
        print(f"Chart '{title}': Plotly figure created successfully.")
        
        #------------------------------------------------------------------------------
        #--------------------------------------------------------------------------------
        # ... בתוך create_timeseries_chart, לפני return fig.to_html ...
        graph_html_output = fig.to_html(full_html=False, include_plotlyjs=False)
        print(f"\n--- Plotly HTML for chart '{title}' ---")
        print(graph_html_output)
        print(f"--- End Plotly HTML for chart '{title}' ---\n")
        return graph_html_output
        #---------------------------------------------------------------------------------
        #--------------------------------------------------------------------------------
        
        
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    except Exception as e:
        print(f"Chart '{title}': Error creating Plotly figure: {e}")
        import traceback
        traceback.print_exc() # הדפסת Traceback מלא של השגיאה מ-Plotly
        return f"<p class='text-danger'>Error generating chart '{title}'. Details: {e}</p>"

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
            # מנקה נתונים ישנים מה-session לפני טעינת חדשים
            session.pop('income_annual_df', None)
            session.pop('income_quarterly_df', None)
            # (אפשר להוסיף גם למאזן ותזרים אם נשתמש בהם ישירות לגרפים)

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
                        # שמירת ה-DataFrame ל-CSV (טוב לגיבוי ולבדיקה ידנית)
                        file_statement_name = human_readable_names_for_file[stmt_key]
                        file_name = f"{ticker}_{file_statement_name}_{variant}.csv"
                        ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, ticker)
                        os.makedirs(ticker_save_dir, exist_ok=True)
                        save_path = os.path.join(ticker_save_dir, file_name)
                        try:
                            if isinstance(data_item.index, pd.DatetimeIndex):
                                data_item.index.name = data_item.index.name or 'Report Date'
                            data_item.to_csv(save_path, index=True)
                            session_data_status[result_key] = f"Saved: {os.path.basename(save_path)}"
                            any_success = True
                            print(f"SimFinFund.py: Saved {result_key} to {save_path}")

                            # !!! שמירת ה-DataFrame ב-session !!!
                            # נשמור רק את דוחות ההכנסה כרגע, כי רק אותם אנו צריכים לגרפים שהוגדרו
                            if stmt_key == 'income':
                                # ה-DataFrame נשמר כ-JSON כי אובייקטים מורכבים לא נשמרים ישירות ב-session
                                session[f'{result_key}_df_json'] = data_item.to_json(orient='split', date_format='iso')
                                print(f"SimFinFund.py: Stored {result_key}_df_json in session.")
                        except Exception as e:
                            session_data_status[result_key] = f"Error saving CSV/session for {result_key}: {e}"
                            print(f"SimFinFund.py: Error saving CSV/session for {result_key}: {e}")
                    elif isinstance(data_item, dict) and "Error" in data_item:
                        session_data_status[result_key] = f"Error downloading {result_key}: {data_item['Details']}"
                    else: 
                        session_data_status[result_key] = f"No data or unexpected format for {result_key}."
            
            session['data_download_status'] = session_data_status

            if any_success:
                flash(f"נתונים עבור {ticker} הורדו (או נוסו להורדה).", "success")
            else:
                flash(f"הורדת הנתונים עבור {ticker} נכשלה. בדוק לוגים והודעות סטטוס.", "danger")
            
            return redirect(url_for('route_graphs_annual')) 
        else:
            flash("לא הוזן טיקר.", "warning")
    return redirect(url_for('route_home'))

def get_dataframe_from_session_or_csv(ticker, variant, statement_key):
    """
    Tries to load DataFrame from session. If not found, tries from CSV.
    """
    session_key = f"{statement_key}_{variant}_df_json"
    df = None
    error_message = None
    info_message = None

    # נסה לטעון מה-session
    if session_key in session:
        try:
            df_json = session[session_key]
            df = pd.read_json(df_json, orient='split', convert_dates=['index']) # המרת אינדקס התאריכים
            df = df.sort_index()
            if not df.empty:
                info_message = f"Data for {statement_key} ({variant}) loaded from session."
                print(f"SimFinFund.py: Loaded {session_key} from session.")
            else:
                info_message = f"Data for {statement_key} ({variant}) from session is empty."
                df = None # התייחס כאל לא נטען
        except Exception as e:
            error_message = f"Error loading {statement_key} ({variant}) from session: {e}. Will try CSV."
            print(f"SimFinFund.py: {error_message}")
            session.pop(session_key, None) # הסר מה-session אם הוא פגום

    # אם לא הצליח מה-session, נסה לטעון מה-CSV
    if df is None: # או אם df התקבל ריק מהסשן
        file_path = get_statement_file_path(ticker, statement_key, variant)
        print(f"SimFinFund.py: Attempting to load {statement_key} ({variant}) from CSV: {file_path}")
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0)
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, errors='coerce')
                    df = df[df.index.notna()].sort_index()
                
                if not df.empty:
                    info_message = info_message or f"Data for {statement_key} ({variant}) loaded from CSV: {os.path.basename(file_path)}"
                    # אופציונלי: טען מחדש ל-session לשימוש עתידי בבקשות אחרות
                    session[session_key] = df.to_json(orient='split', date_format='iso')
                else:
                    info_message = info_message or f"CSV file ({os.path.basename(file_path)}) for {statement_key} ({variant}) is empty."
                    df = None
            except Exception as e:
                error_message = (error_message or "") + f" Error reading CSV {file_path}: {e}"
        elif not error_message: # אם הקובץ לא קיים ואין שגיאה קודמת מהסשן
             error_message = f"CSV file for {statement_key} ({variant}) not found for ticker {ticker}."
             download_status = session.get('data_download_status', {}).get(f"{statement_key}_{variant}")
             if download_status: error_message += f" (Download status: {download_status})"
    
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
    
    # !!! טעינת DataFrame מדוח הכנסות שנתי מה-session או מ-CSV !!!
    df_income, error_msg_data, info_msg_data = get_dataframe_from_session_or_csv(current_ticker, 'annual', 'income')
    
    print(f"--- Data for Annual Graphs (Ticker: {current_ticker}) ---")
    if df_income is not None:
        print("Annual Income Statement DataFrame (head for graph):")
        print(df_income.head())
        print(f"Columns available: {df_income.columns.tolist()}")
        print(f"Index type: {type(df_income.index)}")
    else:
        print(f"Annual Income Statement DataFrame is None. Error: {error_msg_data}, Info: {info_msg_data}")
    print("----------------------------------------------------")

    graph_revenue_html = None
    graph_net_income_html = None
    
    if df_income is not None and not df_income.empty:
        # נשתמש ב-'Net Income (Common)' אם קיים, אחרת ננסה 'Net Income'
        net_income_col_name = 'Net Income (Common)' 
        revenue_col_name = 'Revenue'

        graph_revenue_html = create_timeseries_chart(df_income, 
                                                    y_column=revenue_col_name, 
                                                    title=f'הכנסות (Revenue) - שנתי',
                                                    y_axis_title='סכום', chart_type='bar')

        graph_net_income_html = create_timeseries_chart(df_income, 
                                                        y_column=net_income_col_name, 
                                                        title=f'רווח נקי ({net_income_col_name}) - שנתי',
                                                        y_axis_title='סכום', chart_type='bar')
    elif not error_msg_data and not info_msg_data : 
        error_msg_data = "לא נטענו נתוני דוח הכנסות להצגת גרפים."
        
    return render_template('base_layout.html', 
                           page_title=page_title, current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Annual',
                           graph_revenue_html=graph_revenue_html, graph_net_income_html=graph_net_income_html,
                           data_error_message=error_msg_data, data_info_message=info_msg_data,   
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
    
    # !!! טעינת DataFrame מדוח הכנסות רבעוני מה-session או מ-CSV !!!
    df_income_q, error_msg_data_q, info_msg_data_q = get_dataframe_from_session_or_csv(current_ticker, 'quarterly', 'income')

    print(f"--- Data for Quarterly Graphs (Ticker: {current_ticker}) ---")
    if df_income_q is not None:
        print("Quarterly Income Statement DataFrame (head for graph):")
        print(df_income_q.head())
        print(f"Columns available: {df_income_q.columns.tolist()}")
        print(f"Index type: {type(df_income_q.index)}")
    else:
        print(f"Quarterly Income Statement DataFrame is None. Error: {error_msg_data_q}, Info: {info_msg_data_q}")
    print("----------------------------------------------------")

    graph_revenue_html_q = None
    graph_net_income_html_q = None

    if df_income_q is not None and not df_income_q.empty:
        net_income_col_name = 'Net Income (Common)' if 'Net Income (Common)' in df_income_q.columns else 'Net Income'
        revenue_col_name = 'Revenue'
        
        graph_revenue_html_q = create_timeseries_chart(df_income_q, 
                                                      y_column=revenue_col_name, 
                                                      title=f'הכנסות (Revenue) - רבעוני',
                                                      y_axis_title='סכום', chart_type='bar')

        graph_net_income_html_q = create_timeseries_chart(df_income_q, 
                                                         y_column=net_income_col_name, 
                                                         title=f'רווח נקי ({net_income_col_name}) - רבעוני',
                                                         y_axis_title='סכום', chart_type='bar')
    elif not error_msg_data_q and not info_msg_data_q:
        error_msg_data_q = "לא נטענו נתוני דוח הכנסות להצגת גרפים."
        
    return render_template('base_layout.html', 
                           page_title=page_title, current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Quarterly',
                           graph_revenue_html=graph_revenue_html_q, graph_net_income_html=graph_net_income_html_q,  
                           data_error_message=error_msg_data_q, data_info_message=info_msg_data_q,
                           api_key_status_display=api_key_status)

# ... (route_valuations ו- route_update_api_key_action כמו קודם) ...
def get_api_key_status_for_display(): # ודא שהפונקציה הזו מוגדרת כראוי
    # ... (כמו קודם) ...
    if os.path.exists(API_KEY_FILE) and os.path.getsize(API_KEY_FILE) > 0:
        with open(API_KEY_FILE, 'r') as f:
            key_in_file = f.read().strip()
        if key_in_file.lower() == 'free':
             return "משתמש במפתח 'free' מהקובץ."
        else:
             return "מפתח API מותאם אישית נטען מהקובץ."
    else:
        return "קובץ מפתח לא קיים או ריק, משתמש ב-'free' כברירת מחדל."

@app.route('/valuations') # ודא שכל ה-routes מוגדרים
def route_valuations():
    current_ticker = session.get('current_ticker', None)
    api_key_status = get_api_key_status_for_display()
    return render_template('base_layout.html', 
                           page_title='הערכות שווי',
                           current_ticker=current_ticker,
                           content_template='content_valuations.html',
                           api_key_status_display=api_key_status)

@app.route('/update_api_key_action', methods=['POST'])
def route_update_api_key_action():
    # ... (כמו קודם) ...
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
            session['api_key_status_display'] = f"שגיאה בעדכון: {e}" 
            flash(f'שגיאה בעדכון מפתח API: {e}', 'danger')
            print(f"SimFinFund.py: Error updating API key: {e}")
        
        return redirect(request.referrer or url_for('route_home'))
    return redirect(url_for('route_home'))


if __name__ == '__main__':
    app.run(debug=True)