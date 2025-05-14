# SimFinFund.py
import simfin as sf
import pandas as pd
import os
import json
import yfinance as yf

from flask import Flask, render_template, request, url_for, redirect, flash, session
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils

from downloader import download_financial_statements, download_price_history_with_mavg

# --- הגדרות API ---
API_KEY_FILE = 'simfin_api_key.txt' # נשאר כפי שהוא, לניהול מפתח SimFin

def load_simfin_api_key():
    api_key = 'free'
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, 'r') as f:
                read_key = f.read().strip()
            if read_key:
                api_key = read_key
        except IOError:
            print(f"SimFinFund.py: Could not read API key file '{API_KEY_FILE}'. Using 'free'.")
    return api_key

api_key_to_set = load_simfin_api_key()
sf.set_api_key(api_key_to_set)

simfin_data_directory = os.path.join(os.path.expanduser('~'), 'simfin_data')
os.makedirs(simfin_data_directory, exist_ok=True)
sf.set_data_dir(simfin_data_directory)

script_dir = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DATA_BASE_DIR = os.path.join(script_dir, 'Data')
os.makedirs(PROCESSED_DATA_BASE_DIR, exist_ok=True)

app = Flask(__name__)

# --- טעינת SECRET_KEY מקובץ secrets.py ---
try:
    from secrets import FLASK_SECRET_KEY
    app.config['SECRET_KEY'] = FLASK_SECRET_KEY
except ImportError:
    # הדפס אזהרה רק בתהליך הראשי של שרת הפיתוח של Flask
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("-" * 80)
        print("אזהרה: קובץ secrets.py עם FLASK_SECRET_KEY לא נמצא.")
        print("משתמש במפתח ברירת מחדל המיועד לפיתוח בלבד (לא מאובטח).")
        print("בסביבת ייצור, חובה ליצור קובץ secrets.py עם מפתח אקראי וחזק,")
        print(f"ולהוסיף את secrets.py לקובץ .gitignore. הקובץ צריך להכיל: FLASK_SECRET_KEY = 'your_strong_random_key'")
        print("ניתן לייצר מפתח לדוגמה עם: python -c \"import os; print(os.urandom(24).hex())\"")
        print("-" * 80)
    app.config['SECRET_KEY'] = 'a_very_default_and_insecure_secret_key_CHANGE_THIS_IF_NO_SECRETS_FILE'
except AttributeError: # אם הקובץ קיים אבל המשתנה לא מוגדר בו
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("-" * 80)
        print("אזהרה: המשתנה FLASK_SECRET_KEY אינו מוגדר בקובץ secrets.py.")
        print("משתמש במפתח ברירת מחדל המיועד לפיתוח בלבד (לא מאובטח).")
        print("-" * 80)
    app.config['SECRET_KEY'] = 'another_default_and_insecure_secret_key_CHANGE_THIS'


# ... (שאר הקוד שלך, כולל פונקציות עזר, פונקציות גרפים, ונתיבים - ללא שינוי מהגרסה הקודמת שהצגתי, אלא אם יש תיקונים ספציפיים שנעשה בהמשך) ...
# (המשך הקוד מפה והלאה זהה לגרסה הקודמת שהצגתי לך, כולל כל התיקונים הקטנים והשיפורים שכבר עשינו בפונקציות הגרפים, טעינת הנתונים והנתיבים)


# --- פונקציות עזר ---
def get_statement_file_path(ticker, statement_type_key, variant):
    human_readable_names = {
        'income': 'Income_Statement', 'balance': 'Balance_Sheet', 'cashflow': 'Cash_Flow_Statement'
    }
    file_statement_name = human_readable_names.get(statement_type_key, f"Unknown_{statement_type_key}")
    file_name = f"{ticker}_{file_statement_name}_{variant}.csv"
    ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, ticker)
    return os.path.join(ticker_save_dir, file_name)

def get_api_key_status_for_display():
    # זו אותה פונקציה מהקוד הקודם
    if os.path.exists(API_KEY_FILE) and os.path.getsize(API_KEY_FILE) > 0:
        with open(API_KEY_FILE, 'r') as f:
            key_in_file = f.read().strip()
        return "מפתח API מותאם אישית נטען מהקובץ." if key_in_file.lower() != 'free' else "משתמש במפתח 'free' מהקובץ."
    return "קובץ מפתח לא קיים או ריק, משתמש ב-'free' כברירת מחדל."

# --- פונקציות ליצירת גרפים ---
# create_timeseries_chart - ללא שינוי מהגרסה הקודמת שהצגתי
def create_timeseries_chart(df, y_column, title, x_column_name_in_df=None, y_axis_title=None, chart_type='bar'):
    if df is None or df.empty:
        return {"error": f"No data available to create chart: {title} (DataFrame is None or empty)."}

    x_data = None
    x_label = None
    df_for_plotting = df.copy()

    if x_column_name_in_df is None:
        x_data = df_for_plotting.index
        x_label = df_for_plotting.index.name if df_for_plotting.index.name else 'Date'
        if not isinstance(df_for_plotting.index, pd.DatetimeIndex):
            try:
                df_for_plotting.index = pd.to_datetime(df_for_plotting.index, errors='coerce')
                df_for_plotting = df_for_plotting[df_for_plotting.index.notna()]
                if not df_for_plotting.empty:
                    df_for_plotting = df_for_plotting.sort_index()
                    x_data = df_for_plotting.index
                else:
                    x_data = df.index.astype(str)
                    df_for_plotting = df.copy()
            except Exception as e: 
                x_data = df.index.astype(str)
                df_for_plotting = df.copy() 
        elif not (df_for_plotting.index.is_monotonic_increasing or df_for_plotting.index.is_monotonic_decreasing): 
            df_for_plotting = df_for_plotting.sort_index()
            x_data = df_for_plotting.index 
    else:
        if x_column_name_in_df not in df_for_plotting.columns:
            return {"error": f"X-axis column '{x_column_name_in_df}' not found for chart '{title}'."}
        x_data = df_for_plotting[x_column_name_in_df] 
        x_label = x_column_name_in_df
        if pd.api.types.is_datetime64_any_dtype(df_for_plotting[x_column_name_in_df]):
             df_for_plotting = df_for_plotting.sort_values(by=x_column_name_in_df)
             x_data = df_for_plotting[x_column_name_in_df] 

    if y_column not in df_for_plotting.columns:
        return {"error": f"Column '{y_column}' not found for chart '{title}'. Available: {df_for_plotting.columns.tolist()}"}

    try:
        df_for_plotting[y_column] = pd.to_numeric(df_for_plotting[y_column], errors='coerce')
        df_cleaned = df_for_plotting.dropna(subset=[y_column]) 
        if df_cleaned.empty:
            return {"error": f"No valid numeric data to display for '{y_column}' in chart '{title}'."}
    except Exception as e:
        return {"error": f"Error processing numeric data for chart '{title}': {e}"}

    if x_column_name_in_df is None:
        final_x_data = df_cleaned.index
    else:
        final_x_data = df_cleaned[x_column_name_in_df]

    try:
        if chart_type == 'bar':
            fig = px.bar(df_cleaned, x=final_x_data, y=y_column, title=title,
                           labels={y_column: y_axis_title if y_axis_title else y_column, 
                                   x_label: x_label})
        elif chart_type == 'line':
            fig = px.line(df_cleaned, x=final_x_data, y=y_column, title=title,
                            labels={y_column: y_axis_title if y_axis_title else y_column, 
                                    x_label: x_label}, 
                            markers=True)
        else: 
            return {"error": f"Unsupported chart type: {chart_type}"}

        fig.update_layout(yaxis_title=y_axis_title if y_axis_title else y_column, 
                          xaxis_title=x_label,
                          yaxis_tickformat=',.0f', height=450, margin=dict(l=40, r=20, t=60, b=40))

        if pd.api.types.is_datetime64_any_dtype(final_x_data):
             fig.update_xaxes(tickformat='%Y-%m-%d', type='category') 

        chart_json_output = {"data": fig.data, "layout": fig.layout}
        return chart_json_output

    except Exception as e:
        print(f"Chart '{title}': Error creating Plotly figure object: {e}")
        return {"error": f"Error generating chart '{title}'. Details: {e}"}

# create_candlestick_chart_with_mavg - ללא שינוי מהגרסה הקודמת שהצגתי
def create_candlestick_chart_with_mavg(df_prices, ticker_symbol, moving_averages_to_plot=None):
    if df_prices is None or df_prices.empty:
        return {"error": "No price data available for candlestick chart."}
    try:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_prices.index, open=df_prices['Open'], high=df_prices['High'],
                                     low=df_prices['Low'], close=df_prices['Close'], name=f'{ticker_symbol}'))
        if moving_averages_to_plot:
            for ma_col in moving_averages_to_plot:
                if ma_col in df_prices.columns: 
                    fig.add_trace(go.Scatter(x=df_prices.index, y=df_prices[ma_col], mode='lines', name=ma_col, line=dict(width=1.5)))
        fig.update_layout(title=f'גרף נרות יומי וממוצעים נעים - {ticker_symbol}', xaxis_title='תאריך', yaxis_title='מחיר',
                          xaxis_rangeslider_visible=False, height=600, legend_title_text='מקרא')
        return {"data": fig.data, "layout": fig.layout}
    except Exception as e:
        print(f"Error creating candlestick chart for {ticker_symbol}: {e}")
        return {"error": f"Error generating candlestick chart: {e}"}

# --- Flask Routes ---
# route_home - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/')
def route_home():
    current_ticker = session.get('current_ticker', '')
    api_key_status = get_api_key_status_for_display()
    chart_json = None
    price_error = None

    if current_ticker:
        moving_averages_config = [20, 50, 100, 150, 200]
        df_prices = download_price_history_with_mavg(current_ticker, period="10y", interval="1d", moving_averages=moving_averages_config)

        if df_prices is not None and not df_prices.empty:
            ma_cols_to_plot = [f'MA{ma}' for ma in moving_averages_config if f'MA{ma}' in df_prices.columns]
            chart_data = create_candlestick_chart_with_mavg(df_prices, current_ticker, ma_cols_to_plot)
            if chart_data and "error" not in chart_data:
                chart_json = json.dumps(chart_data, cls=plotly.utils.PlotlyJSONEncoder)
            elif chart_data and "error" in chart_data:
                price_error = chart_data["error"]
        else:
            price_error = f"לא נמצאו נתוני מחירים עבור {current_ticker} או שגיאה בהורדה."

    return render_template('base_layout.html', 
                           page_title='ניתוח מניות - דף הבית', 
                           current_ticker=current_ticker,
                           content_template='content_home.html',
                           candlestick_chart_json=chart_json, 
                           price_data_error=price_error,
                           api_key_status_display=api_key_status)

# route_set_ticker - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/set_ticker', methods=['POST'])
def route_set_ticker():
    if request.method == 'POST':
        ticker = request.form.get('ticker_input', '').upper().strip() 
        if ticker: 
            session['current_ticker'] = ticker
            download_results = download_financial_statements(ticker_symbol=ticker)
            session_data_status = {} 
            any_success = False

            for stmt_key_for_session in ['income']: 
                 for variant_for_session in ['annual', 'quarterly']:
                    session.pop(f'{stmt_key_for_session}_{variant_for_session}_df_json', None)

            for variant in ['annual', 'quarterly']:
                for stmt_key in ['income', 'balance', 'cashflow']:
                    result_key = f"{stmt_key}_{variant}"
                    data_item = download_results.get(result_key)

                    if isinstance(data_item, pd.DataFrame) and not data_item.empty:
                        human_readable_names = {'income': 'Income_Statement', 'balance': 'Balance_Sheet', 'cashflow': 'Cash_Flow_Statement'}
                        file_name = f"{ticker}_{human_readable_names[stmt_key]}_{variant}.csv"
                        ticker_save_dir = os.path.join(PROCESSED_DATA_BASE_DIR, ticker)
                        os.makedirs(ticker_save_dir, exist_ok=True)
                        save_path = os.path.join(ticker_save_dir, file_name)
                        try:
                            if isinstance(data_item.index, pd.DatetimeIndex) and data_item.index.name is None:
                                 data_item.index.name = 'Report Date'
                            data_item.to_csv(save_path, index=True)
                            session_data_status[result_key] = f"Saved: {os.path.basename(save_path)}"
                            any_success = True
                            if stmt_key == 'income': 
                                session[f'{result_key}_df_json'] = data_item.to_json(orient='split', date_format='iso')
                        except Exception as e:
                            session_data_status[result_key] = f"Error saving CSV for {result_key}: {e}"
                            print(f"Error saving {result_key} for {ticker} to CSV: {e}")
                    elif isinstance(data_item, dict) and "Error" in data_item:
                        session_data_status[result_key] = f"Download Error for {result_key}: {data_item['Details']}"
                    else: 
                        session_data_status[result_key] = f"No data or empty data for {result_key}."

            session['data_download_status'] = session_data_status
            flash(f"Data for {ticker} processed." if any_success else f"Failed to process or no data found for {ticker}.", "success" if any_success else "danger")
            return redirect(url_for('route_home')) 
        else:
            flash("לא הוזן טיקר או שהטיקר מכיל רק רווחים.", "warning")
    return redirect(url_for('route_home'))

# get_dataframe_from_session_or_csv - ללא שינוי מהגרסה הקודמת שהצגתי
def get_dataframe_from_session_or_csv(ticker, variant, statement_key):
    session_key = f"{statement_key}_{variant}_df_json"
    df = None
    error_message = None
    info_message = None

    if session_key in session:
        try:
            df_json_str = session.get(session_key)
            if df_json_str: 
                df = pd.read_json(df_json_str, orient='split', convert_dates=['index'])
                if not isinstance(df.index, pd.DatetimeIndex): 
                    df.index = pd.to_datetime(df.index, errors='coerce')
                df = df.sort_index() 
                if not df.empty:
                    info_message = f"Data for {statement_key} ({variant}) loaded from session."
                else: 
                    df = None 
                    info_message = f"Data for {statement_key} ({variant}) from session is empty. Trying CSV."
            else: 
                 session.pop(session_key, None) 
                 info_message = f"Invalid data in session for {statement_key} ({variant}). Trying CSV."
        except Exception as e:
            error_message = f"Error loading {statement_key} ({variant}) from session: {e}. Trying CSV."
            session.pop(session_key, None) 
            df = None 

    if df is None:
        file_path = get_statement_file_path(ticker, statement_key, variant)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0)
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, errors='coerce')
                df = df[df.index.notna()] 
                df = df.sort_index()

                if not df.empty: 
                    loaded_from_csv_msg = f"Data for {statement_key} ({variant}) loaded from CSV: {os.path.basename(file_path)}"
                    info_message = f"{info_message} {loaded_from_csv_msg}".strip() if info_message else loaded_from_csv_msg
                    if statement_key == 'income':
                        session[session_key] = df.to_json(orient='split', date_format='iso')
                else:
                    empty_csv_msg = f"CSV file for {statement_key} ({variant}) is empty."
                    info_message = f"{info_message} {empty_csv_msg}".strip() if info_message else empty_csv_msg
                    df = None 
            except Exception as e:
                csv_error_msg = f"Error reading CSV {os.path.basename(file_path)} for {statement_key} ({variant}): {e}"
                error_message = f"{error_message} {csv_error_msg}".strip() if error_message else csv_error_msg
                df = None 
        elif not error_message: 
            file_not_found_msg = f"CSV file for {statement_key} ({variant}) not found for {ticker}."
            error_message = file_not_found_msg
    return df, error_message, info_message

# route_graphs_annual - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/graphs/annual')
def route_graphs_annual():
    current_ticker = session.get('current_ticker')
    api_key_status = get_api_key_status_for_display()
    if not current_ticker: 
        flash("אנא בחר טיקר תחילה.", "warning")
        return redirect(url_for('route_home'))

    df_income, error_data, info_data = get_dataframe_from_session_or_csv(current_ticker, 'annual', 'income')
    graph_revenue_json, graph_net_income_json = None, None

    if df_income is not None and not df_income.empty:
        revenue_col = next((col for col in ['Revenue', 'Total Revenue', 'Sales'] if col in df_income.columns), None)
        net_income_col_options = ['Net Income (Common)', 'Net Income', 'Net Income Available to Common Shareholders']
        net_income_col = next((col for col in net_income_col_options if col in df_income.columns), None)

        if revenue_col:
            chart_rev = create_timeseries_chart(df_income, revenue_col, f'הכנסות ({revenue_col}) - שנתי', y_axis_title='סכום')
            if chart_rev and "error" not in chart_rev: 
                graph_revenue_json = json.dumps(chart_rev, cls=plotly.utils.PlotlyJSONEncoder)
            elif chart_rev and "error" in chart_rev : 
                error_data = (error_data + "; " if error_data else "") + f"Revenue chart error: {chart_rev['error']}"
        else:
            error_data = (error_data + "; " if error_data else "") + "Revenue column not found in annual income data."

        if net_income_col:
            chart_ni = create_timeseries_chart(df_income, net_income_col, f'רווח נקי ({net_income_col}) - שנתי', y_axis_title='סכום')
            if chart_ni and "error" not in chart_ni: 
                graph_net_income_json = json.dumps(chart_ni, cls=plotly.utils.PlotlyJSONEncoder)
            elif chart_ni and "error" in chart_ni:
                error_data = (error_data + "; " if error_data else "") + f"Net income chart error: {chart_ni['error']}"
        else:
            error_data = (error_data + "; " if error_data else "") + "Net income column not found in annual income data."

    elif df_income is None: 
        no_data_msg = "No annual income data available to generate graphs."
        error_data = (error_data + "; " if error_data else "") + no_data_msg

    return render_template('base_layout.html', page_title=f'גרפים שנתיים - {current_ticker}', current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Annual',
                           graph_revenue_json=graph_revenue_json, graph_net_income_json=graph_net_income_json,
                           data_error_message=error_data, data_info_message=info_data, api_key_status_display=api_key_status)

# route_graphs_quarterly - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/graphs/quarterly')
def route_graphs_quarterly():
    current_ticker = session.get('current_ticker')
    api_key_status = get_api_key_status_for_display()
    if not current_ticker: 
        flash("אנא בחר טיקר תחילה.", "warning")
        return redirect(url_for('route_home'))

    df_income_q, error_data_q, info_data_q = get_dataframe_from_session_or_csv(current_ticker, 'quarterly', 'income')
    graph_revenue_json_q, graph_net_income_json_q = None, None

    if df_income_q is not None and not df_income_q.empty:
        revenue_col = next((col for col in ['Revenue', 'Total Revenue', 'Sales'] if col in df_income_q.columns), None)
        net_income_col_options = ['Net Income (Common)', 'Net Income', 'Net Income Available to Common Shareholders']
        net_income_col = next((col for col in net_income_col_options if col in df_income_q.columns), None)

        if revenue_col:
            chart_rev_q = create_timeseries_chart(df_income_q, revenue_col, f'הכנסות ({revenue_col}) - רבעוני', y_axis_title='סכום')
            if chart_rev_q and "error" not in chart_rev_q: 
                graph_revenue_json_q = json.dumps(chart_rev_q, cls=plotly.utils.PlotlyJSONEncoder)
            elif chart_rev_q and "error" in chart_rev_q :
                 error_data_q = (error_data_q + "; " if error_data_q else "") + f"Quarterly revenue chart error: {chart_rev_q['error']}"
        else:
            error_data_q = (error_data_q + "; " if error_data_q else "") + "Revenue column not found in quarterly income data."

        if net_income_col:
            chart_ni_q = create_timeseries_chart(df_income_q, net_income_col, f'רווח נקי ({net_income_col}) - רבעוני', y_axis_title='סכום')
            if chart_ni_q and "error" not in chart_ni_q: 
                graph_net_income_json_q = json.dumps(chart_ni_q, cls=plotly.utils.PlotlyJSONEncoder)
            elif chart_ni_q and "error" in chart_ni_q:
                error_data_q = (error_data_q + "; " if error_data_q else "") + f"Quarterly net income chart error: {chart_ni_q['error']}"
        else:
             error_data_q = (error_data_q + "; " if error_data_q else "") + "Net income column not found in quarterly income data."

    elif df_income_q is None:
        no_data_msg_q = "No quarterly income data available to generate graphs."
        error_data_q = (error_data_q + "; " if error_data_q else "") + no_data_msg_q

    return render_template('base_layout.html', page_title=f'גרפים רבעוניים - {current_ticker}', current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Quarterly',
                           graph_revenue_json=graph_revenue_json_q, graph_net_income_json=graph_net_income_json_q,
                           data_error_message=error_data_q, data_info_message=info_data_q, api_key_status_display=api_key_status)

# route_valuations - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/valuations')
def route_valuations():
    current_ticker = session.get('current_ticker', None)
    api_key_status = get_api_key_status_for_display()
    return render_template('base_layout.html', 
                           page_title='הערכות שווי',
                           current_ticker=current_ticker,
                           content_template='content_valuations.html',
                           api_key_status_display=api_key_status)

# route_update_api_key_action - ללא שינוי מהגרסה הקודמת שהצגתי
@app.route('/update_api_key_action', methods=['POST'])
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
            else: 
                if os.path.exists(API_KEY_FILE):
                    try: 
                        os.remove(API_KEY_FILE)
                    except OSError as e: 
                        print(f"Could not remove API key file: {e}") 
                        flash('שגיאה במחיקת קובץ מפתח API קיים, אך האפליקציה תשתמש בנתוני "free".', 'warning')
                    else:
                         flash('מפתח API נמחק/נוקה. האפליקציה תשתמש כעת בנתוני "free".', 'info')
                else: 
                    flash('לא היה מפתח API מותאם אישית, האפליקציה ממשיכה להשתמש בנתוני "free".', 'info')

                sf.set_api_key('free') 
                session['api_key_status_display'] = get_api_key_status_for_display() 

        except Exception as e: 
            error_message_for_user = "שגיאה בעדכון מפתח API. אנא בדוק את הלוגים של השרת."
            flash(error_message_for_user, 'danger')
            print(f"Error updating API key: {e}") 
            session['api_key_status_display'] = "שגיאה בעדכון מפתח." 

        return redirect(request.referrer or url_for('route_home'))

    return redirect(url_for('route_home'))

if __name__ == '__main__':
    app.run(debug=True)