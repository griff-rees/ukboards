#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utils for saving and loading network files, logging and ordinance data."""

from csv import DictReader
from dataclasses import dataclass, field
from datetime import datetime
from json import dump, load
from logging import INFO, FileHandler, getLogger
from os import PathLike
from os.path import getctime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import requests
from networkx import Graph, node_link_data, node_link_graph
from requests.exceptions import ConnectionError

CHECK_EXTERNAL_IP_ADDRESS_GOOGLE = "https://domains.google.com/checkip"

POSTCODE_IO = "https://api.postcodes.io/"
POSTCODE_CURRENT = POSTCODE_IO + "postcodes/"
POSTCODE_TERMINATED = POSTCODE_IO + "terminated_postcodes/"

DEFAULT_API_KEY_PATH = Path(".env")
JSON_DATA_PATH = Path("data/json")

LOG_FOLDER = Path("logs/")
LOG_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S"
LOG_FILENAME_DATE_FORMAT = "%Y-%m-%d-%H:%M:%S"

JSON_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
JSON_ADDITIONAL_DATA_KEY = "ukboards-metadata"
METADATA_DATETIME_KEYS = ["start_time", "end_time"]

logger = getLogger(__name__)

CharityAPIKeyType = str
CompanyAPIKeyType = str
APIKeyDictType = Dict[
    str, Optional[Union[CharityAPIKeyType, CompanyAPIKeyType]]
]

QueryValueTypes = Optional[Union[str, bool, int, List]]
QueryParameters = Dict[str, QueryValueTypes]

DataRowDict = Dict[str, Union[str, int]]

JSONDict = Dict[str, Any]

KindsIDType = Set[Optional[Union[str, int]]]
KindsDict = Dict[str, KindsIDType]

CSVRowType = Tuple[int, Dict[str, str]]


def formatted_now_str(date_format: str = LOG_FILENAME_DATE_FORMAT) -> str:
    """Return current time in ``date_format`` format."""
    return datetime.now().strftime(date_format)


DEFAULT_LOG_FILE_NAME = f"default_{formatted_now_str()}.log"


@dataclass
class RunConfig:
    """Base Typed Dict of query runs.

    Todo:
        * Add logs at an INFO default level
        * Consider storing relative log file with time stamp
    """

    # root_id: Optional[Union[str, int]]
    # kind: Literal['charity', 'company']
    parameter_state: QueryParameters = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # logs: [],
    connected_components_count: Optional[int] = None
    kinds_ids_dict: Optional[KindsDict] = None
    # composed_runs: List = field(default_factory=list)


def get_network_json_file_name(
    prefix: str = "charity_",
    time: Optional[datetime] = None,
    time_format: str = LOG_FILENAME_DATE_FORMAT,
) -> str:
    """Return a json file name datetime.now() timestamp by default."""
    time = time or datetime.now()
    return f"{prefix}-{time.strftime(time_format)}.json"


def get_latest_json_file_name(
    prefix: str = "", path: PathLike = JSON_DATA_PATH
) -> PathLike:
    """Return the latest json file in path with prefix."""
    path = Path(path)
    try:
        return max(path.glob(f"*{prefix}*.json"), key=getctime)
    except ValueError:
        raise NoMatchingDataPathError(path=path, prefix=prefix)


def read_csv(path: PathLike, **kwargs) -> Iterator[CSVRowType]:
    """Open `path` and return a list of dicts."""
    with open(path, **kwargs) as csv_file:
        for i, line in enumerate(DictReader(csv_file, **kwargs)):
            yield i, line


def write_json_graph(
    graph: Graph,
    path: PathLike = JSON_DATA_PATH,
    additional_data: JSONDict = None,
    additional_data_key: str = JSON_ADDITIONAL_DATA_KEY,
) -> None:
    """Write a json file including nodes, edges and attributes."""
    path = Path(path)
    path.parent.mkdir(exist_ok=True, parents=True)
    with open(path, "w") as graph_file:
        json_graph: JSONDict = node_link_data(graph)
        if additional_data:
            json_graph[additional_data_key] = additional_data
        dump(json_graph, graph_file, default=str)


def read_json_graph(
    path: PathLike = JSON_DATA_PATH,
    additional_data: bool = False,
    additional_data_key: str = JSON_ADDITIONAL_DATA_KEY,
) -> Union[Graph, Tuple[Graph, Graph]]:
    """Read a json link_data_format file with nodes, edges and attributes."""
    path = Path(path)
    with open(path) as graph_file:
        if additional_data:
            json_graph: JSONDict = load(
                graph_file, object_hook=json_deserialise
            )
            return (
                node_link_graph(json_graph),
                json_graph.get(additional_data_key),
            )
        return node_link_graph(load(graph_file))


def json_deserialise(
    json_dict: JSONDict,
    time_keys: Sequence[str] = METADATA_DATETIME_KEYS,
    time_format: str = JSON_DATE_FORMAT,
    root_key: str = JSON_ADDITIONAL_DATA_KEY,
):
    """Deserialise a JSON Datetime string."""
    for k, v in json_dict.items():
        if k in time_keys:
            json_dict[k] = datetime.strptime(v, time_format)
        elif type(v) is str:
            if v.isdigit() and not v.startswith("0"):
                json_dict[k] = int(v)
            elif v.startswith("{") and v.endswith("}"):
                values = v.strip("{}'").split(", ")
                json_dict[k] = {
                    int(val)
                    if val.isdigit() and not val.startswith("0")
                    else val.strip("'")
                    for val in values
                }
            elif v == "set()":
                json_dict[k] = set()
    return json_dict


def get_ordinance_data(post_code: str) -> Optional[JSONDict]:
    """Request ordinance survey data from postcodes.io."""
    try:
        response: requests.Response = requests.get(
            POSTCODE_CURRENT + post_code
        )
        if response.status_code == 200:
            return response.json()["result"]
        elif response.status_code == 404:
            logger.warning(
                f"ordinance.io query for {post_code} "
                f"returned a 404. Trying {POSTCODE_TERMINATED}"
            )
            response = requests.get(POSTCODE_TERMINATED + post_code)
            if response.status_code == 200:
                return response.json()["result"]
            else:
                logger.error(
                    f"No current or terminated record of {post_code} "
                    f"available at the ordinance survey."
                )
                return None
        else:
            raise
    except ConnectionError:
        raise InternetConnectionError


def ordinance_wrapper(node_key: Union[int, str, float], data: JSONDict):
    """Call ``get_ordinance_data`` on data and return a tuple with node_key."""
    address: Dict[str, str]
    post_code: Optional[str] = None
    if data["kind"] == "company":
        address = data["data"]["company"]["registered_office_address"]
        post_code = address.get("postal_code", None)
    elif data["kind"] == "personal-appointment":
        address = data["data"]["items"]["address"]
        post_code = address.get("postal_code", None)
    elif data["kind"] == "officer":
        address = data["data"]["items"][0]["address"] if data["data"] else None
        post_code = address.get("postal_code", None) if address else None
    elif data["kind"] in ("charity", "trustee"):
        if "Address" in data["data"]:
            address = {
                k: v.strip() if v else v
                for k, v in data["data"]["Address"].items()
            }
            post_code = address.get("Postcode")
            if isinstance(post_code, str):
                post_code = post_code.strip()
    else:
        raise NotImplementedError(f"No implementation of kind: {data['kind']}")
    data["address"] = address
    data["post_code"] = post_code
    data["ordinance"] = get_ordinance_data(post_code) if post_code else None
    data["latitude"] = (
        data["ordinance"]["latitude"] if data["ordinance"] else None
    )
    data["longitude"] = (
        data["ordinance"]["longitude"] if data["ordinance"] else None
    )


def call_node_func(graph: Graph, func: Callable) -> Graph:
    """Call a function iterating on all graph nodes."""
    try:
        for node in graph.nodes(data=True):
            func(*node)
    except AttributeError:
        logger.warning(
            f"{graph} passed which must be a Graph "
            f"object so {func} cannot be run."
        )


def set_node_data_func(graph: Graph, name: str, func: Callable) -> Graph:
    """Call a function to add data to nodes, iterating on all graph nodes."""
    for node in graph.nodes(data=True):
        node[1][name] = func(*node)


def file_log_handler(
    level: int = INFO,
    filename: str = DEFAULT_LOG_FILE_NAME,
    folder: PathLike = LOG_FOLDER,
    reset_log: bool = True,
    *args,
    **kwargs,
) -> FileHandler:
    """Add a file logger.

    Todo:
        * Consider generalising to type of handler.
    """
    log_path = Path(folder) / filename
    log_path.parent.mkdir(exist_ok=True, parents=True)
    if reset_log:
        file_handler = FileHandler(log_path, mode="w")
    else:
        file_handler = FileHandler(log_path)
    file_handler.setLevel(level)
    return file_handler


def get_kinds_ids_dict(graph: Graph, kinds: Tuple[str, ...]) -> KindsDict:
    """Return a dicts of ids of each kind.

    In the case of Companies House companies there are companies, board members
    and controllers. See ukboards.companies.COMPANEY_NETWORK_KINDS
    """
    kind_dict: KindsDict = {k: set() for k in kinds}
    for node_id, data in graph.nodes(data=True):
        kind_dict[data["kind"]].add(node_id)
    return kind_dict


class Error(Exception):
    """Base class for exceptions in this module.

    See: https://docs.python.org/3/tutorial/errors.html
    """

    pass


class NegativeIntBranchException(Error):
    """Error of a branch being a non-integer and/or less than 0.

    Todo:
        * Consider replacing self.message with self.msg.
    """

    def __init__(
        self,
        branches: int,
        message: str = None,
    ) -> None:
        """Initialise exception attributes based on branch numbers."""
        self.branches = branches
        self.message = message or (
            f"{branches} is an invalid number of "
            "network branches. It must be an int "
            "and > 0."
        )

    def __str__(self) -> str:
        """Set self.__str__ to use self.message."""
        return self.message


class ExceededMaxBranchesException(Error):
    """Error of a branch being a non-integer and/or less than 0.

    Todo:
        * Consider replacing self.message with self.msg.
    """

    def __init__(
        self,
        branches: int,
        max_branches: int,
        message: str = None,
    ) -> None:
        """Initialise exception attributes based on branch numbers."""
        self.branches: int = branches
        self.max_branches: int = max_branches
        self.message: str = message or (
            f"Current branches {branches} >= "
            f"maximum {max_branches} branches "
            "allowed."
        )

    def __str__(self) -> str:
        """Set self.__str__ to use self.message."""
        return self.message


class InternetConnectionError(Error):
    """Either no internet connection or a restricted local network."""

    DEFAULT_MESSAGE = (
        "You external IP address cannot be "
        "found. You may have lost internet "
        "connectivity or have a restricted "
        "local connection without access to "
        "the wider internet, including "
        "google.com, Companies House and "
        "Charity Commission APIs."
    )

    def __init__(self, msg: str = DEFAULT_MESSAGE, *args, **kwargs) -> None:
        """Return normal Error class with custom default msg."""
        super().__init__(msg)


class NoLoadedNetworkDataError(Error):
    """Exception if calculating ego networks prior to loading network data."""

    DEFAULT_MESSAGE = (
        "Network data must be loaded prior to calculating ego networks."
    )

    def __init__(self, msg: str = DEFAULT_MESSAGE, *args, **kwargs) -> None:
        """Add msg = DEFAULT_MESSAGE to standard Exception __init__."""
        super().__init__(msg)


class NoMatchingDataPathError(Error):
    """Exception of no existing path for saving or loading data."""

    def __init__(
        self,
        msg: Optional[str] = None,
        path: PathLike = Path(),
        prefix: str = "",
    ) -> None:
        """Raise error of ``path`` and ``prefix`` failing to match files."""
        self.msg = (
            msg
            or f"No path '{path}' contains files matching prefix: '{prefix}'."
        )
        self.path = path
        self.prefix = prefix
        super().__init__(self.msg)


def get_external_ip_address(
    checkip_url: str = CHECK_EXTERNAL_IP_ADDRESS_GOOGLE,
) -> str:
    """Check external ip address, raise an error if no connection."""
    try:
        return requests.get(checkip_url).text
    except ConnectionError:
        raise InternetConnectionError
