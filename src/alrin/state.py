from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from viat import ViatVault

    from alrin.logging import AlrinLogger
    from alrin.resolver import AlrinPathResolver


@dataclass(frozen=True)
class AlrinSharedState:
    vault: ViatVault
    resolver: AlrinPathResolver
    logger: AlrinLogger
