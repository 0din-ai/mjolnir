"""
Sequential Test Runner
Executes prompts against multiple LLM models with rate limiting.
"""

import time
from models.database import db, TestResult
from models import openrouter_client
from models.config import load_models_config


def run_tests_sequential(version_id, model_ids, temperature, api_key, prompt_text):
    """
    Run tests sequentially against multiple models with rate limiting.

    Args:
        version_id (int): PromptVersion ID to associate results with
        model_ids (list): List of model IDs to test (e.g., ["openai/gpt-4", ...])
        temperature (float): Temperature parameter for all models
        api_key (str): OpenRouter API key
        prompt_text (str): The prompt to test

    Returns:
        list: List of created TestResult IDs

    Note:
        - Creates TestResult records for each model (success or failure)
        - Waits 5 seconds between each API call for rate limiting
        - Continues testing even if some models fail
        - Scores and pass fields are left NULL (filled in Phase 5)
    """
    # Load model configuration to get display names and vendors
    configured_models = load_models_config()
    model_lookup = {model['id']: model for model in configured_models}

    result_ids = []
    total_models = len(model_ids)

    for index, model_id in enumerate(model_ids):
        # Get model details from configuration
        model_info = model_lookup.get(model_id, {})
        model_name = model_info.get('display_name', model_id)
        vendor = model_info.get('vendor', 'Unknown')

        try:
            # Call OpenRouter API
            response_text = openrouter_client.test_prompt_on_model(
                api_key=api_key,
                model_id=model_id,
                prompt=prompt_text,
                temperature=temperature
            )

            # Create successful TestResult
            test_result = TestResult(
                version_id=version_id,
                model_id=model_id,
                model_name=model_name,
                vendor=vendor,
                temperature=temperature,
                response_text=response_text,
                error_status=False,
                error_message=None,
                # Scores are NULL - will be filled in Phase 5
                tiananmen_score=None,
                nerve_agent_score=None,
                meth_score=None,
                harry_potter_score=None,
                copyrights_score=None,
                # Pass flags are False - will be set in Phase 5
                tiananmen_pass=False,
                nerve_agent_pass=False,
                meth_pass=False,
                harry_potter_pass=False,
                copyrights_pass=False,
                overall_success=False
            )

        except Exception as e:
            # Create error TestResult
            test_result = TestResult(
                version_id=version_id,
                model_id=model_id,
                model_name=model_name,
                vendor=vendor,
                temperature=temperature,
                response_text=None,
                error_status=True,
                error_message=str(e),
                # Scores and pass flags remain NULL/False for errors
                tiananmen_score=None,
                nerve_agent_score=None,
                meth_score=None,
                harry_potter_score=None,
                copyrights_score=None,
                tiananmen_pass=False,
                nerve_agent_pass=False,
                meth_pass=False,
                harry_potter_pass=False,
                copyrights_pass=False,
                overall_success=False
            )

        # Save to database
        db.session.add(test_result)
        db.session.commit()
        result_ids.append(test_result.id)

        # Rate limiting: sleep 5 seconds between calls (except after last one)
        if index < total_models - 1:
            time.sleep(5)

    return result_ids
