"""
main.py
Orchestrator: loads config, runs extraction and transformation.

Enhanced with:
- Better error handling and logging
- Command-line arguments for more flexibility
- Progress reporting
"""
import json
import os
import sys
import logging
import argparse
import time
from datetime import datetime
from extract import fetch_all_projects
from transformer import transform_all_projects, transform_project_to_jsonl

# Set up logging
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/main.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path="config.json"):
    """
    Load configuration from JSON file
    
    Example:
        config = load_config()
        # Returns the parsed config.json as a dictionary
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.info(f"Loaded configuration with {len(config.get('projects', []))} projects")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing config file: {e}")
        sys.exit(1)
    except IOError as e:
        logger.error(f"Error reading config file: {e}")
        sys.exit(1)

def setup_directories():
    """
    Create necessary directories for the ETL pipeline
    
    Example:
        setup_directories()
        # Creates data/raw, data/processed, and data/checkpoints directories
    """
    dirs = ["data/raw", "data/processed", "data/checkpoints", "data/logs"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.debug(f"Ensured directory exists: {d}")

def clean_data(specific_project=None):
    """
    Clean checkpoint files to start fresh
    
    Args:
        specific_project: If provided, only clean data for this project
        
    Example:
        clean_data()  # Cleans all checkpoint files
        clean_data("HADOOP")  # Cleans only HADOOP checkpoint files
    """
    import glob
    import os
    
    if specific_project:
        # Clean only specific project checkpoints
        checkpoint_files = glob.glob(f"data/checkpoints/{specific_project}.*")
        logger.info(f"Cleaning checkpoint files for project: {specific_project}")
    else:
        # Clean all checkpoint files
        checkpoint_files = glob.glob("data/checkpoints/*")
        logger.info("Cleaning all checkpoint files")
    
    # Delete checkpoint files
    for file in checkpoint_files:
        try:
            os.remove(file)
            logger.debug(f"Deleted checkpoint file: {file}")
        except Exception as e:
            logger.error(f"Error deleting file {file}: {e}")
    
    logger.info(f"Removed {len(checkpoint_files)} checkpoint files")

def parse_args():
    """
    Parse command-line arguments
    
    Example:
        args = parse_args()
        # Returns parsed arguments with extract, transform, and project flags
    """
    parser = argparse.ArgumentParser(description="Jira ETL Pipeline")
    parser.add_argument("--extract", action="store_true", help="Run extraction phase")
    parser.add_argument("--transform", action="store_true", help="Run transformation phase")
    parser.add_argument("--project", type=str, help="Process only a specific project")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--clean", action="store_true", help="Clean checkpoint files to start fresh")
    
    args = parser.parse_args()
    
    # If no flags specified, run both extract and transform
    if not (args.extract or args.transform):
        args.extract = True
        args.transform = True
        
    return args

def main(run_extract=True, run_transform=True, specific_project=None, config_path="config.json"):
    """
    Main orchestrator function
    
    Enhanced with:
    - Better error handling
    - Support for running specific phases
    - Support for processing a single project
    - Timing information
    
    Example:
        main(run_extract=True, run_transform=True)
        # Runs both extraction and transformation for all projects
        
        main(run_extract=False, run_transform=True, specific_project="HADOOP")
        # Runs only transformation for the HADOOP project
    """
    start_time = time.time()
    logger.info("Starting ETL pipeline")
    
    # Ensure directories exist
    setup_directories()
    
    # Load configuration
    cfg = load_config(config_path)
    
    # Filter to specific project if requested
    if specific_project:
        if specific_project in cfg.get("projects", []):
            cfg["projects"] = [specific_project]
            logger.info(f"Processing only project: {specific_project}")
        else:
            logger.error(f"Project {specific_project} not found in config")
            return False
    
    success = True
    
    # 1) Extract
    if run_extract:
        logger.info("Starting extraction phase")
        extract_start = time.time()
        try:
            success_count = fetch_all_projects(cfg)
            extract_time = time.time() - extract_start
            logger.info(f"Extraction completed in {extract_time:.2f} seconds")
            if success_count == 0:
                logger.warning("No projects were successfully extracted")
                success = False
        except Exception as e:
            logger.exception(f"Error during extraction phase: {e}")
            success = False

    # 2) Transform
    if run_transform and success:
        logger.info("Starting transformation phase")
        transform_start = time.time()
        try:
            projects = cfg.get("projects", [])
            total_issues = transform_all_projects(projects)
            transform_time = time.time() - transform_start
            logger.info(f"Transformation completed in {transform_time:.2f} seconds")
            logger.info(f"Processed {total_issues} total issues")
        except Exception as e:
            logger.exception(f"Error during transformation phase: {e}")
            success = False
    
    # Report total runtime
    total_time = time.time() - start_time
    logger.info(f"ETL pipeline completed in {total_time:.2f} seconds")
    
    return success

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Clean data if requested
    if args.clean:
        clean_data(args.project)
    
    # Run the pipeline with the specified options
    success = main(
        run_extract=args.extract,
        run_transform=args.transform,
        specific_project=args.project,
        config_path=args.config
    )
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
