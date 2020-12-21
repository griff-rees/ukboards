"""Basic configuration for adding fixtures for tests.

This adds pytest marks regarding API access to Companies House.
"""

from os import getenv
from typing import Optional

import pytest
from dotenv import load_dotenv

from ukboards.utils import (
    DEFAULT_API_KEY_PATH,
    InternetConnectionError,
    get_external_ip_address,
)

load_dotenv(dotenv_path=DEFAULT_API_KEY_PATH)

COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME: str = (
    "COMPANIES_HOUSE_ALLOWED_IP_ADDRESS"
)
COMPANIES_HOUSE_ALLOWED_IP_ADDRESS: Optional[str] = getenv(
    COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME, ""
)

try:
    IP_ADDRESS: Optional[str] = get_external_ip_address()
except InternetConnectionError:
    IP_ADDRESS = None
    pass

skip_if_not_allowed_ip = pytest.mark.skipif(
    IP_ADDRESS != COMPANIES_HOUSE_ALLOWED_IP_ADDRESS,
    reason=(
        "Fails unless ip address is registered for Companies House api key."
    ),
)
