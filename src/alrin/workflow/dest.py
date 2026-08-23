import contextlib
import hashlib
import logging
from collections.abc import MutableSequence, MutableSet

import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject, inject_subject
from alrin.metadata import AlrinPackageVersion, AlrinPkgbuildMetadata
from alrin.pkginfo import AlrinBuiltPackage, PackageArchPair, get_existing_built, get_newly_built
from alrin.resolver import AlrinPathResolver
from alrin.source import AlrinPackageSource
from alrin.workflow import alpmdb_add_package_files, alpmdb_bulk_remove_packages

from .gnupg import create_signature_file


logger = logging.getLogger(__name__)


def remove_built_file(built: AlrinBuiltPackage) -> None:
    built.path.unlink()

    with contextlib.suppress(FileNotFoundError):
        built.get_signature_path().unlink()


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgbase)
def update_version_from_build_files(pkg: AlrinPackageSource) -> None:
    versions = {built.info.pkgver for built in get_newly_built(pkg)}

    if len(versions) == 0:
        raise AlrinPackageMetadataError('No files build to extract the version from')

    if len(versions) > 1:
        raise AlrinPackageMetadataError(f'Multiple versions of the same package {pkg}')

    raw_version = next(iter(versions))
    pkg.version = AlrinPackageVersion.from_string(raw_version)


class BuiltFileProcessor:
    newly_built: MutableSequence[AlrinBuiltPackage]
    existing_built: MutableSequence[PackageArchPair]
    obsolete_architectures: MutableSequence[PackageArchPair]
    built_files_in_dest: MutableSequence[AlrinBuiltPackage]
    ignored_new_files: MutableSet[AlrinBuiltPackage]

    def __init__(self) -> None:
        self.newly_built = []
        self.existing_built = []
        self.ignored_new_files = set()
        self.obsolete_architectures = []
        self.built_files_in_dest = []

    def disseminate_file(self, resolver: AlrinPathResolver, built: AlrinBuiltPackage) -> None:
        for arch in built.iter_arch():
            logger.info(f'Copying {built.path.name} for architecture {arch}.')

            arch_path = resolver.get_dest() / arch
            arch_path.mkdir(parents=True, exist_ok=True)
            dest_file_path = arch_path / built.path.name
            built.path.copy(dest_file_path)

            with contextlib.suppress(FileNotFoundError):
                built.get_signature_path().copy(arch_path / (built.path.name + '.sig'))

            self.built_files_in_dest.append(
                AlrinBuiltPackage(arch_path / built.path.name),
            )

    def remove_from_obsolete(self, pkgname: str, arch: str) -> None:
        try:
            obs_index = next(
                i for i, o in enumerate(self.obsolete_architectures)
                if o.built.info.pkgname == pkgname and o.arch == arch
            )
        except StopIteration:
            pass
        else:
            del self.obsolete_architectures[obs_index]

    def _process_existing_built(self, pkg: AlrinPackageSource) -> None:
        for existing_pair in self.existing_built:
            existing, dest_arch = existing_pair

            if existing.info.pkgbase != pkg.pkgbase:
                continue
            elif existing.info.arch != dest_arch:
                self.obsolete_architectures.append(existing_pair)
                continue

            try:
                new = next(built for built in self.newly_built if built.info.pkgname == existing.info.pkgname)
            except StopIteration:
                logger.warning(f'Package file {existing.path.name} exists in the destination, but not among the newly built files.')

                if click.confirm(f'Remove {existing.path.name}?', True):
                    remove_built_file(existing)

                continue

            if existing.info.pkgver == new.info.pkgver:
                old_hash = hashlib.md5(existing.path.read_bytes()).hexdigest()
                new_hash = hashlib.md5(new.path.read_bytes()).hexdigest()

                if old_hash == new_hash:
                    logger.info(f'Package file {existing.path.name} has not changed.')
                else:
                    logger.warning(f'Package file {existing.path.name} has been rebuilt with the same version, but is different from the old one.')

                if click.confirm(f'Replace the existing {existing.path.name}?', False):
                    remove_built_file(existing)
                else:
                    for arch in existing.iter_arch():
                        self.remove_from_obsolete(existing.info.pkgname, arch)

                    self.ignored_new_files.add(new)
            else:
                logger.info(f'Removing old {existing.path.name}.')
                remove_built_file(existing)

    def _process_newly_built(self, pkg: AlrinPackageSource) -> None:
        builddate: int | None = None
        builddate_file_name: str | None = None

        for built in self.newly_built:
            if built in self.ignored_new_files:
                continue

            if builddate is None:
                builddate = built.info.builddate
                builddate_file_name = built.path.name
            elif built.info.builddate != builddate:
                logger.warning(
                    f'{builddate_file_name} and {built.path.name} have different build dates: {built.info.builddate} and {builddate}.',
                )

            logger.info(f'Signing {built.path.name}.')
            create_signature_file(built.path)
            self.disseminate_file(pkg.shared.resolver, built)

        # Nothing has been done
        if builddate is None:
            return

        with pkg.shared.vault.storage as conn, conn.get_mutator(pkg.get_rel_path()) as mut:
            mut['pkgver'] = pkg.version.pkgver
            mut['pkgrel'] = pkg.version.pkgrel

            if pkg.version.epoch is not None:
                mut['epoch'] = pkg.version.epoch

            mut['builddate'] = builddate
            pkg.viat_meta = AlrinPkgbuildMetadata.from_json(mut)

    def clean_obsolete_files(self) -> None:
        for existing, arch in self.obsolete_architectures:
            logger.debug(f'Removing obsolete copy {existing.path.name} for {arch}.')
            remove_built_file(existing)

    def process_pkg(self, pkg: AlrinPackageSource) -> None:
        self.newly_built.extend(get_newly_built(pkg))
        self.existing_built.extend(get_existing_built(pkg.shared.resolver))
        self._process_existing_built(pkg)
        self._process_newly_built(pkg)


def process_built_files(*pkgs: AlrinPackageSource) -> None:
    processor = BuiltFileProcessor()

    for pkg in pkgs:
        with inject_subject(logger, pkg.pkgbase):
            processor.process_pkg(pkg)

    processor.clean_obsolete_files()
    alpmdb_add_package_files(pkg.shared, processor.built_files_in_dest)
    alpmdb_bulk_remove_packages(pkg.shared, processor.obsolete_architectures)
