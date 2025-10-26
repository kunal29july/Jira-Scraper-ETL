"""
worker.py
Runs the ETL pipeline at regular intervals using schedule.

Enhanced with:
- Better logging and error handling
- Command-line arguments for configuration
- Health check mechanism
- Status reporting
"""
import schedule
import time
import logging
import os
import argparse
import json
import signal
import sys
from datetime import datetime, timedelta
from main import main, load_config

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/worker.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state for health check
last_successful_run = None
worker_start_time = None

def update_status(success=True, message=""):
    """
    Update the worker status file
    
    Example:
        update_status(True, "Job completed successfully")
        # Updates data/worker_status.json with success status and timestamp
    """
    global last_successful_run
    
    if success:
        last_successful_run = datetime.now()
    
    status = {
        "last_update": datetime.now().isoformat(),
        "worker_uptime": str(datetime.now() - worker_start_time) if worker_start_time else "unknown",
        "last_successful_run": last_successful_run.isoformat() if last_successful_run else None,
        "status": "healthy" if success else "error",
        "message": message
    }
    
    try:
        with open("data/worker_status.json", "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update status file: {e}")

def job():
    """
    Run the ETL pipeline job
    
    Enhanced with:
    - Better error handling
    - Status reporting
    - Timing information
    """
    job_start = datetime.now()
    logger.info(f"Starting scheduled job at {job_start.isoformat()}")
    update_status(True, "Job started")
    
    try:
        # Run the ETL pipeline
        success = main(run_extract=True, run_transform=True)
        
        # Update status based on result
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()
        
        if success:
            message = f"Job completed successfully in {duration:.2f} seconds"
            logger.info(message)
            update_status(True, message)
        else:
            message = f"Job completed with errors in {duration:.2f} seconds"
            logger.warning(message)
            update_status(False, message)
            
    except Exception as e:
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()
        message = f"Job failed after {duration:.2f} seconds: {str(e)}"
        logger.exception(message)
        update_status(False, message)

def parse_args():
    """
    Parse command-line arguments
    
    Example:
        args = parse_args()
        # Returns parsed arguments with interval and config options
    """
    parser = argparse.ArgumentParser(description="Jira ETL Pipeline Worker")
    parser.add_argument("--interval", type=int, default=6, help="Job interval in hours")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--no-initial-run", action="store_true", help="Skip initial run at startup")
    return parser.parse_args()

def setup_signal_handlers():
    """
    Set up signal handlers for graceful shutdown
    """
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, exiting gracefully")
        update_status(True, "Worker stopped gracefully")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def run_worker(interval_hours=6, config_path="config.json", skip_initial_run=False):
    """
    Run the worker process that schedules ETL jobs
    
    Enhanced with:
    - Better logging
    - Status reporting
    - Signal handling for graceful shutdown
    
    Example:
        run_worker(interval_hours=12)
        # Runs the ETL pipeline every 12 hours
    """
    global worker_start_time
    worker_start_time = datetime.now()
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Log worker start
    logger.info(f"Worker starting at {worker_start_time.isoformat()}")
    logger.info(f"Job interval: {interval_hours} hours")
    
    # Load config to validate it
    try:
        cfg = load_config(config_path)
        projects = cfg.get("projects", [])
        logger.info(f"Configured to process {len(projects)} projects: {', '.join(projects)}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        update_status(False, f"Failed to load configuration: {e}")
        return
    
    # Initialize status
    update_status(True, "Worker started")
    
    # Run once at startup (unless skipped)
    if not skip_initial_run:
        logger.info("Running initial job at startup")
        job()
    else:
        logger.info("Skipping initial job at startup")
    
    # Schedule regular jobs
    schedule.every(interval_hours).hours.do(job)
    logger.info(f"Scheduled next job at {(datetime.now() + timedelta(hours=interval_hours)).isoformat()}")

    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except Exception as e:
        logger.exception(f"Worker loop failed: {e}")
        update_status(False, f"Worker loop failed: {e}")

if __name__ == "__main__":
    args = parse_args()
    run_worker(
        interval_hours=args.interval,
        config_path=args.config,
        skip_initial_run=args.no_initial_run
    )
