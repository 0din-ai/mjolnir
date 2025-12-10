"""
Configuration management for LLM Jailbreak Research Tool
Handles loading model configuration from YAML and managing API keys in the database.
"""

import os
import yaml
import requests
from typing import Dict, List, Optional, Tuple
from models.database import db, Configuration


def load_models_config() -> List[Dict[str, str]]:
    """
    Load model configuration from config/models.yaml.

    Returns:
        List of model dictionaries with keys: id, display_name, vendor

    Raises:
        FileNotFoundError: If models.yaml doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'models.yaml'
    )

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config.get('models', [])


def get_api_key(key_name: str) -> Optional[str]:
    """
    Retrieve an API key from the Configuration table.

    Args:
        key_name: Name of the API key (e.g., "openrouter", "0din_ai")

    Returns:
        API key value if found, None otherwise
    """
    config_entry = Configuration.query.filter_by(key=key_name).first()
    return config_entry.value if config_entry else None


def set_api_key(key_name: str, value: str) -> None:
    """
    Insert or update an API key in the Configuration table.

    Args:
        key_name: Name of the API key (e.g., "openrouter", "0din_ai")
        value: API key value to store
    """
    config_entry = Configuration.query.filter_by(key=key_name).first()

    if config_entry:
        # Update existing key
        config_entry.value = value
    else:
        # Insert new key
        config_entry = Configuration(key=key_name, value=value)
        db.session.add(config_entry)

    db.session.commit()


def validate_models_against_openrouter(
    api_key: str,
    configured_models: List[Dict[str, str]]
) -> Tuple[List[str], Optional[str]]:
    """
    Validate configured models against OpenRouter's API.

    Args:
        api_key: OpenRouter API key
        configured_models: List of model dicts from load_models_config()

    Returns:
        Tuple of (unavailable_models, error_message)
        - unavailable_models: List of model IDs that are configured but not available
        - error_message: Error description if API call failed, None otherwise
    """
    try:
        # Query OpenRouter /models endpoint
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10
        )

        if response.status_code != 200:
            return [], f"OpenRouter API returned status {response.status_code}"

        # Extract available model IDs
        available_models_data = response.json()
        available_model_ids = {model['id'] for model in available_models_data.get('data', [])}

        # Check which configured models are unavailable
        configured_model_ids = {model['id'] for model in configured_models}
        unavailable = [
            model_id for model_id in configured_model_ids
            if model_id not in available_model_ids
        ]

        return unavailable, None

    except requests.RequestException as e:
        return [], f"Failed to connect to OpenRouter API: {str(e)}"
    except (KeyError, ValueError) as e:
        return [], f"Failed to parse OpenRouter API response: {str(e)}"


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display purposes.

    Shows first 3 characters, then asterisks, then last 3 characters.
    Example: "sk-abc123def456" -> "sk-***456"

    Args:
        api_key: Full API key string

    Returns:
        Masked version of the key
    """
    if not api_key or len(api_key) < 8:
        return "***"

    return f"{api_key[:3]}***{api_key[-3:]}"
