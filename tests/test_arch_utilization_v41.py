"""The V4.1 utilisation study (tools/arch_utilization_v41.py): its surgery reproduces the budget model when no lever
is applied, the recorded operating points reproduce, and the recommendation obeys the user's adoption rule (no
adopted change slows the batch-1 per-user rate, with or without MTP)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

U = pytest.importorskip("arch_utilization_v41")
A = U.A
REC = ROOT / "results/arch/v41_utilization.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_solve_without_levers_is_the_budget_model():
    sp = U.req_spec()
    for ctx in U.CONTEXTS:
        a = A.price(sp, ctx, fill=True)
        b = U.solve(sp, ctx, muts=[lambda g, s: None])      # surgery path with a no-op mutation
        assert b["T_s"] == pytest.approx(a["T_s"], rel=1e-12)


def test_recorded_batch1_point_reproduces(rec):
    p = U.op_point(U.req_spec(), U.PRIMARY, 1)
    r = rec["utilisation"][str(U.PRIMARY)]["spec"]["b1"]
    assert p["tokens_s_per_user"] == pytest.approx(r["tokens_s_per_user"], rel=1e-9)
    assert p["mfu_array"]["all"] == pytest.approx(r["mfu_array"]["all"], rel=1e-9)


def test_coordinator_estimates(rec):
    chk = rec["coordinator_check"]
    assert 0.0005 < chk["batch1_mfu"]["model"] < 0.002           # ~0.1%
    # ~4% since the saturated point runs the users HELD at 1M (866 after the 0.9 capacity reserve) and is bound by
    # its busiest pipeline stage (arch_budget_v41.stage_bound), not the stage mean
    assert 0.02 < chk["saturated_mfu"]["model"] < 0.12
    # This is provisioned-port / macro capacity, not runtime utilisation.
    # The four-stack, pooled-engine design prices it at about 42%.
    assert chk["rom_read_39pct"]["provisioned_port_over_macro"] == pytest.approx(0.42, abs=0.02)
    assert chk["rom_read_39pct"]["actual_b1"] < 0.001


def test_utilisation_rises_with_batch(rec):
    u = rec["utilisation"][str(U.PRIMARY)]["spec"]
    assert u["b1"]["mfu_array"]["all"] < u["fill28"]["mfu_array"]["all"] < u["sat1024"]["mfu_array"]["all"]
    # the pipeline fill keeps the batch-1 per-user rate
    assert u["fill28"]["tokens_s_per_user"] == pytest.approx(u["b1"]["tokens_s_per_user"], rel=1e-9)


def test_adopted_levers_never_slow_batch1(rec):
    for n in rec["adopted_levers"]:
        for ctx, v in rec["leave_one_out_l3"][n].items():
            assert v["us_saved_b1"] >= -1e-9 and v["us_saved_verify"] >= -1e-9, (n, ctx)
    assert "replicate_router" not in rec["adopted_levers"]      # shadowed, and slower in the full set


def test_design_point_is_not_slower_at_batch1(rec):
    for ctx in map(str, U.CONTEXTS):
        base = rec["utilisation"][ctx]["spec_l3"]
        dp = rec["design_point"]["rows"][ctx]
        assert dp["b1"]["tokens_s_per_user"] >= base["b1"]["tokens_s_per_user"]
        assert dp["b1_mtp"]["tokens_s_per_user"] >= base["b1_mtp"]["tokens_s_per_user"]


def test_pooled_engines_cost_no_batch1_time(rec):
    u = rec["unification"]
    for ctx in map(str, U.CONTEXTS):
        b = u["batch1"][ctx]
        overlap = u["conflicts"][ctx]["quantised_pool_overlap_on_path_us"] + u["conflicts"][ctx]["bf16_pool_overlap_on_path_us"]
        t_spec, t_pool = 1e6 / b["spec"], 1e6 / b["pooled"]
        assert t_pool + overlap <= t_spec + 0.3                   # within the serialisation bound
    assert u["pooled_area"]["total"] < 0.7 * u["spec_area_mm2"]


def test_one_shot_engine_width_is_a_requirement(rec):
    s = rec["levers"]["on_l3"]["single"]
    assert s["oneshot_as_built_16_lanes"]["200000"]["delta_us"] > 1.0     # the 16-lane engine is exposed
    assert abs(s["oneshot_128_lanes"]["200000"]["delta_us"]) < 1e-9        # 128 lanes hide it


def test_collective_census(rec):
    c = rec["bottleneck"]["census_spec"]
    assert c["collectives_on_path"] == 177 and c["hops_on_path"] == 29   # 4 x 40 + 8 top-k merges + 8 row gathers + argmax
    assert c["collective_latency_us"] == pytest.approx(26.35, abs=0.1)


def test_nonlayer_dies_are_idle_and_right_sized(rec):
    n = rec["nonlayer_right_size"]
    assert n["hbm_stacks_removed"] == (76 - 4) * U.STACKS_PER_DIE   # the head dies keep theirs (C10)
    assert n["engine_area_removed_mm2"] > 0.35 * n["engine_area_array_spec_mm2"]


def test_energy_with_static_on_both_machines(rec):
    e = rec["energy_with_static"]
    b1 = e["rows"]["200000/b1"]
    # static dominates a batch-1 token on both machines, so the ratio with static is far below the dynamic-only one
    assert b1["rom_spec"]["static_j"] > 0.9 * b1["rom_spec"]["total_j"]
    assert b1["hbm_over_rom_spec"]["with_static"] < 0.1 * b1["hbm_over_rom_spec"]["dynamic_only"]
    for k, o in e["rows"].items():
        assert o["hbm_over_rom_design"]["with_static"] > 1.0, k      # the ROM array still wins everywhere
        assert o["rom_design"]["total_j"] <= o["rom_spec"]["total_j"] * 1.0001, k
