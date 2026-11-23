import os
from types import SimpleNamespace

from gateway import darwin_exit_lock, status


def test_requires_kernel_exit_and_matching_process_incarnation(monkeypatch):
    monkeypatch.setattr(darwin_exit_lock.sys, "platform", "darwin")
    monkeypatch.setattr(status, "get_process_start_time", lambda _pid: 123)
    state = "?E"
    monkeypatch.setattr(
        darwin_exit_lock.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=state),
    )

    assert darwin_exit_lock.process_is_exiting(42, 123)
    assert not darwin_exit_lock.process_is_exiting(42, 122)
    state = "S"
    assert not darwin_exit_lock.process_is_exiting(42, 123)


def test_cannot_replace_another_lock_generation(tmp_path, monkeypatch):
    path = tmp_path / "gateway.lock"
    monkeypatch.setattr(darwin_exit_lock, "process_is_exiting", lambda *_args: True)

    with path.open("w") as handle:
        os.replace(path, tmp_path / "old.lock")
        path.write_text("replacement")
        assert not darwin_exit_lock.replace_exiting_lock(path, handle, 42, 123)
        assert path.read_text() == "replacement"


def test_replaces_inode_owned_by_exiting_process(tmp_path, monkeypatch):
    path = tmp_path / "gateway.lock"
    monkeypatch.setattr(darwin_exit_lock, "process_is_exiting", lambda *_args: True)

    with path.open("w") as handle:
        assert darwin_exit_lock.replace_exiting_lock(path, handle, 42, 123)
    assert not path.exists()
