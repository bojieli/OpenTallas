import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_rows as D


def plan():
    return {"die": {"period_ps": 833}, "clock": {"tap_window": {"window_ps": 80.0}, "seam_hold": {"seam_ps": 180.0}},
            "partitions": [], "partition_types": {"a": {"clock": {"die_islands_um": [[0, 0, 1, 1]]}}, "b": {"clock": {}}}}


def test_apply_sets_deletes_and_reports():
    p = plan()
    rows = {"rows": {"a": {"clock.reserved_sites_um": [{"rect_um": [0, 0, 1, 1]}], "clock.die_islands_um": {"$delete": True}}},
            "top": {"clock.seam_hold.seam_ps": 208.0}}
    assert D.apply_rows(p, rows) == ["@top", "a"]
    assert "die_islands_um" not in p["partition_types"]["a"]["clock"]
    assert p["partition_types"]["a"]["clock"]["reserved_sites_um"] == [{"rect_um": [0, 0, 1, 1]}]
    assert p["clock"]["seam_hold"]["seam_ps"] == 208.0
    assert D.apply_rows(p, rows) == []          # second application changes nothing


def test_apply_refuses_unknown_type_and_root_types():
    with pytest.raises(ValueError):
        D.apply_rows(plan(), {"rows": {"zz": {"clock.x": 1}}})
    with pytest.raises(ValueError):
        D.apply_rows(plan(), {"top": {"partition_types.a.clock": {}}})


def test_windows_clamp_skip_and_seam():
    kw = {"plan_sha256": "s", "per_port_ps": {"a": {"clk": 75.0, "clk_c1": 220.0}, "b": {"clk": 10.0}, "gone": {"clk": 1.0}}}
    r = D.window_rows(plan(), kw, skip=("b",), seam=208.0, margin=0.0)
    t = r["top"]["clock.tap_window.per_port_ps"]
    assert t == {"a": {"clk": 75.0, "clk_c1": 208.25}} and r["over_cap"] == [["a", "clk_c1", 220.0]]
    m = D.window_rows(plan(), {"per_port_ps": {"a": {"clk": 75.0, "clk_c1": 199.0}}})        # default margin 10
    assert m["top"]["clock.tap_window.per_port_ps"] == {"a": {"clk": 85.0, "clk_c1": 208.25}}
    assert m["over_cap"] == [["a", "clk_c1", 199.0]] and m["margin_ps"] == 10.0
    assert r["top"]["clock.seam_hold.seam_ps"] == 208.0
    p = plan()
    assert D.apply_rows(p, r) == ["@top"] and p["clock"]["tap_window"]["window_ps"] == 80.0


def test_cli_apply(tmp_path):
    (tmp_path / "p.json").write_text(json.dumps(plan()))
    (tmp_path / "r.json").write_text(json.dumps({"rows": {"b": {"clock.tap_max_sinks": 5}}}))
    assert D.main(["apply", str(tmp_path / "p.json"), str(tmp_path / "r.json"), "-o", str(tmp_path / "o.json")]) == 0
    assert json.loads((tmp_path / "o.json").read_text())["partition_types"]["b"]["clock"]["tap_max_sinks"] == 5


def test_cli_windows_fails_on_a_port_over_the_cap(tmp_path):
    (tmp_path / "p.json").write_text(json.dumps(plan()))
    (tmp_path / "k.json").write_text(json.dumps({"per_port_ps": {"a": {"clk": 205.0}}}))
    argv = ["windows", str(tmp_path / "p.json"), str(tmp_path / "k.json"), "-o", str(tmp_path / "r.json")]
    assert D.main(argv) == 1 and D.main(argv + ["--allow-over-cap"]) == 0 and D.main(argv + ["--margin", "3"]) == 0
