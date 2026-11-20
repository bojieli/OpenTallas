"""HEAD-CROSSING-1119 (COORD 11-20): a post-freeze site nudge must re-freeze the site digest, so nudge -> reach passes
without a hand re-freeze (r12 and r13 both failed frozen_home_match after the row nudge)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_reach as CR  # noqa: E402


def _tree():
    t = dict(sites={"b0": [0.0, 0.0], "r1": [100.0, 0.0], "r2": [300.0, 0.0]},
             parent_of={"r1": "b0", "r2": "r1"}, taps=[], node_buf={}, meta={})
    t["meta"]["physical_dme"] = CR.freeze_sites(t, 405.0)
    return t


def test_hand_edit_breaks_frozen_match():
    t = _tree()
    t["sites"]["r1"] = [100.054, 0.27]
    r = CR.actual_reach(t, 405.0)
    assert r["frozen_home_match"] is False and r["verdict"] == "FAIL"


def test_apply_moves_then_reach_passes(tmp_path):
    t = _tree()
    old = t["meta"]["physical_dme"]["frozen_sites_sha256"]
    CR.apply_moves(t, {"r1": [100.054, 0.27]}, "row nudge")
    r = CR.actual_reach(t, 405.0)
    assert r["verdict"] == "PASS" and r["frozen_home_match"] is True
    pd = t["meta"]["physical_dme"]
    assert pd["site_edits"][-1] == dict(reason="row nudge", cells=1, previous_frozen_sites_sha256=old)
    assert pd["frozen_sites_sha256"] != old


def test_apply_moves_keeps_reach_limit():
    t = _tree()
    CR.apply_moves(t, {"r2": [600.0, 0.0]}, "far move")   # digest matches, the over-reach wire still fails
    r = CR.actual_reach(t, 405.0)
    assert r["frozen_home_match"] is True and r["verdict"] == "FAIL" and r["over_count"] == 1


def test_apply_rejects_unknown_cell_and_empty_reason():
    t = _tree()
    with pytest.raises(KeyError):
        CR.apply_moves(t, {"zz": [1.0, 1.0]}, "x")
    with pytest.raises(ValueError):
        CR.apply_moves(t, {"r1": [1.0, 1.0]}, "")


def test_cli_apply_then_reach(tmp_path):
    src, mv, out = tmp_path / "t.json", tmp_path / "m.json", tmp_path / "o.json"
    src.write_text(json.dumps(_tree()))
    mv.write_text(json.dumps({"moves": {"r1": [100.054, 0.27]}}))
    assert CR.main(["apply", str(src), str(mv), str(out), "--reason", "nudge"]) == 0
    assert CR.main([str(out), "--max-um", "405"]) == 0
