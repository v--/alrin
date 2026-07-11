
# ruff: file-ignore[repeated-append]
import logging
import pathlib
import subprocess
lazy from collections.abc import Sequence


logger = logging.getLogger(__name__)


BINARY_DEPENDENCIES = [
    'which',
    'repo-add', 'repo-remove',
    'arch-nspawn', 'mkarchroot', 'makechrootpkg',
]


def check_binary_dependencies() -> None:
    for binary in BINARY_DEPENDENCIES:
        try:
            subprocess.run(['which', binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as err:
            raise SystemExit(f'Could not locate external dependency {binary!r}') from err


def arch_nspawn(
    working_dir: pathlib.Path,
    command: Sequence[str],
    *,
    pacman_config: pathlib.Path | None = None,
    cwd: pathlib.Path | None = None,
) -> None:
    extra_args = list[str]()

    if pacman_config and pacman_config.exists():
        logger.debug('Synchronizing pacman.conf.')
        extra_args = ['-C', pacman_config.as_posix()]

    subprocess.run(
        [
            'arch-nspawn', *extra_args, working_dir.as_posix(),
            *command,
        ],
        check=True,
        cwd=cwd,
    )


def mkarchroot(
    working_dir: pathlib.Path,
    package_list: Sequence[str],
    *,
    cwd: pathlib.Path | None = None,
) -> None:
    subprocess.run(
        [
            'mkarchroot',
            working_dir.as_posix(),
            *package_list,
        ],
        check=True,
        cwd=cwd,
    )


def makechrootpkg(
    chrootdir: pathlib.Path,
    *,
    makepkg_args: Sequence[str] | None = None,
    clean_before_building: bool = False,
    working_dir_name: str | None = None,
    cwd: pathlib.Path | None = None,
    # ruff: ignore[invalid-argument-name]
    SOURCE_DATE_EPOCH: int | None = None,
    # ruff: ignore[invalid-argument-name]
    GNUPGHOME: pathlib.Path | None = None,
) -> None:
    args = ['makechrootpkg', '-r', chrootdir.as_posix()]

    if clean_before_building:
        args.append('-c')

    if working_dir_name:
        args.append('-l')
        args.append(working_dir_name)

    if makepkg_args:
        args.append('--')
        args.extend(makepkg_args)

    env = dict[str, str]()

    if SOURCE_DATE_EPOCH is not None:
        env['SOURCE_DATE_EPOCH'] = str(SOURCE_DATE_EPOCH)

    if GNUPGHOME is not None:
        env['GNUPGHOME'] = GNUPGHOME.as_posix()

    subprocess.run(
        args,
        check=True,
        cwd=cwd,
        env=env,
    )


def repo_add(
    path_to_db: pathlib.Path,
    package_paths: Sequence[pathlib.Path],
    *,
    quiet: bool = False,
    sign: bool = False,
    cwd: pathlib.Path | None = None,
) -> None:
    option_args = list[str]()

    if quiet:
        option_args.append('--quiet')

    if sign:
        option_args.append('--sign')

    subprocess.run(
        [
            'repo-add', *option_args, path_to_db,
            *(path.as_posix() for path in package_paths),
        ],
        check=True,
        cwd=cwd,
    )


def repo_remove(
    path_to_db: pathlib.Path,
    package_names: Sequence[str],
    *,
    quiet: bool = False,
    sign: bool = False,
    cwd: pathlib.Path | None = None,
) -> None:
    option_args = list[str]()

    if quiet:
        option_args.append('--quiet')

    if sign:
        option_args.append('--sign')

    subprocess.run(
        [
            'repo-remove', *option_args, path_to_db,
            *package_names,
        ],
        check=True,
        cwd=cwd,
    )
