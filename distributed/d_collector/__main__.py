#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
    Main command-line entry point.
'''

__version__ = '0.9.8b0'

import json
import os
import pipelines
import sys
import tempfile

from argparse        import ArgumentParser, HelpFormatter
from collector       import DistributedCollector
from multiprocessing import cpu_count
from utils           import authenticate, get_logger

STATE = {
    'file_watcher': {},
    'interval': 5,
    'kerberos': {},
    'local_staging': tempfile.gettempdir(),
    'process_opts': '',
    'processes': cpu_count(),
    'producer': {}
}

def main():
    try:
        args  = parse_args()
        conf  = json.loads(args.config_file.read())

        # .............................set up logger
        get_logger('SHIELD.DC', args.log_level)

        # .............................set up STATE
        conf.update(conf['pipelines'][args.type])
        del conf['pipelines']

        for key in conf.keys():
            if isinstance(conf[key], basestring) and conf[key].strip() == '':
                continue

            if key in STATE.keys():
                STATE[key] = conf[key]

        # .............................check kerberos authentication
        if os.getenv('KRB_AUTH'):
            authenticate(**STATE['kerberos'])

        # .............................instantiate Distributed Collector
        dc = DistributedCollector(args.type, args.topic, args.partition,
                args.skip_conversion, **STATE)

        dc.start()
    except SystemExit: raise
    except:
        sys.excepthook(*sys.exc_info())
        sys.exit(1)

def parse_args():
    '''
        Parse command-line options found in 'args' (default: sys.argv[1:]).

    :returns: On success, a namedtuple of Values instances.
    '''
    parser   = ArgumentParser(
        prog='d-collector',
        description='Distributed Collector transmits to Kafka cluster already processed '
            'files in a comma-separated (CSV) output format.',
        epilog='END',
        formatter_class=lambda prog: HelpFormatter(prog, max_help_position=36, width=80),
        usage='d-collector [OPTIONS]... -t <pipeline> --topic <topic>')

    # .................................set optional arguments
    parser._optionals.title = 'Optional Arguments'

    parser.add_argument('-c', '--config-file', metavar='FILE', type=file,
        default=os.path.expanduser('~/.d-collector.json'),
        help='path of configuration file')

    parser.add_argument('-l', '--log-level', metavar='STRING', default='INFO',
        help='determine the level of the logger')

    parser.add_argument('-p', '--partition', metavar='INTEGER', default=None, type=int,
        help='optionally specify a partition')

    parser.add_argument('-s', '--skip-conversion', action='store_true', default=False,
        help='no transformation will be applied to the data; useful for importing CSV files')

    parser.add_argument('-v', '--version', action='version', version='%(prog)s {0}'
        .format(__version__))

    # .................................set required arguments
    required = parser.add_argument_group('Required Arguments')

    required.add_argument('--topic', required=True, metavar='STRING',
        help='name of topic where the messages will be published')

    required.add_argument('-t', '--type', choices=pipelines.__all__, required=True,
        help='type of data that will be collected', metavar='STRING')

    return parser.parse_args()


if __name__ == '__main__': main()
