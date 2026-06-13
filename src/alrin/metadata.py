import functools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, cast


if TYPE_CHECKING:
    from collections.abc import Sequence

    from alpm.type_aliases import SourceInfo
    from viat.support.json import JsonObjectT


@dataclass(frozen=True)
@functools.total_ordering
class AlrinPackageVersion:
    @classmethod
    def from_srcinfo(cls, srcinfo: SourceInfo) -> Self:
        return cls(
            pkgver=str(srcinfo.base.version.pkgver),
            pkgrel=str(srcinfo.base.version.pkgrel),
            epoch=srcinfo.base.version.epoch.value if srcinfo.base.version.epoch else None,
        )

    @classmethod
    def from_json(cls, reader: JsonObjectT) -> Self:
        return cls(
            pkgver=cast('str', reader['pkgver']),
            pkgrel=cast('str', reader['pkgrel']),
            epoch=cast('int | None', reader.get('epoch')),
        )

    pkgver: str
    pkgrel: str
    epoch: int | None

    def __lt__(self, other: AlrinPackageVersion) -> bool:
        self_epoch = self.epoch or float('-inf')
        other_epoch = other.epoch or float('-inf')

        return self_epoch < other_epoch or self.pkgver < other.pkgver or self.pkgrel < other.pkgrel


@dataclass(frozen=True)
class AlrinMetadata:
    @classmethod
    def from_json(cls, reader: JsonObjectT) -> Self:
        return cls(
            version=AlrinPackageVersion.from_json(reader),
            builddate=cast('int | None', reader.get('builddate')),
            add_python_suffix=cast('bool', reader.get('add_python_suffix', False)),
            git_root=cast('str | None', reader.get('git_root')),
            extra_makedepends=cast('Sequence[str] | None', reader.get('extra_makedepends')),
        )

    version: AlrinPackageVersion
    builddate: int | None
    git_root: str | None
    add_python_suffix: bool
    extra_makedepends: Sequence[str] | None
