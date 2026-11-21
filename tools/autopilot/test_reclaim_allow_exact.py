"""FLEET-WATCH-R4 11-21: grt_arm_reclaim reaches a terminal attempt dir under a protected rows dir through the CURRENT guard's exact allow, and the sweep retries guard-refused / old rows."""
import json, os, pathlib, sys
sys.path.insert(0, os.path.dirname(__file__))
import test_grt_reclaim_routed as T
import kit_wave as K

GUARD = str(pathlib.Path(__file__).resolve().parent.parent / "fleet" / "ot_delete_guard.py")


def test_attempt_under_protected_rows_dir_is_reclaimed_with_exact_allow(tmp_path, monkeypatch):
    rows = tmp_path / "runs" / "qwen_compute" / "kit-wave"
    rows.mkdir(parents=True)
    d, rec = T._mk(rows / "ev", 2, False)
    monkeypatch.setattr(K, "RECLAIM_GUARD", GUARD)
    monkeypatch.setenv("HOME", str(tmp_path))
    st = tmp_path / ".local/state/ot-delete-guard"; st.mkdir(parents=True)
    (st / "protected.txt").write_text(str(rows) + "\n")
    out = K.grt_arm_reclaim(T.AP, rec, ["localhost"])
    assert "MB" in out and "REFUSE" not in out, out
    assert not (d / "run/results/asap7/x/base/3_place.odb").exists()
    assert str(d) in (st / "allow_exact.txt").read_text()
    assert rows.exists() and (d / "spec.json").exists()                     # only run DBs go; the protected ancestor and the spec stay


def test_signoff_dir_is_never_allowed(tmp_path, monkeypatch):
    rows = tmp_path / "runs" / "d" / "kit-wave"; rows.mkdir(parents=True)
    d, rec = T._mk(rows / "ev", 2, False)
    (d / "signoff.json").write_text("{}")
    monkeypatch.setattr(K, "RECLAIM_GUARD", GUARD); monkeypatch.setenv("HOME", str(tmp_path))
    st = tmp_path / ".local/state/ot-delete-guard"; st.mkdir(parents=True); (st / "protected.txt").write_text(str(rows) + "\n")
    assert "signoff.json" in K.grt_arm_reclaim(T.AP, rec, ["localhost"]) and not (st / "allow_exact.txt").exists()
