# BalanceDownloadCode.py (Original)
import simfin as sf
from simfin.names import *
import pandas as pd
import os

try:
    print("Attempting to load Balance Sheet data within BalanceDownloadCode.py...")
    df = sf.load_balance(variant='quarterly', market='us', refresh_days=1)
    print("Balance Sheet data loaded successfully within BalanceDownloadCode.py.")
except Exception as e:
    print(f"Error loading Balance Sheet data within BalanceDownloadCode.py: {e}")
    df = {'Error': f'Loading Balance Sheet failed: {e}'}