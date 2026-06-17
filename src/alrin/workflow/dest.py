import contextlib
import hashlib
import logging
lazy from collections.abc import Sequence

import click

from alrin.buildinfo import AlrinBuiltPackage, get_existing_built, get_newly_built
from alrin.logging import bind_logger_to_subject
from alrin.metadata import AlrinMetadata
lazy from alrin.source import AlrinPackageSource

from .signing import create_signature_file


logger = logging.getLogger(__name__)


def remove_built_file(built: AlrinBuiltPackage) -> None:
    built.path.unlink()

    with contextlib.suppress(FileNotFoundError):
        built.get_signature_path().unlink()


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgname)
def process_built_files(pkg: AlrinPackageSource) -> Sequence[AlrinBuiltPackage]:  # noqa: C901
    built_files = get_newly_built(pkg)
    ignored_files = set[AlrinBuiltPackage]()

    for existing in get_existing_built(pkg.shared):
        if existing.info.pkgbase != pkg.pkgname:
            continue

        existing_rel = existing.path.relative_to(pkg.shared.resolver.get_dest())

        try:
            new = next(built for built in built_files if built.info.pkgname == existing.info.pkgname and built.info.pkgarch == existing.info.pkgarch)
        except StopIteration:
            logger.warn(f'Package file {existing.path.name} exists in the destination, but not in the newly built files.')

            if click.confirm(f'Remove {existing_rel}?', True):
                remove_built_file(existing)
            else:
                ignored_files.add(new)

            continue

        if existing.info.pkgver == new.info.pkgver:
            old_hash = hashlib.md5(existing.path.read_bytes()).hexdigest()
            new_hash = hashlib.md5(new.path.read_bytes()).hexdigest()

            if old_hash == new_hash:
                logger.info(f'Package file {existing.path.name} has not changed.')
            else:
                logger.warn(f'Package file {existing.path.name} rebuilt with the same version, but is different from the old one.')

            if click.confirm(f'Replace the existing {existing_rel.as_posix()!s}?', False):
                remove_built_file(existing)
            else:
                ignored_files.add(new)
        else:
            logger.info(f'Removing old {existing_rel.as_posix()!s}.')
            remove_built_file(existing)

    builddate: int | None = None
    builddate_pkg_name: str | None = None

    result = list[AlrinBuiltPackage]()

    for built in built_files:
        if built in ignored_files:
            continue

        if builddate is None:
            builddate = built.info.builddate
            builddate_pkg_name = built.path.name
        elif built.info.builddate != builddate:
            logger.warn(
                f'{builddate_pkg_name} and {built.path.name} have different build dates: {built.info.builddate} and {builddate}.',
            )

        logger.info(f'Signing {built.path.name}.')
        create_signature_file(built.path)

        for arch in built.iter_arch():
            logger.info(f'Copying {built.path.name} for architecture {arch}.')

            dest_path = pkg.shared.resolver.get_dest()
            arch_path = dest_path / arch
            arch_path.mkdir(parents=True, exist_ok=True)

            built.path.copy(arch_path / built.path.name)
            built.get_signature_path().copy(arch_path / (built.path.name + '.sig'))
            result.append(
                AlrinBuiltPackage(arch_path / built.path.name),
            )

    # Nothing has been done
    if builddate is None:
        return result

    with pkg.shared.vault.storage as conn, conn.get_mutator(pkg.get_rel_path()) as mut:
        mut['pkgver'] = pkg.version.pkgver
        mut['pkgrel'] = pkg.version.pkgrel

        if pkg.version.epoch is not None:
            mut['epoch'] = pkg.version.epoch

        mut['builddate'] = builddate
        pkg.viat_meta = AlrinMetadata.from_json(mut)

    return result
