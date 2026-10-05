"""Microarchitecture model: record consistency and the design decisions it supports."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/v41_rom.json"


def _rows():
    return {r["design"]: r for r in json.loads(REC.read_text())["rows"]}


def test_wire_cycles_matches_w1_crossing_rule():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import uarch_model as U
    # W1: VM -> farthest expert strip 20,465.5 um = 19 one-way cycles at 920 ps / 60 ps uncertainty
    assert U.wire_cycles(20465.5, 1e12 / 920) == 19
    assert U.wire_cycles(1340.0, 1e12 / 920) == 2


def test_record_orders_designs_as_documented():
    r = _rows()
    assert r["as_built"]["tokens_s"] < 100
    assert r["spec_contiguous"]["tokens_s"] < r["spec_striped"]["tokens_s"] < r["proposal"]["tokens_s"]
    # striping alone does not fit the ROM-field strips; the proposal does
    assert not r["spec_striped"]["area"]["fits"]
    assert r["proposal"]["area"]["fits"]
    # K-split rows beat whole-row ownership (W10's measured whole-row reads and expert collisions)
    assert r["proposal_whole"]["tokens_s"] < r["proposal_ksplit"]["tokens_s"]
    # the proposal's VM ports are routable over the ROM field
    assert r["proposal"]["network"]["column_utilisation"] < 1.0


def test_sweep_rejects_unroutable_ports():
    s = json.loads(REC.read_text())["sweep"]
    for row in s:
        if row["vm_read_elems"] >= 128:
            assert row["network"]["column_utilisation"] > 1.0


@pytest.mark.skipif(not os.environ.get("OT_SLOW"), reason="re-prices the full DAG (~2 min); set OT_SLOW=1")
def test_proposal_reprices_to_record():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import copy
    import uarch_model as U
    got = U.evaluate(copy.deepcopy(U.PRESETS["proposal"]), 1048576)
    assert abs(got["tokens_s"] - _rows()["proposal"]["tokens_s"]) < 1.0


def test_hbm_gpu_record_w13():
    rec = json.loads((ROOT / "results/uarch/hbm_gpu.json").read_text())
    r = {x["design"]: x for x in rec["rows"]}
    # the prefetching bulk copy hides the boundaries the additive form charges
    assert r["qwen_hbm_gpu"]["tokens_s"] >= r["qwen_hbm_gpu_derived_barrier_no_prefetch"]["tokens_s"]
    assert r["qwen_hbm_gpu"]["boundaries"] == 181
    for m in ("qwen", "v41"):
        d = rec["designs"][m]
        assert d["barrier"]["boundary_cycles"] < 200
        assert d["barrier"]["source"].startswith("results/floorplan/hbm_gpu/")
        assert d["die_fit"]["fits"]
        assert d["sm_count"] == 32
    # V4.1: the K-chain-aware chain with group-slot issue beats row-slot; speculation beats AR on both dies
    assert r["v41_hbm_gpu_groupslot"]["tokens_s"] > r["v41_hbm_gpu_rowslot"]["tokens_s"]
    sp = {x["design"]: x for x in rec["speculation"]}
    assert sp["qwen_hbm_dflash_best"]["tokens_s"] > sp["qwen_hbm_ar"]["tokens_s"]
    assert sp["v41_hbm_mtp"]["tokens_s"] > sp["v41_hbm_ar"]["tokens_s"]


def test_hbm_gpu_floorplans_legal():
    for m in ("qwen", "v41"):
        fp = json.loads((ROOT / f"results/floorplan/hbm_gpu/{m}_hbm_die.json").read_text())
        assert fp["legality"]["legal"] and fp["fits"]
        assert fp["macro_counts"]["ot_hbm3e_phy"] == 4


def test_rom_field_power_is_the_measured_pair():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import uarch_model as U
    pw = _rows()["proposal"]["power"]
    f = _rows()["proposal"]["clock_hz"]
    N = U.PAIR_W["placed_pairs"]
    # W18: 83.5 mW idle with the clock running, 0.22 mW with the per-pair ICG, at 1.087 GHz (scaled to the clock)
    assert abs(pw["field"]["clock_w"] - N * (0.0835 - 0.00022) * f / 1.087e9) < 0.5
    assert abs(pw["field"]["leakage_w"] - N * 0.00022) < 0.01
    # ungated, the field clock alone exceeds the liquid-cooling budget: the per-pair ICG is a requirement
    assert pw["field"]["clock_w"] > U.COOLING_LIMIT_W
    assert not pw["ungated"]["fits_cooling_saturated"]
    assert pw["per_pair_icg"]["fits_cooling_saturated"]
    assert pw["per_pair_icg"]["static_w"] < pw["ungated"]["static_w"] / 10
    # a whole-field op busies every pair it holds: the instantaneous peak is a PDN load, above the thermal budget
    assert pw["field"]["peak_busy_pairs"] <= N
    assert pw["per_pair_icg"]["peak_w_saturated"] > pw["per_pair_icg"]["total_w_saturated"]


def test_power_clock_sensitivity_scales_dynamic_power():
    s = json.loads(REC.read_text())["power_clock_sensitivity"]
    base = _rows()["proposal"]
    prev_t, prev_clk = base["tokens_s"], base["power"]["field"]["clock_w"]
    for r in s["rows"]:
        # a faster clock buys less than the clock ratio (wires, HBM and collectives keep their times)
        assert prev_t < r["tokens_s"] < base["tokens_s"] * r["clock_hz"] / base["clock_hz"]
        assert r["power"]["field"]["clock_w"] > prev_clk
        prev_t, prev_clk = r["tokens_s"], r["power"]["field"]["clock_w"]


def test_switch_rings_fit_the_refit_spare_slots():
    sr = _rows()["proposal"]["power"]["switch_rings"]
    assert 23.0 < sr["switch_ring_mm2"] < 25.0          # W18: 5% of the cluster area for a 10 mV budget
    assert sr["fits_spare_slots"] and sr["pair_slots_needed"] <= sr["pair_slots"]
