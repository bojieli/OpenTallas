"""QC-S28-VISFORM delta: guarded apply and the SC-ECHAN family move on a toy sc type."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import visform as V  # noqa: E402


def toy():
    t = dict(outline_um=[613.44, 1831.68], buses=[],
             hard_cores=[dict(inst="u_core", origin_um=[345.6, 980.825574], outline_um=[244.56, 514.08], orient="R0",
                              track_offset_um=[0.012, 0.012])],
             clock=dict(taps=[dict(name="glue_01", kind="glue", xy=[311.04, 1370.8], from_root_um=328.3),
                              dict(name="glue_00", kind="glue", xy=[311.04, 460.9], from_root_um=337.0),
                              dict(name="u_core.ck", kind="core", xy=[468.024, 980.885574])],
                        landing_contract=dict(collector_tree=dict(core_resets=[dict(inst="u_core", pin_um=[410.424, 980.8856],
                                                                                   xy=[341.292, 980.8856])]),
                                              group_rects_um={"u_cland_rst_a": [339.14, 1020.0, 343.46, 1024.3]})),
             ft_slots=[dict(name="s", in_face="W", out_face="E", width=2, stations=3,
                            regs_um=[[0, 1100], [200, 1100], [342.0, 1100]],
                            bit_sites_um=[[[199.0, 1100.0], [199.0, 1100.27]], [[341.28, 1100.0], [341.28, 1100.27]]]),
                       dict(name="n", in_face="N", out_face="S", width=1, stations=2,
                            regs_um=[[300.0, 1831.68], [299.0, 1100.0]], bit_sites_um=[[[298.08, 1100.0]]])])
    return dict(die=dict(grid_um=8.64), budgets={}, partition_types={"sle_sc_v2": t, "sle_fw_v3": dict(outline_um=[1, 1])})


def test_sc_echan_moves_core_and_w_edge_items_and_keeps_bits_legal():
    P = toy()
    ops, rep = [], {"SC-ECHAN": {}}
    V.sc_echan(P, ops, rep, 302.4)
    out, bad = V.apply_ops(P, dict(ops=ops))
    assert not bad
    t = out["partition_types"]["sle_sc_v2"]
    assert t["hard_cores"][0]["origin_um"][0] == 302.4
    assert rep["SC-ECHAN"]["sle_sc_v2"]["e_gap_um"][1] > 66
    taps = {x["name"]: x for x in t["clock"]["taps"]}
    assert taps["u_core.ck"]["xy"][0] == pytest.approx(424.824)
    assert taps["glue_01"]["xy"][0] == pytest.approx(267.84) and taps["glue_01"]["from_root_um"] == pytest.approx(371.5)
    assert taps["glue_00"]["xy"][0] == 311.04                       # below the core: untouched
    cr = t["clock"]["landing_contract"]["collector_tree"]["core_resets"][0]
    assert cr["pin_um"][0] == pytest.approx(367.224) and cr["xy"][0] == pytest.approx(298.092)
    assert t["clock"]["landing_contract"]["group_rects_um"]["u_cland_rst_a"][2] < 302.4
    s = t["ft_slots"][0]
    assert s["regs_um"][2][0] == pytest.approx(298.8) and s["regs_um"][1] == [200, 1100]
    # the shifted bits of slot s land on slot n's fixed bit at 298.08 -> re-sited to a free lattice site
    bits = [tuple(b) for st in s["bit_sites_um"] for b in st] + [tuple(b) for st in t["ft_slots"][1]["bit_sites_um"] for b in st]
    occ = V.Occ()
    for b in bits:
        assert not occ.hit(b)
        occ.add(b)
    assert all(b[0] < 302.4 - V.HALO for b in bits)


def test_apply_refuses_a_changed_from_value():
    P = toy()
    ops, rep = [], {"SC-ECHAN": {}}
    V.sc_echan(P, ops, rep, 302.4)
    Q = copy.deepcopy(P)
    Q["partition_types"]["sle_sc_v2"]["hard_cores"][0]["origin_um"] = [337.0, 980.825574]
    out, bad = V.apply_ops(Q, dict(ops=ops))
    assert out is None and bad and bad[0][-1] == "origin_um"


def test_off_lattice_core_x_is_refused():
    with pytest.raises(SystemExit):
        V.sc_echan(toy(), [], {"SC-ECHAN": {}}, 300.0)


def test_ctl_ring_and_fw_eface_family_keys():
    P = toy()
    P["partition_types"].update({"sle_ctl__a": {}, "sle_ctl__b": {}})
    P["budgets"] = {"cland_strip_density_types": {"sle_ctl__a": 1.0}, "cland_strip_rows_types": {"sle_ctl__b": 2, "x": 3}}
    ops, rep = [], {}
    V.ctl_ring(P, ops, rep)
    V.fw_eface(P, ops, rep)
    out, bad = V.apply_ops(P, dict(ops=ops))
    b = out["budgets"]
    assert b["cland_strip_density_types"] == {"sle_ctl": 1.0} and b["cland_strip_rows_types"] == {"x": 3, "sle_ctl": 2}
    assert b["face_flop_ew_types"]["sle_st_a"] == {"cpitch_sites": 80, "row_stride": 3}
    assert rep["FW-EFACE"]["types"] == ["sle_fw_v3"]
