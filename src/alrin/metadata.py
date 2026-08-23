import functools
import re
from dataclasses import dataclass
from typing import Self, cast

from alpm.type_aliases import SourceInfo
from viat.support.json import JsonObject, JsonObjectT

from alrin.exceptions import AlrinConfigurationError, AlrinPackageMetadataError


# From the repo-add man page
COMPRESSION_VALUES = ['bz2', 'gz', 'lrz', 'lz', 'lz4', 'lzo', 'xz', 'zst', 'Z']


@dataclass(frozen=True)
class AlrinDatabaseMetadata:
    name: str
    compression: str | None

    @classmethod
    def from_json(cls, json: JsonObjectT) -> Self:
        name = json.get('name')

        if name is None:
            raise AlrinConfigurationError('The database table must specify a name')

        if not isinstance(name, str):
            raise AlrinConfigurationError(f'The database name must be a string, not {name}')

        compression = json.get('compression')

        if compression is not None and compression not in COMPRESSION_VALUES:
            raise AlrinConfigurationError(f'Invalid compression value {compression!r}')

        return cls(name, compression)

    def get_db_file_name(self) -> str:
        if self.compression:
            return f'{self.name}.db.tar.{self.compression}'

        return f'{self.name}.db.tar'


@dataclass(frozen=True)
class AlrinVaultMetadata:
    database: AlrinDatabaseMetadata

    @classmethod
    def from_json(cls, json: JsonObjectT) -> Self:
        database = json.get('database')

        if not isinstance(database, JsonObject):
            raise AlrinConfigurationError('Expected a database table in the config')

        return cls(AlrinDatabaseMetadata.from_json(database))


@dataclass(frozen=True)
class AlrinPkgbuildMetadata:
    version: AlrinPackageVersion
    builddate: int | None
    git_root: str | None
    add_pkgrel_suffix: bool
    note: str | None

    @classmethod
    def from_json(cls, json: JsonObjectT) -> Self:
        return cls(
            version=AlrinPackageVersion.from_json(json),
            builddate=cast('int | None', json.get('builddate')),
            add_pkgrel_suffix=cast('bool', json.get('add_pkgrel_suffix', False)),
            git_root=cast('str | None', json.get('git_root')),
            note=cast('str | None', json.get('note')),
        )


@dataclass(frozen=True)
@functools.total_ordering
class AlrinPackageVersion:
    pkgver: str
    pkgrel: str
    epoch: int | None

    @classmethod
    def from_srcinfo(cls, srcinfo: SourceInfo) -> Self:
        return cls(
            pkgver=str(srcinfo.base.version.pkgver),
            pkgrel=str(srcinfo.base.version.pkgrel),
            epoch=srcinfo.base.version.epoch.value if srcinfo.base.version.epoch else None,
        )

    @classmethod
    def from_json(cls, json: JsonObjectT) -> Self:
        return cls(
            pkgver=cast('str', json['pkgver']),
            pkgrel=cast('str', json['pkgrel']),
            epoch=cast('int | None', json.get('epoch')),
        )

    @classmethod
    def from_string(cls, string: str) -> Self:
        if match := re.match(r'((?P<epoch>\d+):)?(?P<pkgver>[^-]+)-(?P<pkgrel>\d+(.\d+)?)', string):
            groups = match.groupdict()

            return cls(
                pkgver=groups['pkgver'],
                pkgrel=groups['pkgrel'],
                epoch=int(groups['epoch']) if groups.get('epoch') else None,
            )

        raise AlrinPackageMetadataError(f'Could not parse version {string!r}')

    def __lt__(self, other: AlrinPackageVersion) -> bool:
        self_epoch = self.epoch or float('-inf')
        other_epoch = other.epoch or float('-inf')

        return self_epoch < other_epoch or self.pkgver < other.pkgver or self.pkgrel < other.pkgrel

    def __str__(self) -> str:
        if self.epoch:
            return f'{self.epoch}:{self.pkgver}-{self.pkgrel}'

        return f'{self.pkgver}-{self.pkgrel}'
