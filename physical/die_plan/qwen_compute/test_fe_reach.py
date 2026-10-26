"""D-QC-FE-REACH (PATH-QC 10-26): fe_reach.py extract (bound-module bit map) + gen_plan.declare_fe_reach_stations
(n per FE in bus, mirror-equalised per port role, lanes fixed_cycles)."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fe_reach as FR  # noqa: E402
import gen_plan as G  # noqa: E402

BOUND = """module qfd_qc_slw_fe__slw_fe_v9 (input wire clk);
    wire [3:0] x_stm_i_q;
    wire [3:0] dd_ei_q;
    wire [3:0] w_core_st_up_o;
    wire [3:0] w_core_chu_q;
    ot_dp_st #(.W(4)) u_bout_st_eo (.clk(clk), .rst_n(rst_n), .d(w_core_st_up_o[3:0]), .ea(rst_n), .q(st_eo[3:0]), .eq(st_eo[4]));
    ot_dp_st #(.W(4)) u_bout_x_fw_o (.clk(clk), .rst_n(rst_n), .d({w_core_chu_q[1:0], w_core_chu_q[3:2]}), .ea(rst_n), .q(x_fw_o[3:0]), .eq(x_fw_o[4]));
    qfd_dv_s6_fup u_core (
        .ch_up_i(dd_ei_q),
        .chu_q(w_core_chu_q),
        .st_up_c({x_stm_i_q[3:0]}),
        .st_up_o(w_core_st_up_o)
    );
endmodule
"""


def test_extract_bit_map():
    r = FR.extract_type(BOUND)
    assert r["leaf"] == "qfd_dv_s6_fup" and r["bits"] == 8
    ch = sorted(map(tuple, r["chains"]))
    assert ("x_stm_i", 0, 3, "st_eo", 0, 0) in ch           # zero-logic forwarder, bitwise
    assert ("dd_ei", 0, 1, "x_fw_o", 2, 1) in ch and ("dd_ei", 2, 3, "x_fw_o", 0, 1) in ch   # via chu_q


def _plan():
    def bus(n, d, face, lo, hi, w=4):
        return dict(name=n, dir=d, width=w, kind="data", face=face, window_um=[lo, hi], layers=["M6", "M4"],
                    order="lsb_low")
    t = lambda: dict(outline_um=[622.08, 1339.2], buses=[bus("x_stm_i", "in", "W", 1000, 1010), bus("st_eo", "out", "E", 700, 710),
                                                       bus("dd_ei", "in", "E", 130, 140), bus("x_fw_o", "out", "W", 520, 530)])
    tw = t()
    te = t()
    for b in te["buses"]:
        b["name"] = b["name"].replace("_ei", "_wi").replace("_eo", "_wo")
    te["buses"][2]["window_um"] = [100, 110]          # longer dd_wi route on the E slice: mirror max wins
    return dict(partition_types=dict(slw_fe_v9=tw, sle_fe_v9=te),
                partitions=[dict(name="sl_W0_fe", type="slw_fe_v9"), dict(name="sl_E0_fe", type="sle_fe_v9"),
                            dict(name="sl_W0_stm", type="x")],
                ports=[dict(id="L0__0", src=dict(part="sl_W0_stm", bus="x_stm_fe_o"), dst=dict(part="sl_W0_fe", bus="x_stm_i")),
                       dict(id="L1__0", src=dict(part="sl_W0_stm", bus="q"), dst=dict(part="sl_E0_fe", bus="dd_wi"))],
                lanes=[dict(id="L0", ports=["L0__0"]), dict(id="L1", ports=["L1__0"], fixed_cycles=1)])


def test_declare_counts_and_mirror():
    raw = _plan()
    fmap = dict(types={"slw_fe_v9": dict(chains=[["x_stm_i", 0, 3, "st_eo", 0, 0], ["dd_ei", 0, 3, "x_fw_o", 0, 1]]),
                       "sle_fe_v9": dict(chains=[["x_stm_i", 0, 3, "st_wo", 0, 0], ["dd_wi", 0, 3, "x_fw_o", 0, 1]])})
    rep = G.declare_fe_reach_stations(raw, fmap)
    reff = G.ST_LEN - G.FE_REACH_MARGIN
    # forwarder W (y~1000) -> E (y~700): L ~ 622 + 300 -> ceil(L / reff) - 1 = 2
    assert rep["role_stations"]["x_stm_i"] == 2
    # registered E (y~130 / ~100) -> W (y~520): ceil(L / reff) - 2 = 1 on both mirrors (dd_Xi one role)
    L = 622.08 + (525 - 105)
    assert rep["role_stations"]["dd_Xi"] == math.ceil(L / reff) - 2 == 1
    ist = {e["conn"]: e for e in raw["partition_types"]["slw_fe_v9"]["internal_stations"]}
    assert len(ist["bus:x_stm_i"]["regs_um"]) == 2 and ist["bus:x_stm_i"]["bit_route"] == "chain"
    assert len(ist["bus:dd_ei"]["regs_um"]) == 1
    assert rep["worst_hop_um"] <= G.ST_LEN
    lanes = {ln["id"]: ln for ln in raw["lanes"]}
    assert lanes["L0"]["fixed_cycles"] == 2 and lanes["L1"]["fixed_cycles"] == 2
    try:
        G.declare_fe_reach_stations(raw, fmap)
    except SystemExit:
        pass
    else:
        raise AssertionError("re-application must fail closed")
