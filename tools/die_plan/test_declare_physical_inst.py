"""DIE-HBM-90-TNAME 11-07, class (i): HBM root kit_rtl stopped on "core clock clk_c12: expected one bound leaf
u_mu_fused_program, got 0"; the as-built RTL and the bind map name the instance u_mu_fused_programme.  The plan event
tool declare_physical_inst.py declares that bound leaf as the core's physical identity and fails closed otherwise; with
it, bind kit-rtl wires the planned core clock on the bound leaf."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import declare_physical_inst as D  # noqa: E402
import kit_core_clocks as K  # noqa: E402

OLD, NEW, MOD = "u_mu_fused_program", "u_mu_fused_programme", "ot_hnx_fused_host_program"
RTL = """module hbm_arch_root (
    input wire clk,
    input wire d
);
    // as-built u_mu_fused_programme
    ot_hnx_fused_host_program #(.DELIVERED_RESET(1)) u_u_mu_fused_programme (
        .clk(clk),
        .cfg_v(d)
    );
    ot_hnx_fused_hub_n4ext u_u_mu_fused_root (
        .clk(clk)
    );
endmodule
"""


def plan():
    return {"partition_types": {"root": {
        "module": "hbm_arch_root",
        "contents": [{"inst": OLD, "module": MOD, "cells": 2154}],
        "hard_cores": [{"inst": "u_mu_fused_root", "module": "ot_hnx_fused_hub_n4ext"},
                       {"inst": OLD, "module": MOD, "origin_um": [734.4, 5339.52]}],
        "clock": {"taps": [{"name": OLD + ".clk", "kind": "core", "xy": [838.08, 5468.88]}]}}}}


@pytest.fixture
def rtl(tmp_path):
    (tmp_path / "hbm_arch_root.sv").write_text(RTL)
    return tmp_path


def test_declares_the_bound_leaf_and_keeps_everything_else(rtl):
    before = plan()
    raw, led = D.apply(plan(), "root", OLD, NEW, rtl)
    t = raw["partition_types"]["root"]
    assert t["hard_cores"][1] == dict(before["partition_types"]["root"]["hard_cores"][1],
                                      physical_inst=NEW, physical_master=MOD)
    for k in ("contents", "clock", "module"):
        assert t[k] == before["partition_types"]["root"][k]
    assert t["hard_cores"][0] == before["partition_types"]["root"]["hard_cores"][0]
    assert led["bound_leaf_master"] == MOD and len(led["plan_fields"]) == 2


def test_with_the_declaration_kit_rtl_wires_the_bound_leaf(rtl):
    raw, _ = D.apply(plan(), "root", OLD, NEW, rtl)
    phys = {c["inst"]: c["physical_inst"] for c in raw["partition_types"]["root"]["hard_cores"] if c.get("physical_inst")}
    row = ("clk_c12", phys.get(OLD, OLD), "clk", 0, 250)
    text, receipt = K.wire(RTL, "hbm_arch_root", [row])
    assert ".clk(clk_c12)" in text and receipt[0]["instance"] == "u_u_mu_fused_programme"
    with pytest.raises(ValueError, match="expected one bound leaf u_mu_fused_program, got 0"):
        K.wire(RTL, "hbm_arch_root", [("clk_c12", OLD, "clk", 0, 250)])


def test_no_bound_leaf_of_the_new_name_fails_closed(rtl):
    (rtl / "hbm_arch_root.sv").write_text(RTL.replace("u_u_mu_fused_programme", "u_u_mu_fused_progx"))
    with pytest.raises(SystemExit, match="has 0 leaf"):
        D.apply(plan(), "root", OLD, NEW, rtl)


def test_old_name_still_bound_fails_closed(rtl):
    (rtl / "hbm_arch_root.sv").write_text(RTL.replace("endmodule", "    x u_u_mu_fused_program (.clk(clk));\nendmodule"))
    with pytest.raises(SystemExit, match="still has a leaf"):
        D.apply(plan(), "root", OLD, NEW, rtl)


def test_other_master_fails_closed(rtl):
    (rtl / "hbm_arch_root.sv").write_text(RTL.replace("ot_hnx_fused_host_program #", "ot_other #"))
    with pytest.raises(SystemExit, match="the plan core is"):
        D.apply(plan(), "root", OLD, NEW, rtl)


def test_existing_physical_identity_fails_closed(rtl):
    p = plan()
    p["partition_types"]["root"]["hard_cores"][1].update(physical_inst="x", physical_master=MOD)
    with pytest.raises(SystemExit, match="already declares"):
        D.apply(p, "root", OLD, NEW, rtl)


def test_cli_roundtrip(rtl, tmp_path):
    src = tmp_path / "in.json"
    src.write_text(json.dumps(plan()))
    out, led = tmp_path / "out.json", tmp_path / "led.json"
    assert D.main([str(src), str(out), str(led), "--type", "root", "--old", OLD, "--new", NEW,
                   "--bound-rtl", str(rtl)]) == 0
    assert json.loads(out.read_text())["partition_types"]["root"]["hard_cores"][1]["physical_inst"] == NEW
