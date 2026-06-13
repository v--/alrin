class AlrinException(Exception):
    pass


class AlrinError(AlrinException):
    pass


class AlrinPackageError(AlrinError):
    pass


class AlrinPackageMetadataError(AlrinPackageError):
    pass


class AlrinPackageBuildError(AlrinPackageError):
    pass
