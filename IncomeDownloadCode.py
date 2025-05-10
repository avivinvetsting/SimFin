# IncomeDownloadCode.py (גרסה מתוקנת)
import simfin as sf
from simfin.names import * # QUARTERLY, ANNUAL וכו'
import pandas as pd
# אין צורך ב-os כאן יותר, מכיוอน שטיפול בנתיבים למפתח API ותיקיית נתונים יעשה בקוד הראשי

# הערה: sf.set_api_key() ו- sf.set_data_dir() ייקראו בקוד הראשי (SimFinFund.py).
# מודול זה לא יחזור על הקריאות הללו.

def download_income_statement(ticker_symbol, variant='quarterly', market='us'):
    """
    מוריד או טוען מהמטמון את דוח ההכנסות עבור טיקר ותדירות ספציפיים.

    Args:
        ticker_symbol (str): סימול הטיקר (למשל, 'MSFT').
        variant (str): 'quarterly' או 'annual'.
        market (str): השוק (למשל, 'us').

    Returns:
        pandas.DataFrame: DataFrame עם נתוני דוח ההכנסות, או
        dict: מילון עם מידע על שגיאה אם ההורדה נכשלה.
    """
    print(f"IncomeDownloadCode.py: מנסה לטעון 'us-income-{variant}' עבור טיקר: {ticker_symbol}...")
    df_income = None
    error_info = None

    try:
        df_income = sf.load_income(variant=variant, market=market, ticker=ticker_symbol)

        if df_income is not None and not df_income.empty:
            print(f"IncomeDownloadCode.py: דוח הכנסות נטען בהצלחה עבור {ticker_symbol} ({variant}).")
            return df_income
        elif df_income is not None and df_income.empty: # ה-DataFrame ריק
            error_message = f"IncomeDownloadCode.py: לא נמצאו נתוני הכנסות עבור טיקר {ticker_symbol} ({variant}). ה-DataFrame ריק."
            print(error_message)
            error_info = {"Error": "NoDataFound", "Details": error_message, "Ticker": ticker_symbol, "Variant": variant}
            return error_info
        else: # df_income is None - קריאה ל-sf.load_income החזירה None
            error_message = f"IncomeDownloadCode.py: טעינת נתוני הכנסות נכשלה עבור טיקר {ticker_symbol} ({variant}). sf.load_income החזיר None."
            print(error_message)
            error_info = {"Error": "LoadFailed", "Details": error_message, "Ticker": ticker_symbol, "Variant": variant}
            return error_info

    except sf.SimFinTickerNotFoundError as e:
        error_message = f"IncomeDownloadCode.py: טיקר '{ticker_symbol}' לא נמצא על ידי SimFin עבור {market}-income-{variant}: {e}"
        print(error_message)
        error_info = {"Error": "TickerNotFound", "Details": str(e), "Ticker": ticker_symbol, "Variant": variant}
    except sf.SimFinAuthError as e:
        error_message = f"IncomeDownloadCode.py: שגיאת אימות SimFin: {e}. בדוק את מפתח ה-API שלך."
        print(error_message)
        error_info = {"Error": "SimFinAuthError", "Details": str(e)}
    except sf.SimFinAccountError as e:
        error_message = f"IncomeDownloadCode.py: שגיאת חשבון SimFin: {e}. בעיה אפשרית עם מגבלות מפתח API או מנוי."
        print(error_message)
        error_info = {"Error": "SimFinAccountError", "Details": str(e)}
    except sf.SimFinRateLimitError as e:
        error_message = f"IncomeDownloadCode.py: שגיאת מגבלת קצב בקשות SimFin: {e}. יותר מדי בקשות."
        print(error_message)
        error_info = {"Error": "SimFinRateLimitError", "Details": str(e)}
    except ConnectionError as e: # שגיאת רשת כללית
        error_message = f"IncomeDownloadCode.py: שגיאת חיבור רשת: {e}."
        print(error_message)
        error_info = {"Error": "ConnectionError", "Details": str(e)}
    except Exception as e: # תופס כל שגיאה אחרת לא צפויה
        error_message = f"IncomeDownloadCode.py: שגיאה לא צפויה התרחשה עבור טיקר {ticker_symbol} ({variant}): {e}"
        print(error_message)
        error_info = {"Error": "UnexpectedError", "Details": str(e), "Ticker": ticker_symbol, "Variant": variant}
    
    return error_info # יוחזר אם df_income נשאר None או אם הייתה שגיאה כללית

# # לדוגמה, אם רוצים לבדוק את המודול ישירות (לא חובה להשאיר בקוד הסופי):
# if __name__ == '__main__':
#     # חשוב: כדי להריץ את זה ישירות, צריך לוודא ש-API key ו-data_dir מוגדרים קודם.
#     # אפשר להוסיף כאן הגדרות מקומיות לבדיקה (שיוסרו מאוחר יותר).
#     # לדוגמה (אל תשכח להחליף בערכים אמיתיים לבדיקה):
#     # try:
#     #     sf.set_api_key('YOUR_API_KEY_OR_FREE') 
#     #     sf.set_data_dir('path_to_your_simfin_data_directory_for_testing')
#     # except Exception as e:
#     #     print(f"Error setting up for test: {e}")
#     #     exit()
#
#     print("\n--- IncomeDownloadCode.py executed directly for testing ---")
#     # test_data_msft_q = download_income_statement(ticker_symbol='MSFT', variant='quarterly')
#     # if isinstance(test_data_msft_q, pd.DataFrame):
#     #     print("\nMSFT Quarterly Income Statement:")
#     #     print(test_data_msft_q.head())
#     # else:
#     #     print(f"\nError fetching MSFT Quarterly: {test_data_msft_q}")