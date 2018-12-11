# -*- coding: utf-8 -*-

"""CLI tool for allocine"""
import sys
import click
import allocine

# Usage : allocine_cli.py --help


@click.command()
@click.option(
    '--paramwithenvvar', '-p',
    envvar="PARAM1",
    type=str,
    help='example string param (or set the env var PARAM1)',
)
@click.option(
    '--paramwithdefaultvalue', '-d',
    type=str,
    help='example param with default value',
    default='fr',
    show_default=True,
)
@click.option(
    '--requiredparam', '-f',
    type=str,
    help='param required',
    required=True,
)
@click.option(
    '--flagparam',
    is_flag=True,
    help='flag param (True if set, False if not)',
)
@click.option(
    '--choiceparam',
    type=click.Choice(['val1', 'val2'])
)
def main(paramwithenvvar, paramwithdefaultvalue, requiredparam, flagparam,
         choiceparam):
    """
    !!! TO BE UPDATED !!!
    Description of the CLI tool,
    will be used in the --help
    """
    print()

if __name__ == "__main__":
    main()
