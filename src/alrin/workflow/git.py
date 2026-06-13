import contextlib
import shutil
import subprocess
from typing import TYPE_CHECKING

import pygit2

from alrin.exceptions import AlrinPackageMetadataError


if TYPE_CHECKING:
    import pathlib

    from alrin.source import AlrinPackageSource
    from alrin.state import AlrinSharedState


def clean_worktree(pkg: AlrinPackageSource) -> None:
    if pkg.repo is None:
        raise AlrinPackageMetadataError('No git repository specified')

    pkg.shared.logger.info(f'Clearing working tree in {pkg.get_rel_path().as_posix()!r}.')
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

    pkg.shared.logger.info(f'Updating repository {pkg.get_rel_path().as_posix()!r}.')
    remote.fetch()

    try:
        remote_head = next(iter(remote.list_heads()))
    except StopIteration:
        raise AlrinPackageMetadataError(f"No heads for remote 'origin' in {pkg.get_rel_path()}") from None

    if pkg.repo.head.peel().id != remote_head.oid:
        pkg.repo.head.set_target(remote_head.oid)

    clean_worktree(pkg)


def unregister_submodule(shared: AlrinSharedState, rel_path: pathlib.Path) -> None:
    # Removing a git module is tricky. We remove the directory itself only after unregistering it.
    # See https://stackoverflow.com/a/35743109/2756776
    root_path = shared.resolver.get_root()
    raw_path = rel_path.as_posix()

    # libgit2 cannot handle submodule deletion
    shared.logger.info(f'Unstaging git submodule {raw_path!r}.')
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                'git', 'rm', '--cached', '--force', raw_path,
            ],
            check=True,
            cwd=root_path,
        )

    shared.logger.info(f'Removing git config for {raw_path!r}.')
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                'git', 'submodule', 'deinit', '--force', raw_path,
            ],
            check=True,
            cwd=root_path,
        )

    shared.logger.info(f'Removing git submodule config for {raw_path!r}.')
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
        shared.logger.info(f'Removing internal git clone of {raw_path!r}.')
        shutil.rmtree(internal_module_path)
