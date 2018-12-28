# Allociné

[![Travis](https://img.shields.io/travis/tducret/allocine-python.svg)](https://travis-ci.org/tducret/allocine-python)
[![Coveralls github](https://img.shields.io/coveralls/github/tducret/allocine-python.svg)](https://coveralls.io/github/tducret/allocine-python)
[![PyPI](https://img.shields.io/pypi/v/allocine.svg)](https://pypi.org/project/allocine/)
![License](https://img.shields.io/github/license/tducret/allocine-python.svg)

![Cinéma](cinema.jpg)

## Description

**Avec cet outil, vous récupérez les horaires des séances ciné directement dans le terminal**.

## Requirements

- Python 3.5
- pip3

## Installation

```bash
pip3 install -U allocine
```
## CLI tool usage

![Capture terminal](capture.svg)

#### Help

```bash
seances.py --help
Usage: seances.py [OPTIONS] ID_CINEMA

  Les séances de votre cinéma dans le terminal, avec ID_CINEMA : identifiant
  du cinéma sur Allociné, ex: C0159 pour l’UGC Ciné Cité Les Halles. Se
  trouve dans l’url :
  http://allocine.fr/seance/salle_gen_csalle=<ID_CINEMA>.html

Options:
  -j, --jour TEXT    jour des séances souhaitées (au format DD/MM/YYYY ou +1
                     pour demain), par défaut : aujourd’hui
  -s, --semaine      affiche les séance pour les 7 prochains jours
  -e, --entrelignes  ajoute une ligne entre chaque film pour améliorer la
                     lisibilité
  --help             Show this message and exit.
```

#### Basic usage

```bash
seances.py P2235

MJC Ciné 113, le 27/12/2018
┌──────────────────────────────────────────────────────────┬──────┬───────┬───────┬───────┬───────┐
│ Astérix - Le Secret de la Potion Magique... (VF) - 01h25 │ 4.1* │ 10:15 │       │       │       │
│ L’Empereur de Paris (VF) - 01h50                         │ 3.4* │       │       │ 17:15 │       │
│ Ma mère est folle (VF) - 01h35                           │ 3.0* │       │ 14:15 │       │       │
│ Marche ou crève (VF) - 01h25                             │ 3.6* │       │       │       │ 20:15 │
└──────────────────────────────────────────────────────────┴──────┴───────┴───────┴───────┴───────┘
```

#### For tomorrow, with interlines

```bash
seances.py P2235 -j+1 --entrelignes

MJC Ciné 113, le 28/12/2018
┌────────────────────────────────────────────────────┬──────┬───────┬───────┬───────┐
│ Casse-noisette et les quatre royaumes (VF) - 01h39 │ 3.1* │       │       │ 20:15 │
├────────────────────────────────────────────────────┼──────┼───────┼───────┼───────┤
│ Ma mère est folle (VF) - 01h35                     │ 3.0* │       │ 17:15 │       │
├────────────────────────────────────────────────────┼──────┼───────┼───────┼───────┤
│ Marche ou crève (VF) - 01h25                       │ 3.6* │ 14:15 │       │       │
└────────────────────────────────────────────────────┴──────┴───────┴───────┴───────┘
```

#### For a specific date

```bash
seances.py P2235 --jour 29/12/2018
```

#### For the full week

```bash
seances.py P2235 --semaine
```

## Package usage

```python
# -*- coding: utf-8 -*-
from allocine import Allocine

a = Allocine(theater_id="P2235")

for showtime in a.theater.program.showtimes:
    print(showtime)
```

Example output :

```bash
27/12/2018 10:15 : Astérix - Le Secret de la Potion Magique [244560] (VF) (01h25)
27/12/2018 14:15 : Ma mère est folle [260370] (VF) (01h35)
27/12/2018 17:15 : L’Empereur de Paris [258914] (VF) (01h50)
27/12/2018 20:15 : Marche ou crève [258052] (VF) (01h25)
28/12/2018 14:15 : Marche ou crève [258052] (VF) (01h25)
28/12/2018 17:15 : Ma mère est folle [260370] (VF) (01h35)
28/12/2018 20:15 : Casse-noisette et les quatre royaumes [245656] (VF) (01h39)
29/12/2018 14:15 : Astérix - Le Secret de la Potion Magique [244560] (VF) (01h25)
[...]
```

## TODO

- [ ] Automate Docker image generation on Docker Hub
- [ ] Add docker image usage
