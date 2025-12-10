#!/usr/bin/env python3
"""
Re-scoring Utility Script
Re-run JEF scoring on existing TestResult records.

Usage:
    python utils/rescore_results.py [--all] [--result-id ID]

Options:
    --all           Re-score all test results with response_text
    --result-id ID  Re-score a specific test result by ID

This script is useful for:
- Testing JEF integration
- Debugging scoring issues
- Re-scoring after JEF library updates
- Backfilling scores for old test results
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import db, TestResult, PromptVersion
from models import jef_scorer
from app import app


def rescore_result(result):
    """
    Re-score a single TestResult.

    Args:
        result (TestResult): The test result to re-score

    Returns:
        bool: True if successful, False if error
    """
    if not result.response_text:
        print(f"  Result {result.id}: No response text, skipping")
        return False

    if result.error_status:
        print(f"  Result {result.id}: Has error status, skipping")
        return False

    # Get reference text from PromptVersion
    prompt_version = PromptVersion.query.get(result.version_id)
    reference_text = prompt_version.reference_text if prompt_version else None

    try:
        # Score the response
        scores = jef_scorer.score_response(
            response_text=result.response_text,
            reference_text=reference_text,
            model_name=result.model_name,
            vendor=result.vendor
        )

        # Update the result
        result.tiananmen_score = scores['tiananmen_score']
        result.nerve_agent_score = scores['nerve_agent_score']
        result.meth_score = scores['meth_score']
        result.harry_potter_score = scores['harry_potter_score']
        result.copyrights_score = scores['copyrights_score']

        result.tiananmen_pass = scores['tiananmen_pass'] if scores['tiananmen_pass'] is not None else False
        result.nerve_agent_pass = scores['nerve_agent_pass'] if scores['nerve_agent_pass'] is not None else False
        result.meth_pass = scores['meth_pass'] if scores['meth_pass'] is not None else False
        result.harry_potter_pass = scores['harry_potter_pass'] if scores['harry_potter_pass'] is not None else False
        result.copyrights_pass = scores['copyrights_pass'] if scores['copyrights_pass'] is not None else False

        result.overall_success = scores['overall_success']

        db.session.commit()

        print(f"  Result {result.id}: Re-scored successfully (overall_success={scores['overall_success']})")
        return True

    except Exception as e:
        print(f"  Result {result.id}: Error during re-scoring: {str(e)}")
        db.session.rollback()
        return False


def rescore_all():
    """Re-score all test results with response_text."""
    print("Re-scoring all test results with response_text...")

    # Query all results with response_text
    results = TestResult.query.filter(
        TestResult.response_text.isnot(None),
        TestResult.error_status == False
    ).all()

    print(f"Found {len(results)} results to re-score\n")

    success_count = 0
    for result in results:
        if rescore_result(result):
            success_count += 1

    print(f"\nRe-scoring complete: {success_count}/{len(results)} successful")


def rescore_by_id(result_id):
    """Re-score a specific test result by ID."""
    print(f"Re-scoring test result {result_id}...")

    result = TestResult.query.get(result_id)

    if not result:
        print(f"Error: Test result {result_id} not found")
        return

    if rescore_result(result):
        print("\nRe-scoring complete")
    else:
        print("\nRe-scoring failed")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python utils/rescore_results.py [--all] [--result-id ID]")
        print("\nOptions:")
        print("  --all           Re-score all test results with response_text")
        print("  --result-id ID  Re-score a specific test result by ID")
        sys.exit(1)

    with app.app_context():
        if sys.argv[1] == '--all':
            rescore_all()
        elif sys.argv[1] == '--result-id' and len(sys.argv) >= 3:
            result_id = int(sys.argv[2])
            rescore_by_id(result_id)
        else:
            print("Error: Invalid arguments")
            print("Usage: python utils/rescore_results.py [--all] [--result-id ID]")
            sys.exit(1)


if __name__ == '__main__':
    main()
