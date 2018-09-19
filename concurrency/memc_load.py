import collections
import glob
import gzip
import logging
import multiprocessing
import os
import sys
import threading
import time
from functools import partial
from optparse import OptionParser

import Queue
import memcache

import appsinstalled_pb2

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple('AppsInstalled', ['dev_type', 'dev_id', 'lat', 'lon', 'apps'])
config = {
    'MEMC_MAX_RETRIES': 1,
    'MEMC_TIMEOUT': 3,
    'MAX_JOB_QUEUE_SIZE': 0,
    'MAX_RESULT_QUEUE_SIZE': 0,
    'THREADS_PER_WORKER': 4,
    'MEMC_BACKOFF_FACTOR': 0.3
}


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, '.' + fn))


def insert_appsinstalled(memc_pool, memc_addr, appsinstalled, dry_run=False):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = f'{appsinstalled.dev_type}:{appsinstalled.dev_id}'
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    try:
        if dry_run:
            logging.debug('{} - {} -> {}'.format(memc_addr, key, str(ua).replace('\n', ' ')))
        else:
            try:
                memc = memc_pool.get(timeout=0.1)
            except Queue.Empty:
                memc = memcache.Client([memc_addr], socket_timeout=config['MEMC_TIMEOUT'])
            ok = False
            for n in range(config['MEMC_MAX_RETRIES']):
                ok = memc.set(key, packed)
                if ok:
                    break
                backoff_value = config['MEMC_BACKOFF_FACTOR'] * (2 ** n)
                time.sleep(backoff_value)
            memc_pool.put(memc)
            return ok
    except Exception as e:
        logging.exception(f'Cannot write to memc {memc_addr}: {e}')
        return False
    return True


def parse_appsinstalled(line):
    line_parts = line.strip().split('\t')
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(',')]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(',') if a.isidigit()]
        logging.info(f'Not all user apps are digits: {line}')
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info(f'Invalid geo coords: {line}')
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def handle_task(job_queue, result_queue):
    processed = errors = 0
    while True:
        try:
            task = job_queue.get(timeout=0.1)
        except Queue.Empty:
            result_queue.put((processed, errors))
            return

        memc_pool, memc_addr, appsinstalled, dry_run = task
        ok = insert_appsinstalled(memc_pool, memc_addr, appsinstalled, dry_run)
        if ok:
            processed += 1
        else:
            errors += 1


def handle_logfile(fn, options):
    device_memc = {
        'idfa': options.idfa,
        'gaid': options.gaid,
        'adid': options.adid,
        'dvid': options.dvid,
    }

    pools = collections.defaultdict(Queue.Queue)
    job_queue = Queue.Queue(maxsize=config['MAX_JOB_QUEUE_SIZE'])
    result_queue = Queue.Queue(maxsize=config['MAX_RESULT_QUEUE_SIZE'])

    workers = []
    for i in range(config['THREADS_PER_WORKER']):
        thread = threading.Thread(target=handle_task, args=(job_queue, result_queue))
        thread.daemon = True
        workers.append(thread)

    for thread in workers:
        thread.start()

    processed = errors = 0
    logging.info(f'Processing {fn}')

    with gzip.open(fn) as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue

            appsinstalled = parse_appsinstalled(line)
            if not appsinstalled:
                errors += 1
                continue

            memc_addr = device_memc.get(appsinstalled.dev_type)
            if not memc_addr:
                errors += 1
                logging.error(f'Unknow device type: {appsinstalled.dev_type}')
                continue

            job_queue.put((pools[memc_addr], memc_addr, appsinstalled, options.dry))

            if not all(thread.is_alive() for thread in workers):
                break

    for thread in workers:
        if thread.is_alive():
            thread.join()

    while not result_queue.empty():
        processed_per_worker, errors_per_worker = result_queue.get()
        processed += processed_per_worker
        errors += errors_per_worker

    if processed:
        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info(f'Acceptable error rate ({err_rate}). Successfull load')
        else:
            logging.error(f'High error rate ({err_rate} > {NORMAL_ERR_RATE}). Failed load')

    return fn


def main(options):
    num_processes = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=num_processes)
    fnames = sorted(fn for fn in glob.iglob(options.pattern))
    handler = partial(handle_logfile, options=options)
    for fn in pool.imap(handler, fnames):
        dot_rename(fn)


def prototest():
    sample = 'idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424'
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split('\t')
        apps = [int(a) for a in raw_apps.split(',') if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option('-t', '--test', action='store_true', default=False)
    op.add_option('-l', '--log', action='store', default=None)
    op.add_option('--dry', action='store_true', default=False)
    op.add_option('--pattern', action='store', default='/data/appsinstalled/*.tsv.gz')
    op.add_option('--idfa', action='store', default='127.0.0.1:33013')
    op.add_option('--gaid', action='store', default='127.0.0.1:33014')
    op.add_option('--adid', action='store', default='127.0.0.1:33015')
    op.add_option('--dvid', action='store', default='127.0.0.1:33016')
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info(f'Memc loader started with options: {opts}')
    try:
        main(opts)
    except Exception as e:
        logging.exception(f'Unexpected error: {e}')
        sys.exit(1)
