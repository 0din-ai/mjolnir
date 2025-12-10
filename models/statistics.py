"""
Summary Statistics Calculator
Calculate aggregate statistics for test results.
"""


def calculate_summary(test_results):
    """
    Calculate summary statistics for a list of TestResult objects.

    Args:
        test_results (list): List of TestResult objects

    Returns:
        dict: Dictionary containing:
            - total_count (int): Total number of results
            - success_count (int): Number with overall_success=True
            - failed_count (int): Number with overall_success=False and error_status=False
            - error_count (int): Number with error_status=True
            - success_percentage (float): Percentage of successful jailbreaks
            - failed_percentage (float): Percentage of failed tests
            - error_percentage (float): Percentage of errors

    Notes:
        - Percentages are calculated out of total_count
        - If total_count is 0, all percentages are 0.0
        - success + failed + error = total (100%)
    """
    # Initialize counts
    total_count = len(test_results)
    success_count = 0
    failed_count = 0
    error_count = 0

    # Count results by status
    for result in test_results:
        if result.error_status:
            error_count += 1
        elif result.overall_success:
            success_count += 1
        else:
            failed_count += 1

    # Calculate percentages
    if total_count > 0:
        success_percentage = (success_count / total_count) * 100
        failed_percentage = (failed_count / total_count) * 100
        error_percentage = (error_count / total_count) * 100
    else:
        success_percentage = 0.0
        failed_percentage = 0.0
        error_percentage = 0.0

    return {
        'total_count': total_count,
        'success_count': success_count,
        'failed_count': failed_count,
        'error_count': error_count,
        'success_percentage': round(success_percentage, 1),
        'failed_percentage': round(failed_percentage, 1),
        'error_percentage': round(error_percentage, 1)
    }
