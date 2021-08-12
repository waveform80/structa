#!/usr/bin/python3

import sys
import time
import socket
import argparse
import traceback
import subprocess as sp
import multiprocessing as mp
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


__version__ = '0.1'


class DevRequestHandler(SimpleHTTPRequestHandler):
    server_version = 'DocsPreview/' + __version__
    protocol_version = 'HTTP/1.0'


class DevServer(ThreadingHTTPServer):
    allow_reuse_address = True
    base_path = None


def get_best_family(*address):
    infos = socket.getaddrinfo(
        *address,
        type=socket.SOCK_STREAM,
        flags=socket.AI_PASSIVE,
    )
    family, type, proto, canonname, sockaddr = next(iter(infos))
    return family, sockaddr


def server(config, queue=None):
    try:
        DevServer.address_family, addr = get_best_family(config.bind, config.port)
        handler = partial(DevRequestHandler, directory=str(config.html_path))
        with DevServer(addr, handler) as httpd:
            host, port = httpd.socket.getsockname()[:2]
            hostname = socket.gethostname()
            print(f'Serving {config.html_path} HTTP on {host} port {port}')
            print(f'http://{hostname}:{port}/ ...')
            # XXX Wait for queue message to indicate time to start?
            httpd.serve_forever()
    except:
        if queue is not None:
            queue.put(sys.exc_info())
        raise


def _iter_stats(path):
    for p in path.iterdir():
        if p.is_dir():
            yield from _iter_stats(p)
        else:
            yield p, p.stat()


def get_stats(config):
    return {
        filepath: stat
        for path in config.watch_path
        for filepath, stat in _iter_stats(path)
        if not any(filepath.match(pattern) for pattern in config.ignore)
    }


def get_changes(old_stats, new_stats):
    # Yes, this is crude and could be more efficient but it's fast enough on a
    # Pi so it'll be fast enough on anything else
    return (
        new_stats.keys() - old_stats.keys(), # new
        old_stats.keys() - new_stats.keys(), # deleted
        {                                    # modified
            filepath
            for filepath in old_stats.keys() & new_stats.keys()
            if new_stats[filepath].st_mtime > old_stats[filepath].st_mtime
        }
    )


def rebuild(config):
    print(f'Rebuilding...')
    # XXX Make rebuild command configurable?
    sp.run(['make', 'html'], cwd=Path(__file__).parent)
    return get_stats(config)


def builder(config, queue=None):
    try:
        old_stats = rebuild(config)
        # XXX Add some message to the queue to indicate first build done and
        # webserver can start?
        while True:
            new_stats = get_stats(config)
            created, deleted, modified = get_changes(old_stats, new_stats)
            if created or deleted or modified:
                for filepath in created:
                    print(f'New file, {filepath}')
                for filepath in deleted:
                    print(f'Deleted file, {filepath}')
                for filepath in modified:
                    print(f'Changed detected in {filepath}')
                old_stats = rebuild(config)
            else:
                time.sleep(0.5)  # make sure we're not a busy loop
    except:
        if queue is not None:
            queue.put(sys.exc_info())
        raise


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'html_path', default='build/html', type=Path, nargs='?',
        help="The base directory which you wish to server over HTTP. Default: "
        "%(default)s")
    parser.add_argument(
        '-w', '--watch-path', action='append', default=[],
        help="Can be specified multiple times to append to the list of source "
        "directories to watch for changes")
    parser.add_argument(
        '-i', '--ignore', action='append', default=['*.swp', '*.bak', '*~', '.*'],
        help="Can be specified multiple times to append to the list of "
        "patterns to ignore.")
    parser.add_argument(
        '--bind', metavar='ADDR', default='0.0.0.0',
        help="The address to listen on. Default: %(default)s")
    parser.add_argument(
        '--port', metavar='PORT', default='8000',
        help="The port to listen on. Default: %(default)s")
    config = parser.parse_args(args)
    config.watch_path = [Path(p) for p in config.watch_path]
    if not config.watch_path:
        parser.error('You must specify at least one --watch-path')

    queue = mp.Queue()
    builder_proc = mp.Process(target=builder, args=(config, queue), daemon=True)
    server_proc = mp.Process(target=server, args=(config, queue), daemon=True)
    builder_proc.start()
    server_proc.start()
    exc, value, tb = queue.get()
    server_proc.terminate()
    builder_proc.terminate()
    traceback.print_exception(exc, value, tb)


if __name__ == '__main__':
    sys.exit(main())
