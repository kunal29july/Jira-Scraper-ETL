"""
extract.py
Handles Jira API extraction with pagination, retries, exponential backoff, and checkpointing.

Enhanced with:
- Better logging for debugging and monitoring
- Improved error handling with detailed error messages
- Enhanced checkpointing to track both pagination and last update time
- Support for incremental updates using Jira's updated timestamp
"""
import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

# Set up logging to both console and file
# This helps with debugging and monitoring the extraction process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/extraction.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# config will be loaded by main.py
HEADERS = {"User-Agent": "Kunal-Jira-Scraper/1.0"}

def load_json(path):
    """Load JSON data from a file"""
    with open(path, "r") as f:
        return json.load(f)

def save_raw_issues(project: str, start_at: int, issues: List[Dict]):
    """
    Save raw issue data to disk
    
    Example:
        save_raw_issues("HADOOP", 0, [{"id": "HADOOP-123", ...}, ...])
        # Creates file: data/raw/HADOOP_0.json
    """
    os.makedirs("data/raw", exist_ok=True)
    path = f"data/raw/{project}_{start_at}.json"
    with open(path, "w") as f:
        json.dump(issues, f, indent=2)
    logger.debug(f"Saved {len(issues)} issues to {path}")

def load_checkpoint(project: str) -> Dict[str, Any]:
    """
    Load checkpoint data for a project
    
    Enhanced to support both pagination (start_at) and incremental updates (last_updated)
    
    Returns:
        Dict with keys:
        - start_at: The next page to fetch
        - last_updated: ISO timestamp of the most recently updated issue
        
    Example:
        checkpoint = load_checkpoint("HADOOP")
        # Returns: {"start_at": 50, "last_updated": "2025-01-15T12:34:56.789Z"}
    """
    # First try to load the enhanced JSON checkpoint
    json_path = f"data/checkpoints/{project}.json"
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading JSON checkpoint for {project}: {e}")
    
    # Fall back to the legacy text checkpoint (for backward compatibility)
    legacy_path = f"data/checkpoints/{project}.txt"
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r") as f:
                start_at = int(f.read().strip())
                return {"start_at": start_at, "last_updated": None}
        except (ValueError, IOError) as e:
            logger.error(f"Error loading legacy checkpoint for {project}: {e}")
    
    # Default: start from beginning with no last_updated timestamp
    return {"start_at": 0, "last_updated": None}

def save_checkpoint(project: str, start_at: int, last_updated: Optional[str] = None):
    """
    Save checkpoint data for a project
    
    Enhanced to store both pagination position and last update timestamp
    
    Args:
        project: Project key (e.g., "HADOOP")
        start_at: Next page to fetch
        last_updated: ISO timestamp of the most recently updated issue
        
    Example:
        save_checkpoint("HADOOP", 50, "2025-01-15T12:34:56.789Z")
        # Creates file: data/checkpoints/HADOOP.json
    """
    os.makedirs("data/checkpoints", exist_ok=True)
    
    # If last_updated not provided, keep existing value
    if last_updated is None:
        checkpoint = load_checkpoint(project)
        last_updated = checkpoint.get("last_updated")
    
    # Save as JSON with both start_at and last_updated
    json_path = f"data/checkpoints/{project}.json"
    with open(json_path, "w") as f:
        json.dump({"start_at": start_at, "last_updated": last_updated}, f, indent=2)
    
    # Also update legacy checkpoint for backward compatibility
    legacy_path = f"data/checkpoints/{project}.txt"
    with open(legacy_path, "w") as f:
        f.write(str(start_at))

def fetch_issues_for_project(project_key: str, cfg: dict):
    """
    Fetches issues from Jira using pagination. Handles:
     - HTTP 429 (rate limit) by sleeping configured seconds
     - 5xx server errors with retry/backoff
     - Request exceptions with retry/backoff
     - Saves raw pages to disk and checkpoint to resume
     - Supports incremental updates using the 'updated' timestamp
     
    Enhanced with:
     - Better logging for debugging and monitoring
     - Improved error handling with detailed error messages
     - Support for incremental updates to only fetch new/changed issues
     - SSL verification can be disabled to handle certificate issues
     
    Example:
        # In config.json:
        # {
        #   "incremental": true,
        #   "lookback_days": 7,
        #   "max_results": 50,
        #   "verify_ssl": false
        # }
        
        fetch_issues_for_project("HADOOP", config)
        # This will fetch only issues updated in the last 7 days
        # or all issues if no previous checkpoint exists
    """
    base_url = "https://issues.apache.org/jira/rest/api/latest/search"
    max_results = cfg.get("max_results", 50)
    polite_delay = cfg.get("polite_delay_seconds", 2)
    rate_limit_sleep = cfg.get("rate_limit_sleep_seconds", 30)
    backoff_base = cfg.get("retry_backoff_base", 2)
    max_retries = cfg.get("max_retries", 5)
    
    # New config options for incremental updates
    incremental = cfg.get("incremental", False)
    lookback_days = cfg.get("lookback_days", 7)
    
    # SSL verification option (default to False to handle certificate issues)
    verify_ssl = cfg.get("verify_ssl", False)
    if not verify_ssl:
        logger.info(f"SSL certificate verification is disabled")
        # Suppress InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Load enhanced checkpoint with both pagination and last_updated info
    checkpoint = load_checkpoint(project_key)
    start_at = checkpoint.get("start_at", 0)
    last_updated = checkpoint.get("last_updated")
    
    # Track the latest update timestamp seen during this run
    latest_update_seen = None
    total = None

    # Build JQL query with incremental update if enabled
    jql = f"project={project_key}"
    if incremental and last_updated:
        # Use the last_updated timestamp from the checkpoint
        jql += f" AND updated >= '{last_updated.split('T')[0]}'"
        logger.info(f"[{project_key}] Running incremental update since {last_updated.split('T')[0]}")
    elif incremental:
        # No previous checkpoint, use lookback_days
        lookback_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        jql += f" AND updated >= '{lookback_date}'"
        logger.info(f"[{project_key}] No previous checkpoint, using lookback of {lookback_days} days (since {lookback_date})")

    logger.info(f"[{project_key}] Starting extraction with JQL: {jql}")
    
    # Print the URL and parameters for visibility
    full_url = f"{base_url}?jql={jql}&maxResults={max_results}&fields=*all"
    print(f"\n===== EXTRACTION URL =====")
    print(f"Base URL: {base_url}")
    print(f"JQL Query: {jql}")
    print(f"Full URL (example): {full_url}")
    print(f"===========================\n")

    while True:
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
            "fields": "*all"
        }

        attempt = 0
        while True:
            try:
                # Log the request attempt
                logger.debug(f"[{project_key}] Requesting page with startAt={start_at}, maxResults={max_results}")
                
                # Make the request with timeout and SSL verification option
                resp = requests.get(
                    base_url, 
                    params=params, 
                    headers=HEADERS, 
                    timeout=15,
                    verify=cfg.get("verify_ssl", False)  # Disable SSL verification by default
                )
                status = resp.status_code
                
                if status == 200:
                    # Success - parse the JSON response
                    data = resp.json()
                    
                    # Print the request URL for visibility
                    print(f"Request URL: {resp.url}")
                    break
                    
                elif status == 429:
                    # Rate limit hit — sleep a polite long time and retry
                    logger.warning(f"[{project_key}] Received 429 Rate Limit. Sleeping {rate_limit_sleep}s.")
                    time.sleep(rate_limit_sleep)
                    attempt += 1
                    
                elif 500 <= status < 600:
                    # Server error: backoff and retry with exponential backoff
                    wait = backoff_base ** attempt
                    logger.warning(f"[{project_key}] Server error {status}. Backing off {wait}s (attempt {attempt+1}/{max_retries+1}).")
                    time.sleep(wait)
                    attempt += 1
                    
                else:
                    # Unexpected status — log details and raise to outer exception handling
                    error_text = resp.text[:200]  # Limit to first 200 chars to avoid huge logs
                    logger.error(f"[{project_key}] Unexpected HTTP status {status}: {error_text}...")
                    resp.raise_for_status()
                    
            except requests.exceptions.Timeout:
                # Specific handling for timeouts
                wait = backoff_base ** attempt
                logger.warning(f"[{project_key}] Request timed out. Backing off {wait}s (attempt {attempt+1}/{max_retries+1}).")
                time.sleep(wait)
                attempt += 1
                
            except requests.exceptions.RequestException as e:
                # Network-level issue — exponential backoff retry
                if attempt >= max_retries:
                    logger.error(f"[{project_key}] Max retries exceeded for network error: {e}")
                    raise
                    
                wait = backoff_base ** attempt
                logger.warning(f"[{project_key}] Request Exception: {e}. Backing off {wait}s (attempt {attempt+1}/{max_retries+1}).")
                time.sleep(wait)
                attempt += 1

            # Check if we've exceeded max retries
            if attempt > max_retries:
                error_msg = f"Max retries exceeded for project {project_key} at startAt={start_at}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        issues = data.get("issues", [])
        total = data.get("total", total)
        
        if not issues:
            logger.info(f"[{project_key}] No issues returned for startAt={start_at}. Ending.")
            break

        # Log detailed information about the fetched issues
        logger.info(f"[{project_key}] Fetched {len(issues)} issues. Total issues: {total}")
        
        # Print summary of each issue for visibility
        print(f"\n===== FETCHED {len(issues)} ISSUES FROM {project_key} =====")
        for i, issue in enumerate(issues):
            key = issue.get("key", "UNKNOWN")
            summary = issue.get("fields", {}).get("summary", "No summary")
            status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            updated = issue.get("fields", {}).get("updated", "Unknown date")
            print(f"{i+1}. {key}: {summary[:50]}{'...' if len(summary) > 50 else ''} | Status: {status} | Updated: {updated}")
        print(f"================================================\n")
        
        # Print a sample of the raw data for the first issue (if available)
        if issues:
            sample_issue = issues[0]
            print(f"\n===== SAMPLE RAW DATA FOR {sample_issue.get('key')} =====")
            print(f"Issue Key: {sample_issue.get('key')}")
            print(f"Issue ID: {sample_issue.get('id')}")
            print(f"Self URL: {sample_issue.get('self')}")
            
            # Print fields available in the issue
            fields = sample_issue.get("fields", {})
            print("\nAvailable Fields:")
            for field_name in sorted(fields.keys()):
                field_value = fields.get(field_name)
                if isinstance(field_value, dict):
                    print(f"  - {field_name}: [Object]")
                elif isinstance(field_value, list):
                    print(f"  - {field_name}: [Array with {len(field_value)} items]")
                elif field_value is None:
                    print(f"  - {field_name}: null")
                elif isinstance(field_value, str) and len(field_value) > 50:
                    print(f"  - {field_name}: {field_value[:50]}...")
                else:
                    print(f"  - {field_name}: {field_value}")
            
            # Print sample of comments if available
            comments = fields.get("comment", {}).get("comments", [])
            if comments:
                print(f"\nSample Comment ({len(comments)} total):")
                comment = comments[0]
                print(f"  Author: {comment.get('author', {}).get('displayName')}")
                comment_body = comment.get('body', '')
                print(f"  Body: {comment_body[:100]}{'...' if len(comment_body) > 100 else ''}")
                print(f"  Created: {comment.get('created')}")
            
            print(f"================================================\n")
        
        # Log more detailed information about a sample issue
        if issues:
            sample = issues[0]
            logger.info(f"[{project_key}] Sample issue: {sample.get('key')} - {sample.get('fields', {}).get('summary')}")
            logger.debug(f"[{project_key}] Sample issue fields: {list(sample.get('fields', {}).keys())}")
            
            # Count comments for the sample issue
            comments = sample.get("fields", {}).get("comment", {}).get("comments", [])
            logger.info(f"[{project_key}] Sample issue has {len(comments)} comments")
            
            # Log labels and components
            labels = sample.get("fields", {}).get("labels", [])
            components = [c.get("name") for c in sample.get("fields", {}).get("components", [])]
            logger.info(f"[{project_key}] Sample issue labels: {labels}")
            logger.info(f"[{project_key}] Sample issue components: {components}")

        # Track the latest update timestamp for incremental updates
        for issue in issues:
            updated = issue.get("fields", {}).get("updated")
            if updated and (not latest_update_seen or updated > latest_update_seen):
                latest_update_seen = updated

        # Save raw page and checkpoint
        save_raw_issues(project_key, start_at, issues)
        start_at += len(issues)
        save_checkpoint(project_key, start_at, latest_update_seen)
        
        logger.info(f"[{project_key}] Fetched {len(issues)} issues. startAt now {start_at} / total {total}")
        
        # Example of what's being saved:
        # If we just fetched issues where the most recent update was "2025-01-15T12:34:56.789Z",
        # the checkpoint would now contain:
        # {"start_at": 50, "last_updated": "2025-01-15T12:34:56.789Z"}

        # Polite delay between requests to avoid hitting rate limits
        time.sleep(polite_delay)

        if total is not None and start_at >= total:
            logger.info(f"[{project_key}] Reached total {total}. Done.")
            break

def fetch_all_projects(cfg: dict):
    """
    Fetch all projects specified in the config
    
    Enhanced with better logging and error handling
    
    Example:
        # In config.json:
        # {
        #   "projects": ["HADOOP", "SPARK", "KAFKA"],
        #   "incremental": true
        # }
        
        fetch_all_projects(config)
        # This will fetch issues for all three projects
    """
    projects = cfg.get("projects", ["HADOOP"])
    success_count = 0
    
    logger.info(f"Starting extraction for {len(projects)} projects: {', '.join(projects)}")
    
    for p in projects:
        try:
            logger.info(f"Starting fetch for project: {p}")
            fetch_issues_for_project(p, cfg)
            success_count += 1
            logger.info(f"Successfully completed fetch for project: {p}")
        except Exception as e:
            logger.error(f"Failed fetching project {p}: {e}", exc_info=True)
    
    logger.info(f"Completed extraction: {success_count}/{len(projects)} projects successful")
    return success_count
