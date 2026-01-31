import json
import os
import tempfile
import time
import logging

logger = logging.getLogger("PhoenixState")

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")

def save_state(data: dict, filepath: str = STATE_FILE):
    """
    Saves data to a JSON file atomically (Write Temp -> Rename).
    This ensures the reader (API) never sees a half-written file.
    """
    try:
        # Add timestamp metadata
        data['_meta'] = {
            'updated_at': time.time(),
            'updated_iso': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Write to a temporary file first
        dir_name = os.path.dirname(filepath)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
            json.dump(data, tf, ensure_ascii=False)
            temp_name = tf.name
        
        # Atomic Rename (POSIX compliant)
        os.replace(temp_name, filepath)
        # logger.debug(f"State saved to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        if 'temp_name' in locals() and os.path.exists(temp_name):
            os.remove(temp_name)

def load_state(filepath: str = STATE_FILE) -> dict:
    """
    Reads the state JSON file.
    Returns empty dict if file doesn't exist or is corrupted.
    """
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return {}
