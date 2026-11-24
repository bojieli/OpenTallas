"""COPY-SLOTS-HOST-1123 (COORD 20:1x): per-host tree-copy slot override file <lock dir>/SLOTS (epyc11 = 4)"""
import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import src_manifest as SM  # noqa: E402


def _fork():
    p = HERE.parent / "fleet" / "ot-tree-fork"
    ld = importlib.machinery.SourceFileLoader("ot_tree_fork_slots", str(p))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
    ld.exec_module(m)
    return m


def test_default_file_env(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_TREE_COPY_SLOTS", raising=False)
    F = _fork()
    assert SM.copy_slots(str(tmp_path)) == 2 and F.host_slots(str(tmp_path)) == 2
    (tmp_path / "SLOTS").write_text("4\n")
    assert SM.copy_slots(str(tmp_path)) == 4 and F.host_slots(str(tmp_path)) == 4
    assert F.CopySlot(lock_dir=str(tmp_path)).n == 4
    monkeypatch.setenv("OT_TREE_COPY_SLOTS", "3")                    # an explicit caller env still wins
    assert SM.copy_slots(str(tmp_path)) == 3 and F.host_slots(str(tmp_path)) == 3
    (tmp_path / "SLOTS").write_text("junk")
    monkeypatch.delenv("OT_TREE_COPY_SLOTS")
    assert SM.copy_slots(str(tmp_path)) == 2


def test_four_copyslots_hold_at_once(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_TREE_COPY_SLOTS", raising=False)
    F = _fork()
    (tmp_path / "SLOTS").write_text("4")
    held = [F.CopySlot(lock_dir=str(tmp_path), wait_s=0, poll_s=0.01, out=lambda *_: None).__enter__() for _ in range(4)]
    assert sorted(h.slot for h in held) == [0, 1, 2, 3]
    try:
        F.CopySlot(lock_dir=str(tmp_path), wait_s=0, poll_s=0.01, out=lambda *_: None).__enter__()
        raise AssertionError("fifth slot granted")
    except F.Busy:
        pass
    for h in held:
        h.__exit__()


def test_slot_sh_reads_target_file(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_TREE_COPY_SLOTS", raising=False)
    (tmp_path / "SLOTS").write_text("4")
    pre = SM.slot_sh(lock_dir=str(tmp_path))
    assert "SLOTS" in pre
    # 3 slots held by python -> the shell still gets slot-3 (n=4 from the file) and exits at once
    F = _fork()
    held = [F.CopySlot(lock_dir=str(tmp_path), wait_s=0, poll_s=0.01, out=lambda *_: None).__enter__() for _ in range(3)]
    r = subprocess.run(["bash", "-c", pre + "echo GOT"], capture_output=True, text=True, timeout=20)
    assert r.stdout.strip() == "GOT", r
    for h in held:
        h.__exit__()
    assert "n=5;" in SM.slot_sh(n=5, lock_dir=str(tmp_path))
