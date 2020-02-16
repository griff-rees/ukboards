import os
import pytest
from dotenv import load_dotenv

from uk_boards.utils import (get_external_ip_address, InternetConnectionError,
                             DEFAULT_API_KEY_PATH)


load_dotenv(dotenv_path=DEFAULT_API_KEY_PATH)

COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME = 'COMPANIES_HOUSE_ALLOWED_IP_ADDRESS'
COMPANIES_HOUSE_ALLOWED_IP_ADDRESS = os.getenv(
    COMPANIES_HOUSE_ALLOWED_IP_ADDRESS_NAME, '')

try:
    IP_ADDRESS = get_external_ip_address()
except InternetConnectionError:
    IP_ADDRESS = None
    pass

skip_if_not_allowed_ip = pytest.mark.skipif(
    IP_ADDRESS != COMPANIES_HOUSE_ALLOWED_IP_ADDRESS,
    reason="Fails unless ip address is registered for Companies House api key."
)
