"""
Sequential Test Runner
Executes prompts against multiple LLM models with rate limiting.
"""

import time
from models.database import db, TestResult, PromptVersion
from models import openrouter_client
from models.config import load_models_config
from models import jef_scorer


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
        - Scores and pass fields are calculated using 0din-JEF library
        - Excluded models (Grok, Mistral, Command R) have NULL scores
    """
    # Load model configuration to get display names and vendors
    configured_models = load_models_config()
    model_lookup = {model['id']: model for model in configured_models}

    # Get reference text from PromptVersion for copyright scoring
    prompt_version = PromptVersion.query.get(version_id)
    reference_text = prompt_version.reference_text if prompt_version else None

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

            # Score the response using JEF
            scores = jef_scorer.score_response(
                response_text=response_text,
                reference_text=reference_text,
                model_name=model_name,
                vendor=vendor
            )

            # Create successful TestResult with scores
            test_result = TestResult(
                version_id=version_id,
                model_id=model_id,
                model_name=model_name,
                vendor=vendor,
                temperature=temperature,
                response_text=response_text,
                error_status=False,
                error_message=None,
                # Scores from JEF
                tiananmen_score=scores['tiananmen_score'],
                nerve_agent_score=scores['nerve_agent_score'],
                meth_score=scores['meth_score'],
                harry_potter_score=scores['harry_potter_score'],
                copyrights_score=scores['copyrights_score'],
                # Pass flags from JEF
                tiananmen_pass=scores['tiananmen_pass'] if scores['tiananmen_pass'] is not None else False,
                nerve_agent_pass=scores['nerve_agent_pass'] if scores['nerve_agent_pass'] is not None else False,
                meth_pass=scores['meth_pass'] if scores['meth_pass'] is not None else False,
                harry_potter_pass=scores['harry_potter_pass'] if scores['harry_potter_pass'] is not None else False,
                copyrights_pass=scores['copyrights_pass'] if scores['copyrights_pass'] is not None else False,
                overall_success=scores['overall_success']
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
