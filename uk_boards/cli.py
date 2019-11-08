# -*- coding: utf-8 -*-

"""Console script for uk_boards."""
import sys
import click


@click.command()
def main(args=None):
    """Console script for uk_boards."""
    click.echo("Replace this message by putting your code into "
               "uk_boards.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
