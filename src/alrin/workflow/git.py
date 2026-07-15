import logging
import pathlib
import shutil

import pygit2

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject
lazy from alrin.source import AlrinPackageSource
lazy from alrin.state import AlrinSharedState


logger = logging.getLogger(__name__)


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgname)
def clean_worktree(pkg: AlrinPackageSource) -> None:
    if pkg.repo is None:
        raise AlrinPackageMetadataError('No git repository specified')

    logger.info('Clearing working tree.')

    pkg.repo.checkout_head(
        strategy=pygit2.GIT_CHECKOUT_FORCE | pygit2.GIT_CHECKOUT_REMOVE_UNTRACKED | pygit2.GIT_CHECKOUT_REMOVE_UNTRACKED,
    )


# libgit2 is bad at removing entire sections, so we recreate the config anew
def remove_config_section(path: pathlib.Path, section_name: str) -> None:
    config = pygit2.Config(path.as_posix())

    if any(section.name.startswith(section_name) for section in config):
        logger.info(f'Removing section {section_name} from {path}.')
        entries = list(config)
        path.unlink()
        new_config = pygit2.Config(path.as_posix())

        for entry in entries:
            if not entry.name.startswith(section_name):
                new_config[entry.name] = entry.value


@bind_logger_to_subject(logger, lambda pkg: pkg.pkgname)
def update_repo(pkg: AlrinPackageSource) -> None:
    if pkg.repo is None:
        raise AlrinPackageMetadataError('No git repository specified')

    try:
        remote = next(remote for remote in pkg.repo.remotes if remote.name == 'origin')
    except StopIteration:
        raise AlrinPackageMetadataError("No remote named 'origin' set") from None

    logger.info('Updating repository.')
    remote.fetch()

    try:
        remote_head = next(iter(remote.list_heads()))
    except StopIteration:
        raise AlrinPackageMetadataError(f"No heads for remote 'origin' in {pkg.get_rel_path()}") from None

    if pkg.repo.head.peel().id != remote_head.oid:
        pkg.repo.head.set_target(remote_head.oid)

    clean_worktree(pkg)


@bind_logger_to_subject(logger, lambda _, pkgname: pkgname)
def unregister_submodule(shared: AlrinSharedState, pkgname: str) -> None:
    # Removing a git module is tricky. We remove the directory itself only after unregistering it.
    # See https://stackoverflow.com/a/35743109/2756776
    root_path = shared.resolver.get_root()
    pkg_path = shared.resolver.get_pkg(pkgname)
    raw_path = pkg_path.relative_to(root_path).as_posix()

    repo = pygit2.Repository(root_path)

    if pkg_path.exists():
        logger.info('Removing the main directory.')
        shutil.rmtree(pkg_path)
        repo.index.add_all([raw_path])
        repo.index.write()

    remove_config_section(
        root_path.joinpath('.git', 'config'),
        f'submodule.{raw_path}',
    )

    remove_config_section(
        root_path.joinpath('.gitmodules'),
        f'submodule.{raw_path}',
    )

    internal_module_path = shared.resolver.get_root() / '.git' / 'modules' / raw_path

    if internal_module_path.exists():
        logger.info('Removing internal git submodule clone.')
        shutil.rmtree(internal_module_path)
