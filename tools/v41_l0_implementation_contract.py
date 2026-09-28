#!/usr/bin/env python3
"""Generate and validate a fail-closed V4.1 layer-zero implementation contract.

This is an executable contract proposal, not a chip schedule or a rate model.
It records exact ISA dependencies and bounded stage evidence while leaving
unmeasured producer, shared-resource, physical and feedback service unknown.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/v41_l0_implementation_contract.json"
PRE = "results/arch/v41_single_token_schedule_preflight.json"
BIND = "results/rtl/hdc_v41x_fullshape_program_bind.json"
COLL = "results/rtl/v41_tp_layer0_collective_sequence.json"
DIE = "results/arch/v41_die_assembly.json"
REGION = "results/arch/v41_hbm_region_preflight.json"
QE_LOCAL = "results/rtl/v41x_qe_local_tile_bank_l0.json"
INDEX_SCORE_RTL = "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_batch.sv"
DIE_RTL = "rtl/chip/ot_chip_v41x_die.sv"
TILE_RTL = "rtl/chip/ot_chip_v41x_tile.sv"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def address_unit(name: str, fields: dict) -> str:
    if name in ("coll_src", "coll_dst", "coll_ibase"):
        return "VM_FP32_element"
    if name in ("qe_wbase", "me_wbase", "he_wbase"):
        return "logical_engine_weight_word_ROM_or_HBM_unselected_unmapped"
    if name == "me_obase":
        return "VM_16_FP32_element_word"
    if name in ("qe_xbase", "qe_obase", "me_xbase", "he_xbase", "he_obase"):
        return "VM_FP32_element"
    if name.endswith("base"):
        return "logical_address_unit_unresolved_by_source_or_mode"
    raise ValueError(f"not an address field: {name}")


def _address_fields(fields: dict) -> dict:
    return {k: {"value": v, "unit": address_unit(k, fields)}
            for k, v in fields.items()
            if k.endswith("base") or k in ("coll_src", "coll_dst")}


def derive() -> dict:
    pre, binder, coll, die, region, local = [load(p) for p in
                                             (PRE, BIND, COLL, DIE, REGION, QE_LOCAL)]
    assert pre["status"] == "blocked_missing_finite_service_contract"
    assert binder["instruction_count"] == len(pre["instructions"]) == 111
    assert coll["passed"] and coll["program_bind_sha256"] == digest(ROOT / BIND)
    assert die["clock_hz"] == 1_087_000_000.0
    assert len(coll["cases"]) == 12 and coll["sum_blocked_service_cycles"] == 2780
    cases = {c["descriptor"]["pc"]: c for c in coll["cases"]}
    ops = []
    for t, p in zip(binder["instruction_trace"], pre["instructions"], strict=True):
        pc, fields = t["pc"], t["fields"]
        assert pc == p["pc"] and t["tag"] == p["tag"] and t["unit"] == fields["unit"]
        assert sorted(t["reads"]) == p["reads"] and sorted(t["writes"]) == p["writes"]
        service = {"measured_cycles": None, "first_input_cycle": None,
                   "last_input_cycle": None, "first_output_cycle": None,
                   "last_output_cycle": None, "producer_ready_cycle": None,
                   "consumer_accept_cycle": None, "physical_owner": None,
                   "status": "unmeasured_in_complete_layer"}
        descriptor = None
        if p["unit"] == "COLL":
            c = cases[pc]
            d = c["descriptor"]
            assert (d["seq"], d["tag"], d["mode"], d["src_element"],
                    d["dst_element"], d["source_elements"]) == (
                    fields["coll_seq"], t["tag"], fields["coll_op"], fields["coll_src"],
                    fields["coll_dst"], fields["coll_n"])
            service.update(measured_cycles=c["cycles_blocked_to_all_done"],
                           first_input_cycle=p["collective"]["measured_stage_service"]["first_input_tx_after_issue"],
                           last_input_cycle=p["collective"]["measured_stage_service"]["last_input_tx_after_issue"],
                           first_output_cycle=p["collective"]["measured_stage_service"]["first_vm_write_after_issue"],
                           last_output_cycle=p["collective"]["measured_stage_service"]["last_vm_write_after_issue"],
                           status="measured_isolated_synthetic_producer_stage")
            descriptor = {"seq": d["seq"], "op": d["mode"], "src_element": d["src_element"],
                          "dst_element": d["dst_element"], "input_elements": d["source_elements"],
                          "input_64B_words": d["source_words"],
                          "output_64B_words": p["collective"]["output_vm_words_per_die"]}
        ops.append({"pc": pc, "tag": t["tag"], "unit": p["unit"],
                    "logical_owner": {"layer": 0, "rank": 0, "stage": "unassigned_in_integer_placement",
                                      "die": "unassigned_in_integer_placement", "cluster": None},
                    "reads": p["reads"], "writes": p["writes"],
                    "dependency_edges": {"isa_wait_completion_pcs": p["wait_unit_completion_pcs"],
                                         "raw_producer_pcs": p["raw_producer_pcs"],
                                         "war_reader_pcs": p["potential_war_reader_pcs"],
                                         "waw_writer_pcs": p["potential_waw_writer_pcs"],
                                         "issue_after_previous_pc": p["issue_after_previous_pc"]},
                    "address_fields": _address_fields(fields), "collective_descriptor": descriptor,
                    "service": service})
    paths = ("tools/v41_l0_implementation_contract.py", PRE, BIND, COLL, DIE,
             REGION, QE_LOCAL, INDEX_SCORE_RTL, DIE_RTL, TILE_RTL)
    pins = {p: digest(ROOT / p) for p in paths}
    return {"schema": "opentallas.v41.l0-implementation-contract.v1", "status": "proposal_blocked",
            "source_sha256": pins,
            "scope": "one real layer-0 rank-0 200K instruction binding; 1M position/selected-ID binding open",
            "weight_source_binding": {"logical_program_is_source_agnostic": True,
                                      "tile_default_W_HBM": 1,
                                      "die_forwards_weight_source_parameter": False,
                                      "ROM_die_mode_status": "blocked_until_die_exposes_W_HBM_0_and_exact_gate",
                                      "HBM_die_mode_status": "tile_default_only_full_layer_service_unproved",
                                      "source_files": [DIE_RTL, TILE_RTL]},
            "contexts": [
                {"context_tokens": 200000, "position": 199999, "binding_status": "exact_instruction_and_selected_image",
                 "selected_expert_ids": binder["source_experts"],
                 "program_binding_record": BIND, "token_latency_cycles": None},
                {"context_tokens": 1048576, "position": 1048575, "binding_status": "missing_position_and_selected_ID_binding",
                 "selected_expert_ids": None, "program_binding_record": None, "token_latency_cycles": None,
                 "required_inputs": ["one_M_position_sparse_RoPE_or_production_prefetch",
                                     "one_M_exact_selected_expert_IDs_and_checkpoint_shard",
                                     "one_M_packed_window_and_selected_CKV_region"]}],
            "clock": {"library": "ASAP7_analytical_reference", "target_hz": int(die["clock_hz"]),
                      "target_period_ps": 1e12 / die["clock_hz"], "achieved_hz": None,
                      "die_route_status": "absent", "source_record": DIE},
            "resource_interfaces": {
                "collective_stage_VM": {"physical_id": "die0.collective.behavioral_VM_four_banks",
                                        "read_ports_64B_per_cycle": 4, "write_ports_64B_per_cycle": 4,
                                        "receive_fifo_depth_words": coll["contract"]["CL_DEPTH"],
                                        "status": "measured_isolated_stage_only", "record": COLL},
                "full_die_VM": {"physical_id": None, "read_ports_64B_per_cycle": None,
                                "write_ports_64B_per_cycle": None, "capacity_bytes": None,
                                "status": "physical_macro_route_unclosed"},
                "QE_ROM_banks": {"physical_id": None, "read_ports": None,
                                 "status": "two_matrix_local_witness_only", "record": QE_LOCAL},
                "ME_HE_ROM_banks": {"physical_id": None, "read_ports": None,
                                    "status": "full_placement_and_port_service_unknown"},
                "shared_HBM_stacks": {"stack_count_per_die": 4, "pc_count_per_stack": 32,
                                      "sector_bytes": 32, "sustained_joint_service": None,
                                      "status": "region_preflight_only_no_joint_traffic", "record": REGION}},
            "operations": ops,
            "known_stage_service": {"collective_descriptor_count": len(cases),
                                    "synthetic_ready_blocked_cycles_sum": coll["sum_blocked_service_cycles"],
                                    "actual_producer_ready": None,
                                    "actual_layer_service_cycles": None},
            "critical_path_budget": {"complete_dependency_path": False,
                                     "selected_topology_budget_cycles": None,
                                     "allocation_rule": "derive from complete mapped producer/transfer/consumer/commit path and achieved clock; no arbitrary tok/s target",
                                     "component_inputs": [
                                         {"path": "two HE K2560 adapter loads", "known_local_floor_cycles": 5120,
                                          "allocated_cycles": None, "missing": "full-width HE compute/overlap/VM service"},
                                         {"path": "two wo_a K4096 G4 adapter loads", "known_local_floor_cycles": 2048,
                                          "allocated_cycles": None, "missing": "finite VM-to-ME route and concurrent resource trace"},
                                         {"path": "twelve actual blocking collective descriptors",
                                          "isolated_synthetic_stage_cycles": 2780, "allocated_cycles": None,
                                          "missing": "real producer readiness, shared VM and die-integrated link route"},
                                         {"path": "packed window cold refill", "known_sectors": 2176,
                                          "allocated_cycles": None, "missing": "cache state and shared HBM timing"},
                                         {"path": "remaining QE SU XU attention and feedback", "known_local_floor_cycles": None,
                                          "allocated_cycles": None, "missing": "complete finite service and exact commit trace"}]},
            "missing_contracts": [
                "one_M_context_position_and_selected_expert_image_binding",
                "full_integer_stage_die_cluster_and_ROM_bank_ownership_for_all_111_ops",
                "all_111_op_producer_first_last_and_consumer_accept_timing",
                "full_die_VM_bank_ports_capacity_queues_and_ME_HE_COLL_shared_schedule",
                "packed_window_RoPE_index_and_QE_weight_shared_HBM_service",
                "achieved_die_and_TP_link_clock_after_route_and_power",
                "layer_output_state_commit_and_next_token_feedback"],
            "total_latency_cycles": None}


def validate(c: dict) -> None:
    """Reject stale or silently promoted implementation evidence."""
    assert c["schema"] == "opentallas.v41.l0-implementation-contract.v1"
    assert c["status"] == "proposal_blocked" and c["total_latency_cycles"] is None
    for name, expected in c["source_sha256"].items():
        assert digest(ROOT / name) == expected, f"stale source pin: {name}"
    assert len(c["operations"]) == 111
    assert [o["pc"] for o in c["operations"]] == list(range(111))
    assert c["contexts"][0]["context_tokens"] == 200000
    assert c["contexts"][1]["binding_status"] == "missing_position_and_selected_ID_binding"
    assert all(x["token_latency_cycles"] is None for x in c["contexts"])
    assert c["clock"]["target_hz"] == 1_087_000_000 and c["clock"]["achieved_hz"] is None
    assert c["weight_source_binding"]["tile_default_W_HBM"] == 1
    assert c["weight_source_binding"]["die_forwards_weight_source_parameter"] is False
    assert "parameter integer W_HBM = 1" in (ROOT / TILE_RTL).read_text()
    assert "W_HBM" not in (ROOT / DIE_RTL).read_text()
    bank = c["resource_interfaces"]["collective_stage_VM"]
    collective_evidence = load(COLL)
    assert bank["read_ports_64B_per_cycle"] == bank["write_ports_64B_per_cycle"] == \
        collective_evidence["contract"]["bank_vm_writes_per_cycle"] == 4
    assert bank["receive_fifo_depth_words"] == collective_evidence["contract"]["CL_DEPTH"] == 256
    assert bank["record"] == COLL
    assert c["resource_interfaces"]["full_die_VM"]["status"] != "routed_pass"
    binder, coll = load(BIND), load(COLL)
    assert coll["program_bind_sha256"] == digest(ROOT / BIND)
    assert c["contexts"][0]["position"] == binder["rope_token_patch"]["position"]
    assert c["contexts"][0]["selected_expert_ids"] == binder["source_experts"]
    cases = {x["descriptor"]["pc"]: x for x in coll["cases"]}
    assert len(cases) == 12
    for o, t in zip(c["operations"], binder["instruction_trace"], strict=True):
        assert (o["pc"], o["tag"], o["reads"], o["writes"]) == (
            t["pc"], t["tag"], t["reads"], t["writes"])
        assert o["address_fields"] == _address_fields(t["fields"])
        deps = o["dependency_edges"]
        assert all(p < o["pc"] for p in deps["isa_wait_completion_pcs"])
        assert all(p < o["pc"] for p in deps["raw_producer_pcs"].values())
        if o["unit"] == "COLL":
            case = cases[o["pc"]]
            d, f = o["collective_descriptor"], t["fields"]
            assert (d["seq"], d["op"], d["src_element"], d["dst_element"],
                    d["input_elements"], d["input_64B_words"]) == (
                    f["coll_seq"], f["coll_op"], f["coll_src"], f["coll_dst"],
                    f["coll_n"], f["coll_n"] // 16)
            assert o["service"]["measured_cycles"] == case["cycles_blocked_to_all_done"] > 0
            assert o["service"]["producer_ready_cycle"] is None
        else:
            assert o["collective_descriptor"] is None
            assert o["service"]["measured_cycles"] is None
    assert sum(o["service"]["measured_cycles"] for o in c["operations"]
               if o["unit"] == "COLL") == 2780
    assert c["known_stage_service"]["actual_layer_service_cycles"] is None
    assert not c["critical_path_budget"]["complete_dependency_path"]
    assert c["critical_path_budget"]["selected_topology_budget_cycles"] is None
    assert all(x["allocated_cycles"] is None for x in c["critical_path_budget"]["component_inputs"])


def main() -> None:
    contract = derive()
    validate(contract)
    OUT.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    print(contract["status"], len(contract["operations"]),
          len([o for o in contract["operations"] if o["unit"] == "COLL"]))


if __name__ == "__main__":
    main()
