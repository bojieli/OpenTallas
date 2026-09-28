"""Structural and provenance gates for the blocked full-shape layer-0 schedule."""

import json
from pathlib import Path

import pytest

from tools import v41_single_token_schedule_preflight as S


def test_record_is_current_and_source_pinned():
    saved = json.loads(S.OUT.read_text())
    assert S.build() == saved
    for path, digest in saved["source_sha256"].items():
        assert S.sha(S.ROOT / path) == digest
    assert saved["status"] == "blocked_missing_finite_service_contract"
    assert saved["summary"]["token_latency_cycles"] is None
    assert saved["summary"]["service_reservations_complete"] is False


def test_bound_program_preserves_separate_expert_packets_and_dependencies():
    rec = S.build()
    rows = rec["instructions"]
    assert len(rows) == 111
    assert rec["summary"]["collectives"] == 12
    assert rec["summary"]["all_collective_input_vm_words_per_die"] == 686
    assert rec["summary"]["all_collective_output_vm_words_per_die"] == 1784
    acts = [r for r in rows if r["unit"] == "COLL" and ".act" in r["tag"]]
    assert len(acts) == 7
    assert [r["collective"]["input_vm_words_per_die"] for r in acts] == [36] * 7
    assert rows[10]["wait_unit_completion_pcs"][-1] == 9
    assert rows[55]["raw_producer_pcs"]["ACT6"] == 54
    assert rows[35]["raw_producer_pcs"]["ACC"] == 34
    assert rows[36]["raw_producer_pcs"]["ACC"] == 34
    assert rows[35]["known_component_floor_cycles"] == 1024
    assert rows[36]["known_component_floor_cycles"] == 1024
    assert rows[1]["known_component_floor_cycles"] == 2560
    assert rows[45]["known_component_floor_cycles"] == 2560
    assert all(r["physical_owner"] is None and r["service_cycles"] is None for r in rows)


def test_external_memory_demand_is_conditional_and_distinct():
    demand = S.build()["known_external_hbm_demand"]
    assert demand["cold_window_refill_sectors"] == 128 * 17
    assert demand["rope_patch_bytes"] == 256
    assert demand["rope_patch_sectors"] == 8
    assert demand["index_scan_sectors"] == 0
    assert "unmeasured" in demand["warm_window_hit"]


def test_rejects_stale_binder_source_pin(tmp_path: Path):
    binder = json.loads(S.BINDER.read_text())
    first = next(iter(binder["source_sha256"]))
    binder["source_sha256"][first] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(binder))
    with pytest.raises(AssertionError, match=first):
        S.build(path)
