import pathlib
import re
import tarfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import IO


@dataclass
class AlpmPackageInfo:
    pkgname: str
    pkgbase: str
    version: str
    arch: str


def read_database(path: pathlib.Path) -> Sequence[AlpmPackageInfo]:
    with tarfile.open(path) as tar_file:
        return [process_pkgtar(file) for file in map(tar_file.extractfile, tar_file.getmembers()) if file]


def process_pkgtar_iter(file: IO[bytes]) -> Iterable[tuple[str, str]]:
    key_name: str = ''
    content: str = ''

    while (raw_line := file.readline()):
        line: str = raw_line.decode('utf-8')

        if m := re.match(r'%(?P<key_name>\w+)%', line):
            if len(content) > 0:
                yield key_name, content.rstrip()
                content = ''

            key_name = m.groupdict()['key_name']
        else:
            content += line

    if len(content) > 0:
        yield key_name, content.rstrip()


def process_pkgtar(file: IO[bytes]) -> AlpmPackageInfo:
    full_data = dict(process_pkgtar_iter(file))

    return AlpmPackageInfo(
        pkgname=full_data['NAME'],
        pkgbase=full_data['BASE'],
        version=full_data['VERSION'],
        arch=full_data['ARCH'],
    )
