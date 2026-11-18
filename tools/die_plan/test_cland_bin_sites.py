"""QC-CB-GEN-1115 cland_bin_sites.py: u_bin inside its own band at the edge facing the route, every hop <= 405 um, legal sites."""
import cland_bin_sites as C


def _plan(bands, stations=None):
    return {"partition_types": {"cbn_qx": dict(
        outline_um=[1235.52, 2540.16],
        hard_cores=[dict(inst="u_t22", origin_um=[86.4, 69.12], outline_um=[457.92, 1157.76])],
        buses=[dict(name="bc_i22", face="S", window_um=[94.128, 183.376]), dict(name="nb_i22", face="S", window_um=[184.336, 272.768])],
        internal_stations=stations or [],
        clock=dict(landing_contract=dict(bands=bands)))}}


BANDS = {"bc_i22": dict(rect_um=[84.24, 17.28, 289.44, 62.64]), "nb_i22": dict(rect_um=[291.6, 17.28, 542.16, 62.64])}
PREV = {"types": {"cbn_qx": {"bc_i22": {"u_bin": [492.48, 34.56], "u_st": [587.52, 328.32], "route_um": 1171.9}}}}


def test_u_bin_at_the_east_end_of_its_own_band_and_hops_under_405():
    r = C.build(_plan(BANDS), PREV, {}, set(), set())["cbn_qx"]["bc_i22"]
    assert r["u_bin"] == [280.8, 34.56] and r["equal_hop_um"] <= 405 and "u_st_more" in r        # bin + 2 stations: 4 hops
    assert len(r["hops"]) == 4 and abs(r["hops"][0] - (138.752 - 280.8 and abs(280.8 - 138.752) + 34.56)) < 1.0


def test_sites_are_legal_and_on_the_grid():
    r = C.build(_plan(BANDS), PREV, {}, set(), set())["cbn_qx"]["bc_i22"]
    core = [86.4, 69.12, 544.32, 1227.0]
    for p in [r["u_bin"], r["u_st"]] + r.get("u_st_more", []):
        assert abs(p[0] / C.GRID - round(p[0] / C.GRID)) < 1e-6 and abs(p[1] / C.GRID - round(p[1] / C.GRID)) < 1e-6
        assert not (core[0] - 4.32 < p[0] < core[2] + 4.32 and core[1] - 4.32 < p[1] < core[3] + 4.32)


def test_plan_stations_are_counted_first_and_long_first_leg_gets_a_station():
    st = [dict(conn="bus:nb_i22", from_um=[228.552, 0.0], to_um=[77.856, 919.207], regs_um=[[34.56, 190.08], [34.56, 578.88]])]
    r = C.build(_plan(BANDS, st), {}, {}, set(), {"nb_i22"})["cbn_qx"]["nb_i22"]
    assert r["plan_stations"] == 2 and r["equal_hop_um"] <= 405 and r["u_bin"][0] == 302.4


def test_vertical_first_route_when_the_horizontal_first_leg_runs_on_a_core_edge():
    # plan station in the channel, tap on the core E edge: the horizontal-first L puts its vertical on the core edge (illegal), vertical-first is legal
    st = [dict(conn="bus:bc_i22", from_um=[138.0, 0.0], to_um=[544.224, 688.46], regs_um=[[587.52, 95.04]])]
    r = C.build(_plan({"bc_i22": dict(rect_um=[17.28, 17.28, 110.784, 75.6])}, st), {}, {}, set(), {"bc_i22"})["cbn_qx"]["bc_i22"]
    assert r["equal_hop_um"] <= 405 and r["plan_stations"] == 1


def test_u_bin_outside_a_hard_core_ring_band():
    p = _plan({"bc_i22": dict(rect_um=[100.0, 17.28, 190.0, 69.12])})
    p["partition_types"]["cbn_qx"]["hard_cores"].append(dict(inst="cl_bc_i22", origin_um=[100.0, 17.28], outline_um=[90.0, 51.84]))
    st = [dict(conn="bus:bc_i22", from_um=[638.0, 0.0], to_um=[544.224, 688.46], regs_um=[[587.52, 95.04]])]
    p["partition_types"]["cbn_qx"]["internal_stations"] = st
    r = C.build(p, {}, {}, set(), {"bc_i22"})["cbn_qx"]["bc_i22"]
    assert r.get("u_bin_outside_band") is True and r["equal_hop_um"] <= 405
