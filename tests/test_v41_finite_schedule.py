"""A component witness passes while missing or impossible full schedules fail closed."""

from copy import deepcopy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_finite_schedule as FS  # noqa: E402
import v41_finite_schedule_subset as S  # noqa: E402


def witness():
    return json.loads(S.OUT.read_text())


def test_exact_serial_component_witness_is_current_and_bounded():
    m = witness()
    assert S.build() == m
    for path, digest in m["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    result = FS.audit(m)
    assert result["status"] == "pass_resource_witness", result["errors"]
    assert result["scope"] == "operator_subset"
    assert result["makespan_cycles"] == 266 + 1220 + 80 + 476
    assert result["physical_peak_per_cycle"]["vm_port_b_write"] == 1
    assert result["useful_demand_by_class"]["vm_write"] == 4 * (266 + 80)
    assert result["wait_cycles_by_kind"]["verified_collective_stage"] == 0


def test_shared_physical_port_alias_conflict_is_rejected():
    m = witness()
    m["resources"]["second_vm_write_alias"] = dict(m["resources"]["dma_vm_write"])
    r = m["operations"][0]["reservations"][1]
    m["operations"][0]["reservations"].append(dict(r, resource="second_vm_write_alias"))
    assert any("over capacity" in e for e in FS.audit(m)["errors"])


def test_full_layer_needs_actual_program_placement_and_queues():
    m = witness()
    m["scope"] = "full_layer"
    m["operations"][0]["kind"] = "collective"
    errors = FS.audit(m)["errors"]
    assert any("program_path" in e for e in errors)
    assert any("all_unit_trace_path" in e for e in errors)
    assert any("shared-service queue IDs" in e for e in errors)


def test_fractional_expert_placement_and_missing_instruction_fail():
    m = witness()
    m["contract"]["tensor_specs"] = {"expert_w2": {"rows": 1280}}
    m["tensor_fragments"] = [dict(fragment_id="bad", tensor_id="expert_w2", expert_id=151.778,
                                  row_start=0, row_end=1280, owner_die=0,
                                  owner_cluster=0, physical_bytes=4096)]
    m["contract"]["instruction_ids"].append("L0.missing")
    errors = FS.audit(m)["errors"]
    assert any("fractional/noninteger expert" in e for e in errors)
    assert any("program instructions not scheduled" in e for e in errors)


def test_stale_source_pin_is_rejected():
    m = deepcopy(witness())
    m["source_sha256"]["tools/v41_finite_schedule.py"] = "0" * 64
    assert any("source pin mismatch" in e for e in FS.audit(m)["errors"])


def test_index_and_kv_on_same_stack_cannot_claim_independent_bandwidth():
    m = witness()
    for name, cls in (("index_stack0", "index_hbm"), ("kv_stack0", "kv_hbm")):
        m["resources"][name] = dict(physical_id=name, capacity_per_cycle=32,
                                    unit="32B_sector", classes=[cls], owner_die=0, stack_id=0)
    assert any("same physical HBM stack" in e for e in FS.audit(m)["errors"])
