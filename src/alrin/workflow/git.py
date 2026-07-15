import pathlib
import contextlib
import logging
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

    main_config = pygit2.Config(root_path.joinpath('.git', 'config').as_posix())

    if f'submodule.{raw_path}.path' in main_config:
        logger.info('Unregistering git submodule.')
        del main_config[f'submodule.{raw_path}.url']
        del main_config[f'submodule.{raw_path}.path']

    submodule_config = pygit2.Config(root_path.joinpath('.gitmodules').as_posix())

    if f'submodule.{raw_path}.path' in submodule_config:
        logger.info('Removing git submodule config.')
        del submodule_config[f'submodule.{raw_path}.url']
        del submodule_config[f'submodule.{raw_path}.path']
        repo.index.add('.gitmodules')
        repo.index.write()

    internal_module_path = shared.resolver.get_root() / '.git' / 'modules' / raw_path

    if internal_module_path.exists():
        logger.info('Removing internal git submodule clone.')
        shutil.rmtree(internal_module_path)
