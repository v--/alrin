from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import pathlib

    from viat import ViatVault


@dataclass(frozen=True)
class AlrinPathResolver:
    vault: ViatVault

    def get_root(self) -> pathlib.Path:
        return self.vault.resolver.get_root()

    def pkg_get(self, name: str) -> pathlib.Path:
        return self.get_root() / 'pkgbuild' / name

    def get_jail(self) -> pathlib.Path:
        return self.get_root() / 'pkgjail'

    def get_dest(self) -> pathlib.Path:
        return self.get_root() / 'pkgdest'

    def relativize(self, path: pathlib.Path) -> pathlib.Path:
        return self.vault.resolver.relativize(path)
