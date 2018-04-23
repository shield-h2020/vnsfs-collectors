#!/usr/bin/env python

import os

from d_collector.__main__ import __version__
from setuptools           import setup, find_packages

with open('README.md') as fp:
    README = fp.read()

setup(
    name='d-collector',
    version=__version__,
    author='Space Hellas S.A.',
    author_email='ggar@space.gr',
    url='https://www.space.gr/',
    license='Apache License 2.0',
    description='Distributed Collector transmits to Kafka cluster already processed '
        'files in a comma-separated (CSV) output format.',
    long_description=README,
    keywords="spot shield distributed collector d-collector",
    packages=find_packages(),
    install_requires=open('requirements.txt').read().strip().split('\n'),
    entry_points={ 'console_scripts': ['d-collector = d_collector.__main__:main'] },
    data_files=[(os.path.expanduser('~'), ['.d-collector.json'])]
)
