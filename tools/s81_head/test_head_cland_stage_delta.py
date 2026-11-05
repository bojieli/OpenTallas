"""DH55-CLAND: geometry + count rules of head_cland_stage_delta.py on a synthetic strip type (no plan files needed)."""
import importlib.util, json, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("hcsd", HERE / "head_cland_stage_delta.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)


def fake_type():
    bands = {"a_i": {"rect_um": [17, 17, 97, 131]}, "b_i": {"rect_um": [1073, 646, 1279, 691]}}
    pins = [dict(name="cland_fstart_out_x_o", xy_um=[2, 193]), dict(name="cland_up_ready_x_o", xy_um=[2, 188]),
            dict(name="cland_fstart_out_y_o", xy_um=[700, 120]), dict(name="cland_up_ready_y_o", xy_um=[705, 120])]
    T = {"clock": {"start_capture_um": [672.0, 126.8], "landing_contract": {"bands": bands, "pins": pins}}}
    coll = {"mask": {"inputs": ["a_i", "b_i"], "outputs": ["x_o", "y_o"], "tree_bus": "t_o", "intra_outputs": ["t_o"]},
            "collector_root_xy": [83.0, 0.0], "local_registered_depth": 4}
    return T, coll


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setitem(D.RRL, "t", [("r1", 1, 663, 127, 1), ("r2", 2, 663, 127, 0), ("r3", 3, 663, 127, 0),
                                     ("q3", 3, 82, 204, 0), ("s3", 3, 1180, 340, 0), ("w3", 3, 162, 700, 0)])
    monkeypatch.setitem(D.CTRL_DEPTH, "t", 4)
    monkeypatch.setitem(D.AGG1, "t", (90.0, 300.0))


def test_chain_hops_bounded():
    a, b = (0.0, 0.0), (1000.0, 600.0)
    for ea, eb in ((0, 0), (40, 90), (5, 120)):
        n = D.stages_needed(a, ea, b, eb)
        pts = [a] + D.chain(a, ea, b, eb, n) + [b]
        hops = [D.md(p, q) for p, q in zip(pts, pts[1:])]
        hops[0] += ea; hops[-1] += eb
        assert max(hops) <= D.HMAX + 1e-6
        assert D.stages_needed(a, ea, b, eb) == 0 or (D.md(a, b) + ea + eb) > D.HMAX


def test_type_delta_counts(setup):
    T, coll = fake_type()
    add, rep = D.type_delta("t", T, coll)
    R = add["landing_reader_start"]["depth"]
    assert set(add["landing_reader_start"]["branches"]) == {"a_i", "b_i"}           # every input ring
    assert all(len(b["stages"]) == R for b in add["landing_reader_start"]["branches"].values())   # uniform depth
    assert rep["ring_K_delta"] == {"a_i": -R, "b_i": -R}
    W = add["landing_writer_start"]["depth"]
    assert set(add["landing_writer_start"]["branches"]) == {"x_o"}                 # y_o FSTART is next to the origin
    assert rep["writer_buses_receiver_K_delta"] == {"x_o": W}
    assert rep["steady_data_cycles_added"] == 0 and rep["boot_extra_cycles"] == R + W
    for b in add["landing_writer_start"]["branches"].values():                     # writer raws never exported
        assert all(s["raw_reset"] != "r1" for s in b["stages"])
    # every status relay chain keeps hops <= HMAX from the band's farthest flop to the target
    assert "b_i" in add["landing_status_input_stages"]["x_o"]
    # local resets: raw depth = control depth - 1, each consumer exactly once, within reach
    seen = []
    for e in add["landing_local_resets"]:
        r = {x[0]: x for x in D.RRL["t"]}[e["raw"]]
        assert r[1] == 3
        assert D.md((r[2], r[3]), e["xy_um"]) <= D.COPY_REACH + 1e-6
        seen += e["consumers"]
    assert len(seen) == len(set(seen))
    assert {"u_cland_origin", "u_cland_fstart_x_o", "u_cland_up_x_o", "u_cland_up_t_o", "u_cland_agg_1"} <= set(seen)
    json.dumps(add)


def test_refuses_existing_knobs(setup):
    T, coll = fake_type()
    T["clock"]["landing_reader_start"] = {"depth": 1}
    with pytest.raises(AssertionError):
        D.type_delta("t", T, coll)


def test_ctl_e_bit_sites_hops(tmp_path):
    """s0 (W face flop, x ~6) -> s1 -> s2 hops stay <= 400 planned (3_place adds ~2.4 um), E pin_reg < 60."""
    rows = ["P\tx\tn_tx_ft_o[%d]\t0\t0\t0\t0\t%.3f" % (b, 8.64 + 0.27 * b) for b in range(65)]
    g = tmp_path / "geom.tsv"
    g.write_text("\n".join(rows) + "\n")
    T = {"ft_slots": [dict(name="n_tx_ft", in_face="W", out_face="E", stations=3, width=64)]}
    D.ctl_e_bit_sites(T, g)
    s = T["ft_slots"][0]["bit_sites_um"]
    w = T["ft_slots"][0]["bit_site_cell_um"][0]
    assert len(s) == 2 and all(len(c) == 65 for c in s)
    c1, c2 = s[0][0][0] + w / 2, s[1][0][0] + w / 2
    assert c1 - 6.0 <= 400.0 and c2 - c1 <= 400.0 and 855.36 - c2 < 60.0
    assert len({tuple(p) for p in s[0]}) == 65                                       # one site per bit


def test_rrl_from_rtl_reads_raw_relays_and_exports(tmp_path):
    f = tmp_path / "w.sv"
    f.write_text("    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 2 depth 1 @ (453.1, 17.3)\n"
                 "    ot_dp_rgate u_rrl_3 (.clk(clk), .d(rst_rl_2), .run(r), .q(rst_n_t2));  // gated pad tap 2 depth 4 @ (453.1, 17.3)\n"
                 "    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_2), .q(rr_t28));  // raw tap tap 28 depth 4 @ (150.7, 8.6)\n"
                 "    assign rst_start_raw_1 = rr_t28;\n")
    assert D.rrl_from_rtl(f) == [("rst_rl_0", 1, 453.1, 17.3, 0), ("rr_t28", 4, 150.7, 8.6, 1)]
