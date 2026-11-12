"""KIT-OVERLAY-1: positions-only per-type overlay (type_overlay.py, gen phys --type-overlay).
python3 -m pytest -q tools/die_plan/test_type_overlay.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP  # noqa: E402
import gen_rtl as GR  # noqa: E402
import schema as S  # noqa: E402
import type_overlay as TO  # noqa: E402

LEF = ("MACRO tcore\n  SIZE 20 BY 10 ;\n  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M5 ;\n        RECT 3.0 1.0 3.2 9.0 ;\n"
       "    END\n  END VDD\n  PIN VSS\n    USE GROUND ;\n    PORT\n      LAYER M5 ;\n        RECT 6.0 1.0 6.2 9.0 ;\n"
       "    END\n  END VSS\nEND tcore\n")
LIB = "library(tcore) {\n cell(tcore) { area : 200; }\n}\n"
A, B = [86.4, 86.4], [302.4, 198.72]        # on the 8.64-um lattice


@pytest.fixture
def plan(tmp_path):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    (tmp_path / "tcore.lef").write_text(LEF)
    for c in ("tt", "ff"):
        (tmp_path / f"tcore_{c}.lib").write_text(LIB)
    raw["partition_types"]["mid"]["hard_cores"] = [dict(
        inst="u_hc", module="tcore", lef=str(tmp_path / "tcore.lef"), lib=str(tmp_path / "tcore_tt.lib"),
        origin_um=A, outline_um=[20.0, 10.0])]
    return raw


def kit(raw, out, **kw):
    GP.write_phys(copy.deepcopy(raw), out, trial=True, skip_ir=True, rc_cal=False, types=["mid"], **kw)
    return {str(p.relative_to(out)): p.read_bytes().replace(str(out).encode(), b"<OUT>")
            for p in out.rglob("*") if p.is_file()}


OV = {"format": TO.FORMAT, "type": "mid", "hard_cores": {"u_hc": {"origin_um": B, "orient": "MX"}}}


def test_no_overlay_is_byte_identical_and_null_overlay_adds_only_receipt(plan, tmp_path):
    a, b = kit(plan, tmp_path / "a"), kit(plan, tmp_path / "b")
    assert a == b and "mid/type_overlay.json" not in a
    null = {"format": TO.FORMAT, "type": "mid", "hard_cores": {"u_hc": {"origin_um": A}}}
    c = kit(plan, tmp_path / "c", type_overlay=null)
    assert set(c) - set(a) == {"mid/type_overlay.json"}
    assert {k: v for k, v in c.items() if k != "mid/type_overlay.json"} == a


def test_position_overlay_changes_only_the_types_placement_tcl(plan, tmp_path):
    a, b = kit(plan, tmp_path / "a"), kit(plan, tmp_path / "b", type_overlay=OV)
    assert set(b) - set(a) == {"mid/type_overlay.json"} and set(a) <= set(b)
    assert sorted(k for k in a if a[k] != b[k]) == ["mid/macro_place.tcl"]
    assert b"302.4" in b["mid/macro_place.tcl"] and b"MX" in b["mid/macro_place.tcl"]
    rec = json.loads(b["mid/type_overlay.json"])
    assert rec["changed"] == {"hard_cores": ["u_hc"]} and rec["base_plan_sha256"] != rec["overlaid_plan_sha256"]


def test_overlay_needs_exactly_its_type(plan, tmp_path):
    with pytest.raises(GR.GenError, match="requires exactly --types mid"):
        GP.write_phys(copy.deepcopy(plan), tmp_path / "x", trial=True, skip_ir=True, rc_cal=False, types=["src"],
                      type_overlay=OV)


@pytest.mark.parametrize("bad,match", [
    ({"ports": []}, "ports"),
    ({"lanes": []}, "lanes"),
    ({"latency": {}}, "latency"),
    ({"outline_um": [1, 1]}, "outline"),
    ({"hard_cores": {"u_hc": {"outline_um": [30.0, 10.0]}}}, "outline_um"),
    ({"hard_cores": {"u_hc": {"module": "x"}}}, "module"),
    ({"hard_cores": {"u_nobody": {"orient": "MX"}}}, "not a hard_cores instance"),
    ({"hard_cores": {"u_hc": {"orient": "R90"}}}, "orient"),
    ({"hard_cores": {"u_hc": {"origin_um": [900.0, 900.0]}}}, "leaves the type outline"),
    ({"internal_stations": {"0": {"regs_um": [[1.0, 1.0]]}}}, "no such station"),
    ({"base_plan_sha256": "00"}, "another bound plan"),
])
def test_non_positional_delta_rejected(plan, bad, match):
    with pytest.raises(TO.OverlayError, match=match):
        TO.apply_validated(plan, {**OV, **bad} if "hard_cores" not in bad else {**OV, "hard_cores": bad["hard_cores"]})


def test_station_count_and_keys_rejected(plan):
    plan["partition_types"]["mid"]["internal_stations"] = [dict(conn="bus:x", from_um=[10.0, 10.0], to_um=[100.0, 10.0],
                                                                regs_um=[[40.0, 10.0], [70.0, 10.0]])]
    for e, match in (({"regs_um": [[40.0, 10.0]]}, "shape"), ({"to_um": [1.0, 1.0]}, "rejected"),
                     ({"conn": "bus:y", "regs_um": [[1.0, 1.0], [2.0, 2.0]]}, "conn")):
        with pytest.raises(TO.OverlayError, match=match):
            TO.apply_overlay(plan, {"format": TO.FORMAT, "type": "mid", "internal_stations": {"0": e}})
    new = TO.apply_overlay(plan, {"format": TO.FORMAT, "type": "mid",
                                  "internal_stations": {"0": {"regs_um": [[50.0, 12.0], [80.0, 12.0]]}}})
    assert new["partition_types"]["mid"]["internal_stations"][0]["regs_um"] == [[50.0, 12.0], [80.0, 12.0]]


def test_diff_of_plans_roundtrips_and_rejects_ports_outline_lanes_latency(plan):
    new = TO.apply_overlay(plan, OV)
    ov = TO.overlay_from_plans(plan, new, "mid")
    assert ov["hard_cores"] == {"u_hc": {"origin_um": B, "orient": "MX"}} and TO.apply_overlay(plan, ov) == new
    for edit, match in ((lambda r: r["ports"][0].update(width=r["ports"][0]["width"] + 1), "ports"),
                        (lambda r: r["lanes"][0].update(ports=r["lanes"][0]["ports"][:-1]), "lanes"),
                        (lambda r: r["partition_types"]["mid"].update(outline_um=[800.0, 800.0]), "outline"),
                        (lambda r: r["latency"].update(x=1), "latency"),
                        (lambda r: r["partition_types"]["sink"]["contents"][0].update(origin_um=[1.0, 1.0]), "contents"),
                        (lambda r: r["partition_types"]["mid"]["hard_cores"][0].update(outline_um=[30.0, 10.0]), "hard_cores")):
        bad = copy.deepcopy(new)
        edit(bad)
        with pytest.raises(TO.OverlayError, match=match):
            TO.overlay_from_plans(plan, bad, "mid")


def test_validation_is_scoped_to_the_type(plan, tmp_path):
    """A broken OTHER type neither stops this type's overlay nor its kit; a broken SELECTED type does."""
    plan["partition_types"]["sink"]["contents"].append(copy.deepcopy(plan["partition_types"]["sink"]["contents"][0]))
    assert any("sink" in e for e in S.validate(plan))
    b = kit(plan, tmp_path / "ok", type_overlay=OV)
    assert "mid/macro_place.tcl" in b
    bad = copy.deepcopy(plan)
    bad["partition_types"]["mid"]["contents"].append(copy.deepcopy(bad["partition_types"]["mid"]["contents"][0]))
    with pytest.raises(GR.GenError, match="duplicate content"):
        GP.write_phys(bad, tmp_path / "bad", trial=True, skip_ir=True, rc_cal=False, types=["mid"], type_overlay=OV)


def test_rtl_projection_change_rejected(plan, monkeypatch):
    calls = []
    monkeypatch.setattr(TO, "rtl_projection", lambda raw, tn: (calls.append(1), {"reset_gate_taps": {"u_hc": "t%d" % len(calls)}})[1])
    with pytest.raises(TO.OverlayError, match="RTL inputs change"):
        TO.apply_validated(plan, OV)


def test_collector_reach_and_seam_hop_on_the_type(plan, monkeypatch):
    import collector_reach as CR
    monkeypatch.setattr(CR, "type_findings", lambda tn, t, reach=CR.REACH_UM: [dict(
        type=tn, kind="edge", src="rst_n_t3", dst="rst_n_t1", hop_um=410.0)])
    with pytest.raises(TO.OverlayError, match="collector_reach"):
        TO.apply_validated(plan, OV)
    monkeypatch.undo()
    base_rows = TO.seam_rows(plan, "mid")
    worse = {k: dict(r, over=True, hop_um=r["hop_um"] + 500) for k, r in base_rows.items()}
    calls = []
    monkeypatch.setattr(TO, "seam_rows", lambda raw, tn: base_rows if not calls.append(1) and len(calls) == 1 else worse)
    if base_rows:
        with pytest.raises(TO.OverlayError, match="seam_hop"):
            TO.apply_validated(plan, OV)


def test_scope_errors_typed_drops_other_types_rows_the_old_scope_kept(plan):
    parts = {p["name"]: p["type"] for p in plan["partitions"]}
    pn_sink = next(n for n, t in parts.items() if t == "sink")
    pn_mid = next(n for n, t in parts.items() if t == "mid")
    errs = ["partition type sink: id_strap x declared twice", "type sink slot s0: bad", "type sink: y",
            f"partition {pn_sink}: id_straps [] != type", f"partition {pn_mid}: id_straps [] != type",
            "partition type mid: z", "$.partition_types.sink.outline_um: bad", "die channel c: needs rect_um"]
    assert S.scope_errors(errs, ["mid"]) == [e for e in errs if e != "type sink: y"]
    assert S.scope_errors_typed(errs, ["mid"], plan) == [errs[4], errs[5], errs[7]]
    assert S.scope_errors_typed(errs, None, plan) == errs
