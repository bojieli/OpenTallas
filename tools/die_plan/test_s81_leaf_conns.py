"""Tests for tools/die_plan/s81_leaf_conns.py (S81-PLANMODEL-1): the S81 leaf vn<->lane model derived from the leaf RTL."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import route_supply as rs  # noqa: E402
import s81_leaf_conns as LC  # noqa: E402
import test_route_supply as trs  # noqa: E402

SLICE = HERE.parents[1] / "rtl" / "dsrom_sys" / "s81_dv" / "slice"
VP = SLICE / "ot_s81sl_vp.sv"
needs_rtl = pytest.mark.skipif(not VP.exists(), reason="leaf RTL not in this (sparse) checkout")


@needs_rtl
def test_vp_glue_is_1024_four_sink_nets():
    vp = LC.parse_vp(VP.read_text())
    hi = vp["hi"]
    assert sum(g["bits"] for g in hi) == 1024 and {len(g["sinks"]) for g in hi} == {4}
    by = {k: sum(g["bits"] for g in hi if g["kind"] == k) for k in ("cf", "ly", "lr")}
    assert by == {"cf": 640, "ly": 128, "lr": 256}
    # 160 b quad-shared (cf, lanes 4KK..4KK+3) and 96 b gl%4-shared (ly + lr, lanes II, II+4, II+8, II+12) per group
    quad = {tuple(sorted(gl for gl, _ in g["sinks"])) for g in hi if g["kind"] == "cf"}
    mod4 = {tuple(sorted(gl for gl, _ in g["sinks"])) for g in hi if g["kind"] in ("ly", "lr")}
    assert quad == {(0, 1, 2, 3), (4, 5, 6, 7), (8, 9, 10, 11), (12, 13, 14, 15)}
    assert mod4 == {(0, 4, 8, 12), (1, 5, 9, 13), (2, 6, 10, 14), (3, 7, 11, 15)}
    for q in quad:
        assert sum(g["bits"] for g in hi if g["kind"] == "cf" and tuple(sorted(gl for gl, _ in g["sinks"])) == q) == 160
    for m in mod4:
        assert sum(g["bits"] for g in hi if g["kind"] in ("ly", "lr") and tuple(sorted(gl for gl, _ in g["sinks"])) == m) == 96
    assert vp["ho_bits"] == 18 and vp["hw_from_sram"] and vp["hs_from_hq"]


@needs_rtl
def test_parser_fails_closed_when_the_glue_stops_sharing():
    txt = VP.read_text()
    bad = txt.replace("ly[4 * k + i] <= yrow_d[YA][32 * i +: 32];", "ly[4 * k + i] <= yrow_d[YA][32 * (4 * k + i) +: 32];")
    assert bad != txt
    with pytest.raises(ValueError):
        LC.parse_vp(bad)


@needs_rtl
def test_leaf_defaults_are_depth_zero_and_kv_leaf_from_w3():
    d = LC.leaf_defaults((SLICE / "ot_s81sl_slice.sv").read_text())
    assert d["CS_HI_D"] == d["CS_HO_D"] == d["CS_SW_D"] == d["CS_VNI_D"] == 0
    w3 = SLICE / "cap_end" / "ot_s81sl_slice_w3.sv"
    if w3.exists():
        kv = LC.kv_leaf_depths(w3.read_text())
        assert kv["t3"]["CS_HI_D"] == 1 and kv["t1"]["CS_HI_D"] == 1 and kv["t3"]["CS_SWR_D"] == 1
        assert kv["t1"]["CS_SWR_D"] == 0 and kv["t5"]["CS_RAR_D"] == 1 and kv["t4"]["CS_RAR_D"] == 0


def leaf_type(station_depth=1):
    """a 16-lane leaf: lanes in a 4x4 grid right of two vn cores and the SRAMs; one hq_d station per lane (plan model)."""
    hc = [dict(inst="u_lf.u_vn.u_a", module="vn", origin_um=[100, 100], outline_um=[100, 100], orient="R0"),
          dict(inst="u_lf.u_vn.u_b", module="vn", origin_um=[100, 300], outline_um=[100, 100], orient="R0"),
          dict(inst="u_lf.u_vp.u_b0", module="sram", origin_um=[100, 500], outline_um=[100, 100], orient="R0"),
          dict(inst="u_lf.u_vp.u_b1", module="sram", origin_um=[100, 700], outline_um=[100, 100], orient="R0")]
    st = []
    for gl in range(16):
        hc.append(dict(inst=f"u_lf.u_vp.g_ln[{gl}].u_l", module="lane", origin_um=[400 + 120 * (gl % 4), 100 + 120 * (gl // 4)],
                       outline_um=[100, 100], orient="R0"))
        for half in ("a", "b"):
            st.append({"conn": f"core:u_lf.u_vn.u_{half}.hq_d|core:u_lf.u_vp.g_ln[{gl}].u_l", "bits": 256,
                       "launch": f"core:u_lf.u_vn.u_{half}.hq_d", "capture": f"u_lf.u_vp.g_ln[{gl}].u_l",
                       "from_um": [200, 150], "to_um": [450, 150], "regs_um": [[300, 150]] * station_depth})
    return dict(outline_um=[1000, 900], hard_cores=hc, internal_stations=st)


def kit():
    return LC._kit()


@needs_rtl
def test_build_type_nets_claims_and_phantoms():
    vp = LC.parse_vp(VP.read_text())
    t = leaf_type(1)
    base = {"u_lf.u_vn.u_a": {"hq_d": [f"core:u_lf.u_vp.g_ln[{g}].u_l" for g in range(16)],
                              "hr_v": [f"core:u_lf.u_vp.g_ln[{g}].u_l" for g in range(16)], "c_s": ["core:u_lf.u_vn.u_b"]}}
    r0 = LC.build_type("t", t, vp, {"CS_HI_D": 0}, kit(), base=base)
    nets = r0["nets"]
    assert sum(n["bits"] for n in nets if n["kind"] == "hi_fan") == 1024
    assert sum(n["bits"] for n in nets if n["kind"] == "hi_feed") == 2 * 256          # vn_a and vn_b each drive the OR
    assert [n["bits"] for n in nets if n["kind"] == "ho"] == [18] * 16
    assert {tuple(sorted({p for _, p in n["pins"]})) for n in nets if n["kind"] == "hi_fan"} >= {("y",)}
    # depth 0: every plan hq_d station is unrealised; depth 1 (a kv_leaf bind): none is
    assert len(r0["phantom"]) == 32 and all(p["cls"] == "hi" for p in r0["phantom"])
    assert not LC.build_type("t", t, vp, {"CS_HI_D": 1}, kit(), base=base)["phantom"]
    # the vn ports the lanes no longer see per lane: hq_d claimed (-> glue), hr_v to the vp glue, c_s kept
    c = r0["conns"]["u_lf.u_vn.u_a"]
    assert c["hq_d"] == ["glue"] and c["hr_v"] == ["glue"] and c["c_s"] == ["core:u_lf.u_vn.u_b"]
    assert base["u_lf.u_vn.u_a"]["hr_v"][0].startswith("core:")                        # the input is not mutated


@needs_rtl
def test_sram_paths_are_opt_in():
    vp = LC.parse_vp(VP.read_text())
    t = leaf_type(0)
    a = LC.build_type("t", t, vp, {}, kit())
    b = LC.build_type("t", t, vp, {}, kit(), sram=True)
    assert len(b["nets"]) == len(a["nets"]) + 6 and {n["kind"] for n in b["nets"]} - {n["kind"] for n in a["nets"]} == {
        "sram_feed", "sram_hw", "hq_wd"}


def test_type_without_a_16_lane_leaf_is_not_modelled():
    assert LC.type_insts([dict(inst="u_a"), dict(inst="u_lf.u_vp.g_ln[0].u_l")]) is None


def test_route_supply_reads_the_sidecar(tmp_path):
    """fanout_nets claim their ports (no glue escape, no core_conns net) and replace them by one multi-sink net;
    unrealised_stations are dropped before the demand is built; --no-planmodel turns both off."""
    trs.plan(tmp_path, n=40, macro=False)
    P = json.loads((tmp_path / "plan.json").read_text())
    t = P["partition_types"]["t"]
    t["internal_stations"] = [{"conn": "core:u_a.d|core:u_b", "launch": "core:u_a.d", "capture": "u_b", "from_um": [50, 100],
                               "to_um": [350, 300], "regs_um": [[200, 200]], "bits": 40}]
    (tmp_path / "plan.json").write_text(json.dumps(P))
    base = {"t": {"u_a": {"d": ["core:u_b"]}, "u_b": {"d": ["core:u_a"]}}}
    side = dict(core_conns=base,
                fanout_nets={"t": [dict(name="n0", kind="hi_fan", bits=40, pins=[["u_a", "d"], ["u_b", "d"]])]},
                unrealised_stations={"t": {"phantom": [dict(idx=0, conn="core:u_a.d|core:u_b", bits=40)]}})
    (tmp_path / "side.json").write_text(json.dumps(side))
    (tmp_path / "base.json").write_text(json.dumps({"core_conns": base}))
    out = {}
    for arm, f, extra in (("stock", "base.json", []), ("model", "side.json", []), ("off", "side.json", ["--no-planmodel"])):
        (tmp_path / "core_conns.json").write_text((tmp_path / f).read_text())
        _, r, _ = trs.run(tmp_path, *extra)
        out[arm] = r
    assert out["stock"]["station_bits"] == 40 and "UNREALISED" not in " ".join(out["stock"]["notes"])
    assert out["model"]["station_bits"] == 0
    assert any(n.startswith("UNREALISED 1 plan station") for n in out["model"]["notes"])
    assert any(n.startswith("PLANMODEL 1 fan-out nets / 40 b replace 80 core pins") for n in out["model"]["notes"])
    assert out["off"]["station_bits"] == 40 and not any(n.startswith("PLANMODEL") for n in out["off"]["notes"])


def test_fanout_net_is_one_net_not_one_per_sink(tmp_path):
    """four sinks on one net cost the net's bbox once; four 2-pin chains to the same sinks cost four times."""
    trs.plan(tmp_path, n=40, macro=False)
    one = dict(name="n", kind="hi_fan", bits=40, pins=[["u_a", "d"], ["u_b", "d"]])
    base = {"t": {"u_a": {"d": ["core:u_b"]}, "u_b": {"d": ["core:u_a"]}}}
    for k, nets in (("one", [one]), ("two", [one, dict(one, name="m")])):
        (tmp_path / "core_conns.json").write_text(json.dumps(dict(core_conns=base, fanout_nets={"t": nets})))
        out = trs.run(tmp_path)[1]
        if k == "one":
            wl1 = out["wirelength_mm"]
        else:
            wl2 = out["wirelength_mm"]
    assert wl2 > wl1 * 1.5
