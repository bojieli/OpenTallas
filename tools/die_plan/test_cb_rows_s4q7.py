"""QC-CB-GEN-1115: cb_rows_s4q7.py (one ring per strip, hop>600 station rows) and the gen_cb_strip.py face-aware hop."""
import math
import cb_rows_s4q7 as R


def test_station_row_equal_hops_on_the_route_and_row_grid():
    t = dict(internal_stations=[dict(conn="bus:bc_i10", from_um=[670.992, 0.0], to_um=[544.224, 1915.34], regs_um=[[673.92, 1019.52]],
                                     bits=517, note="x, hops [1022.4, 1025.5]; y")])
    (conn, nr, n0, n1, hop), = R.stations(t, "t", {})
    assert (conn, n0, n1) == ("bus:bc_i10", 1, 5) and hop < 405
    assert all(abs(y / R.GRID - round(y / R.GRID)) < 1e-6 for _, y in nr["regs_um"])
    assert R.stations(t, "t", {"types": {"t": {"bc_i10": {}}}}) == []                      # a sidecar u_bin row already splits it
    t["internal_stations"][0]["note"] = "hops [410.0]"
    assert R.stations(t, "t", {}) == []                                                    # 405-600 um stays in the baseline ledger


def test_reshape_one_ring_per_strip():
    bands = {"na_i22": dict(rect_um=[19.44, 17.28, 71.28, 106.1], ring_width=576), "bc_i22": dict(rect_um=[19.44, 108.3, 71.28, 214.1], ring_width=576),
             "nb_i22": dict(rect_um=[73.44, 17.28, 492.48, 30.24], ring_width=576)}
    t = dict(outline_um=[1235.52, 2540.16], hard_cores=[dict(inst="u_t22", origin_um=[86.4, 69.12], outline_um=[457.92, 1157.76])],
             buses=[dict(name="na_i22", window_um=[4.32, 93.168]), dict(name="bc_i22", window_um=[94.128, 183.376]),
                    dict(name="nb_i22", window_um=[184.336, 272.768])], clock=dict(landing_contract=dict(bands=bands)))
    rows, rep = R.reshape(t, "t")
    r = {k.split(".")[-1]: v["rect_um"] for k, v in rows.items()}
    assert r["na_i22"][2] <= 82.08 and r["bc_i22"][3] <= 69.12 - 4.32 and r["nb_i22"][3] <= 69.12 - 4.32
    assert r["bc_i22"][2] < r["nb_i22"][0]                                                  # one ring per strip, no overlap
    for k, v in rows.items():
        assert 0.4 <= 5400 / 576 * 576 / v["area_reserve_um2"] <= 0.6 and v["max_pin_to_band_hop_um"] < 403
