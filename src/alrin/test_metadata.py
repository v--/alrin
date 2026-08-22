from alrin.metadata import AlrinPackageVersion


def test_parse_version() -> None:
    version = AlrinPackageVersion.from_string('3-1')
    assert version.pkgver == '3'
    assert version.pkgrel == '1'
    assert version.epoch is None


def test_parse_version_with_pkgrel_suffix() -> None:
    version = AlrinPackageVersion.from_string('3-1.314')
    assert version.pkgver == '3'
    assert version.pkgrel == '1.314'
    assert version.epoch is None


def test_parse_version_with_epoch() -> None:
    version = AlrinPackageVersion.from_string('2:3-1')
    assert version.pkgver == '3'
    assert version.pkgrel == '1'
    assert version.epoch == 2
