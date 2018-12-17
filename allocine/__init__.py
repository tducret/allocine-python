# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

import requests
from requests import ConnectionError
from dataclasses import dataclass
from typing import List
from datetime import datetime

__author__ = """Thibault Ducret"""
__email__ = 'hello@tducret.com'
__version__ = '0.0.1'

_DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


class Client(object):
    """ Do the requests with the servers """
    def __init__(self):
        self.session = requests.session()
        self.headers = {
                    'Host': 'myhost.com',
                    'User-Agent': 'User agent',
                    }

    def _get(self, url, expected_status_code=200):
        ret = self.session.get(url=url, headers=self.headers)
        if (ret.status_code != expected_status_code):
            raise ConnectionError(
                'Status code {status} for url {url}\n{content}'.format(
                    status=ret.status_code, url=url, content=ret.text))
        return ret

    def _post(self, url, post_data, expected_status_code=200):
        ret = self.session.post(url=url,
                                headers=self.headers,
                                data=post_data)
        if (ret.status_code != expected_status_code):
            raise ConnectionError(
                'Status code {status} for url {url}\n{content}'.format(
                    status=ret.status_code, url=url, content=ret.text))
        return ret


@dataclass
class Movie:
    id: int
    title: str


@dataclass
class Theater:
    id: int
    name: str


@dataclass
class Showtime:
    datetime_str: str

    def __post_init__(self):
        self.datetime_obj = self._str_datetime_to_datetime_obj(
            datetime_str=self.datetime_str)
        self.hour = self._get_hour_str(self.datetime_obj)

    @staticmethod
    def _get_hour_str(datetime_obj):
        return str(datetime_obj.strftime("%H:%M"))

    @staticmethod
    def _str_datetime_to_datetime_obj(datetime_str,
                                      date_format=_DEFAULT_DATE_FORMAT):
        return datetime.strptime(datetime_str, date_format)


@dataclass
class MovieShowtimes:
    movie: Movie
    theater: Theater
    showtimes: List[Showtime]


class MyClass(object):
    """ Class to... """
    def __init__(self, param1, list1, dict1):
        self.param1 = param1
        self.list1 = list1
        self.dict1 = dict1

    def get_param1(self):
        """ Get the param1 """
        return(self.param1)

    def __str__(self):
        return('{}'.format(self.param1))

    def __repr__(self):
        return("Myclass(param1={})".format(self.param1))

    def __len__(self):
        return len(self.list1)

    def __getitem__(self, key):
        """ Méthod to access the object as a list
        (ex : list1[1]) """
        return self.list[key]

    def __getattr__(self, attr):
        """ Method to access a dictionnary key as an attribute
        (ex : dict1.my_key) """
        return self.dict1.get(attr, "")
