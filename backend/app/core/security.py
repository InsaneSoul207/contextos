"""
ContextOS Security Utilities.

Provides API key validation and first-run key generation.
"""

import logging
import secrets
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_PLACEHOLDER = "change-me-to-a-random-secret"


def generate_api_key() -> str:
    """Generate a cryptographically secure random API key."""
    return secrets.token_urlsafe(32)


def ensure_api_key() -> str:
    """Return the configured API key, generating one on first run if needed.

    If the key is still the default placeholder, a new random key is generated,
    saved into a ``api_key.txt`` file inside the data directory, and returned.
    """
    settings = get_settings()
    key = settings.contextos_api_key

    if key and key != _DEFAULT_PLACEHOLDER:
        return key

    # Check for a previously generated key file
    key_file: Path = settings.data_dir / "api_key.txt"
    if key_file.exists():
        saved = key_file.read_text().strip()
        if saved:
            return saved

    # Generate a fresh key
    new_key = generate_api_key()
    key_file.write_text(new_key)
    logger.info("Generated new API key and saved to %s", key_file)
    return new_key


def validate_api_key(provided_key: Optional[str]) -> bool:
    """Return True if *provided_key* matches the configured API key."""
    expected = ensure_api_key()
    if not provided_key:
        return False
    return secrets.compare_digest(provided_key, expected)
