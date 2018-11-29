'''
    Internal subroutines for e.g. executing commands and initializing
:class:`logging.Logger` objects.
'''

import logging
import os
import signal
import subprocess
import sys

from logging.handlers import RotatingFileHandler
from multiprocessing  import current_process

def authenticate(**kwargs):
    '''
        Authentication via Kerberos.
    '''
    logger     = logging.getLogger('SHIELD.DC.UTILS')
    kinit      = kwargs.get('kinit')
    if os.getenv('KINITPATH'):
        kinit = os.getenv('KINITPATH')

    kinit_opts = os.getenv('KINITOPTS') or ''
    key_tab    = '-kt {0}'.format(kwargs.get('keytab'))
    krb_user   = kwargs.get('principal')

    if not (kinit and key_tab and krb_user):
        raise EnvironmentError('Please, verify Kerberos configuration.')

    command    = '{0} {1} {2} {3}'.format(kinit, kinit_opts, key_tab, krb_user)
    logger.debug('Execute command: {0}'.format(command))

    call(command, shell=True)
    logger.info('Kerberos ticket obtained!')

def call(cmd, shell=False):
    '''
        Run command with arguments, wait to complete and return ``True`` on success.

    :param cmd: Command string to be executed.
    :returns  : ``True`` on success, otherwise ``None``.
    :rtype    : ``bool``
    '''
    logger = logging.getLogger('SHIELD.DC.UTILS')
    logger.debug('Execute command: {0}'.format(cmd))

    try:
        subprocess.call(cmd, shell=shell)
        return True

    except Exception as exc:
        logger.error('[{0}] {1}'.format(exc.__class__.__name__, exc.message))

def get_logger(name, level='INFO', filepath=None, fmt=None):
    '''
        Return a new logger or an existing one, if any.

    :param name    : Return a logger with the specified name.
    :param filepath: Path of the file, where logs will be saved. If it is not set,
                     redirects the log stream to `sys.stdout`.
    :param fmt     : A format string for the message as a whole, as well as a format
                     string for the date/time portion of the message.
                     Default: '%(asctime)s %(levelname)-8s %(name)-32s %(message)s'
    :rtype         : :class:`logging.Logger`
    '''
    logger = logging.getLogger(name)
    # .................................if logger already exists, return it
    if logger.handlers: return logger

    if filepath:
        # .............................rotate log file (1 rotation per 512KB)
        handler = RotatingFileHandler(filepath, maxBytes=524288, backupCount=8)
    else:
        handler = logging.StreamHandler(sys.stdout)

    fmt = fmt or '%(asctime)s %(levelname)-8s %(name)-32s %(message)s'
    handler.setFormatter(logging.Formatter(fmt))

    try:
        logger.setLevel(getattr(logging, level.upper() if level else 'INFO'))
    except: logger.setLevel(logging.INFO)

    logger.addHandler(handler)
    return logger

def init_child(tmpdir):
    '''
        Initialize new process from multiprocessing module's Pool.

    :param tmpdir: Path of local staging area.
    '''
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # .................................for each process, create an isolated temp folder
    proc_dir = os.path.join(tmpdir, current_process().name)

    if not os.path.isdir(proc_dir):
        os.mkdir(proc_dir)

def popen(cmd, cwd=None, raises=False):
    '''
        Execute the given command string in a new process. Send data to stdin and read
    data from stdout and stderr, until end-of-file is reached.

    :param cwd     : If it is set, then the child's current directory will be change to
                     `cwd` before it is executed.
    :param raises  : If ``True`` and stderr has data, it raises an ``OSError`` exception.
    :returns       : The output of the given command; pair of (stdout, stderr).
    :rtype         : ``tuple``
    :raises OSError: If `raises` and stderr has data.
    '''
    logger   = logging.getLogger('SHIELD.DC.UTILS')
    parser   = lambda x: [] if x == '' else [y.strip() for y in x.strip().split('\n')]

    logger.debug('Execute command: {0}'.format(cmd))
    process  = subprocess.Popen(cmd, shell=True, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    # .................................trim lines and remove the empty ones
    _stdout  = [x for x in parser(out) if bool(x)]
    _stderr  = [x for x in parser(err) if bool(x)]

    if _stderr and raises:
        raise OSError('\n'.join(_stderr))

    return _stdout, _stderr
