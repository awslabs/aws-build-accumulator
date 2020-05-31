import logging
import os
import pathlib
import sys


CACHE_FILE = "cache.json"
CACHE_POINTER = ".litani_cache_dir"
CI_STAGES = ["build", "test", "report"]


def get_cache_dir():
    def cache_pointer_dirs():
        current = pathlib.Path(os.getcwd()).resolve(strict=True)
        yield current
        while current.parent != current:
            current = current.parent
            yield current
        current = pathlib.Path(os.getcwd()).resolve(strict=True)
        for root, _, dirs in os.walk(current):
            for dyr in dirs:
                yield pathlib.Path(os.path.join(root, dyr))

    for possible_dir in cache_pointer_dirs():
        logging.debug(
            "Searching for cache pointer in %s", possible_dir)
        possible_pointer = possible_dir / CACHE_POINTER
        try:
            if possible_pointer.exists():
                logging.debug(
                    "Found a cache pointer at %s", possible_pointer)
                with open(possible_pointer) as handle:
                    pointer = handle.read().strip()
                possible_cache = pathlib.Path(pointer)
                if possible_cache.exists():
                    logging.debug("cache is at %s", possible_cache)
                    return possible_cache
                logging.warning(
                    "Found a cache file at %s pointing to %s, but that "
                    "directory does not exist. Continuing search...",
                    possible_pointer, possible_cache)
        except PermissionError:
            pass

    logging.error(
        "Could not find a pointer to a litani cache. Did you forget "
        "to run `litani init`?")
    sys.exit(1)


def get_report_dir():
    return get_cache_dir() / "html"


def get_artifacts_dir():
    return get_cache_dir() / "artifacts"


def get_status_dir():
    return get_cache_dir() / "status"
