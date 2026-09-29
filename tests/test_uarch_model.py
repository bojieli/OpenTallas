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


def test_hbm_gpu_floorplans_legal():
    for m in ("qwen", "v41"):
        fp = json.loads((ROOT / f"results/floorplan/hbm_gpu/{m}_hbm_die.json").read_text())
        assert fp["legality"]["legal"] and fp["fits"]
        assert fp["macro_counts"]["ot_hbm3e_phy"] == 4
