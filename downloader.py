# downloader.py
import simfin as sf
import pandas as pd
import time # להשהיות

def download_financial_statements(ticker_symbol, market='us'):
    """
    Downloads ANNUAL and QUARTERLY financial statements (income, balance, cashflow)
    for a specific ticker. Uses the 'filtering after full load' approach.

    Args:
        ticker_symbol (str): The stock ticker.
        market (str): The market (e.g., 'us').

    Returns:
        dict: A dictionary where keys are like 'income_annual', 'income_quarterly', etc.,
              and values are DataFrames or error dictionaries.
    """
    print(f"downloader.py: Attempting to download ALL (Annual & Quarterly) statements for {ticker_symbol}...")
    results = {}
    ticker_upper = ticker_symbol.upper()
    variants = ['annual', 'quarterly']
    statement_types_map = {
        'income': sf.load_income,
        'balance': sf.load_balance,
        'cashflow': sf.load_cashflow
    }
    statement_type_readable_names = {
        'income': 'Income Statement',
        'balance': 'Balance Sheet',
        'cashflow': 'Cash Flow Statement'
    }

    for variant in variants:
        for stmt_key, load_function in statement_types_map.items():
            result_key = f"{stmt_key}_{variant}" # למשל, 'income_annual'
            readable_name = statement_type_readable_names[stmt_key]
            print(f"downloader.py: Processing {readable_name} ({variant}) for {ticker_upper}...")
            time.sleep(0.5) # השהייה קטנה בין כל קריאת API

            try:
                # טעינת כל הדאטהסט וסינון
                df_all = load_function(variant=variant, market=market)
                
                current_df = None 
                if df_all is not None:
                    # בדיקה אם 'Ticker' הוא חלק מהאינדקס או עמודה
                    if 'Ticker' in df_all.index.names:
                        if ticker_upper in df_all.index.get_level_values('Ticker'):
                            current_df = df_all.loc[ticker_upper]
                        else: 
                            current_df = pd.DataFrame() 
                    elif 'Ticker' in df_all.columns:
                        current_df = df_all[df_all['Ticker'] == ticker_upper]
                    else: 
                        results[result_key] = {"Error": "FilterFailed", "Details": f"Could not find 'Ticker' info in {readable_name} ({variant}) dataset."}
                        print(f"downloader.py: FilterFailed for {result_key}")
                        continue 

                    if current_df is not None: 
                        if not current_df.empty:
                            results[result_key] = current_df.copy()
                            print(f"downloader.py: {result_key} for {ticker_symbol} processed successfully.")
                        else:
                            results[result_key] = {"Error": "NoDataFound", "Details": f"No {readable_name} ({variant}) data for {ticker_symbol} (DataFrame empty after filter)."}
                            print(f"downloader.py: NoDataFound for {result_key}")
                else: 
                    results[result_key] = {"Error": "LoadFailed", "Details": f"Failed to load ALL {readable_name} ({variant}) (SimFin returned None)."}
                    print(f"downloader.py: LoadFailed for ALL {result_key}")
            
            except Exception as e:
                print(f"downloader.py: Exception for {result_key} for {ticker_symbol}: {e}")
                results[result_key] = {"Error": "ProcessingException", "Details": str(e)}
                
    print(f"downloader.py: Finished all download attempts for {ticker_symbol}.")
    return results