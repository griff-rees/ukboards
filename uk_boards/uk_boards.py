# -*- coding: utf-8 -*-

"""Main module."""


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
