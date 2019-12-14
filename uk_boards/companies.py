#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import time

from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv

import networkx

import requests
from requests.exceptions import ConnectionError

from .utils import InternetConnectionError, get_external_ip_address

logger = logging.getLogger(__name__)

load_dotenv()


COMPANIES_HOUSE_URL = 'https://api.companieshouse.gov.uk'
COMPANIES_HOUSE_API_KEY_NAME = "COMPANIES_HOUSE_KEY"
COMPANIES_HOUSE_API_KEY = os.getenv(COMPANIES_HOUSE_API_KEY_NAME)


JSONDict = Dict[str, Any]


def companies_house_query(query: str,
                          auth_key: str = COMPANIES_HOUSE_API_KEY,
                          sleep_time: int = 60,
                          url_prefix: str = COMPANIES_HOUSE_URL,
                          max_trials: int = 6,
                          ) -> Optional[JSONDict]:
    """
    Companies House API quiery repeated when necessary, returns json if valid.

    The `auth_tuple` reflects the `(username, password)` auth
    parameters customised for Companies House api which expects the `api_key`
    in the username spot and no separate component (hence blank password).

    Args:
        query (str): a query string such as '/company/04547069'
        auth_key (str): API key which is by default loaded from a .env file
        sleep_time (int): Number of seconds to pause after query error
        url_prefix (str): Prefix of url that defaults to COMPANIES HOUSE API
        trials (int): Number of attempts to query, default with sleep_time
                      exceeds the 5 min max query time

    Returns:
        dict: A Dict of a valid JSON response (`200` response code)
        None: None returned for response codes `404`, `500` and `502`

    Raises:
        Exception: If number of `trials` is exceeded.

    Todo:
        * Cover all exceptions in tests
        * Consider more effient means of managing 429 Too Many Requests errors
    """
    auth_tuple = (auth_key, "")
    trials = max_trials
    while trials:
        try:
            response = requests.get(url_prefix + query, auth=auth_tuple)
        except ConnectionError:
            raise InternetConnectionError
        if response.status_code == 200:
            return response.json()
        logger.warning(f'Status code {response.status_code} from {query}')
        if response.status_code in (403, 401):
            raise CompaniesHousePermissionError(query)
        if response.status_code == 404:
            logger.error(f'Skipping {query}')
            return None
        if response.status_code == 500:
            logger.warning(f'Will skip after {max_trials - trials} repeat')
            if trials < max_trials - 1:
                return None
        if response.status_code == 502:
            # Server error, likely an overload issue (hence adding to wait)
            logger.warning(f'Adding a {sleep_time} sec wait')
            time.sleep(sleep_time)
        logger.warning(f'Trying again in {sleep_time} seconds...')
        time.sleep(sleep_time)
        trials -= 1
    raise Exception(
            f"Failed {max_trials} attempt(s) querying "
            f"{url_prefix + query}")


class CompaniesHousePermissionError(Exception):

    """An exception for handling 403 forbidden errors."""

    def __init__(self, query: str = None, message: str = None, ) -> None:
        """Either set passed message or set to _default_error_message()."""
        self.query = query
        self.message = message or self._default_error_message()

    def __str__(self) -> str:
        return self.message

    def _default_error_message(self) -> str:
        """Try to check current IP address to raise clear permission error."""
        ip_address = get_external_ip_address()
        return (f'Query: {self.query}\nreturned a 403 (forbidden) error. '
                'If that query seems correct, check the '
                f'{COMPANIES_HOUSE_API_KEY_NAME} is set in your local .env '
                'file.\n'
                'If both are correct, check the external IP address of '
                f'this computer ({ip_address}) is included in the list of '
                'Restricted IPs on your registered Companies House API Key.')


def stringify_company_number(company_number: Union[int, str]) -> str:
    """Enforce correct company number as string of length >= 8."""
    company_number = str(company_number)
    if len(company_number) < 8:
        return company_number.rjust(8, '0')  # Shorter need preceeding '0's
    return company_number


def get_company_network(company_number: int = '04547069',
                        branches: int = 0,) -> Optional[networkx.Graph]:
    """
    Query the network of board members recursively.

    Note:
        * 429 Too Many Requests error raised if > 600/min
        * Test officers error on company '01086582'
        * Consider removing print statement within the related loop
        * Refactor todo info into documentation
        * Add option of including network collected prior to error
    """
    g = networkx.Graph()
    logger.debug('Querying board network from {}'.format(company_number))
    company_number = stringify_company_number(company_number)
    company = companies_house_query('/company/' + company_number)
    if not company:
        logger.error('Querying data on company {} failed'.format(
            company_number))
        return None
    logger.debug(company['company_name'])
    g.add_node(company_number, name=company['company_name'],
               bipartite=0, data=company)
    officers = companies_house_query(
        '/company/{}/officers'.format(company_number))
    if not officers:
        logger.error("Error requesting officers of company {0} "
                     "({1})".format(company['company_name'], company_number))
        # Worth considering saving error here
        return None
    for officer in officers['items']:
        officer_id = officer['links']['officer']['appointments'].split('/')[2]
        logger.debug('{0} {1} {2}'.format(company_number, officer['name'],
                                          officer_id))
        g.add_node(officer_id, name=officer['name'], bipartite=1, data=officer)
        g.add_edge(company_number, officer_id)
        if branches:
            appointments = companies_house_query(
                '/officers/{}/appointments'.format(officer_id))
            if not appointments:
                logger.error("Error requesting appointments of board "
                             "member {0} ({1}) of company {2} ({3})".format(
                                 officer['name'], officer_id,
                                 company['company_name'], company_number))
                # Worth considering saving error here
                continue
            for related_company in appointments['items']:
                # if not related_company:
                #     assert False
                #     logger.warning("Failed request")
                related_company_number = \
                    related_company['appointed_to']['company_number']
                if related_company_number not in g.nodes:
                    subgraph = get_company_network(related_company_number,
                                                   branches=branches - 1)
                    if subgraph:
                        g = networkx.compose(g, subgraph)
                        assert networkx.is_bipartite(subgraph)
                    else:
                        logger.warning("Skipping company {0} from board "
                                       "member {1} ({2}) of company {3} "
                                       "({4})".format(related_company_number,
                                                      officer['name'],
                                                      officer_id,
                                                      company['company_name'],
                                                      company_number))
                        print(related_company)
    return g
