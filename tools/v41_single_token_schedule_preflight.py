#!/usr/bin/env python3
"""Bound layer-0 TP-4 instruction graph and missing finite-service contract.

This is a constructive dependency/packet extraction from the actual 111-op
emitter and its checkpoint-selected ROM binder. It refuses to assign a token
cycle count while first/last readiness, physical banks/ports, shared HBM and
achieved service are absent. In particular it preserves all seven separate
36-word expert activation gathers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import v41_fullshape_program_bind as B  # noqa: E402

BINDER = ROOT / "results/rtl/hdc_v41x_fullshape_program_bind.json"
COLLECTIVE = ROOT / "results/rtl/v41_tp_layer0_collective_sequence.json"
OUT = ROOT / "results/arch/v41_single_token_schedule_preflight.json"
UNIT_NAMES = {I.UNIT_END: "END", I.UNIT_ME: "ME", I.UNIT_SU: "SU",
              I.UNIT_QE: "QE", I.UNIT_XU: "XU", I.UNIT_HE: "HE",
              I.UNIT_COLL: "COLL"}
WAIT_UNIT = {I.UNIT_ME: 0, I.UNIT_SU: 1, I.UNIT_QE: 2,
             I.UNIT_XU: 3, I.UNIT_HE: 4}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(f: dict) -> str:
    unit = f["unit"]
    if unit == I.UNIT_ME:
        return "attention_kv" if f.get("me_wsrc") else "bf16_rom_weight"
    if unit == I.UNIT_QE:
        return "quant_rom_weight"
    if unit == I.UNIT_HE:
        return "hcp_rom_weight"
    if unit == I.UNIT_SU:
        return "vector_or_state"
    if unit == I.UNIT_XU:
        return "select_or_gather"
    if unit == I.UNIT_COLL:
        return "collective"
    if unit == I.UNIT_END:
        return "completion"
    raise ValueError(f"unknown unit {unit}")


def missing_for(f: dict) -> list[str]:
    unit = f["unit"]
    if unit == I.UNIT_COLL:
        return ["first_last_real_producer_and_consumer_ready_cycles",
                "shared_physical_VM_read_write_ports_and_queue_events",
                "die_integrated_link_engine_and_DMA_contention", "routed_frequency_and_power"]
    if unit == I.UNIT_ME:
        if f.get("me_wsrc"):
            return ["packed_window_or_selected_ckv_HBM_prefetch_and_arbiter_trace",
                    "attention_VM_read_write_ports", "first_last_row_readiness", "routed_service"]
        return ["matrix_to_ROM_macro_and_cluster_port_mapping",
                "FP32_activation_VM_read_and_conversion_trace",
                "ME_compute_and_result_drain_at_target_width", "routed_service"]
    if unit == I.UNIT_QE:
        return ["packed_FP4_sector_to_16_lane_adapter", "QE_ROM_macro_row_port_owner",
                "QE_activation_and_output_VM_ports", "target_width_compute_and_routed_service"]
    if unit == I.UNIT_HE:
        return ["HCP_HW256_repacked_image_and_macro_ports",
                "HE_2560_chunk_activation_load_overlap", "target_width_compute_and_routed_service"]
    if unit == I.UNIT_SU:
        return ["vector_operand_port_and_bank_schedule", "SFU_reduce_rounding_pipeline_latency",
                "first_last_chunk_readiness_and_result_drain"]
    if unit == I.UNIT_XU:
        return ["selector_or_Engram_port_schedule", "selection_completion_and_next_input_readiness"]
    return ["terminal_state_commit_and_next_token_feedback"]


def component_floor(f: dict) -> tuple[int, str]:
    """Optimistic component floor under the recorded one-write-port VM point."""
    if f["unit"] == I.UNIT_HE and f.get("he_k") == 2560:
        return 2560, "HE adapter copies one 8-element K chunk/cycle before the HCP command"
    if (f["unit"] == I.UNIT_ME and f.get("_tag") == "L0.out" and
            not f.get("me_wsrc") and f.get("me_k") == 4096):
        return 1024, "corrected wo_a adapter LOADs four FP32 elements/cycle per o-group"
    if f["unit"] == I.UNIT_COLL:
        words = f["coll_n"] // 16
        out = 4 * words if f["coll_op"] == I.COLL_ALL_GATHER else words
        return out, "reference one-port 64-B VM output point; no startup, link or producer delay"
    return 0, "no source-pinned full-width completion service; zero only for a lower bound"


def collective_service(binder: dict, path: Path = COLLECTIVE) -> dict[int, dict]:
    """Bind a measured stage service only to the exact emitted descriptor set."""
    rec = json.loads(path.read_text())
    assert rec["schema"] == "v41_tp_layer0_collective_sequence_v1" and rec["passed"]
    assert rec["program_bind_sha256"] == sha(BINDER)
    for name, digest in rec["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    assert rec["contract"]["blocked_COLL_v1"] and rec["contract"]["CL_LANES"] == 16
    assert rec["contract"]["GW"] == 4 and rec["contract"]["bank_vm_writes_per_cycle"] == 4
    trace = binder["instruction_trace"]
    cases = rec["cases"]
    assert len(cases) == 12
    bound = {}
    for case in cases:
        d = case["descriptor"]
        pc = d["pc"]
        t = trace[pc]
        f = t["fields"]
        assert t["unit"] == I.UNIT_COLL and t["tag"] == d["tag"]
        assert (f["coll_seq"], f["coll_op"], f["coll_src"], f["coll_dst"], f["coll_n"]) == (
            d["seq"], d["mode"], d["src_element"], d["dst_element"], d["source_elements"])
        assert d["source_words"] == f["coll_n"] // 16
        assert len(case["per_die"]) == 4
        assert all(x["writes"] == (4 if f["coll_op"] == I.COLL_ALL_GATHER else 1) *
                   d["source_words"] for x in case["per_die"])
        assert all(x["finish"] - x["start"] == case["cycles_blocked_to_all_done"]
                   for x in case["per_die"])
        assert pc not in bound
        bound[pc] = dict(source_record=str(path.relative_to(ROOT)),
                         source_record_sha256=sha(path),
                         service_cycles=case["cycles_blocked_to_all_done"],
                         first_input_tx_after_issue=min(x["first_tx"] - x["start"] for x in case["per_die"]),
                         last_input_tx_after_issue=max(x["last_tx"] - x["start"] for x in case["per_die"]),
                         first_vm_write_after_issue=min(x["first_vm"] - x["start"] for x in case["per_die"]),
                         last_vm_write_after_issue=max(x["last_vm"] - x["start"] for x in case["per_die"]),
                         peak_receive_fifo_words=max(x["peak_fifo"] for x in case["per_die"]),
                         producer_ready_at_issue="assumed_by_synthetic_fixture_not_proven",
                         scope="isolated persistent four-rank link/DMA/behavioral-VM stage; no producer, HBM or route")
    assert sum(x["service_cycles"] for x in bound.values()) == rec["sum_blocked_service_cycles"] == 2780
    return bound


def build(binder_path: Path = BINDER) -> dict:
    binder = json.loads(binder_path.read_text())
    assert binder["schema"] == "opentallas.v41x.fullshape.program_bind.v1"
    for path, digest in binder["source_sha256"].items():
        assert sha(ROOT / path) == digest, path
    for path, key in ((B.DEFAULT_LAYOUT, "layout_sha256"),
                      (B.DEFAULT_SHARD, "shard_sha256"),
                      (B.DEFAULT_QE, "qe_stream_sha256"),
                      (B.DEFAULT_ROPE, "rope_patch_sha256")):
        assert sha(path) == binder[key], path
    assert binder["layer"] == 0 and binder["rank"] == 0
    shape_program = R.build_tp_layer0()
    trace = binder["instruction_trace"]
    assert len(shape_program) == len(trace) == binder["instruction_count"] == 111
    assert [t["pc"] for t in trace] == list(range(111))
    program = []
    for pc, t in enumerate(trace):
        s = shape_program[pc]
        assert (t["unit"], t["tag"], t["reads"], t["writes"]) == (
            s["unit"], s.get("_tag"), sorted(s.get("_reads", ())), sorted(s.get("_writes", ())))
        f = dict(t["fields"])
        assert f["unit"] == t["unit"]
        f.update(_tag=t["tag"], _reads=t["reads"], _writes=t["writes"])
        program.append(f)
    qe_pcs = {f["pc"] for f in binder["qe_address_trace"]}
    assert all(program[pc]["unit"] == I.UNIT_QE for pc in qe_pcs)
    me_pcs = [f["pc"] for f in binder["me_wo_a_trace"]]
    assert me_pcs == [35, 36]
    assert all(program[pc]["unit"] == I.UNIT_ME and not program[pc].get("me_xjs") for pc in me_pcs)
    measured_coll = collective_service(binder)

    # These are structural dependencies. A region RAW edge does not by itself
    # say whether the first chunk or full producer result is required.
    last_write: dict[str, int] = {}
    last_read: dict[str, int] = {}
    last_unit: dict[int, int] = {}
    last_coll: int | None = None
    rows = []
    floor_starts: list[int] = []
    floor_ends: list[int] = []
    for pc, f in enumerate(program):
        unit = f["unit"]
        reads = sorted(f.get("_reads", ()))
        writes = sorted(f.get("_writes", ()))
        wait_mask = f.get("wait", 0)
        hard = set()
        raw = {}
        war = {}
        waw = {}
        if last_coll is not None:
            hard.add(last_coll)  # COLL v1 blocks issue until result written.
        for u, bit in WAIT_UNIT.items():
            if wait_mask & (1 << bit) and u in last_unit:
                hard.add(last_unit[u])
        if unit in (I.UNIT_QE, I.UNIT_XU) and unit in last_unit:
            hard.add(last_unit[unit])  # their adapter accepts one op at a time
        for name in reads:
            if name in last_write:
                raw[name] = last_write[name]
        for name in writes:
            if name in last_write:
                waw[name] = last_write[name]
            if name in last_read:
                war[name] = last_read[name]
        row = dict(pc=pc, tag=f.get("_tag"), unit=UNIT_NAMES[unit],
                   service_class=classify(f), issue_after_previous_pc=pc - 1 if pc else None,
                   wait_mask=wait_mask, wait_unit_completion_pcs=sorted(hard),
                   reads=reads, writes=writes, raw_producer_pcs=raw,
                   potential_war_reader_pcs=war, potential_waw_writer_pcs=waw,
                   first_last_readiness="unknown",
                   first_last_result_cycles=None, physical_owner=None,
                   service_cycles=None, missing_contract=missing_for(f))
        floor, floor_basis = component_floor(f)
        # This is an optimistic reference schedule, not an executable one.
        # RAW/WAR/WAW readiness and all unmeasured work are deliberately zero.
        min_issue = floor_starts[-1] + 1 if floor_starts else 0
        lower_start = max([min_issue] + [floor_ends[d] for d in hard])
        lower_end = lower_start + floor
        row.update(known_component_floor_cycles=floor,
                   known_component_floor_basis=floor_basis,
                   incomplete_lower_bound_start_cycle=lower_start,
                   incomplete_lower_bound_end_cycle=lower_end)
        if unit == I.UNIT_COLL:
            n = f["coll_n"]
            assert n > 0 and n % 16 == 0
            words = n // 16
            gather = f["coll_op"] == I.COLL_ALL_GATHER
            row["collective"] = dict(op="all_gather" if gather else "all_reduce",
                                     input_vm_words_per_die=words,
                                     output_vm_words_per_die=4 * words if gather else words,
                                     one_write_port_output_floor_cycles=4 * words if gather else words,
                                     seq=f["coll_seq"], rounded=bool(f.get("coll_rnd")))
            row["collective"]["measured_stage_service"] = measured_coll[pc]
            last_coll = pc
        rows.append(row)
        floor_starts.append(lower_start)
        floor_ends.append(lower_end)
        for name in reads:
            last_read[name] = pc
        for name in writes:
            last_write[name] = pc
        if unit in WAIT_UNIT:
            last_unit[unit] = pc
    coll = [r for r in rows if r["unit"] == "COLL"]
    acts = [r for r in coll if ".act" in r["tag"] and r["tag"].endswith("_gather")]
    assert len(coll) == 12 and len(acts) == 7
    assert all(r["collective"]["input_vm_words_per_die"] == 36 for r in acts)
    assert len({r["pc"] for r in acts}) == 7
    assert binder["status"] == "blocked" and binder["blockers"]
    dyn = R.dyn_values(R.SHIPPED, 199999)
    assert dyn["WIN"] == 128
    source_paths = ("tools/v41_single_token_schedule_preflight.py", "tools/hdc_replay_v41.py",
                    "tools/hdc_program_v41.py", "tools/hdc_isa_v41.py",
                    "tools/v41_fullshape_program_bind.py", str(binder_path.relative_to(ROOT)),
                    str(COLLECTIVE.relative_to(ROOT)),
                    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_batch.sv",
                    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv",
                    "results/rtl/hdc_v41x_idx_four_stack_verilator_collector_pipeline.json",
                    "results/rtl/v41x_qe_local_tile_bank_l0.json",
                    str(B.DEFAULT_LAYOUT.relative_to(ROOT)), str(B.DEFAULT_SHARD.relative_to(ROOT)),
                    str(B.DEFAULT_QE.relative_to(ROOT)), str(B.DEFAULT_ROPE.relative_to(ROOT)))
    pins = {p: sha(ROOT / p) for p in source_paths}
    return dict(schema="opentallas.v41.single-token-schedule-preflight.v1",
                status="blocked_missing_finite_service_contract",
                source_sha256=pins, binder_status=binder["status"], binder_blockers=binder["blockers"],
                selected_expert_ids=binder["source_experts"],
                claim_boundary="complete current layer-0 instruction/dependency/packet extraction only; no token cycles or rate",
                summary=dict(instructions=len(rows), collectives=len(coll),
                             separate_expert_activation_gathers=len(acts),
                             expert_activation_input_vm_words=[r["collective"]["input_vm_words_per_die"] for r in acts],
                             total_expert_activation_input_vm_words=sum(r["collective"]["input_vm_words_per_die"] for r in acts),
                             all_collective_input_vm_words_per_die=sum(r["collective"]["input_vm_words_per_die"] for r in coll),
                             all_collective_output_vm_words_per_die=sum(r["collective"]["output_vm_words_per_die"] for r in coll),
                             measured_isolated_collective_blocked_service_cycles=sum(
                                 r["collective"]["measured_stage_service"]["service_cycles"] for r in coll),
                             measured_collective_source_ready="synthetic_fixture_only",
                             one_vm_write_port_aggregate_output_floor_cycles=sum(r["collective"]["output_vm_words_per_die"] for r in coll),
                             bound_qe_accesses=len(binder["qe_address_trace"]),
                             me_wo_a_pcs=me_pcs, service_reservations_complete=False,
                             layer0_optimistic_component_floor_cycles=floor_ends[-1],
                             component_floor_reference="one 64-B VM output write/cycle; HE K-load and wo_a G4-load floors; all missing service zero",
                             component_floor_excludes="RAW/WAR/WAW readiness, compute, link, shared HBM, physical ports, routing and state commit",
                             token_latency_cycles=None),
                known_external_hbm_demand=dict(
                    context_tokens=200000, position=199999,
                    window_rows=dyn["WIN"], packed_window_sectors_per_row=17,
                    cold_window_refill_sectors=dyn["WIN"] * 17,
                    warm_window_hit="unmeasured; one active user's rows may persist only while that stage retains its state",
                    rope_patch_bytes=(binder["rope_token_patch"]["absolute_last_word"] -
                                      binder["rope_token_patch"]["absolute_first_word"] + 1) * 8,
                    rope_patch_sectors=8,
                    index_scan_sectors=0,
                    note="cold-window and RoPE physical request counts only; no request/return overlap, arbiter or cache-hit timing credited"),
                missing_global_contract=[
                    "integer_die_cluster_macro_row_port_placement_for_all_checkpoint_fragments",
                    "bounded_VM_read_write_and_converter_schedule_for_every_instruction",
                    "per_descriptor_first_last_operand_readiness_and_queue_transitions",
                    "shared_four_stack_HBM_KV_constant_index_and_all_weight_HBM_trace",
                    "routed_local_and_TP_link_latency_frequency_area_power",
                    "exact_layer_output_and_committed_state_through_full_die",
                ], ranked_missing_paths=[
                    dict(rank=1, scope="index_heavy_layer_not_L0",
                         path="sharded_key_delivery_to_score_and_topk",
                         current_resource="one ot_hdc_v41x_idx_pool_batch serial META/DESC/RUN scorer after 64-key beat",
                         structural_floor_cycles_at_262144_keys=4096 * (1 + 64 + 1 + 64),
                         floor_basis="4096 beats; IDLE accept >=1, META >=64, DESC >=1, RUN >=64 cycles per beat",
                         index_only_delivery_cycles=9278,
                         gap="score and selector ready/backpressure absent from index-only HBM collector gate",
                         required_gate="same 262144-key four-stack scan with actual pooled score/selector ready and exact top-k"),
                    dict(rank=2, scope="L0_and_all_weighted_layers",
                         path="checkpoint_to_local_ROM_QE_ME_HE_port_ownership",
                         bound_selected_QE_accesses=len(binder["qe_address_trace"]),
                         physical_lower_bound_cycles=None,
                         gap="local QE tile witness maps two matrices only; full die bank/cluster/read-port map absent",
                         required_gate="all selected program weight accesses mapped to finite macro rows/ports with exact token outputs"),
                    dict(rank=3, scope="L0",
                         path="VM_and_activation_readiness_across_ME_HE_and_collectives",
                         isolated_collective_blocked_cycles=2780,
                         separate_HE_load_floor_cycles=2 * 2560,
                         separate_wo_a_G4_load_floor_cycles=2 * 1024,
                         gap="producer first/last availability and VM/convert/store conflicts unmeasured; component costs cannot be summed or overlapped as token latency",
                         required_gate="bound PC-level issue/read/write trace including ME/HE adapter loads and twelve exact COLLs"),
                    dict(rank=4, scope="L0_cold_window",
                         path="shared_HBM_window_RoPE_weight_arbitration",
                         cold_window_refill_sectors=2176, rope_position_sectors=8,
                         physical_lower_bound_cycles=None,
                         gap="per-token hit/miss and shared stack/PC service absent; preloaded window is not HBM throughput",
                         required_gate="timed packed-window and RoPE prefetch sharing HBM with QE weights and emitted program"),
                ], instructions=rows)


def main() -> None:
    rec = build()
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"], rec["summary"])


if __name__ == "__main__":
    main()
