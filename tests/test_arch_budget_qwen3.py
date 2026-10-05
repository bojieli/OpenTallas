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
    assert abs(b["target_cycles"] - max(b["weight_sweep_ideal_cycles"] / 0.55, t["kv_stream_cycles"] / 0.95)) <= 1
    assert b["binding"] == "kv_stream"
    # BF16 KV at 8k is KV-bound at half the rate
    assert rec["budget"]["targets"]["8192/bf16"]["target_tokens_s"] < 0.55 * b["target_tokens_s"]


def test_area_ledger(rec):
    """One die of the two-reticle package: every block, half of the 8-bit ROM, the lane copies and the slack add up
    to the reticle; the groups a die are the most its ROM feeds at 8 bits (the next step of 512 is not fed)."""
    a = rec["area"]
    used = a["compute_mm2"] + a["interconnect_mm2"] + a["overhead_mm2"] + a["hbm_phy_mm2"] + a["ucie_phy_mm2"] + \
        a["kv_prefetch_buffer_mm2"] + a["stream_unit_spill_mm2"] + a["target_rom_mm2"] + a["drafter_rom_mm2"] + \
        a["lane_copies_added"] * a["lane_copy_mm2"]
    assert a["fits"] and used + a["slack_mm2"] == pytest.approx(a["die_mm2"], abs=0.05)
    assert 0 <= a["slack_mm2"] < a["lane_copy_mm2"]
    assert a["lane_multiplier_m"] == 1 + a["lane_copies_added"] == 5
    assert (a["dies"], a["groups_per_die"]) == (2, 6144) and rec["rom_design"]["groups"] == 2 * 6144
    assert a["rom_read"]["headroom"] >= 1 > a["rom_read"]["next_step_headroom"]
    assert a["package"]["hbm_stacks"] == 2 * a["stacks_per_die_by_beachfront"] == 8
    cap = rec["rom_capacity"]
    assert cap["weight_bits"] == 8 and a["package"]["target_rom_mm2"] == pytest.approx(cap["target_mm2"], abs=0.01)


def test_die_split_and_ucie_exchange(rec):
    """TP-2: every layer is split across both dies; the token's exchanges are 2 a layer + 1, each an H-element FP32
    partial, their latency (and the embedding-row handoff) on the chain, from the configured link; the calibrated
    chain is one die's slice replayed at 6,144 groups plus the INT8 scale multiply and the exchanges."""
    ds, x = rec["die_split"], rec["ucie"]["exchange"]
    assert len(ds["dies"]) == 2 and ds["exchanges_per_token"] == x["exchanges_per_token"] == 2 * rec["shape"]["L"] + 1
    assert x["bytes_per_exchange_per_direction"] == 4 * rec["shape"]["H"]          # FP32 partials
    assert rec["ucie"]["link"]["hop_latency_s"] == 1e-8
    assert x["cycles_per_token"] == 1419 and x["exchange_cycles"] == 1407
    for ch in rec["dependency_chain"].values():
        assert ch["ucie_exchange_cycles"] == x["cycles_per_token"]
    ab = rec["as_built_calibrated"]["8192"]
    assert ab["groups"] == 6144 and ab["scale_multiply_cycles"] == 5 * (6 * rec["shape"]["L"] + 1)
    assert ab["cycles"] == ab["sequencer_cycles"] + ab["scale_multiply_cycles"] + x["cycles_per_token"] == 101037
    alt = rec["layer_cut_alternative"]
    assert alt["ar_tokens_s"] < 0.6 * rec["power"]["points"]["ar_batch1"]["at"]["design"]["tokens_s"]


def test_o4_frozen_study_has_the_same_configuration(rec):
    """The frozen O4 choice stays the configuration; the current RTL latency
    replay supersedes that study's rates by charging KV-sourced post-tree stages."""
    o4 = json.loads((ROOT / "results/arch/qwen3_8bit_design.json").read_text())
    o4 = o4["configurations"]["O4_two_reticles_one_package"]
    pp = rec["power_production"]["scenarios"]
    assert pp["B_proposed_production"]["rom"]["ar_batch1"]["step_cycles"] == rec["as_built_calibrated"]["8192"]["cycles"]
    # The current replay also charges the RTL's ceil(log2(6144)) split tree.
    assert rec["as_built_calibrated"]["8192"]["cycles"] - o4["performance"]["ar_step_cycles"] == 1228
    best = o4["performance"]["dflash"]["best"]
    assert pp["B_proposed_production"]["rom"][f"dflash_block{best['block']}"]["step_cycles"] - best["step_cycles"] == 410


def test_record_is_current(rec, fresh):
    for key in ("budget", "requirements", "gap", "dflash", "hbm_requirements", "batch", "area", "rom_token"):
        assert json.loads(json.dumps(fresh[key], default=float)) == rec[key], key
    assert fresh["as_built_calibrated"]["8192"]["cycles"] == rec["as_built_calibrated"]["8192"]["cycles"]


def test_speculation(rec):
    """DFlash is read from the serial step record, never restated: no tau constant or acceptance histogram in the
    tool, and the design point's block, tokens a step, step cycles and MACs are the record's."""
    for name in ("TAU_CENTRAL", "ACCEPT_HIST", "tokens_per_step", "rom_block_sweep", "DFLASH_SLOTS"):
        assert not hasattr(A, name), name
    d = rec["dflash"]
    timing = json.loads((ROOT / d["source"]).read_text())
    m = rec["area"]["lane_multiplier_m"]
    for key, r in d["rom"].items():
        want = timing["rom"][key]["best"]
        assert {k: want[k] for k in r["best"]} == r["best"], key
    best = d["rom"][f"8192/fp8/m{m}"]["best"]
    assert d["tau_design_point"] == best["tokens_per_step"] and d["block_design_point"] == best["block"]
    # the draft phase is on the step: step = draft + verify + commit, and its MACs are charged
    assert best["step_cycles"] == best["draft_cycles"] + best["verify_cycles"] + best["commit_cycles"]
    assert best["draft_weight_macs"] > 0 and best["draft_attention_macs"] > 0
    assert best["macs_per_step"] == sum(best[k] for k in ("draft_weight_macs", "draft_attention_macs",
                                                          "verify_weight_macs", "verify_attention_macs"))
    # with lane copies the ROM die gains; at m = 1 it does not at 8k
    assert best["speedup"] > 1.3
    assert d["rom"]["8192/fp8/m1"]["best"]["speedup"] <= 1.01
    assert all(v["speedup"] > 2 for v in d["hbm"].values())
    assert all(v["tokens_s"] == timing["hbm"][f]["best"]["tokens_s"] for f, v in d["hbm"].items())


# The performance gate: the calibrated model replaying the program the core
# runs, at shipped shapes and the design context, must not regress past the
# ratchet, and the gap to the budget target is reported.  Lower RATCHET as
# blocks land; the gate is met when RATCHET <= the budget target.
# The 868-cycle correction is a model bug fix: the RTL uses $clog2(G), while
# the former replay used floor(log2(G)) at G=6144.  It does not mark a slower RTL.
RATCHET_8K = 101_037


def test_performance_gate(rec, fresh):
    cyc = fresh["as_built_calibrated"]["8192"]["cycles"]
    assert cyc <= RATCHET_8K, f"calibrated token {cyc} cycles regressed past the ratchet {RATCHET_8K}"
    target = rec["budget"]["target_cycles"]
    print(f"calibrated {cyc} cycles vs budget target {target}: {cyc / target:.2f}x")


def test_the_package_token_is_compute_bound(rec, fresh):
    """On 8 stacks the FP8 KV stream is under the calibrated chain at 8k: the package's autoregressive token is bound
    by its compiled chain (with the UCIe exchanges), which is over the budget target (the KV stream over 95% of the
    token) -- the performance gate is open, by less than 10%."""
    lc = fresh["as_built_calibrated"]["8192"]["layer_chain"]
    assert lc["cycles"] == sum(s["cycles"] for s in lc["stages"])
    kv = rec["rom_token"]["8192/fp8"]["kv_stream_cycles"]
    cyc = fresh["as_built_calibrated"]["8192"]["cycles"]
    assert cyc > kv
    assert rec["budget"]["target_cycles"] < cyc < 1.1 * rec["budget"]["target_cycles"]


def test_production_power_basis(rec):
    """Power in the two sourced scenarios: per-token energy is the sum of its components, the provisioned power is
    1.2 x worst / (VR x PSU), every point sits under the saturated worst case, and the ROM die beats the HBM
    comparator per token with KV read from HBM on both."""
    pp = rec["power_production"]
    P = pp["inputs"]
    assert set(pp["scenarios"]) == set(A.SCENARIOS)
    for s, body in pp["scenarios"].items():
        w = body["worst_case"]
        assert abs(w["provisioned_w_per_die"] - 1.2 * w["package_w"] / w["dies"] / (P["vr"] * P["psu"])) < 1.0
        for sc in body["rom"].values():
            assert sc["die_w"] <= w["die_w"] and sc["package_w"] <= w["package_w"]
            assert abs(sum(sc["die_components_mj_per_token"].values()) - sc["die_energy_per_token_mj"]) < 0.01
            assert abs(sc["die_energy_per_token_mj"] + sc["stack_energy_per_token_mj"] - sc["energy_per_token_mj"]) < 0.01
        for sc in body["hbm_comparator"].values():
            assert abs(sum(sc["die_components_mj_per_token"].values()) - sc["die_energy_per_token_mj"]) < 0.01
            assert sc["die_components_mj_per_token"]["hbm_controller_phy_io"] > 0     # the die's HBM share
        assert body["ratios_batch1"]["hbm_over_rom"] > 1
        assert all(sc["weight_format"] == "rom_format_int8" for sc in body["hbm_comparator"].values())
        assert body["rom"]["ar_batch1"]["die_components_mj_per_token"]["hbm_controller_phy_io"] > 0


def test_cooling_capped_rom_over_hbm_rate_ratio(rec, fresh):
    """Compare the two-reticle ROM and matched INT8 HBM packages at the same cooling class."""
    for scenario in ("A_measured_implementation", "B_proposed_production"):
        saved = rec["power_production"]["scenarios"][scenario]
        calculated = fresh["power_production"]["scenarios"][scenario]
        ratios = saved["ratios_batch1"]["rom_over_hbm_capped_rate"]
        assert ratios == calculated["ratios_batch1"]["rom_over_hbm_capped_rate"]
        assert set(ratios) == {"liquid", "air"}
        for cooling in ("liquid", "air"):
            rom = saved["rom"]["ar_batch1"]["cooling"][cooling]["capped_tokens_s"]
            hbm = saved["hbm_comparator"]["batch1"]["cooling"][cooling]["capped_tokens_s"]
            assert ratios[cooling] == round(rom / hbm, 4)
            assert rom <= saved["rom"]["ar_batch1"]["tokens_s"]
            assert hbm <= saved["hbm_comparator"]["batch1"]["tokens_s"]


def test_power_reads_the_sourced_scenarios_and_matches_their_record(rec):
    """Single source of truth: every power input is tools/power_scenarios' (no 408 W cooling, no 0.8-inside-13.1
    HBM split, W4A8 priced per MAC not per operation), and the ROM points this tool prices are the ones
    configs/hardware/power_scenarios.json pins -- so the two records agree to rounding."""
    import power_scenarios as PS
    cfg = PS.load_cfg()
    P = rec["power_production"]["inputs"]
    assert P["hbm_pj_per_bit"] == PS.hbm_split(cfg)
    assert P["hbm_pj_per_bit"]["die"] == pytest.approx(10.19) and P["hbm_pj_per_bit"]["stack"] == pytest.approx(3.45)
    assert P["mac_pj"]["B_proposed_production"]["fp8"] == 0.59        # the 8-bit weight's MAC: BF16 mult + FP32 add
    assert P["cooling"]["air"]["die_limit_w"] == pytest.approx(PS.cooling_w(cfg, "air", 2))
    assert rec["power"]["cooling_class"] == cfg["design_points"]["qwen3"]["cooling_class"] == "liquid"
    assert rec["power"]["cooling"]["air"]["die_limit_w"] == pytest.approx(374.6, abs=0.05)
    assert rec["power"]["cooling"]["liquid"]["die_limit_w"] == pytest.approx(474.6, abs=0.05)
    for name in ("COOLING_W", "MAC_POWER_SHARE", "HBM_IDLE_W_PER_STACK", "GPU_PJ_PER_MAC", "E_SRAM_PER_BYTE"):
        assert not hasattr(A, name), name
    pinned = cfg["design_points"]["qwen3"]
    dp = rec["power_production"]["design_point"]
    for k in ("ar_batch1", "dflash"):
        assert {f: dp[k][f] for f in pinned[k]} == pinned[k], k
    assert {f: dp["area_mm2"][f] for f in pinned["area_mm2"]} == pinned["area_mm2"]
    for f in ("clock_hz", "hbm_stacks", "dies_per_package", "weight_bits", "drafter_weight_bits", "weight_scale_bytes",
              "weight_mac_format"):
        assert dp[f] == pinned[f], f
    ps = json.loads(PS.OUT.read_text())
    for s in A.SCENARIOS:
        mine = rec["power_production"]["scenarios"][s]["rom"]
        theirs = ps["scenarios"][s]["qwen3_8b_rom_8k"]
        for k, t in (("ar_batch1", "ar_batch1"), (f"dflash_block{dp['dflash']['block']}", "dflash")):
            assert mine[k]["energy_per_token_mj"] == pytest.approx(theirs[t]["energy_per_token_mj"], rel=1e-4)
            assert mine[k]["die_w"] == pytest.approx(theirs[t]["die_w_at_design_rate"], abs=0.1)
            assert mine[k]["cooling"][theirs[t]["cooling_class"]]["capped_tokens_s"] == pytest.approx(theirs[t]["capped_rate"], abs=0.1)


def test_power_prices_the_serial_dflash_step(rec):
    """The DFlash power point is the step record's best ROM block: its rate is tokens a step over the serial step
    (the draft phase's time charged), and its MACs include the drafter's."""
    dfl = rec["dflash"]["rom"][f"8192/fp8/m{rec['area']['lane_multiplier_m']}"]["best"]
    dp = rec["power_production"]["design_point"]["dflash"]
    assert (dp["block"], dp["step_cycles"], dp["tokens_per_step"]) == (dfl["block"], dfl["step_cycles"],
                                                                       dfl["tokens_per_step"])
    pt = rec["power"]["points"]["dflash"]
    assert pt["macs_per_step"] == dfl["macs_per_step"]
    for s in A.SCENARIOS:
        r = rec["power_production"]["scenarios"][s]["rom"][f"dflash_block{dfl['block']}"]
        assert r["tokens_s"] == pytest.approx(dfl["tokens_s"], abs=0.1)


def test_power_budget_is_the_die_limit_less_the_non_mac_power(rec):
    """The MAC energy that fits is (die limit - static - non-MAC dynamic x rate) / MAC rate; scenario A's lane is
    hotter than B's and caps lower; with free MACs the autoregressive die is still over the limit."""
    pw = rec["power"]
    lim = pw["cooling"]["air"]["die_limit_w"]
    for key, pt in pw["points"].items():
        d = pt["at"]["design"]
        assert d["die_w_without_macs"] == pytest.approx(pt["die_static_w"] + pt["die_non_mac_dynamic_mj_per_token"]
                                                        / 1e3 * d["tokens_s"], abs=0.2)     # one die
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
    left OVER-PROVISIONED without its right-sizing applied; the HBM comparator
    keeps the ROM package's core; the record is current."""
    u = json.loads(UTIL.read_text())
    assert u == json.loads(json.dumps(A.utilization(fresh, fresh["clock_hz"]), default=float))
    assert len(u["rom"]) == 4 and all(len(sc["blocks"]) >= 12 for sc in u["rom"].values())
    for v in u["verdicts"]:
        assert v["verdict"].startswith(("RIGHT-SIZED", "JUSTIFIED")) or "(applied)" in v["verdict"]
    # the comparator (the ROM package's lanes) is never slowed by its lanes at 8k
    spec = u["hbm"][f"{A.LANES_HBM}_lanes"]["scenarios"]
    assert all(sc["slowed_by_lanes"] == 0 for k, sc in spec.items() if not k.startswith("ctx2048"))
    assert len(u["hbm"]) == 2
    # halving the stream unit slows the single user; the chain sets the step
    ar = u["rom"]["ar_batch1"]["step_cycles"]
    assert u["su_width_sweep_cycles"]["512"] > ar == u["su_width_sweep_cycles"]["1024"]
