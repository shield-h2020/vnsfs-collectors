'''
    Monitor a directory for new files, convert them to text output format, split them to
small chunks of bytes - according to the maximum size of the request - serialize and
publish to Kafka cluster.
'''

import logging
import os
import shutil
import signal
import time

from file_watcher    import FileWatcher
from multiprocessing import Pool
from publish         import publish
from tempfile        import mkdtemp
from utils           import init_child


class DistributedCollector:
    '''
        Distributed Collector manages the process to collect and publish all the files to
    the Kafka cluster.

    :param datatype       : Type of data to be collected.
    :param topic          : Name of topic where the messages will be published.
    :param partition      : Optionally specify a partition.
    :param skip_conversion: If ``True``, then no transformation will be applied to the data.
    '''

    def __init__(self, datatype, topic, partition, skip_conversion, **conf):
        self._logger          = logging.getLogger('SHIELD.DC.COLLECTOR')
        self._logger.info('Initializing Distributed Collector process...')

        self._datatype        = datatype
        self._interval        = conf['interval']
        self._isalive         = True
        self._partition       = partition
        self._process_opts    = conf['process_opts']
        self._processes       = conf['processes']
        self._producer_kwargs = conf['producer']
        self._skip_conversion = skip_conversion
        self._topic           = topic

        # .............................init FileObserver
        self.FileWatcher      = FileWatcher(**conf['file_watcher'])

        # .............................set up local staging area
        self._tmpdir          = mkdtemp(prefix='_DC.', dir=conf['local_staging'])
        self._logger.info('Use directory "{0}" as local staging area.'.format(self._tmpdir))

        # .............................define a process pool object
        self._pool            = Pool(self._processes, init_child, [self._tmpdir])
        self._logger.info('Master Collector will use {0} parallel processes.'
            .format(self._processes))

        signal.signal(signal.SIGUSR1, self.kill)
        self._logger.info('Initialization completed successfully!')

    def __del__(self):
        '''
            Called when the instance is about to be destroyed.
        '''
        if hasattr(self, '_tmpdir'):
            self._logger.info('Clean up temporary directory "{0}".'.format(self._tmpdir))
            shutil.rmtree(self._tmpdir)

    @property
    def isalive(self):
        '''
            Wait and return True if instance is still alive.
        '''
        time.sleep(self._interval)
        return self._isalive

    def kill(self):
        '''
            Receive signal for termination from an external process.
        '''
        self._logger.info('Receiving a kill signal from an external process...')
        self._isalive = False

    def start(self):
        '''
            Start Master Collector process.
        '''
        self._logger.info('Start "{0}" Collector!'.format(self._datatype.capitalize()))

        self.FileWatcher.start()
        self._logger.info('Signal the {0} thread to start.'.format(str(self.FileWatcher)))

        try:
            while self.isalive:
                files = [self.FileWatcher.dequeue for _ in range(self._processes)]
                for _file in [x for x in files if x]:
                    self._pool.apply_async(publish, args=(
                        _file,
                        self._tmpdir,
                        self._process_opts,
                        self._datatype,
                        self._topic,
                        self._partition,
                        self._skip_conversion), kwds=self._producer_kwargs)

        except KeyboardInterrupt: pass
        finally:
            self.FileWatcher.stop()
            self._pool.close()
            self._pool.join()
            self._logger.info('Stop "{0}" Collector!'.format(self._datatype.capitalize()))
