import importlib.resources
import pathlib
import tomllib

import pygit2
from viat import ViatVault
from viat.vault import locate_existing_vault_root

from alrin.exceptions import AlrinConfigurationError
from alrin.metadata import AlrinVaultMetadata
from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState, get_vault_path
from alrin.workflow.gnupg import initialize_keyring


def copy_resource_traversible(res: importlib.resources.abc.Traversable, target_path: pathlib.Path) -> None:
    if res.is_dir():
        target_path.mkdir(exist_ok=True, parents=True)

        for sub in res.iterdir():
            copy_resource_traversible(sub, target_path / sub.name)

    if res.is_file():
        target_path.write_bytes(res.read_bytes())


def initialize_alrin_vault(repo_path: pathlib.Path) -> None:
    vault = ViatVault.initialize(repo_path)

    copy_resource_traversible(
        importlib.resources.files('alrin.vault_template'),
        vault.resolver.get_root(),
    )

    pygit2.init_repository(repo_path)


def initialize_shared_state(*, vault_path: pathlib.Path | None = None, verbose: bool = False) -> AlrinSharedState:
    vault = ViatVault(
        locate_existing_vault_root(vault_path or get_vault_path()),
    )

    resolver = AlrinPathResolver(vault)
    initialize_keyring(resolver)

    try:
        with open(resolver.get_config(), 'rb') as file:
            json = tomllib.load(file)
    except OSError as err:
        raise AlrinConfigurationError('Could not read config file') from err
    except tomllib.TOMLDecodeError as err:
        raise AlrinConfigurationError('Invalid TOML config file') from err

    meta = AlrinVaultMetadata.from_json(json)
    return AlrinSharedState(vault, resolver, meta, verbose_logging=verbose)
