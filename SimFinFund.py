# SimFinFund.py
import simfin as sf
import pandas as pd
import os
import json # לייצוא נתוני גרף ל-JSON
import yfinance as yf # לייבוא עבור פונקציית גרף הנרות

from flask import Flask, render_template, request, url_for, redirect, flash, session
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils # לייצוא נתוני גרף ל-JSON

# --- ייבוא פונקציות ההורדה ---
from downloader import download_financial_statements, download_price_history_with_mavg

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
                # print("SimFinFund.py: API key loaded from file.") # הוסר
            # else: # הוסר
                # print(f"SimFinFund.py: API key file is empty. Using 'free'.") # הוסר
        except IOError:
            print(f"SimFinFund.py: Could not read API key file. Using 'free'.") # נשאר - מידע חשוב
    # else: # הוסר
        # print(f"SimFinFund.py: API key file not found. Using 'free'.") # הוסר
    return api_key

api_key_to_set = load_simfin_api_key()
sf.set_api_key(api_key_to_set)

simfin_data_directory = os.path.join(os.path.expanduser('~'), 'simfin_data')
os.makedirs(simfin_data_directory, exist_ok=True)
sf.set_data_dir(simfin_data_directory)
# print(f"SimFinFund.py: SimFin data directory set to: {simfin_data_directory}") # הוסר

script_dir = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DATA_BASE_DIR = os.path.join(script_dir, 'Data')
os.makedirs(PROCESSED_DATA_BASE_DIR, exist_ok=True)
# print(f"SimFinFund.py: Processed CSVs will be saved to: {PROCESSED_DATA_BASE_DIR}") # הוסר

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_for_flask_sessions_CHANGE_ME_PLEASE_FINAL'

# print("SimFinFund.py: Application starting. Data will be fetched on user request via ticker input.") # הוסר

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
    if os.path.exists(API_KEY_FILE) and os.path.getsize(API_KEY_FILE) > 0:
        with open(API_KEY_FILE, 'r') as f:
            key_in_file = f.read().strip()
        return "מפתח API מותאם אישית נטען מהקובץ." if key_in_file.lower() != 'free' else "משתמש במפתח 'free' מהקובץ."
    return "קובץ מפתח לא קיים או ריק, משתמש ב-'free' כברירת מחדל."

# --- פונקציות ליצירת גרפים ---

def create_timeseries_chart(df, y_column, title, x_column_name_in_df=None, y_axis_title=None, chart_type='bar'):
    """
    Creates a time series chart (bar or line) using Plotly Express.
    Assumes the DataFrame's index is DatetimeIndex if x_column_name_in_df is None.
    Returns a dictionary for Plotly JSON rendering or an error dictionary.
    """
    # print(f"\n--- Attempting to create chart: '{title}' ---") # הוסר
    if df is None or df.empty:
        # print(f"DataFrame is empty for chart '{title}'") # הוסר
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

        # print(f"Chart '{title}': Plotly figure object created successfully.") # הוסר
        chart_json_output = {"data": fig.data, "layout": fig.layout}
        return chart_json_output

    except Exception as e:
        print(f"Chart '{title}': Error creating Plotly figure object: {e}") # נשאר - מידע שגיאה חשוב
        # import traceback # הוסר
        # traceback.print_exc() # הוסר
        return {"error": f"Error generating chart '{title}'. Details: {e}"}


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
        print(f"Error creating candlestick chart for {ticker_symbol}: {e}") # נשאר - מידע שגיאה חשוב
        return {"error": f"Error generating candlestick chart: {e}"}

# --- Flask Routes ---
@app.route('/')
def route_home():
    current_ticker = session.get('current_ticker', '')
    api_key_status = get_api_key_status_for_display()
    chart_json = None
    price_error = None

    if current_ticker:
        # print(f"route_home: Current ticker is {current_ticker}. Fetching price history...") # הוסר
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
            # print(f"route_home: {price_error}") # הוסר, המשתמש יראה הודעה מתאימה
            
    return render_template('base_layout.html',
                           page_title='ניתוח מניות - דף הבית',
                           current_ticker=current_ticker,
                           content_template='content_home.html',
                           candlestick_chart_json=chart_json,
                           price_data_error=price_error,
                           api_key_status_display=api_key_status)

@app.route('/set_ticker', methods=['POST'])
def route_set_ticker():
    if request.method == 'POST':
        ticker = request.form.get('ticker_input', '').upper()
        if ticker:
            session['current_ticker'] = ticker
            # print(f"SimFinFund.py: Ticker set to {ticker}. Attempting to download financial data...") # הוסר
            download_results = download_financial_statements(ticker_symbol=ticker)
            session_data_status = {}
            any_success = False
            session.pop('income_annual_df_json', None)
            session.pop('income_quarterly_df_json', None)
            # (אפשר להוסיף גם למאזן ותזרים אם נשתמש בהם ישירות לגרפים)

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
                            if isinstance(data_item.index, pd.DatetimeIndex): data_item.index.name = data_item.index.name or 'Report Date'
                            data_item.to_csv(save_path, index=True)
                            session_data_status[result_key] = f"Saved: {os.path.basename(save_path)}"
                            any_success = True
                            if stmt_key == 'income': # שמור רק דוחות הכנסה ב-session כרגע
                                session[f'{result_key}_df_json'] = data_item.to_json(orient='split', date_format='iso')
                        except Exception as e:
                            session_data_status[result_key] = f"Error saving CSV/session: {e}"
                            print(f"Error saving {result_key} for {ticker} to CSV/session: {e}") # נשאר - שגיאה חשובה
                    elif isinstance(data_item, dict) and "Error" in data_item:
                        session_data_status[result_key] = f"Download Error: {data_item['Details']}"
                    else: session_data_status[result_key] = f"No data for {result_key}."
            session['data_download_status'] = session_data_status
            flash(f"Data for {ticker} processed." if any_success else f"Failed to process data for {ticker}.", "success" if any_success else "danger")
            return redirect(url_for('route_home'))
        else:
            flash("לא הוזן טיקר.", "warning")
    return redirect(url_for('route_home'))

def get_dataframe_from_session_or_csv(ticker, variant, statement_key):
    session_key = f"{statement_key}_{variant}_df_json"
    df = None; error_message = None; info_message = None
    if session_key in session:
        try:
            df = pd.read_json(session[session_key], orient='split', convert_dates=['index']).sort_index()
            if not df.empty: info_message = f"Data loaded from session."
            else: df = None; info_message = "Data from session is empty."
        except Exception as e: error_message = f"Error loading from session: {e}. Trying CSV."; session.pop(session_key, None)
    if df is None:
        file_path = get_statement_file_path(ticker, statement_key, variant)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0)
                if not isinstance(df.index, pd.DatetimeIndex): df.index = pd.to_datetime(df.index, errors='coerce')
                df = df[df.index.notna()].sort_index()
                if not df.empty:
                    info_message = (info_message or "") + f" Data loaded from CSV: {os.path.basename(file_path)}"
                    session[session_key] = df.to_json(orient='split', date_format='iso') # טען מחדש לסשן
                else: info_message = (info_message or "") + f" CSV file is empty."; df = None
            except Exception as e: error_message = (error_message or "") + f" Error reading CSV {file_path}: {e}"
        elif not error_message: error_message = f"CSV file for {statement_key} ({variant}) not found for {ticker}."
    return df, error_message, info_message

@app.route('/graphs/annual')
def route_graphs_annual():
    current_ticker = session.get('current_ticker')
    api_key_status = get_api_key_status_for_display()
    if not current_ticker: flash("אנא בחר טיקר תחילה.", "warning"); return redirect(url_for('route_home'))

    df_income, error_data, info_data = get_dataframe_from_session_or_csv(current_ticker, 'annual', 'income')
    graph_revenue_json, graph_net_income_json = None, None
    if df_income is not None and not df_income.empty:
        net_income_col = 'Net Income (Common)' if 'Net Income (Common)' in df_income.columns else 'Net Income'
        revenue_col = 'Revenue'
        chart_rev = create_timeseries_chart(df_income, revenue_col, 'הכנסות (Revenue) - שנתי', y_axis_title='סכום')
        if chart_rev and "error" not in chart_rev: graph_revenue_json = json.dumps(chart_rev, cls=plotly.utils.PlotlyJSONEncoder)
        else: error_data = (error_data or "") + (chart_rev["error"] if chart_rev else " Chart error.")

        chart_ni = create_timeseries_chart(df_income, net_income_col, f'רווח נקי ({net_income_col}) - שנתי', y_axis_title='סכום')
        if chart_ni and "error" not in chart_ni: graph_net_income_json = json.dumps(chart_ni, cls=plotly.utils.PlotlyJSONEncoder)
        else: error_data = (error_data or "") + (chart_ni["error"] if chart_ni else " Chart error.")

    return render_template('base_layout.html', page_title=f'גרפים שנתיים - {current_ticker}', current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Annual',
                           graph_revenue_json=graph_revenue_json, graph_net_income_json=graph_net_income_json,
                           data_error_message=error_data, data_info_message=info_data, api_key_status_display=api_key_status)

@app.route('/graphs/quarterly')
def route_graphs_quarterly():
    current_ticker = session.get('current_ticker')
    api_key_status = get_api_key_status_for_display()
    if not current_ticker: flash("אנא בחר טיקר תחילה.", "warning"); return redirect(url_for('route_home'))

    df_income_q, error_data_q, info_data_q = get_dataframe_from_session_or_csv(current_ticker, 'quarterly', 'income')
    graph_revenue_json_q, graph_net_income_json_q = None, None
    if df_income_q is not None and not df_income_q.empty:
        net_income_col = 'Net Income (Common)' if 'Net Income (Common)' in df_income_q.columns else 'Net Income'
        revenue_col = 'Revenue'
        chart_rev_q = create_timeseries_chart(df_income_q, revenue_col, 'הכנסות (Revenue) - רבעוני', y_axis_title='סכום')
        if chart_rev_q and "error" not in chart_rev_q: graph_revenue_json_q = json.dumps(chart_rev_q, cls=plotly.utils.PlotlyJSONEncoder)
        else: error_data_q = (error_data_q or "") + (chart_rev_q["error"] if chart_rev_q else " Chart error.")

        chart_ni_q = create_timeseries_chart(df_income_q, net_income_col, f'רווח נקי ({net_income_col}) - רבעוני', y_axis_title='סכום')
        if chart_ni_q and "error" not in chart_ni_q: graph_net_income_json_q = json.dumps(chart_ni_q, cls=plotly.utils.PlotlyJSONEncoder)
        else: error_data_q = (error_data_q or "") + (chart_ni_q["error"] if chart_ni_q else " Chart error.")

    return render_template('base_layout.html', page_title=f'גרפים רבעוניים - {current_ticker}', current_ticker=current_ticker,
                           content_template='content_graphs.html', graph_type='Quarterly',
                           graph_revenue_json=graph_revenue_json_q, graph_net_income_json=graph_net_income_json_q,
                           data_error_message=error_data_q, data_info_message=info_data_q, api_key_status_display=api_key_status)

@app.route('/valuations')
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
                    try: os.remove(API_KEY_FILE)
                    except Exception: pass
                sf.set_api_key('free')
                session['api_key_status_display'] = get_api_key_status_for_display()
                flash('מפתח API נמחק/נוקה. האפליקציה תשתמש כעת בנתוני "free".', 'info')
        except Exception as e:
            session['api_key_status_display'] = f"שגיאה בעדכון: {e}"
            flash(f'שגיאה בעדכון מפתח API: {e}', 'danger')
            print(f"Error updating API key: {e}") # נשאר - שגיאה חשובה
        return redirect(request.referrer or url_for('route_home'))
    return redirect(url_for('route_home'))

if __name__ == '__main__':
    app.run(debug=True)