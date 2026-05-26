import json
import requests
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import ctypes
import winsound
import threading
import urllib3

# ---------------- PATH RESOLUTION ----------------
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_FILE = resource_path("config.json")
STATE_FILE = resource_path("seen_problems.json")

# ---------------- LOGGING SYSTEM ----------------
def setup_logging(log_level_str="INFO"):
    """
    Sets up industrial-grade rotating logging. 
    Prevents file bloating and tracks exact line errors.
    """
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Keeps max 5MB per file, rotates across 3 backup files
    handler = RotatingFileHandler(
        resource_path('notification_debug.log'), 
        maxBytes=5 * 1024 * 1024, 
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()  # Avoid handler duplication
    logger.addHandler(handler)

    # Forcefully constrain dependency noise to matching level
    logging.getLogger("requests").setLevel(level)
    logging.getLogger("urllib3").setLevel(level)
    logging.getLogger("urllib3.connectionpool").setLevel(level)

# ---------------- ERROR PARSER LOGIC ----------------
def get_json_error_context(file_path, exception):
    """
    Reads the file to extract the exact text line where the JSON error occurred
    and builds a visual code snippet pointer highlighting the syntax error.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        lineno = exception.lineno
        colno = exception.colno
        
        if 0 < lineno <= len(lines):
            error_line = lines[lineno - 1].rstrip('\n')
            # Generate visual caret spacing matching the mistake context
            pointer = " " * (colno - 1) + "^"
            return (
                f"\n File: {file_path}\n"
                f" Line {lineno}, Column {colno}:\n"
                f"----------------------------------------\n"
                f"{error_line}\n"
                f"{pointer}\n"
                f"----------------------------------------\n"
                f"Reason: {exception.msg}"
            )
    except Exception:
        pass
    return f"File: {file_path} | Error at line {exception.lineno}, col {exception.colno}: {exception.msg}"

# ---------------- CONFIG & STATE MANAGEMENT ----------------
def load_config():
    """ Safely loads and parses config.json, highlighting exact syntax failures visually """
    if not os.path.exists(CONFIG_FILE):
        logging.critical(f"FATAL: Configuration file missing at: {CONFIG_FILE}")
        sys.exit(1)
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        detailed_err = get_json_error_context(CONFIG_FILE, e)
        logging.critical(f"FATAL: Malformed JSON syntax configuration detected!{detailed_err}")
        show_notification("Config Syntax Error", f"Fix your config.json syntax:{detailed_err}")
        sys.exit(1)

def load_seen():
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except json.JSONDecodeError as e:
        detailed_err = get_json_error_context(STATE_FILE, e)
        logging.error(f"CORRUPTION WARNING: State tracking index file is broken!{detailed_err}")
        show_notification("State File Corrupted", f"seen_problems.json is invalid:\n{detailed_err}\n\nRe-seeding tracking database fresh.")
        return set()
    except Exception as e:
        logging.warning(f"Could not read state file ({e}). Starting fresh.")
        return set()

def save_seen(seen_ids):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(seen_ids), f, indent=2)
    except Exception as e:
        logging.error(f"Failed to write state tracking file: {e}")

# ---------------- DYNATRACE API ----------------
def fetch_open_problems(config):
    base_url = config["dynatrace"]["base_url"].rstrip("/")
    token = config["dynatrace"]["api_token"]
    
    app_settings = config.get("app_settings", {})
    ssl_verify = app_settings.get("ssl_verify", True)
    
    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {
        "Authorization": f"Api-Token {token}",
        "Accept": "application/json"
    }
    url = f"{base_url}/api/v2/problems"

    # --- THIS IS THE UPDATED FILTERING LOGIC ---
    filters = config.get("filters", {})
    management_zones = filters.get("management_zones") or filters.get("managementZones", [])

    if isinstance(management_zones, str):
        management_zones = [management_zones]

    problem_selector = 'status("open")'

    if management_zones:
        mz_filters = ",".join([f'"{mz}"' for mz in management_zones])
        problem_selector += f',managementZones({mz_filters})'
    # -------------------------------------------

    params = {
        "problemSelector": problem_selector,
        "pageSize": 500
    }

    logging.debug(f"API Outbound Call Request -> Params: {params} | SSL Verify: {ssl_verify}")

    resp = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
        verify=ssl_verify
    )
    
    resp.raise_for_status()
    return resp.json().get("problems", [])
# ---------------- NOTIFICATION WORKER ----------------
def show_notification(title, message):
    def popup():
        try:
            winsound.MessageBeep()
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            logging.info("Native OS popup notification sent successfully.")
        except Exception as e:
            logging.error(f"Failed to trigger system notification: {e}")

    threading.Thread(target=popup, daemon=True).start()

# ---------------- MONITORING ENGINE ----------------
def execution_cycle(config):
    """ Evaluates single running pass against Dynatrace endpoint """
    seen = load_seen()
    problems = fetch_open_problems(config)

    current_ids = {p["problemId"] for p in problems}
    new_problems = [p for p in problems if p["problemId"] not in seen]

    # --- FIRST STATE SEEDING ---
    if not seen:
        if problems:
            msg = f"{len(problems)} active structural problems discovered."
            show_notification("Dynatrace Monitor Hooked", msg)
            logging.info(f"Initial run completed. Indexed {len(problems)} existing items.")
        save_seen(current_ids)
        return

    # --- STEADY STATE (NO DRIFT) ---
    if not new_problems:
        logging.debug("Poll completed. 0 changes reported.")
        save_seen(current_ids)
        return

    # --- NEW CRITICAL ALERTS FOUND ---
    max_items = 5
    msg_lines = [
        f"• {p.get('title', 'No title')} [{p.get('displayId', 'N/A')}]"
        for p in new_problems[:max_items]
    ]
    msg = "\n".join(msg_lines)

    if len(new_problems) > max_items:
        msg += f"\n\n+ {len(new_problems) - max_items} additional occurrences reported..."

    show_notification("🚨 NEW Dynatrace Incidents!", msg)
    logging.info(f"Alert deployed for {len(new_problems)} fresh incidents.")
    save_seen(current_ids)

# ---------------- MAIN RUNNER LOOP ----------------
if __name__ == "__main__":
    # Boot bootstrap logging fallback (INFO level)
    setup_logging("INFO")
    
    # Run absolute root configuration checkpoint
    config = load_config()
    
    app_settings = config.get("app_settings", {})
    setup_logging(app_settings.get("log_level", "INFO"))
    
    polling_interval = app_settings.get("interval_seconds", 60)
    print(f" Monitor running. Polling interval: {polling_interval}s. Check logs for debug traces.")
    logging.info(f"Engine Initialization Successful. Target polling: {polling_interval}s.")

    while True:
        try:
            # Hot reload configuration adjustments safely
            config = load_config()
            execution_cycle(config)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Network / Connectivity pipeline fault: {req_err}")
        except Exception as loop_err:
            logging.error(f"Unexpected kernel loop execution exception: {loop_err}", exc_info=True)
            
        time.sleep(polling_interval)
