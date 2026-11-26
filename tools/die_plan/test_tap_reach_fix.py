"""tap_reach_fix.py (C-TAP-REACH): static check + default-off plan flag generator."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import reach_fix as RF  # noqa: E402
import tap_reach_fix as TR  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _plan(tmp_path, raw, name="plan.json"):
    p = tmp_path / name
    p.write_text(json.dumps(raw))
    return p


def _measure(raw, path, tn="mid"):
    P = RF.plan_obj(raw, path)
    RF._reset_caches(P)
    return TR.measure(P, tn, TR.RADIUS_UM, RF)[0]


def test_check_reports_seats_beyond_radius(tmp_path):
    path = _plan(tmp_path, EX)
    row = _measure(copy.deepcopy(EX), path)
    assert row["over"] > 0 and row["c1_max_um"] > TR.RADIUS_UM
    assert row["over220"] <= row["over"] and row["over300"] <= row["over220"]
    lines = TR.findings(copy.deepcopy(EX), str(path))
    assert any(l.startswith("WARN ADV-TAP-REACH mid:") for l in lines), lines


def test_flag_absent_is_byte_identical(tmp_path):
    raw = copy.deepcopy(EX)
    path = _plan(tmp_path, raw)
    before = json.dumps(raw, sort_keys=True)
    selected, report = TR.derive(raw, path, tmp_path)
    assert (selected, report) == ([], {})
    assert json.dumps(raw, sort_keys=True) == before
    raw[TR.FLAG] = {"enable": 0}
    assert TR.derive(raw, path, tmp_path) == ([], {})


def test_flag_adds_taps_and_every_seat_inside_radius(tmp_path):
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1}
    path = _plan(tmp_path, raw)
    selected, report = TR.derive(raw, path, tmp_path)
    assert "mid" in selected and report["mid"]["status"] == "derive", report
    ck = raw["partition_types"]["mid"]["clock"]
    assert ck["tap_mode"] == "grid+explicit" and ck["added_taps"]
    after = _measure(raw, path)
    assert after["over"] == 0 and after["c1_max_um"] <= TR.RADIUS_UM, after
    assert report["mid"]["after"]["over"] < report["mid"]["before"]["over"]
    # original table untouched: new taps are appended after the existing grid taps
    import schema as S
    base = [n for n, _x, _y in S.tap_grid(RF.plan_obj(copy.deepcopy(EX), path), "mid")]
    now = [n for n, _x, _y in S.tap_grid(RF.plan_obj(raw, path), "mid")]
    assert now[:len(base)] == base and len(now) > len(base)


def test_idempotent(tmp_path):
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1}
    path = _plan(tmp_path, raw)
    TR.derive(raw, path, tmp_path)
    once = json.dumps(raw, sort_keys=True)
    selected, _ = TR.derive(raw, path, tmp_path)
    assert selected == [] and json.dumps(raw, sort_keys=True) == once


def test_types_regex_scopes_the_generator(tmp_path):
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1, "types": "^nomatch$"}
    path = _plan(tmp_path, raw)
    before = json.dumps(raw, sort_keys=True)
    assert TR.derive(raw, path, tmp_path) == ([], {})
    assert json.dumps(raw, sort_keys=True) == before


def test_registered_as_plan_advisory_check():
    import plan_advisory as PA
    assert ("TAP-REACH", "tap_reach_fix") in PA.CHECKS and callable(TR.findings)


def test_parallel_jobs_match_serial(tmp_path):
    a, b = copy.deepcopy(EX), copy.deepcopy(EX)
    a[TR.FLAG] = {"enable": 1}
    b[TR.FLAG] = {"enable": 1, "jobs": 2}
    pa, pb = _plan(tmp_path, a, "a.json"), _plan(tmp_path, b, "b.json")
    sa, _ = TR.derive(a, pa, tmp_path)
    sb, _ = TR.derive(b, pb, tmp_path)
    assert sa == sb and a["partition_types"] == b["partition_types"]


def test_distant_legal_site_is_not_a_fix(tmp_path, monkeypatch):
    import schema as S
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1}
    path = _plan(tmp_path, raw)
    before = json.dumps(raw["partition_types"]["mid"], sort_keys=True)
    # every legal site is 600 um from the seats it should serve
    monkeypatch.setattr(S, "tap_clear", lambda t, x, y, *a, **k: (x + 600.0, y))
    selected, report = TR.derive(raw, path, tmp_path)
    assert selected == [] and report["mid"]["status"] in ("unchanged", "reverted: over-radius seats %s -> %s, max %s -> %s" % (
        report["mid"]["before"]["over"], report["mid"]["before"]["over"], report["mid"]["before"]["c1_max_um"],
        report["mid"]["before"]["c1_max_um"])) or report["mid"]["status"].startswith("reverted")
    assert json.dumps(raw["partition_types"]["mid"], sort_keys=True) == before


def test_span_stage_splits_wide_taps_and_is_opt_in(tmp_path):
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1}
    path = _plan(tmp_path, raw)
    TR.derive(raw, path, tmp_path)
    reach_only = copy.deepcopy(raw)
    m0 = _measure(raw, path)
    raw2 = copy.deepcopy(reach_only)
    raw2[TR.FLAG] = {"enable": 1, "span_um": 150}
    sel, rep = TR.derive(raw2, path, tmp_path)
    m1 = _measure(raw2, path)
    if m0["span_taps_over_300"] == 0 and TR.SPAN_UM == 300:
        pass
    # with a 150-um span limit the span stage must not leave more wide taps than before and must keep every seat in reach
    P = RF.plan_obj(raw2, path)
    RF._reset_caches(P)
    wide0 = TR.measure(RF.plan_obj(reach_only, path), "mid", TR.RADIUS_UM, RF, 150)[0]["span_taps_over_300"]
    wide1 = TR.measure(P, "mid", TR.RADIUS_UM, RF, 150)[0]["span_taps_over_300"]
    assert wide1 <= wide0 and m1["over"] == 0
    if sel:
        assert wide1 < wide0 and rep["mid"]["status"] == "derive"


def test_flag_is_in_the_schema_and_the_dump(tmp_path):
    import schema as S
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1, "radius_um": 220, "span_um": 300, "rounds": 3, "jobs": 2, "types": "^mid$"}
    assert S.validate(raw) == []
    raw[TR.FLAG]["bogus"] = 1
    assert S.validate(raw)
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert "tap_reach" in on_disk["properties"]


def test_type_whose_reset_relays_move_is_reverted(tmp_path, monkeypatch):
    raw = copy.deepcopy(EX)
    raw[TR.FLAG] = {"enable": 1}
    path = _plan(tmp_path, raw)
    before = json.dumps(raw["partition_types"]["mid"], sort_keys=True)
    calls = []
    monkeypatch.setattr(TR, "_reset_sig", lambda P, tn: calls.append(1) or ([("rst_rl_0", float(len(calls)), 0.0)], None))
    selected, report = TR.derive(raw, path, tmp_path)
    assert selected == [] and report["mid"]["status"].startswith("reverted: the new taps move")
    assert json.dumps(raw["partition_types"]["mid"], sort_keys=True) == before


def test_row_form_only_sets_the_flag_and_is_idempotent(tmp_path):
    src = _plan(tmp_path, EX, "in.json")
    out, rep = tmp_path / "out.json", tmp_path / "rep.json"
    assert TR.main(["--row", str(src), str(out), str(rep), "--types", "^mid$", "--jobs", "2"]) == 0
    got = json.loads(out.read_text())
    assert got[TR.FLAG] == {"enable": 1, "types": "^mid$", "jobs": 2}
    assert {k: v for k, v in got.items() if k != TR.FLAG} == EX              # nothing else touched
    out2 = tmp_path / "out2.json"
    assert TR.main(["--row", str(out), str(out2), str(rep), "--span", "300"]) == 0
    assert json.loads(out2.read_text())[TR.FLAG] == {"enable": 1, "types": "^mid$", "jobs": 2, "span_um": 300.0}
