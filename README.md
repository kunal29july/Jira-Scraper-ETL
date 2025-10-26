# Apache Jira Scraper — Enhanced ETL Pipeline

This repository provides a **robust Python ETL pipeline** to extract issues from Apache Jira, transform them, and produce a JSONL corpus suitable for LLM training.

## Project Scope
- Scrapes Apache projects: **HADOOP, SPARK, KAFKA**
- Handles pagination, rate limits, retries with exponential backoff
- Enhanced checkpointing to resume interrupted runs
- Incremental updates to only fetch new/changed issues
- Text cleaning and normalization
- Derived tasks for LLM training (summarization, QA pairs, classification)
- Comprehensive logging and error handling

## System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  config.json│     │   main.py   │     │  worker.py  │
│  ---------- │     │  ---------- │     │  ---------- │
│Configuration│---->│ Orchestrator│<----│  Scheduler  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
         ┌─────────────────┴─────────────────┐
         │                                   │
┌────────▼───────┐                 ┌─────────▼────────┐
│   extract.py   │                 │  transformer.py  │
│  ------------- │                 │  --------------  │
│  Data Fetching │                 │ Data Processing  │
└────────┬───────┘                 └─────────┬────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│   data/raw/     │                 │ data/processed/ │
│  -------------- │                 │ --------------  │
│   Raw JSON      │                 │  JSONL Output   │
└─────────────────┘                 └─────────────────┘
```

### Data Flow
1. **Configuration Loading**: `main.py` loads settings from `config.json`
2. **Extraction**: `extract.py` fetches data from Jira API and saves to `data/raw/`
3. **Transformation**: `transformer.py` processes raw data and saves to `data/processed/`
4. **Scheduling**: `worker.py` manages periodic execution of the pipeline

## Key Features

### Extraction
- **Pagination**: Handles Jira's paginated results with checkpointing
- **Rate limiting**: Handles HTTP 429 responses with configurable sleep time
- **Error handling**: Uses exponential backoff for 5xx errors
- **Incremental updates**: Uses timestamps to only fetch changed issues

### Transformation
- **Advanced Text Cleaning**: Normalizes text, removes error logs, replaces URLs
- **Derived tasks**: Generates summarization, classification, and QA pairs
- **Data validation**: Ensures data quality and consistency

## Data Model

The pipeline produces JSONL files with the following structure:

```json
{
  "id": "HADOOP-123",
  "title": "Issue title",
  "description": "Detailed description...",
  "status": "Open",
  "priority": "Major",
  "reporter": "John Doe",
  "assignee": "Jane Smith",
  "created": "2025-01-01T12:34:56.789Z",
  "updated": "2025-01-15T12:34:56.789Z",
  "labels": ["bug", "performance"],
  "components": ["core", "io"],
  "comments": [
    {
      "author": "Alice",
      "body": "Comment text...",
      "created": "2025-01-02T12:34:56.789Z"
    }
  ],
  "derived_tasks": {
    "summary": "Concise summary of the issue",
    "classifications": ["bug", "performance"],
    "qa_pairs": [
      {
        "question": "How do I fix this bug?",
        "answer": "You need to update the library."
      }
    ]
  }
}
```

## Design Trade-offs

- **File-based Storage**: Simple, portable, compatible with LLM training pipelines
- **Sequential Processing**: Simpler implementation, lower resource usage
- **Page-level Checkpointing**: Balances overhead and recovery granularity
- **Rule-based Text Cleaning**: Fast, deterministic, transparent
- **Incremental Updates**: Reduces API load, faster subsequent runs

## Future Improvements

- Add parallel async requests (aiohttp) to speed up multiple project fetches
- Add a web dashboard for monitoring pipeline status
- Implement real-time data processing with message queues
- Add support for additional Jira projects and custom JQL queries
- Database integration for enterprise use (MySQL/PostgreSQL)
- Docker containerization for easier deployment
- Kubernetes deployment for scaling

## Setup and Usage

### Quick Setup (Linux)

```bash
# Navigate to the project directory
cd path/to/jira_scraper_project

# Make the script executable
chmod +x setup.sh

# Run the setup shell script
./setup.sh
```

### Manual Setup

```bash
# Navigate to the project directory
cd path/to/jira_scraper_project

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# Run the full pipeline
python main.py

# Run only extraction
python main.py --extract

# Run only transformation
python main.py --transform

# Process a specific project
python main.py --project HADOOP

# Clean checkpoint files to start fresh
python main.py --clean
```

### Scheduled Execution

```bash
# Run every 6 hours (default)
python worker.py

# Run every hour
python worker.py --interval 1
```

### Using Cron

```bash
# Edit your crontab
crontab -e

# Add this line to run every hour
0 * * * * cd /path/to/jira_scraper_project && python main.py >> /path/to/jira_scraper_project/data/cron.log 2>&1
```

### Using Make Commands

```bash
# Run the full pipeline
make

# Run only extraction or transformation
make extract
make transform

# Clean checkpoint files and run from scratch
make clean

# Run for a specific project
make project PROJECT=HADOOP

# Run the worker
make worker
make worker-interval INTERVAL=1
```

## Error Handling & Testing

- **Checkpointing**: Saves progress after each page of issues
- **Exponential backoff**: Retries with increasing delays for transient errors
- **Graceful degradation**: Continues processing even if some issues fail
- **Comprehensive logging**: Detailed logs for debugging
- **Unit tests**: Test suite for extraction and transformation components

Run tests with:
```bash
make test
```
