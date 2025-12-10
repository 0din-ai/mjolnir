"""
OpenRouter API Client
Handles communication with OpenRouter API for testing prompts against LLM models.
"""

import requests
import json


def test_prompt_on_model(api_key, model_id, prompt, temperature=0.7, timeout=60):
    """
    Test a prompt against a specific model via OpenRouter API.

    Args:
        api_key (str): OpenRouter API key
        model_id (str): Model identifier (e.g., "anthropic/claude-3.5-sonnet")
        prompt (str): The prompt text to test
        temperature (float): Temperature parameter for generation (default: 0.7)
        timeout (int): Request timeout in seconds (default: 60)

    Returns:
        str: The model's response text

    Raises:
        Exception: If API call fails for any reason (network, auth, rate limit, etc.)
    """
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # OpenRouter uses OpenAI-compatible format
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout
        )

        # Raise exception for HTTP errors (4xx, 5xx)
        response.raise_for_status()

        # Parse JSON response
        response_data = response.json()

        # Extract message content from OpenAI-compatible response format
        # Response format: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in response_data and len(response_data["choices"]) > 0:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content", "")

            if content:
                return content
            else:
                raise Exception("No content in response message")
        else:
            raise Exception("No choices in response")

    except requests.exceptions.Timeout:
        raise Exception(f"Request timeout after {timeout} seconds")
    except requests.exceptions.ConnectionError:
        raise Exception("Network connection error")
    except requests.exceptions.HTTPError as e:
        # Include status code and response text in error message
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_msg = error_data.get("error", {}).get("message", str(e))
        except:
            error_msg = str(e)
        raise Exception(f"HTTP {status_code}: {error_msg}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from API")
    except Exception as e:
        # Re-raise any other exceptions with original message
        raise Exception(str(e))
