# -*- coding: utf-8 -*-

"""Main module."""

from collections.abc import MutableSequence

from copy import deepcopy

from dataclasses import dataclass, field

from datetime import datetime

import logging

import time

from typing import (Dict, Callable, ClassVar, Optional, List, Sequence, Tuple,
                    Type, Union)

from networkx import Graph, compose_all, number_connected_components

from .companies import CompanyNetworkClient
from .charities import get_charity_network
from .utils import (read_csv, add_file_logger, QueryParameters, RunConfigType,
                    LOG_TIME_FORMAT)


logger = logging.getLogger(__name__)

DEFAULT_COMPANY_COLUMN_NAME = 'Company'
DEFAULT_CHARITY_COLUMN_NAME = 'Charity'
DEFAULT_ORGANISATION_COLUMN_NAME = 'Organisation'

DataRowDict = Dict[str, Union[str, int]]


@dataclass
class OrganisationEntry:

    data: DataRowDict
    organisation_key_name: str = DEFAULT_ORGANISATION_COLUMN_NAME
    charity_key_name: str = DEFAULT_CHARITY_COLUMN_NAME
    company_key_name: str = DEFAULT_COMPANY_COLUMN_NAME

    def __str__(self):
        return (f'{self.name}: Company {self.company_id} | '
                f'Charity {self.charity_id}')

    @property
    def company_id(self):
        if not hasattr(self, '_company_id'):
            if self.company_key_name in self.data:
                self._company_id = self.data[self.company_key_name]
        return self._company_id

    @property
    def charity_id(self):
        if not hasattr(self, '_charity_id'):
            if self.charity_key_name in self.data:
                self._charity_id = self.data[self.charity_key_name]
        return self._charity_id

    @property
    def name(self):
        if not hasattr(self, '_name'):
            if self.organisation_key_name in self.data:
                self._name = self.data[self.organisation_key_name]
        return self._name


OrganisationSequence = List[OrganisationEntry]


@dataclass
class OrganisationSequence(MutableSequence):

    """Class for managing queires of a Sequence of ``OrganisationEntry``.

    Todo:
        * Refactor charities query to generate a client like
          ``CompanyNetworkClient``
        * Include reset options in various cachable attributes
    """
    data_reader: Callable[..., OrganisationSequence] = read_csv
    data_reader_params: Dict[str, Union[str, int]] = field(default_factory=dict)
    organisation_entry_params: Dict[str, str] = field(default_factory=dict)
    company_client_params: QueryParameters = field(default_factory=dict)
    charity_client_params: QueryParameters = field(default_factory=dict)
    reset_logs: bool = True
    _charity_runs: Sequence[RunConfigType] = field(default_factory=list)
    _company_runs: Sequence[RunConfigType] = field(default_factory=list)
    __company_client_class: ClassVar[Type[CompanyNetworkClient]] = (
            CompanyNetworkClient
        )
    # __charity_client_class  # To be added when charity query is refactored
    __charity_client: ClassVar[Callable] = get_charity_network
    # **kwargs

    def __getitem__(self, index) -> OrganisationEntry:
        return self.organisations[index]

    def __setitem__(self, index, value) -> None:
        self.organisations[index] = value

    def __delitem__(self, index) -> None:
        del self.organisations[index]

    def __len__(self) -> int:
        return len(self.organisations)

    def insert(self, index, value) -> None:
        self.organisations.insert(index, value)

    @property
    def organisations(self,
                      *args: QueryParameters,
                      **kwargs: QueryParameters) -> OrganisationSequence:
        if not hasattr(self, '_organisations'):
            reader_dict_args: QueryParameters = {**self.data_reader_params,
                                                 **kwargs}
            org_entry_args: QueryParameters = {
                    **self.organisation_entry_params, **kwargs}
            self._organisations: OrganisationSequence = [
                    OrganisationEntry(org, **org_entry_args)
                    for _, org in self.data_reader(*args, **reader_dict_args)]
        return self._organisations

    @property
    def company_client(self,
                       *args: QueryParameters,
                       **kwargs: QueryParameters) -> Graph:
        if not hasattr(self, "_company_client"):
            self._company_client = (
                    self._OrganisationSequence__company_client_class(
                        **self.company_client_params
                    ))
            # self.__company_client = self.__company_client_class(
            # )
            # self._test_client = self.__company_client_class
        # assert False
        # return self._company_client.get_networks(*args, **kwargs)
        return self._company_client

    # @property
    # def company_client(self,
    #                    *args: QueryParameters,
    #                    **kwargs: QueryParameters) -> Graph:
    #     if not hasattr(self, "_company_client"):
    #         self._company_client = (
    #                 self._OrganisationSequence__company_client_class(
    #                     **self.company_client_params
    #                 ))
    #         # self.__company_client = self.__company_client_class(
    #         # )
    #         # self._test_client = self.__company_client_class
    #     # assert False
    #     return self._company_client.get_networks(*args, **kwargs)

    @property
    def _charity_client(self,
                        *args: QueryParameters,
                        **kwargs: QueryParameters) -> Graph:
        return self.__charity_client(*args, **kwargs,
                                     **self.charity_client_params)

    def _get_charity_networks(self,
                              *args: QueryParameters,
                              **kwargs: QueryParameters,
                              ) -> None:
        """Iterate organisations' ``charity_id`` and query their networks."""
        for organisation in self:
            if organisation.charity_id and (
                    not hasattr(organisation, 'charity_network') or
                    organisation.charity_network is None):
                logger.info(f'Querying charity {organisation.charity_id} '
                            f'for {organisation.name}...')
                dict_args = {**self.charity_client_params, **kwargs}
                self._charity_runs.append(
                        {'root_charity_id': organisation.charity_id,
                         'start_time': datetime.now(),
                         'end_time': None,
                         'kinds_ids_dict': None,
                         # Params need apprasing for inclusion of locals
                         'parameter_state': self.charity_client_params,
                         'connected_components_count': None,
                         })

                network: Optional[Graph] = self._charity_client(
                        organisation.charity_id, *args, **dict_args)
                self._charity_runs[-1]['end_time'] = datetime.now()
                # self._charity_runs[-1]['kinds_ids_dict']
                self._charity_runs['connected_components_count'] = (
                        number_connected_components(network)
                        )
                setattr(organisation, 'charity_network', network)

    def _get_company_networks(self,
                              *args: QueryParameters,
                              **kwargs: QueryParameters) -> None:
        for organisation in self:
            if organisation.company_id and (
                    not hasattr(organisation, 'company_network') or
                    organisation.company_network is None):
                logger.info(f'Querying company {organisation.company_id} '
                            f'for {organisation.name}...')
                # dict_args = {**self.company_client_params, **kwargs}
                # network: Optional[Graph] = self.company_client.get_network(
                #         organisation.company_id, *args, **dict_args)
                network: Optional[Graph] = self.company_client.get_network(
                        organisation.company_id, *args, **kwargs)
                self._company_runs.append(self._company_client._runs[-1])
                setattr(organisation, 'company_network', network)

    @property
    def charity_network(self,
                        *args: QueryParameters,
                        **kwargs: QueryParameters) -> Graph:
        if not hasattr(self, '_charity_network'):
            self._get_charity_networks(*args, **kwargs)
            self._charity_network: Graph = compose_all(
                    o.charity_network for o in self.organisations
                    if hasattr(o, 'charity_network'))
        return deepcopy(self._charity_network)

    @property
    def company_network(self,
                        *args: QueryParameters,
                        **kwargs: QueryParameters) -> Graph:
        """Return a deepcopy of a composition of all company graphs.

        Todo:
            * Consider ways to avoid confusion of charity graphs are
              independent but company graphs are not by default.
            * Consider taking advantage of just passing a list of company_ids
        """
        if not hasattr(self, '_company_network'):
            self._get_company_networks(*args, **kwargs)
            self._company_network: Graph = deepcopy(
                    # Assuming ``_graph`` is best state to work with
                    self.company_client._graph
                    )
        return deepcopy(self._company_network)

    def get_networks(self,
                     records: Optional[int] = None,
                     start_entry: int = 0,
                     log_to_file: bool = True) -> Tuple[Optional[Graph],
                                                        Optional[Graph]]:
        # if logging_level:
        #     logger.setLevel(logging_level)
        # if log_path != LOG_PATH:
        #     # logging_level = logging_level or logging.DEBUG
        #     log_path = Path(log_path)
        #     log_path.parent.mkdir(exist_ok=True, parents=True)
        #     if reset_log:
        #         file_handler = logging.FileHandler(log_path, mode='w')
        #     else:
        #         file_handler = logging.FileHandler(log_path)
        #     file_handler.setLevel(logging_level)
        #     logger.addHandler(file_handler)
        # if not self.organisations_list:
        #     organisations_list = get_organisations_list(csv_path,
        #     csv_encoding)
        # records = records or len(organisations_list)
        if log_to_file:
            add_file_logger()
        records = records or len(self)
        start = time.localtime()
        logger.info(f'Start: {time.strftime(LOG_TIME_FORMAT, start)}')
        if start_entry:
            logger.info(f'Beginning with record {start_entry}')
        try:
            for i, organisation in enumerate(self[start_entry:records]):
                # if i % 10 is 0:
                # Sort out printing timing estimates
                # deciles = time.localtime()
                # logger.info('Average time per organisation: {}'.format(
                # ))
                logger.info(f'{organisation.name:80} {i+1}/'
                            f'{records-start_entry}')
                # organisation._get_networks(branches)
                print()
        finally:
            end = time.localtime()
            logger.info(f'End: {time.strftime(LOG_TIME_FORMAT, end)}')
            logger.info(f'Total Time: '
                        f'{time.strftime(LOG_TIME_FORMAT, end - start)}')
        # if pickle_path:
        #     with open(pickle_path, 'wb') as pickle_file:
        #         pickle.dump(organisations_list, pickle_file)
        return self._company_network, self._charity_network
