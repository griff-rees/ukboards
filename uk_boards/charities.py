#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

import logging

import networkx

import os

from requests import Session

from typing import List, Optional

from zeep import Client, Settings, Plugin
from zeep.exceptions import Fault

logger = logging.getLogger(__name__)

load_dotenv()

CHARITY_COMMISSION_WSDL = ('http://apps.charitycommission.gov.uk/'
                           'Showcharity/API/SearchCharitiesV1/'
                           'SearchCharitiesV1.asmx?wsdl')

CHARITY_COMMISSION_API_KEY = os.environ.get("CHARITY_KEY")

API_KEY_NAME = 'APIKey'


def get_client(wsdl: str = CHARITY_COMMISSION_WSDL,
               raw_response: bool = False,
               plugins: List[Plugin] = None,
               session: Session = None) -> Client:
    """Generate a Client for querying Charities Commision API."""
    settings = Settings(strict=False, xml_huge_tree=True,
                        raw_response=raw_response)
    return Client(wsdl=wsdl, settings=settings, plugins=plugins)


def check_registered_charity_number(search: str, charity_number: int,
                                    client: Client = None,
                                    api_key: str = CHARITY_COMMISSION_API_KEY
                                    ) -> int:
    """Check if registered charity number is a correct one."""
    if not client:
        client = get_client()
    charities = client.service.GetCharitiesByName(APIKey=api_key,
                                                  strSearch=search,)
    for charity in charities:
        charity_data = client.service.GetCharityByRegisteredCharityNumber(
            APIKey=api_key,
            registeredCharityNumber=charity['RegisteredCharityNumber'],)
        if charity_data['CharityNumber'] == charity_number:
            return charity_data['RegisteredCharityNumber']
    raise Exception('No charity found with "CharityNumber": ' +
                    str(charity_number))


def get_charity_network(charity_number: int = 1085314,  # TATE FOUNDATION
                        branches: int = 0,
                        client: Client = None,
                        test_name: str = None) -> Optional[networkx.Graph]:
    g = networkx.Graph()
    if not client:
        client = get_client()
    try:
        charity_data = client.service.GetCharityByRegisteredCharityNumber(
            APIKey=os.environ.get("CHARITY_KEY"),
            registeredCharityNumber=charity_number,)
    except Fault:
        logger.error(f'Fault error pulling for {charity_number}')
        return
    if not charity_data:
        logger.warning("No data on charity {}".format(charity_number))
        if not test_name:
            logger.warning("No records from Charities Commision on "
                           "this Arts Council Instition")
            return
    charity_name = charity_data['CharityName']
    if test_name:  # Test the name of the queried  Charity fits the intended
        try:
            assert charity_name == test_name
        except AssertionError:
            logger.exception('Referral test name "{0}" is different from '
                             '"{1}" which is associated '
                             'with charity_number {2}'.format(
                                 test_name.strip(), charity_name.strip(),
                                 charity_number))
    g.add_node(charity_number,
               name=charity_name,
               bipartite=0,
               data=charity_data)  # Add a charity/company attribute
    logger.debug(charity_name)
    for subsidiary in range(charity_data['SubsidiaryNumber'] + 1):
        trustees = client.service.GetCharityTrustees(
            APIKey=os.environ.get("CHARITY_KEY"),
            registeredCharityNumber=charity_number,
            subsidiaryNumber=subsidiary)
        if not trustees:
            logger.warning("No trustees for charity {0} ({1} "
                           "subsidiary {2})".format(charity_name.strip(),
                                                    charity_number,
                                                    subsidiary))
            continue
        for trustee in trustees:
            logger.debug('{0} {1} {2}'.format(charity_number,
                                              trustee['TrusteeName'],
                                              trustee['TrusteeNumber']))
            g.add_node(trustee['TrusteeNumber'],
                       name=trustee['TrusteeName'],
                       bipartite=1,
                       data=trustee)
            g.add_edge(charity_number,
                       trustee['TrusteeNumber'])
            if branches and trustee['RelatedCharitiesCount']:
                for charity in trustee['RelatedCharities']:
                    # related_charity_number = \
                    #     get_charity_number(charity['CharityName'],
                    #                                   charity['CharityNumber'],
                    #                                   client=client)
                    if charity['CharityNumber'] not in g.nodes:
                        subgraph = get_charity_network(
                            charity['CharityNumber'], branches - 1,
                            client=client, test_name=charity['CharityName'])
                        assert networkx.is_bipartite(subgraph)
                        g = networkx.compose(g, subgraph)
                        assert networkx.is_bipartite(g)
    return g
