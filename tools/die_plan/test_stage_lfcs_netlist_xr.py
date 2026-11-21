"""LF-CS stage with S81 strip form B (VP_XR): the plan HI depth of an XR leaf is effective (it includes XR's per-lane HI
stage), so the source gets plan HI - 1; the die netlist's LF_VP_XR mask and the --vp-xr contracts must agree."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_lfcs_netlist as SN  # noqa: E402
from test_stage_lfcs_netlist import PLAN, NET, _rtl, _st  # noqa: E402

T8 = "ot_s81sl_leaf__t8"


def plan_hi3():
    """t8 (s_0N leaf 1) with an effective hi chain of 3: the XR stage priced in the plan."""
    p = copy.deepcopy(PLAN)
    st = p["partition_types"][T8]["internal_stations"]
    st[2] = _st("core:u_lf.u_vn.u_a.hq_d", "u_lf.u_vp.g_ln[3].u_l", 3)
    return p


NET_XR = NET.replace("#(.HBC_ENABLE(0)) u_s_0N", "#(.LF_VP_XR(5'b00010), .HBC_ENABLE(0)) u_s_0N")


def hi_line(out):
    return next(ln for ln in out.splitlines() if "u_s_0N" in ln)


def test_xr_leaf_plan_hi3_stages_source_2_gs_2(tmp_path):
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {"HI_D": "20'h22222", "HI_GS": "20'h22222"})
    out, rep = SN.stage(plan_hi3(), NET_XR, rtl, vp_xr={T8: 1})
    line = hi_line(out)
    # leaf 1 = source 2 (effective 3 with XR), GS 2; leaf 3 (t9, no hi) 0; leaves 0, 2, 4 module default 2
    assert ".LF_CS_HI_D(20'h20222)" in line and ".LF_CS_HI_GS(20'h20222)" in line
    assert line.startswith("    ot_s81sl_slice_x #(.LF_VP_XR(5'b00010), .HBC_ENABLE(0), .LF_CS_HI_D(")
    r = next(r for r in rep if r.get("type") == T8)
    assert r["vp_xr"] == 1 and r["plan_hi_d"] == 3 and r["depths"]["HI_D"] == 2 and r["depths"]["HI_GS"] == 2


def test_old_path_on_an_xr_netlist_refuses_the_fourth_stage(tmp_path):
    """mutant: the unchanged helper would write source HI 3 under XR (effective 4); a mask bit without contract stops."""
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {})
    with pytest.raises(SystemExit, match=r"mask bit 1 differs from the VP_XR contract 0"):
        SN.stage(plan_hi3(), NET_XR, rtl)
    with pytest.raises(SystemExit, match=r"mask bit 0 differs from the VP_XR contract 1"):
        SN.stage(plan_hi3(), NET, rtl, vp_xr={T8: 1})          # contract but no mask on the die instance


def test_xr0_and_no_contract_are_byte_identical_to_the_old_path(tmp_path):
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {"HI_D": "20'h22222", "HI_GS": "20'h22222"})
    base, _ = SN.stage(PLAN, NET, rtl)
    assert SN.stage(PLAN, NET, rtl, vp_xr={T8: 0})[0] == base
    assert SN.stage(PLAN, NET.replace("#(.HBC_ENABLE(0))", "#(.LF_VP_XR(5'b00000), .HBC_ENABLE(0))"), rtl)[0] == \
        base.replace("#(.HBC_ENABLE(0)", "#(.LF_VP_XR(5'b00000), .HBC_ENABLE(0)")


def test_xr_refusals(tmp_path):
    with pytest.raises(SystemExit, match="effective HI depth must include the XR stage"):
        p = copy.deepcopy(PLAN)
        p["partition_types"][T8]["internal_stations"].pop(2)          # no hi rows: XR stage not priced
        SN.leaf_depths(p, vp_xr={T8: 1})
    p = copy.deepcopy(PLAN)
    p["partition_types"][T8]["hard_cores"] = []
    with pytest.raises(SystemExit, match="no hard cores"):
        SN.leaf_depths(p, vp_xr={T8: 1})
    p = copy.deepcopy(PLAN)
    p["partition_types"]["ot_s81sl_kv_leaf__t3"] = copy.deepcopy(p["partition_types"][T8])
    p["partitions"].append(dict(name="s_2N_L0", type="ot_s81sl_kv_leaf__t3"))
    d, _ = SN.leaf_depths(p, vp_xr={"ot_s81sl_kv_leaf__t3": 1})     # a kv leaf with hard cores is an XR leaf like any other
    assert d[("2N", 0)]["HI_D"] == 1 and d[("2N", 0)]["HI_GS"] == 0
    with pytest.raises(SystemExit, match="unknown leaf"):
        SN.leaf_depths(PLAN, vp_xr={"ot_s81sl_leaf__t99": 1})
    with pytest.raises(SystemExit, match="integer 0 or 1"):
        SN.leaf_depths(PLAN, vp_xr={T8: 2})
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {})
    with pytest.raises(SystemExit, match="literal five-bit mask"):
        SN.stage(plan_hi3(), NET.replace("#(.HBC_ENABLE(0))", "#(.LF_VP_XR(MASK))"), rtl, vp_xr={T8: 1})


def test_cli_contract(tmp_path):
    import json
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {})
    (tmp_path / "plan.json").write_text(json.dumps(plan_hi3()))
    (tmp_path / "net.v").write_text(NET_XR)
    assert SN.main([str(tmp_path / "plan.json"), str(tmp_path / "net.v"), str(tmp_path / "out.v"), "--rtl", str(rtl),
                    "--vp-xr", f"{T8}:1"]) == 0
    assert ".LF_CS_HI_D(20'h00020)" in (tmp_path / "out.v").read_text()
    with pytest.raises(SystemExit):
        SN.main([str(tmp_path / "plan.json"), str(tmp_path / "net.v"), str(tmp_path / "o2.v"), "--rtl", str(rtl),
                 "--vp-xr", f"{T8}:1", "--vp-xr", f"{T8}:1"])


KV = ["ot_s81sl_kv_leaf__t2", "ot_s81sl_kv_leaf__t3", "ot_s81sl_kv_leaf__t1", "ot_s81sl_kv_leaf__t4", "ot_s81sl_kv_leaf__t5"]
KV_DFT = {"HI_D": "20'h11110", "HO_D": "20'h11110", "H_G": "20'h44444", "SW_D": "20'h11110", "SWR_D": "20'h11010"}
KV_BARE = "  ot_s81sl_slice_sukv_raw512_w3 #(.LF_VP_XR(5'b11111)) u_s_3N (.clk(ck), .fault(f));\n"


def plan_kv():
    """The kv slice of the S81 record: L0 = kv_leaf t2 (KV bank, no hard cores), L1-L4 kv leaves, plan hi 2 (XR priced), sw 1."""
    typ = dict(hard_cores=[1], internal_stations=[_st("core:u_lf.u_vn.u_a.hq_d", "u_lf.u_vp.g_ln[3].u_l", 2),
                                                  _st("core:u_lf.u_vs.sw_d", "u_lf.u_vsw.i_d", 1)])
    p = dict(partition_types={}, partitions=[])
    for k, t in enumerate(KV):
        p["partitions"].append(dict(name=f"s_3N_L{k}", type=t))
        p["partition_types"][t] = copy.deepcopy(typ) if k else dict(hard_cores=[], internal_stations=[])
    return p


def test_kv_slice_restage_reproduces_the_record(tmp_path):
    """S81-LEAF-REGRID 11-21: the tool refused every full restage of the S81 die on u_s_3N (kv leaves under a 11111
    mask, with and without contracts); skipping the mask check priced HI_D 22220 (elaborates plan HI + 1).  The netlist
    of record (die_b178_lfcs.v, J6 base 44be6051) has u_s_3N HI_D 20'h11110, HI_GS 20'h00000."""
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_sukv_raw512_w3", KV_DFT)
    p = plan_kv()
    xr = {t: 1 for t in KV[1:]}
    out, rep = SN.stage(p, KV_BARE, rtl, vp_xr=xr)
    assert out.startswith("  ot_s81sl_slice_sukv_raw512_w3 #(.LF_VP_XR(5'b11111), .LF_CS_HI_D(20'h11110), "
                          ".LF_CS_HI_GS(20'h00000), .LF_CS_HO_D(20'h00000), .LF_CS_HO_GS(20'h00000), .LF_CS_H_G(20'h44444), ")
    assert ".LF_CS_SW_D(20'h11110)" in out and out.endswith(") u_s_3N (.clk(ck), .fault(f));\n")
    assert [r.get("skipped", r.get("vp_xr")) for r in rep] == ["no hard cores (no leaf chains)", 1, 1, 1, 1]
    # mutants: no contract on a kv leaf refuses (it would stage 22220); a contract on the bank leaf refuses
    with pytest.raises(SystemExit, match=r"leaf 1: LF_VP_XR mask bit 1 differs from the VP_XR contract 0"):
        SN.stage(p, KV_BARE, rtl, vp_xr={t: 1 for t in KV[2:]})
    with pytest.raises(SystemExit, match="no hard cores"):
        SN.stage(p, KV_BARE, rtl, vp_xr=dict(xr, **{KV[0]: 1}))
    # the bank leaf's mask bit is not priced either way; a kv leaf with mask bit 0 is staged at the plan depth
    assert SN.stage(p, KV_BARE.replace("11111", "11110"), rtl, vp_xr=xr)[0] == out.replace("11111", "11110", 1)
    out0, _ = SN.stage(p, KV_BARE.replace("11111", "11101"), rtl, vp_xr={t: 1 for t in KV[2:]})
    assert ".LF_CS_HI_D(20'h11120)" in out0


def test_sr_contract_prices_the_output_station(tmp_path):
    """S81 J7 vp_sr: plan ho depth includes the SR output station (u_cst_ho D = CS_HO_D - CS_HO_GS + SRO), so source
    HO_D = plan ho - 1; without the contract the restage of the J7 plan wrote ho + 1 on every leaf (elaborates plan + 1)."""
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {"HO_D": "20'h22222", "HO_GS": "20'h22222"})
    p = copy.deepcopy(PLAN)
    lane = "u_lf.u_vp.g_ln[3].u_l"
    p["partition_types"][T8]["internal_stations"].append(_st("core:u_lf.u_vn.u_a.hw_d", lane, 3))      # ho row
    old, _ = SN.stage(p, NET, rtl)
    assert ".LF_CS_HO_D(20'h20232)" in hi_line(old) and ".LF_CS_HO_GS(20'h20232)" in hi_line(old)
    out, rep = SN.stage(p, NET, rtl, vp_sr={T8: 1})
    assert ".LF_CS_HO_D(20'h20222)" in hi_line(out) and ".LF_CS_HO_GS(20'h20222)" in hi_line(out)
    assert out.replace("20'h20222", "20'h20232") == old.replace("20'h20222", "20'h20232")       # nothing else moves
    r = next(r for r in rep if r.get("type") == T8)
    assert r["vp_sr"] == 1 and r["plan_ho_d"] == 3 and r["depths"]["HO_D"] == 2
    gs0, _ = SN.stage(p, NET, rtl, {T8: {"HO_GS": 0}}, None, {T8: 1})
    assert ".LF_CS_HO_D(20'h20222)" in hi_line(gs0) and ".LF_CS_HO_GS(20'h20202)" in hi_line(gs0)
    with pytest.raises(SystemExit, match="must include the SR output station"):
        q = copy.deepcopy(PLAN)
        SN.leaf_depths(q, vp_sr={T8: 1})                              # no ho rows: SR station not priced
    with pytest.raises(SystemExit, match="integer 0 or 1"):
        SN.leaf_depths(p, vp_sr={T8: 2})
