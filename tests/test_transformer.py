"""
test_transformer.py
Unit tests for the transformer module.

These tests verify the functionality of the transformation functions,
particularly focusing on text cleaning, derived task generation,
and issue validation.
"""
import sys
import os
import unittest
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transformer import (
    clean_text, 
    extract_qa_pairs, 
    generate_summary, 
    classify_issue,
    validate_issue,
    transform_issue
)

class TestCleanText(unittest.TestCase):
    """Tests for the clean_text function."""
    
    def test_none_input(self):
        """Test that None input returns an empty string."""
        self.assertEqual(clean_text(None), "")
    
    def test_empty_string(self):
        """Test that empty string input returns an empty string."""
        self.assertEqual(clean_text(""), "")
    
    def test_whitespace_removal(self):
        """Test that excessive whitespace is removed."""
        self.assertEqual(clean_text("  Hello  World  "), "Hello World")
    
    def test_newline_normalization(self):
        """Test that multiple newlines are normalized."""
        self.assertEqual(clean_text("Hello\n\n\nWorld"), "Hello World")
    
    def test_tab_replacement(self):
        """Test that tabs are replaced with spaces."""
        self.assertEqual(clean_text("Hello\tWorld"), "Hello World")
    

    
    def test_jira_formatting_removal(self):
        """Test that Jira formatting artifacts are removed."""
        self.assertEqual(clean_text("Hello {code}World{code}"), "Hello World")
        self.assertEqual(clean_text("Hello {noformat}World{noformat}"), "Hello World")
    
    def test_ci_url_replacement(self):
        """Test that CI URLs are replaced with a placeholder."""
        self.assertEqual(
            clean_text("Check https://ci-hadoop.apache.org/job/12345 for details."),
            "Check [CI_URL] for details."
        )
    


class TestExtractQAPairs(unittest.TestCase):
    """Tests for the extract_qa_pairs function."""
    
    def test_empty_inputs(self):
        """Test with empty inputs."""
        self.assertEqual(extract_qa_pairs("", []), [])
    
    def test_no_questions(self):
        """Test with description that has no questions."""
        self.assertEqual(extract_qa_pairs("This is a statement. This is another statement.", []), [])
    
    def test_questions_no_comments(self):
        """Test with questions but no comments."""
        self.assertEqual(extract_qa_pairs("How do I fix this bug?", []), [])
    
    


class TestGenerateSummary(unittest.TestCase):
    """Tests for the generate_summary function."""
    
    def test_title_only(self):
        """Test with only a title."""
        self.assertEqual(generate_summary("Bug in parser", ""), "Bug in parser")
    
    def test_title_and_description(self):
        """Test with title and description."""
        self.assertEqual(
            generate_summary("Bug in parser", "The JSON parser fails when given empty input."),
            "Bug in parser - The JSON parser fails when given empty input"
        )
    
    def test_description_starts_with_title(self):
        """Test when description starts with the title."""
        title = "Bug in parser"
        description = "Bug in parser when handling empty input."
        result = generate_summary(title, description)
        
        # Check that the result contains the full description
        self.assertTrue(description.startswith(result) or result.startswith(description))
    
    def test_long_summary_truncation(self):
        """Test that long summaries are truncated."""
        long_title = "A" * 100
        long_description = "B" * 100
        result = generate_summary(long_title, long_description, max_length=150)
        self.assertEqual(len(result), 150)
        self.assertTrue(result.endswith("..."))
    
    def test_real_world_example(self):
        """Test with a real-world example from Jira."""
        title = "S3A: retry on MPU completion failure"
        description = "Experienced transient failure in test run: all MPU complete posts failed because the request or parts were not found. The tests started succeeding 60-90s later."
        
        result = generate_summary(title, description)
        
        # Check that the result contains both the title and the first part of the description
        self.assertIn(title, result)
        self.assertIn("Experienced transient failure", result)
        self.assertIn("MPU complete posts failed", result)


class TestClassifyIssue(unittest.TestCase):
    """Tests for the classify_issue function."""
    
    def test_empty_issue(self):
        """Test with an empty issue."""
        self.assertEqual(classify_issue({}), [])
    
    def test_issue_type_classification(self):
        """Test classification based on issue type."""
        issue = {"fields": {"issuetype": {"name": "Bug"}}}
        self.assertEqual(classify_issue(issue), ["bug"])
    
    def test_summary_classification(self):
        """Test classification based on summary."""
        issue = {"fields": {"summary": "Fix memory leak in cache"}}
        result = classify_issue(issue)
        self.assertIn("bug", result)
    
    def test_labels_classification(self):
        """Test classification based on labels."""
        issue = {"fields": {"labels": ["performance", "security"]}}
        result = classify_issue(issue)
        self.assertIn("performance", result)
        self.assertIn("security", result)
    
    def test_multiple_classifications(self):
        """Test multiple classifications."""
        issue = {
            "fields": {
                "issuetype": {"name": "Improvement"},
                "summary": "Fix performance issue",
                "labels": ["performance", "bug"]
            }
        }
        result = classify_issue(issue)
        self.assertIn("improvement", result)
        self.assertIn("performance", result)
        self.assertIn("bug", result)
        # Check for no duplicates
        self.assertEqual(len(result), 3)
    
    def test_real_world_example(self):
        """Test with a real-world example from Jira."""
        issue = {
            "fields": {
                "issuetype": {"name": "Bug"},
                "summary": "S3A: retry on MPU completion failure",
                "description": "Experienced transient failure in test run...",
                "labels": ["s3", "reliability"]
            }
        }
        result = classify_issue(issue)
        self.assertIn("bug", result)


class TestValidateIssue(unittest.TestCase):
    """Tests for the validate_issue function."""
    
    def test_valid_issue(self):
        """Test with a valid issue."""
        issue = {
            "id": "HADOOP-123",
            "title": "Bug in parser",
            "description": "The JSON parser fails when given empty input.",
            "status": "Open",
            "priority": "Major",
            "reporter": "John Doe",
            "assignee": "Jane Smith",
            "created": "2025-01-01T12:34:56.789Z",
            "updated": "2025-01-15T12:34:56.789Z",
            "comments": [
                {
                    "author": "Alice",
                    "body": "I can reproduce this.",
                    "created": "2025-01-02T12:34:56.789Z"
                }
            ]
        }
        is_valid, errors = validate_issue(issue)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
    
    def test_missing_required_fields(self):
        """Test with missing required fields."""
        issue = {
            "description": "The JSON parser fails when given empty input.",
            "status": "Open"
        }
        is_valid, errors = validate_issue(issue)
        self.assertFalse(is_valid)
        self.assertIn("Missing issue ID", errors)
        self.assertIn("Missing or empty title", errors)
    
    def test_malformed_dates(self):
        """Test with malformed dates."""
        issue = {
            "id": "HADOOP-123",
            "title": "Bug in parser",
            "created": "2025-01-01",  # Missing time component
            "updated": "invalid date"
        }
        is_valid, errors = validate_issue(issue)
        self.assertFalse(is_valid)
        
        # Check that the errors contain messages about malformed dates
        date_errors = [error for error in errors if "Malformed date" in error]
        self.assertTrue(len(date_errors) >= 2)
        
        # Check that both created and updated dates are mentioned in the errors
        created_errors = [error for error in errors if "created" in error]
        updated_errors = [error for error in errors if "updated" in error]
        self.assertTrue(len(created_errors) > 0)
        self.assertTrue(len(updated_errors) > 0)
    
    def test_empty_comment_body(self):
        """Test with empty comment body."""
        issue = {
            "id": "HADOOP-123",
            "title": "Bug in parser",
            "comments": [
                {"author": "Alice", "body": ""},
                {"author": "Bob", "body": "This is a comment."}
            ]
        }
        is_valid, errors = validate_issue(issue)
        self.assertFalse(is_valid)
        self.assertIn("Empty comment body at index 0", errors)


class TestTransformIssue(unittest.TestCase):
    """Tests for the transform_issue function."""
    
    def test_basic_transformation(self):
        """Test basic transformation of an issue."""
        raw_issue = {
            "key": "HADOOP-123",
            "fields": {
                "summary": "Bug in parser",
                "description": "The JSON parser fails when given empty input.",
                "status": {"name": "Open"},
                "priority": {"name": "Major"},
                "reporter": {"displayName": "John Doe"},
                "assignee": {"displayName": "Jane Smith"},
                "created": "2025-01-01T12:34:56.789Z",
                "updated": "2025-01-15T12:34:56.789Z",
                "labels": ["bug", "parser"],
                "components": [{"name": "core"}, {"name": "io"}],
                "comment": {
                    "comments": [
                        {
                            "author": {"displayName": "Alice"},
                            "body": "I can reproduce this.",
                            "created": "2025-01-02T12:34:56.789Z"
                        }
                    ]
                }
            }
        }
        
        result = transform_issue(raw_issue)
        
        self.assertEqual(result["id"], "HADOOP-123")
        self.assertEqual(result["title"], "Bug in parser")
        self.assertEqual(result["description"], "The JSON parser fails when given empty input.")
        self.assertEqual(result["status"], "Open")
        self.assertEqual(result["priority"], "Major")
        self.assertEqual(result["reporter"], "John Doe")
        self.assertEqual(result["assignee"], "Jane Smith")
        self.assertEqual(result["created"], "2025-01-01T12:34:56.789Z")
        self.assertEqual(result["updated"], "2025-01-15T12:34:56.789Z")
        self.assertEqual(result["labels"], ["bug", "parser"])
        self.assertEqual(result["components"], ["core", "io"])
        
        self.assertEqual(len(result["comments"]), 1)
        self.assertEqual(result["comments"][0]["author"], "Alice")
        self.assertEqual(result["comments"][0]["body"], "I can reproduce this.")
        self.assertEqual(result["comments"][0]["created"], "2025-01-02T12:34:56.789Z")
        
        self.assertIn("derived_tasks", result)
        self.assertIn("summary", result["derived_tasks"])
        self.assertIn("classifications", result["derived_tasks"])
        self.assertIn("qa_pairs", result["derived_tasks"])
    
    def test_empty_issue(self):
        """Test transformation of an empty issue."""
        result = transform_issue({})
        # The function returns an empty dictionary for empty input
        self.assertEqual(result, {})
    
    def test_error_handling(self):
        """Test error handling during transformation."""
        # Create a raw issue that will cause an error during transformation
        raw_issue = {
            "key": "HADOOP-123",
            "fields": {
                "summary": "Bug in parser",
                "description": "The JSON parser fails when given empty input.",
                "status": None,  # This will cause an error when trying to access status["name"]
                "priority": {"name": "Major"}
            }
        }
        
        # The function should not raise an exception
        try:
            result = transform_issue(raw_issue)
            
            # Check that the basic fields are still extracted
            self.assertEqual(result["id"], "HADOOP-123")
            self.assertEqual(result["title"], "Bug in parser")
            
            # Check that the status is set to a default value
            self.assertEqual(result["status"], "Unknown")
        except Exception as e:
            self.fail(f"transform_issue raised an exception: {e}")
    
    def test_real_world_example(self):
        """Test with a real-world example from Jira."""
        # Create a sample raw issue
        raw_issue = {
            "key": "HADOOP-123",
            "fields": {
                "summary": "Bug in parser",
                "description": "The JSON parser fails when given empty input.",
                "status": {"name": "Open"},
                "priority": {"name": "Major"},
                "reporter": {"displayName": "John Doe"},
                "assignee": {"displayName": "Jane Smith"},
                "created": "2025-01-01T12:34:56.789Z",
                "updated": "2025-01-15T12:34:56.789Z",
                "labels": ["bug", "parser"],
                "components": [{"name": "core"}, {"name": "io"}],
                "comment": {
                    "comments": [
                        {
                            "author": {"displayName": "Alice"},
                            "body": "I can reproduce this.",
                            "created": "2025-01-02T12:34:56.789Z"
                        }
                    ]
                }
            }
        }
        
        # Transform the issue
        result = transform_issue(raw_issue)
        
        # Verify the result
        self.assertIsNotNone(result["id"])
        self.assertIsNotNone(result["title"])
        self.assertIn("derived_tasks", result)


if __name__ == "__main__":
    unittest.main()
