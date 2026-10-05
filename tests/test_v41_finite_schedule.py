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


def test_historical_serial_component_witness_fails_closed_on_changed_rtl():
    m = witness()
    assert S.build() == m
    for path, digest in m["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    result = FS.audit(m)
    assert result["status"] == "blocked"
    assert any("exact stage source mismatch rtl/rom/ot_rom_oneshot_px.sv" in e
               for e in result["errors"])
    assert result["scope"] == "operator_subset"
    assert result["makespan_cycles"] is None
    assert m["operations"][-1]["end_cycle"] == 266 + 1220 + 80 + 476
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


def two_expert_bank_witness():
    """Synthetic local-bank schedule for checking fixed versus shared MAC ownership."""
    m = witness()
    m["contract"]["instruction_ids"] = ["expert0", "expert1"]
    m["contract"]["tensor_specs"] = {f"w{i}": {"rows": 1} for i in (0, 1)}
    m["tensor_fragments"] = [dict(fragment_id=f"f{i}", tensor_id=f"w{i}", expert_id=i,
                                  row_start=0, row_end=1, owner_die=0,
                                  owner_cluster=0, physical_bytes=10) for i in (0, 1)]
    m["resources"] = {}
    m["operations"] = []
    for i in (0, 1):
        start = i
        for suffix, cls, cap, unit in (("issue", "issue", 1, "issue"),
                                       ("mac", "quant_mac", 1, "MAC"),
                                       ("rom", "weight_rom", 10, "byte"),
                                       ("read", "vm_read", 1, "word"),
                                       ("write", "vm_write", 1, "word")):
            m["resources"][f"{suffix}{i}"] = dict(physical_id=f"{suffix}{i}",
                                                     capacity_per_cycle=cap, unit=unit,
                                                     classes=[cls], owner_die=0,
                                                     serves_clusters=[0], served_expert_ids=[i])
        m["operations"].append(dict(id=f"e{i}", kind="qe_rom", instruction_id=f"expert{i}",
                                    die=0, cluster=0, start_cycle=start, end_cycle=start + 10,
                                    ready_cycle=start, deps=[], tensor_fragment_ids=[f"f{i}"],
                                    demands=dict(issue=1, quant_mac=10, weight_rom=10,
                                                 vm_read=1, vm_write=1),
                                    reservations=[
                                        dict(resource=f"issue{i}", **{"class": "issue"},
                                             start_cycle=start, end_cycle=start + 1, rate=1),
                                        dict(resource=f"mac{i}", **{"class": "quant_mac"},
                                             start_cycle=start, end_cycle=start + 10, rate=1),
                                        dict(resource=f"rom{i}", **{"class": "weight_rom"},
                                             start_cycle=start, end_cycle=start + 1, rate=10),
                                        dict(resource=f"read{i}", **{"class": "vm_read"},
                                             start_cycle=start, end_cycle=start + 1, rate=1),
                                        dict(resource=f"write{i}", **{"class": "vm_write"},
                                             start_cycle=start + 9, end_cycle=start + 10, rate=1),
                                    ]))
    return m


def test_fixed_near_rom_tiles_and_bounded_bank_local_pool():
    fixed = two_expert_bank_witness()
    assert FS.audit(fixed)["status"] == "pass_resource_witness"
    equal_mac_area_pool = deepcopy(fixed)
    equal_mac_area_pool["resources"]["mac0"]["capacity_per_cycle"] = 2
    equal_mac_area_pool["resources"]["mac1"]["capacity_per_cycle"] = 2
    equal_mac_area_pool["resources"]["mac1"]["physical_id"] = "mac0"
    assert FS.audit(equal_mac_area_pool)["status"] == "pass_resource_witness"
    pooled = deepcopy(fixed)
    pooled["resources"]["mac1"]["physical_id"] = "mac0"
    assert any("over capacity" in e for e in FS.audit(pooled)["errors"])
    # A one-lane shared candidate needs a serial schedule; counters reveal it.
    second = pooled["operations"][1]
    second["start_cycle"], second["end_cycle"] = 10, 20
    for reservation in second["reservations"]:
        reservation["start_cycle"] += 9
        reservation["end_cycle"] += 9
    verdict = FS.audit(pooled)
    assert verdict["status"] == "pass_resource_witness", verdict["errors"]
    assert verdict["wait_cycles_by_kind"]["qe_rom"] == 9


def test_remote_rom_fragment_requires_explicit_local_mapping():
    m = two_expert_bank_witness()
    m["tensor_fragments"][1]["owner_cluster"] = 1
    assert any("not local to compute cluster" in e for e in FS.audit(m)["errors"])


def test_full_scope_cannot_buy_rate_with_unbudgeted_area_or_power():
    m = witness()
    m["scope"] = "full_layer"
    m["contract"].update(layer_id=0, area_limit_mm2_by_die={"0": 0.5},
                         power_limit_w_by_die={"0": 1},
                         fixed_area_mm2_by_die={"0": 0},
                         fixed_power_w_by_die={"0": 0})
    for resource in m["resources"].values():
        resource.update(owner_die=0, area_mm2=1, idle_w=1, active_w=1)
    errors = FS.audit(m)["errors"]
    assert any("physical area exceeds limit" in e for e in errors)
    assert any("simultaneous power exceeds cooling limit" in e for e in errors)


def test_nonfinite_capacity_rate_and_power_cannot_buy_a_witness():
    bad_capacity = witness()
    bad_capacity["resources"]["dma_vm_write"]["capacity_per_cycle"] = float("nan")
    assert any("physical_id, capacity" in e for e in FS.audit(bad_capacity)["errors"])

    bad_rate = witness()
    bad_rate["operations"][0]["reservations"][1]["rate"] = float("inf")
    assert any("invalid reservation" in e for e in FS.audit(bad_rate)["errors"])

    bad_power = witness()
    bad_power["scope"] = "full_layer"
    bad_power["resources"]["dma_vm_write"].update(owner_die=0, area_mm2=0,
                                                       idle_w=0, active_w=float("nan"))
    assert any("concrete die, area and idle/active power" in e
               for e in FS.audit(bad_power)["errors"])


def test_full_scope_referenced_empty_queue_is_not_evidence():
    m = witness()
    m["scope"] = "full_layer"
    m["operations"][0]["kind"] = "collective"
    m["operations"][0]["queue_ids"] = ["q0"]
    m["queues"] = {"q0": {"depth": 1, "events": []}}
    assert any("queue q0 has no bound events" in e for e in FS.audit(m)["errors"])


def test_malformed_resource_reservation_queue_and_dependency_block_without_crash():
    for edit, required in (
        (lambda m: m["resources"]["dma_vm_write"].pop("physical_id"), "unbound class/resource"),
        (lambda m: m["operations"][0]["reservations"].append(None), "reservation object"),
        (lambda m: m["operations"][0].update(deps="bad"), "dependency list required"),
        (lambda m: m["queues"].update(q0={"depth": 1, "events": [None]}), "cycle and nonzero integer delta"),
    ):
        m = witness()
        edit(m)
        assert any(required in e for e in FS.audit(m)["errors"])


def test_queue_events_must_belong_to_declared_operation_and_interval():
    m = witness()
    m["scope"] = "full_layer"
    op = m["operations"][0]
    op["kind"] = "collective"
    op["queue_ids"] = ["q0"]
    m["queues"] = {"q0": {"depth": 2, "events": [
        {"cycle": 0, "delta": 1, "op": "not_an_operation"},
        {"cycle": op["end_cycle"] + 1, "delta": -1, "op": op["id"]},
    ]}}
    errors = FS.audit(m)["errors"]
    assert any("event not bound" in e for e in errors)
    assert any("outside operation interval" in e for e in errors)


def test_full_clock_and_extra_tensor_must_be_concrete():
    m = witness()
    m["scope"] = "full_layer"
    m["contract"]["clock_hz"] = float("nan")
    assert any("finite positive clock_hz" in e for e in FS.audit(m)["errors"])

    extra = two_expert_bank_witness()
    extra["tensor_fragments"][0]["tensor_id"] = "unlisted_weight"
    assert any("absent from tensor_specs" in e for e in FS.audit(extra)["errors"])


def test_stage_record_must_match_selected_measured_case(tmp_path):
    m = witness()
    record = json.loads((ROOT / "results/rtl/v41_collective_depth_campaign.json").read_text())
    selected = next(c for c in record["cases"] if c["case"] == "act_d128_q2_blocked_pairwise")
    selected["exposed_tail_cycles"] -= 1
    path = tmp_path / "bad_stage.json"
    path.write_text(json.dumps(record))
    m["source_sha256"] = {"bad_stage.json": hashlib.sha256(path.read_bytes()).hexdigest()}
    m["operations"][0]["exact_stage_record"]["path"] = "bad_stage.json"
    errors = FS.audit(m, root=tmp_path)["errors"]
    assert any("stage interval or measured case mismatch" in e for e in errors)


def test_malformed_manifest_shapes_block_without_exception():
    assert FS.audit([])["status"] == "blocked"
    for field, value in (("contract", []), ("operations", [None]),
                         ("tensor_fragments", [None]), ("queues", {"q0": None})):
        m = witness()
        m[field] = value
        assert FS.audit(m)["status"] == "blocked"
