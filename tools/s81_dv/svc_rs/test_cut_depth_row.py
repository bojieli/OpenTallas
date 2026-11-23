"""SVC-CUT-DEPTH row tool: sizing math and latency rows on a two-piece synthetic plan; wrapper patch state in the tree."""
import importlib.util, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cut_depth_row", HERE / "cut_depth_row.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def _plan():
    core = lambda m, x, y: dict(inst="c", module=m, origin_um=[x, y], outline_um=[100.0, 100.0])
    return dict(
        partition_types=dict(
            t_att=dict(outline_um=[1000.0, 2000.0], hard_cores=[core("ot_s81c_attn_hcore", 0.0, 0.0), core("ot_s81c_attn_hcore", 850.0, 900.0), core("ot_s81_svc_merge_h4", 900.0, 1900.0)]),
            t_rs=dict(outline_um=[500.0, 2000.0], hard_cores=[core("sram", 0.0, 950.0), core("sram", 400.0, 0.0)])),
        partitions=[dict(name="svc_1_rs", type="t_rs", origin_um=[0.0, 0.0], orient="R0"), dict(name="svc_1", type="t_att", origin_um=[500.0, 0.0], orient="R0")],
        ports=[dict(id="L1_0", src=dict(part="svc_1_rs", bus="o_u_rsv_01_Q_p"), dst=dict(part="svc_1", bus="i_u_rsv_01_Q_p"), width=805, face="E", window_um=[900.0, 1100.0], note="x: cut route leaf u_rsv_01 -> u_rsv_01 piece 0 -> 1"),
               dict(id="L2_0", src=dict(part="svc_1", bus="o_u_rsv_01_Q_p_2"), dst=dict(part="svc_1_rs", bus="i_u_rsv_01_Q_p_2"), width=1100, face="W", window_um=[900.0, 1100.0], note="x: cut route leaf u_rsv_01 -> u_rsv_01 piece 1 -> 0"),
               dict(id="L3_0", src=dict(part="svc_1", bus="o_attn_i0_p"), dst=dict(part="svc_1_rs", bus="i_attn_i0_p"), width=9, face="W", window_um=[10.0, 20.0], note="x: cut route sink attn_i0 piece 1 -> 0")],
        lanes=[dict(id="L1", ports=["L1_0"]), dict(id="L2", ports=["L2_0"]), dict(id="L3", ports=["L3_0"])],
        latency=dict(lanes=dict(L1=dict(cycles=2), L2=dict(cycles=2), L3=dict(cycles=2))))


def test_sizing_and_rows():
    tab, uni = M.sizing(_plan(), 405.0)
    att = [x for x in tab if x["side"] == "att"][0]; rest = [x for x in tab if x["side"] == "rest"][0]
    # att window W face x=0 y=1000: cores at (50,50) 1000, (900,950) 950, (950,1950) 1900 -> med 1000, max 1900
    assert (att["dmed"], att["dmax"], att["k_med"], att["k_max"], att["lanes"]) == (1000.0, 1900.0, 2, 4, 2)
    # rest window E face x=500 y=1000: cores (50,1000) 450, (450,50) 1000 -> med 1000 (upper), max 1000
    assert (rest["dmax"], rest["k_max"]) == (1000.0, 2)
    assert uni["att"]["k_med"] == 2 and uni["rest"]["k_max"] == 2
    doc = M.latency_rows(_plan(), 4, 5)
    assert [r["lane"] for r in doc["rows"]] == ["L1", "L2"] and all(r["added_cycles"] == 9 for r in doc["rows"])
    assert doc["rows"][0]["direction"].startswith("in") and doc["rows"][1]["direction"].startswith("out")
    assert doc["schedule"]["registered_out_lane_at_slice_edges"] == 18 and doc["schema"] == "opentallas.latency_rows.v1"


def test_wrapper_default_depth_is_as_built():
    w = (HERE.parents[2] / "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv").read_text()
    assert re.search(r"parameter integer CUT_D = 1\b", w)
    assert "for (cut_gi = 1; cut_gi < CUT_D" in w and not re.search(r"reg \[[^\]]+\] st \[", w)   # plain flop vectors, no register arrays
