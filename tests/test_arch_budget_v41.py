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
    """Re-pricing the report's own graph at the report's assumptions returns the report's numbers."""
    hl = A.headline()
    dag = A.dag_spec(A.dag_machine(1), env["clock"])
    for ctx in A.CONTEXTS:
        assert A.price(dag, ctx)["tokens_s_per_user"] == pytest.approx(hl["tokens_s_per_user"][ctx], rel=1e-9)


def test_required_spec_meets_the_headline_at_every_context_and_batch_64(rec):
    hl = A.headline()
    sp = req_spec(rec)
    for ctx in A.CONTEXTS:
        assert A.price(sp, ctx)["tokens_s_per_user"] >= hl["tokens_s_per_user"][ctx] * 0.999
    assert A.price(sp, 200000, batch=64)["tokens_s_per_user"] >= hl["tokens_s_per_user_b64"][200000] * 0.999


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
    assert rows[2]["tokens_s_per_user"]["default 4.1 (user decision)"] > 2 * ar


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
