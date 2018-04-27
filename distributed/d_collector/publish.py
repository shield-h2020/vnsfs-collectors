'''
    Publish human-readable formatted data to the Kafka cluster.
'''

import logging
import os
import pipelines
import shutil

from multiprocessing import current_process
from producer        import Producer

def publish(rawfile, tmpdir, opts, datatype, topic, partition, skip_conv, **kwargs):
    '''
        Publish human-readable formatted data to the Kafka cluster.

    :param rawfile  : Path of original raw file.
    :param tmpdir   : Path of local staging area.
    :param opts     : A set of options for the conversion.
    :param datatype : Type of data that will be ingested.
    :param topic    : Topic where the messages will be published.
    :param partition: The partition number where the messages will be delivered.
    :param skip_conv: Skip `convert` function.
    :param kwargs   : Configuration parameters to initialize the
                      :class:`collector.Producer` object.
    '''
    def send_async(segid, timestamp_ms, items):
        try:
            metadata = producer.send_async(topic, items, None, partition, timestamp_ms)
            logger.info('Published segment-{0} to Kafka cluster. [Topic: {1}, '
                'Partition: {2}]'.format(segid, metadata.topic, metadata.partition))

            return True
        except RuntimeError:
            logger.error('Failed to publish segment-{0} to Kafka cluster.'.format(segid))
            logger.info('Store segment-{0} to local staging area as "{1}".'
                .format(segid, store_segment(segid, items, filename, tmpdir)))

    filename  = os.path.basename(rawfile)
    proc_name = current_process().name
    logger    = logging.getLogger('SHIELD.DC.PUBLISH.{0}'.format(proc_name))
    logger.info('Processing raw file "{0}"...'.format(filename))

    proc_dir  = os.path.join(tmpdir, proc_name)
    allpassed = True

    try:
        module      = getattr(pipelines, datatype)
        producer    = Producer(**kwargs)

        if skip_conv:
            shutil.copy2(rawfile, tmpdir)
            staging = os.path.join(tmpdir, os.path.basename(rawfile))
        else:
            staging = module.convert(rawfile, proc_dir, opts, datatype + '_')

        logger.info('Load converted file to local staging area as "{0}".'
            .format(os.path.basename(staging)))

        partitioner = module.prepare(staging, producer.max_request)
        logger.info('Group lines of text-converted file and prepare to publish them.')

        for segmentid, datatuple in enumerate(partitioner):
            try:
                allpassed &= send_async(segmentid, *datatuple)
            except RuntimeError: allpassed = False

        os.remove(staging)
        logger.info('Remove CSV-converted file "{0}" from local staging area.'
            .format(staging))

        if allpassed:
            logger.info('All segments of "{0}" published successfully to Kafka cluster.'
                .format(filename))
            return

        logger.warning('One or more segment(s) of "{0}" were not published to Kafka cluster.'
            .format(filename))

    except IOError as ioe:
        logger.warning(ioe.message)

    except Exception as exc:
        logger.error('[{0}] {1}'.format(exc.__class__.__name__, exc.message))

    finally:
        if producer:
            producer.close()

def store_segment(id, items, filename, path):
    '''
        Store segment to the local staging area to try to send to Kafka cluster later.

    :param id      : The id of the current segment.
    :param items   : List of lines from the text-converted file.
    :param filename: The name of the original raw file.
    :param path    : Path of local staging area.
    :returns       : The name of the segment file in the local staging area.
    :rtype         : ``str``
    '''
    name = '{0}_segment-{1}.csv'.format(filename.replace('.', '_'), id)

    with open(os.path.join(path, name), 'w') as fp:
        [fp.write(x + '\n') for x in items]

    return name
