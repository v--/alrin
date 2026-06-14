import contextlib
import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

import pygit2

from alrin.exceptions import AlrinPackageMetadataError


if TYPE_CHECKING:

    from alrin.source import AlrinPackageSource
    from alrin.state import AlrinSharedState


logger = logging.getLogger(__name__)


def clean_worktree(pkg: AlrinPackageSource) -> None:
    if pkg.repo is None:
        raise AlrinPackageMetadataError('No git repository specified')

    pkg.bound_logger.info('Clearing working tree.')
    pkg.repo.checkout_head(
        strategy=pygit2.GIT_CHECKOUT_FORCE | pygit2.GIT_CHECKOUT_REMOVE_UNTRACKED | pygit2.GIT_CHECKOUT_REMOVE_UNTRACKED,
    )


def update_repo(pkg: AlrinPackageSource) -> None:
    if pkg.repo is None:
        raise AlrinPackageMetadataError('No git repository specified')

    try:
        remote = next(remote for remote in pkg.repo.remotes if remote.name == 'origin')
    except StopIteration:
        raise AlrinPackageMetadataError("No remote named 'origin' set") from None

    pkg.bound_logger.info('Updating repository.')
    remote.fetch()

    try:
        remote_head = next(iter(remote.list_heads()))
    except StopIteration:
        raise AlrinPackageMetadataError(f"No heads for remote 'origin' in {pkg.get_rel_path()}") from None

    if pkg.repo.head.peel().id != remote_head.oid:
        pkg.repo.head.set_target(remote_head.oid)

    clean_worktree(pkg)


def unregister_submodule(shared: AlrinSharedState, pkgname: str) -> None:
    # Removing a git module is tricky. We remove the directory itself only after unregistering it.
    # See https://stackoverflow.com/a/35743109/2756776
    root_path = shared.resolver.get_root()
    rel_path = shared.resolver.get_pkg(pkgname).relative_to(root_path)
    bound_logger = logging.LoggerAdapter(logger, extra=dict(subject=pkgname))
    raw_path = rel_path.as_posix()

    # libgit2 cannot handle submodule deletion
    bound_logger.info('Unstaging git submodule.')
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                'git', 'rm', '--cached', '--force', raw_path,
            ],
            check=True,
            cwd=root_path,
        )

    bound_logger.info('Unregistering git submodule.')
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                'git', 'submodule', 'deinit', '--force', raw_path,
            ],
            check=True,
            cwd=root_path,
        )

    bound_logger.info('Removing git submodule config.')
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                'git', 'config', '--file', '.gitmodules', '--remove-section', f'submodule.{raw_path}',
            ],
            check=True,
            cwd=root_path,
        )

    internal_module_path = shared.resolver.get_root() / '.git' / 'modules' / raw_path

    if internal_module_path.exists():
        bound_logger.info('Removing internal git submodule clone.')
        shutil.rmtree(internal_module_path)
