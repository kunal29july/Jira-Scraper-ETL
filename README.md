# Apache Jira Scraper — Enhanced ETL Pipeline

This repository provides a **robust Python ETL pipeline** to extract issues from Apache Jira, transform them, and produce a JSONL corpus suitable for LLM training. The pipeline is designed with fault tolerance, incremental updates, and data quality as primary considerations.

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

### Key Innovations

- **Advanced Text Cleaning Algorithm**: Our pipeline implements sophisticated pattern recognition to identify and remove error logs, stack traces, and other noise that would confuse LLM training, while preserving the valuable technical context.

- **Derived Task Generation**: Beyond simple extraction, we generate multiple derived tasks from each issue:
  - Automatic summarization that combines title and key description elements
  - Multi-label classification based on content analysis
  - Question-answer pair extraction from discussions

- **Fault-Tolerant Architecture**: The system is designed to handle real-world challenges like network failures, rate limiting, and malformed data with graceful degradation rather than complete failure.

- **Incremental Processing**: Our checkpoint system tracks both pagination position and timestamp of the most recently updated issue, enabling efficient resumption and incremental updates.

- **Automated Scheduling with Health Monitoring**: The worker component provides:
  - Configurable scheduled execution at regular intervals
  - Health check mechanism that tracks successful runs
  - Status reporting through a JSON status file
  - Graceful shutdown handling
  - Command-line configuration for flexible deployment

### Data Flow
1. **Configuration Loading**: `main.py` loads settings from `config.json`
2. **Extraction**: `extract.py` fetches data from Jira API and saves to `data/raw/`
3. **Transformation**: `transformer.py` processes raw data and saves to `data/processed/`
4. **Scheduling**: `worker.py` manages periodic execution of the pipeline

## Key Features

### Extraction
- **Pagination**: Handles Jira's paginated results with checkpointing
  - Uses `startAt` and `maxResults` parameters to fetch pages of issues
  - Saves checkpoint after each page to enable resumption
  - Tracks total issue count to determine when all pages have been fetched
- **Rate limiting**: Handles HTTP 429 responses with configurable sleep time
  - Automatically sleeps when rate limits are hit
  - Configurable delay between requests to avoid hitting limits
- **Error handling**: Uses exponential backoff for 5xx errors
  - Retries with increasing delays: `wait = backoff_base ** attempt`
  - Configurable maximum retry attempts
  - Detailed logging of all retry attempts
- **Incremental updates**: Uses timestamps to only fetch changed issues
  - Tracks last update timestamp in checkpoint files
  - Uses JQL filters like `updated >= "2025-01-01"` to fetch only changed issues
  - Configurable lookback period for first run

### Transformation
- **Advanced Text Cleaning**: 
  - Normalizes whitespace and newlines for consistent formatting
  - Removes error logs and stack traces using pattern recognition
  - Identifies and removes entire error blocks, not just individual lines
  - Replaces long CI system URLs with simple placeholders
  - Handles Jira-specific formatting artifacts
- **Derived tasks**: Generates additional data for LLM training:
  - **Summarization**: Creates concise summaries combining title and description
  - **Classification**: Multi-label classification based on issue type, summary, and labels
  - **QA pairs**: Extracts question-answer pairs from descriptions and comments
- **Data validation**: 
  - Validates all transformed records against schema
  - Checks for required fields and proper formatting
  - Validates date formats and field types
  - Gracefully handles malformed data

### Technical Implementation Details
- **HTTP Request Management**:
  - Uses `requests` library with session management
  - Configurable SSL verification (can be disabled in corporate environments)
  - Custom headers and authentication handling
- **JSON Processing**:
  - Efficient streaming JSON parsing for large responses
  - Handles nested JSON structures in Jira responses
  - Preserves original data while adding derived fields
- **File Operations**:
  - Atomic file writes to prevent corruption
  - Directory creation with proper error handling
  - JSONL format for easy streaming and processing

## Data Model

The pipeline produces JSONL files with the following structure:

```json
{
  "id": "HADOOP-123",
  "title": "Bug in parser",
  "description": "The JSON parser fails when given empty input.",
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
      "body": "I can reproduce this.",
      "created": "2025-01-02T12:34:56.789Z"
    }
  ],
  "derived_tasks": {
    "summary": "Bug in parser - The JSON parser fails when given empty input",
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

### Data Fields Explained

#### Core Fields
- **id**: Unique identifier from Jira (e.g., "HADOOP-123")
- **title**: Issue title/summary
- **description**: Full issue description with cleaned text
- **status**: Current issue status (e.g., "Open", "In Progress", "Resolved")
- **priority**: Issue priority (e.g., "Major", "Critical")
- **reporter**: Person who reported the issue
- **assignee**: Person assigned to the issue
- **created**: ISO 8601 timestamp of creation
- **updated**: ISO 8601 timestamp of last update
- **labels**: Array of labels applied to the issue
- **components**: Array of components affected by the issue

#### Comments
Array of comment objects with:
- **author**: Comment author name
- **body**: Cleaned comment text
- **created**: ISO 8601 timestamp of comment creation

#### Derived Tasks
- **summary**: Concise summary combining title and key description elements
- **classifications**: Array of classifications derived from issue content
- **qa_pairs**: Array of question-answer pairs extracted from description and comments

## Design Trade-offs

- **File-based Storage**: Simple, portable, compatible with LLM training pipelines
- **Sequential Processing**: Simpler implementation, lower resource usage
- **Page-level Checkpointing**: Balances overhead and recovery granularity
- **Rule-based Text Cleaning**: Fast, deterministic, transparent
- **Incremental Updates**: Reduces API load, faster subsequent runs

## Configuration Options

The `config.json` file provides extensive configuration options:

```json
{
  "jira_base_url": "https://issues.apache.org/jira",
  "projects": ["HADOOP", "SPARK", "KAFKA"],
  "max_results": 50,
  "polite_delay_seconds": 1,
  "rate_limit_sleep_seconds": 5,
  "backoff_base": 2,
  "max_attempts": 3,
  "incremental": true,
  "lookback_days": 7,
  "verify_ssl": false
}
```

### Configuration Parameters

- **jira_base_url**: Base URL for the Jira API
- **projects**: List of Jira project keys to extract
- **max_results**: Number of issues to fetch per page (max 100 for Jira)
- **polite_delay_seconds**: Delay between successful requests to avoid rate limits
- **rate_limit_sleep_seconds**: Time to sleep when hitting a rate limit (HTTP 429)
- **backoff_base**: Base for exponential backoff calculation
- **max_attempts**: Maximum number of retry attempts for failed requests
- **incremental**: Whether to use incremental updates based on timestamps
- **lookback_days**: Days to look back for the first run with incremental updates
- **verify_ssl**: Whether to verify SSL certificates (can be disabled in corporate environments)

## Error Handling & Fault Tolerance

The pipeline includes several mechanisms to ensure reliability:

- **Checkpointing**: 
  - Saves progress after each page of issues is processed
  - Stores both pagination position and last update timestamp
  - Enables efficient resumption after interruptions
  - Separate checkpoint files for each project

- **Exponential backoff**: 
  - Retries with increasing delays for transient errors
  - Formula: `wait = backoff_base ** attempt`
  - Configurable maximum attempts
  - Different handling for different error types (429 vs 5xx)

- **Graceful degradation**: 
  - Continues processing even if some issues fail
  - Skips problematic issues rather than failing the entire run
  - Records errors in logs for later investigation

- **Comprehensive logging**: 
  - Detailed logs for debugging and monitoring
  - Separate log files for extraction and transformation
  - Configurable log levels
  - Timestamps and context for all log entries

## Testing Framework

The project includes a comprehensive test suite to verify functionality:

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test interactions between components
- **Mock Tests**: Use mocks to simulate API responses and errors

### Test Coverage

- **Extraction Tests**:
  - Test pagination handling
  - Test rate limit handling
  - Test error handling and retries
  - Test checkpoint saving and loading
  - Test incremental updates

- **Transformation Tests**:
  - Test text cleaning functions
  - Test derived task generation
  - Test data validation
  - Test error handling during transformation

## Future Improvements

- Add parallel async requests (aiohttp) to speed up multiple project fetches
- Add a web dashboard for monitoring pipeline status
- Implement real-time data processing with message queues
- Add support for additional Jira projects and custom JQL queries
- Database integration for enterprise use (MySQL/PostgreSQL)
- Docker containerization for easier deployment
- Kubernetes deployment for scaling

## Setup and Usage

### Automatic Setup Scripts

The project includes automated setup scripts that handle all the necessary setup steps for you:

#### Linux Setup (setup.sh)

```bash
# Navigate to the project directory
cd path/to/jira_scraper_project

# Make the script executable
chmod +x setup.sh

# Run the setup shell script
./setup.sh
```

This script automatically:
1. Creates a Python virtual environment
2. Installs all required dependencies
3. Sets up necessary data directories
4. Handles SSL certificate issues in corporate environments
5. Provides instructions for activating the environment

The setup script includes error handling and will attempt alternative installation methods if the standard approach fails (such as using `--trusted-host` flags for SSL issues).

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

### Scheduled Execution with Worker

The worker component provides automated scheduling with health monitoring:

```bash
# Run every 6 hours (default)
python worker.py

# Run every hour
python worker.py --interval 1

# Skip the initial run at startup
python worker.py --no-initial-run
```

The worker process:
1. Runs the ETL pipeline immediately at startup (unless --no-initial-run is specified)
2. Schedules subsequent runs at the specified interval
3. Maintains a status file at `data/worker_status.json` with:
   - Last update timestamp
   - Worker uptime
   - Last successful run timestamp
   - Current health status
   - Status message
4. Handles graceful shutdown on SIGINT/SIGTERM signals
5. Provides detailed logging in `data/worker.log`

For production deployments, you can run the worker as a background process:

```bash
# Run as a background process
nohup python worker.py > /dev/null 2>&1 &
```

### Using Cron

```bash
# Edit your crontab
crontab -e

# Add this line to run every hour
cd /path/to/jira_scraper_project && python main.py >> /path/to/jira_scraper_project/data/cron.log 2>&1
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

### Running Tests

```bash
# Run all tests
make test

# Run specific test modules
make test-extract
make test-transform
```

The test suite uses Python's unittest framework and includes mocks for external dependencies to enable reliable testing without actual API calls.
