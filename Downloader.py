# downloader.py (גרסה עם סינון DataFrame לאחר טעינה כללית)
import simfin as sf
import pandas as pd
import os # הוספנו למקרה שנרצה להשתמש בו בעתיד, כרגע לא חובה

def download_all_statements_for_ticker(ticker_symbol, variant='quarterly', market='us'):
    """
    Downloads income, balance, and cash flow statements for a specific ticker
    by loading the full dataset and then filtering.
    """
    print(f"downloader.py: Attempting to download and filter all statements for {ticker_symbol} ({variant})...")
    results = {
        'income': {"Error": "NotProcessed", "Details": "Income statement not processed yet."},
        'balance': {"Error": "NotProcessed", "Details": "Balance sheet not processed yet."},
        'cashflow': {"Error": "NotProcessed", "Details": "Cash flow statement not processed yet."}
    }
    ticker_upper = ticker_symbol.upper() # לסינון, חשוב שהטיקר יהיה באותיות גדולות

    # Income Statement
    try:
        print(f"downloader.py: Loading ALL Income Statements for {market}-{variant} to filter for {ticker_upper}...")
        df_all_income = sf.load_income(variant=variant, market=market) # טוען את כל השוק
        
        if df_all_income is not None:
            # ודא שהעמודה 'Ticker' קיימת באינדקס או כעמודה רגילה
            if 'Ticker' in df_all_income.index.names: # אם 'Ticker' הוא חלק מה-MultiIndex
                if ticker_upper in df_all_income.index.get_level_values('Ticker'):
                    df_income = df_all_income.loc[ticker_upper]
                else: # הטיקר לא נמצא באינדקס
                    df_income = pd.DataFrame() # DataFrame ריק
            elif 'Ticker' in df_all_income.columns: # אם 'Ticker' הוא עמודה רגילה
                df_income = df_all_income[df_all_income['Ticker'] == ticker_upper]
            else: # אין דרך לסנן לפי טיקר
                results['income'] = {"Error": "FilterFailed", "Details": f"Could not find 'Ticker' information in Income Statement dataset to filter by."}
                df_income = None # לא ניתן להמשיך עם הדוח הזה
                print(f"downloader.py: Could not find 'Ticker' information in Income Statement dataset.")


            if df_income is not None: # אם הסינון בוצע או לא היה נחוץ (אבל אז זה שגוי)
                if not df_income.empty:
                    results['income'] = df_income.copy() # חשוב להשתמש ב-copy כדי למנוע SettingWithCopyWarning מאוחר יותר
                    print(f"downloader.py: Income Statement for {ticker_symbol} filtered successfully.")
                else: # הטיקר נמצא אבל אין לו נתונים (שורות ריקות)
                    results['income'] = {"Error": "NoDataFound", "Details": f"No Income Statement data found for {ticker_symbol} after filtering (DataFrame for ticker was empty)."}
                    print(f"downloader.py: No Income Statement data for {ticker_symbol} (DataFrame for ticker was empty).")
            # אם df_income הוא None (כי הסינון נכשל), הודעת השגיאה כבר ב-results
        else: # sf.load_income החזיר None
            results['income'] = {"Error": "LoadFailed", "Details": f"Failed to load ALL Income Statements (SimFin returned None)."}
            print(f"downloader.py: Failed to load ALL Income Statements (SimFin returned None).")
    except Exception as e:
        print(f"downloader.py: Error processing Income Statement for {ticker_symbol}: {e}")
        results['income'] = {"Error": "ProcessingException", "Details": str(e)}

    # Balance Sheet (באותה גישה של טעינה כללית וסינון)
    try:
        print(f"downloader.py: Loading ALL Balance Sheets for {market}-{variant} to filter for {ticker_upper}...")
        df_all_balance = sf.load_balance(variant=variant, market=market)
        
        if df_all_balance is not None:
            if 'Ticker' in df_all_balance.index.names:
                if ticker_upper in df_all_balance.index.get_level_values('Ticker'):
                    df_balance = df_all_balance.loc[ticker_upper]
                else:
                    df_balance = pd.DataFrame()
            elif 'Ticker' in df_all_balance.columns:
                df_balance = df_all_balance[df_all_balance['Ticker'] == ticker_upper]
            else:
                results['balance'] = {"Error": "FilterFailed", "Details": f"Could not find 'Ticker' information in Balance Sheet dataset to filter by."}
                df_balance = None
                print(f"downloader.py: Could not find 'Ticker' information in Balance Sheet dataset.")

            if df_balance is not None:
                if not df_balance.empty:
                    results['balance'] = df_balance.copy()
                    print(f"downloader.py: Balance Sheet for {ticker_symbol} filtered successfully.")
                else:
                    results['balance'] = {"Error": "NoDataFound", "Details": f"No Balance Sheet data found for {ticker_symbol} after filtering (DataFrame for ticker was empty)."}
                    print(f"downloader.py: No Balance Sheet data for {ticker_symbol} (DataFrame for ticker was empty).")
        else:
            results['balance'] = {"Error": "LoadFailed", "Details": f"Failed to load ALL Balance Sheets (SimFin returned None)."}
            print(f"downloader.py: Failed to load ALL Balance Sheets (SimFin returned None).")
    except Exception as e:
        print(f"downloader.py: Error processing Balance Sheet for {ticker_symbol}: {e}")
        results['balance'] = {"Error": "ProcessingException", "Details": str(e)}

    # Cash Flow Statement (באותה גישה של טעינה כללית וסינון)
    try:
        print(f"downloader.py: Loading ALL Cash Flow Statements for {market}-{variant} to filter for {ticker_upper}...")
        df_all_cashflow = sf.load_cashflow(variant=variant, market=market)
        
        if df_all_cashflow is not None:
            if 'Ticker' in df_all_cashflow.index.names:
                if ticker_upper in df_all_cashflow.index.get_level_values('Ticker'):
                    df_cashflow = df_all_cashflow.loc[ticker_upper]
                else:
                    df_cashflow = pd.DataFrame()
            elif 'Ticker' in df_all_cashflow.columns:
                df_cashflow = df_all_cashflow[df_all_cashflow['Ticker'] == ticker_upper]
            else:
                results['cashflow'] = {"Error": "FilterFailed", "Details": f"Could not find 'Ticker' information in Cash Flow dataset to filter by."}
                df_cashflow = None
                print(f"downloader.py: Could not find 'Ticker' information in Cash Flow dataset.")

            if df_cashflow is not None:
                if not df_cashflow.empty:
                    results['cashflow'] = df_cashflow.copy()
                    print(f"downloader.py: Cash Flow Statement for {ticker_symbol} filtered successfully.")
                else:
                    results['cashflow'] = {"Error": "NoDataFound", "Details": f"No Cash Flow Statement data found for {ticker_symbol} after filtering (DataFrame for ticker was empty)."}
                    print(f"downloader.py: No Cash Flow Statement data for {ticker_symbol} (DataFrame for ticker was empty).")
        else:
            results['cashflow'] = {"Error": "LoadFailed", "Details": f"Failed to load ALL Cash Flow Statements (SimFin returned None)."}
            print(f"downloader.py: Failed to load ALL Cash Flow Statements (SimFin returned None).")
    except Exception as e:
        print(f"downloader.py: Error processing Cash Flow Statement for {ticker_symbol}: {e}")
        results['cashflow'] = {"Error": "ProcessingException", "Details": str(e)}
            
    print(f"downloader.py: Finished download and filter attempts for {ticker_symbol}. Results have keys: {list(results.keys())}")
    return results