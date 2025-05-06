# Installation: pip install simfin
# import packages
import os
import simfin as sf

# Set the project directory
TARGET_DIR = r"D:\Investment Codes\Codes\Developement\SimFinFund"

# Set your API-key for downloading data.
# Load API key from file
API_KEY_FILE = os.path.join(TARGET_DIR, 'simfin_api_key.txt')
api_key = 'free'  # Default to free

if os.path.exists(API_KEY_FILE):
    try:
        with open(API_KEY_FILE, 'r') as f:
            read_key = f.read().strip()
            if read_key:
                api_key = read_key
                print("API key loaded successfully from file.")
            else:
                print(f"Warning: API key file {API_KEY_FILE} is empty. Using 'free' data.")
    except Exception as e:
        print(f"Warning: Error reading API key file: {e}. Using 'free' data.")
else:
    print(f"Warning: API key file {API_KEY_FILE} not found. Using 'free' data.")

sf.set_api_key(api_key)

# Set the local directory where data-files are stored.
# The directory will be created if it does not already exist.
data_dir = os.path.join(TARGET_DIR, 'simfin_data')
sf.set_data_dir(data_dir)
print(f"SimFin data directory set to: {data_dir}")

# Download the data from the SimFin server and load into a Pandas DataFrame.
df = sf.load_cashflow(variant='quarterly')

# Print the first rows of the data.
print(df.head())
