# CashflowDownloadCode.py (מותאם ללוגיקה הישנה של SimFinFund.py - פתרון זמני)
import simfin as sf
from simfin.names import *
import pandas as pd
import os # הוספנו בחזרה כי הקוד הישן כנראה מצפה לזה

# הערה: קוד זה מותאם לעבוד עם הלוגיקה הקיימת ב-SimFinFund.py
# שמצפה למשתנה df גלובלי.
# זהו פתרון זמני עד ש-SimFinFund.py ישוכתב לעבוד עם פונקציות ייעודיות.

# הקוד הבא דומה למה שהיה לך ב-IncomeDownloadCode.py ו-BalanceDownloadCode.py המקוריים
# הוא יטען את כל נתוני תזרים המזומנים (מה שה-API מאפשר) למשתנה df.

df = None # אתחול המשתנה
error_message_global = None

try:
    # נניח ש-SimFinFund.py כבר קרא ל-sf.set_api_key() ו-sf.set_data_dir()
    # עם זאת, אם IncomeDownloadCode ו-BalanceDownloadCode מגדירים אותם בעצמם,
    # גם כאן צריך לעשות זאת כדי לשמור על עקביות זמנית.
    # אם SimFinFund.py *כן* מגדיר אותם גלובלית לפני ה-import, אז השורות הבאות מיותרות.
    # נבדוק את הפלט שלך - IncomeDownloadCode כן מגדיר אותם, אז גם כאן:

    TARGET_DIR_FALLBACK = r"D:\Investment Codes\Codes\Developement\SimFinFund" # נתיב גיבוי
    script_base_dir = os.path.dirname(os.path.abspath(__file__)) # נתיב הקובץ הנוכחי
    # נסה למצוא את TARGET_DIR באופן יחסי או השתמש בגיבוי
    # זה רק כדי להתאים להתנהגות של IncomeDownloadCode כפי שנראתה בפלט שלך
    if os.path.exists(os.path.join(script_base_dir, 'simfin_api_key.txt')):
        current_target_dir = script_base_dir
    else:
        current_target_dir = TARGET_DIR_FALLBACK

    API_KEY_FILE_CF = os.path.join(current_target_dir, 'simfin_api_key.txt')
    api_key_cf = 'free'
    if os.path.exists(API_KEY_FILE_CF):
        try:
            with open(API_KEY_FILE_CF, 'r') as f_cf:
                read_key_cf = f_cf.read().strip()
                if read_key_cf:
                    api_key_cf = read_key_cf
                    # print("CashflowDownloadCode: API key loaded successfully.") # פחות פלט מפורט
        except Exception:
            pass # שגיאות בקריאת מפתח יגרמו לשימוש ב-'free'
    # sf.set_api_key(api_key_cf) # הקוד הראשי אמור לעשות זאת פעם אחת

    data_dir_cf = os.path.join(current_target_dir, 'simfin_data')
    # sf.set_data_dir(data_dir_cf) # הקוד הראשי אמור לעשות זאת פעם אחת

    print("CashflowDownloadCode.py: Attempting to load FULL Cash Flow data (old logic)...")
    # טעינת כל נתוני תזרים המזומנים מהשוק (או מה שה-API החינמי מאפשר)
    # ללא פרמטר ticker, כדי שהלוגיקה הישנה ב-SimFinFund.py תוכל לסנן
    loaded_df = sf.load_cashflow(variant='quarterly', market='us') # או 'annual' אם זה מה שהשתמשת

    if loaded_df is not None and not loaded_df.empty:
        df = loaded_df # הגדרת המשתנה הגלובלי df
        print("CashflowDownloadCode.py: Full Cash Flow data loaded successfully into global 'df'.")
    elif loaded_df is not None and loaded_df.empty:
        error_message_global = "CashflowDownloadCode.py: Loaded full cash flow data but it is empty."
        print(error_message_global)
        df = pd.DataFrame() # DataFrame ריק כדי למנוע שגיאת 'df not found' אבל עדיין לציין ריקנות
    else: # loaded_df is None
        error_message_global = "CashflowDownloadCode.py: Failed to load full cash flow data (returned None)."
        print(error_message_global)
        df = pd.DataFrame() # DataFrame ריק

except Exception as e:
    error_message_global = f"CashflowDownloadCode.py: Error loading FULL Cash Flow data: {e}"
    print(error_message_global)
    # במקרה של שגיאה, SimFinFund.py יראה ש-df הוא None או ריק, או יקבל את הודעת השגיאה מה-print.
    # כדי להיות עקבי עם הלוגיקה שמחפשת module.df, ניצור df ריק.
    df = pd.DataFrame({'Error': [error_message_global]})


# כעת, כאשר SimFinFund.py ייבא את המודול הזה, הוא ימצא את המשתנה 'df'
# והלולאה הראשונית שלו אמורה להיות מסוגלת לנסות לסנן אותו.