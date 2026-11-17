"""QC-CBGLUE-1116: qc_raw_branches_gen.py / qc_raw_branches_delta.py (FSTART literal raw-reset branches)."""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qc_raw_branches_delta as delta  # noqa: E402
import qc_raw_branches_gen as gen  # noqa: E402
from landing_raw_branches import RawBranches  # noqa: E402

# cbf_q01 form: tap relay chain from the S-edge pad, ring relay at the E landing a00_i, FSTART flops on the S face
BODY = """module t__cbx_coreclk (input wire clk, input wire arst_n);
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_root_n), .q(rst_rl_1));  // raw pad tap None depth 1 @ (100.0, 10.0)
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw wire tap None depth 2 @ (500.0, 10.0)
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw wire tap None depth 3 @ (500.0, 400.0)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));  // raw wire tap None depth 4 @ (900.0, 900.0)
"""
RING = "    ot_dp_rrelay u_cland_rst_a00_i (.clk(clk), .d(rst_rl_4), .q(cland_reset_a00_i));"
TAIL = """    wire cland_start_d, cland_start_raw;
    ot_dp_landing_relay u_cland_fstart_a00_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(o0));
    ot_dp_landing_relay u_cland_fstart_n_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(o1));
    assign cland_start_raw = cland_reset_a00_i;
endmodule
"""
PINS = [dict(name="fclk_in_a00_i", xy_um=[1200.0, 1000.0], dir="in", kind="clock"),
        dict(name="cland_fstart_out_a00_o", xy_um=[150.0, 2.0], dir="out", kind="ctl"),
        dict(name="cland_fstart_out_n_o", xy_um=[1100.0, 1100.0], dir="out", kind="ctl"),
        dict(name="cland_fstart_out_nf_o", xy_um=[10.0, 10.0], dir="out", kind="ctl")]   # no face flop: no role


def plan():
    return {"schema": "x", "partition_types": {
        "cbx": {"outline_um": [1210.0, 1200.0], "clock": {"landing_contract": {"pins": PINS}}},
        "other": {"outline_um": [10, 10]}}}


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t__cbx_coreclk.sv").write_text(BODY + RING + "\n" + TAIL)
    (tmp_path / "rtl" / "t__cbx_other.sv").write_text("module x; endmodule\n")
    (tmp_path / "plan.json").write_text(json.dumps(plan()))
    return tmp_path


def test_gen_branches_hops_and_literal_validation(setup):
    out = setup / "rb.json"
    assert gen.main([str(setup / "plan.json"), str(setup / "rtl"), str(out), "--types", "cbx"]) == 0
    r = json.load(open(out))["cbx"]
    assert r["raw"] == "cland_reset_a00_i" and r["raw_xy"] == [1200.0, 1000.0]
    assert r["chain"] == ["rst_root_n", "rst_rl_1", "rst_rl_2", "rst_rl_3", "rst_rl_4", "cland_reset_a00_i"]
    # near consumer (200 um) keeps the shared raw; the far S-face one gets a branch with every hop <= 330 um
    assert r["report"]["fstart:n_o"]["branch"] is None
    assert [b["consumers"] for b in r["branches"]] == [["fstart:a00_o"]]
    assert "fstart:nf_o" not in r["report"]
    assert r["report"]["fstart:a00_o"]["max_hop_um"] <= 330.0
    b = r["branches"][0]
    assert b["base"] == "rst_rl_3" and [s["original"] for s in b["stages"]] == ["rst_rl_4", "cland_reset_a00_i"]
    # the FE3 emitter's own checker accepts it: base in the original body, ring relay as registered baseline
    g = RawBranches("cbx", r["branches"], BODY + TAIL, [1210.0, 1200.0])
    g.baseline_relay(RING)
    net = g.raw_for("fstart:a00_o", "cland_start_raw")
    text = BODY + RING + "\n" + TAIL + "\n".join(g.rtl)
    v = g.validate(text)
    assert v["flops"] == 2 and v["consumers"]["fstart:a00_o"]["net"] == net


def test_gen_needs_one_bound_file(setup):
    p = plan()
    p["partition_types"]["nosuch"] = p["partition_types"]["cbx"]
    with pytest.raises(gen.GenError):
        gen.gen_type(p, str(setup / "rtl"), "nosuch", 330.0, 300.0)
    with pytest.raises(gen.GenError):
        gen.gen_type(plan(), str(setup / "rtl"), "absent", 330.0, 300.0)


def test_delta_one_line_plan_only_target_changes(setup):
    rb = {"cbx": {"branches": [{"name": "fs_a", "base": "b", "stages": [], "consumers": ["fstart:a"]}]},
          "other": {"branches": []}}
    text = json.dumps(plan()) + "\n"
    new, done = delta.apply(text, rb)
    assert list(done) == ["cbx"] and new.endswith("\n") and "\n" not in new.rstrip("\n")
    p = json.loads(new)
    assert p["partition_types"]["cbx"]["clock"]["landing_raw_branches"] == rb["cbx"]["branches"]
    assert p["partition_types"]["other"] == plan()["partition_types"]["other"]
    with pytest.raises(ValueError):
        delta.apply(new, rb)
    assert json.loads(delta.apply(new, rb, replace=True)[0]) == p


def test_delta_indented_plan_splices(setup):
    text = json.dumps(plan(), indent=1)
    rb = {"cbx": {"branches": [{"name": "fs_a", "base": "b", "stages": [], "consumers": ["fstart:a"]}]}}
    new, _ = delta.apply(text, rb)
    assert json.loads(new)["partition_types"]["cbx"]["clock"]["landing_raw_branches"]
    assert re.search(r'^  "other": ', new, re.M)
