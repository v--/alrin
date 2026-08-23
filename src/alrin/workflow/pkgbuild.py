import logging
import re
import sys

from alrin.logging import inject_subject
from alrin.metadata import AlrinPackageVersion
from alrin.source import AlrinPackageSource


PYTHON_VERSION_SUFFIX = f'.{sys.version_info.major}{sys.version_info.minor}'
logger = logging.getLogger(__name__)


def preprocess_pkgbuild(pkg: AlrinPackageSource) -> None:
    pkgbuild_path = pkg.get_abs_path().joinpath('PKGBUILD')
    pkgrel = pkg.version.pkgrel

    if pkg.viat_meta.add_pkgrel_suffix and not pkgrel.endswith(PYTHON_VERSION_SUFFIX):
        with inject_subject(logger, pkg.pkgbase):
            logger.info(f'Adding a pkgrel suffix {PYTHON_VERSION_SUFFIX}.')

        pkgbuild_path.write_text(
            re.sub(r'pkgrel=.+', 'pkgrel=' + pkgrel + PYTHON_VERSION_SUFFIX, pkgbuild_path.read_text('utf-8')),
        )

        pkgrel += PYTHON_VERSION_SUFFIX

    pkg.version = AlrinPackageVersion(
        pkgver=pkg.version.pkgver,
        pkgrel=pkgrel,
        epoch=pkg.version.epoch,
    )
