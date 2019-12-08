# -*- coding: utf-8 -*-

"""Console script for uk_boards."""

import json
import sys

import click

from .companies import companies_house_query, COMPANIES_HOUSE_KEY
from .charities import get_client, CHARITY_COMMISSION_API_KEY


@click.group(name="uk_boards")
@click.option('--api-keys-path', '-a', type=click.Path(exists=True),
              envvar='UK_BOARD_KEYS', default='.env', nargs=1,
              help='Path to file with API keys (default=.env)')
@click.option('--indent', '-i', type=int, nargs=1, default=2,
              show_default=True,
              help='How many spaces to indent printing json queries.')
@click.pass_context
def uk_boards(ctx, indent, api_keys_path):
    """Console script for uk_boards."""
    ctx.ensure_object(dict)

    ctx.obj['indent'] = indent
    ctx.obj['api_keys_path'] = api_keys_path
    return 0


@uk_boards.command()
@click.argument('company_number', type=str, nargs=1)
@click.option('--api-key', '-k', 'api_key', type=str, nargs=1,
              default=COMPANIES_HOUSE_KEY)
@click.pass_context
def company(ctx, company_number, api_key):
    """Query Companies House by company number."""
    # company_json = companies_house_query(f'/company/{company_number}',
    #                                      auth_key=ctx.obj['api-key'])
    company_json = companies_house_query(f'/company/{company_number}',
                                         auth_key=api_key)

    click.echo(json.dumps(company_json, indent=ctx.obj['indent']))


@uk_boards.command()
@click.argument('charity_number', type=str, nargs=1)
@click.option('--api-key', '-k', type=str, nargs=1,
              default=CHARITY_COMMISSION_API_KEY)
@click.pass_context
def charity(ctx, charity_number, api_key):
    """Query Charities Commision by registered charity number."""
    client = get_client(api_key)
    charity_data = client.service.GetCharityByRegisteredCharityNumber(
        registeredCharityNumber=charity['RegisteredCharityNumber'],)
    click.echo(json.dumps(charity_data, indent=ctx.obj['indent']))


@uk_boards.command()
@click.argument('csv_path', type=click.Path(exists=True), nargs=1)
def csv_organisations(csv_path):
    """Path to csv with company and charity numbers."""
    pass


if __name__ == "__main__":
    sys.exit(uk_boards(obj={}))  # pragma: no cover
