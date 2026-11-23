"""ADV-SITE-COLLIDE: the HEAD r18m hd_lep0N_w positive (3dd49f406010) is flagged, its r18n fix (341dbb140f8f) and the
designed layouts the module must leave alone are not."""
import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("adv_site_collide", HERE / "adv_site_collide.py")
SC = importlib.util.module_from_spec(_spec)
sys.modules["adv_site_collide"] = SC
_spec.loader.exec_module(SC)


def _lep0n_w(stage_y=1370.0):
    """hd_lep0N_w as in r18m (stage_y 1370) / r18n (1380): the coll_i0 reader START stages beside the coll_o1 / coll_o2
    status stages and local reset k12 (plan values)."""
    return {
        "outline_um": [820.8, 1408.32],
        "hard_cores": [{"inst": "u_rg1.u_pair", "origin_um": [34.56, 846.72], "outline_um": [777.6, 492.48]}],
        "relay_sites": {"u_core.u.g_rfan.u_rfan.g_leaf[25].leaf_r": [340.0, 687.0]},
        "reset": {"local_taps_um": [[743.04, 1343.52]]},
        "clock": {
            "landing_reader_start": {"depth": 2, "branches": {"coll_i0": {"stages": [
                {"xy_um": [131.61, stage_y], "raw_reset": "rst_rl_256"},
                {"xy_um": [485.61, stage_y], "raw_reset": "rst_rl_256"}]}}},
            "landing_status_input_stages": {
                "agg": {"coll_i0": [{"xy_um": [512.51, 1370.0]}, {"xy_um": [185.42, 1370.0]}]},
                "coll_o1": {"coll_i0": [{"xy_um": [487.06, 1370.0]}, {"xy_um": [134.51, 1370.0]}]},
                "coll_o2": {"coll_i0": [{"xy_um": [487.92, 1370.0]}, {"xy_um": [136.24, 1370.0]}]}},
            "landing_status_anchors": {"u_cland_agg_4": [170.39, 1380.0], "u_cland_agg_5": [495.8, 1380.0]},
            "landing_local_resets": [
                {"name": "k12", "raw": "rst_rl_256", "xy_um": [487.06, 1370.0],
                 "consumers": ["u_cland_sin_coll_o1_coll_i0_0", "u_cland_sin_coll_o2_coll_i0_0"]}],
        },
    }


def _plan(**types):
    return {"partition_types": types, "partitions": [{"name": f"u_{n}", "type": n} for n in types], "ports": []}


def _crowd(lines):
    return [x for x in lines if " CROWD " in x]


def test_r18m_positive_flagged():
    out = SC.findings(_plan(hd_lep0N_w=_lep0n_w(1370.0)), "r18m.json")
    c = _crowd(out)
    assert len(c) == 1, out
    assert c[0].startswith("WARN ADV-SITE-COLLIDE hd_lep0N_w: CROWD 4 FIRM sites at 3 points")
    assert "reader_start.coll_i0.stages[1] (485.61,1370)" in c[0]
    assert "local_reset.k12(rst_rl_256) (487.06,1370)" in c[0]
    assert out[-1].startswith("WARN ADV-SITE-COLLIDE 1 crowded window(s)")


def test_r18n_fix_clean():
    assert SC.findings(_plan(hd_lep0N_w=_lep0n_w(1380.0)), "r18n.json") == []


def test_start_fan_and_fstart_reset_are_designed():
    """S81 slice_station__t8 / KV kv3_pv_*: many START branches share one stage point, the fstart local reset sits beside
    them, a bit-sited station register 1.1 um away: no CROWD."""
    t = {"outline_um": [800.0, 1300.0],
         "ft_slots": [{"name": "ft8", "regs_um": [[551.6541, 1221.4287]], "bit_sites_um": [[[551.0, 1221.0]]]}],
         "clock": {"landing_writer_start": {"branches": {
                       f"ft{k}_o": {"stages": [{"xy_um": [600.0, 1222.56]}, {"xy_um": [551.392, 1222.56]}]}
                       for k in (5, 6, 7, 8, 9, 10)}},
                   "landing_local_resets": [{"name": "fstart_1", "raw": "rst_rl_43", "xy_um": [551.104, 1224.224],
                                             "consumers": ["u_cland_fstart_ft8_o"]}]}}
    assert _crowd(SC.findings(_plan(slice_station__t8=t), "p.json")) == []


def test_status_with_own_reset_and_bit_relays_are_designed():
    """HEAD hd_spn: 2 status stages + their 2 reset copies on 2 points; hd_tile: 27 bus-bit relays in 4.3 um."""
    t = {"outline_um": [700.0, 2100.0],
         "relay_sites": {f"u_b.g_a[0].g_ais.u_ad1/q[{i}]": [175.17 + 0.14 * i, 329.97] for i in range(27)},
         "clock": {"landing_status_input_stages": {"b_o": {"bd_i": [{"xy_um": [409.0, 2022.91]}],
                                                           "hd_i": [{"xy_um": [409.35, 2023.29]}]}},
                   "landing_local_resets": [
                       {"name": "geo_154", "raw": "rst_rl_49", "xy_um": [409.0, 2022.91], "consumers": ["u_cland_sin_b_o_bd_i_0"]},
                       {"name": "geo_170", "raw": "rst_rl_49", "xy_um": [409.35, 2023.29], "consumers": ["u_cland_sin_b_o_hd_i_0"]}]}}
    assert _crowd(SC.findings(_plan(hd_spn=t), "p.json")) == []


def test_keepout_move_and_halo():
    t = _lep0n_w(1380.0)
    t["clock"]["landing_local_resets"].append({"name": "k3", "raw": "rst_rl_220", "xy_um": [430.0, 1319.65],
                                               "consumers": ["u_cland_sin_coll_o1_coll_i1_0"]})
    out = SC.findings(_plan(hd_lep0N=t), "p.json", list_keepout=True)
    k = [x for x in out if " KEEPOUT " in x]
    assert len(k) == 1 and "local_reset.k3(rst_rl_220) at (430,1319.65)" in k[0] and "moves it 26.0 um to (430,1345.68)" in k[0], out
    h = copy.deepcopy(_lep0n_w(1380.0))
    h["hard_cores"][0]["halo_um"] = 6.0
    h["clock"]["landing_status_anchors"]["u_cland_agg_9"] = [400.0, 1342.5]    # 3.3 um above the box: rows kept, halo blocks
    out = SC.findings(_plan(hd_lep0N=h), "p.json", list_keepout=True)
    assert any(" KEEPOUT status status_anchor.u_cland_agg_9" in x and "HALO-1 ring of u_rg1.u_pair" in x for x in out), out
    del h["hard_cores"][0]["halo_um"]
    assert not any(" KEEPOUT " in x for x in SC.findings(_plan(hd_lep0N=h), "p.json", list_keepout=True))


def test_never_raises():
    assert SC.findings(None, "x")[0].startswith("WARN ADV-SITE-COLLIDE not checked")
    bad = _plan(t={"clock": {"landing_reader_start": {"branches": {"a": {"stages": [{"xy_um": ["x", None]}]}}},
                             "landing_local_resets": "oops"}, "relay_sites": [1, 2]})
    out = SC.findings(bad, "x")
    assert all(x.startswith("WARN ADV-SITE-COLLIDE") for x in out)


def test_line_cap():
    t = _lep0n_w(1370.0)
    br = t["clock"]["landing_reader_start"]["branches"]
    for i in range(40):                                   # 40 more START-on-status collisions
        x = 20.0 + 15.0 * i
        br[f"b{i}"] = {"stages": [{"xy_um": [x, 200.0]}]}
        t["clock"]["landing_status_input_stages"]["coll_o1"][f"b{i}"] = [{"xy_um": [x + 1.0, 200.0]}]
        t["clock"]["landing_status_input_stages"]["coll_o2"][f"b{i}"] = [{"xy_um": [x + 1.8, 200.0]}]
        t["clock"]["landing_local_resets"].append({"name": f"r{i}", "xy_um": [x + 1.0, 200.0], "consumers": ["u_cland_sin_x"]})
    out = SC.findings(_plan(hd_lep0N_w=t), "p.json", list_keepout=True)
    assert len(out) == SC.MAX_LINES + 1 and out[-1].startswith("WARN ADV-SITE-COLLIDE 41 crowded window(s)"), out[-1]
