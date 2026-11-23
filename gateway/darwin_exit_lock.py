"""Recover locks retained by a macOS process that has reached kernel exit."""
from __future__ import annotations

from contextlib import contextmanager
import logging
import os
from pathlib import Path
import stat
import subprocess
import sys

logger = logging.getLogger(__name__)


def process_is_exiting(pid: int, start_time: int | None) -> bool:
    """Require a matching incarnation on both sides of the kernel state query."""
    if sys.platform != "darwin" or pid <= 0 or start_time is None:
        return False
    from gateway.status import get_process_start_time

    if get_process_start_time(pid) != start_time:
        return False
    try:
        result = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "state="],
            capture_output=True, text=True, timeout=1, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    # Darwin ps adds E for a process with P_WEXIT. An unresponsive but live
    # process, including a suspended one, is never grounds to replace a lock.
    state = result.stdout.strip()
    return (result.returncode == 0 and "E" in state and
            get_process_start_time(pid) == start_time)


@contextmanager
def serialize_claim(path: Path):
    """Fence lock replacement against concurrent macOS claims."""
    if sys.platform != "darwin":
        yield True
        return
    from gateway.status import _try_acquire_file_lock
    from gateway.runtime_ownership import _open_checked, _LOCK_FLAGS

    guard_path = path.with_name(f".{path.name}.claim")
    with os.fdopen(_open_checked(guard_path, _LOCK_FLAGS), "r+", encoding="utf-8") as guard:
        yield _try_acquire_file_lock(guard)


def replace_exiting_lock(path: Path, handle, pid: int, start_time: int | None) -> bool:
    """Reclaim the same inode only when its recorded owner is in kernel exit.

    The caller holds the claim interlock, and retries flock on the replacement.
    """
    if not process_is_exiting(pid, start_time):
        return False
    current = path.lstat()
    opened = os.fstat(handle.fileno())
    if (not stat.S_ISREG(current.st_mode) or current.st_uid != os.getuid() or
            current.st_nlink != 1 or not os.path.samestat(current, opened)):
        return False
    path.unlink()
    logger.warning("Recovered %s retained by exiting macOS process %s", path, pid)
    return True
