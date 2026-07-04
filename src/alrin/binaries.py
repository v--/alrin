import logging
import subprocess


logger = logging.getLogger(__name__)


def check_binary_dependencies(*bin_names: str) -> None:
    for binary in bin_names:
        try:
            subprocess.run(['which', binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as err:
            raise SystemExit(f'Could not locate external dependency {binary!r}') from err
