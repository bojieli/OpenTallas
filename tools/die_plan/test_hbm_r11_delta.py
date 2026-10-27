"""PATH-HBM-R11 y-demand segments / option (a) / die growth: synthetic checks (new opt-in tool, no default change)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r11_delta as D  # noqa: E402
import hbm_r10_delta as R10  # noqa: E402


def test_cc_serialise_only_long_core_core():
    st = [dict(conn="c1", from_um=[100.0, 100.0], to_um=[1300.0, 100.0], bits=9, regs_um=[]),     # 1200 um core-core
          dict(conn="c2", from_um=[100.0, 100.0], to_um=[600.0, 100.0], bits=9, regs_um=[]),      # 500 um: kept
          dict(conn="f", from_um=[100.0, 0.0], to_um=[1500.0, 100.0], bits=9, regs_um=[]),        # face: kept
          dict(conn="s", from_um=[100.0, 50.0], to_um=[1500.0, 100.0], bits=9, regs_um=[], serial_k=4)]
    links = D.serialise_cc(st, 2000.0, 400.0, 2, 1000.0)
    assert [l["conn"] for l in links] == ["c1"] and st[0]["bits"] == 5 and st[0]["bits_parallel"] == 9
    assert st[1]["bits"] == 9 and st[2]["bits"] == 9 and st[3]["bits"] == 9
    assert D.serialise_cc(copy.deepcopy(st), 2000.0, 400.0, 1) == []


def test_spread_restores_legaliser():
    orig = R10.legalise
    st = [dict(from_um=[100.0, 400.0], to_um=[100.0, 200.0], bits=60, regs_um=[],
               r10=dict(face="N", fend="from", bus="L", ivx=[0.0, 900.0], ivy=[0.0, 400.0]))]
    D.spread_place(st, 900.0, 400.0, 6.0, 3.0)
    assert R10.legalise is orig and abs(st[0]["from_um"][0] - 100.0) < 1e-6


def _die():
    T = {"hub": dict(outline_um=[100.0, 100.0], hard_cores=[]),
         "bank": dict(outline_um=[50.0, 100.0], hard_cores=[]),
         "top": dict(outline_um=[150.0, 50.0], hard_cores=[]),
         "root": dict(outline_um=[20.0, 300.0], hard_cores=[dict(inst="r0", origin_um=[0.0, 0.0], outline_um=[20.0, 140.0])],
                      contents=[], internal_stations=[dict(from_um=[0.0, 10.0], to_um=[0.0, 250.0], regs_um=[[0.0, 200.0]])],
                      ft_slots=[], clock=dict(tap_um=[5.0, 260.0], taps=[]), reset={})}
    parts = [dict(name="H", type="hub", origin_um=[0.0, 100.0]), dict(name="B", type="bank", origin_um=[100.0, 100.0]),
             dict(name="T", type="top", origin_um=[0.0, 200.0]), dict(name="R", type="root", origin_um=[150.0, 0.0])]
    ports = [dict(src=dict(part="R", bus="a"), dst=dict(part="T", bus="b"), face="E", window_um=[210.0, 240.0]),
             dict(src=dict(part="B", bus="a"), dst=dict(part="H", bus="b"), face="W", window_um=[120.0, 180.0])]
    return dict(die=dict(outline_um=[170.0, 300.0], io=[], pg=dict(domains=[])), partition_types=T, partitions=parts,
                ports=ports, clock=dict(spine=dict(root_um=[160.0, 250.0])))


def test_grow_die_inserts_once_above_rigid_root_core():
    P = _die()
    g = D.grow_die(P, ["H"], 100.0, 160.0)
    pos = {p["name"]: p["origin_um"] for p in P["partitions"]}
    assert g["dH_um"] == 60.0 and g["insertion_y_um"] >= 140.0 - 1e-6        # root core r0 [0,140] not cut
    assert pos["T"] == [0.0, 260.0] and pos["B"] == [100.0, 100.0] and pos["H"] == [0.0, 100.0]
    assert P["die"]["outline_um"] == [170.0, 360.0] and P["partition_types"]["root"]["outline_um"] == [20.0, 360.0]
    st = P["partition_types"]["root"]["internal_stations"][0]
    assert st["from_um"] == [0.0, 10.0] and st["to_um"] == [0.0, 310.0] and st["regs_um"] == [[0.0, 260.0]]
    assert P["ports"][0]["window_um"] == [270.0, 300.0] and P["ports"][1]["window_um"] == [120.0, 180.0]
    assert g["hub_row_gap_rects_um"] == [[100.0, 200.0, 150.0, 260.0]]
    assert P["clock"]["spine"]["root_um"] == [160.0, 310.0]


def test_grow_row_types_closes_strip():
    P = _die()
    P["partition_types"]["bank"]["internal_stations"] = [dict(from_um=[10.0, 100.0], to_um=[10.0, 20.0], regs_um=[])]
    g = D.grow_die(P, ["H"], 100.0, 160.0, grow_row=True)
    assert g["row_types_grown"] == ["bank"] and g["hub_row_gap_rects_um"] == []
    assert P["partition_types"]["bank"]["outline_um"] == [50.0, 160.0]
    assert P["partition_types"]["bank"]["internal_stations"][0]["from_um"] == [10.0, 160.0]
