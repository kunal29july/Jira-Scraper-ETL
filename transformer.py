"""
transformer.py
Transforms raw Jira issue pages (saved JSON) into cleaned JSONL records for LLM training.

Enhanced with:
- Text cleaning and normalization
- More derived tasks for LLM training (summarization, QA pairs)
- Better handling of edge cases (malformed fields, missing values)
- Data validation
- Improved logging
"""
import glob
import json
import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/transformation.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text fields
    
    - Handles None values
    - Removes excessive whitespace
    - Normalizes line endings
    - Removes common noise patterns
    - Filters out error logs and stack traces
    - Converts newlines to spaces for plain text output
    
    Example:
        clean_text("  This is a\n\n\ntext with   spaces  ")
        # Returns: "This is a text with spaces"
    """
    if text is None:
        return ""
    
    # Filter out common error log patterns
    # This helps remove stack traces and error logs that aren't useful for LLM training
    
    # Remove lines starting with common error indicators
    lines = text.split('\n')
    filtered_lines = []
    in_error_block = False
    
    for line in lines:
        # Skip lines that look like error logs or stack traces
        if (re.match(r'^\[ERROR\]|^Exception|^at\s+[\w\.]+|^\s+at\s+[\w\.]+|^Caused by:|^\s+\.\.\.\s+\d+\s+more|^java\.|\u00bb', line) or
            re.match(r'^\s*\w+(\.\w+)+(Exception|Error):', line)):
            in_error_block = True
            continue
            
        # If we see a line that doesn't look like part of an error block, reset the flag
        if in_error_block and line.strip() and not line.startswith(' '):
            in_error_block = False
            
        # Only include lines that aren't part of error blocks
        if not in_error_block:
            # Clean the line: remove carriage returns and trim whitespace
            clean_line = line.replace('\r', '').strip()
            if clean_line:  # Only add non-empty lines
                filtered_lines.append(clean_line)
    
    # Join the filtered lines with spaces instead of newlines for plain text output
    text = ' '.join(filtered_lines)
    
    # Replace tabs with spaces
    text = text.replace('\t', ' ')
    
    # Remove excessive spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove common Jira/Markdown formatting artifacts
    text = re.sub(r'\{code.*?\}|\{noformat\}', '', text)
    
    # Remove URLs that are likely pointing to error logs or CI systems
    text = re.sub(r'https?://ci-hadoop\.apache\.org/job/\S+', '[CI_URL]', text)
    
    # Trim whitespace
    return text.strip()

def extract_qa_pairs(description: str, comments: List[Dict]) -> List[Dict]:
    """
    Extract potential question-answer pairs from issue description and comments
    
    Example:
        extract_qa_pairs("How do I fix this bug?", [{"body": "You need to update the library."}])
        # Returns: [{"question": "How do I fix this bug?", "answer": "You need to update the library."}]
    """
    qa_pairs = []
    
    # Look for question patterns in description
    questions = re.findall(r'([^.!?]+\?)', description)
    
    # For each question, try to find an answer in the comments
    for question in questions:
        for comment in comments:
            body = comment.get("body", "")
            if body and len(body) > 10:  # Simple heuristic for a meaningful answer
                qa_pairs.append({
                    "question": question.strip(),
                    "answer": clean_text(body)
                })
                break  # Use the first comment that could be an answer
    
    return qa_pairs

def generate_summary(title: str, description: str, max_length: int = 150) -> str:
    """
    Generate a concise summary of the issue
    
    Example:
        generate_summary("Bug in parser", "The JSON parser fails when given empty input.")
        # Returns: "Bug in JSON parser that fails when given empty input."
    """
    # Start with the title
    summary = title
    
    # If description is available, extract the first sentence or first N characters
    if description:
        # Get first sentence if available
        first_sentence = re.split(r'[.!?]', description)[0]
        
        if first_sentence and len(first_sentence) > 5:
            # Combine title and first sentence
            if first_sentence.lower().startswith(title.lower()):
                summary = first_sentence
            else:
                summary = f"{title} - {first_sentence}"
    
    # Truncate if too long
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
        
    return summary

def classify_issue(raw_issue: Dict) -> List[str]:
    """
    Classify the issue into multiple categories
    
    Example:
        classify_issue({"fields": {"summary": "Fix memory leak", "labels": ["performance"]}})
        # Returns: ["bug", "performance"]
    """
    fields = raw_issue.get("fields", {})
    summary = fields.get("summary", "").lower()
    description = fields.get("description", "").lower() if fields.get("description") else ""
    labels = [l.lower() for l in fields.get("labels", [])]
    issue_type = fields.get("issuetype", {}).get("name", "").lower()
    
    classifications = []
    
    # Use issue type if available
    if issue_type:
        classifications.append(issue_type)
    
    # Check for bug indicators
    if "bug" in summary or "fix" in summary or "error" in summary or "fail" in summary:
        classifications.append("bug")
    
    # Check for feature indicators
    if "feature" in summary or "add" in summary or "implement" in summary or "new" in summary:
        classifications.append("feature")
    
    # Check for improvement indicators
    if "improve" in summary or "enhance" in summary or "refactor" in summary or "update" in summary:
        classifications.append("improvement")
    
    # Check for performance indicators
    if "performance" in summary or "slow" in summary or "fast" in summary or "speed" in summary:
        classifications.append("performance")
    
    # Add relevant labels
    for label in labels:
        if label in ["bug", "feature", "improvement", "performance", "security", "documentation"]:
            classifications.append(label)
    
    # Remove duplicates and return
    return list(set(classifications))

def validate_issue(transformed: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a transformed issue record
    
    Returns:
        Tuple of (is_valid, list_of_errors)
        
    Example:
        validate_issue({"id": "HADOOP-123", "title": ""})
        # Returns: (False, ["Missing or empty title"])
    """
    errors = []
    
    # Check required fields
    if not transformed.get("id"):
        errors.append("Missing issue ID")
    
    if not transformed.get("title"):
        errors.append("Missing or empty title")
    
    # Check for malformed dates
    for date_field in ["created", "updated"]:
        date_value = transformed.get(date_field)
        if date_value and not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_value):
            errors.append(f"Malformed date in {date_field}: {date_value}")
    
    # Check comments structure
    comments = transformed.get("comments", [])
    for i, comment in enumerate(comments):
        if not comment.get("body"):
            errors.append(f"Empty comment body at index {i}")
    
    return len(errors) == 0, errors

def transform_issue(raw_issue: Dict) -> Dict:
    """
    Transform a raw Jira issue into a structured format for LLM training
    
    Enhanced with:
    - Better text cleaning
    - More derived tasks (summarization, QA pairs, multi-label classification)
    - Improved handling of edge cases
    
    Example:
        transform_issue({"key": "HADOOP-123", "fields": {...}})
        # Returns a cleaned and enhanced issue record
    """
    if not raw_issue:
        logger.warning("Received empty issue to transform")
        return {}
        
    issue_key = raw_issue.get("key", "UNKNOWN")
    
    try:
        fields = raw_issue.get("fields", {})
        comments = fields.get("comment", {}).get("comments", [])
        
        # Clean and normalize text fields
        summary = clean_text(fields.get("summary"))
        description = clean_text(fields.get("description"))
        
        # Extract basic metadata with fallbacks for missing fields
        status = fields.get("status", {}).get("name") if fields.get("status") else "Unknown"
        priority = fields.get("priority", {}).get("name") if fields.get("priority") else None
        reporter = fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None
        assignee = fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None
        
        # Clean and structure comments
        cleaned_comments = []
        for c in comments:
            if not c:
                continue
                
            cleaned_comments.append({
                "author": c.get("author", {}).get("displayName") if c.get("author") else "Unknown",
                "body": clean_text(c.get("body")),
                "created": c.get("created")
            })
        
        # Generate derived tasks for LLM training
        classifications = classify_issue(raw_issue)
        issue_summary = generate_summary(summary, description)
        qa_pairs = extract_qa_pairs(description, cleaned_comments)
        
        # Create the transformed record
        transformed = {
            "id": issue_key,
            "title": summary,
            "description": description,
            "status": status,
            "priority": priority,
            "reporter": reporter,
            "assignee": assignee,
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "labels": fields.get("labels", []),
            "components": [c.get("name") for c in fields.get("components", [])] if fields.get("components") else [],
            "comments": cleaned_comments,
            "derived_tasks": {
                "summary": issue_summary,
                "classifications": classifications,
                "qa_pairs": qa_pairs
            }
        }
        
        # Validate the transformed record
        is_valid, errors = validate_issue(transformed)
        if not is_valid:
            logger.warning(f"Issue {issue_key} has validation errors: {', '.join(errors)}")
        
        return transformed
        
    except Exception as e:
        logger.error(f"Error transforming issue {issue_key}: {e}", exc_info=True)
        # Return a minimal record so processing can continue
        return {
            "id": issue_key,
            "error": str(e),
            "title": raw_issue.get("fields", {}).get("summary", "Error during transformation"),
            "derived_tasks": {
                "summary": "Error during transformation",
                "classifications": ["error"]
            }
        }

def find_raw_files_for_project(project: str) -> List[str]:
    """
    Find all raw JSON files for a project
    
    Example:
        find_raw_files_for_project("HADOOP")
        # Returns: ["data/raw/HADOOP_0.json", "data/raw/HADOOP_50.json", ...]
    """
    pattern = f"data/raw/{project}_*.json"
    files = sorted(glob.glob(pattern))
    logger.debug(f"Found {len(files)} raw files for project {project}")
    return files

def transform_project_to_jsonl(project: str) -> int:
    """
    Transform all raw files for a project into a single JSONL file
    
    Enhanced with:
    - Better error handling
    - Progress reporting
    - Validation statistics
    
    Example:
        transform_project_to_jsonl("HADOOP")
        # Processes all HADOOP raw files and creates data/processed/HADOOP_issues.jsonl
    """
    raw_files = find_raw_files_for_project(project)
    if not raw_files:
        logger.warning(f"No raw files found for project {project} — nothing to transform.")
        return 0

    os.makedirs("data/processed", exist_ok=True)
    out_path = f"data/processed/{project}_issues.jsonl"
    
    # Statistics for reporting
    count = 0
    error_count = 0
    validation_errors = 0
    
    logger.info(f"Starting transformation for project {project} with {len(raw_files)} raw files")
    print(f"\n===== STARTING TRANSFORMATION FOR {project} =====")
    print(f"Found {len(raw_files)} raw files to process")
    
    with open(out_path, "w") as out_f:
        for i, rf in enumerate(raw_files):
            try:
                with open(rf, "r") as f:
                    issues = json.load(f)
                
                file_count = 0
                for issue in issues:
                    try:
                        # Print basic info about the issue being transformed
                        key = issue.get("key", "UNKNOWN")
                        summary = issue.get("fields", {}).get("summary", "No summary")
                        print(f"Transforming issue: {key} - {summary[:50]}{'...' if len(summary) > 50 else ''}")
                        
                        record = transform_issue(issue)
                        
                        # Check if transformation resulted in error
                        if "error" in record:
                            error_count += 1
                            print(f"  [ERROR] Transforming issue {key}: {record.get('error')}")
                        
                        # Check for validation errors
                        is_valid, errors = validate_issue(record)
                        if not is_valid:
                            validation_errors += 1
                            print(f"  [WARNING] Validation issues for {key}: {', '.join(errors)}")
                        else:
                            print(f"  [SUCCESS] Transformed issue {key}")
                            
                            # Print some details about the transformed record
                            qa_pairs = len(record.get("derived_tasks", {}).get("qa_pairs", []))
                            classifications = record.get("derived_tasks", {}).get("classifications", [])
                            print(f"     - Generated {qa_pairs} QA pairs")
                            print(f"     - Classifications: {', '.join(classifications) if classifications else 'None'}")
                        
                        # Write to output file
                        out_f.write(json.dumps(record) + "\n")
                        count += 1
                        file_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing issue in file {rf}: {e}", exc_info=True)
                        error_count += 1
                
                # Log progress every few files
                if (i + 1) % 5 == 0 or i == len(raw_files) - 1:
                    logger.info(f"Processed {i+1}/{len(raw_files)} files for {project} ({count} issues so far)")
                else:
                    logger.debug(f"Processed file {rf} with {file_count} issues")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in file {rf}: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error processing file {rf}: {e}", exc_info=True)
                error_count += 1
    
    # Log final statistics
    logger.info(f"Transformed {count} issues for project {project} -> {out_path}")
    logger.info(f"Statistics for {project}: {error_count} errors, {validation_errors} validation warnings")
    
    # Print summary for user visibility
    print(f"\n===== TRANSFORMATION COMPLETE FOR {project} =====")
    print(f"Processed {count} issues")
    print(f"Errors: {error_count}")
    print(f"Validation warnings: {validation_errors}")
    print(f"Output file: {out_path}")
    print(f"================================================\n")
    
    return count

def transform_all_projects(projects: list) -> int:
    """
    Transform all projects in the list
    
    Enhanced with better logging and error handling
    
    Example:
        transform_all_projects(["HADOOP", "SPARK", "KAFKA"])
        # Transforms all three projects and returns the total number of issues
    """
    total = 0
    success_count = 0
    
    logger.info(f"Starting transformation for {len(projects)} projects: {', '.join(projects)}")
    
    for p in projects:
        try:
            logger.info(f"Starting transformation for project: {p}")
            project_count = transform_project_to_jsonl(p)
            total += project_count
            success_count += 1
            logger.info(f"Successfully completed transformation for project: {p}")
        except Exception as e:
            logger.error(f"Failed transforming project {p}: {e}", exc_info=True)
    
    logger.info(f"Completed transformation: {success_count}/{len(projects)} projects successful, {total} total issues")
    return total
