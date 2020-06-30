#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent
reqs_path = HERE / 'requirements.txt'
with open(reqs_path) as reqs_file:
    requirements = reqs_file.read().splitlines()

__version__ = '0.0.12'  # Should match with __init.py__
_GITHUB_URL = 'https://github.com/tducret/allocine-python'
_KEYWORDS = ['api', 'allocine', 'parsing',
             'python-wrapper', 'scraping', 'scraper', 'parser']
_SCRIPTS = ['seances.py']

setup(
    name='allocine',
    packages=find_packages(),
    package_data={},
    scripts=_SCRIPTS,
    version=__version__,
    license="MIT license",
    platforms='Posix; MacOS X',
    description="Non official Python wrapper for allocine.fr",
    long_description="Non official Python wrapper for allocine.fr",
    author="Thibault Ducret",
    author_email='hello@tducret.com',
    url=_GITHUB_URL,
    download_url='{github_url}/tarball/{version}'.format(
                                                github_url=_GITHUB_URL,
                                                version=__version__),
    keywords=_KEYWORDS,
    setup_requires=requirements,
    install_requires=requirements,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.7',
    tests_require=['pytest'],
)

# ------------------------------------------
# To upload a new version on pypi
# ------------------------------------------
# Make sure everything was pushed (with a git status)
# (or git commit --am "Comment" and git push)
# export VERSION=0.0.12; git tag $VERSION -m "Normalisation des nationalités + fallback et warning si introuvable"; git push --tags

# If you need to delete a tag
# git push --delete origin $VERSION; git tag -d $VERSION
