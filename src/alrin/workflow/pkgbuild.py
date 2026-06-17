import ast
import logging
import re
import sys
from typing import TextIO

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject
from alrin.metadata import AlrinPackageVersion
lazy from alrin.source import AlrinPackageSource


logger = logging.getLogger(__name__)


def geneate_pkgbuild_regex(key: str) -> re.Pattern:
    return re.compile(rf'{key}=(?P<value>.+)')


def find_pkgbuild_value(pkgbuild_text: str, key: str) -> str | None:
    if match := re.search(geneate_pkgbuild_regex(key), pkgbuild_text):
        raw_value = match.group('value')

        try:
            value = ast.literal_eval(raw_value)

            if isinstance(value, str):
                return value
            else:
                return raw_value
        except SyntaxError:
            return raw_value

    return None


def extract_pkgbuild_version(file: TextIO) -> AlrinPackageVersion:
    pkgbuild_text = file.read()
    pkgver = find_pkgbuild_value(pkgbuild_text, 'pkgver')

    if pkgver is None:
        raise AlrinPackageMetadataError('Could not read pkgver from PKGBUILD')

    pkgrel = find_pkgbuild_value(pkgbuild_text, 'pkgrel')

    if pkgrel is None:
        raise AlrinPackageMetadataError('Could not read pkgver from PKGBUILD')

    epoch = find_pkgbuild_value(pkgbuild_text, 'epoch')

    return AlrinPackageVersion(
        pkgver=pkgver,
        pkgrel=pkgrel,
        epoch=int(epoch) if epoch else None,
    )


def preprocess_pkgbuild(pkg: AlrinPackageSource) -> None:
    pkgbuild_path = pkg.get_abs_path().joinpath('PKGBUILD')

    if pkg.viat_meta.extra_makedepends is not None:
        with inject_subject(logger, pkg.pkgname):
            logger.info('Adding custom extra_makedepends list.')

        pkgbuild = pkgbuild_path.read_text('utf-8')
        extra_makedepends = ' '.join(repr(dep) for dep in pkg.viat_meta.extra_makedepends)

        if 'makedepends=' in pkgbuild:
            pkgbuild_path.write_text(
                pkgbuild.replace('makedepends=(', 'makedepends=(' + extra_makedepends + ' '),
            )
        else:
            pkgbuild_path.write_text(
                'makedepends=(' + extra_makedepends + ')\n' + pkgbuild,
            )

    if not pkg.viat_meta.add_python_suffix:
        return

    with pkg.get_abs_path().joinpath('PKGBUILD').open() as file:
        pkgbuild_version = extract_pkgbuild_version(file)

    version_suffix = f'.{sys.version_info.major}{sys.version_info.minor}'
    pkgrel = pkgbuild_version.pkgrel

    if not pkgrel.endswith(version_suffix):
        with inject_subject(logger, pkg.pkgname):
            logger.info(f'Adding a pkgrel suffix {version_suffix}.')

        pkgbuild_path.write_text(
            re.sub(r'(?<=pkgrel=).+', 'pkgrel=' + pkgrel + version_suffix, pkgbuild_path.read_text('utf-8')),
        )

        pkgrel += version_suffix

    pkg.version = AlrinPackageVersion(
        pkgver=pkgbuild_version.pkgver,
        pkgrel=pkgrel,
        epoch=pkgbuild_version.epoch,
    )


def postprocess_pkgbuild(pkg: AlrinPackageSource) -> None:
    with pkg.get_abs_path().joinpath('PKGBUILD').open() as file:
        pkg.version = extract_pkgbuild_version(file)
