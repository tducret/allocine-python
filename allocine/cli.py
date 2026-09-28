"""Command-line interface for Allociné showtimes."""

from datetime import date, datetime, timedelta

import click
from prettytable import ALL, FRAME, UNICODE, PrettyTable

from allocine.client import Allocine
from allocine.schedules import get_showtimes_of_a_day


def clear_cache(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    with Allocine(cache=True) as allocine:
        removed = allocine.clear_cache()
    click.echo(f"Cache vidé ({removed} entrée(s)).")
    ctx.exit()


def extract_field_names(dict_list):
    """Return a sorted list of field names from a dictionary list."""
    field_names = []
    for row_dict in dict_list:
        field_names += row_dict.keys()
    field_names = list(set(field_names))
    return sorted(field_names)


@click.command()
@click.argument("id_cinema", type=str, required=True)
@click.option(
    "--clear-cache",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=clear_cache,
    help="vide entièrement le cache et quitte",
)
@click.option(
    "--jour",
    "-j",
    type=str,
    help="jour des séances souhaitées \
(au format DD/MM/YYYY ou +1 pour demain), par défaut : aujourd’hui",
)
@click.option(
    "--semaine",
    "-s",
    is_flag=True,
    help="affiche les séance pour les 7 prochains jours",
)
@click.option(
    "--entrelignes",
    "-e",
    is_flag=True,
    help="ajoute une ligne entre chaque film pour améliorer la lisibilité",
)
def main(id_cinema, entrelignes, jour=None, semaine=None):
    """
    Les séances de votre cinéma dans le terminal, avec
    ID_CINEMA : identifiant du cinéma sur Allociné,
    ex: C0159 pour l’UGC Ciné Cité Les Halles. Se trouve dans l’url :
    http://allocine.fr/seance/salle_gen_csalle=<ID_CINEMA>.html
    """
    today = date.today()
    allocine = Allocine(cache=True)

    jours = []
    if semaine is False:
        if jour is None:
            jours.append(today.strftime("%d/%m/%Y"))
        elif jour[0] == "+":
            delta_jours = int(jour[1:])
            jour_obj = today + timedelta(days=delta_jours)
            jours.append(jour_obj.strftime("%d/%m/%Y"))
        else:
            jours.append(jour)
    else:
        for delta in range(0, 7):
            jour_obj = today + timedelta(days=delta)
            jours.append(jour_obj.strftime("%d/%m/%Y"))

    requested_dates = [datetime.strptime(jour, "%d/%m/%Y").date() for jour in jours]
    showtimes = allocine.get_showtimes(
        theater_id=id_cinema,
        from_date=min(requested_dates),
        to_date=max(requested_dates),
    )
    theater = allocine.get_theater(theater_id=id_cinema)

    print("{}, le ".format(theater.name), end="")
    for jour in jours:
        print(get_showtime_table(showtimes=showtimes, entrelignes=entrelignes, jour=jour))
        print()


def get_showtime_table(showtimes, entrelignes, jour):
    showtime_table = []

    date_obj = datetime.strptime(jour, "%d/%m/%Y").date()
    day_showtimes = get_showtimes_of_a_day(showtimes, date=date_obj)
    movies_available_today = set(showtime.movie for showtime in day_showtimes)

    for movie_version in movies_available_today:
        title = movie_version.title
        if len(title) >= 31:  # On tronque les titres trop longs
            title = title[:31] + "..."

        # '*1_film' pour être sûr que cela soit la 1ère colonne
        movie_row = {"*1_film": "{} ({}) - {}".format(title, movie_version.version, movie_version.duration_str)}

        movie_row["*2_note"] = "{}*".format(movie_version.rating_str)

        for showtime in day_showtimes:
            if showtime.movie != movie_version:
                continue
            hour = showtime.hour_str.split(":")[0]  # 11:15 => 11
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
