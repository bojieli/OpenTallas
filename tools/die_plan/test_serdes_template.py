"""HARD-S81-SERDES-1 11-13: serdes_template.py (one template for every shore serdes type)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import serdes_template as st  # noqa: E402


def _type(px, face, wi, wo):
    return {"outline_um": [2885.76, 1226.88], "verilog_defines": ["OT_KP4_DEC_HARD"],
            "contents": [{"inst": "u_phy", "physical_parts": [
                {"physical_inst": "u_bound.u_core.u_ptx", "origin_um": [px, 1092.96], "orient": "MX"},
                {"physical_inst": "u_bound.u_core.u_prx", "origin_um": [px, 951.48], "orient": "MX"}]},
                {"inst": "u_bound.u_core.u_dec.u_dly.u_dmem", "origin_um": [1183.68, 62.652]},
                {"inst": "u_bound.u_core.u_dec.u_out.u_cmem", "origin_um": [1373.76, 62.652]}],
            "hard_cores": [{"inst": "u_core.u_dec.u_chn", "origin_um": [864.0, 95.04], "orient": "R180"}],
            "buses": [{"name": "coll_i0", "dir": "in", "face": face, "window_um": wi},
                      {"name": "coll_o0", "dir": "out", "face": face, "window_um": wo}]}


def test_e_face_type_passes_with_the_fixed_rows():
    r = st.template("t2", _type(244.536, "E", [119.04, 228.444], [6.144, 117.852]))
    assert r["verdict"] == "PASS" and r["end"] == "E" and r["max_hop_um"] <= 405
    assert r["island_um"][2] == 2490.936 and abs(r["island_um"][3] - 943.98) < 1e-6      # under the PMA, at its E end
    assert [c["rows"] for c in r["serdes_lanes"]["chains"]] == [3, 6, 5, 3]
    gen_phys.serdes_lanes_cfg_tcl(r["serdes_lanes"])                                     # the generator accepts it


def test_s_face_type_uses_the_pma_end_nearest_the_bar():
    r = st.template("t12", _type(63.528, "S", [1020.288, 1128.54], [776.64, 884.508]))
    assert r["end"] == "W" and r["verdict"] == "PASS"


def test_moves_are_moves_only_and_on_the_grid():
    r = st.template("t2", _type(244.536, "E", [119.04, 228.444], [6.144, 117.852]))
    for leaf, m in r["moves"].items():
        dx = m["to"][0] - m["from"][0]; dy = m["to"][1] - m["from"][1]
        assert abs(dx / st.GX - round(dx / st.GX)) < 1e-6 and abs(dy / st.GY - round(dy / st.GY)) < 1e-6, leaf


def test_blocks_leave_exactly_island_and_strip_free():
    r = st.template("t2", _type(244.536, "E", [119.04, 228.444], [6.144, 117.852]))
    def blocked(x, y): return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in r["serdes_lanes"]["blocks"])
    ix0, iy0, ix1, iy1 = r["island_um"]
    assert not blocked((ix0 + ix1) / 2, (iy0 + iy1) / 2)
    assert blocked(500.0, 300.0) and blocked(ix0 - 5, iy0 + 5) and blocked((ix0 + ix1) / 2, iy0 - 5)
    sx0, sy0, sx1, sy1 = r["pin_strip_um"]
    assert not blocked((sx0 + sx1) / 2, (sy0 + sy1) / 2)


def test_apply_sets_the_key_the_define_and_the_origins():
    plan = {"partition_types": {"t2": _type(244.536, "E", [119.04, 228.444], [6.144, 117.852])}}
    r = st.template("t2", plan["partition_types"]["t2"])
    out = st.apply(plan, [r])["partition_types"]["t2"]
    assert "OT_S81_SERDES_LANE" in out["verilog_defines"] and out["serdes_lanes"] == r["serdes_lanes"]
    assert out["hard_cores"][0]["origin_um"] == r["moves"]["u_chn"]["to"]
    assert plan["partition_types"]["t2"]["hard_cores"][0]["origin_um"] == [864.0, 95.04]   # input untouched


def test_apply_adds_the_cone_forms_and_delta_lists_only_serdes_changes():
    plan = {"partition_types": {"t2": _type(244.536, "E", [119.04, 228.444], [6.144, 117.852]),
                                "other": {"outline_um": [10, 10], "verilog_defines": ["X"]}}}
    r = st.template("t2", plan["partition_types"]["t2"])
    new = st.apply(plan, [r])
    d = new["partition_types"]["t2"]["verilog_defines"]
    assert d[:2] == ["OT_KP4_DEC_HARD", "OT_S81_SERDES_LANE"] and all(x in d for x in st.CONE_DEFINES)
    assert "OT_S81_RCK_RELAY4" not in d
    assert st.apply(plan, [r], cone=False)["partition_types"]["t2"]["verilog_defines"] == ["OT_KP4_DEC_HARD", "OT_S81_SERDES_LANE"]
    dl = st.delta(plan, new)
    assert set(dl) == {"t2"} and dl["t2"]["verilog_defines"]["from"] == ["OT_KP4_DEC_HARD"]
    assert dl["t2"]["moves"]["u_core.u_dec.u_chn"]["to"][0] == r["moves"]["u_chn"]["to"]
    assert dl["t2"]["moves"]["u_bound.u_core.u_dec.u_dly.u_dmem"]["to"][0] == r["moves"]["u_dmem"]["to"]


def test_apply_moves_srams_that_are_physical_parts():
    ty = _type(244.536, "E", [119.04, 228.444], [6.144, 117.852])
    sr = [c for c in ty["contents"] if c["inst"].endswith(("u_dmem", "u_cmem"))]
    ty["contents"] = [c for c in ty["contents"] if c not in sr]
    ty["contents"][0]["physical_parts"] += [{"physical_inst": c["inst"], "origin_um": c["origin_um"], "orient": "R0"} for c in sr]
    plan = {"partition_types": {"t2": ty}}
    r = st.template("t2", ty)
    pp = {q["physical_inst"].split(".")[-1]: q for q in st.apply(plan, [r])["partition_types"]["t2"]["contents"][0]["physical_parts"]}
    assert pp["u_dmem"]["origin_um"] == r["moves"]["u_dmem"]["to"] and pp["u_cmem"]["origin_um"] == r["moves"]["u_cmem"]["to"]
