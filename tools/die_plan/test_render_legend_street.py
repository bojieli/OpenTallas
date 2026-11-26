"""R6-RENDER-LEGEND-STREET (VIS-REOWN 11-25, COORD): die render legend lists every type, stations above taps, PRE/static counts in the
title instead of a bare 'G0 PASS', street map shaded by per-street demand, per-type mode -> render_type_heat."""
import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import render  # noqa: E402
import streets as ST  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
PRE_LOG = "FAIL GEOM station x in cl_a\nFAIL GEOM station y in cl_b\nFAIL TOOLS-ARITY f/2\nWARN ADV-REACH leg 410 um\nPLAN-GATE-PRE FAIL\n"


def test_pre_counts_from_json_log_dict_and_none(tmp_path):
    (tmp_path / "pre.log").write_text(PRE_LOG)
    (tmp_path / "pre.json").write_text(json.dumps({"findings": ["FAIL GEOM a", "FAIL REACH-UNCHECKED b"], "advisories": ["WARN ADV x"]}))
    c, adv = render.pre_counts(str(tmp_path / "pre.log"))
    assert c == {"GEOM": 2, "TOOLS": 1} and adv == 1
    assert render.pre_counts(str(tmp_path / "pre.json")) == ({"GEOM": 1, "REACH": 1}, 1)
    assert render.pre_counts({"findings": []}) == ({}, 0)
    assert render.pre_counts(None) is None and render.pre_counts(str(tmp_path / "missing")) is None


def test_title_never_a_bare_g0_pass():
    R = check.Report()
    R.warn("x", "w")
    t = render.status_title(None, R, None)
    assert "G0 PASS" not in t and "G0 only: 0 errors / 1 warnings" in t and "PRE/static not supplied" in t
    t = render.status_title(None, R, {"findings": ["FAIL GEOM a", "FAIL GEOM b", "FAIL INPUT c"]})
    assert "PRE/static FAIL 2 classes: GEOM 2, INPUT 1" in t
    assert "PRE/static PASS" in render.status_title(None, R, {"findings": []})


def test_type_colours_distinct_for_60_types():
    pytest.importorskip("matplotlib")
    cols = render.type_colors([f"t{i:02d}" for i in range(60)])
    assert len(set(cols.values())) == 60


def test_render_legend_lists_every_type_and_title_has_pre(tmp_path):
    pytest.importorskip("matplotlib")
    (tmp_path / "pre.log").write_text(PRE_LOG)
    png = tmp_path / "p.png"
    check.run(copy.deepcopy(EX), png=png, pre=str(tmp_path / "pre.log"))
    rec = json.loads(Path(str(png) + ".json").read_text())
    types = sorted(EX["partition_types"])
    assert rec["types"] == len(types) and [l.split(" ", 1)[1] for l in rec["legend_types"]] == types
    assert "PRE/static FAIL 2 classes: GEOM 2, TOOLS 1" in rec["title"] and "G0 PASS" not in rec["title"]
    assert rec["zorder"]["station"] > rec["zorder"]["clock_tap"]
    assert png.stat().st_size > 10000


def test_streets_shaded_by_demand(tmp_path):
    pytest.importorskip("matplotlib")
    ko = [(69.12 + k * 369.12, 69.12, 369.12 + k * 369.12, 369.12, f"c{k}") for k in range(2)]
    flows = [("lane_a", 512, [(0.0, 400.0), (900.0, 400.0)]), ("lane_b", 64, [(380.0, 0.0), (380.0, 500.0)])]
    A = ST.analyze(900.0, 500.0, ko, ST.config(), flows=flows)
    req = A["req"][A["net"]]
    assert req.size and float(req.max()) > float(req.min()) + 1.0          # a gradient, not one flat width
    assert A["narrow"].shape == A["net"].shape
    ST.render(A, ko, tmp_path / "s.png", 900.0, 500.0, "t")
    assert (tmp_path / "s.png").stat().st_size > 1000
    assert ST.analyze(900.0, 500.0, ko, ST.config())["req"] is None         # flat mode: no demand field (unchanged look)


def test_per_type_mode_delegates_to_render_type_heat(tmp_path, monkeypatch):
    import render_type_heat
    seen = []
    monkeypatch.setattr(render_type_heat, "main", lambda argv: seen.append(argv) or 0)
    assert render.main(["plan.json", str(tmp_path), "--types", "a,b"]) == 0
    assert render.main(["plan.json", str(tmp_path), "--types", "all"]) == 0
    assert seen == [["plan.json", str(tmp_path), "--types", "a,b"], ["plan.json", str(tmp_path)]]
