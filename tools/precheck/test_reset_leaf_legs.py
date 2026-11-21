"""QC-PLAN-R9-LEAFLEG: reset_leaf_legs.py (advisory leaf relay -> reset consumer legs of a bound plan)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_leaf_legs as RLL  # noqa: E402

T = "cbx_t"


def bound_sv(station_net="rst_n"):
    return f"""module {T} (input clk, output rst_o_0);
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw wire tap None depth 1 @ (10.0, 10.0)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run wire tap None depth 1 @ (10.0, 10.0)
    wire rst_n_t0;
    ot_dp_rgate u_rrl_1 (.clk(clk), .d(rst_rl_0), .run(rn_rst_rl_0), .q(rst_n_t0));  // gated tap tap 0 depth 2 @ (10.0, 10.0)
    wire rst_n_t1;
    ot_dp_rgate u_rrl_2 (.clk(clk), .d(rst_rl_0), .run(rn_rst_rl_0), .q(rst_n_t1));  // gated tap tap 1 depth 2 @ (900.0, 900.0)
    wire rr_t2;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_0), .q(rr_t2));  // raw tap tap 2 depth 2 @ (990.0, 10.0)
    assign rst_o_0 = rr_t2;  // registered reset out
    wire rst_n = rst_n_t0;
    ot_dp_st #(.W(4)) u_bout_y_o0 (.clk(clk), .rst_n(rst_n_t1), .d(x), .ea(rst_n), .q(y_o0[3:0]), .eq(y_o0[4]));
    ot_dp_lk #(.W(1)) u_lk_c_rst_n (.clk(clk), .d(rst_n_t1), .q(lk_c_rst_n));
    qfd_c_xstn u_u_fab_u_x_0_0 (
        .ck(clk),
        .rst_n({station_net})
    );
    qfd_c_xstn u_u_fab_u_x_9_9 (.ck(clk), .rst_n(rst_n_t1));
endmodule
"""


def tree():
    rel = [dict(name="u_rrl_0", xy=[10.0, 10.0], d="rst_root_n", q="rst_rl_0", depth=1, tap=0, kind="wire"),
           dict(name="u_rrl_1", xy=[10.0, 10.0], d="rst_rl_0", q="rst_n_t0", depth=2, tap=0, kind="tap"),
           dict(name="u_rrl_2", xy=[900.0, 900.0], d="rst_rl_0", q="rst_n_t1", depth=2, tap=1, kind="tap"),
           dict(name="u_rrl_3", xy=[990.0, 10.0], d="rst_rl_0", q="rr_t2", depth=2, tap=2, kind="raw")]
    return dict(relays=rel, taps=["clk", "clk_t1", "o0"], n_clock_taps=2, n_reset_consumers=2, outs=[[1000.0, 10.0]],
                core_resets=[dict(inst="u_c", pin="rst_n", pin_um=[900.0, 1250.0], xy=[900.0, 1250.0], tap=1)])


def plan(inst_taps=None):
    r = {"consumer_sites_um": [["clk", 10.0, 10.0], ["clk_t1", 900.0, 900.0]]}
    if inst_taps is not None:
        r["inst_taps"] = inst_taps
    return {"partition_types": {T: {"module": T, "outline_um": [1000.0, 1300.0], "reset": r,
                                    "buses": [{"name": "y_o0", "dir": "out", "width": 4, "face": "N", "window_um": [880.0, 920.0]}]}}}


def make(tmp_path, station_net="rst_n", inst_taps=None):
    b = tmp_path / "bind"
    (b / "rtl").mkdir(parents=True)
    (b / "rtl" / f"{T}.sv").write_text(bound_sv(station_net))
    (b / "rtl" / f"{T}.reset_tree.json").write_text(json.dumps({"plan_type": T, "tree": tree()}))
    (b / "bind_reset.json").write_text(json.dumps({"types": {T: {"outs": [["rst_o_0", 1000.0, 10.0]]}}}))
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan(inst_taps)))
    pos = tmp_path / "pos.json"
    pos.write_text(json.dumps({T: {"u_u_fab_u_x_0_0": [[880.0, 880.0], [870.0, 860.0]]}}))
    return b, p, pos


def legs(rep, consumer):
    return [x for x in rep["types"][T]["legs"] if x["consumer"] == consumer]


def test_far_station_on_leaf_alias_is_over_and_inst_tap_fixes_it(tmp_path):
    b, p, pos = make(tmp_path)
    rep = RLL.run(b, p, positions=json.loads(pos.read_text()))
    r = rep["types"][T]
    (st,) = legs(rep, "u_u_fab_u_x_0_0.rst_n")
    assert st["relay"] == "u_rrl_1" and st["leg_um"] == 1740.0          # worst placed point (880, 880) from (10, 10)
    assert r["verdict"] == "OVER" and r["over"][0]["consumer"] == "u_u_fab_u_x_0_0.rst_n"
    # the station with no position is never PASS
    assert {u["consumer"] for u in r["unmeasured"]} == {"u_u_fab_u_x_9_9.rst_n"}
    b2, p2, pos2 = make(tmp_path / "fixed", "rst_n_t1", [{"tap": 1, "sinks": ["u_u_fab_u_x_0_0"]}])
    rep2 = RLL.run(b2, p2, positions=json.loads(pos2.read_text()))
    (st2,) = legs(rep2, "u_u_fab_u_x_0_0.rst_n")
    assert st2["relay"] == "u_rrl_2" and st2["leg_um"] == 70.0
    over2 = {x["consumer"] for x in rep2["types"][T]["over"]}
    assert "u_u_fab_u_x_0_0.rst_n" not in over2 and rep2["types"][T]["inst_taps_not_applied"] == []
    assert over2 == {"u_c.rst_n", "u_bout_y_o0.ea", "u_bout_y_o0.rst_n"}   # core 350 um, bank 400 um from the nearest tap
    assert [u["consumer"] for u in rep2["types"][T]["unmeasured"]] == ["u_u_fab_u_x_9_9.rst_n"]   # still no position


def test_inst_taps_row_not_in_bound_rtl_is_listed(tmp_path):
    b, p, _ = make(tmp_path, "rst_n", [{"tap": 1, "sinks": ["u_u_fab_u_x_0_0"]}])
    r = RLL.run(b, p)["types"][T]
    assert r["inst_taps_not_applied"] == [{"sink": "u_u_fab_u_x_0_0", "port": "rst_n", "want": "rst_n_t1", "bound": "rst_n"}]


def test_core_out_tap_and_lockup(tmp_path):
    b, p, _ = make(tmp_path)
    rep = RLL.run(b, p)
    (core,) = legs(rep, "u_c.rst_n")
    assert core["relay"] == "u_rrl_2" and core["leg_um"] == 350.0 and core in rep["types"][T]["over"]
    (out,) = legs(rep, "rst_o_0")
    assert out["relay"] == "u_rrl_3" and out["leg_um"] == 10.0
    assert {x["consumer"] for x in rep["types"][T]["legs"] if x["cls"] == "tap"} == {"tap0:clk", "tap1:clk_t1"}
    assert not legs(rep, "u_lk_c_rst_n.d")                                # covered by the core row


def test_bank_kit_repoint_and_bound_net(tmp_path):
    b, p, _ = make(tmp_path)
    (ea,) = legs(RLL.run(b, p), "u_bout_y_o0.ea")                         # face N window centre (900, 1300)
    assert ea["leg_rtl_um"] == 2180.0 and ea["bound_relay"] == "u_rrl_1"
    assert ea["relay"] == "u_rrl_2" and ea["leg_um"] == 400.0             # nearest consumer tap; still over 300
    (raw,) = legs(RLL.run(b, p, kit_repoint=False), "u_bout_y_o0.ea")
    assert raw["relay"] == "u_rrl_1" and raw["leg_um"] == 2180.0


def test_cli_exit_codes_and_outputs(tmp_path):
    b, p, pos = make(tmp_path)
    oj, ot = tmp_path / "o.json", tmp_path / "o.tsv"
    assert RLL.main([str(b), str(p), "--positions", str(pos), "--out-json", str(oj), "--out-tsv", str(ot)]) == 0
    rep = json.loads(oj.read_text())
    assert rep["advisory"] is True and rep["summary"]["types_over"] == 1
    rows = [l.split("\t") for l in ot.read_text().splitlines()]
    assert rows[0][0] == "status" and {r[0] for r in rows[1:]} == {"OVER", "UNMEASURED"}
    assert RLL.main([str(tmp_path / "nope"), str(p)]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    assert RLL.main([str(b), str(bad)]) == 2


def test_inst_taps_row_on_core_tap_is_flagged(tmp_path):
    b, p, _ = make(tmp_path, "rst_n", [{"tap": 2, "sinks": ["u_u_fab_u_x_0_0"]}])
    r = RLL.run(b, p)["types"][T]
    assert r["inst_taps_off_consumer"] == [{"tap": 2, "tap_name": "o0", "n_reset_consumers": 2, "sinks": ["u_u_fab_u_x_0_0"]}]
