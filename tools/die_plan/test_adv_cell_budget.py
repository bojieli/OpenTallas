"""PRECHECK-CELLCAP: adv_cell_budget slot terms calibrated on the S81 kv_leaf t2 bound shell (epyc11 whole3/stat_mapped3.txt, 11-23)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_cell_budget as CB  # noqa: E402
import plan_advisory as PA  # noqa: E402

# the old-plan t2 shell: 111 ft stations (count x width) and 15 ft landings + 4 W=2 monitors (width, padded flops)
T2_STATIONS = [(34, 276), (27, 70), (16, 668), (12, 597), (9, 1104), (5, 594), (4, 265), (4, 2)]
T2_BANDS = [(1104, 5760)] * 2 + [(597, 3200)] * 4 + [(668, 3520)] + [(276, 1600)] * 5 + [(70, 640)] * 3 + [(2, 320)] * 4
T2_MEASURED_STATIONS, T2_MEASURED_LANDINGS, T2_MEASURED_TOTAL = 86_374, 186_608, 658_649


def t2_type(**kw):
    t = {"outline_um": [4380.48, 1226.88],
         "ft_slots": [{"name": f"ft{i}", "width": w, "stations": 1} for i, (n, w) in enumerate(T2_STATIONS) for _ in range(n)],
         "clock": {"landing_contract": {"bands": {f"b{i}": {"width": w, "padded_data_storage_flops": p, "ring_place": "ff"}
                                                 for i, (w, p) in enumerate(T2_BANDS)}}},
         "contents": [{"inst": "u_lf", "module": "ot_s81sl_kv_leaf"}]}
    t.update(kw)
    return t


def test_t2_slot_terms_within_two_percent_of_measured():
    ov = CB.overhead(t2_type())
    assert abs(ov["ft_stations"] / T2_MEASURED_STATIONS - 1) < 0.02
    assert abs(ov["landings"] / T2_MEASURED_LANDINGS - 1) < 0.02
    assert ov["n_landings"] == 19


def test_t2_whole_type_projection_within_15_percent_and_flagged():
    mods = CB.load_modules()
    r = CB.project("ot_s81sl_kv_leaf__t2", t2_type(), mods)
    assert abs(r["est"] / T2_MEASURED_TOTAL - 1) < 0.15
    assert r["est"] > CB.FLAG_SYNTH
    kvx = CB.project("ot_s81sl_kv_leaf__t2", t2_type(verilog_defines=["OT_S81_KVLEAF_EXIT_RELAYS"]), mods)
    assert abs(kvx["est"] / 517_668 - 1) < 0.15        # measured with hard exit relays


def test_findings_name_slot_terms_and_summary():
    raw = {"die": {"name": "s81"}, "partition_types": {"ot_s81sl_kv_leaf__t2": t2_type(), "small": {"outline_um": [10, 10]}},
           "partitions": [{"type": "ot_s81sl_kv_leaf__t2"}, {"type": "small"}]}
    out = CB.findings(raw, "p.json", cells_cache={"cells": {}})
    assert out[0].startswith("WARN ADV-CELL-BUDGET ot_s81sl_kv_leaf__t2: projected ")
    assert "landings" in out[0] and "ft stations" in out[0] and "400,000 cap" in out[0]
    assert out[-1].startswith("WARN ADV-CELL-BUDGET summary: 1 of 2 soft types")


def test_alternating_polarity_drops_the_inverter():
    t = {"ft_slots": [{"width": 100, "stations": 10}]}
    assert CB.overhead(t)["ft_stations"] == 2000
    assert CB.overhead(dict(t, dly_alt_pol=True))["ft_stations"] == 1150
    assert CB.overhead(dict(t, verilog_defines=["OT_ST_QNALT"]))["ft_stations"] == 1150


def test_internal_station_bits_fall_back_to_bus_width_and_relays():
    t = {"buses": [{"name": "x", "width": 64}],
         "internal_stations": [{"conn": "bus:x", "regs_um": [[0, 0], [1, 1]]}, {"conn": "core:a|core:b", "regs_um": [[0, 0]]},
                               {"bits": 8, "regs_um": [[0, 0]] * 3}],
         "relay_depth": [{"bits": [0, 9], "D": 2}]}
    ov = CB.overhead(t)
    assert ov["internal_stations"] == 2 * (128 + 24) and ov["unsized_ist"] == 1 and ov["relays"] == 40


def test_narrow_ring_small_bands_are_lite():
    bands = {"a": {"width": 1, "padded_data_storage_flops": 320}, "b": {"width": 258, "padded_data_storage_flops": 1600, "ring_place": "ff"}}
    t = {"clock": {"landing_ring_narrow": True, "landing_contract": {"bands": bands}}}
    assert CB.overhead(t)["landings"] == 80 + 7500
    t["clock"]["landing_ring_narrow"] = False
    assert CB.overhead(t)["landings"] == 660 + 7500


def test_kit_floor_ages_out_and_type_cells_ignored_with_cores():
    now = time.time()
    cache = {"x__cl1234567": {"last": {"cells": 380_000, "t0": now - 3600, "stage": "geom"}},
             "y": {"last": {"cells": 5_000_000, "t0": now - 5 * 86400}}}       # project() takes the die's {type: record}
    mods = {"modules": {}, "types": {}}
    assert CB.project("x__cl7654321", {}, mods, cache, now)["est"] == 380_000          # base-type kit, fresh
    assert CB.project("y", {}, mods, cache, now)["est"] == 0                            # 5-day-old flat kit ignored
    assert CB.project("z", {"cells": 900_000, "hard_cores": [{"inst": "c"}]}, mods, cache, now)["est"] == 0
    assert CB.project("z", {"cells": 360_000}, mods, cache, now)["est"] == 360_000


def test_registered_in_plan_advisory():
    assert ("CELL-BUDGET", "adv_cell_budget") in PA.CHECKS
    raw = {"die": {"name": "s81"}, "partition_types": {"t": t2_type()}, "partitions": [{"type": "t"}]}
    out = PA.run(raw, "p.json", checks=("CELL-BUDGET",), cells_cache={"cells": {}})
    assert out and all(x.startswith("WARN ADV-CELL-BUDGET") for x in out)
