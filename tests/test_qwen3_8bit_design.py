"""The 8-bit Qwen3-8B ROM design record (tools/qwen3_8bit_design.py): the evidence behind the adopted two-reticle
baseline.  The record priced 8-bit weights against the single-reticle 3.5-bit baseline of its day and is frozen (its
tool refuses to run against the O4 baseline HEAD implements); these tests hold its internal consistency, its fit
verdict, and that its O4 option is the design tools/arch_budget_qwen3.py now implements."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import qwen3_8bit_design as D  # noqa: E402

REC = ROOT / "results/arch/qwen3_8bit_design.json"
BUDGET = ROOT / "results/arch/qwen3_budget.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


@pytest.fixture(scope="module")
def base():
    return json.loads(BUDGET.read_text())


def test_tool_refuses_the_adopted_baseline():
    """The options were priced against one reticle; at HEAD the baseline is O4, so re-running would mislabel it."""
    with pytest.raises(SystemExit):
        D.evaluate()


def test_checks_pass(rec):
    assert rec["checks"] and all(rec["checks"].values()), rec["checks"]


def test_inventory_is_the_model(rec):
    inv = rec["inventory"]
    assert inv["target_params"] == inv["model_config_total_parameters"] == 8_190_735_360
    cap = rec["capacity"]["int8_per_channel"]
    assert cap["target"]["elements"] + cap["lm_head"]["elements"] + cap["embedding"]["elements"] + \
        cap["target"]["norms"] == inv["target_params"]
    assert cap["drafter"]["elements"] + cap["drafter"]["norms"] == inv["drafter_params"]


def test_capacity_rule(rec):
    """Two select cells an 8-bit weight against 7/6 at the HC1 3.5-bit mixture: 12/7 of the 3.5-bit ROM, plus the
    scales and BF16 norms."""
    cap = rec["capacity"]
    base = cap["baseline_3p5bit"]["target_mm2"]
    assert base == pytest.approx(261.98, abs=0.01)
    for fmt in ("int8_per_channel", "fp8_e4m3_block128"):
        got = cap[fmt]["target_total"]["mm2"]
        assert 12 / 7 * base < got < 12 / 7 * base * 1.001, (fmt, got)
    assert cap["storage_only_rom_mm2_target_int8"] > 815.0


def test_single_reticle_verdict(rec):
    v = rec["verdict"]
    c0 = rec["configurations"]["C0_single_reticle"]["ledger"]
    assert v["single_reticle_fits"] is False and v["deficit_mm2"] == c0["deficit_mm2"] > 0
    assert v["deficit_without_drafter_mm2"] > 0
    assert v["fits_by_configuration"] == {k: c["ledger"]["fits"] for k, c in rec["configurations"].items()}


def test_options_are_consistent_and_not_adopted(rec):
    assert rec["status"].startswith("SCENARIO")
    for k, c in rec["configurations"].items():
        assert c["adopted"] is False, k
        led = c["ledger"]
        used = led["compute_mm2"] + led["interconnect_mm2"] + led["overhead_mm2"] + led["hbm_phy_mm2"] + \
            led["ucie_phy_mm2"] + led["kv_ring_mm2"] + led["stream_unit_spill_mm2"] + led["target_rom_mm2"] + \
            led["drafter_rom_mm2"] + led["lane_copies_added"] * led["lane_copy_mm2"]
        if led["fits"]:
            assert used + led["slack_mm2"] == pytest.approx(led["die_mm2"], abs=0.1), k
            assert c["performance"]["rom_read"]["ok"], k
        else:
            assert used - led["die_mm2"] == pytest.approx(led["deficit_mm2"], abs=0.1), k
        # without a lane copy speculation cannot pay on the ROM die
        if led["lane_multiplier_m"] == 1 and not c["parameters"]["lm_head_in_hbm"]:
            assert c["performance"]["dflash"]["best"]["block"] == 1, k
    assert any(c["ledger"]["fits"] and c["ledger"]["dies"] == 1 for c in rec["configurations"].values())


def test_adopted_o4_is_the_baseline(rec, base):
    """The baseline implements O4: the same dies, groups, stacks, lane multiplier, 8-bit ROM and rates."""
    o4 = rec["configurations"]["O4_two_reticles_one_package"]
    led, pf = o4["ledger"], o4["performance"]
    a = base["area"]
    assert (a["dies"], a["groups_per_die"], a["lane_multiplier_m"]) == (led["dies"], led["groups_per_die"],
                                                                        led["lane_multiplier_m"]) == (2, 6144, 5)
    assert base["package"]["hbm_stacks"] == pf["hbm_stacks_total"] == 8
    assert base["package"]["weight_bits"] == 8
    assert a["target_rom_mm2"] == pytest.approx(led["target_rom_mm2"], abs=0.01)
    assert a["drafter_rom_mm2"] == pytest.approx(led["drafter_rom_mm2"], abs=0.01)
    assert a["rom_read"]["headroom"] == pf["rom_read"]["headroom"]
    pp = base["power_production"]["scenarios"]["B_proposed_production"]["rom"]
    assert pp["ar_batch1"]["tokens_s"] == pf["ar_tokens_s"]
    best = pf["dflash"]["best"]
    assert pp[f"dflash_block{best['block']}"]["tokens_s"] == best["tokens_s"]
    assert pp[f"dflash_block{best['block']}"]["step_cycles"] == best["step_cycles"]
    # the one difference: the baseline sizes each die's KV ring to its half of a layer (3.2 mm2), the record
    # carried the single-reticle ring (6.2 mm2) to each die, so the baseline has that much more slack
    assert a["slack_mm2"] - led["slack_mm2"] == pytest.approx(led["kv_ring_mm2"] - a["kv_prefetch_buffer_mm2"], abs=0.02)
    for s in ("A_measured_implementation", "B_proposed_production"):
        r = base["power_production"]["scenarios"][s]["rom"]["ar_batch1"]
        assert r["energy_per_token_mj"] == pytest.approx(o4["power"][s]["ar_batch1"]["energy_per_token_mj"], abs=0.05)


def test_single_reticle_does_not_fit(rec):
    """Why two reticles: no single-reticle configuration keeps every 8-bit weight in ROM with the drafter."""
    c0 = rec["configurations"]["C0_single_reticle"]["ledger"]
    assert c0["fits"] is False and c0["deficit_mm2"] > 60
