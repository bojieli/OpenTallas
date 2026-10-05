"""The V4.1 top-down budget (tools/arch_budget_v41.py): the re-pricing reproduces the report's DAG, the committed
required spec meets the headline on the same DAG, and the findings the spec rests on hold."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

A = pytest.importorskip("arch_budget_v41")
REC = ROOT / "results/arch/arch_budget_v41.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


@pytest.fixture(scope="module")
def env():
    return A._env()


def req_spec(rec):
    return A.Spec(**rec["required_spec"])


def test_dag_spec_reproduces_the_headline_exactly(env):
    """Re-pricing the report's own graph at the report's assumptions (plain option b) returns the report's numbers."""
    hl = A.headline()
    dag = A.dag_spec(A.dag_machine(1), env["clock"])
    for ctx in A.CONTEXTS:
        assert A.price(dag, ctx, base=A.PLAIN_B)["tokens_s_per_user"] == pytest.approx(hl["tokens_s_per_user"][ctx],
                                                                                     rel=1e-9)


def test_baseline_is_faster_than_plain_b(rec):
    req = rec["requirement"]["headline"]
    for ctx in ("8192", "200000", "1048576"):
        assert req["tokens_s_per_user"][ctx] > req["tokens_s_per_user_plain_b"][ctx]


def test_required_spec_meets_the_headline_at_every_context_and_batch_64(rec):
    hl = rec["requirement"]["headline"]
    sp = req_spec(rec)
    for ctx in A.CONTEXTS:
        assert A.price(sp, ctx)["tokens_s_per_user"] >= hl["tokens_s_per_user"][str(ctx)] * 0.999
    # the batch-64 sizing target is on the stage-mean basis (arch_budget_v41.OCC_BASIS); reported points are not
    assert A.price(sp, 200000, batch=64, occupancy="stage_mean")["tokens_s_per_user"] >= \
        hl["tokens_s_per_user_b64"]["200000"] * 0.999


def test_one_occupancy_basis_for_reported_points_and_adopted_hbm_stacks(rec):
    assert A.OCC_BASIS == ["busiest_stage"]
    assert rec["occupancy_basis"]["reported"] == "busiest_stage"
    hl = rec["requirement"]["headline"]
    assert hl["hbm_stacks_per_die"] == A.ROM_DIE_HBM_STACKS == rec["kv_state"]["stacks_per_die"]
    assert hl["hbm_stacks_per_package"] == 2 * A.ROM_DIE_HBM_STACKS
    for ctx, row in rec["occupancy_basis"]["required_b64_tokens_s_per_user"].items():
        assert row["busiest_stage"] <= row["stage_mean"] * (1 + 1e-9)


def test_required_spec_fits_the_compute_envelope(rec):
    assert rec["required_area_mm2"]["total"] < rec["compute_envelope_mm2"]
    assert rec["required_spec"]["rom_bytes"] < rec["rom_read_capacity_bytes_per_cycle"]


def test_golden_orders_cannot_meet_the_target_at_any_width(rec):
    """Under the golden's sequential accumulation orders the fixed part alone exceeds the token budget."""
    for ctx in ("8192", "200000", "1048576"):
        b = rec["budget"][ctx]
        assert b["fixed_us"]["golden_orders"] > b["target_us"]
        assert b["fixed_us"]["required_orders"] < b["target_us"]


def test_as_built_widths_are_two_orders_short(rec):
    for ctx, row in rec["priced"].items():
        assert row["as_built"]["tokens_s_per_user"] < row["dag"]["tokens_s_per_user"] / 50


def test_each_requirement_matters(rec):
    """Undoing any single width requirement drops the rate below the target at 200K."""
    target = rec["budget"]["200000"]["target_tokens_s"]
    abl = rec["ablations_tokens_s_per_user"]
    for tag in ("golden_orders", "su_as_built_8", "weight_engines_as_built", "attention_on_64_lanes",
                "indexer_on_64_lanes"):
        assert abl[tag]["200000"] < target, tag
    assert abl["indexer_on_64_lanes"]["1048576"] < abl["indexer_on_64_lanes"]["8192"]


def test_workload_scales_with_context_only_through_the_indexer(rec):
    w = {k: v["totals"] for k, v in rec["workload"].items()}
    assert w["8192"]["macs"]["weight:fp4"] == w["1048576"]["macs"]["weight:fp4"]
    assert w["1048576"]["macs"]["indexer:fp4"] > 20 * w["8192"]["macs"]["indexer:fp4"]
    active = sum(v for k, v in w["200000"]["macs"].items() if k.startswith("weight"))
    assert 14e9 < active < 17e9                       # ~16 B active parameters, one MAC each


def test_distinct_experts_union():
    assert A.distinct_experts(1, 384, 6) == pytest.approx(6.0)
    assert A.distinct_experts(6, 384, 6) == pytest.approx(384 * (1 - (1 - 6 / 384) ** 6))


def test_speculation_per_operator(rec):
    """Dense GEMVs: bytes shared on HBM (ratio 1), MAC-bound on the AR-sized ROM die (~B); routed experts cost
    their union on both machines; fixed latency is paid once per pass."""
    sp = rec["mtp"]["speculation"]["200000"]
    assert sp["hbm_m1"]["classes"]["dense_gemv"]["ratio_busy"] == pytest.approx(1.0, abs=0.01)
    assert sp["rom_m1"]["classes"]["dense_gemv"]["ratio_busy"] > 4
    assert sp["rom_m6"]["classes"]["dense_gemv"]["ratio_busy"] == pytest.approx(1.0, abs=0.01)
    u = sp["hbm_m1"]["distinct_experts"] / 6
    assert sp["hbm_m1"]["classes"]["routed_experts"]["ratio_busy"] == pytest.approx(u, rel=0.1)
    assert sp["rom_m6"]["classes"]["routed_experts"]["ratio_busy"] == pytest.approx(u, rel=0.1)
    for k in ("rom_m1", "hbm_m1"):
        assert sp[k]["classes"]["fixed"]["ratio_busy"] < 1.5


def test_mtp_design_point_fits_and_pays(rec):
    d = rec["mtp"]["design"]["200000"]
    assert d["design_m"] >= 2
    rows = {r["m"]: r for r in d["rows"]}
    ar = rec["required_priced"]["200000"]["tokens_s_per_user"]
    assert rows[2]["tokens_s_per_user"][A.TAU_HEADLINE_LABEL] > 2 * ar


def test_rom_beats_hbm_at_every_batch(rec):
    for ctx, b in rec["batch"].items():
        rom = {r["batch"]: r for r in b["rows"]["rom"]}
        hbm = {r["batch"]: r for r in b["rows"]["hbm"]}
        for bt in rom:
            assert rom[bt]["ar_aggregate_tokens_s"] > hbm[bt]["ar_aggregate_tokens_s"]
            assert rom[bt]["ar_energy_j_per_token_gated"] < hbm[bt]["ar_energy_j_per_token_gated"]


def test_engram_port_is_sized_by_bandwidth(rec):
    e = rec["engram"]
    assert e["required_bytes_per_cycle"] < 32 < e["as_built_port_bytes_per_cycle"]


def test_block_table_names_every_gap(rec):
    blocks = {b["block"]: b for b in rec["blocks"]}
    assert blocks["stream unit, linear lanes"]["ratio"] >= 64
    assert blocks["indexer engine (FP4 x FP4)"]["ratio"] > 1000


def test_rom_and_comparator_dies_carry_four_stacks(rec):
    """Standing decision: 4 HBM3E stacks per die (today's interposers), for the ROM die and the comparator."""
    assert A.ROM_DIE_HBM_STACKS == 4
    assert rec["kv_state"]["stacks_per_die"] == 4
    assert rec["kv_state"]["sustained_Bps_per_die"] == pytest.approx(3.6e12)
    assert rec["hbm_comparator"]["hbm_stacks_per_die"] == 4
    hb = rec["hbm_comparator"]
    ctx = "200000"
    # usable = technology.json efficiencies.hbm_capacity (0.9, the reserve the Qwen3 budget applies) x physical
    cap = rec["capacity"][ctx]
    assert cap["capacity_efficiency"] == 0.9
    assert cap["rom_users"] == int(0.9 * 4 * hb["stack_capacity_B"] // cap["per_user_bytes_busiest_die"])
    assert cap["rom_users_without_reserve"] == int(4 * hb["stack_capacity_B"] // cap["per_user_bytes_busiest_die"])
    assert rec["capacity"]["1048576"]["rom_users"] == 866 and cap["rom_users"] == 4516


def test_saturated_rows_beyond_the_users_held_are_flagged(rec):
    for ctx, b in rec["batch"].items():
        for mach in ("rom", "hbm"):
            held = rec["capacity"][ctx][f"{mach}_users"]
            for r in b["rows"][mach]:
                assert r["fits_capacity"] == (r["batch"] <= held)


def test_one_budget_model_carries_the_user_decisions(rec):
    """The unified budget (arch_budget_v41_dp retired): checkpoint precision, online softmax with norm folding
    rejected, the measured V4.1-Flash tau 3.65 with the published 3.5-4.1 band as sensitivities, 1M primary, the measured collective exposure rows
    and the per-class cooling limits."""
    assert not (ROOT / "tools/arch_budget_v41_dp.py").exists()
    assert rec["tool"] == "tools/arch_budget_v41.py"
    assert A.TAU_HEADLINE == 3.65 and A.TAU_DEFAULT == A.TAU_HEADLINE and A.TAU_CI95 == (3.5, 3.84)
    taus = {p["label"]: p["tau"] for p in A.tau_points()}
    assert taus[A.TAU_HEADLINE_LABEL] == 3.65 and 3.5 in taus.values() and 4.1 in taus.values()
    assert rec["target_context"]["chosen"] == 1048576
    steps = [s["step"] for s in rec["chain_ladder"]]
    assert any("online softmax" in s for s in steps) and any("REJECTED" in s for s in steps)
    assert "osm" in A.CHAIN_LEVERS
    ce = rec["collective_exposure"]
    assert ce["tau"] == 3.65
    for ctx in ("200000", "1048576"):
        assert ce["spec"][ctx]["measured_exposure"] < ce["spec"][ctx]["overlap_assumed"]
    p = rec["power"]
    assert set(p["cooling_limit_w_per_die_by_class"]) == {"air", "liquid"}
    assert p["cooling_limit_w_per_die"] == p["cooling_limit_w_per_die_by_class"]["liquid"]   # liquid baseline (2026-09-28)
    assert p["cooling_limit_w_per_die_by_class"]["air"] < 407.5   # the withdrawn 0.5 W/mm2 x 815 mm2 rule
    # the check is the HOTTEST die (the stage holding layer 20's uncapped index scan): at the specification's widths
    # and its stage-mean saturated rate it is over the air limit, an upper bound (docs/ARCH_SPEC_V41.md s6 item 12)
    hd = p["hottest_die"]
    assert hd["batch1"]["factor"] > 1 and hd["saturated"]["factor"] > 1
    for m in p["by_lane_mult"].values():
        assert m["saturated_die_dynamic_w"] > m["average_die"]["saturated_dynamic_w"]
    # with layer 20's scan split over S12-S14 (tools/v41_stage_rebalance.py) the spec's worst die fits a liquid-cooled
    # package (within a watt of the air limit, so no air verdict is asserted)
    assert p["worst_case_die_w"] < p["cooling_limit_w_per_die_by_class"]["liquid"]


def test_checkpoint_precision_prices_router_and_wo_a_as_released(rec):
    assert A.FP8 == pytest.approx(1 + 1 / 1024)          # one UE8M0 scale per 32 x 32 block
    ops = {o["name"]: o for o in rec["layer20_ops_200k"]}
    assert ops["ffn.router"]["fmt"] == "bf16"
    assert ops["attn.wo_a"]["fmt"] == "bf16xfp8w"
