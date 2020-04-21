import json
import os

current_dir = os.path.dirname(__file__)
config_file_path = os.path.join(current_dir, '../config.json')
with open(config_file_path) as file:
    CONFIG = json.load(file)

TOKEN_KEY = CONFIG["token_secret_key"]
GMAIL_APP_PASSWORD = CONFIG["GMAIL_APP_PASSWORD"]

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ROOT_DATABASE_PATH = os.path.join(current_dir, CONFIG['ROOT_RELATIVE_PATH'])
USER_DATABASE_PATH = os.path.join(current_dir, CONFIG['USER_RELATIVE_PATH'])
ROOT_TABLES_SCRIPT_PATH = os.path.join(current_dir, 'root_tables.sql')
