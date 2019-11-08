#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

import logging

import networkx

import os

import requests
from requests.auth import HTTPBasicAuth

import time


logger = logging.getLogger(__name__)

load_dotenv()


COMPANIES_HOUSE_URL = 'https://api.companieshouse.gov.uk'
COMPANIES_HOUSE_AUTH = HTTPBasicAuth(os.getenv("COMPANIES_HOUSE_KEY"), "")


def safe_companies_house_query(url, auth=COMPANIES_HOUSE_AUTH, sleep_time=60):
    """Query url, if error wait for rate limit and try again, return json."""
    trials = 6
    while trials:
        response = requests.get(COMPANIES_HOUSE_URL + url, auth=auth)
        if response.status_code == 200:
            return response.json()
        logger.warning('Status code {0} from {1}'.format(response.status_code,
                                                         url))
        if response.status_code == 404:
            logger.error('Skipping ' + url)
            return None
        if response.status_code == 500:
            logger.warning('Will skip after 1 repeat')
            if trials < 5:
                return None
        if response.status_code == 502:
            # Server error, expecting an overload issue (hence adding to wait)
            logger.warning('Adding a {} sec wait'.format(2*sleep_time))
            time.sleep(sleep_time*2)
        logger.warning('Trying again in {} seconds...'.format(sleep_time))
        time.sleep(sleep_time)
        trials -= 1
    raise Exception("Failed 5 attempts querying " + url)


def correct_company_number(company_number):
    """Enforce correct company number as string of length >= 8."""
    company_number = str(company_number)
    if len(company_number) < 8:
        return company_number.rjust(8, '0')  # Shorter need preceeding '0's
    return company_number


def get_company_network(company_number='04547069', branches=0,):
    """
    Query the network of board members recursively.

    Note:
        * 429 Too Many Requests error raised if > 600/min
        * Test officers error on company '01086582'
        * Consider removing print statement within the related loop
        * Refactor todo info into documentation
    """
    g = networkx.Graph()
    logger.debug('Querying board network from {}'.format(company_number))
    company_number = correct_company_number(company_number)
    company = safe_companies_house_query('/company/' + company_number)
    if not company:
        logger.error('Querying data on company {} failed'.format(
            company_number))
        return None
    logger.debug(company['company_name'])
    g.add_node(company_number, name=company['company_name'],
               bipartite=0, data=company)
    officers = safe_companies_house_query(
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
            appointments = safe_companies_house_query(
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
