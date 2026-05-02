import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

_REQUIRED_FILES = [
    "games/poe1/bot_data/mods_jewel.json",
    "games/poe1/bot_data/mods_gear.json",
]


def validate_repoe(root: Path | None = None) -> bool | list[str]:
    if root is None:
        root = Path(__file__).resolve().parent.parent

    errors = []

    for rel in _REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            msg = f"{rel}: file not found"
            logger.warning(msg)
            errors.append(msg)
            continue

        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            msg = f"{rel}: invalid JSON — {exc}"
            logger.warning(msg)
            errors.append(msg)
            continue

        if not isinstance(data, dict) or not data:
            msg = f"{rel}: expected a non-empty JSON object"
            logger.warning(msg)
            errors.append(msg)

    return errors if errors else True


def health(root: Path | None = None) -> dict:
    if root is None:
        root = Path(__file__).resolve().parent.parent

    result = validate_repoe(root)
    if result is True:
        return {"ok": True}
    return {"ok": False, "errors": result}


def watch_repoe(
    callback: Callable[[Path], None],
    root: Path | None = None,
    interval: float = 1.0,
    stop: threading.Event | None = None,
) -> threading.Thread:
    if root is None:
        root = Path(__file__).resolve().parent.parent

    if stop is None:
        stop = threading.Event()

    watched = [root / rel for rel in _REQUIRED_FILES]
    mtimes: dict[Path, float] = {}
    for path in watched:
        try:
            mtimes[path] = path.stat().st_mtime
        except FileNotFoundError:
            mtimes[path] = 0.0

    def _poll() -> None:
        while not stop.wait(interval):
            for path in watched:
                try:
                    mtime = path.stat().st_mtime
                except FileNotFoundError:
                    mtime = 0.0
                if mtime != mtimes[path]:
                    mtimes[path] = mtime
                    try:
                        callback(path)
                    except Exception:
                        logger.exception("watch_repoe callback raised for %s", path)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    return thread
