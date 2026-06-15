# Alrin

Alrin (**A**rch **L**inux **r**epository for [**i**vasilev.**n**et](https://ivasilev.net)) is a bunch of code that grew out of me managing [my](https://ivasilev.net/pacman) [pacman](https://pacman.archlinux.page/)/[ALPM](https://alpm.archlinux.page/) repository.

In short, this tool needs a repository for managing state, say `alrin-state`, determined by the `ALRIN_STATE_REPO` environment variable or the working directory as a fallback. Packages with `PKGBUILD`/`.SRCINFO` files are stored as git submodules in `alrin-state/pkgbuild`, which allows easily checking for updates by simply pulling. [Viat](https://github.com/v--/viat) is used to store versions and some other metadata --- see below.

The builds use [`makechrootpkg`](https://man.archlinux.org/man/makechrootpkg.1) and the resulting files are put in the `alrin-state/pkgdest` directory, along with the package databases.

> [!NOTE]
> It is likely that every person managing a pacman repository has needs different from mine. If you find this tool useful, you can always contact me or open a pull request with whatever changes you need.

## Quickstart

To use `alrin` without cloning the repository, you can utilize [`pipx`](https://pipx.pypa.io/en/stable/):

```shell
pipx install git+https://github.com/v--/alrin
```

A new state repository can be initialized by running a variation of

```shell
mkdir $ALRIN_STATE_REPO
cp --recursive viat_sample $ALRIN_STATE_REPO/.viat
cd $ALRIN_STATE_REPO
git init
```

The following can then register `<package>` from the AUR:

```shell
alrin pkg-add <package>
```

The following updates all packages:

```shell
alrin bulk-update
```

The [tricky job](https://stackoverflow.com/a/35743109/2756776) of removing a git submodule, along with the associated build files and Viat metadata, can be done by

```shell
alrin pkg-remove <package>
```

There are two more commands --- see below.

## Some examples

The following is an excerpt from `.viat/store.toml` in my personal state repository:

```toml
["pkgbuild/dpsprep"]
pkgver = "2.6.4"
pkgrel = "3.314"
builddate = 1781369820
```

If modified during the build, `pkgver`, `pkgrel` and `buliddate` attributes are set after each `pkg-update <package>` or `bulk-update`. The `builddate` is reused as `SOURCE_DATE_EPOCH` if running `pkg-rebuild <package>` (if a [reproducible](https://reproducible-builds.org) package needs to be recreated for whatever reason).

Here is a slightly more complicated example:

```toml
["pkgbuild/python-postfix-policyd-spf"]
extra_makedepends = [
    "python-setuptools",
]
pkgver = "2.0.2"
pkgrel = "5.314"
builddate = 1781386810
add_python_suffix = true
```

The role of `extra_makedepends` should be obvious. The `add_python_suffix` flag determines whether to automatically add a Python version suffix to `pkgrel` in case the package has none. See [this thread](https://bbs.archlinux.org/viewtopic.php?id=311573) for details.

Finally, consider the following example:

```toml
["pkgbuild/mkinitcpio-growrootfs"]
git_root = "ec2-packages"
pkgver = "2.1"
pkgrel = "1"
builddate = 1781374235
```

Here, `pkgbuild/mkinitcpio-growrootfs` is a symlink to `../ec2-packages/mkinitcpio-growrootfs`, where `ec2-packages` is [this repository](https://git.uplinklabs.net/steven/ec2-packages). The role of the `git_root` attribute should be obvious.

There are some more supported attributes like `skip_pgp` (in case the PGP signatures have been verified independently) or `note` (for plain text notes).
