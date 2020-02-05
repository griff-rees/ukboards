#!/usr/bin/env python
# -*- coding: utf-8 -*-

from csv import DictReader

import logging

from os import PathLike

from pathlib import Path

from typing import Dict, Optional, Sequence, Union

import requests
from requests.exceptions import ConnectionError

CHECK_EXTERNAL_IP_ADDRESS_GOOGLE = 'https://domains.google.com/checkip'

DEFAULT_API_KEY_PATH = Path('.env')

LOG_PATH = Path('logs/')
LOG_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S"

logger = logging.getLogger(__name__)

QueryParameters = Dict[str, Union[int, bool]]

DataRowDict = Dict[str, Union[str, int]]

RunConfigType = Dict[str, Optional[QueryParameters]]


def read_csv(path: str, **kwargs) -> Sequence[DataRowDict]:
    """Open `path` and return a list of dicts."""
    with open(path, **kwargs) as csv_file:
        for i, line in enumerate(DictReader(csv_file, **kwargs)):
            yield i, line


def add_file_logger(logger_instance: logging.Logger = None,
                    logging_level: Optional[int] = logging.INFO,
                    log_path: PathLike = LOG_PATH,
                    reset_log: bool = True):
    """Add a file logger."""
    if not logger_instance:
        logger_instance = logging.Logger()
    if logging_level:
        logger_instance.setLevel(logging_level)
    # if log_path != LOG_PATH:
        # logging_level = logging_level or logging.DEBUG
    if type(log_path) == str:
        log_path = Path(log_path)
    log_path.parent.mkdir(exist_ok=True, parents=True)
    if reset_log:
        file_handler = logging.FileHandler(log_path, mode='w')
    else:
        file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging_level)
    logger.addHandler(file_handler)


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


class InternetConnectionError(Error):

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
