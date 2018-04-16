#!/usr/bin/env python

import os

from d_collector.__main__ import __version__
from setuptools           import setup, find_packages

setup(
    name='distributed-collector',
    version=__version__,
    description='Distributed Collector transmits to Kafka cluster already processed '
        'files in a comma-separated (CSV) output format.',
    author='Space Hellas S.A.',
    author_email='ktzoulas@gmail.gr',
    url='https://www.space.gr/',
    license='Apache License 2.0',
    packages=find_packages(),
    install_requires=open('requirements.txt').read().strip().split('\n'),
    entry_points={ 'console_scripts': ['dc = d_collector.__main__:main'] },
    data_files=[(os.path.expanduser('~'), ['.d-collector.json'])]
)
