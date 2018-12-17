# -*- coding: utf-8 -*-

"""CLI tool for allocine"""
import sys
import click
import allocine
from prettytable import PrettyTable #, UNICODE

# Usage : allocine_cli.py --help


def extract_field_names(dict_list):
    """ Returns a sorted list of field names from a dictionary list
    > extract_field_names([{'a': 1, 'b': 2}, {'a': 3, 'c': 4}])
    ['a', 'b', 'c']
    """
    field_names = []
    for row_dict in dict_list:
        field_names += row_dict.keys()
    field_names = list(set(field_names))  # Removes duplicates
    return sorted(field_names)  # sort it in ascending order


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
    # required=True,
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
    x = PrettyTable()
    # x.set_style(UNICODE)
    x.header = False

    seances = [{'*film': 'L’Exorcisme de Hannah Grace',
            '09': '09:00', '11': '11:10', '14': '14:50', '16': '16:45', '20': '20:35',
            '22': '22:30'},
           {'*film': 'Pupille',
            '11': '11:40', '13': '13:50', '16': '16:00', '18': '18:10',
            '20': '20:20', '22': '22:30'},
           {'*film': 'Titanic',
            '09': '09:30', '11': '11:50', '18': '18:20',
            '20': '20:00'}]

    x.field_names = extract_field_names(seances)

    for seances_film in seances:
        row = []
        for field_name in x.field_names:
            row.append(seances_film.get(field_name, ""))
        x.add_row(row)

    x.align["*film"] = "l"

    print(x)


if __name__ == "__main__":
    main()
