import os, sys, subprocess, json, shlex
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as K


class AP:
    HUB_NAME = "localhost"
    @staticmethod
    def sh(argv, timeout=0, input=None):
        p = subprocess.run(argv, capture_output=True, text=True, input=input)
        return p.returncode, p.stdout + p.stderr, ""


def _mk(tmp, n, routed):
    d = tmp / "items" / "t47" / f"attempt_{n}"
    b = d / "run" / "results" / "asap7" / "x" / "base"
    b.mkdir(parents=True)
    (b / "3_place.odb").write_text("x")
    if routed:
        (b / "5_2_route.odb").write_text("x")
    (d / "spec.json").write_text(json.dumps({"work": str(d)}))
    return d, {"dir": str(d), "item": "t47", "attempt": n}


def test_routed_unsigned_attempt_not_reclaimed_until_superseded(tmp_path, monkeypatch):
    g = tmp_path / "g.py"; g.write_text("import sys; sys.exit(0)")
    monkeypatch.setattr(K, "RECLAIM_GUARD", str(g))
    monkeypatch.setenv("HOME", str(tmp_path))
    pl = tmp_path / ".local/state/ot-delete-guard"; pl.mkdir(parents=True); (pl / "protected.txt").write_text("")
    d2, r2 = _mk(tmp_path, 2, True)
    out = K.grt_arm_reclaim(AP, r2, ["localhost"])
    assert "routed result unsigned" in out and (d2 / "run/results/asap7/x/base/5_2_route.odb").exists()
    _mk(tmp_path, 3, True)
    out = K.grt_arm_reclaim(AP, r2, ["localhost"])
    assert "MB" in out and not (d2 / "run/results/asap7/x/base/5_2_route.odb").exists()
