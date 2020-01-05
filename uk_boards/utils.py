#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import requests
from requests.exceptions import ConnectionError


CHECK_EXTERNAL_IP_ADDRESS_GOOGLE = 'https://domains.google.com/checkip'

DEFAULT_API_KEY_PATH = Path('.env')


class InternetConnectionError(Exception):

    """Either no internet connection or a restricted local network."""

    pass


def get_external_ip_address(
        checkip_url: str = CHECK_EXTERNAL_IP_ADDRESS_GOOGLE) -> str:
    """Check external ip address, raise an error if no connection."""
    try:
        return requests.get(checkip_url).text
    except ConnectionError:
        raise InternetConnectionError("You external IP address cannot be "
                                      "found. You may have lost internet "
                                      "connectivity or have a restricted "
                                      "local connection without access to "
                                      "the wider internet, including "
                                      "google.com, Companies House and "
                                      "Charity Commission APIs.")
