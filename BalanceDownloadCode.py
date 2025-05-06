import simfin as sf
from simfin.names import *
import pandas as pd
import os
# import time # No need for time import in this specific module unless using delays within it

# This module is imported by SimFinFund.py, which sets the API key and data directory.
# DO NOT set the API key or data directory here again.

# Load the data into a Pandas DataFrame.
# The API key is set by SimFinFund.py
try:
    print("Attempting to load Balance Sheet data within BalanceDownloadCode.py...")
    # Use the same parameters for loading as in SimFinFund.py's load_and_filter_statement
    df = sf.load_balance(variant='quarterly', market='us', refresh_days=1)
    print("Balance Sheet data loaded successfully within BalanceDownloadCode.py.")
except Exception as e:
    print(f"Error loading Balance Sheet data within BalanceDownloadCode.py: {e}")
    # If loading fails, store an error dictionary in 'df' so SimFinFund can detect it
    df = {'Error': f'Loading Balance Sheet failed: {e}'}

# The SimFinFund.py script will access this 'df' variable after import.
# No need to print df.head() or perform further processing here.