"""The Qwen3-8B architecture budget (tools/arch_budget_qwen3.py): workload
arithmetic, budget derivation, the committed record, and the PERFORMANCE GATE
(the RTL-calibrated sequencer model at shipped shapes against the budget)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_budget_qwen3 as A  # noqa: E402

REC = ROOT / "results/arch/qwen3_budget.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


@pytest.fixture(scope="module")
def fresh():
    return A.evaluate()


def test_workload_counts():
    wl = A.workload(2048)
    L, H, NH, KV, HD, FF, V = (A.Q[k] for k in ("L", "H", "NH", "KV", "HD", "FF", "V"))
    layer = (NH + 2 * KV) * HD * H + H * NH * HD + 2 * FF * H + H * FF
    assert wl["weight_macs"] == L * layer + V * H == 7_568_097_280
    assert wl["attention_macs"] == 2 * L * NH * HD * 2048
    assert wl["bytes"]["kv_read"] == 2 * L * KV * HD * 2048 * 2 == 301_989_888
    assert A.workload(8192)["bytes"]["kv_read"] == 4 * wl["bytes"]["kv_read"]
    assert A.kv_bytes(A.workload(8192), "fp8") == 603_979_776


def test_split_rule_matches_the_engine():
    # floor(G/S) tiles a round: 7,680 groups cannot tile S = 2048 in whole rounds
    s, rounds, kc = A.split_rounds(6144, 4096, 7680)
    assert (7680 // s) * rounds >= 48
    # on the spec's 8,192 groups the sweep is at its ideal
    per_layer, head = A.matrices()
    tiled = A.Q["L"] * sum(A.mv_cycles(n, k, 8192)[0] for n, k in per_layer.values()) + \
        sum(A.mv_cycles(n, k, 8192)[0] for n, k in head.values())
    ideal = A.workload(2048)["weight_macs"] / (8192 * 16)
    assert tiled <= 1.001 * ideal
    # the ISA as built before the spec work (2-bit split) is several times off
    assert A.mv_cycles(24576, 4096, 7680, max_split=8)[0] >= 5 * A.mv_cycles(24576, 4096, 8192)[0]


def test_budget_design_point(rec):
    b = rec["budget"]
    assert b["context"] == 8192 and b["kv_format"] == "fp8"
    t = b["targets"]["8192/fp8"]
    assert b["target_cycles"] == max(round(b["weight_sweep_ideal_cycles"] / 0.55), round(t["kv_stream_cycles"] / 0.95))
    assert b["binding"] == "kv_stream"
    # BF16 KV at 8k is KV-bound at half the rate
    assert rec["budget"]["targets"]["8192/bf16"]["target_tokens_s"] < 0.55 * b["target_tokens_s"]


def test_area_ledger(rec):
    a = rec["area"]
    used = a["hbm_phy_mm2"] + a["kv_prefetch_buffer_mm2"] + a["drafter_rom_mm2"] + a["stream_unit_spill_mm2"] + \
        a["lane_copies_added"] * a["lane_copy_mm2"]
    assert used <= a["freed_sram_mm2"] + 0.1
    assert a["lane_multiplier_m"] == 1 + a["lane_copies_added"]


def test_record_is_current(rec, fresh):
    for key in ("budget", "requirements", "gap", "dflash", "hbm_requirements", "batch", "area", "rom_token"):
        assert json.loads(json.dumps(fresh[key], default=float)) == rec[key], key
    assert fresh["as_built_calibrated"]["8192"]["cycles"] == rec["as_built_calibrated"]["8192"]["cycles"]


def test_speculation(rec):
    d = rec["dflash"]
    assert d["tau_central"] == 4.1
    m = rec["area"]["lane_multiplier_m"]
    # with lane copies the ROM die gains; at m = 1 it does not at 8k
    assert d["rom"][f"8192/fp8/m{m}"]["best"]["speedup"] > 1.3
    assert d["rom"]["8192/fp8/m1"]["best"]["speedup"] <= 1.01
    assert all(v["speedup_at_tau_central"] > 3 for v in d["hbm"].values())


# The performance gate: the calibrated model replaying the program the core
# runs, at shipped shapes and the design context, must not regress past the
# ratchet, and the gap to the budget target is reported.  Lower RATCHET as
# blocks land; the gate is met when RATCHET <= the budget target.
RATCHET_8K = 174_856


def test_performance_gate(rec, fresh):
    cyc = fresh["as_built_calibrated"]["8192"]["cycles"]
    assert cyc <= RATCHET_8K, f"calibrated token {cyc} cycles regressed past the ratchet {RATCHET_8K}"
    target = rec["budget"]["target_cycles"]
    print(f"calibrated {cyc} cycles vs budget target {target}: {cyc / target:.2f}x")
