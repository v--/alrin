from alrin.pkginfo import parse_version


def test_parse_version() -> None:
    version = parse_version('3-1')
    assert version.pkgver == '3'
    assert version.pkgrel == '1'
    assert version.epoch is None


def test_parse_version_with_pkgrel_suffix() -> None:
    version = parse_version('3-1.314')
    assert version.pkgver == '3'
    assert version.pkgrel == '1.314'
    assert version.epoch is None


def test_parse_version_with_epoch() -> None:
    version = parse_version('2:3-1')
    assert version.pkgver == '3'
    assert version.pkgrel == '1'
    assert version.epoch == 2
