import contextlib
import functools
import logging
import sys
lazy from collections.abc import Callable, Generator

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



class SubjectFilter(logging.Filter):
    subject: str

    def __init__(self, subject: str) -> None:
        super().__init__()
        self.subject = subject

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'subject'):
            record.subject = self.subject

        return True


@contextlib.contextmanager
def inject_subject(logger: logging.Logger, subject: str) -> Generator[None]:
    filter_ = SubjectFilter(subject)
    logger.addFilter(filter_)

    try:
        yield
    finally:
        logger.removeFilter(filter_)


def bind_logger_to_subject[**P, R](logger: logging.Logger, get_subject: Callable[..., str]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fun: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fun)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with inject_subject(logger, get_subject(*args, **kwargs)):
                return fun(*args, **kwargs)

        return wrapper

    return decorator
