"""
utils.py
Utility functions for the ETL pipeline.

Enhanced with:
- File operations (read/write JSON, JSONL)
- Data validation helpers
- Error handling utilities
- Timing and performance measurement
"""
import os
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, TypeVar, Union

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')

def save_json(path: str, data: Any, indent: int = 2) -> bool:
    """
    Save data as JSON to a file
    
    Args:
        path: File path to save to
        data: Data to save (must be JSON serializable)
        indent: Indentation level for pretty printing
        
    Returns:
        True if successful, False otherwise
        
    Example:
        save_json("data/config_backup.json", {"projects": ["HADOOP"]})
        # Saves the dictionary to data/config_backup.json
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {path}: {e}")
        return False

def load_json(path: str, default: Optional[T] = None) -> Union[Dict, List, T]:
    """
    Load JSON data from a file with error handling
    
    Args:
        path: File path to load from
        default: Default value to return if loading fails
        
    Returns:
        Loaded JSON data or default value if loading fails
        
    Example:
        config = load_json("config.json", default={})
        # Returns the parsed JSON or an empty dict if the file doesn't exist
    """
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading JSON from {path}: {e}")
        return default if default is not None else {}

def append_jsonl(path: str, data: Dict) -> bool:
    """
    Append a JSON object to a JSONL file
    
    Args:
        path: File path to append to
        data: JSON object to append
        
    Returns:
        True if successful, False otherwise
        
    Example:
        append_jsonl("data/logs.jsonl", {"timestamp": "2025-01-01", "message": "Log entry"})
        # Appends the JSON object as a new line in the JSONL file
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(data) + "\n")
        return True
    except Exception as e:
        logger.error(f"Error appending to JSONL file {path}: {e}")
        return False

def read_jsonl(path: str) -> List[Dict]:
    """
    Read a JSONL file into a list of dictionaries
    
    Args:
        path: File path to read from
        
    Returns:
        List of parsed JSON objects
        
    Example:
        records = read_jsonl("data/processed/HADOOP_issues.jsonl")
        # Returns a list of all JSON objects in the file
    """
    results = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    results.append(json.loads(line))
        return results
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading JSONL file {path}: {e}")
        return []

def compute_file_hash(path: str) -> Optional[str]:
    """
    Compute MD5 hash of a file
    
    Args:
        path: File path
        
    Returns:
        MD5 hash as hex string, or None if file doesn't exist
        
    Example:
        hash = compute_file_hash("data/raw/HADOOP_0.json")
        # Returns the MD5 hash of the file contents
    """
    if not os.path.exists(path):
        return None
        
    try:
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except IOError as e:
        logger.error(f"Error computing hash for {path}: {e}")
        return None

class Timer:
    """
    Simple timer for measuring execution time
    
    Example:
        with Timer() as t:
            # Do some work
            time.sleep(1)
        print(f"Operation took {t.elapsed:.2f} seconds")
    """
    
    def __init__(self, name: Optional[str] = None):
        self.name = name
        self.start_time = None
        self.elapsed = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        if self.name:
            logger.debug(f"Timer '{self.name}': {self.elapsed:.2f} seconds")

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,)) -> Callable:
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier (e.g., 2.0 means delay doubles each retry)
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(IOError,))
        def read_file(path):
            with open(path, 'r') as f:
                return f.read()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_attempts, delay
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    mtries -= 1
                    if mtries <= 0:
                        raise
                        
                    logger.warning(f"Retry: {func.__name__} failed: {e}. Retrying in {mdelay:.2f}s...")
                    time.sleep(mdelay)
                    mdelay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator

def ensure_dir(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists or was created, False otherwise
        
    Example:
        ensure_dir("data/processed")
        # Creates the directory if it doesn't exist
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False

def get_timestamp() -> str:
    """
    Get current timestamp in ISO format
    
    Returns:
        Current timestamp as string
        
    Example:
        timestamp = get_timestamp()
        # Returns something like "2025-01-15T12:34:56.789Z"
    """
    return datetime.utcnow().isoformat() + "Z"
