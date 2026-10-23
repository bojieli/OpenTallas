"""tests for tools/die_plan/bind.py (BINDER2 10-23): python3 -m pytest tools/die_plan/test_bind.py

Runs the binder end to end (Yosys elab -> bind -> Yosys re-elab + connectivity proof + Verilator lint) on the
examples/bind_tiny die: a GEN-style die top with relays, a reset repeater, a fault OR, clock/reset sources, a dissolved
structural parent and a declared strap.  Needs Yosys ($OT_BIND_YOSYS or the ORFS docker image); skipped otherwise.
"""
import copy
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
pytestmark = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


def run(plan, out, *cmds):
    for c in cmds:
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        if rc:
            return rc
    return 0


def plan_copy(tmp_path, name, edit):
    """the example plan with `edit(plan)` applied, written next to the example sources (asbuilt.base made absolute)"""
    p = json.loads((EX / name).read_text())
    edit(p)
    p["asbuilt"]["base"] = str(EX)
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def report(out):
    return json.loads((Path(out) / "bind_report.json").read_text())


def verify(out):
    return json.loads((Path(out) / "verify_report.json").read_text())


@pytest.mark.parametrize("name", ["die_plan.json", "die_plan_lanes.json"])
def test_tiny_binds_and_proves(tmp_path, name):
    out = tmp_path / "o"
    assert run(EX / name, out, "elab", "bind", "verify") == 0
    r, v = report(out), verify(out)
    assert r["proof"] == dict(unbound=0, tied=0, undriven=0, multiply_bound=0, straps=8)
    assert r["n_errors"] == 0
    assert v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0 and v["counts"]["matched"] == 64
    if v["lint"].get("ran"):
        assert v["lint"]["errors"] == 0
    # leaves unchanged: the generated partitions instantiate the original masters with the as-built parameters
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    assert "lf_a #(.ID(P_u_a_ID))" in ta and "lf_b u_u_b" in ta
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert re.search(r"bt_ta #\(.*\.P_u_a_ID\(1\)", top) and re.search(r"bt_ta #\(.*\.P_u_a_ID\(2\)", top)
    # no constant reaches a leaf except through a declared strap parameter
    for f in (out / "rtl").glob("bt_*.sv"):
        body = f.read_text().split(");", 1)[1]
        assert not re.search(r"\.\w+\(\s*\d+'[bdh]", body), f


def test_lanes_ft_station_and_latency(tmp_path):
    out = tmp_path / "o"
    assert run(EX / "die_plan_lanes.json", out, "elab", "bind") == 0
    r = report(out)
    assert r["lanes"]["carrying"] == 6 and r["lanes"]["unplanned_bits"] == 0 and r["lanes"]["ft_hops"] == 1
    ft = (out / "rtl" / "bt_tf.sv").read_text()
    assert "input  wire [8:0] y_i" in ft and "output wire [8:0] y_o" in ft and ft.count("ot_dp_st #(.W(8))") == 1
    lat = {b["lane"]: b for b in json.loads((out / "bind_latency.json").read_text())["buses"]}
    assert lat["a0y"]["bound_stages"] == 3 == lat["a0y"]["plan_cycles"]
    assert lat["a0y"]["asbuilt_stages"] == [2, 2]          # two as-built relays removed, recorded
    assert lat["a1y"]["bound_stages"] == 2 and lat["a1y"]["asbuilt_stages"] == [1, 1]
    # plan bus names are the partition port names
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    for port in ("y_o", "ys_o", "f_o", "x_i"):
        assert re.search(rf"\b{port}\b", ta)


def test_forwarded_lane_chain(tmp_path):
    """no direct A0 -> S lane: the bits ride A0 -> A1 (via F) -> S, forwarded inside A1"""
    def edit(p):
        p["ports"] = [x for x in p["ports"] if x["id"] != "a0s__0"]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "a0s"]
        for x in p["ports"]:
            if x["id"] == "a1s__0":
                x["width"] = 16
        for b in p["partition_types"]["ta"]["buses"]:
            if b["name"] == "ys_o":
                b["width"] = 16
        for b in p["partition_types"]["ts"]["buses"]:
            if b["name"] == "d1_i":
                b["width"] = 16
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0
    r = report(out)
    assert r["lanes"]["forwarded_bits"] == 8 and r["lanes"]["unplanned_bits"] == 0
    assert r["lanes"]["forwarded_pairs"] == {"A0->S": 8}
    v = verify(out)
    assert v["verdict"] == "PASS", v["mismatches"][:3]
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert sinks["snk.d0[0]"][2] == 3 + 2                   # A0->A1 lane (3 cycles) + A1->S lane (2)


def test_unplanned_bits_are_reported(tmp_path):
    def edit(p):
        for x in p["ports"]:
            if x["id"] == "a0s__0":
                x["width"] = 5
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind")
    r = report(out)
    # 3 bits of A0 -> S have no lane room (A0 -> A1 -> S forwarding has no room either: a1s is full)
    assert r["lanes"]["unplanned_bits"] == 3 and r["proof"]["unbound"] == 3
    assert any(e.startswith("UNPLANNED A0 -> S: 3") for e in r["errors"])


def test_constant_is_reported_never_tied(tmp_path):
    """drop the strap declaration: the as-built 4'd5 / 4'd6 on u_b.id is TIED in the as-built; the binder reports it and
    leaves the leaf input an undriven wire (never a generated constant), so the proof fails"""
    def edit(p):
        p["asbuilt"]["straps"] = []
    out = tmp_path / "o"
    rc = run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify")
    r = report(out)
    assert r["proof"]["tied"] == 8 and r["proof"]["straps"] == 0
    assert any(e.startswith("TIED p0.u_b.id[0] = 1") for e in r["errors"])
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    assert "UNBOUND tied: p0.u_b.id[0]" in ta and "4'b" not in ta.split(");", 1)[1]
    assert rc != 0 and verify(out)["verdict"] == "FAIL"


def test_unmapped_and_unknown_are_errors(tmp_path):
    def edit(p):
        p["asbuilt"]["map"]["parts"].pop("snk")
        p["asbuilt"]["transport"] = [t for t in p["asbuilt"]["transport"] if t["module"] != "trep"]
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind")
    r = report(out)
    assert r["unmapped"] == 1
    assert any(e.startswith("UNMAPPED snk") for e in r["errors"])
    assert any(e.startswith("UNKNOWN_MODULE rst_rep0 (trep)") for e in r["errors"])


def test_substitute_inst_variant(tmp_path):
    """p1.u_b takes the plan variant lf_b_nid (no id port): its 4 strap bits disappear (recorded, not tied), A1 binds
    as a variant of type ta, and the proof still passes"""
    def edit(p):
        p["asbuilt"]["substitute_inst"] = [{"inst": r"p1\.u_b", "module": "lf_b_nid", "reason": "test chain head"}]
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0
    r = report(out)
    assert r["variants"]["instances"] == 1 and r["variants"]["removed_input_bits"] == {"lf_b_nid.id": 4}
    assert r["proof"]["tied"] == 0 and r["proof"]["straps"] == 4 and r["n_errors"] == 0
    assert any(t["type"] == "ta" for t in r["type_splits"])
    assert verify(out)["verdict"] == "PASS"
    assert "lf_b_nid u_u_b" in "".join(f.read_text() for f in (out / "rtl").glob("bt_ta*.sv"))


def test_lint_split(tmp_path):
    """asbuilt.lint_split: top against leaf interface stubs + one run per partition module with its own leaf closure"""
    def edit(p):
        p["asbuilt"]["lint_split"] = True
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0
    lt = verify(out)["lint"]
    if lt.get("ran"):
        assert lt["split"] and lt["errors"] == 0 and lt["runs"] >= 3
