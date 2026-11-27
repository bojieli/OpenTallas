"""SEAM-PAD-R3: per-pin seam pad sizing from measured parent arrivals (class C-PARENT-SEAM-HOLD)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_hold_pad as F
import seam_pad_per_pin as S

CHILD = "a[0]\tu/d0/D\t-43.0\t620.0\na[1]\tu/d1/D\t-47.0\t610.0\nrst_n[0]\tu/rn/RESETN\t-54.6\t649.0\nfi[0]\tu/fil/D\t-47.8\t627.0\n"


def test_contract_only_sizes_every_negative_pin():
    spec, audit = S.size(S.read_child(CHILD))
    assert audit["pins"] == 4 and audit["padded"] == 4
    assert spec["per_endpoint"] == {"a[0]": 2, "a[1]": 2, "rst_n[0]": 2, "fi[0]": 2}
    assert spec["by"] == "port" and spec["schema"] == F.SCHEMA
    assert not audit["refused"]


def test_measured_parent_replaces_contract():
    ff = "B\ta[0]\tp\ts\te\t73.5\t400\nB\ta[1]\tp\ts\te\t40.0\t400\nA\ta[0]\tp\ts\te\t500\t400\n"
    spec, audit = S.size(S.read_child(CHILD), S.read_parent(ff, "B"), S.read_parent(ff, "A"))
    assert spec["per_endpoint"] == {"rst_n[0]": 2, "fi[0]": 2}          # a[*] covered by the measured parent
    assert audit["by_basis"]["measured_parent"] == dict(pins=2, padded=0, cells=0)
    assert audit["by_basis"]["contract"]["padded"] == 2


def test_extra_ff_reset_measurement_and_guard():
    spec, audit = S.size(S.read_child(CHILD), {"a[0]": 73.5, "a[1]": 40.0}, None, extra_ff={"rst_n[0]": -0.911})
    assert spec["per_endpoint"]["rst_n[0]"] == 1                        # ceil((30 + 0.911) / 35) = 1
    assert "fi[0]" in spec["per_endpoint"]
    spec2, _ = S.size(S.read_child(CHILD), {"a[0]": 29.0}, None)        # below the measured guard (30) is padded, at it is not
    assert spec2["per_endpoint"]["a[0]"] == 1
    spec3, _ = S.size(S.read_child(CHILD), {"a[0]": 30.0}, None)
    assert "a[0]" not in spec3["per_endpoint"]


def test_tt_cost_refusal_and_n_max_are_never_silent():
    child = S.read_child("x[0]\tu/x/D\t-200.0\t900.0\ny[0]\tu/y/D\t-50.0\t100.0\n")
    spec, audit = S.size(child)
    assert spec["per_endpoint"] == {"x[0]": 6}                         # x: 390 ps TT cost of 900 slack; y: 130 ps of 100 -> refused
    assert {r["port"] for r in audit["refused"]} == {"y[0]"}
    spec, audit = S.size(child, tt_floor=-42.0)                        # the whole-core gate floor would accept y (-30)
    assert spec["per_endpoint"] == {"x[0]": 6, "y[0]": 2} and not audit["refused"]
    spec, audit = S.size(child, n_max=5, tt_floor=-42.0)
    reasons = {r["port"]: r["why"] for r in audit["refused"]}
    assert "needs 6 HB4 > n_max 5" in reasons["x[0]"]


def test_stage_installs_hook_once_and_validates():
    spec, _ = S.size(S.read_child(CHILD))
    with tempfile.TemporaryDirectory() as td:
        kd = Path(td)
        (kd / "hold_budget.tcl").write_text("# GENERATED\nsource /work/face_capture_release.tcl\n")
        r1 = S.stage(kd, spec)
        r2 = S.stage(kd, spec)                                         # idempotent
        assert r1["padded"] == r2["padded"] == 4 and r1["cells"] == 8
        t = (kd / "hold_budget.tcl").read_text()
        assert t.count("source /work/seam_pad_port.tcl") == 1 and t.startswith("# GENERATED\n")
        assert "{rst_n[0]} 2" in (kd / "seam_pad_port_n.tcl").read_text()
        assert (kd / "seam_pad_port.tcl").read_text() == S.HOOK_TCL.read_text()
        (kd / "hold_budget.tcl").unlink()
        try:
            S.stage(kd, spec)
        except SystemExit:
            pass
        else:
            raise AssertionError("stage must refuse a kit without hold_budget.tcl")
    bad = dict(spec, by="inst")
    try:
        S.tcl_dict(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("by=inst spec accepted")


def test_cli_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "c.tsv").write_text(CHILD)
        rc = S.main(["size", "--child", str(td / "c.tsv"), "--out", str(td / "s.json"), "--audit", str(td / "a.json"),
                     "--pad-tsv", str(td / "p.tsv")])
        assert rc == 0
        assert (td / "p.tsv").read_text().splitlines()[0].split("\t") == ["a[0]", "2"]
        assert json.loads((td / "a.json").read_text())["schema"] == S.SCHEMA


def test_hook_tcl_fails_closed_text():
    t = S.HOOK_TCL.read_text()
    assert "OT_SEAM_PAD_ALLOW_MISSING" in t and "shared net" in t and "HB4xp67_ASAP7_75t_R" in t
    # review fixes (Fable 11-27): dont_touch on pad cells and nets, input-only, idempotent
    assert t.count("setDoNotTouch 1") >= 2 and "is not an input" in t and "already applied" in t


def test_measured_guard_is_larger_and_tt_floor_default_zero():
    ff = {"a[0]": 23.0, "a[1]": 29.0, "a[2]": 31.0}
    child = S.read_child("a[0]\tu/d0/D\t-43.0\t620.0\na[1]\tu/d1/D\t-47.0\t610.0\na[2]\tu/d2/D\t-1.0\t600.0\n")
    spec, audit = S.size(child, ff, None)
    assert spec["per_endpoint"] == {"a[0]": 1, "a[1]": 1}              # +23 / +29 < 30 get a cell, +31 does not
    assert audit["rows"][0]["guard_ps"] == S.MEASURED_GUARD_PS and S.TT_FLOOR_PS == 0.0
    tight = S.read_child("x[0]\tu/x/D\t-50.0\t100.0\n")            # 2 cells = 130 ps > 100 ps of TT slack: refused at floor 0
    _, audit2 = S.size(tight)
    assert [r["port"] for r in audit2["refused"]] == ["x[0]"]

