import logging
import sys

import colorlog


class AlrinLoggerHandler(logging.StreamHandler):
    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(
            colorlog.ColoredFormatter(
                stream=sys.stderr,  # Without explicitly setting the stream, TTY detection does not work.
                style='{',
                fmt='{green}{asctime}{reset} {bold}{log_color}{levelname:8}{reset} {cyan}{subject}{reset} {log_color}{message}{reset}',
                datefmt='%X',
                defaults={'subject': '<system>'},
                log_colors={**colorlog.default_log_colors, 'INFO': 'white'},
            ),
        )


def setup_logging(verbose: bool = False) -> None:
    base_logger = logging.getLogger('alrin')
    base_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    base_logger.addHandler(AlrinLoggerHandler())
