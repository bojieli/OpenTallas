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
RATCHET_8K = 123_301


def test_performance_gate(rec, fresh):
    cyc = fresh["as_built_calibrated"]["8192"]["cycles"]
    assert cyc <= RATCHET_8K, f"calibrated token {cyc} cycles regressed past the ratchet {RATCHET_8K}"
    target = rec["budget"]["target_cycles"]
    print(f"calibrated {cyc} cycles vs budget target {target}: {cyc / target:.2f}x")


def test_layer_chain_is_under_the_kv_floor(rec, fresh):
    """The per-layer compute chain at the spec configuration fits under the
    per-layer share of the FP8 KV stream: the ROM token is KV-bound at 8k."""
    lc = fresh["as_built_calibrated"]["8192"]["layer_chain"]
    assert lc["cycles"] == sum(s["cycles"] for s in lc["stages"])
    kv = rec["rom_token"]["8192/fp8"]["kv_stream_cycles"]
    assert lc["cycles"] < kv / rec["shape"]["L"]
    assert fresh["as_built_calibrated"]["8192"]["cycles"] <= rec["budget"]["target_cycles"]


def test_production_power_basis(rec):
    """Power in the two sourced scenarios: per-token energy is the sum of its components, the provisioned power is
    1.2 x worst / (VR x PSU), every point sits under the saturated worst case, and the ROM die beats the HBM
    comparator per token with KV read from HBM on both."""
    pp = rec["power_production"]
    P = pp["inputs"]
    assert set(pp["scenarios"]) == set(A.SCENARIOS)
    for s, body in pp["scenarios"].items():
        w = body["worst_case"]
        assert abs(w["provisioned_w"] - 1.2 * w["package_w"] / (P["vr"] * P["psu"])) < 1.0
        for sc in body["rom"].values():
            assert sc["die_w"] <= w["die_w"] and sc["package_w"] <= w["package_w"]
            assert abs(sum(sc["die_components_mj_per_token"].values()) - sc["die_energy_per_token_mj"]) < 0.01
            assert abs(sc["die_energy_per_token_mj"] + sc["stack_energy_per_token_mj"] - sc["energy_per_token_mj"]) < 0.01
        for sc in body["hbm_comparator"].values():
            assert abs(sum(sc["die_components_mj_per_token"].values()) - sc["die_energy_per_token_mj"]) < 0.01
            assert sc["die_components_mj_per_token"]["hbm_controller_phy_io"] > 0     # the die's HBM share
        assert body["ratios_batch1"]["hbm_over_rom"] > body["ratios_batch1"]["hbm_rom_format_over_rom"] > 1
        assert body["rom"]["ar_batch1"]["die_components_mj_per_token"]["hbm_controller_phy_io"] > 0


def test_power_reads_the_sourced_scenarios_and_matches_their_record(rec):
    """Single source of truth: every power input is tools/power_scenarios' (no 408 W cooling, no 0.8-inside-13.1
    HBM split, W4A8 priced per MAC not per operation), and the ROM points this tool prices are the ones
    configs/hardware/power_scenarios.json pins -- so the two records agree to rounding."""
    import power_scenarios as PS
    cfg = PS.load_cfg()
    P = rec["power_production"]["inputs"]
    assert P["hbm_pj_per_bit"] == PS.hbm_split(cfg)
    assert P["hbm_pj_per_bit"]["die"] == pytest.approx(10.19) and P["hbm_pj_per_bit"]["stack"] == pytest.approx(3.45)
    assert P["mac_pj"]["B_proposed_production"]["w4a8"] == 0.45 >= 2 * 0.09   # >= two operations a MAC
    assert P["cooling"]["air"]["die_limit_w"] == pytest.approx(PS.cooling_w(cfg, "air", 1))
    assert rec["power"]["cooling"]["air"]["die_limit_w"] == pytest.approx(549.47, abs=0.01)
    for name in ("COOLING_W", "MAC_POWER_SHARE", "HBM_IDLE_W_PER_STACK", "GPU_PJ_PER_MAC", "E_SRAM_PER_BYTE"):
        assert not hasattr(A, name), name
    pinned = cfg["design_points"]["qwen3"]
    dp = rec["power_production"]["design_point"]
    for k in ("ar_batch1", "dflash"):
        assert {f: dp[k][f] for f in pinned[k]} == pinned[k], k
    assert {f: dp["area_mm2"][f] for f in pinned["area_mm2"]} == pinned["area_mm2"]
    assert dp["clock_hz"] == pinned["clock_hz"]
    ps = json.loads(PS.OUT.read_text())
    for s in A.SCENARIOS:
        mine = rec["power_production"]["scenarios"][s]["rom"]
        theirs = ps["scenarios"][s]["qwen3_8b_rom_8k"]
        for k, t in (("ar_batch1", "ar_batch1"), (f"dflash_tau{A.TAU_CENTRAL}_block3", "dflash")):
            assert mine[k]["energy_per_token_mj"] == pytest.approx(theirs[t]["energy_per_token_mj"], rel=1e-4)
            assert mine[k]["die_w"] == pytest.approx(theirs[t]["die_w_at_design_rate"], abs=0.1)
            assert mine[k]["cooling"]["air"]["capped_tokens_s"] == pytest.approx(theirs[t]["capped_rate"], abs=0.1)


def test_power_budget_is_the_die_limit_less_the_non_mac_power(rec):
    """The MAC energy that fits is (die limit - static - non-MAC dynamic x rate) / MAC rate; scenario A's lane is
    hotter than B's and caps lower; with free MACs the autoregressive die is still over the limit."""
    pw = rec["power"]
    lim = pw["cooling"]["air"]["die_limit_w"]
    for key, pt in pw["points"].items():
        d = pt["at"]["design"]
        assert d["die_w_without_macs"] == pytest.approx(pt["die_static_w"] + pt["die_non_mac_dynamic_mj_per_token"]
                                                        / 1e3 * d["tokens_s"], abs=0.2)
        assert d["pj_per_mac_that_fits"]["air"] == pytest.approx((lim - d["die_w_without_macs"]) / d["mac_rate_per_s"]
                                                                 * 1e12, abs=2e-3)
        la = pt["lanes"]
        assert la["A_measured_implementation"]["cooling"]["air"]["capped_tokens_s"] <= \
            la["B_proposed_production"]["cooling"]["air"]["capped_tokens_s"] <= d["tokens_s"]
    assert pw["points"]["ar_batch1"]["at"]["design"]["pj_per_mac_that_fits"]["air"] < 0
    assert pw["points"]["ar_batch1"]["rate_cap_with_free_macs"]["air"] < pw["points"]["ar_batch1"]["at"]["design"]["tokens_s"]


UTIL = ROOT / "results/arch/qwen3_utilization.json"


def test_utilization_gate_covers_every_block_and_is_current(fresh):
    """The utilisation gate (user, before the core P&R): every block of both
    designs has a peak, a demand and a verdict in four scenarios; nothing is
    left OVER-PROVISIONED without its right-sizing applied; right-sizing the
    HBM comparator's lanes slows no scenario; the record is current."""
    u = json.loads(UTIL.read_text())
    assert u == json.loads(json.dumps(A.utilization(fresh, fresh["clock_hz"]), default=float))
    assert len(u["rom"]) == 4 and all(len(sc["blocks"]) >= 12 for sc in u["rom"].values())
    for v in u["verdicts"]:
        assert v["verdict"].startswith(("RIGHT-SIZED", "JUSTIFIED")) or "(applied)" in v["verdict"]
    # the comparator's lanes never bind at 8k; the rejected smaller array slows the 2k batch rows
    spec = u["hbm"][f"{A.LANES_HBM}_lanes"]["scenarios"]
    assert all(sc["slowed_by_lanes"] == 0 for k, sc in spec.items() if not k.startswith("ctx2048"))
    cand = u["hbm"][f"{A.GROUPS_HBM_CANDIDATE * A.W}_lanes"]["scenarios"]
    assert all(cand[k]["slowed_by_lanes"] == 0 for k in cand if not k.startswith("ctx2048"))
    k2 = next(k for k in cand if k.startswith("ctx2048"))
    assert cand[k2]["step_cycles"] > spec[k2]["step_cycles"] * 1.2
    # the stream unit is the smallest width that keeps the single user at the KV floor
    ar = u["rom"]["ar_batch1"]["step_cycles"]
    assert u["su_width_sweep_cycles"]["512"] > ar >= u["su_width_sweep_cycles"]["1024"]
