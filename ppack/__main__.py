import argparse
import sys
from pathlib import Path
from traceback import print_tb
from typing import List

from ppack.process import perform


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog='ppack')

    parser.add_argument(
        '-r',
        dest='resources',
        metavar='resources',
        action='store_true',
        help='create a resources folder with all non-python files (it will be named <target>_resources)',
    )

    parser.add_argument(
        '-f',
        dest='filter',
        metavar='filter',
        action='append',
        default=[],
        help='defines files and folders to be filtered out (glob pattern)',
    )

    parser.add_argument(
        '-z',
        dest='zip',
        metavar='zip',
        action='store_true',
        help='provide target as zip file',
    )

    parser.add_argument(
        'source',
        help='source package path',
    )

    parser.add_argument(
        'target',
        help='target python or zip file (will be cleared)',
    )

    args = parser.parse_args(argv)

    try:
        perform(
            Path(args.source),
            Path(args.target),
            [Path(filter_item).resolve() for filter_item in args.filter],
            args.resources,
            args.do_zip,
        )
    except Exception as ex:
        print(f'ERROR: {ex}')
        print_tb(ex)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])