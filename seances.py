#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CLI tool for allocine"""
import click
from allocine import Allocine
from prettytable import PrettyTable, UNICODE, FRAME, ALL
from datetime import date, timedelta, datetime

# Usage : seances.py --help


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
@click.argument(
    'id_cinema',
    type=str,
    required=True
)
@click.option(
    '--jour', '-j',
    type=str,
    help="jour des séances souhaitées \
(au format DD/MM/YYYY ou +1 pour demain), par défaut : aujourd’hui",
)
@click.option(
    '--semaine', '-s',
    is_flag=True,
    help='affiche les séance pour les 7 prochains jours',
)
@click.option(
    '--entrelignes', '-e',
    is_flag=True,
    help='ajoute une ligne entre chaque film pour améliorer la lisibilité',
)
def main(id_cinema, entrelignes, jour=None, semaine=None):
    """
    Les séances de votre cinéma dans le terminal, avec
    ID_CINEMA : identifiant du cinéma sur Allociné,
    ex: C0159 pour l’UGC Ciné Cité Les Halles. Se trouve dans l’url :
    http://allocine.fr/seance/salle_gen_csalle=<ID_CINEMA>.html
    """
    today = date.today()
    allocine = Allocine()

    jours = []
    if semaine is False:
        if jour is None:
            jours.append(today.strftime("%d/%m/%Y"))
        elif jour[0] == '+':
            delta_jours = int(jour[1:])
            jour_obj = today + timedelta(days=delta_jours)
            jours.append(jour_obj.strftime("%d/%m/%Y"))
        else:
            jours.append(jour)
    else:
        for delta in range(0, 7):
            jour_obj = today + timedelta(days=delta)
            jours.append(jour_obj.strftime("%d/%m/%Y"))

    theater = allocine.get_theater(theater_id=id_cinema)

    print('{}, le '.format(theater.name), end='')
    for jour in jours:
        print(get_showtime_table(
            theater=theater,
            entrelignes=entrelignes,
            jour=jour)
        )
        print()


def get_showtime_table(theater, entrelignes, jour):
    showtime_table = []

    date_obj = datetime.strptime(jour, '%d/%m/%Y').date()
    movies_available_today = theater.get_movies_available_for_a_day(date=date_obj)

    for movie_version in movies_available_today:

        title = movie_version.title
        if len(title) >= 31:  # On tronque les titres trop longs
            title = title[:31] + '...'

        # '*1_film' pour être sûr que cela soit la 1ère colonne
        movie_row = {'*1_film': "{} ({}) - {}".format(
            title,
            movie_version.version,
            movie_version.duration_str)}

        movie_row['*2_note'] = "{}*".format(movie_version.rating_str)

        showtimes = theater.get_showtimes_of_a_movie(
            movie_version=movie_version, date=date_obj)

        for showtime in showtimes:
            hour = showtime.hour_str.split(':')[0]  # 11:15 => 11
            movie_row[hour] = showtime.hour_str

        showtime_table.append(movie_row)

    seances = showtime_table

    retour = "{}\n".format(jour)

    if len(seances) <= 0:
        retour += "Aucune séance"

    else:
        table = PrettyTable()
        table.set_style(UNICODE)
        table.header = False

        if entrelignes is True:
            table.hrules = ALL
        else:
            table.hrules = FRAME

        table.field_names = extract_field_names(seances)

        for seances_film in seances:
            row = []
            for field_name in table.field_names:
                row.append(seances_film.get(field_name, ""))
            table.add_row(row)

        table.align["*1_film"] = "l"
        table.sortby = "*1_film"
        retour += str(table)

    return retour


if __name__ == "__main__":
    main()
