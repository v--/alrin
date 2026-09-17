# Alrin

Alrin (**A**rch **L**inux **r**epository for [**i**vasilev.**n**et](https://ivasilev.net)) is a bunch of code that grew out of me managing [my](https://ivasilev.net/pacman) [pacman](https://pacman.archlinux.page/)/[ALPM](https://alpm.archlinux.page/) repository.

In short, this tool allows describing an ALPM repository in a git-friendly format. It operates a [Viat](https://github.com/v--/viat) vault in either the current directory or the one specified by the `ALRIN_VAULT` environment variable. Packages with `PKGBUILD`/`.SRCINFO` files are stored as git submodules in `$ALRIN_VAULT/pkgbuild`.

The builds use [`makechrootpkg`](https://man.archlinux.org/man/makechrootpkg.1) and the resulting files are put in the `$ALRIN_VAULT/pkgdest` directory, along with the package databases.

> [!NOTE]
> It is likely that every person managing a pacman repository has needs different from mine. If you find this tool useful, you can always contact me or open a pull request with whatever changes you need.

## Quickstart

To use `alrin` without cloning the repository, you can utilize [`pipx`](https://pipx.pypa.io/en/stable/):

```shell
pipx install git+https://github.com/v--/alrin
```

A new vault can be initialized by running `alrin init <dbname>` in an empty directory. Some basic configuration can then be done by editing `$ALRIN_STATE/alrin.toml`.

You can optionally copy or symlink a `pacman.conf` file in `$ALRIN_VAULT` and it will get synchronized before very build. To feed the existing repository to `makechrootpkg`, append

```ini
[<repo name>]
Server = file:///<vault path>/pkgdest/$arch
```

The following can then register `<package>` from the AUR:

```shell
alrin pkg add <package>
```

The following updates all packages:

```shell
alrin bulk update
```

If you want to generate reports for updated packages, you can use

```shell
alrin bulk update --summary-path summary.json
```

The [tricky job](https://stackoverflow.com/a/35743109/2756776) of removing a git submodule, along with the associated build files and Viat metadata, can be done by

```shell
alrin pkg remove <package>
```

There are two more commands --- see below.

## GPG Keyring

Alrin creates a custom keyring at `$ALRIN_VAULT/keyring` that is used during the build. It can be managed via

```shell
GNUPGHOME=$ALRIN_VAULT/keyring gpg ...
```

This directory is intended to be ignored by version control. The `$ALRIN_VAULT/keyring_backup.asc` file can be used to backup and restore its public keys via

```shell
alrin keyring backup
```

and

```shell
alrin keyring restore
```

## Some examples

The following is an excerpt from `.viat/store.toml` in my personal state repository:

```toml
["pkgbuild/dpsprep"]
pkgver = "2.6.4"
pkgrel = "3.314"
builddate = 1781369820
```

If modified during the build, `pkgver`, `pkgrel` and `buliddate` attributes are set after each `pkg update <package>` or `bulk-update`. The `builddate` is reused as `SOURCE_DATE_EPOCH` if running `pkg rebuild <package>` (if a [reproducible](https://reproducible-builds.org) package needs to be recreated for whatever reason; note that `.BUILDINFO` will differ the package's dependencies are updated).

For Python packages, whose installation directory depends on the version of Python, a custom suffix can be automatically added to `pkgrel`, like so (see [this thread](https://bbs.archlinux.org/viewtopic.php?id=311573) for details):

```toml
["pkgbuild/python-djvulibre-python"]
pkgver = "0.9.3"
pkgrel = "3.314"
add_pkgrel_suffix = true
builddate = 1783420854
```

Finally, consider the following example:

```toml
["pkgbuild/mkinitcpio-growrootfs"]
git_root = "ec2-packages"
pkgver = "2.1"
pkgrel = "1"
builddate = 1781374235
```

Here, `pkgbuild/mkinitcpio-growrootfs` is a symlink to `../ec2-packages/mkinitcpio-growrootfs`, where `ec2-packages` is [this repository](https://git.uplinklabs.net/steven/ec2-packages). The role of the `git_root` attribute should be obvious.
