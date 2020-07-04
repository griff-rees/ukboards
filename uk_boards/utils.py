#!/usr/bin/env python
# -*- coding: utf-8 -*-

from csv import DictReader

from datetime import datetime

from json import dump, load

import logging

from networkx import Graph, node_link_data, node_link_graph

from os import PathLike

from pathlib import Path

from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import requests
from requests.exceptions import ConnectionError

CHECK_EXTERNAL_IP_ADDRESS_GOOGLE = 'https://domains.google.com/checkip'

POSTCODE_IO = 'https://api.postcodes.io/postcodes/'

DEFAULT_API_KEY_PATH = Path('.env')

JSON_DATA_PATH = Path('data/json')

LOG_FOLDER = Path('logs/')
LOG_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S"
LOG_FILENAME_DATE_FORMAT = "%Y-%m-%d-%H:%M:%S"

logger = logging.getLogger(__name__)

QueryParameters = Dict[str, Union[int, bool]]

DataRowDict = Dict[str, Union[str, int]]

JSONDict = Dict[str, Any]

RunConfigType = Dict[str, Optional[Union[List, QueryParameters]]]


def formatted_now_str(date_format: str = LOG_FILENAME_DATE_FORMAT):
    """Return current time in ``date_format`` format."""
    return datetime.now().strftime(date_format)


DEFAULT_LOG_FILE_NAME = f"default_{formatted_now_str()}.log"


def read_csv(path: PathLike, **kwargs) -> Sequence[DataRowDict]:
    """Open `path` and return a list of dicts."""
    with open(path, **kwargs) as csv_file:
        for i, line in enumerate(DictReader(csv_file, **kwargs)):
            yield i, line


def write_json_graph(graph: Graph, path: PathLike = JSON_DATA_PATH) -> None:
    """Write a json file including nodes, edges and attributes."""
    path = Path(path)
    path.parent.mkdir(exist_ok=True, parents=True)
    with open(path, "w") as graph_file:
        dump(node_link_data(graph), graph_file, default=str)


def read_json_graph(path: PathLike = JSON_DATA_PATH) -> Graph:
    """Read a json link_data_format file with nodes, edges and attributes."""
    with open(path) as graph_file:
        return node_link_graph(load(graph_file))


def get_ordinance_data(post_code: str) -> requests.Response:
    """Request ordinance survey data from postcodes.io."""
    try:
        return requests.get(POSTCODE_IO + post_code)
    except ConnectionError:
        raise InternetConnectionError


def ordinance_wrapper(node_key: Union[int, str, float], data: JSONDict):
    """Call ``get_ordinance_data`` on data and return a tuple with node_key."""
    address: Optional[Dict[str, str]] = None
    post_code: Optional[str] = None
    if data['kind'] == 'company':
        address = data['data']['company']['registered_office_address']
        post_code = address['postal_code']
    elif data['kind'] == 'personal-appointment':
        address = data['data']['items']['address']
        post_code = address['postal_code']
    elif data['kind'] == 'officer':
        address = data['data']['items'][0]['address']
        post_code = address['postal_code']
    elif data['kind'] in ('charity', 'trustee'):
        if 'Address' in data['data']:
            address = {k: v.strip() if v else v
                       for k, v in data['data']['Address'].items()}
            post_code = address['Postcode'].strip()
    else:
        raise NotImplementedError(f"No implementation of kind: {data['kind']}")
    data['address']: Optional[str] = address
    data['post_code']: Optional[str] = post_code
    data['ordinance']: Optional[JSONDict] = (
            get_ordinance_data(post_code).json()['result']
            if post_code else None
        )
    data['latitude']: Optional[float] = (
            data['ordinance']['latitude']
            if data['ordinance'] else None
        )
    data['longitude']: Optional[float] = (
            data['ordinance']['longitude']
            if data['ordinance'] else None
        )


def call_node_func(graph: Graph, func: Callable) -> Graph:
    """Call a function iterating on all graph nodes."""
    for node in graph.nodes(data=True):
        func(*node)


def set_node_data_func(graph: Graph, name: str, func: Callable) -> Graph:
    """Call a function to add data to nodes, iterating on all graph nodes."""
    for node in graph.nodes(data=True):
        node[1][name] = func(*node)


def file_log_handler(level: Optional[int] = logging.INFO,
                     filename: PathLike = DEFAULT_LOG_FILE_NAME,
                     folder: PathLike = LOG_FOLDER,
                     reset_log: bool = True,
                     *args, **kwargs) -> logging.FileHandler:
    """Add a file logger.

    Todo:
        * Consider generalising to type of handler.
    """
    log_path = Path(folder) / filename
    log_path.parent.mkdir(exist_ok=True, parents=True)
    if reset_log:
        file_handler = logging.FileHandler(log_path, mode='w')
    else:
        file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    return file_handler


def get_kinds_ids_dict(graph: Graph, kinds: set) -> Sequence[set]:
    """Return a dicts of ids of each kind.

    In the case of Companies House companies there are companies, board members
    and controllers. See uk_boards.companeis.COMPANEY_NETWORK_KINDS
    """
    kind_dict = {k: set() for k in kinds}
    for node_id, data in graph.nodes(data=True):
        kind_dict[data['kind']].add(node_id)
    return kind_dict


class Error(Exception):

    """Base class for exceptions in this module.

    See: https://docs.python.org/3/tutorial/errors.html
    """

    pass


class NegativeIntBranchException(Error):

    """Error of a branch being a non-integer and/or less than 0."""

    def __init__(self, branches: int,
                 message: str = None,
                 ) -> None:
        self.branches = branches
        self.message = message or (f"{branches} is an invalid number of "
                                   "network branches. It must be an int "
                                   "and > 0.")

    def __str__(self) -> str:
        return self.message


class ExceededMaxBranchesException(Error):

    """Error of a branch being a non-integer and/or less than 0."""

    def __init__(self, branches: int,
                 max_branches: int,
                 message: str = None,
                 ) -> None:
        self.branches: int = branches
        self.max_branches: int = max_branches
        self.message: str = message or (f"Current branches {branches} >= "
                                        f"maximum {max_branches} branches "
                                        "allowed.")

    def __str__(self) -> str:
        return self.message


class InternetConnectionError(Error):

    """Either no internet connection or a restricted local network."""

    DEFAULT_MESSAGE = ("You external IP address cannot be "
                       "found. You may have lost internet "
                       "connectivity or have a restricted "
                       "local connection without access to "
                       "the wider internet, including "
                       "google.com, Companies House and "
                       "Charity Commission APIs.")

    def __init__(self, msg: str = DEFAULT_MESSAGE, *args, **kwargs) -> None:
        super().__init__(msg, *args, **kwargs)


def get_external_ip_address(
        checkip_url: str = CHECK_EXTERNAL_IP_ADDRESS_GOOGLE) -> str:
    """Check external ip address, raise an error if no connection."""
    try:
        return requests.get(checkip_url).text
    except ConnectionError:
        raise InternetConnectionError
