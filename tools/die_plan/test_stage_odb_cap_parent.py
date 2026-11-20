"""stage_odb_cap --parent (QC slw_fe_v1__cl95cd1d0c, KIT_NOT_SELF_CONTAINED at place): the watcher deleted 2_3_floorplan_tapcell.odb while the
ot-job publish of the run dir was walking it (publish run: ENOENT) because it outlived run_kit.sh (nohup, 36 h).  It now stops when the
run_kit.sh that started it has ended and never deletes after that."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_odb_cap as C  # noqa: E402


def test_parent_alive_and_gone():
    assert C.parent_alive(None) and C.parent_alive(0) and C.parent_alive(os.getpid())
    p = subprocess.Popen(["true"])
    p.wait()
    assert not C.parent_alive(p.pid)


def test_once_deletes_nothing_when_the_parent_is_gone(tmp_path, monkeypatch):
    logs = []
    monkeypatch.setattr(C, "plan", lambda base, now, files, ended=False: [(str(tmp_path / "2_3_floorplan_tapcell.odb"), 1)])
    (tmp_path / "2_3_floorplan_tapcell.odb").write_text("x")
    monkeypatch.setattr(C, "kept_by_env", lambda kit: None)
    done = C.once(str(tmp_path), str(tmp_path), False, log=logs.append, scan=lambda k: ([], []), alive=lambda: False)
    assert done == [] and (tmp_path / "2_3_floorplan_tapcell.odb").exists() and any("parent gone" in m for m in logs)
    done = C.once(str(tmp_path), str(tmp_path), False, log=logs.append, scan=lambda k: ([], []), alive=lambda: True)
    assert len(done) == 1 and (tmp_path / "2_3_floorplan_tapcell.odb").stat().st_size == 0      # FLOW-FIX-2045: a live run empties it (placeholder)


def test_watch_returns_without_deleting_when_the_parent_is_gone(tmp_path):
    p = subprocess.Popen(["true"])
    p.wait()
    logs = []
    C.watch(str(tmp_path), str(tmp_path), 0.01, 1.0, logs.append, p.pid)
    assert any("watcher ends without deleting" in m for m in logs)


def test_the_generated_run_kit_passes_its_pid_to_the_watcher():
    src = (HERE / "gen_phys.py").read_text()
    assert '--max-hours 36 --parent $$ >>"$K/stage_odb_cap.log"' in src
