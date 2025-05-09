import simfin as sf
from simfin.names import *
import pandas as pd
import os
import time
from flask import Flask, render_template, url_for


Tiker = 'ASML'
# --- API Key Handling ---
API_KEY_FILE = 'simfin_api_key.txt'

def load_simfin_api_key():
    api_key = None
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, 'r') as f:
                api_key = f.read().strip()
            if not api_key:
                print(f"Warning: API key file {API_KEY_FILE} is empty. Using 'free' data.")
                api_key = 'free'
            else:
                 print("API key loaded successfully from file.")
        except IOError:
            print(f"Warning: Could not read API key file {API_KEY_FILE}. Using 'free' data.")
            api_key = 'free'
    else:
        print(f"Warning: API key file {API_KEY_FILE} not found. Using 'free' data.")
        api_key = 'free'
    return api_key

# Load the API key and configure SimFin
api_key = load_simfin_api_key()
sf.set_api_key(api_key)

# Set the local directory where SimFin data-files are stored (for SimFin's internal cache)
# This is separate from where we will save the filtered data.
simfin_cache_dir = os.path.expanduser('~/simfin_data/') # Keep SimFin's cache in the home directory
sf.set_data_dir(simfin_cache_dir)


# --- Define the directory for saving filtered data relative to the script ---
# Get the directory of the current script
script_dir = os.path.dirname(__file__)
# Define the path to the new Data directory
data_save_base_dir = os.path.join(script_dir, 'Data') # <-- Changed to save directly in Data

# Create the base Data directory if it doesn't exist
os.makedirs(data_save_base_dir, exist_ok=True)
print(f"Filtered data will be saved to the 'Data' directory: {data_save_base_dir}")


# --- Flask Application Setup ---
app = Flask(__name__)

# Define the ticker and variant to use
TARGET_TICKER = Tiker

TARGET_VARIANT = 'quarterly' # Or 'annual'

# --- Data Download, Filtering, and Saving upon Server Startup ---
# This block runs ONCE when the script starts, before app.run()
print("\n--- Starting initial data download, filtering, and saving ---")

datasets_to_process = {
    'Income Statement': 'IncomeDownloadCode',
    'Balance Sheet': 'BalanceDownloadCode',
    'Cash Flow Statement': 'CashflowDownloadCode'
}

# Dictionary to hold the full market DataFrames from imports (optional, mainly for debugging)
downloaded_dfs = {}

for dataset_name, module_name in datasets_to_process.items():
    print(f"\nProcessing {dataset_name} data (from module: {module_name})...")
    try:
        # Import the download module - this triggers the download (or cache load) inside it
        # Ensure these download modules DO NOT have sf.set_api_key or os.chdir
        module = __import__(module_name) # Use __import__ for dynamic import

        if hasattr(module, 'df') and isinstance(module.df, pd.DataFrame) and not module.df.empty:
            print(f"Successfully loaded full market DataFrame from {module_name}.")
            df_full = module.df
            downloaded_dfs[dataset_name] = df_full # Store the full DataFrame

            # --- Filter and Save the filtered data to a CSV file ---
            if TARGET_TICKER in df_full.index.get_level_values('Ticker'):
                 ticker_data = df_full.loc[TARGET_TICKER]
                 print(f"Filtered data for ticker {TARGET_TICKER} for {dataset_name}.")

                 # Create a subdirectory for the ticker within the Data directory
                 ticker_save_dir = os.path.join(data_save_base_dir, TARGET_TICKER) # <-- Save in Data/Ticker/
                 os.makedirs(ticker_save_dir, exist_ok=True)

                 # Define the filename
                 safe_dataset_name = dataset_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                 file_name = f"{TARGET_TICKER}_{safe_dataset_name}_{TARGET_VARIANT}.csv"
                 save_path = os.path.join(ticker_save_dir, file_name)

                 try:
                     ticker_data.to_csv(save_path, index=True) # Save with index (Report Date)
                     print(f"Successfully saved filtered data to: {save_path}")
                 except Exception as save_e:
                     print(f"Error saving filtered data to CSV ({save_path}): {save_e}")
                 # --- End Save ---

            else:
                 print(f"Info: No {dataset_name} data found for ticker {TARGET_TICKER} in the loaded dataset.")

        elif hasattr(module, 'df') and isinstance(module.df, dict) and 'Error' in module.df:
            # If the module's df is an error dict (from the except block in the module itself if it has one)
             print(f"Error reported during import of {module_name}: {module.df['Error']}")
        else:
            print(f"Warning: Could not load full market DataFrame from {module_name}. 'df' not found or is empty.")

    except ImportError as e:
        print(f"Import Error: Could not import module {module_name}: {e}. Make sure the file exists and has no syntax errors.")
    except Exception as e:
        print(f"An unexpected error occurred while processing {module_name}: {e}")

    # Optional: Add a small delay between processing different datasets during startup
    # time.sleep(1) # Re-enabled delay if needed

print("\n--- Initial data processing complete ---")


# --- Flask Routes (Now loading from saved files) ---

@app.route('/')
def index():
    """
    Landing page with links to the different reports.
    """
    # Passing data_save_base_dir to the template is optional, but helpful
    return render_template('index.html',
                           ticker=TARGET_TICKER,
                           variant=TARGET_VARIANT,
                           data_save_base_dir=data_save_base_dir)

@app.route('/<statement_type>')
def show_statement(statement_type):
    """
    Generic route to display statement data loaded from saved CSV files.
    """
    statement_name_map = {
        'income': 'Income Statement',
        'balance': 'Balance Sheet',
        'cashflow': 'Cash Flow Statement'
    }
    display_name = statement_name_map.get(statement_type, 'Unknown Statement')

    data_html = f"<p style='color: red;'>Error: Could not load data for {display_name}.</p>"
    file_found = False

    # Construct the expected save path based on the statement type
    safe_dataset_name = display_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    file_name = f"{TARGET_TICKER}_{safe_dataset_name}_{TARGET_VARIANT}.csv"
    save_path = os.path.join(data_save_base_dir, TARGET_TICKER, file_name) # <-- Load from Data/Ticker/

    print(f"\nWeb request for {display_name}. Attempting to load data from file: {save_path}")

    if os.path.exists(save_path):
        try:
            # Read the data from the saved CSV file
            # Assuming index column is the first column (as saved with index=True)
            ticker_data = pd.read_csv(save_path, index_col=0)
            file_found = True
            print(f"Successfully loaded data from file: {save_path}")

            if not ticker_data.empty:
                 # Convert numeric columns to appropriate format if needed (optional)
                 # for col in ticker_data.columns:
                 #     if pd.api.types.is_numeric_dtype(ticker_data[col]):
                 #         ticker_data[col] = ticker_data[col].apply(lambda x: f'{x:,.0f}' if pd.notnull(x) else '') # Format as integers with commas

                 data_html = ticker_data.to_html(index=True, classes='table table-striped')
            else:
                 data_html = f"<p style='color: blue;'>Info: The saved file ({file_name}) is empty.</p>"

        except Exception as e:
            data_html = f"<p style='color: red;'>Error reading data file ({file_name}): {e}</p>"
            print(data_html)
    else:
        data_html = f"<p style='color: blue;'>Info: Data file not found for {display_name} ({file_name}). Data may not have been downloaded or saved successfully during server startup.</p>"
        print(data_html)


    return render_template('statement.html',
                           ticker=TARGET_TICKER,
                           variant=TARGET_VARIANT,
                           statement_name=display_name,
                           data_html=data_html)


# --- Running the Flask App ---
if __name__ == '__main__':
    # Add data_save_base_dir to the app config for potential use in templates (optional)
    app.config['DATA_SAVE_BASE_DIR'] = data_save_base_dir
    app.run(debug=True)