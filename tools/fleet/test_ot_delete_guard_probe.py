"""FLEET-OPS 11-25: the delete guard refuses a probe / private-kit job dir with any file written in the last 12 h (HEAD-SERDES-REFLOOR v2 probe lost its odb 10 min after it finished)"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ot_delete_guard as G  # noqa: E402


def mk(root, rel, age_h):
    d = root / rel
    d.mkdir(parents=True)
    f = d / "run/3_place.odb"
    f.parent.mkdir(parents=True)
    f.write_text("odb")
    t = time.time() - age_h * 3600
    for q in (f, f.parent, d):
        os.utime(q, (t, t))
    return d


def test_young_probe_dir_is_refused_old_one_and_non_probe_are_not(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PROBE_HOLD_S", raising=False)
    young = mk(tmp_path, "claude/kw/runs/s81_head/kit-wave/s81_head/w/private/HEAD-SERDES-REFLOOR/hd_serdes_v2_1125", 0.2)
    old = mk(tmp_path, "claude/kw/runs/s81_head/kit-wave/s81_head/w/private/HEAD-SERDES-REFLOOR/hd_serdes_v1_1124", 30)
    job = mk(tmp_path, "claude/ot-jobs/slw_hc2-place-host-1-2", 1)
    plain = mk(tmp_path, "claude/lane/work", 0.1)
    assert "young probe dir" in (G.young_probe_refusal(str(young)) or "")
    assert "young probe dir" in (G.young_probe_refusal(str(job)) or "")
    assert G.young_probe_refusal(str(old)) is None
    assert G.young_probe_refusal(str(plain)) is None                    # not a probe / job dir: the other guards decide
    f = old / "run/late_report.txt"
    f.write_text("x")                                                    # a report written inside an old probe keeps it
    assert "young probe dir" in (G.young_probe_refusal(str(old)) or "")


def test_hold_is_configurable_and_the_wired_refusal_comes_first(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PROBE_HOLD_S", raising=False)
    d = mk(tmp_path, "claude/x/private/L/k", 5)
    assert G.young_probe_refusal(str(d)) is not None
    monkeypatch.setenv("OT_PROBE_HOLD_S", "3600")
    assert G.young_probe_refusal(str(d)) is None                         # 5 h old > 1 h hold
    monkeypatch.setenv("OT_PROBE_HOLD_S", "0")
    assert G.young_probe_refusal(str(mk(tmp_path, "claude/y/private/L/k2", 0.1))) is None
    monkeypatch.delenv("OT_PROBE_HOLD_S")
    young = mk(tmp_path, "claude/z/private/L/k3", 0.1)
    assert "young probe dir" in (G.refuse(str(young), protected=[], allow=set()) or "")
