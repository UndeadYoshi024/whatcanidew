import logging
from pathlib import Path

from tools.health import validate_repoe


def run_health_check(root: Path | None = None) -> None:
    result = validate_repoe(root)
    if result is not True:
        logging.getLogger(__name__).warning(
            "repoe validation failed: %d error(s) — see above", len(result)
        )
