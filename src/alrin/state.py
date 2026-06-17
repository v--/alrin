from dataclasses import dataclass

lazy from viat import ViatVault

lazy from alrin.resolver import AlrinPathResolver


@dataclass(frozen=True)
class AlrinSharedState:
    vault: ViatVault
    resolver: AlrinPathResolver
    verbose_logging: bool
