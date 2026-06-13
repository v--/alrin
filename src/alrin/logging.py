import logging
import sys

import colorlog


class AlrinLogger(logging.Logger):
    handler: logging.StreamHandler

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.handler = logging.StreamHandler(sys.stderr)
        self.handler.setFormatter(
            colorlog.ColoredFormatter(
                '%(bold)s%(asctime)s%(reset)s %(bold)s%(log_color)s%(levelname)s%(bold)s%(reset)s %(message)s',
                datefmt='%H:%M:%S',
            ),
        )

        self.addHandler(self.handler)
