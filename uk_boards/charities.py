#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base mode for querying Charity Commission SOAP API."""

from dataclasses import dataclass, field
from logging import getLogger
from os import getenv
from typing import Final, List, Optional, Tuple, Union

from dotenv import load_dotenv
from networkx import Graph, compose, is_bipartite
from zeep import Client, Plugin, Settings
from zeep.exceptions import Fault
from zeep.helpers import serialize_object

from .utils import DEFAULT_API_KEY_PATH, CharityAPIKeyType, RunConfig

logger = getLogger(__name__)

load_dotenv(dotenv_path=DEFAULT_API_KEY_PATH)

CHARITY_COMMISSION_WSDL = (
    "https://apps.charitycommission.gov.uk/"
    "Showcharity/API/SearchCharitiesV1/"
    "SearchCharitiesV1.asmx?wsdl"
)

CHARITY_COMMISSION_API_KEY_NAME: Final[str] = "APIKey"
CHARITY_COMMISSION_API_KEY_ENV_NAME: Final[str] = "CHARITY_COMMISSION_KEY"
CHARITY_COMMISSION_API_KEY: Final[Optional[CharityAPIKeyType]] = getenv(
    CHARITY_COMMISSION_API_KEY_ENV_NAME
)

CHARITY_NETWORK_KINDS: Final[Tuple[str, str]] = ("charity", "trustee")

CharityIDType = int
CharityRootIDsType = Union[CharityIDType, Tuple[CharityIDType, ...]]


class CharitiesAuthPlugin(Plugin):
    """Add an APIKey to each request."""

    def __init__(
        self,
        api_key_name: str = CHARITY_COMMISSION_API_KEY_NAME,
        api_key_value: Optional[
            CharityAPIKeyType
        ] = CHARITY_COMMISSION_API_KEY,
    ) -> None:
        """Initialise api_key_name and api_key_value."""
        self.api_key_name = api_key_name
        self.api_key_value = api_key_value

    def egress(self, envelope, http_headers, operation, binding_options):
        """Auto add to the envelope (or replace) Charity api_key.

        :param envelope: The envelope as XML node
        :param http_headers: Dict with the HTTP headers
        :param operation: The associated Operation instance
        :param binding_options: Binding specific options for the operation
        """
        for element in operation.input.body.type.elements:
            if (
                element[0] == self.api_key_name
                and element[1].name == self.api_key_name
            ):
                key_type = element[1]
                key_type.render(envelope[0][0], self.api_key_value)
        return envelope, http_headers


def get_client(
    wsdl: str = CHARITY_COMMISSION_WSDL,
    raw_response: bool = False,
    api_key_name: str = CHARITY_COMMISSION_API_KEY_NAME,
    api_key_value: Optional[CharityAPIKeyType] = CHARITY_COMMISSION_API_KEY,
    plugins: List[Plugin] = None,
    **kwargs,
) -> Client:
    """Generate a Client for querying Charities Commision API."""
    settings: Settings = Settings(
        strict=False, xml_huge_tree=True, raw_response=raw_response
    )
    plugins = (
        [CharitiesAuthPlugin(api_key_name, api_key_value)]
        if not plugins
        else plugins
    )
    return Client(wsdl=wsdl, settings=settings, plugins=plugins, **kwargs)


def check_registered_charity_number(
    name: str,
    charity_number: CharityIDType,
    client: Optional[Client] = None,
) -> int:
    """Check if registered charity_number matches searched name."""
    if not client:
        client = get_client()
    charities = client.service.GetCharitiesByName(
        strSearch=name,
    )
    for charity in charities:
        charity_data = client.service.GetCharityByRegisteredCharityNumber(
            registeredCharityNumber=charity["RegisteredCharityNumber"],
        )
        if charity_data["CharityNumber"] == charity_number:
            return charity_data["RegisteredCharityNumber"]
    raise Exception(
        'No charity found with "CharityNumber": ' f"{charity_number}"
    )


def get_charity_network(
    charity_number: CharityIDType = 1085314,  # TATE
    branches: int = 0,  # FOUNDATION
    client: Optional[Client] = None,
    api_key: Optional[str] = CHARITY_COMMISSION_API_KEY,
    test_name: str = None,
    *args,
    **kwargs,
) -> Optional[Graph]:
    """Query Charity Commission API for board interlock network."""
    g: Graph = Graph()
    if not client:
        client = get_client(api_key_value=api_key)
    assert isinstance(charity_number, int)
    try:
        charity_data = client.service.GetCharityByRegisteredCharityNumber(
            registeredCharityNumber=charity_number,
        )
    except Fault:
        logger.error(f"Fault error pulling for {charity_number}")
        return None
    if not charity_data:
        logger.warning(f"No data on charity {charity_number}")
        if not test_name:
            logger.warning(
                "No records from Charities Commision on "
                "this Arts Council Instition"
            )
            return None
    charity_name = charity_data["CharityName"]
    if test_name:  # Test the name of the queried Charity is the intended
        try:
            assert charity_name == test_name
        except AssertionError:
            logger.exception(
                'Referral test name "{0}" is different from '
                '"{1}" which is associated '
                "with charity_number {2}".format(
                    test_name.strip(), charity_name.strip(), charity_number
                )
            )
    g.add_node(
        charity_number,
        name=charity_name.strip(),
        bipartite=0,
        # Add a charity/company attribute
        kind=CHARITY_NETWORK_KINDS[0],
        data=serialize_object(charity_data),
    )
    logger.debug(charity_name)
    for subsidiary in range(charity_data["SubsidiaryNumber"] + 1):
        trustees = client.service.GetCharityTrustees(
            registeredCharityNumber=charity_number, subsidiaryNumber=subsidiary
        )
        if not trustees:
            logger.warning(
                "No trustees for charity {0} ({1} "
                "subsidiary {2})".format(
                    charity_name.strip(), charity_number, subsidiary
                )
            )
            continue
        for trustee in trustees:
            logger.debug(
                "{0} {1} {2}".format(
                    charity_number,
                    trustee["TrusteeName"],
                    trustee["TrusteeNumber"],
                )
            )
            g.add_node(
                trustee["TrusteeNumber"],
                name=trustee["TrusteeName"].strip(),
                bipartite=1,
                kind=CHARITY_NETWORK_KINDS[1],
                data=serialize_object(trustee),
            )
            g.add_edge(charity_number, trustee["TrusteeNumber"])
            if branches and trustee["RelatedCharitiesCount"]:
                for charity in trustee["RelatedCharities"]:
                    # related_charity_number = \
                    #     get_charity_number(charity['CharityName'],
                    #                                   charity['CharityNumber'],
                    #                                   client=client)
                    if charity["CharityNumber"] not in g.nodes:
                        subgraph = get_charity_network(
                            charity["CharityNumber"],
                            branches - 1,
                            client=client,  # type: ignore[misc]
                            test_name=charity["CharityName"],
                            *args,
                            **kwargs,
                        )
                        assert is_bipartite(subgraph)
                        g = compose(g, subgraph)
                        assert is_bipartite(g)
    return g


@dataclass
class CharityRunConfig(RunConfig):
    """RunConfig dict with type enforced root_id."""

    root_id: Optional[CharityRootIDsType] = None
    success: Optional[bool] = False
    kind: Final[str] = "charity"
    composed_runs: List["CharityRunConfig"] = field(default_factory=list)
