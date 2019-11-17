# -*- coding: utf-8 -*-

"""Console script for uk_boards."""

import json
import sys
import click

from .companies import companies_house_query


@click.group()
# @click.option('--api-keys-path', '-a', type=click.Path(exists=True),
#               envvar='UK_BOARD_KEYS', default='.env', nargs=1,
#               help='Path to file with API keys (default=.env)')
@click.option('--indent', '-i', type=int, nargs=1, default=2,
              show_default=True,
              help='How many spaces to indent printing json queries.')
@click.pass_context
def main(ctx, indent):
    """Console script for uk_boards."""
    ctx.ensure_object(dict)

    ctx.obj['indent'] = indent
    # ctx.obj['api_keys_path'] = api_keys_path
    # click.echo(api_keys_path)
    return 0


@main.command()
@click.argument('company_number', type=str, nargs=1)
@click.pass_context
def company(ctx, company_number):
    """Query Companies House by company number."""
    company_json = companies_house_query(f'/company/{company_number}')
    click.echo(json.dumps(company_json, indent=ctx.obj['indent']))


@main.command()
@click.argument('csv_path', type=click.Path(exists=True), nargs=1)
def csv_organisations(csv_path):
    """Path to csv with company and charity numbers."""
    pass


if __name__ == "__main__":
    sys.exit(main(obj={}))  # pragma: no cover
