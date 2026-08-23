import contextlib
import hashlib
import logging
from collections.abc import MutableSequence, MutableSet, Sequence

import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject
from alrin.metadata import AlrinPackageVersion, AlrinPkgbuildMetadata
from alrin.pkginfo import AlrinBuiltPackage, PackageArchPair, PackageNameArchPair, get_existing_built, get_newly_built
from alrin.source import AlrinPackageSource
from alrin.workflow import alpmdb_add_package_files, alpmdb_bulk_remove_packages

from .gnupg import create_signature_file


logger = logging.getLogger(__name__)


def remove_built_file(built: AlrinBuiltPackage) -> None:
    built.path.unlink()

    with contextlib.suppress(FileNotFoundError):
        built.get_signature_path().unlink()


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgname)
def update_version_from_build_files(pkg: AlrinPackageSource) -> None:
    versions = {built.info.pkgver for built in get_newly_built(pkg)}

    if len(versions) == 0:
        raise AlrinPackageMetadataError('No files build to extract the version from')

    if len(versions) > 1:
        raise AlrinPackageMetadataError(f'Multiple versions of the same package {pkg}')

    raw_version = next(iter(versions))
    pkg.version = AlrinPackageVersion.from_string(raw_version)


class BuiltFileProcessor:
    pkg: AlrinPackageSource
    newly_built: Sequence[AlrinBuiltPackage]
    existing_built: Sequence[PackageArchPair]

    ignored_new_files: MutableSet[AlrinBuiltPackage]
    obsolete_architectures: MutableSet[PackageNameArchPair]
    built_files_in_dest: MutableSequence[AlrinBuiltPackage]

    def __init__(self, pkg: AlrinPackageSource) -> None:
        self.pkg = pkg
        self.newly_built = get_newly_built(pkg)
        self.existing_built = get_existing_built(pkg.shared.resolver)
        self.ignored_new_files = set()
        self.obsolete_architectures = set()
        self.built_files_in_dest = []

    def disseminate_file(self, built: AlrinBuiltPackage) -> None:
        for arch in built.iter_arch():
            logger.info(f'Copying {built.path.name} for architecture {arch}.')

            arch_path = self.pkg.shared.resolver.get_dest() / arch
            arch_path.mkdir(parents=True, exist_ok=True)
            dest_file_path = arch_path / built.path.name

            # If we disseminate an existing built file for other architectures, we must ignore copying a file to itself
            if dest_file_path == built.path:
                continue

            self.obsolete_architectures.discard(PackageNameArchPair(built.info.pkgname, arch))
            built.path.copy(arch_path / built.path.name)

            with contextlib.suppress(FileNotFoundError):
                built.get_signature_path().copy(arch_path / (built.path.name + '.sig'))

            self.built_files_in_dest.append(
                AlrinBuiltPackage(arch_path / built.path.name),
            )

    def process_existing_built(self) -> None:
        for existing, dest_arch in self.existing_built:
            if existing.info.pkgbase != self.pkg.pkgname:
                continue
            elif existing.info.pkgarch != dest_arch:
                logger.debug(f'Removing existing copy {existing.path.name} for {dest_arch}. We will create a copy of the newly built file.')
                remove_built_file(existing)
                self.obsolete_architectures.add(PackageNameArchPair(existing.info.pkgname, dest_arch))
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
                    self.disseminate_file(existing)
                    self.ignored_new_files.add(new)
            else:
                logger.info(f'Removing old {existing.path.name}.')
                remove_built_file(existing)

    def process_newly_built(self) -> None:
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
            self.disseminate_file(built)

        # Nothing has been done
        if builddate is None:
            return

        with self.pkg.shared.vault.storage as conn, conn.get_mutator(self.pkg.get_rel_path()) as mut:
            mut['pkgver'] = self.pkg.version.pkgver
            mut['pkgrel'] = self.pkg.version.pkgrel

            if self.pkg.version.epoch is not None:
                mut['epoch'] = self.pkg.version.epoch

            mut['builddate'] = builddate
            self.pkg.viat_meta = AlrinPkgbuildMetadata.from_json(mut)

    def process_all(self) -> None:
        self.process_existing_built()
        self.process_newly_built()


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgname)
def process_built_files(pkg: AlrinPackageSource) -> BuiltFileProcessor:
    processor = BuiltFileProcessor(pkg)
    processor.process_all()
    return processor


def process_built_files_and_update_db(pkg: AlrinPackageSource) -> None:
    processor = process_built_files(pkg)
    alpmdb_add_package_files(pkg.shared, processor.built_files_in_dest)
    alpmdb_bulk_remove_packages(pkg.shared, list(processor.obsolete_architectures))
