# -*- coding: utf-8 -*-

"""Console script for uk_boards."""

from json import dumps
from logging import getLogger
from sys import exit
from typing import Optional

import click
from dotenv import dotenv_values
from zeep import Client

from .charities import (
    CHARITY_COMMISSION_API_KEY,
    CHARITY_COMMISSION_API_KEY_NAME,
    get_client,
)
from .companies import (
    COMPANIES_HOUSE_API_KEY,
    COMPANIES_HOUSE_API_KEY_NAME,
    companies_house_query,
)
from .utils import (
    DEFAULT_API_KEY_PATH,
    APIKeyDictType,
    CharityAPIKeyType,
    CompanyAPIKeyType,
    JSONDict,
)

logger = getLogger(__name__)


@click.group(name="uk_boards")
@click.option(
    "--api-keys-path",
    "-a",
    "api_keys_path",
    type=click.Path(dir_okay=False, file_okay=True),
    envvar="UK_BOARD_KEYS",
    default=DEFAULT_API_KEY_PATH,
    nargs=1,
    help="Path to file with API keys (default=.env)",
)
@click.option(
    "--indent",
    "-i",
    type=int,
    nargs=1,
    default=2,
    show_default=True,
    help="How many spaces to indent printing json queries.",
)
@click.pass_context
def uk_boards(
    ctx: click.Context, indent: int, api_keys_path: click.Path
) -> int:
    """Console interface for uk_boards.

    Todo:
        * Add opitions for generating an .env file for API keys
    """
    ctx.ensure_object(dict)
    if api_keys_path:
        try:
            api_keys: APIKeyDictType = dotenv_values(api_keys_path)
            for key_name, key in api_keys.items():
                ctx.obj[key_name] = key
        except FileNotFoundError:
            pass
            # path = input("No file provided for Companies House or "
            #              "Charities Commission API keys. Press enter to "
            #              f"create a default '{DEFAULT_API_KEY_PATH}' file "
            #              "in this folder or type your preferred filename "
            #              "(or CTL+C to quit): ")
    ctx.obj["indent"] = indent
    return 0


@uk_boards.command()
@click.argument("charity_number", type=str, nargs=1)
@click.option(
    "--api-key",
    "-k",
    "api_key",
    type=CharityAPIKeyType,
    nargs=1,
    default=CHARITY_COMMISSION_API_KEY,
)
@click.pass_context
def charity(ctx: click.Context, charity_number: str, api_key: str) -> None:
    """Query Charities Commision by registered charity number."""
    if CHARITY_COMMISSION_API_KEY_NAME in ctx.obj:
        api_key = ctx.obj[CHARITY_COMMISSION_API_KEY]
    client: Client = get_client(api_key_value=api_key)
    charity_data = client.service.GetCharityByRegisteredCharityNumber(
        registeredCharityNumber=charity_number,
    )
    click.echo(charity_data)


@uk_boards.command()
@click.argument("company_number", type=str, nargs=1)
@click.option(
    "--api-key",
    "-k",
    "api_key",
    type=CompanyAPIKeyType,
    nargs=1,
    default=COMPANIES_HOUSE_API_KEY,
)
@click.pass_context
def company(ctx: click.Context, company_number: str, api_key: str) -> None:
    """Query Companies House by company number."""
    if COMPANIES_HOUSE_API_KEY_NAME in ctx.obj:
        api_key = ctx.obj[COMPANIES_HOUSE_API_KEY_NAME]
    company_json: Optional[JSONDict] = companies_house_query(
        f"/company/{company_number}", auth_key=api_key
    )
    click.echo(dumps(company_json, indent=ctx.obj["indent"]))


@uk_boards.command()
@click.argument("csv_path", type=click.Path(exists=True), nargs=1)
def csv_organisations(csv_path: click.Path):
    """Path to csv with company and charity numbers."""
    pass


if __name__ == "__main__":
    exit(uk_boards(obj={}))  # pragma: no cover
