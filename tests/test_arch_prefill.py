"""GPU prefill + KV ingest budget (tools/arch_prefill.py -> results/arch/prefill_ingest.json)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_prefill as A  # noqa: E402

REC = ROOT / "results/arch/prefill_ingest.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


@pytest.fixture(scope="module")
def v41():
    return A.V41()


def test_record_is_current(rec):
    assert json.loads(json.dumps(A.build(), sort_keys=True)) == rec


def test_indexer_scan_sum_is_exact(v41):
    for a, b in ((0, 3000), (15000, 40000), (100, 17000)):
        assert v41.keys_sum(a, b) == pytest.approx(sum(v41.keys(p) for p in range(a, b)), rel=1e-12)


def test_bytes_agree_with_the_rack_and_the_budget(rec, v41):
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["kv_replication"]
    cold = {(r["design"], r["context"]): r for r in rec["v41_cold"] if r["gpus"].startswith("8 ")
            and r["rate_key"] == "conservative" and r["link"]["nics"] == 2}
    r = cold[("v41_rom", 1048576)]
    assert r["bytes_sent"]["owner_rows"] == rack["ingest"]["bytes_sent_once_per_user"]
    assert r["bytes_written_hbm_replicated"] == pytest.approx(rack["replicated_bytes_per_user_1m"])
    assert r["busiest_stage_bytes"] == pytest.approx(rack["busiest_stage_bytes_per_user"])
    assert r["capacity"]["rom_users"] == 962 and r["busiest_die_bytes"] == 93458432
    assert rec["v41_workload"]["sent_B_per_new_token"] == 890


def test_ingest_requirements_hold(rec):
    """ingest adds <= 1 ms or <= 2% of the prefill to TTFT (streamed) and takes <= 1% of a die's HBM."""
    for r in rec["v41_cold"]:
        assert r["stream"]["exposed_tail_s"] <= max(1e-3, 0.02 * r["gpu_prefill_s"])
        assert r["burst"]["time_s"] <= 0.02 * r["gpu_prefill_s"]
        assert r["hbm_share"]["fraction_of_die_hbm"] < 0.01
        assert r["stream"]["link_busy_fraction"] < 0.05
    for q in rec["qwen_cold"]:
        assert q["stream"]["exposed_last_layer_s"] <= max(1e-3, 0.02 * q["gpu_prefill_s"])
        assert q["hbm_share_at_link_rate"] < 0.01


def test_gpu_calibration_is_plausible(rec):
    for k, v in rec["gpu_calibration"]["rates"].items():
        assert 0.2 < v["b200_mfu_fp8_dense"] < 0.5, k
    assert 0.3 < rec["dense_gpu_calibration"]["h100_mfu_fp8_dense"] < 0.6


def test_late_bind_frees_the_slot(rec):
    for c, s in rec["slot_reservation"].items():
        assert s["late_bind_reserved_fraction"] < 1e-3 < s["stream_reserved_fraction"]


def test_qwen_capacity_explains_the_atlas_figure(rec):
    assert rec["qwen_cold"][0]["capacity"]["users_at_0p9"] == 201
