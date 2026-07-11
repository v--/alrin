from dataclasses import dataclass
lazy import pathlib

lazy from viat import ViatVault


@dataclass(frozen=True)
class AlrinPathResolver:
    vault: ViatVault

    def get_root(self) -> pathlib.Path:
        return self.vault.resolver.get_root()

    def get_pkg(self, name: str) -> pathlib.Path:
        return self.get_root() / 'pkgbuild' / name

    def get_jail(self) -> pathlib.Path:
        return self.get_root() / 'pkgjail'

    def get_dest(self) -> pathlib.Path:
        return self.get_root() / 'pkgdest'

    def get_keyring(self) -> pathlib.Path:
        return self.get_root() / 'keyring'

    def get_keyring_backup(self) -> pathlib.Path:
        return self.get_root() / 'keyring_backup.asc'

    def relativize(self, path: pathlib.Path) -> pathlib.Path:
        return self.vault.resolver.relativize(path)
