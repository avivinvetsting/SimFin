# downloader.py
import simfin as sf
import pandas as pd
import time # להשהיות
import yfinance as yf

#---------------------------------------------------------------------------------------------

def download_price_history_with_mavg(ticker_symbol, period="10y", interval="1d", moving_averages=None):
    """
    Downloads historical price data for a ticker and calculates specified moving averages.

    Args:
        ticker_symbol (str): The stock ticker.
        period (str): Period for historical data (e.g., "1mo", "6mo", "1y", "5y", "max").
        interval (str): Data interval (e.g., "1d", "1wk", "1mo").
        moving_averages (list of int, optional): List of window sizes for moving averages.
                                                 Defaults to None (no moving averages).

    Returns:
        pd.DataFrame: DataFrame with OHLC, Volume, and calculated moving averages, or None if error.
    """
    # print(f"downloader.py: Downloading price history for {ticker_symbol} (period: {period}, interval: {interval})") # הוסר
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist_df = ticker.history(period=period, interval=interval)

        if hist_df.empty:
            print(f"downloader.py: No price history found for {ticker_symbol} with period {period}, interval {interval}.") # נשאר - מידע חשוב
            return None

        if moving_averages:
            for ma in moving_averages:
                if isinstance(ma, int) and ma > 0:
                    hist_df[f'MA{ma}'] = hist_df['Close'].rolling(window=ma).mean()
        
        # print(f"downloader.py: Price history for {ticker_symbol} downloaded and MAs calculated.") # הוסר
        return hist_df
    except Exception as e:
        print(f"downloader.py: Error downloading price history for {ticker_symbol}: {e}") # נשאר - מידע שגיאה חשוב
        return None
#---------------------------------------------------------------------------------------------

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
    # print(f"downloader.py: Attempting to download ALL (Annual & Quarterly) statements for {ticker_symbol}...") # הוסר
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
            result_key = f"{stmt_key}_{variant}"
            readable_name = statement_type_readable_names[stmt_key]
            # print(f"downloader.py: Processing {readable_name} ({variant}) for {ticker_upper}...") # הוסר
            time.sleep(0.5)

            try:
                df_all = load_function(variant=variant, market=market)
                
                current_df = None
                if df_all is not None:
                    if 'Ticker' in df_all.index.names:
                        if ticker_upper in df_all.index.get_level_values('Ticker'):
                            current_df = df_all.loc[ticker_upper]
                        else:
                            current_df = pd.DataFrame()
                    elif 'Ticker' in df_all.columns:
                        current_df = df_all[df_all['Ticker'] == ticker_upper]
                    else:
                        results[result_key] = {"Error": "FilterFailed", "Details": f"Could not find 'Ticker' info in {readable_name} ({variant}) dataset."}
                        # print(f"downloader.py: FilterFailed for {result_key}") # הוסר (המידע קיים ב-results)
                        continue

                    if current_df is not None:
                        if not current_df.empty:
                            results[result_key] = current_df.copy()
                            # print(f"downloader.py: {result_key} for {ticker_symbol} processed successfully.") # הוסר
                        else:
                            results[result_key] = {"Error": "NoDataFound", "Details": f"No {readable_name} ({variant}) data for {ticker_symbol} (DataFrame empty after filter)."}
                            # print(f"downloader.py: NoDataFound for {result_key}") # הוסר (המידע קיים ב-results)
                else:
                    results[result_key] = {"Error": "LoadFailed", "Details": f"Failed to load ALL {readable_name} ({variant}) (SimFin returned None)."}
                    print(f"downloader.py: LoadFailed for ALL {result_key} for {ticker_symbol}") # נשאר - שגיאה חשובה

            except Exception as e:
                print(f"downloader.py: Exception for {result_key} for {ticker_symbol}: {e}") # נשאר - שגיאה חשובה
                results[result_key] = {"Error": "ProcessingException", "Details": str(e)}
                
    # print(f"downloader.py: Finished all download attempts for {ticker_symbol}.") # הוסר
    return results