# -*- coding: utf-8 -*-

"""Console script for ukboards."""

from json import dumps
from logging import getLogger
from sys import exit
from typing import Optional

import click
from dotenv import dotenv_values
from zeep import Client

from .charities import (
    CHARITY_COMMISSION_API_KEY,
    CHARITY_COMMISSION_API_KEY_ENV_NAME,
    CharityIDType,
    get_client,
)
from .companies import (
    COMPANIES_HOUSE_API_KEY,
    COMPANIES_HOUSE_API_KEY_ENV_NAME,
    CompanyIDType,
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


@click.group(name="ukboards")
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
def ukboards(
    ctx: click.Context, indent: int, api_keys_path: click.Path
) -> int:
    """Query UK company and charity board data."""
    ctx.ensure_object(dict)
    if api_keys_path:
        try:
            api_keys: APIKeyDictType = dotenv_values(api_keys_path)
            for key_name, key in api_keys.items():
                ctx.obj[key_name] = key
        except FileNotFoundError:
            pass
            # Todo: * Add opitions for generating an .env file for API keys.
            # path = input("No file provided for Companies House or "
            #              "Charities Commission API keys. Press enter to "
            #              f"create a default '{DEFAULT_API_KEY_PATH}' file "
            #              "in this folder or type your preferred filename "
            #              "(or CTL+C to quit): ")
    ctx.obj["indent"] = indent
    return 0


@ukboards.command()
@click.argument("charity_id", type=CharityIDType, nargs=1)
@click.option(
    "--api-key",
    "-k",
    "api_key",
    type=CharityAPIKeyType,
    nargs=1,
    default=CHARITY_COMMISSION_API_KEY,
)
@click.pass_context
def charity(
    ctx: click.Context, charity_id: CharityIDType, api_key: CharityAPIKeyType
) -> None:
    """Query Charities Commision by charity id."""
    if CHARITY_COMMISSION_API_KEY_ENV_NAME in ctx.obj:
        api_key = ctx.obj[CHARITY_COMMISSION_API_KEY]
    client: Client = get_client(api_key_value=api_key)
    charity_data = client.service.GetCharityByRegisteredCharityNumber(
        registeredCharityNumber=charity_id,
    )
    click.echo(charity_data)


@ukboards.command()
@click.argument("company_id", type=CompanyIDType, nargs=1)
@click.option(
    "--api-key",
    "-k",
    "api_key",
    type=CompanyAPIKeyType,
    nargs=1,
    default=COMPANIES_HOUSE_API_KEY,
)
@click.pass_context
def company(
    ctx: click.Context, company_id: CompanyIDType, api_key: CompanyAPIKeyType
) -> None:
    """Query Companies House by company id."""
    if COMPANIES_HOUSE_API_KEY_ENV_NAME in ctx.obj:
        api_key = ctx.obj[COMPANIES_HOUSE_API_KEY_ENV_NAME]
    company_json: Optional[JSONDict] = companies_house_query(
        f"/company/{company_id}", auth_key=api_key
    )
    click.echo(dumps(company_json, indent=ctx.obj["indent"]))


@ukboards.command()
@click.argument("csv_path", type=click.Path(exists=True), nargs=1)
def csv_organisations(csv_path: click.Path):
    """Path to csv with company and charity ids."""
    pass


if __name__ == "__main__":
    exit(ukboards(obj={}))  # pragma: no cover
