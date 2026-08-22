class AlrinException(Exception):
    pass


class AlrinError(AlrinException):
    pass


class AlrinVaultError(AlrinError):
    pass


class AlrinConfigurationError(AlrinError):
    pass


class AlrinJailError(AlrinError):
    pass


class AlrinPackageError(AlrinError):
    pass


class AlrinPackageMetadataError(AlrinPackageError):
    pass


class AlrinPackageBuildError(AlrinPackageError):
    pass


class AlrinKeyringError(AlrinError):
    pass
