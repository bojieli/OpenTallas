#!/usr/bin/env python3
"""Microarchitecture analytical model: re-price the architecture DAG from elements, replicas, mappings,
ports, networks and wires (docs/MICROARCH_MODEL.md, AGENTS.md rule 1).

    python3 tools/uarch_model.py [--ctx 1048576] [--out results/uarch/v41_rom.json]

WHY.  tools/arch_budget_v41.py prices every node of the token DAG from die-level widths (spec.weight_macs,
spec.rom_bytes, ...): a matvec reads ROM at the WHOLE DIE's aggregate rate, activations and results cost
nothing to move, and wire delay is a separate lump (arch_lanes_v41.wire_mutation).  Composed hardware does not
work that way.  A matrix is read only as fast as the macros that hold it; its activation vector comes out of
the vector memory through a finite read port and a broadcast tree whose depth is set by the floorplan; its
results go back through a finite return network and VM write port; a stream-unit op runs at the lane count
actually built; and the index scan runs at the reader's measured sector rate.  This module keeps the
architecture's DAG, its workload and its dependency structure, and replaces each node's issue and depth with
those microarchitectural terms.  The same node therefore has an architecture price and a microarchitecture
price, and every gap between them is attributed to one named parameter.

A DESIGN is a dict of named parameters (PRESETS below): the as-built RTL (measured elements), the
architecture spec realised naively (the spec's widths but real mappings, ports and wires), and proposals.
Every constant cites its source; ASSUMED marks a number that has no measurement yet.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import hashlib
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_budget_v41 as A  # noqa: E402

# ---------------------------------------------------------------------------------------------------------
# Physical constants (sources in-line)
# ---------------------------------------------------------------------------------------------------------
WIRE_PS_PER_UM = 0.5997       # routed express-link fit (tools/chip_assembly/floorplans.wire_delay_model)
WIRE_OVERHEAD_PS = 189.5      # same fit: flop clk-q + setup + skew
UNCERTAINTY_PS = 60.0         # adopted clock uncertainty (briefing / W5 records)
ROM_MACRO_UM2 = 125.712 * 119.340   # ot_rom_8192x274_m8 (physical/asap7_memory_macros)
ROM_DEPTH = 8192
FP8_MAC_UM2 = 78.466875       # arch_budget_v41 unit_areas (ot_hdc_blockdot / 32, closed 1195.7 MHz)
BF16_MAC_UM2 = 509.352        # arch_budget_v41 unit_areas (ot_mac_bf16_fp32_pipe)
DFF_UM2 = 0.2916              # DFFHQNx1 (W5 unit areas, results/floorplan/qwen_o4_unit_areas.json)


def dsrom_field_spine_route_price(r=16, pq=0):
    """Immutable a721 spine, physical-only hold/slew repair budget.

    Rates and replicas come from the actual screen ports/kept source loops.
    The registered die wires and quantiser are outside this local screen.
    Physical buffering changes no architectural state, port or cycle edge.
    """
    if r not in (16, 128) or pq not in (0, 1):
        raise ValueError('Only the four handed-off source-bound screens')
    bw = sum([1,6,3,1,1,2,1,8,3,2,256,10,256,10,3,3,1,3,4,32,1024])
    r16_area = 39039.0 if pq == 0 else 39226.3
    return dict(schema='opentallas.dsrom.field_spine.route_price.v1',
        source_commit='a721a0448', RTL_immutable=True, new_RTL=False,
        source_sha256='1b1ca9190db389c4e93addbb5f73e2179cb914d51c649de19225683fd822baa7',
        replicas=1, regions=r, PQ=pq, MACs_per_cycle=0,
        memory_bytes_per_cycle=dict(VM_read=64*4, VM_write=r*4,
                                   stream_ROM=6, phase_ROM_two_ports=16),
        boundary_bits_per_cycle=dict(VM_read_payload=2048,
            return_payload_and_identity=69*r, VM_write_data_address_enable=52*r,
            broadcast=bw),
        required_logical_boundary_tracks=2048+69*r+52*r+bw,
        actual_channel_capacity_tracks=None,
        routing_capacity_proven=False,
        kept_instances=dict(g_ixb=32, g_ixq=8, g_sel=4*r,
            u_oh0=r, u_oh1=r, u_oh2=r, u_oh3=r, u_oh4=r,
            u_rsfm=r, u_cc=1, g_aqi=4, g_bwb=4, g_grp=r//16),
        kept_state_and_mux_cost='Existing source onehot/read/select/return replicas retained; no removed-state or mux credit',
        existing_R16_measured_screen_cell_area_um2=r16_area,
        actual_R128_screen_cell_area_um2=None,
        fixed_R128_core_area_um2=(477.84-2.16)**2 if r == 128 else None,
        repair_buffer_reservation_cells=1024,
        repair_buffer_cell_area_budget_um2=1024*0.10206,
        buffer_budget_is_not_measured_growth=True,
        slot_fit_after_repair='Require actual routed screen area/geometry and retained replicas; no full-die slot claim',
        new_architectural_FF_bits=0, new_memory_ports=0,
        added_pipeline_edges=0, added_single_user_token_cycles=0,
        inherited_measured_cycle_cost=dict(go=2, broadcast=1, return_stages=3,
            last_row_write=6, node=6, stream_length_delta=0, op_pair_spacing_delta=0),
        cycle_cost_source='results/rtl/dsrom_field_spine_20261004/DESIGN_NOTE.md and field_baseline/field_pq.json',
        inherited_registered_field_crossing_cycles=80,
        target_period_ns=0.833333, SS_setup_uncertainty_ps=60,
        FF_hold_uncertainty_ps=25, hold_corners=['WC','BC'],
        admission_GB=32 if r == 16 else 64, NUM_CORES=16,
        physical_adopted=False, actual_repair_gain_measured=False,
        screen_scope='Registered neighbours, two-cycle ROM models; quantiser stub and full die routes not qualified',
        adoption_requirement='Both baseline screens and both PQ screens require nonnegative SS/FF, zero SI/DRC/antenna, exact source and kept replicas; no tiny-negative tolerance')


def dsrom_source_program_inventory(words_by_home, *, tp=4, instruction_bits=2048, address_bits=14):
    """Finite compiler inventory; active content does not shrink physical ROM."""
    if tp != 4 or instruction_bits != 2048 or address_bits != 14:
        raise ValueError('selected native S81 instruction/entry/TP aperture required')
    if any(type(n) is not int or not 0 < n <= 1<<address_bits for n in words_by_home.values()):
        raise ValueError('actual native program capacity exceeded')
    return dict(words_per_rank_by_home=words_by_home,
        active_bytes_per_rank=sum(words_by_home.values())*instruction_bits//8,
        active_bytes_TP4=sum(words_by_home.values())*instruction_bits//8*tp,
        declared_address_capacity_words_per_home=1<<address_bits,
        instruction_bits_per_fetch=instruction_bits,
        declared_capacity_is_not_active_word_count=True,
        physical_ROM_area_and_port_cost=None,
        physical_storage_slot_bound=False,
        runtime_END_prefetch_restore_ACK_and_drain_cycles=None,
        compiler_added_hardware_FF=0,added_global_port_width_bits=0,
        new_hardware=False,adoption=False)


def dsrom_source_selection_restore_inventory():
    """Existing native SU BYP: exact L19.A0 restore, no physical credit.

    s81_minimum_su256.cpp::inputs interns identical A/B/C/D addresses before
    issuing scalar SourceIo requests. Four operands alias one 512-word span.
    The actual owner still owes native transport, writes, ACK and reverse drain.
    """
    return dict(added_instruction_words_per_rank=2,added_active_program_bytes_TP4=2048,
        copied_bytes_per_rank=2048,copied_bytes_TP4=8192,
        native_operand_references_per_rank=4*512,
        native_prefetch_scalar_reads_per_rank=512,
        native_prefetch_scalar_port_parallelism=1,
        native_publication_writes_per_rank=512,native_target_ACKs_per_rank=512,
        added_FF=0,added_global_port_bits=0,added_response_edges=None,
        SU_serial_clock_GHz=0.9,loaded_clock_binding_qualified=False,
        copy_cycles=None,transport_cycles=None,source_lease_hold_cycles=None,
        fence_drain_cycles=None,physical_area=None,physical_slots=None,adopted=False)


def dsrom_source_fragment_calendar(events, measured_service_cycles=None):
    """Price a compiler's finite source order; missing service costs stay unknown.

    This is a sequential candidate calendar, not a FIELD phase census or a
    claim that operand movement is free. TP4 service is maximum, never sum.
    Cost rows, when supplied by an actual owner, include prefetch, arithmetic,
    publication/ACK, context restore, collective and fragment drain cycles.
    """
    costs = {} if measured_service_cycles is None else measured_service_cycles
    rows = []
    finish = 0.0
    for ordinal, e in enumerate(events):
        if e['ordinal'] != ordinal or e['depends_on'] != ([] if ordinal==0 else [ordinal-1]):
            raise ValueError('literal sequential source calendar/order required')
        cost = costs.get(e['node'])
        seconds = None
        if cost is not None:
            if len(cost) != 4:
                raise ValueError('actual TP4 per-rank service costs required')
            values=[]
            for r in cost:
                if r['cycles'] < 0 or r['clock_hz'] <= 0:
                    raise ValueError('service cycle/clock price bounds')
                values.append(r['cycles']/r['clock_hz'])
            seconds=max(values)
        start=finish
        finish=None if start is None or seconds is None else start+seconds
        rows.append(dict(node=e['node'],depends_on=e['depends_on'],start_s=start,
                         service_s=seconds,finish_s=finish,
                         missing=e['missing']+([] if cost is not None else ['actual composed per-rank service cycles/clock'])))
    return dict(order='literal source order, sequential dependencies; no overlap credit',
                rank_composition='TP4 maximum',rows=rows,composed_seconds=finish,
                composition_complete=all(not r['missing'] for r in rows),
                unknown_costs_are_zero=False,added_hardware_area_um2=0,
                hardware_change='compiler-only candidate; existing physical capacity/homes unresolved',
                adoption=False)


def dsrom_recovery_decision_gate():
    """Source-pinned, conditional S81 recovery DAG prices; no hardware adoption.

    The timing authority is dsrom_1m_allmeasured.compose. Missing measured SU
    costs remain missing rather than becoming zero or inheriting fusion floors.
    """
    path = ROOT / "results/rtl/dsrom_recovery_20261004/decision_gate/model.json"
    record = json.loads(path.read_text())
    return dict(schema=record["schema"], record=str(path.relative_to(ROOT)),
                scenarios={k:dict(verdict=v["verdict"], adoption=v["adoption"],
                    composition_complete=v["composition_complete"],
                    conditional_cost=v["conditional_cost"], missing=v["missing"])
                    for k,v in record["scenarios"].items()},
                historical_contrast=record["historical_contrast"],
                comparison=record["comparison"],
                hardware_build_admitted=record["hardware_build_admitted"],
                full_die_trigger=record["full_die_trigger"])


def mbist_bira_pipeline_cost(dmax=256, entries=6, sram_banks=2, clock_ns=0.833):
    """Item8(b) repair-search pipeline; deterministic cycle/bit pricing, no closure claim."""
    chunks = (dmax + 15) // 16
    groups = (chunks + 3) // 4
    partial_bits = chunks * 5 + groups * 7
    extra_cycles_per_subset = 2
    extra_cycles_per_analysis = extra_cycles_per_subset * (1 << entries)
    return dict(schema="opentallas.uarch.mbist-bira-pipeline.v1", enabled_default=False,
        source="rtl/dft/ot_mbist_bira.sv S_SRCH/S_SRCH2/S_SRCH3; item8(b) prescribed pipeline",
        geometry=dict(dmax=dmax, entries=entries, sram_banks=sram_banks),
        search_cycles_per_subset=dict(baseline=3, successor=5),
        added_cycles_per_analysis=extra_cycles_per_analysis,
        worst_added_bist_cycles=sram_banks * extra_cycles_per_analysis,
        worst_added_bist_ns=clock_ns * sram_banks * extra_cycles_per_analysis,
        clean_bist_added_cycles=0, single_user_token_added_cycles=0,
        memory_port_bytes_per_cycle_delta=0, external_boundary_bits_per_cycle_delta=0,
        macs_per_cycle=0, replicas=1, shared_controller=True,
        pipeline_register_bits=partial_bits, added_state_bits=1,
        registered_boundaries_bits=[chunks * 5, groups * 7],
        fanin=dict(chunk_bits=16, group_chunks=4, final_groups=groups),
        fanout="each cm_r bit to one chunk; each chunk count to one group; no new external fanout",
        area_estimate_um2=(partial_bits + 1) * DFF_UM2,
        area_status="ESTIMATE flop-only; adder/mux/clock/routing delta requires measured shell",
        routing_tracks_status="ESTIMATE internal local tree, no added shell ports; actual route required",
        floorplan_status="existing shell vehicle; slot fit requires measured total area",
        clock_status="UNVALIDATED: require routed SS60/FF25 at 0.833ns, DRC/antenna/electrical zero")

# weights delivered by one ROM word, by the node's format (W1 bank map: FP4 two 136-bit 32-blocks per
# 274-bit word, FP8 one 264-bit block, BF16 16 x 16 bit, FP32 8 x 32 bit)
WEIGHTS_PER_WORD = {"fp4": 64, "fp8": 32, "bf16": 16, "fp32": 8}

# K (input width) of every weight node of the V4.1 DAG, per die (tools/decode_critical_path.v41_graph;
# configs/models/candidates/deepseek-v4.1-flash.json).  Rows per die = die MACs / K.
NODE_K = {
    "a_proj": 5120, "wq_b": 1280, "wo_a": 4096, "wo_b": 2048, "router": 5120, "shared_gu": 5120,
    "experts_gu": 5120, "down": 2304, "hc.fn": 20480, "cmp.wk": 512, "wkv": 3072, "lm_head": 5120,
}
NODE_FMT = {
    "a_proj": "fp8", "wq_b": "fp8", "wo_a": "bf16", "wo_b": "fp8", "router": "bf16", "shared_gu": "fp8",
    "experts_gu": "fp4", "down": "fp4", "hc.fn": "fp32", "cmp.wk": "bf16", "wkv": "fp8", "lm_head": "bf16",
}
# floorplan region of each weight node's macros (W1 pack: results/floorplan/v41_pack_expanded_woa.json)
NODE_REGION = {
    "experts_gu": "expert", "down": "expert", "wo_a": "me", "a_proj": "dense", "wq_b": "dense",
    "wo_b": "dense", "shared_gu": "dense", "router": "dense", "cmp.wk": "dense", "wkv": "spill",
    "lm_head": "dense", "hc.fn": "hub",
}



def dsrom_baseline_link_clock_repair(flit_bytes=64, credits=512, seqw=10,
                                     channel_cycles=156, traversals=81):
    """Default-off baseline reliability repair, not the rejected cut-through lever.

    Source: ot_dsrom_link_rt.sv; screen_base_rt SS -417.3ps/FF +4.2ps,
    rr_f[37] -> reverse CRC/ACK/rewind -> st_replays[27]. Retain the
    baseline payload, lane/PHY budgets, cumulative credits and replay storage.
    One registered launch payload cuts window/replay-select from forward CRC.
    Receive CRC flags align with existing frame registers (zero added edges).
    """
    if min(flit_bytes, credits, seqw, channel_cycles, traversals) < 1:
        raise ValueError("positive link dimensions required")
    if credits > 2 ** (seqw - 1):
        raise ValueError("ambiguous sequence window")
    w = 8 * flit_bytes
    cw = math.ceil(math.log2(credits + 1))
    fpw = w + seqw + 1
    baseline_loop = 2 * channel_cycles + 2 + 2 + 6
    repaired_loop = baseline_loop + 1
    # Payload+valid head and two aligned CRC flags. Status counters retain
    # their cycle-visible values: bounded 8-bit parallel increment segments.
    ff = fpw + 1 + 2
    return dict(candidate="DSROM_BASELINE_LINK_RT_CLOCK1", default_enabled=False,
        baseline_source_sha256=hashlib.sha256((ROOT / "rtl/dsrom_sys/ot_dsrom_link_rt.sv").read_bytes()).hexdigest(),
        baseline_ss_setup_ps=-417.3, baseline_ff_hold_ps=4.2,
        period_ps=1000/1.2, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        macs_per_cycle=0, memory_bytes_per_port_edge=flit_bytes,
        replay_write_ports=1, replay_read_ports=1, fifo_write_ports=1, fifo_read_ports=1,
        forward_bits_per_edge=fpw+32, reverse_bits_per_edge=1+seqw+cw+32,
        replicas=dict(launch_head=1, aligned_crc_flags=2, status_counters=9,
                      status_counter_8bit_segments=36),
        added_ff_bits=ff, added_ff_body_um2_proxy=ff*DFF_UM2,
        added_ff_50pct_reservation_um2_proxy=2*ff*DFF_UM2,
        added_comb_area_um2=None, actual_slot_fit=None,
        added_packet_edges=1, added_ack_generation_edges=0,
        added_ack_credit_roundtrip_edges=1,
        diagnostic_observation_delay_edges=0,
        baseline_credit_loop_edges=baseline_loop, repaired_credit_loop_edges=repaired_loop,
        credits=credits, sequence_bits=seqw,
        ideal_credit_bound_flits_per_edge=min(1, credits/repaired_loop),
        bytes_per_edge_bound=flit_bytes*min(1, credits/repaired_loop),
        selected_stage_hops=traversals,
        added_single_user_stage_chain_us=traversals/1.2e3,
        baseline_hop_cycles=909, candidate_hop_cycles_lower_bound=911,
        hop_two_endpoint_added_edges=2,
        # Board then package fanout: one extra launch edge in each endpoint.
        added_single_user_two_endpoint_chain_us=2*traversals/1.2e3,
        token_return_8_traversals_added_us=8/1.2e3,
        token_latency_not_measured=True, error_replay_latency_not_measured=True,
        routing_tracks_needed=fpw+32+1+seqw+cw+32,
        channel_tracks_available=None, routing_fit=False,
        minimum_context=dict(credits=16, seqw=5, flit_bytes=64,
            queue_depth_not_selected_512=True, die_um=[240,180], core_um=[236,176],
            baseline_mapped_cell_um2=13622.28354,
            positive_logic_buffer_reserve_um2_proxy=5000,
            reserved_cell_um2_proxy=13622.28354+ff*DFF_UM2+5000,
            cell_area_capacity_um2_at_50pct=236*176*.5,
            source_grid="ORFS asap7_tech_1x_201209.lef M4 H/M5 V pitch0.048um",
            gross_directional_tracks=dict(horizontal=math.floor(176/.048),vertical=math.floor(236/.048)),
            tracks_after_50pct_clock_PG_policy_reserve=dict(horizontal=math.floor(176/.048/2),vertical=math.floor(236/.048/2)),
            physical_obstruction_union_measured=False,
            boundary_target=dict(input_max_ps=100,input_min_ps=30,output_max_ps=60,output_min_ps=25,load_fF=.6),
            boundary_basis="Candidate registered parent: SS measured launch92.8ps +7.2ps route budget; setup34.1ps +25.9ps output budget; actual routes/corner closure pending.",
            prebuild_reserved_capacity_pass=(13622.28354+ff*DFF_UM2+5000<=236*176*.5),
            context_route_allowed=True, full_queue_clock_qualified=False),
        ss_ff_qualified=False, physical_admitted=False,
        limits="FF price is a source proxy; comb/CTS/PG/routes/loaded SSFF must be measured. No PHY or cut-through gain.")


def node_key(name: str) -> str:
    tail = name.split(".", 1)[1] if "." in name else name
    for k in sorted(NODE_K, key=len, reverse=True):
        if tail.endswith(k):
            return k
    return ""


WIRE_PS_PER_UM_LOADED = 0.76  # W3 real-technology channel runs: 0.72-0.81 ps/um under 300-1,500 routed wires
                              # (branch claude/w3-v41-die-assembly 01ef74dc, v41_corridor records)


def wire_cycles(um: float, clock_hz: float, ps_per_um: float = WIRE_PS_PER_UM) -> int:
    """One-way cycles to cross `um` of registered wire (W1 rule: registers = ceil(L/seg) - 1, +1 cycle)."""
    period_ps = 1e12 / clock_hz
    seg = (period_ps - UNCERTAINTY_PS - WIRE_OVERHEAD_PS) / ps_per_um
    regs = max(0, math.ceil(um / seg) - 1)
    return regs + 1 if regs > 0 else (1 if um > 0 else 0)


def rom_spine_publication_price(*, roots=128, elements=2417, phases=1):
    """One paired publication edge; alternatives, never two free pipe stages.

    Selected enclosing bus: each root {valid,row16,pos3,fp32,bf16,error}.
    E1 component bus: each bank {valid,value32,row16,seg5,nseg5,error,pos3}
    plus per-element busy/fault. Actual parent capture owns phase identity and
    remains live until real VM acceptance/drain; no new identity ledger here.
    Liberty SS DFFASRHQNx1: area .37908 um2, CLK .433982 fF.
    All bits conservatively cold-reset; clock buffers/wire and fault steering
    are additional unknown positive costs, not free energy or closure.
    """
    if min(roots, elements, phases) < 1:
        raise ValueError("positive actual source geometry required")
    root_bits = 69 * roots + 1
    element_bits = 63 * 2 + 2
    def cost(bits):
        return dict(ff_bits=bits, ff_cell_body_um2=bits * .37908,
                    placement_floor_um2_at50pct=bits * .37908 * 2,
                    clock_pin_capacitance_ff=bits * .433982,
                    clock_buffers_wire_energy_w=None,
                    fault_fanout_buffers_mux_area_um2=None)
    return dict(selected_root_boundary=cost(root_bits),
                E1_component_alternative=cost(element_bits),
                E1_replicated_alternative=cost(element_bits * elements),
                boundary_payload_bits_per_cycle=69 * roots,
                boundary_payload_bytes_per_cycle=69 * roots / 8,
                compute_macs_per_cycle=0,
                VM_commit_payload_bytes_per_cycle=4 * roots,
                added_external_boundary_bits_per_cycle=0,
                added_buffered_net_bits=root_bits,
                root_publication_replica_count=roots,
                E1_publication_replica_count=elements,
                result_added_edges_per_phase=1,
                fault_added_edges=1, issue_interval_edges=1,
                phase_chain_added_edges=phases,
                phase_chain_added_ns=phases * (1 / 1.2),
                parent_busy="Existing phase/capture ownership through positive VM commit and capture_drained; never a delayed idle credit",
                fault_policy="Aligned fault drives existing warm-quarantine request, inhibits writes, retains accepted debt; prior writes not rolled back",
                root_fault_quarantine_fanout=roots,
                publication_visibility_guard=dict(
                    purpose="Existing capture_live/drained exports include the actual pending publication copy before consumer/retirement",
                    added_FF=0, added_edges=0,
                    quiet_OR2_count=2 * roots + 1, quiet_INV_count=1,
                    quarantine_AND2_count=roots, quarantine_OR2_count=roots,
                    export_OR3_count=1, export_AND3_count=1,
                    export_INV_count_no_CSE=2,
                    cell_body_um2_no_CSE=(4 * roots + 3) * .08748 + 3 * .04374,
                    OR2_AND2_OR3_AND3_cell_area_um2=.08748,
                    INV_cell_area_um2=.04374,
                    basis="ASAP7 RVT SS SIMPLE211120/INVBUF220122 Liberty; explicit Boolean construction, not synthesis/loaded delay",
                    raw_fault_timing="Still timed through source publication_quiet to actual phase live/drained/C8 guards; no free fault-blind edge or falsepath",
                    quiet_control_sink_count=4,
                    loaded_clock_wire_fault_fanout_cost=None,
                    paired_register_timing_gain_guaranteed=False),
                E1_fault_bank_fanout=2,
                tracks_slot_fit=None, gate_power_w=None,
                source_exactness_pass=False, connected_consumer_gate_pass=False,
                SSFF_closed=False, physical_admission=False)


def rom_spine_repin_price(displacements_um, setup_slack_ps, hold_slack_ps):
    """Same-frame pin-only recipe: bound both shorter and longer Manhattan wires.

    Charge the upper 0.81 ps/um of W3's measured loaded-channel range, rather
    than the unloaded express-link proxy. Margins are from the unchanged CTS
    snapshot, including SS60/FF25. This is an analytical admission bound, not
    routed timing or a guarantee that cell placement and buffering stay fixed.
    """
    upper_loaded_ps_per_um = 0.81
    longest = max(displacements_um, default=0.0)
    delta = longest * upper_loaded_ps_per_um
    setup_left = setup_slack_ps - delta
    hold_left = hold_slack_ps - delta
    fits = setup_left > 0 and hold_left > 0
    return dict(max_pin_displacement_um=round(longest, 6),
                total_pin_displacement_um=round(sum(displacements_um), 6),
                wire_ps_per_um=upper_loaded_ps_per_um,
                wire_basis="W3 loaded-channel measured range 0.72-0.81 ps/um; upper endpoint",
                incremental_wire_delay_bound_ps=round(delta, 6),
                estimated_setup_remaining_ps=round(setup_left, 6),
                estimated_hold_remaining_ps=round(hold_left, 6),
                analytical_budget_fits=fits, area_delta_mm2=0,
                protocol_cycle_delta=0 if fits else None,
                power_delta_w=None, routed_closure=False,
                assumption="Same endpoints and buffering; displacement bounds incremental Manhattan wire only")


# ---------------------------------------------------------------------------------------------------------
# Designs.  Every resource is a named parameter; PRESETS differ only where stated.
# ---------------------------------------------------------------------------------------------------------
BASE = dict(
    name="base",
    # ROM weight array
    macros=13798,                 # busiest die, stage 1 rank 3 (W1 bank map, v41_die_bankmap_busiest_expanded_woa)
    mapping="contiguous",         # "contiguous": a matrix slice owns its full-depth banks (W1 map);
                                  # "striped": every matrix's rows interleaved over all macros (W8)
    expert_fill_rows=5760,        # rows of an expert matrix per bank in the contiguous map (70.3% of 8192)
    bf16_stripe_macros=None,      # striped mapping: macros that carry BF16 lanes (None = every macro); BF16
                                  # matrices (wo_a, router, cmp.wk, lm_head) stripe over only these
    mac_lanes_per_macro=None,     # None: one word per cycle per macro (lanes sized to the word); else a cap
    weight_macs_die=None,         # optional die-wide MAC cap (as-built: 512 QE block-dot lanes)
    bf16_macs_die=None,
    elem_fill=78,                 # measured: W2 QE ROM/MAC neighbourhood accept -> first result 78 cycles
                                  # (claude/w2-rommac, qe_romac_exactness.json; the formula gave 45-60)
    wire_ps_per_um=WIRE_PS_PER_UM_LOADED,
    # vector memory ports (elements of 32 bit per cycle)
    vm_read_elems=4,              # x operand path: G4 = 4 FP32 elements/cycle (V41_FLOORPLAN_CONNECTIVITY 2)
    vm_write_elems=64,            # collective/result write: 4 x 512-bit words (W1 handoff 1)
    # networks
    bcast_um={"expert": 20465.5, "dense": 9040.0, "me": 7690.0, "spill": 9590.0, "hub": 0.0},
                                  # VM -> farthest macro of each region (W1 latency_crossings, manhattan)
    return_fanin=8,               # result tree fan-in per registered level (ASSUMED)
    return_leaf_elems=None,       # None: every holding macro is a leaf of the return tree
    # stream unit / SFU
    su_lanes=16, sfu_lanes=8,     # as-built SU (V41_DIE_ENGINE_PROFILE: SUN 16 / SUM 8)
    # attention, index, select
    att_macs=32768,               # as-built attention products (NT64 x H16 x TD32)
    att_measured_job_cycles=609,  # measured H16/D512/T640 process cycles (results/rtl, e1ac020d)
    su_softmax_measured_cycles=3280,  # measured H16/T640 actual SU softmax + divide (b674827f)
    use_measured_attention=True,
    idx_reader_Bpc=60 * 32,       # measured four-stack reader: 557,056 sectors in 9,278 cycles (TASKS)
    idx_macs=1024,                # as-built indexer FP4 block-dot lanes
    collective_cycles=232,        # measured: 12 layer-0 collectives in 2,780 cycles (V41_DIE_ENGINE_PROFILE)
)

# Distributed VM (root decision 2026-09-29): the VM is lane-group-local banks inside HUB_SU_VECTOR (128 groups of 8
# lanes, element i in group i mod 128).  Register stages from the W1 hub geometry (results/floorplan/
# v41_pack_expanded_woa.json), SU lane array 11.96 mm2 as a 3,458 um square abutting the HUB_VM strip and centred on
# it, at 0.92 ns / 0.76 ps/um:
#   x gather     farthest group -> VM port (west edge centre): 3,458 + 1,729 = 5,187 um      -> 6
#   result scatter  VM port -> farthest group, the same run                                    -> 6
#   collective write  with the collective endpoint at the VM port (W10 placement, root 2026-09-29): the scatter
#                     tree alone -> 6 (11 from HUB_COLLECTIVE's W1 position)
#   SU results   reducer root at the array centre -> farthest group 3,458 um (element writes are local) -> 4
VM_DIST = dict(vm_x_gather_stages=6, vm_ret_scatter_stages=6, vm_coll_write_stages=6, su_ret_stages=4)
# the SU's broadcast tree to the farthest lane (W11 SU worker's placement derivation, root-accepted)
SU_BCAST = dict(su_bcast_stages=4)

PRESETS = {
    # the RTL as elaborated today (W1 rung 1 profile + measured component gates)
    "as_built": dict(BASE, name="as_built", weight_macs_die=512, bf16_macs_die=64, idx_macs=1024,
                     vm_read_elems=4, vm_write_elems=4),
    # the architecture spec's widths, realised with the W1 contiguous bank map and today's ports
    "spec_contiguous": dict(BASE, name="spec_contiguous", su_lanes=1024, sfu_lanes=256, att_macs=37184,
                            idx_macs=248832, use_measured_attention=False, collective_cycles=None,
                            idx_reader_Bpc=None),
    # the spec's widths with every matrix striped over every macro (W8 sizing)
    "spec_striped": dict(BASE, name="spec_striped", mapping="striped", su_lanes=1024, sfu_lanes=256,
                         att_macs=37184, idx_macs=248832, use_measured_attention=False, collective_cycles=None,
                         idx_reader_Bpc=None),
}
# proposals: striped rows plus VM ports sized so that neither x nor the result stream binds a projection
PRESETS["prop_vm64"] = dict(PRESETS["spec_striped"], name="prop_vm64", vm_read_elems=64, vm_write_elems=128)
PRESETS["prop_vm256"] = dict(PRESETS["spec_striped"], name="prop_vm256", vm_read_elems=256, vm_write_elems=512)
PRESETS["proposal"] = dict(PRESETS["spec_striped"], name="proposal", vm_read_elems=64, vm_write_elems=128,
                           bf16_stripe_macros=2048, collective_cycles=232, row_split="ksplit",
                           # W11 decisions (2026-09-29): indexer = 16 NK=4 score slices, 64 keys/cycle (beat-aligned
                           # with the reader; reader-bound); attention NL=4 tiles (32,768 products) + PWORDS=2
                           # loader; SU per the RTL layout rule (+14 cycles/layer) with its own VM ports (~6 mm2)
                           idx_macs=262144, att_macs=32768, su_layout_extra_cycles=14, su_vm_ports_mm2=6.0,
                           # ROOT DECISION 2026-09-29 (W15): collectives priced from the RTL measurement of the
                           # adopted design -- endpoint at the die centre (W3 placement, 17 wire stages to the link
                           # PHYs), direct T1 links (no relay), receive depth 1,024 (results/rtl/w15_collectives.json
                           # v41p17_r0d1024_sweep fit); collective_cycles is then unused
                           collective_w15="v41p17_r0d1024",
                           # ROOT DECISION 2026-09-29 (W11): distributed VM (lane-group banks) and SU broadcast stages
                           **VM_DIST, **SU_BCAST)
PRESETS["proposal_whole"] = dict(PRESETS["proposal"], name="proposal_whole", row_split="whole")
PRESETS["proposal_ksplit"] = dict(PRESETS["proposal"], name="proposal_ksplit", row_split="ksplit")
PRESETS["prop_vm256_measured"] = dict(PRESETS["prop_vm256"], name="prop_vm256_measured", su_lanes=16, sfu_lanes=8,
                                      att_macs=32768, use_measured_attention=True, idx_reader_Bpc=60 * 32,
                                      idx_macs=1024, collective_cycles=232)


# ---------------------------------------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------------------------------------
def _spec():
    rec = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())
    fields = {f.name for f in dataclasses.fields(A.Spec)}
    return A.Spec(**{k: v for k, v in rec["required_spec"].items() if k in fields})


_ARCH_CACHE = {}


def arch_graph(ctx: int):
    """The architecture-level priced DAG at the required spec (the model this one refines); a fresh copy."""
    if ctx not in _ARCH_CACHE:
        r = A.price(_spec(), ctx=ctx, keep=True)
        b = r.pop("_built")
        _ARCH_CACHE[ctx] = (r, b)
    r, b = _ARCH_CACHE[ctx]
    return dict(r), copy.deepcopy(b)


EXPERT_ROWS = {"experts_gu": 1152, "down": 1280}   # rows of ONE expert's slice per die (w1|w3 2 x 576; w2 1280)
FADD_PIPE = 5                                       # ot_fp32_add_rne_pipe latency (closed 0.7 ns)


def expected_max_load(balls: int, bins: int, trials: int = 4000, seed: int = 7) -> float:
    """E[max bin occupancy] of `balls` placed uniformly at random in `bins` (Monte Carlo, fixed seed)."""
    import random
    if bins <= 1:
        return float(balls)
    rng = random.Random(seed)
    tot = 0
    for _ in range(trials):
        cnt = {}
        for _b in range(balls):
            k = rng.randrange(bins)
            cnt[k] = cnt.get(k, 0) + 1
        tot += max(cnt.values())
    return tot / trials


def next_pow2(x: int) -> int:
    return 1 << max(0, math.ceil(math.log2(max(1, x))))


CHAIN_FLOOR = 8 * 5   # golden chunk sum = 8 sequential FP32 adds x adder latency 5: no stream round is shorter


def striped_read(d, key, rows, K, fmt):
    """Cycles to read `rows` x K of format `fmt` striped over the ROM field (W10-validated rules):
    whole rows cost ceil(K / weights-per-word) words in one macro; a K split of s puts power-of-two-aligned runs
    of golden chunks (next_pow2(ceil(C / s)) chunks) in each macro, exact under the golden csum padded tree;
    an expert's split is chosen so ONE expert's tile covers the whole field (no tile collisions); every stream
    round lasts at least the chunk-sum chain recurrence.  Returns (t_read, split, adder_levels, holding)."""
    n = d["macros"]
    if fmt == "bf16" and d.get("bf16_stripe_macros"):
        n = min(n, d["bf16_stripe_macros"])
    wpw = WEIGHTS_PER_WORD[fmt]
    C = math.ceil(K / 256)
    s = 1
    seg_words = math.ceil(K / wpw)
    unit_rows = EXPERT_ROWS[key] if key in EXPERT_ROWS else rows
    seg_per_row = 1
    if d.get("row_split", "whole") == "ksplit":
        while s < C and unit_rows * s < n:
            s *= 2
        s = min(s, next_pow2(C))
        if fmt == "fp4":                     # an FP4 word carries block b of two sibling chunks: segments are
            s = min(s, max(1, next_pow2(C) // 2))   # whole chunk pairs (W10 generator rule)
        if s > 1:
            c_seg = next_pow2(math.ceil(C / s))      # golden-aligned chunks per segment
            seg_words = math.ceil(min(K, c_seg * 256) / wpw)
            seg_per_row = math.ceil(C / c_seg)       # a row has ceil(C/c) segments, fewer than s when C is not
                                                     # a power of two (W10: C=20, c=2 -> 10 segments)
    segs = rows * seg_per_row
    holding = min(n, segs)
    if key in EXPERT_ROWS and EXPERT_ROWS[key] * seg_per_row < n:
        active = max(1, round(rows / EXPERT_ROWS[key]))
        tiles = max(1, n // (EXPERT_ROWS[key] * seg_per_row))
        t = expected_max_load(active, tiles) * seg_words
    else:
        t = math.ceil(segs / n) * seg_words
    if d.get("row_split") == "ksplit":
        t = max(t, CHAIN_FLOOR)
    al = math.ceil(math.log2(s)) if s > 1 else 0
    return t, s, al, holding


def price_matvec(nd, name, d, clock, c):
    key = node_key(name)
    if not key or key == "hc.fn":
        return None
    sw = nd["sweep"]
    f = A.die_fraction(name, c, 4)
    macs = sw["macs"] * f
    fmt = NODE_FMT[key]
    K = NODE_K[key]
    rows = max(1.0, macs / K)
    wpw = WEIGHTS_PER_WORD[fmt]
    words = macs / wpw
    region = NODE_REGION[key]
    ksplit = 1
    adder_levels = 0
    t_x = K / d["vm_read_elems"]
    if d["mapping"] == "striped":
        if key == "a_proj":
            # a_proj fuses FP8 (wq_a, wkv) with BF16 rows (index weights_proj when the layer scans; compressor
            # wkv/wgate on KV-source layers), which stripe over the BF16 macros and need x in BF16 lane order:
            # two sequential sub-phases and x streamed twice (W10 interim report)
            L = nd["layer"]
            mode, r = c["modes"][L], c["compress_ratios"][L]
            bf_rows = ((c["index_heads"] if mode.get("scans_index") else 0)
                       + ((2 if r == 2 else 1) * c["head_dim"] if L in c["kv_source_layer_ids"] else 0)) / 4
            parts = [(max(1.0, rows - bf_rows), "fp8")] + ([(bf_rows, "bf16")] if bf_rows else [])
            t_x *= len(parts)                # FP8/FP4 share one FP8 x stream; only BF16 needs a second (W10)
        else:
            parts = [(rows, fmt)]
        t_read, holding = 0.0, 0
        for prow, pfmt in parts:
            tr, ks, al, hd = striped_read(d, key, prow, K, pfmt)
            t_read += tr
            ksplit, adder_levels, holding = max(ksplit, ks), max(adder_levels, al), max(holding, hd)
    else:
        depth_rows = d["expert_fill_rows"] if region == "expert" else ROM_DEPTH
        holding = max(1, math.ceil(words / depth_rows))
        t_read = math.ceil(words / holding)
    lanes_cap = []
    if key in ("wo_a", "router", "cmp.wk", "lm_head"):
        if d["bf16_macs_die"]:
            lanes_cap.append(macs / d["bf16_macs_die"])
    elif d["weight_macs_die"]:
        lanes_cap.append(macs / d["weight_macs_die"])
    t_mac = max(lanes_cap) if lanes_cap else 0.0
    t_ret = rows / d["vm_write_elems"]
    issue_c = max(t_read, t_mac, t_x, t_ret)
    bind = max((("rom_read", t_read), ("mac", t_mac), ("vm_read_x", t_x), ("vm_write_ret", t_ret)),
               key=lambda kv: kv[1])[0]
    leaves = holding if d["return_leaf_elems"] is None else d["return_leaf_elems"]
    tree = math.ceil(math.log(max(2, leaves), d["return_fanin"]))
    wire = 2 * wire_cycles(d["bcast_um"][region], clock, d.get("wire_ps_per_um", WIRE_PS_PER_UM))
    # distributed VM (W11, root 2026-09-29): x is gathered from the lane-group banks to the VM port, results are
    # scattered back to them -- register stages from the hub geometry (VM_DIST below)
    wire += d.get("vm_x_gather_stages", 0) + d.get("vm_ret_scatter_stages", 0)
    depth_c = d["elem_fill"] + wire + tree + adder_levels * FADD_PIPE
    return dict(key=key, fmt=fmt, K=K, rows=rows, words=words, holding=holding, region=region,
                t_read=t_read, t_mac=t_mac, t_x=t_x, t_ret=t_ret, issue=issue_c, bind=bind,
                depth=depth_c, wire=wire, tree=tree, ksplit=ksplit, adder_levels=adder_levels)


def evaluate(d: dict, ctx: int = 1048576):
    arch, b = arch_graph(ctx)
    g = b.g
    E = A._env()
    clock, c = E["clock"], E["c"]
    cyc = 1.0 / clock
    notes = {}
    for name, nd in g.nodes.items():
        k = nd["kind"]
        if k == "matvec":
            r = price_matvec(nd, name, d, clock, c)
            if r is None:
                continue
            nd["issue"] = r["issue"] * cyc
            nd["issue_cat"] = "weight_sweep"
            nd["depth"] = r["depth"] * cyc
            nd["_uarch"] = r
        elif k in ("vector", "reduce"):
            if nd.get("resource") and nd["resource"][0] in ("su", "sfu"):
                lanes_arch = _spec().sfu_lanes if nd["resource"][0] == "sfu" else _spec().su_lanes
                n_el = nd["resource"][1] * lanes_arch
                lanes = d["sfu_lanes"] if nd["resource"][0] == "sfu" else d["su_lanes"]
                nd["issue"] = math.ceil(n_el / lanes) * cyc
        elif k == "kvscan":
            if name.endswith("idx.score") and d["idx_reader_Bpc"]:
                n_keys = int(nd["desc"].split()[2])
                by = n_keys * A.IDX_KEY_B
                macs = n_keys * c["index_heads"] * c["index_head_dim"]
                t = max(by / d["idx_reader_Bpc"], macs / d["idx_macs"])
                nd["issue"] = t * cyc
            elif name.endswith("idx.score"):
                n_keys = int(nd["desc"].split()[2])
                macs = n_keys * c["index_heads"] * c["index_head_dim"]
                nd["issue"] = max(nd["issue"], macs / d["idx_macs"] * cyc)
            elif d["use_measured_attention"] and name.endswith(".scores"):
                # PWORDS=2 loader: measured 449 cycles at T640 (claude/w11-attn c80877d8); else the PWORDS=1 job
                nd["issue"] = (449 if d.get("att_pwords") == 2 else d["att_measured_job_cycles"]) * cyc
                nd["depth"] = 0.0
            elif d["use_measured_attention"] and name.endswith(".pv"):
                nd["issue"] = 0.0      # the measured job covers scores + PV
        elif k == "collective" and d.get("collective_latency_s") is not None:
            nd["depth"] = d["collective_latency_s"] + (d["collective_cycles"] or 0) * cyc
        elif k == "collective" and d.get("collective_w15"):
            nd["depth"] = w15_collective_s(d["collective_w15"], nd["op"], nd["payload"], nd.get("span") or 4)
            nd["issue"] = 0.0          # the measured issue -> last commit latency includes the payload stream
        elif k == "collective" and d["collective_cycles"]:
            nd["depth"] = max(nd["depth"], d["collective_cycles"] * cyc)
        if k == "collective" and d.get("vm_coll_write_stages"):
            nd["depth"] += d["vm_coll_write_stages"] * cyc      # the collective DMA's write into the lane groups
    if d.get("su_layout_extra_cycles"):
        for name, nd in g.nodes.items():
            if name.endswith(".attn.exp"):
                nd["issue"] += d["su_layout_extra_cycles"] * cyc
    if d["use_measured_attention"]:
        # the measured SU softmax chain replaces exp + den + normalize issue (they are one measured process)
        for name, nd in g.nodes.items():
            if name.endswith(".attn.exp"):
                nd["issue"] = d["su_softmax_measured_cycles"] * cyc
                nd["depth"] = 0.0
            elif name.endswith((".attn.den", ".attn.normalize")):
                nd["issue"] = 0.0
    fin = g.solve(True)
    T = fin[b.sink]
    path = g.path(b.sink)
    cats = {}
    for n in path:
        for k_, v in g.contrib[n].items():
            cats[k_] = cats.get(k_, 0.0) + v
    # critical-path time by node family (layer-independent suffix)
    fam = {}
    for n in path:
        nd = g.nodes[n]
        tail = n.split(".", 1)[1] if n.startswith(("L", "E")) and "." in n else n
        t = sum(g.contrib[n].values())
        fam[tail] = fam.get(tail, 0.0) + t
    top = sorted(fam.items(), key=lambda kv: -kv[1])[:25]
    mv = {}
    for name, nd in g.nodes.items():
        u = nd.get("_uarch")
        if u and name.startswith("L20."):
            mv[name] = {k_: (round(v, 1) if isinstance(v, float) else v) for k_, v in u.items()}
    return dict(design=d["name"], ctx=ctx, clock_hz=clock, T_us=T * 1e6, tokens_s=1.0 / T,
                arch_T_us=arch["T_s"] * 1e6, arch_tokens_s=arch["tokens_s_per_user"],
                breakdown_us={k_: round(v * 1e6, 3) for k_, v in sorted(cats.items(), key=lambda kv: -kv[1])},
                critical_path_by_node_us={k_: round(v * 1e6, 3) for k_, v in top},
                layer20_matvecs=mv, _g=g)


# ---------------------------------------------------------------------------------------------------------
# Power ledger (busiest layer die): dynamic energy per token from every priced node's work, network wire energy,
# clock and leakage by area class, HBM interface idle; at the single-user rate and at pipeline saturation.
# Constants: configs/hardware/technology.json (energy.*, power.*), except WIRE_J_PER_BIT_MM (below).
# ---------------------------------------------------------------------------------------------------------
TECH = json.loads((ROOT / "configs/hardware/technology.json").read_text())
_E = TECH["energy"]
_P = TECH["power"]
E_MAC = {k: v["value"] for k, v in _E["mac_energy_j_per_op"].items()}
E_ROM_B = _E["rom_read_j_per_byte"]["value"]
E_SRAM_B = _E["sram_read_j_per_byte"]["value"]
E_HBM_B = _E["hbm_j_per_byte"]["value"]
E_DELIVER_B = _E["operand_delivery_j_per_byte"]["value"]
E_LINK_BIT = 0.5 * (_E["link_j_per_bit"]["ucie_advanced"]["value"] + _E["link_j_per_bit"]["board_serdes_112g"]["value"])
CLOCK_J_MM2 = _P["clock_energy_j_per_mm2_per_cycle"]["value"]
LEAK = {k: v["value"] for k, v in _P["static_leakage_w_per_mm2"].items()}
HBM_IDLE_W_STACK = _P["memory_interface_idle_w_per_stack"]["value"]
E_HBM_IF_B = _P["memory_interface_active_j_per_bit"]["value"] * 8   # on-die PHY/controller share of an HBM byte;
                                                                    # the rest of E_HBM_B dissipates in the stack
COOLING_LIMIT_W = 474.56      # liquid, two-die package (results/arch/v41_hbm_switched.json rom_worst_die_w)
WIRE_J_PER_BIT_MM = 0.1e-12   # ASSUMED: repeated RC global wire, C ~0.2 fF/um, 0.7 V, activity 0.5, x2 repeaters;
                              # a 45 nm survey puts repeated RC wire at ~0.4 pJ/bit/mm (sensitivity row)
SFU_OPS_PER_ELEM = 10         # ASSUMED FP32-op equivalents per exp/sigmoid/divide element
BYTES_PER_WORD = {"fp4": 34, "fp8": 33, "bf16": 32, "fp32": 32}
# ROM field power, MEASURED (W18, 2026-09-30): OpenSTA report_power on W10 p5's routed pair (6_final.odb + SPEF, TT
# 0.7 V, 1.087 GHz, input toggle density 0.5).  A pair = 2 ROM macros + their strip logic.  Busy 229.6 mW (seq 45.1,
# comb 128.0, clock tree 23.7, ROM macros 32.7); idle with the clock running 83.5 mW (clock tree 23.7, flop clock pins
# 27.0, ROM macro clock 32.7, leakage 0.22); idle with an ideal per-pair ICG that also stops the ROM macro clock
# 0.22 mW (leakage: ROM 0.20, cells 0.02).  These replace the area-based clock and leakage of the ROM field (the old
# terms under-stated its clock ~45x); the hub keeps the area-based terms, UNCALIBRATED.
PAIR_W = dict(clock_hz=1.087e9, busy=0.2296, idle_ungated=0.0835, idle_icg=0.00022, leak_rom=0.00020,
              leak_cell=0.00002, placed_pairs=7102,
              src="W18 report_power on W10 p5 routed pair (claude/w18-die-assembly, 2026-09-30); placed pairs = "
                  "results/floorplan/v41_pack_refit_w10_interim.json capacity.used_pair_rows (W10 428c3631)")


# Stage power gating (W18, 2026-09-30): a 16-pair cluster measures 14-17 mV IR; the power-switch rings that hold a
# 10 mV budget take 5% of the cluster area.  Pair outline 513.756 x 131.76 um (W18, from W10 p5's abstract).
SWITCH_RING = dict(cluster_area_frac=0.05, pair_um2=513.756 * 131.76, slots=9931,
                   src="W18 cluster PSM + switch-ring sizing (claude/w18-die-assembly, 2026-09-30); slots = "
                       "v41_pack_refit_w10_interim.json capacity.pair_row_slots")


def switch_ring_ledger():
    """Area of the stage power-switch rings in the ROM field, and whether the re-fit's spare pair slots hold it."""
    N = PAIR_W["placed_pairs"]
    mm2 = SWITCH_RING["cluster_area_frac"] * N * SWITCH_RING["pair_um2"] / 1e6
    slots_needed = N * (1 + SWITCH_RING["cluster_area_frac"])
    return dict(switch_ring_mm2=round(mm2, 2), pair_slots_needed=round(slots_needed),
                pair_slots=SWITCH_RING["slots"], fits_spare_slots=bool(slots_needed <= SWITCH_RING["slots"]),
                basis=SWITCH_RING["src"])


def pair_power(clock):
    """Per-pair ROM-field power at `clock`: leakage, the clock of an idle pair whose clock runs, and the full
    (clock + switching) power of a busy pair, each excluding leakage.  Clock and switching scale linearly with the
    clock from the 1.087 GHz measurement (ASSUMED: same 0.7 V supply)."""
    s = clock / PAIR_W["clock_hz"]
    leak = PAIR_W["idle_icg"]
    return dict(leak=leak, clock=(PAIR_W["idle_ungated"] - leak) * s, busy=(PAIR_W["busy"] - leak) * s)


def busy_pairs(nd):
    """Pairs a weight matvec keeps busy while it issues: the pairs of its holding macros (2 macros a pair)."""
    u = nd.get("_uarch")
    return min(PAIR_W["placed_pairs"], math.ceil(u["holding"] / 2)) if u else 0


def xnet_energy(u, field_mm, wire_j):
    """Energy of a weight matvec outside its pairs: x broadcast over the field, the VM read of x, the partial-sum
    return wires and the VM write of the result (the pairs' own MACs, ROM reads and x capture are in PAIR_W)."""
    xbits = u["K"] * (16 if u["fmt"] == "bf16" else 8)
    return (xbits * field_mm * wire_j + u["K"] * 4 * E_SRAM_B
            + u["rows"] * u["ksplit"] * 32 * (field_mm / FLOORPLAN["cols"] / 2 + 10.0) * wire_j + u["rows"] * 4 * E_SRAM_B)


def power_ledger(d, g, clock, tokens_s, area, wire_j=WIRE_J_PER_BIT_MM):
    """Busiest layer die.  ROM field from the measured pair (PAIR_W): every weight matvec keeps its holding pairs
    busy for its issue time; the other placed pairs idle, clocked (ungated) or stopped by the per-pair ICG.  Hub
    (dedicated units + VM ports) clock and leakage from its area (UNCALIBRATED).  Energy per token = dynamic above
    the clocked-idle floor (field busy excess, off-pair network, hub units, HBM interface, links)."""
    pp = pair_power(clock)
    N = PAIR_W["placed_pairs"]
    stack_e = {}
    per_layer, field_layer, bp_layer, occ_layer, peak_layer = {}, {}, {}, {}, {}
    field_mm = FLOORPLAN["cols"] * 25.628 + 20.0          # broadcast tree wire length (column runs + trunk)
    for name, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0:
            continue
        e = 0.0
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            bp = busy_pairs(nd) * nd["issue"]
            bp_layer[L] = bp_layer.get(L, 0.0) + bp
            field_layer[L] = field_layer.get(L, 0.0) + bp * (pp["busy"] - pp["clock"])
            peak_layer[L] = max(peak_layer.get(L, 0), busy_pairs(nd))
            e += xnet_energy(u, field_mm, wire_j)
        elif k == "matvec" and name.endswith("hc.fn"):
            e += nd["sweep"]["macs"] * E_MAC["fp32"]
        elif k in ("vector", "reduce") and nd.get("_work"):
            cls, n_el = nd["_work"]
            e += n_el * E_MAC["fp32"] * (SFU_OPS_PER_ELEM if cls == "sfu" else 1) + n_el * 4 * 2 * E_SRAM_B
        elif k == "kvscan" and nd.get("_work"):
            cls, macs = nd["_work"]
            e += macs * (E_MAC["fp4"] if cls == "idx" else E_MAC["bf16"])
            if name.endswith("idx.score"):
                hb = int(nd["desc"].split()[2]) * A.IDX_KEY_B
            elif name.endswith(".scores"):
                hb = 640 * A.WIN_ROW_B / 4
            else:
                hb = 0
            e += hb * E_HBM_IF_B
            stack_e[L] = stack_e.get(L, 0.0) + hb * (E_HBM_B - E_HBM_IF_B)
        elif k == "collective":
            e += nd.get("payload", 0) * 8 * E_LINK_BIT
        per_layer[L] = per_layer.get(L, 0.0) + e
        if k not in ("collective", "hop"):
            occ_layer[L] = occ_layer.get(L, 0.0) + nd["issue"]
    lps = 40 / 28
    stages, fstage, bstage, occ, peak = {}, {}, {}, {}, {}
    for L, e in per_layer.items():
        st = int(L / lps)
        stages[st] = stages.get(st, 0.0) + e + field_layer.get(L, 0.0)
        fstage[st] = fstage.get(st, 0.0) + field_layer.get(L, 0.0)
        bstage[st] = bstage.get(st, 0.0) + bp_layer.get(L, 0.0)
        occ[st] = occ.get(st, 0.0) + occ_layer.get(L, 0.0)
        peak[st] = max(peak.get(st, 0), peak_layer.get(L, 0))
    busiest = max(stages, key=stages.get)
    e_tok = stages[busiest]
    e_other = e_tok - fstage[busiest]
    bp_tok = bstage[busiest]                       # busy pair-seconds per token on this die
    stack_tok = sum(v for L, v in stack_e.items() if int(L / lps) == busiest)
    hub_mm2 = area["hub_logic_mm2"]
    sram_mm2 = area["vm_ports"]
    hub_clock_w = CLOCK_J_MM2 * clock * (hub_mm2 + 0.15 * sram_mm2)
    hub_leak_w = hub_mm2 * LEAK["logic"] + sram_mm2 * LEAK["sram_array"]
    field_clock_w = N * pp["clock"]
    field_leak_w = N * pp["leak"]
    idle_w = 4 * HBM_IDLE_W_STACK
    sat_rate = 1.0 / max(occ.values())
    maxp = peak[busiest]

    def mode(icg):
        static = field_leak_w + (0.0 if icg else field_clock_w) + hub_clock_w + hub_leak_w + idle_w
        e = e_tok + (bp_tok * pp["clock"] if icg else 0.0)      # with the ICG a busy pair's clock is dynamic
        p1, ps = static + e * tokens_s, static + e * sat_rate
        # peak: the widest op's pairs busy, the rest idle; the rest of the die at its saturated average
        idle_pair = pp["leak"] + (0.0 if icg else pp["clock"])
        peak_w = (maxp * (pp["busy"] + pp["leak"]) + (N - maxp) * idle_pair + hub_clock_w + hub_leak_w + idle_w
                  + e_other * sat_rate)
        fits = ps <= COOLING_LIMIT_W
        thr = sat_rate if fits else max(0.0, (COOLING_LIMIT_W - static) / e)
        return dict(static_w=round(static, 1), energy_per_token_uJ=round(e * 1e6, 2),
                    total_w_single_user=round(p1, 1), total_w_saturated=round(ps, 1),
                    peak_w_saturated=round(peak_w, 1), fits_cooling_saturated=bool(fits),
                    peak_fits_cooling=bool(peak_w <= COOLING_LIMIT_W),
                    cooling_throttled_tokens_s_per_stage=round(thr, 1))
    ung, icg = mode(False), mode(True)
    out = dict(busiest_stage=busiest, energy_per_token_uJ=round(e_tok * 1e6, 2),
               hbm_stack_energy_per_token_uJ=round(stack_tok * 1e6, 2),
               hbm_stack_w_saturated=round(stack_tok / max(occ.values()), 1),
               dynamic_w_single_user=round(e_tok * tokens_s, 1), dynamic_w_saturated=round(e_tok * sat_rate, 1),
               saturated_tokens_s_per_stage=round(sat_rate, 1),
               clock_w=round(field_clock_w + hub_clock_w, 1), leakage_w=round(field_leak_w + hub_leak_w, 1),
               hbm_idle_w=idle_w,
               total_w_single_user=ung["total_w_single_user"], total_w_saturated=ung["total_w_saturated"],
               cooling_limit_w=COOLING_LIMIT_W, fits_cooling_saturated=ung["fits_cooling_saturated"],
               field=dict(basis="MEASURED per pair (PAIR_W, W18)", placed_pairs=N,
                          pair_w=dict(leak=round(pp["leak"], 5), clock=round(pp["clock"], 5), busy=round(pp["busy"], 5)),
                          clock_w=round(field_clock_w, 1), leakage_w=round(field_leak_w, 2),
                          busy_pair_us_per_token=round(bp_tok * 1e6, 1),
                          busy_pairs_equiv_single_user=round(bp_tok * tokens_s, 1),
                          busy_pairs_equiv_saturated=round(bp_tok * sat_rate, 1),
                          peak_busy_pairs=maxp, dynamic_energy_per_token_uJ=round(fstage[busiest] * 1e6, 2)),
               hub=dict(basis="area x technology.json clock / leakage constants, UNCALIBRATED",
                        clock_w=round(hub_clock_w, 1), leakage_w=round(hub_leak_w, 1)),
               ungated=ung, per_pair_icg=icg, switch_rings=switch_ring_ledger(),
               wire_j_per_bit_mm=wire_j)
    return out

UNIT = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["unit_areas_um2"]
SRAM_256B_MACRO = dict(um2=174.744 * 70.47, bits=262144, width=256)   # ot_sram_1r1w_1024x256_m2_r2c2
FLOORPLAN = dict(die_mm2=815.0, rom_field_strip_mm2=132.34, hub_mm2=233.7, cols=71, rows=190,
                 spine_tracks=1153, over_rom_tracks_per_100um=1128, pair_pitch_um=418.608,
                 src="results/floorplan/v41_pack_expanded_woa.json (claude/w1-v41-floorplan 3756a5bc)")


def area_ledger(d: dict):
    """Logic and memory area (mm2) the design instantiates, by resource.  ROM macros are placed in the W1
    ROM field; lanes must fit its MAC strips (132.34 mm2); dedicated units must fit the hub (233.7 mm2)."""
    n = d["macros"]
    striped = d["mapping"] == "striped"
    nb = (d.get("bf16_stripe_macros") or n) if striped else 64
    out = dict(
        rom_macros=n * ROM_MACRO_UM2,
        blockdot_lanes=(n * 2 * UNIT["blockdot_um2"]) if striped else (d.get("weight_macs_die") or 264960) / 32 * UNIT["blockdot_um2"],
        bf16_lanes=(nb * 16 * UNIT["mac_bf16_um2"]) if striped else (d.get("bf16_macs_die") or 41664) * UNIT["mac_bf16_um2"],
        capture_regs=n * 274 * DFF_UM2,
        chunk_partials=(n * 8 * 32 * DFF_UM2) if striped else 0.0,   # 8 rows x FP32 chunk partial per element
        # K-split partials meet in the return tree: about one FP32 adder per macro pair (UNIT fp32_add_um2)
        return_adders=(n / 2 * UNIT["fp32_add_um2"]) if striped and d.get("row_split") == "ksplit" else 0.0,
        # W10: a BF16 element completes 16 chunk sums a cycle: a 15-adder tree plus 128 chain registers (FP32);
        # an FP4/FP8 element: one chain adder per block-dot lane plus 8 chain registers each
        bf16_chain=(nb * (15 * UNIT["fp32_add_um2"] + 128 * 32 * DFF_UM2)) if striped else 0.0,
        blockdot_chain=(n * 2 * (UNIT["fp32_add_um2"] + 8 * 32 * DFF_UM2)) if striped else 0.0,
        indexer=d["idx_macs"] / 32 * UNIT["blockdot_um2"],
        attention=d["att_macs"] * UNIT["mac_bf16_um2"],
        su_lanes=d["su_lanes"] * UNIT["su_light_lane_um2"],
        sfu_lanes=d["sfu_lanes"] * UNIT["su_lane_um2"],
        vm_ports=(math.ceil(d["vm_read_elems"] * 32 / 256) + math.ceil(d["vm_write_elems"] * 32 / 256))
        * SRAM_256B_MACRO["um2"],
    )
    out = {k: v / 1e6 for k, v in out.items()}
    strip = out["blockdot_lanes"] + out["bf16_lanes"] + out["capture_regs"] + out["chunk_partials"] \
        + out["return_adders"] + out["bf16_chain"] + out["blockdot_chain"]
    hub = out["indexer"] + out["attention"] + out["su_lanes"] + out["sfu_lanes"] + out["vm_ports"] \
        + d.get("su_vm_ports_mm2", 0.0)
    blk = d.get("vmh_block")
    if blk:
        # ROOT RULINGS 2026-10-01: the measured SU+VM block (VM-H, then C_rotate for the product) replaces the SU
        # lanes, SFU lanes and VM ports (its SRAM is the VM; the rest is lane logic and network)
        hub += blk["block_mm2"] - (out["su_lanes"] + out["sfu_lanes"] + out["vm_ports"]
                                   + d.get("su_vm_ports_mm2", 0.0))
        out["vm_ports"] = blk["sram_mm2"]
        out["vmh_block_mm2"] = blk["block_mm2"]
    out["rom_field_strip_used_mm2"] = strip
    out["rom_field_strip_avail_mm2"] = FLOORPLAN["rom_field_strip_mm2"]
    out["hub_logic_mm2"] = hub
    out["hub_avail_mm2"] = FLOORPLAN["hub_mm2"]
    out["fits"] = bool(strip <= FLOORPLAN["rom_field_strip_mm2"] and hub <= FLOORPLAN["hub_mm2"])
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}


def network_ledger(d: dict, clock: float):
    """Activation broadcast and result return networks of the ROM field.

    x broadcast: vm_read_elems per cycle leave the VM as FP8 (BF16 for wo_a: 16 bit) and reach every column
    pair of the field (71 columns; W1 pack).  Result return: vm_write_elems FP32 per cycle arrive at the VM.
    Wires at the VM edge must fit the spine corridor's tracks; each column's vertical run fits over the ROM
    on M6/M8.  Registers: one per register segment along every column run and along the trunk."""
    cols = FLOORPLAN["cols"]
    xb = d["vm_read_elems"] * 16
    rb = d["vm_write_elems"] * 32
    seg_um = ((1e12 / clock) - UNCERTAINTY_PS - WIRE_OVERHEAD_PS) / WIRE_PS_PER_UM
    col_len_um = 25628.0
    trunk_um = d["bcast_um"]["expert"]
    per_col_ret = max(32, rb // cols * 4)                # a column bursts at 4x its fair share of the return
    col_wires = xb + per_col_ret + 64
    col_tracks = FLOORPLAN["over_rom_tracks_per_100um"] * FLOORPLAN["pair_pitch_um"] / 100 * 0.5
    trunk_wires = xb + rb + 64
    spines = math.ceil(trunk_wires / (FLOORPLAN["spine_tracks"]))
    reg_bits = (xb + per_col_ret) * cols * math.ceil(col_len_um / seg_um) + (xb + rb) * math.ceil(trunk_um / seg_um)
    return dict(x_bits_per_cycle=xb, return_bits_per_cycle=rb, trunk_wires=trunk_wires,
                spine_corridors_needed=spines, column_wires=col_wires, column_tracks=round(col_tracks),
                column_utilisation=round(col_wires / col_tracks, 3), register_bits=reg_bits,
                register_mm2=round(reg_bits * DFF_UM2 / 1e6, 3), stages_trunk=wire_cycles(trunk_um, clock))


# ---------------------------------------------------------------------------------------------------------
# Dedicated units (W11): each unit is ONE element replicated to the count the design needs.  Same schema for
# every unit: element (RTL module + parameters), replica count (must be whole), ports per element and in total,
# storage, area per element (a hardened element when one exists, else a marked estimate), and the per-op cycles
# of the L20 (busiest scanning layer) ops at the design's context, which is what evaluate() prices.
# Shared by the V4.1 ROM and V4.1 HBM dies (the hub region of the W1 floorplan).
# ---------------------------------------------------------------------------------------------------------
def dsrom_reindex_kc6_model():
    """Default-off, zero-edge repair of the source-pinned kc5 baseline control.

    Footprint allowance is conservative NAND2-equivalent construction, not
    mapped timing/area. The slot is the retained kc5 context core, not a die
    reservation. Unknown buffers/route occupancy must satisfy explicit bounds.
    """
    # Charge all three local head muxes, even though the old body already
    # contains rotation/hold muxes: no speculative baseline subtraction.
    nand2 = 768 * 9 + 768 * 4 + 3 * 128 * 4 + 8 * 12
    gross = round(nand2 * 0.08748, 8)
    core, cells = 93630.5, 34438.8
    cell_cap = 0.40 * core
    return dict(
        schema="opentallas.dsrom-reindex.kc6-model.v1",
        selected=False, default_enabled=False, mandatory_baseline_repair=True,
        parent_source="2d3057fb8", parent_source_sha256=
        "88864591d588add3b2f23578e778557ece9f53f9bfe7abd698aa15b60938d89d",
        mechanism=["free-running derived cpart; reset-cleared adm_q/cmp retained",
                   "FIFO count alternatives with actual late pop selection",
                   "ready-last head rotation with eight local 16-bit slices"],
        dimensions=dict(NPC=32, WB=128, DF=8, AW=28, TAGW=16, GS=8),
        compute=dict(new_macs_per_cycle=0, new_arithmetic_rounding_points=0),
        ports=dict(list_read_bits=28, list_address_bits=10, list_read_enable_bits=1,
                   request_bits_per_pc=1+28+4+16, request_ready_bits_per_pc=1,
                   response_control_bits_per_pc=1+16+4, response_ready_bits_per_pc=1,
                   unchanged_payload_bytes_per_response_pc=32,
                   control_only_payload_ports=True,
                   drain_bits=2+7+14+10+10+28, drain_ready_bits=1,
                   new_boundary_bits_per_cycle=0, new_memory_bytes_per_cycle=0),
        replicas=dict(control_per_stack=1, stacks_per_rank=4, ranks=4,
                      local_head_slices=8, bits_per_slice=16,
                      new_clock_sinks=0, gross_mux_selectors=768+3*128),
        state=dict(new_ff_bits=0, retained_cpart_bits=1024,
                   reset_enable_loads_removed=1024, reset_switching_increases=True,
                   accepted_debt_reset_policy="unchanged source policy; no new drain proof"),
        area=dict(gross_nand2_equivalents=nand2, nand2_um2=0.08748,
                  nand2_basis="TT cell footprint ONLY, not timing",
                  library_sha256="fa92e6ab1481810602811b1eea54bc016a341f11fb5188d7512c026599adf038",
                  gross_logic_allowance_um2=gross, net_mapped_delta_um2=None,
                  removed_enable_credit_um2=0, mapped_buffers_um2=None),
        slot=dict(scope="kc5 register-to-register context core, not parent die",
                  baseline_core_um2=core, baseline_standard_cells_um2=cells,
                  max_standard_cell_fraction=0.40,
                  max_standard_cells_um2=cell_cap,
                  gross_plus_baseline_um2=round(cells+gross, 8),
                  remaining_buffer_and_mapping_budget_um2=round(cell_cap-cells-gross, 8),
                  fit_verified=False,
                  admission="mapped cells including repair/CTS <= cap; explicit unchanged-core route required"),
        routing=dict(new_count_alternative_nets_max=768, candidate_head_nets=128,
                     extra_track_capacity=None, channel_occupancy_measured=False,
                     acceptance="same slot; zero DRC/antenna/slew/cap/fanout violations"),
        timing=dict(period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    external_side_budget_ps=166.6, new_registered_edges=0,
                    new_cdc=0, predicted_token_latency_delta_cycles=0,
                    same_program_cycles_measured=False, ss_ff_closed=False),
        adoption=False,
        blockers=["actual mapped area/buffers must satisfy slot cap",
                  "unchanged-core routing capacity and SS60/FF25/boundary closure",
                  "original component exactness and measured cycle reconciliation"])


def dsrom_reindex_kc7_model():
    """Same-edge ready-last successor; sizing precedes additive RTL emission."""
    # Three QW=12 state vectors. Four +/- alternatives for seq/left,
    # inuse dispatch base + two drain alternatives; no ready-fed carry chain.
    arithmetic_bits = 7 * 12
    drain_mux_bits = 3 * 12 * 3 + 3
    rob_comparator_bits = 3 * 12
    payload_mux_bits = 32 * (28 + 4 + 16) * 3
    local_predicates = 32 * 6 + 10
    nand2 = (arithmetic_bits * 9 + drain_mux_bits * 4 +
             rob_comparator_bits * 12 + payload_mux_bits * 4 + local_predicates * 12)
    gross = round(nand2 * 0.08748, 8)
    cap, baseline = 37452.2, 34279.5
    return dict(
        schema="opentallas.dsrom-reindex.kc7-model.v1", selected=False,
        default_enabled=False, parent="kc6 OPT_KC6=1; actual route FAIL",
        parent_source_sha256="8db9e624bfb3155205b55a7c08b0a600f8c8dac0489b33d4643fa3663d573483",
        mechanism=["precomputed drain seq/left/inuse and rob_ok alternatives",
                   "independent scale/code payload then eligible/ready final hold mux",
                   "kc6 free-running derived cpart and reset-valid mask retained"],
        dimensions=dict(NPC=32, WB=128, DF=8, AW=28, TAGW=16, LENW=4, QW=12, GS=8),
        compute=dict(new_macs_per_cycle=0, new_rounding_points=0),
        state=dict(added_ff_bits=0, added_clock_sinks=0, accepted_debt_reset_semantics="unchanged"),
        timing=dict(new_edges=0, new_cdc=0, token_latency_delta_cycles=0,
                    period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    ready_external_side_budget_ps=166.6, boundary_checks="original max AND min groups",
                    ready_sampled=False, ss_ff_closed=False, actual_gate_required=True),
        ports=dict(new_bits_per_cycle=0, new_bytes_per_cycle=0,
                   request_per_pc_bits=49, request_ready_per_pc_bits=1,
                   response_control_per_pc_bits=21, response_ready_per_pc_bits=1,
                   response_payload_bytes_per_pc=32, drain_bits=71, drain_ready_bits=1,
                   list_data_bits=28, list_address_bits=10, list_enable_bits=1),
        replicas=dict(control_per_stack=1, stacks_per_rank=4, ranks=4,
                      request_slices_per_pc=6, payload_bits_per_slice=8,
                      drain_state_slices=9, drain_bits_per_slice=4, rob_predicate_slices=1),
        construction=dict(arithmetic_bits=arithmetic_bits, drain_mux_bits=drain_mux_bits,
                          rob_comparator_bits=rob_comparator_bits, payload_mux_bits=payload_mux_bits,
                          local_predicate_allowance=local_predicates,
                          gross_nand2_equivalents=nand2, gross_um2=gross,
                          footprint_basis="same kc6 NAND2 footprint 0.08748um2; no TT timing transfer",
                          removed_logic_credit_um2=0, mapped_buffers_and_net_delta_um2=None),
        slot=dict(core_um2=93630.5, max_cell_fraction=0.40, max_cells_um2=cap,
                  measured_kc6_cells_um2=baseline, gross_plus_baseline_um2=round(baseline+gross,8),
                  remaining_cts_buffer_mapping_budget_um2=round(cap-baseline-gross,8),
                  fit_verified=False, parent_die_reservation=False),
        routing=dict(new_arithmetic_candidate_nets=84, new_payload_candidate_nets=1536,
                     request_ready_final_mux_loads_per_pc=48, drain_ready_mux_loads=37,
                     required_added_tracks=None, available_tracks=None,
                     acceptance="same core/budgets; zero DRC antenna slew cap fanout; actual channel fit"),
        admission="one original semantic gate then one extracted contextual route; no adoption before complete closure")


def dsrom_reindex_kc8_model():
    """Claude's cycle-identical structural repair, priced before its sole route."""
    # 6 kept WB128 copies plus 8 grouped room flags. No removed-cell credit:
    # the old room_all flop may disappear, but mapping determines that debit.
    copies, room = 6 * 128, 8
    ff = copies + room
    nand2 = copies * 4 + room * 4 + (8 * 7 + 7) * 2 + 64
    gross = round(ff * 0.37908 + nand2 * 0.08748, 8)
    parent, cap = 35166.3, 37452.2
    return dict(
        schema="opentallas.dsrom-reindex.kc8-model.v1", selected=False,
        default_enabled=False, source_commit="0b598c6dbf8136463dc11b65373b5f84039fe4c0",
        parent="kc7 terminal FAIL; measured same-context cells, not a die net debit",
        dimensions=dsrom_reindex_kc7_model()["dimensions"],
        mechanism=["8 registered local AND8 room groups; AND8 dispatch join at same edge",
                   "3 kept write-enable copies per lane: metadata31/code32/scale32 loads"],
        compute=dict(new_macs_per_cycle=0, new_rounding_points=0),
        state=dict(gross_added_ff=ff, kept_copy_ff=copies, grouped_room_ff=room,
                   gross_added_clock_sinks=ff, removed_room_all_credit=0,
                   room_reset_set_loads=8, copied_enable_reset="rst_n in synchronous D predicate",
                   accepted_debt_reset_semantics="unchanged"),
        timing=dict(new_edges=0, new_cdc=0, per_user_latency_delta_cycles=0,
                    actual_existing_gate_cases=20, actual_worst_cycles=738,
                    conditional_833ps_us=0.614754, period_ps=833,
                    SS_uncertainty_ps=60, FF_uncertainty_ps=25,
                    ready_external_budget_ps=166.6, original_max_and_min_groups_required=True,
                    dispatch_added_combinational_AND_inputs=8, SS_FF_closed=False,
                    slew_margin_percent=20, acceptance_slew_limit_ps=320, hold_margin_ps=8),
        ports=dsrom_reindex_kc7_model()["ports"],
        replicas=dict(controls_per_stack=1, stacks_per_rank=4, ranks=4,
                      kept_enable_copies_per_lane=3, lanes=2, room_groups=8,
                      FIFOs_per_room_group=8, no_new_memory_ports=True),
        construction=dict(gross_ff_um2=round(ff*0.37908,8),
                          decode_D_reset_allowance_nand2=copies*4+room*4+64,
                          local_AND_and_join_nand2=(8*7+7)*2,
                          gross_nand2_equivalents=nand2, gross_extra_um2=gross,
                          footprint_basis="0.37908um2 FF and 0.08748um2 NAND2; footprint only, no TT delay transfer",
                          conservative_decode_allowance="4 NAND2 per copied bit, no shared-decode or removed-logic credit",
                          mapped_buffers_clock_tree_and_net_delta_um2=None),
        slot=dict(core_um2=93630.5, max_cell_fraction=0.40, max_cells_um2=cap,
                  measured_kc7_cells_um2=parent, construction_total_um2=round(parent+gross,8),
                  remaining_mapping_CTS_repair_budget_um2=round(cap-parent-gross,8),
                  fit_verified=False, parent_die_reservation=False),
        routing=dict(new_internal_copy_Q_nets=copies, new_room_Q_nets=room,
                     copy_Q_select_loads=[31,32,32], same_D_copy_loads=3,
                     clock_reset_wire_sites_and_loaded_delay_unknown=True,
                     additional_tracks=None, available_tracks=None,
                     acceptance="same fixed core; mapped occupancy within cap and zero DRC/antenna/slew/cap/fanout"),
        admission="consume completed20case gate; one OPT_KC8=1 route with slew margin20; new failing cone escalates to Claude, no blind rescue")


def dsrom_reindex_kc7_parallel_model():
    """Owner-directed named fanout; contexts are measured, never die admission."""
    lib = "SEQ_RVT_TT_nldm_220123.lib footprint only, no TT timing transfer"
    extra_ff, extra_reset_mux, extra_and = 128, 128, 256
    split_gross = round(extra_ff * 0.37908 + extra_reset_mux * 4 * 0.08748 + extra_and * 2 * 0.08748, 8)
    # Construction utilization uses the identical synthesized body: baseline
    # context was nominal u35. Actual cell/core occupancy is a route output.
    variants = []
    for u in (40, 45):
        core = round(93630.5 * 35 / u, 6)
        gross_cells = 34279.5 + dsrom_reindex_kc7_model()["construction"]["gross_um2"]
        variants.append(dict(name="kc7_u"+str(u), source="cc5ef9f82", rtl_changed=False,
            nominal_core_utilization_percent=u, expected_core_um2=core,
            floorplan="ORFS CORE_UTILIZATION; remove explicit kc7 core/die override",
            expected_core_basis="same source; prior nominal35 context scaling, actual mapped area may differ",
            construction_max_cell_fraction=0.50,
            gross_cells_um2=round(gross_cells,8),
            expected_remaining_buffer_budget_um2=round(0.50*core-gross_cells,8),
            actual_core_and_fit_unknown=True, parent_die_reservation=False,
            new_ff=0, new_edges=0, new_ports=0))
    return dict(schema="opentallas.dsrom-reindex.kc7-parallel.v1", selected=False,
        directive="CODEX_DIRECTIVE_20261005_parallel_fanout.md Russell item3",
        unchanged_live_variant="kc7 cc5ef9f82 EPYC2; do not mutate/restart",
        utilization_variants=variants,
        split=dict(name="kc7_split2", default_enabled=False,
            mechanism="two kept parallel registered partial comparisons, combinational AND join",
            equations="lo'=adm_q & (&cpart[3:0]); hi'=adm_q & (&cpart[7:4]); cmp=lo&hi",
            exactness="both reset0; conjunction equals prior registered adm_q & (&cpart[7:0]) at same edge",
            new_ff_bits=extra_ff, new_clock_sinks=extra_ff, new_reset_clear_loads=extra_ff,
            new_adm_q_predicate_loads=128, new_combinational_cmp_join_bits=128,
            new_registered_edges=0, new_cdc=0, per_user_latency_delta_cycles=0,
            reference_cycles=738, actual_cycles_required=True,
            existing_ports_and_memory_bytes_unchanged=True, gross_extra_um2=split_gross,
            footprint_basis=lib, ff_allowance_um2=0.37908,
            reset_mux_nand2_equivalents=extra_reset_mux*4, extra_and_nand2_equivalents=extra_and*2,
            baseline_core_um2=93630.5, baseline_cap_um2=37452.2,
            kc7_gross_cells_plus_split_um2=round(34279.5+dsrom_reindex_kc7_model()["construction"]["gross_um2"]+split_gross,8),
            remaining_buffer_budget_um2=round(37452.2-34279.5-dsrom_reindex_kc7_model()["construction"]["gross_um2"]-split_gross,8),
            clock_reset_wire_site_tracks_and_loaded_delay_unknown=True,
            fit_verified=False, physical_closed=False),
        common=dict(period_ps=833, SS_uncertainty_ps=60, FF_uncertainty_ps=25,
            ready_external_budget_ps=166.6, original_min_and_max_groups_required=True,
            port_boundaries=dsrom_reindex_kc7_model()["ports"],
            no_new_bandwidth_or_replica_credit=True, context_only=True,
            cells_include_actual_cts_and_repair=True,
            drc_antenna_slew_cap_fanout_must_be_zero=True),
        admission="u40/u45 measured occupancy <= explicitly priced50% construction cap; split <= old40% cap; no headline adoption")


HBM_PC_SECTORS_PER_CYCLE = (1e12 / 1.0339e9) / 1024.0
                                                # one 32-B burst per 1,024 ps per pseudo-channel (HBM3E 1 TB/s over
                                                # 32 PCs; rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv) at 967.2 ps/cycle
HBM_PCS_DIE = 4 * 32                            # four stacks x 32 pseudo-channels
SECTOR_B = 32
DEDICATED = dict(
    indexer=dict(
        element="ot_hdc_v41x_idx_score_slice #(NK=4, NB=4, IH=32): 4 keys x 32 heads x 128 FP4 dims per cycle "
                "(16 x ot_hdc_v41x_idx_chunk + 4 x ot_hdc_v41x_idx_tail); rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
        sub_element="ot_hdc_v41x_idx_chunk #(NB=4, NKT=1): 8 heads x 1 key, 32 exact FP4 32-block dots = 1,024 MACs",
        macs_per_element=4 * 32 * 128, keys_per_element=4,
        key_bits_in=4 * 544,                    # 4 keys x (512 FP4 code bits + 4 UE8M0 scales + pad) per cycle
        query_bits=17920,                       # 32 heads x (128 FP4 + 4 scales + BF16 weight), one copy per slice
        meta_fifo_bits=64 * 35,                 # score-metadata FIFO (index, mask, last), IW=30
        out_bits=4 * (16 + 30),                 # BF16 score + global index per key
        latency=48,                             # first score after the key beat (results/rtl/v41_idx_score_slice.json)
        area_est_um2=16 * 32 * UNIT["blockdot_um2"] + 4 * 17310.0,
        area_basis="ESTIMATE until hardened: 512 FP4 block dots at the closed FP8/FP4 weight lane's area "
                   "(ot_hdc_blockdot, 2,511 um2 per 32-product lane) + the per-key head-sum (idx_hsum 17,310 um2 "
                   "closed, per key of 4)",
        hardened_record="results/physical_abi3/asap7/hdc/v41x/w11/idx_chunk/physical.json",
        hardened_scale=16,                      # 16 chunks per NK=4 slice (+ 4 tails, 1% of a chunk)
    ),
    idx_reader=dict(
        reindex_control_closure_successor=dsrom_reindex_kc6_model(),
        reindex_ready_boundary_successor=dsrom_reindex_kc7_model(),
        reindex_parallel_closure=dsrom_reindex_kc7_parallel_model(),
        reindex_grouped_room_write_enable_successor=dsrom_reindex_kc8_model(),
        element="per-pseudo-channel key reader: request generator + reorder slice of ot_hdc_v41x_idx_kctl / "
                "_kstream_range (one per HBM3E pseudo-channel), 64-key collector ot_hdc_v41x_idx_shard_quarter_collect",
        replicas_fixed=HBM_PCS_DIE,
        bytes_per_key=A.IDX_KEY_B, sector_B=SECTOR_B,
        peak_sectors_per_cycle=HBM_PCS_DIE * HBM_PC_SECTORS_PER_CYCLE,
        collector_out_bits=64 * 544,
        measured_record="results/rtl/hdc_v41x_idx_four_stack_verilator_collector_pipeline.json",
        measured_sectors_per_cycle=60.04,       # 557,056 sectors in 9,278 cycles (262,144 keys)
    ),
    attention=dict(
        element="ot_hdc_v41x_attn_tile #(H=16, TD=32): 16 heads x 32 BF16 products per cycle, stationary banks; "
                "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv",
        products_per_element=16 * 32, H=16, D=512, TD=32,
        q_bits=512 * 16, kv_row_bits=16 * 265, p_word_bits=32 * 16, pv_out_bits_per_tile=16 * 32,
        area_est_um2=16 * 32 * UNIT["mac_bf16_um2"],
        area_basis="ESTIMATE until hardened: 512 pipelined BF16 MACs (ot_mac_bf16_fp32_pipe 509 um2)",
        hardened_record="results/physical_abi3/asap7/hdc/v41x/w11/attn_tile/physical.json",
        hardened_scale=1,
        measured_record="results/rtl/v41_full_attention_numeric/result.json",
        measured_job_cycles_pwords1=609, measured_pv_window_pwords1=(248, 559),
        # the two-word probability loader (claude/w11-attn c80877d8, results/rtl/w11_attn_ploader.json): exact on all
        # four full-geometry cases; with 2 probability words/cycle upstream (1/cycle gives back the PWORDS=1 cycles)
        measured_job_cycles_pwords2={640: 449, 128: 193}, measured_pv_window_pwords2=(240, 399),
        measured_verify6_cycles={1: 3389, 2: 2429},
    ),
    stream_unit=dict(
        element="ot_hdc_v41x_vec_lane (KIND 0 light / 1 SFU / 2 full lane 0) under ONE controller and ONE "
                "chunk8 reducer (ot_hdc_v41x_vec, ot_hdc_v41x_vec_red); rtl/hdc/v41x/ot_hdc_v41x_vec*.sv",
        read_streams=4, AW=24,
        area_est_light_um2=UNIT["su_light_lane_um2"], area_est_sfu_um2=UNIT["su_lane_um2"],
        area_basis="ESTIMATE until hardened: light lane 1.5 x (2 fp32 mul + 3 fp32 add); SFU lane = the "
                   "synthesis-only ot_hdc_v41_su_lane",
        hardened_record_light="results/physical_abi3/asap7/hdc/v41x/w11/vec_light1024r/physical.json",
        hardened_record_sfu="results/physical_abi3/asap7/hdc/v41x/w11/vec_sfu1024r/physical.json",
        measured_record="results/rtl/v41x_su_softmax.json", measured_softmax_t640_n16_m8=3280,
    ),
)


SU_OP_ACCEPT = 6          # measured: SU accept -> first emit per op (results/rtl/w11_su_spec.json, claude/w11-su)
# SU placement (W11 SU worker derivation): lane array 11.96 mm2 as a square of side 3,458 um; controller at its
# centre -> farthest lane (corner) 3,458 um Manhattan; results return to HUB_VM on the SU region's west edge,
# farthest lane -> VM edge 3,458 + 392 um
SU_FARTHEST_LANE_UM = 3458.0
SU_RETURN_UM = 3850.0
SU_BCAST_STAGES_W1 = wire_cycles(SU_FARTHEST_LANE_UM, 1e12 / 920, WIRE_PS_PER_UM_LOADED)   # = 4
SU_RET_STAGES_W1 = wire_cycles(SU_RETURN_UM, 1e12 / 920, WIRE_PS_PER_UM_LOADED)            # = 5


def _hardened_um2(rel):
    p = ROOT / rel
    if not p.exists():
        return None, None
    dsg = json.loads(p.read_text()).get("design", {})
    return dsg.get("area_um2"), dict(fmax_mhz=round((dsg.get("fmax_hz") or 0) / 1e6, 1), closed=dsg.get("closed"))


def _su_softmax_ops(N, M, heads=16, T=640, hd=512):
    """The attention softmax chain as SU ops (tools/rtl_v41x_su_softmax_campaign.fixture), laid out by the RTL's
    own layout rule (tools/rtl_hdc_v41x_vec_campaign.layout): vectors per op and emit->result depth."""
    import rtl_hdc_v41x_vec_campaign as C
    import hdc_isa_v41 as I
    base = C.op_defaults()
    common = dict(nout=heads, nin=T, abase=0, aso=T, asi=1, dst=I.DST_VM, obase=0, oso=T, osi=1)
    ops = dict(
        max=dict(base, **common, m1=I.M1_AIMM, red=I.RED_MAX, rbase=16384, rso=1),
        exp_sum=dict(base, **common, bbase=16384, bso=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, rbase=16400,
                     rso=1),
        sink=dict(base, nout=1, nin=heads, asrc=I.SRC_CLO, asi=1, bbase=16384, bsi=1, ad=I.AD_NEGB, sfu=I.SFU_EXP,
                  cbase=16400, csi=1, e1=I.E1_ADDC, dst=I.DST_VM, obase=16416, osi=1),
        divide=dict(base, nout=heads, nin=hd, abase=17408, aso=hd, asi=1, bbase=16416, bso=1, m1=I.M1_DIVB, rnd=1,
                    dst=I.DST_VM, obase=17408, oso=hd, osi=1))
    out = {}
    for k, f in ops.items():
        lay = C.layout(f, N, M)
        out[k] = dict(vectors_per_row_set=lay["nv"], vectors=lay["nv"], depth=lay["dR"] if f["red"] else lay["dP"], vw=lay["vw"],
                      span=bool(lay["span"]), bad=bool(lay["bad"]))
    return out


def dedicated_ledger(d: dict, ctx: int = 1048576, layer: int = 20, positions: int = 1):
    """Element, replicas, ports, area and per-op cycles of the four dedicated units of design `d`.
    positions > 1: an MTP verify pass time-multiplexed on the same lanes (m = 1): the index keys, KV rows and
    probabilities of the block are read once, every position's MACs and stream elements are issued in turn."""
    E = A._env()
    c, clock = E["c"], E["clock"]
    ops, meta = A.ops_of_layer(c, layer, ctx)
    keys = int(meta["n_scan"] / 4) if meta["n_scan"] else 0          # keys per die (tensor group 4)
    T = meta["T"]
    out, flags = {}, []
    # -- indexer
    u = DEDICATED["indexer"]
    rep = d["idx_macs"] / u["macs_per_element"]
    if abs(rep - round(rep)) > 1e-9:
        flags.append(f"indexer: idx_macs {d['idx_macs']} is {rep:.3f} NK=4 slices (not whole)")
    rep_i = math.ceil(rep)
    kpc = rep_i * u["keys_per_element"]
    a_h, q_h = _hardened_um2(u["hardened_record"])
    a_el = a_h * u["hardened_scale"] if a_h else u["area_est_um2"]
    reader_Bpc = d["idx_reader_Bpc"] or min(A.ROM_DIE_HBM_BPS / clock, 1e18)
    t_mac = positions * math.ceil(keys / kpc) if keys else 0
    t_rd = keys * A.IDX_KEY_B / reader_Bpc if keys else 0.0
    out["indexer"] = dict(
        element=u["element"], sub_element=u["sub_element"], replicas=rep_i, keys_per_cycle=kpc,
        macs_per_cycle=rep_i * u["macs_per_element"],
        ports_per_element=dict(key_in_bits=u["key_bits_in"], score_out_bits=u["out_bits"], query_bits=u["query_bits"]),
        ports_total=dict(key_in_bits=rep_i * u["key_bits_in"], score_out_bits=rep_i * u["out_bits"]),
        storage_bits=rep_i * (u["query_bits"] + u["meta_fifo_bits"]),
        area_element_um2=round(a_el), area_basis="hardened x16 chunks" if a_h else u["area_basis"],
        hardened=q_h, area_mm2=round(rep_i * a_el / 1e6, 3),
        ops={f"L{layer}.attn.idx.score": dict(keys=keys, positions=positions, t_mac=t_mac, t_reader=round(t_rd, 1),
                                               issue=round(max(t_mac, t_rd), 1), latency=u["latency"],
                                               bind="reader" if t_rd > t_mac else "mac")})
    # -- index reader
    u = DEDICATED["idx_reader"]
    need_spc = reader_Bpc / u["sector_B"]
    out["idx_reader"] = dict(
        element=u["element"], replicas=u["replicas_fixed"], target_bytes_per_cycle=round(reader_Bpc, 1),
        target_sectors_per_cycle=round(need_spc, 2), hbm_peak_sectors_per_cycle=round(u["peak_sectors_per_cycle"], 2),
        per_pc_target_sectors_per_cycle=round(need_spc / u["replicas_fixed"], 4),
        measured_sectors_per_cycle=u["measured_sectors_per_cycle"], measured_record=u["measured_record"],
        collector_out_bits=u["collector_out_bits"],
        ops={f"L{layer}.attn.idx.score(read)": dict(sectors=keys * A.IDX_KEY_B // u["sector_B"],
                                                     cycles_at_target=round(keys * A.IDX_KEY_B / reader_Bpc, 1),
                                                     cycles_measured=round(keys * A.IDX_KEY_B / u["sector_B"]
                                                                           / u["measured_sectors_per_cycle"], 1))})
    # -- attention
    u = DEDICATED["attention"]
    per_row = u["H"] * u["D"]
    NL = d["att_macs"] / per_row
    if abs(NL - round(NL)) > 1e-9:
        flags.append(f"attention: att_macs {d['att_macs']} is NL={NL:.3f} rows/cycle (not whole)")
    NL = max(1, round(NL))
    tiles = NL * u["D"] // u["TD"]
    pwords = d.get("att_pwords", 1)           # 2 = the two-word probability loader (W11)
    PB, DPT = u["H"], u["D"] // tiles                 # p words per TD-row block; p.v beats per block
    beats = math.ceil(T / NL)
    load_per_blk = math.ceil(PB / pwords)
    pv_cycles = math.ceil(T / u["TD"]) * max(DPT, load_per_blk)
    a_h, q_h = _hardened_um2(u["hardened_record"])
    a_el = a_h if a_h else u["area_est_um2"]
    lvt = int(math.log2(u["TD"] // 8))
    out["attention"] = dict(
        element=u["element"], replicas=tiles, rows_per_cycle=NL, products_per_cycle=tiles * u["products_per_element"],
        ports_total=dict(q_bits=u["q_bits"], kv_in_bits=NL * u["kv_row_bits"], p_in_bits=pwords * u["p_word_bits"],
                         pv_out_bits=tiles * u["pv_out_bits_per_tile"]),
        stationary_banks=4 if pwords == 2 else 3,
        area_element_um2=round(a_el), area_basis="hardened" if a_h else u["area_basis"], hardened=q_h,
        area_mm2=round(tiles * a_el / 1e6, 3),
        ops={f"L{layer}.attn.scores": dict(beats=beats, positions=positions, issue=positions * beats,
                                           tile_latency=27 + 3 * lvt),
             f"L{layer}.attn.pv": dict(beats=beats, p_words=math.ceil(T * u["H"] * 16 / u["p_word_bits"]),
                                       pwords_per_cycle=pwords, positions=positions, issue=positions * pv_cycles,
                                       note="p.v issue = blocks x max(beats/block, p-load cycles/block)")},
        measured_job_cycles=(u["measured_job_cycles_pwords2"].get(T) if pwords == 2
                             else (u["measured_job_cycles_pwords1"] if T == 640 else None)),
        measured=dict(record=u["measured_record"], record_pwords2="results/rtl/w11_attn_ploader.json",
                      job_cycles_pwords2=u["measured_job_cycles_pwords2"], verify6=u["measured_verify6_cycles"],
                      job_cycles_pwords1=u["measured_job_cycles_pwords1"],
                      pv_window_pwords1=u["measured_pv_window_pwords1"]))
    # -- stream unit
    u = DEDICATED["stream_unit"]
    N, M = d["su_lanes"], d["sfu_lanes"]
    sm = _su_softmax_ops(N, M, T=T)
    bst, rst = d.get("su_bcast_stages", 0), d.get("su_ret_stages", d.get("su_bcast_stages", 0))
    for v in sm.values():
        v["vectors"] *= positions
    aL, qL = _hardened_um2(u["hardened_record_light"])
    aS, qS = _hardened_um2(u["hardened_record_sfu"])
    light = aL or u["area_est_light_um2"]
    sfu = aS or u["area_est_sfu_um2"]
    ports = dict(read_bits=u["read_streams"] * N * 32, gather_bits=N * 32, write_bits=N * 32, kv_write_bits=N * 32,
                 result_bits=N // 8 * 32)
    banks = {k: math.ceil(v / 256) for k, v in ports.items()}
    out["stream_unit"] = dict(
        element=u["element"], replicas=dict(light=N - M, sfu=M - 1, full=1), lanes=N, sfu_lanes=M,
        ports_total=ports, vm_banks_256b=banks,
        area_element_um2=dict(light=round(light), sfu=round(sfu)),
        area_basis=("hardened" if aL and aS else u["area_basis"]), hardened=dict(light=qL, sfu=qS),
        area_mm2=(d["vmh_block"]["block_mm2"] if d.get("vmh_block") else round(((N - M) * light + M * sfu) / 1e6, 3)),
        area_lanes_ledger_mm2=round(((N - M) * light + M * sfu) / 1e6, 3),
        vmh_block=(dict(d["vmh_block"], note="ROOT RULINGS 2026-10-01: area_mm2 is the measured SU+VM block of the "
                                             "product's VM option (lanes, VM SRAM, network); area_lanes_ledger_mm2 is "
                                             "the lane-only ledger estimate")
                   if d.get("vmh_block") else None),
        ops={f"L{layer}.attn.softmax.{k}": v for k, v in sm.items()},
        softmax_issue_vectors=sum(v["vectors"] for v in sm.values()),
        # a dependent op pays its issue, its pipeline depth, the broadcast tree to the farthest lane and the
        # result return to the VM (su_bcast_stages / su_ret_stages, from the W1 hub placement; root 2026-09-29)
        su_bcast_stages=bst, su_ret_stages=rst,
        softmax_chain_cycles=sum(v["vectors"] + v["depth"] + bst + rst + SU_OP_ACCEPT for v in sm.values()),
        measured=dict(record=u["measured_record"], t640_n16_m8=u["measured_softmax_t640_n16_m8"]))
    hub = sum(out[k]["area_mm2"] for k in ("indexer", "attention", "stream_unit"))
    return dict(design=d["name"], ctx=ctx, layer=layer, T=T, positions=positions, keys_per_die=keys, units=out,
                hub_logic_mm2=round(hub, 3), hub_avail_mm2=FLOORPLAN["hub_mm2"], discrepancies=flags)


# ---------------------------------------------------------------------------------------------------------
# Qwen3-8B ROM die (O4: two reticles, TP-2, INT8 weights, G weight-lane groups of 16 lanes per die)
# ---------------------------------------------------------------------------------------------------------
# The element is already weight-stationary: a group owns its ROM column and 16 lanes; W5 hardens a tile of
# 4 groups (22 code macros ot_rom_4096x266_m8, 4 KV-slice SRAMs).  The architecture replay
# (tools/arch_budget_qwen3.as_built -> tools/hdc_timing.simulate, calibrated 32,191 vs 32,196 RTL cycles) has
# single-cycle wires.  The microarchitecture adds, from W5's floorplan (docs/QWEN_O4_FLOORPLAN.md,
# results/floorplan/qwen_o4/floorplan.json on claude/w5-qwen-physical e93d75ef):
QWEN_WIRE = dict(
    x_stages_extra=24,        # VM -> farthest group 27.0 mm: 25 register stages vs the RTL's 1
    vm_conflict_reg=1,        # registered conflict/bank decode in the 8-bank VM (W5 VM cut: -699 ps without)
    result_write_extra=2,     # result write path (434 cycles / 217 ME ops)
    tree_extra_per_token=1728,  # split-tree compaction beyond the RTL's levels (o/down 1440 + qkv 252 + gu 36)
    ucie_wire_per_token=1898,   # farthest tile -> west UCIe and back, 13 stages each way, 146 crossings
)
# W12 floorplan (tools/qwen_rom_floorplan_w12.py, G=6144, one hardened tile replicated, VM and engine top at the
# spine centre, 0.76 ps/um): per matrix-engine op the instruction/x broadcast, the tree levels above the tile and
# the tree words' return to the spine are register stages of the RTL array (ot_qwen_me_array: BD, NWS, TWS, ORD).
# They replace W5's x + conflict + write per-op terms and its per-token tree term; the UCIe crossing stays.
QWEN_WIRE_W12 = dict(
    bd=31,                    # instruction broadcast + x network, incl. the tile input register and XVM
    xvm=1,                    # registered VM conflict stage (inside bd)
    nws=4, tree_levels=4,     # four upper tree levels (3..6) inside a 16-tile block, 4 stages each
    tws=64,                   # level-6 words -> spine top: worst block word at the b3r12/b3r13 die floorplan, 430.56 um
                              # link-stage pitch (results/rtl/qwen_rom_fulldie_20261003/b3r3/latency_b3r12.json; was 30)
    ord=4,                    # result write -> VM
    me_lat_extra=31 + 4 * 4 + 64 + 4,   # 115 cycles on every ME op's result
    hub_stack_stages=53,      # hub <-> stack link at the same floorplan (r2 entry priced 46): +2 x 36 x 7 cycles a token
    two_beat_bound=1,         # F2 two-beat instruction: +1 cycle a ME op until RTL prefetch is measured (bound)
)
# Vector-memory x read (W12 gap): the engine's x chunk port reads S distinct elements at every K step (IL cycles,
# x held across the slots) or every cycle (x varies with the slot, xjs != 0: the attention ops).  The W5 VM
# (8 skew banks x 4 slices x 3 rows of ot_sram_1r1w_512x128) delivers 32 x 128 bits = 128 FP32 a cycle.
VM_MACRO = dict(name="ot_sram_1r1w_512x128_m4_r2c2", um2=174.096 * 29.70, elems_per_read=4, words=512)
VM_ELEMS_QWEN = 177808


def vm_banking(read_elems):
    """macros (and area) for a VM that reads `read_elems` FP32 a cycle and holds VM_ELEMS_QWEN"""
    ports = math.ceil(read_elems / VM_MACRO["elems_per_read"])
    depth = math.ceil(VM_ELEMS_QWEN / (ports * VM_MACRO["elems_per_read"]))
    rows = math.ceil(depth / VM_MACRO["words"])
    macros = ports * rows
    return dict(read_elems=read_elems, macros=macros, area_mm2=round(macros * VM_MACRO["um2"] / 1e6, 3),
                capacity_elems=macros * VM_MACRO["words"] * VM_MACRO["elems_per_read"])


def qwen_hbm_registered_admission_model(tp=2, engine_advances=None, replicas=None):
    """Held current-command, two registered decision cuts; default-off candidate.

    No next-address signal exists in the selected spine ABI. A grant therefore
    expires on the engine edge, and a new request must be sampled before regrant.
    These extra clocks are mandatory, not hidden as unchanged throughput.
    """
    if tp not in (2, 4):
        raise ValueError("tp must be 2 or 4")
    for value in (engine_advances, replicas):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError("counts must be nonnegative integers or None")
    nseg, width, groups = 8, 24, 96 if tp == 2 else 48
    ff = 2*nseg + 4  # match/availability, no-read, phase[1:0], grant
    return dict(schema="opentallas.qwen.hbm.registered_admission.v1",
                parameter="ADMISSION_PIPE", default=0, tp=tp,
                macs_per_active_engine_edge="unchanged selected W12 geometry",
                engine_advance_ii=3, added_cycles_per_engine_advance=2,
                # This is an engine service charge, not a measured token delta.
                # Current-source layer counts and causal overlap are not enrolled.
                added_token_cycles=None, added_token_ns=None,
                gross_added_engine_service_cycles=None if engine_advances is None else 2*engine_advances,
                gross_added_engine_service_ns=None if engine_advances is None else 2*engine_advances*0.833,
                engine_service_duration_ratio=3,
                service_charge_condition="same logical engine-edge sequence; external service/calendar unchanged",
                current_source_layer_advance_counts=None,
                current_source_layer_slowdown_upper_bound=None,
                current_source_full_token_slowdown_upper_bound=None,
                candidate_verdict="REJECTED_AS_SPEED_OPTIMIZATION",
                physical_run_role="single priced mandatory-clock feasibility measurement only",
                engine_advance_count=engine_advances, replicas=replicas,
                added_ff_bits_per_die=ff, ff_area_floor_um2=ff*DFF_UM2,
                combinational_cost="existing segment comparators; registered-match priority/reduce + phase decode",
                mapped_cell_area_um2=None, slot_fit=None, physical_closed=False,
                added_memory_ports=0, added_memory_bytes_per_cycle=0,
                added_external_boundary_bits=0, retained_request_address_bits=width,
                result_enable_fanout=groups, result_packet_pipeline_bits=0,
                clock_reset_load_added_pins=ff,
                local_registered_decision_tracks=2*nseg+4,
                routing_track_capacity=None,
                accepted_contract="one matching held request per one-edge grant; retire only on me_clk_en",
                command_issue="me_go requires that same registered engine grant",
                held_output_contract="address/data/mask held in existing spine; no delayed strobe-only packet",
                prerequisite="segment table stable across held phase, monotonic same-token arrivals; reset cancels grant",
                token_rate=None, token_speedup=None, adoption=False,
                context_control_measurement=dict(commands=16, engine_advances=7650,
                    baseline_cycles=8055, candidate_cycles=23342, added_cycles=15287,
                    geometry="G6144/SW64/LV7; TP2 and TP4 actual route cuts",
                    arithmetic_qualified=False),
                baseline_clock_sensitivity=dict(
                    policy="same extracted delays only; NOT a routed operating point",
                    io_delay_fraction=0.2, setup_uncertainty_ps=60,
                    required_period_ps=((1341.06 if tp == 2 else 1338.91)+60)/0.8,
                    measured_ss_worst_ps=-734.66 if tp == 2 else -732.51,
                    candidate_clock_qualified=False))


def qwen_hbm_collective_return_cut_model(tp=2):
    """One held same-clock receive packet cut at the actual TP sequencer input.

    No ready is invented: the current collective return is unstallable. All
    payload/control fields travel together, reset cancels the packet valid.
    """
    if tp not in (2, 4):
        raise ValueError("tp must be 2 or 4")
    rank_bits = 1 if tp == 2 else 2
    bits = 512 + rank_bits + 3  # data, rank, valid, last, err
    return dict(parameter="R_NEXT", default=0, ranks=tp,
        captured_packet_bits_per_rank=bits, replicated_capture_bits=bits*tp,
        added_latency_edges_per_collective=1, added_edges_per_record=0,
        accepted_return_ii=1, native_return_ready_present=False,
        arithmetic="unchanged native rank-order FP32 add and original argmax tie rules",
        macs_added=0, new_memory_ports=0, memory_bytes_per_cycle_added=0,
        return_bytes_per_cycle=64, packet_boundary_bits=bits,
        capture_ff_area_floor_um2=(bits-1)*DFF_UM2+0.37908,
        payload_hold_mux_count=bits-1, clock_pins_per_rank=bits,
        added_clock_domains=0, added_cdc=0, mapped_area_um2=None,
        routing_tracks_needed=bits, routing_capacity=None,
        placement_utilizations=[0.25,0.30,0.35], slot_fit=None,
        compose_rule="one exposed edge per completed collective; actual command count required, no free overlap",
        actual_layer_collective_counts=None, actual_token_delta_ns=None,
        SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25, clock_ps=833,
        physical_closed=False, adoption=False, token_rate=None)


def qwen_x_read_stall(G, su_width, ctx, read_elems):
    """Cycles a token adds when the engine's x reads are limited to `read_elems` a cycle (bandwidth bound,
    fully exposed: the engine never stalls in the RTL, so any shortfall delays its issue)."""
    import arch_budget_qwen3 as Q
    import hdc_isa as I
    import hdc_program as P
    import hdc_timing as T
    sw0 = I.SU_WIDTH
    I.SU_WIDTH = su_width
    try:
        prog = P.build_program(Q.capped_layout(G, None, Q.die_shape()))
    finally:
        I.SU_WIDTH = sw0
    d = T.dyn_values(ctx - 1, groups=G, H=Q.Q["H"], half=Q.Q["HD"] // 2, HD=Q.Q["HD"])
    il = I.INTERLEAVE
    stall = 0
    per_op = []
    for f in prog:
        if f.get("unit") != I.UNIT_ME:
            continue
        f = {n: f.get(n, 0) for n, _ in I.FIELDS}
        rounds, kk = T.me_loop(f, d, ctx - 1, G)
        S = 1 << f["me_split"]
        need = math.ceil(S / read_elems)
        issue = rounds * kk * il
        xc = rounds * kk * il * need if f["me_xjs"] else rounds * kk * max(il, need)
        extra = max(0, xc - issue)
        stall += extra
        if extra:
            per_op.append((f["me_wsrc"], S, rounds, kk, extra))
    return stall, per_op


QWEN_AREA = dict(
    array_mm2=560.0,          # tile array area after PHYs, UCIe, spine, corridors (W5: 1,225 x 0.4512 mm2 as
                              # instantiated, 1,470 x 0.3857 pruned)
    code_macros=33792,        # 11 banks of 4096x266 per group-pair column at G=6144 (W5 rung 2)
    macro_um2=121.824 * 62.91,
    macro_pack=1.31,          # tile macro footprint / macro area: W5 tile 976.3 x 462.2 um = 22 code + 4 KV
                              # macros x pack + 4 x 26,250 / 0.5 of logic
    logic_group_um2=26250.0,  # W5 tile logic ESTIMATE 105,000 um2 / 4 groups, placed at 50% utilisation
    logic_group_pruned_um2=18063.0,  # without unreachable fmul / tree registers (calibrated to W5 pruned tile)
    kv_sram_group_um2=94.824 * 41.04,
    util=0.5,
    port_tiles=24,
)


QWEN_EXCHANGE = "q256d64"   # ROOT DECISION 2026-09-29 (W15): the TP-2 oneshot at 256 lanes / depth 64, measured
                            # 71 cycles per all-reduce end to end (results/rtl/w15_collectives.json)
QWEN_EXCHANGE_AS_BUILT = "q16d16"   # ot_qwen_tp_host_binding's engine (16 lanes, depth 16)


def qwen_eval(G=6144, su_width=1024, wires=True, pruned=False, ctx=8192, drafter=False, wire_model="w5",
              x_read_elems=None, exchange="default"):
    """wire_model "w5": W5's per-op x/conflict/write terms plus per-token tree and UCIe terms; "w12": the W12
    floorplan's per-op engine latency (QWEN_WIRE_W12, tree included) plus the UCIe term.  x_read_elems: the VM's
    x-read width (None: unconstrained, as the RTL's per-group x ports); stalls are added per token."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    Q.CLOCK[0] = Q.clock_hz()
    k0 = dict(T.K)
    # W5 derived its wire terms with the unloaded fit (0.5997 ps/um); re-derive the x broadcast from its
    # 27.0 mm distance with the loaded channel constant and scale the tree/UCIe wire terms by the same ratio
    x_extra = wire_cycles(27000.0, Q.clock_hz(), WIRE_PS_PER_UM_LOADED) - 1
    wscale = x_extra / QWEN_WIRE["x_stages_extra"]
    try:
        if wires and wire_model == "w12":
            T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
        elif wires:
            T.K["me_lat"] = k0["me_lat"] + x_extra + QWEN_WIRE["vm_conflict_reg"] \
                + QWEN_WIRE["result_write_extra"]
        r = Q.as_built(ctx, groups=G, su_width=su_width)
    finally:
        T.K.clear()
        T.K.update(k0)
    if wires and wire_model == "w12":
        per_token = round(QWEN_WIRE["ucie_wire_per_token"] * wscale)
    elif wires:
        per_token = round((QWEN_WIRE["tree_extra_per_token"] + QWEN_WIRE["ucie_wire_per_token"]) * wscale)
    else:
        per_token = 0
    x_stall = qwen_x_read_stall(G, su_width, ctx, x_read_elems)[0] if x_read_elems else 0
    cycles = r["cycles"] + per_token + x_stall
    exch_measured = None
    if exchange == "default":        # the measured exchange includes its die wires: ideal-wire rows keep the priced one
        exchange = QWEN_EXCHANGE if wires else None
    if exchange:
        # W15: replace the priced 73 exchanges (hop + transfer + add each) and their die-wire term with the RTL
        # measurement of the token's 73 exchanges, issue -> last result, wires and link layer included
        ucie_w = round(QWEN_WIRE["ucie_wire_per_token"] * wscale) if wires else 0
        exch_measured = w15_record()["configs"][exchange]["exchanges"]["token_exchange_cycles"]
        cycles += exch_measured - Q.tp_exchanges(Q.CLOCK[0])["exchange_cycles"] - ucie_w
    a = QWEN_AREA
    tiles = G / 4
    # integer banking (W12): a group-pair column holds its words in whole 4096-deep banks; 11 at G=6144,
    # 14 at G=5120 (tools/qwen_o4_rom_placement.py QWEN_O4_GROUPS); other G scale the column words
    # USER DECISION 2026-09-29: the Qwen ROM die is AR only, so the DFlash drafter (fc + 5 layers) is not in ROM.
    # Target-only column words: 38,880 at G=6144 (W5), 48,736 at G=5120 (W12); drafter adds 5,600 / 6,880.
    words = (38880 * 6144 / G) + ((5600 * 6144 / G) if drafter else 0)
    exact = {(6144, False): 38880, (6144, True): 44480, (5120, False): 48736, (5120, True): 55616}
    words = exact.get((G, drafter), words * 1.02)          # other G: scaled, +2% tile padding
    banks = math.ceil(words / 4096)
    macros_tile = 2 * banks
    # result-port groups = G / smallest split: 96 at G=6144 (S=64), 40 at G=5120 (S=128); their tiles sit in
    # the spine, and fewer of them return spine area to the array (W12)
    port_tiles = {6144: 24, 5120: 10}.get(G, 24)
    logic = a["logic_group_pruned_um2"] if pruned else a["logic_group_um2"]
    tile_um2 = macros_tile * a["macro_um2"] * a["macro_pack"] + 4 * (logic / a["util"]
                                                                     + a["kv_sram_group_um2"] * a["macro_pack"])
    need_mm2 = (tiles - port_tiles) * tile_um2 / 1e6          # port tiles sit in the spine (W5)
    avail = a["array_mm2"] + (a["port_tiles"] - port_tiles) * tile_um2 / 1e6  # spine area freed by fewer ports
    return dict(G=G, su_width=su_width, wires=wires, pruned=pruned, ctx=ctx, drafter=drafter, cycles=cycles,
                exchange=exchange, exchange_cycles_measured=exch_measured,
                arch_cycles=r["cycles"], tokens_s=Q.CLOCK[0] / cycles, clock_hz=Q.CLOCK[0],
                tile_um2=round(tile_um2), tiles=tiles, array_need_mm2=round(need_mm2, 1),
                array_avail_mm2=round(avail, 1), fits=need_mm2 <= avail, banks_per_column=banks,
                port_tiles=port_tiles, wire_model=wire_model if wires else None, x_read_elems=x_read_elems,
                x_read_stall_cycles=x_stall, vm_banking=vm_banking(x_read_elems) if x_read_elems else None,
                unit_busy=r["unit_busy"], stalls=r["sequencer_stalls"])


def qwen_rows():
    rows = [qwen_eval(6144, 1, wires=False, exchange=QWEN_EXCHANGE_AS_BUILT) | dict(design="qwen_as_built_rtl_no_wires"),
            qwen_eval(6144, 1024, wires=False) | dict(design="qwen_arch"),
            qwen_eval(6144, 1024) | dict(design="qwen_arch_plus_wires"),
            qwen_eval(6144, 1024, pruned=True) | dict(design="qwen_pruned_plus_wires")]
    for G in (3072, 4096, 4608, 5120, 5632, 6144):
        for pr in (False, True):
            rows.append(qwen_eval(G, 1024, pruned=pr) | dict(design=f"qwen_G{G}{'_pruned' if pr else ''}"))
    rows.append(qwen_eval(5120, 1024, pruned=True, drafter=True) | dict(design="qwen_G5120_pruned_with_drafter"))
    rows.append(qwen_eval(6144, 1024, pruned=True, drafter=True) | dict(design="qwen_G6144_pruned_with_drafter"))
    # W12: the floorplan's per-op engine latency, and the VM x-read width (128 = the W5 VM; 512; 2,048)
    rows.append(qwen_eval(6144, 1024, pruned=True, wire_model="w12") | dict(design="qwen_G6144_pruned_w12_wires"))
    for xr in (128, 512, 2048):
        rows.append(qwen_eval(6144, 1024, pruned=True, wire_model="w12", x_read_elems=xr)
                    | dict(design=f"qwen_G6144_pruned_w12_wires_vm{xr}"))
    for r in rows:
        print(f"{r['design']:28s} {r['tokens_s']:8.0f} tok/s  cycles {r['cycles']:>9}  array {r['array_need_mm2']:6.1f}"
              f"/{r['array_avail_mm2']}  fits={r['fits']}")
    return rows


# ---------------------------------------------------------------------------------------------------------
# HBM comparators: a replicated GPU organisation (AGENTS.md rule 3; W9 handoff /tmp/claude-1000/handoff_w9.md)
# ---------------------------------------------------------------------------------------------------------
# Element: an SM-like cluster (4 sub-partitions, Tensor-Core-style exact MMA with golden accumulation order,
# 256 KB RF, ~228 KB SMEM, a bulk-copy port from L2/NoC).  At batch 1 the die is HBM-bound, so the
# microarchitecture terms that decide the token are:
#   supply   the fraction of sustained HBM bandwidth the weight path achieves.  It needs bandwidth x latency
#            bytes in flight (3.6 TB/s x ~0.5 us = 1.8 MB per die); the measured ROM-style QE adapter keeps
#            ~7 words in flight and delivers 39 B/cycle (W4, results/rtl/v41_qe_shared_stall.json).
#   barrier  every dependent operation boundary synchronises the SMs; a hardwired sequencer pays ~7 cycles,
#            a GPU grid barrier through L2 pays more (ASSUMED 200 cycles with a hardware barrier network;
#            1,500 ns is the cooperative-groups grid.sync class -- ASSUMED, to be cited).
#   compute  SMs sized to bandwidth (W9: 32 SMs x 4,096 INT8 MAC/clk per Qwen die) never bind at batch 1.
GPU = dict(barrier_cycles_hw=200,           # superseded: the pre-W13 ASSUMED hardware barrier (kept for the
                                             # labelled comparison row); W13 derives it from the floorplan
                                             # and measures it in RTL (hbm_gpu_design()["barrier"])
           barrier_ns_grid=1097.0,           # MEASURED H100 SXM5 cooperative grid.sync, 132 SMs x 256 threads
                                             # (results/measured/h100_nvls_20261004; owner 2026-10-04 default)
           barrier_ns_grid_v100_superseded=1430.0,   # V100 cooperative-groups grid sync, 1 block/SM, 32 threads
                                             # (L. Zhang et al., "A Study of Single and Multi-device
                                             # Synchronization Methods in Nvidia GPUs", IPDPS 2020, Fig. 5)
           barrier_ns_grid_sensitivity=dict(p100_1_block_per_sm=1770.0, v100_1024_threads=2210.0),
           # MEASURED H100 SXM5 (results/measured/h100_nvls_20261004): back-to-back stream kernel launch, CUDA-graph
           # kernel node (the grid sync above is the same campaign)
           barrier_ns_grid_h100_measured=1097.0, kernel_launch_ns_h100_measured=2672.0,
           graph_node_ns_h100_measured=1014.0,
           barrier_cycles_dsmem_ref=(181, 213),  # H800 SM-to-SM DSMEM latency, cluster 2..16 (Luo et al.,
                                             # arXiv 2501.12084 7.1): the reference for an on-die hardware barrier
           seq_gap_cycles=7,
           adapter_measured_Bpc=39.0, sustained_frac=1.0)


def _grid_tag():
    """Row-name suffix of the grid-sync rows: the measured H100 default, or the superseded V100 figure."""
    return "v100" if GPU["barrier_ns_grid"] == GPU["barrier_ns_grid_v100_superseded"] else "h100"


def qwen_hbm_rows():
    """Qwen3-8B HBM die token.  Headline: the W13 prefetching bulk-copy model (stream_overlap over the program's
    ops; a boundary is exposed only when the SMEM staging cannot hide it).  The additive rows (T = t_hbm +
    boundaries x barrier + tp) are the pre-W13 form, kept and labelled no-prefetch."""
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    hc = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())["hbm_comparator"]["8192"]["rom_format_int8"]
    t_hbm = hc["token_s"]                                        # 8.175 GB at 7.2 TB/s sustained (8 stacks)
    per_die_Bpc = hc["hbm_bytes_per_cycle"] / 2                  # 3,277 B/cycle per die
    # global barriers: one after every MMA op (qkv, attention pv, o, gate_up, down x 36, lm_head); heads are
    # SM-local and the norms run redundantly on the replicated x, so they need none (W13; was 217 + 2 x 36)
    boundaries = 5 * 36 + 1
    tp = Q.tp_exchanges(clock)["cycles"] / clock
    dq = hbm_gpu_design("qwen")
    bnd = dq["barrier"]["boundary_cycles"]
    rows = [dict(design="qwen_hbm_ideal", T_us=round(t_hbm * 1e6, 1), tokens_s=round(1 / t_hbm, 1), supply_frac=1.0,
                 boundaries=boundaries, form="bandwidth only")]
    t = dq["token"]
    rows.append(dict(design="qwen_hbm_gpu", T_us=round(t["cycles"] / clock * 1e6, 1), tokens_s=t["tokens_s"],
                     supply_frac=1.0, boundaries=t["boundaries"], barrier_cycles=bnd,
                     exposed_over_hbm_cycles=t["exposed_over_hbm_cycles"],
                     form="prefetching bulk copy (stream_overlap); barrier derived from the floorplan"))
    for tag, supply, barrier_s in (
            ("qwen_hbm_adapter_as_built_no_prefetch", GPU["adapter_measured_Bpc"] / per_die_Bpc, GPU["seq_gap_cycles"] / clock),
            ("qwen_hbm_gpu_derived_barrier_no_prefetch", 1.0, bnd / clock),
            ("qwen_hbm_gpu_assumed200_no_prefetch", 1.0, GPU["barrier_cycles_hw"] / clock),
            (f"qwen_hbm_gpu_grid_sync_{_grid_tag()}_no_prefetch", 1.0, GPU["barrier_ns_grid"] * 1e-9)):
        T = t_hbm / supply + boundaries * barrier_s + tp
        rows.append(dict(design=tag, T_us=round(T * 1e6, 1), tokens_s=round(1 / T, 1), supply_frac=supply,
                         barrier_us_per_token=round(boundaries * barrier_s * 1e6, 1), boundaries=boundaries,
                         form="additive (pre-W13)"))
    # grid sync with prefetch: the boundary cost enters the stream model
    ops = qwen_hbm_ops(dq["element"], GPU["barrier_ns_grid"] * 1e-9 * clock, dq["drain_cycles"])
    tg, _ = stream_overlap(ops, dq["hbm_Bpc"], dq["sm_count"] * dq["element"]["ingest_Bpc"],
                           dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    rows.append(dict(design=f"qwen_hbm_gpu_grid_sync_{_grid_tag()}", T_us=round(tg / clock * 1e6, 1),
                     tokens_s=round(clock / tg, 1), supply_frac=1.0, boundaries=boundaries,
                     form=f"prefetching bulk copy, {_grid_tag().upper()} grid sync "
                          f"{GPU['barrier_ns_grid'] * 1e-3:.2f} us per boundary"))
    return rows


def v41_boundaries(path, nodes):
    """Global barriers on the V4.1 critical path under the W13 SM mapping: one after every matvec (its rows
    are spread over the SMs), one per attention layer (scores -> softmax -> pv is head-local in the
    dedicated attention unit), one per indexer final top-k, and the argmax.  Norms and the router top-6 run
    redundantly on the replicated x and need none."""
    n = 0
    for x in path:
        k = nodes[x]["kind"]
        if k == "matvec" or x.endswith((".attn.scores", ".idx.topk_final")) or x == "argmax":
            n += 1
    return n


def sm_op_cycles(rows_die: float, K: int, fmt: str, drain: int, group_slot: bool, n_sm: int = 32):
    """One matvec on the SM array: rows_die rows split over n_sm SMs, each row's K inside one SM.  Row-slot
    issue holds IL rows in flight, each walking its G groups x c k-steps (a single row is a K-chain);
    group-slot issue spreads a row's (row, group) items over the IL slots.  Calibrated: the RTL SM
    (results/rtl/gpu_sm_blockdot_exact.json) takes 689 cycles for 9 rows at FP8 K = 5,120 row-slot."""
    rows_sm = math.ceil(max(1.0, rows_die) / n_sm)
    if fmt in ("fp8", "fp4"):
        C, la = math.ceil(K / 256), (8 if fmt == "fp4" else 4)
    else:
        C, la = math.ceil(K / 8), 64
    G, c = math.ceil(C / la), 8
    if group_slot:
        return math.ceil(rows_sm * G / 8) * c * 8 + drain
    return math.ceil(rows_sm / 8) * G * c * 8 + drain


V41_HBM_FABRIC_US = dict(collective_latency=125.9, collective_bytes=1.5, pipeline_hops=0.9, control=2.0)
V41_HBM_DIES = 96          # G = 96: every matrix 1/96 per die (W9 handoff 8)

# HBM switch collective latency, AUTHORITATIVE (owner decision 2026-10-04, third revision).  Scenarios:
#   nvls_measured   (alias central): MEASURED H100 HGX one-shot NVLS all-reduce / multimem.st all-gather with relaxed
#                   hardware-path sync (results/measured/h100_nvls_20261004; NVLink4 / H100 generation).
#                   DEFAULT for the GPU-organised ABLATION (v41_hbm_chain / v41_hbm_rows).
#   gpu_fenced      (alias high): MEASURED one-shot NVLS AR with GPU-correct sys-scope release/acquire sync.
#                   DEFAULT for the GPU-faithful rows.
#   tomahawk_ultra_protocol: a stock Broadcom Tomahawk Ultra scale-up Ethernet tier (~8 chips, one tier, each 2-die
#                   package striping over 8 x 800G ports) running OUR protocol (hardware-initiated register-to-register
#                   sends, completion by arrival counting, link-level retry + CRC, credit flow control).  AR = reduce-
#                   scatter to the slice owner (1 crossing, switch forwards only) + fixed golden-order owner reduction
#                   (HA2 measured reducer) + cut-through switch multicast (2nd crossing); gather = 1 multicast crossing.
#                   Priced PER OP at the W19 program's actual bytes.  DEFAULT for the HBM ACCELERATOR.
#   tomahawk_ultra_inc: the same tier with in-switch reduction (1 crossing): SENSITIVITY only (the switch's reduction
#                   order is unpublished, so bit-exact golden order is not guaranteed).
#   push_optimistic (alias low): measured in-switch data path + one hardware notification (barrier nearly free).
#   w15: the SUPERSEDED RTL-model term (2 x 209 + 250 = 668 ns; W15 fit AR 823.6 / AG 777.0 ns).
# NVLS scenarios replace only the FIXED term (small-message value; W15 slopes carry the bytes; 32 KB = bracket) and add
# a 48-package striping tail of 0.15 us (0.1-0.2), justified by NVLS being flat from 2 to 8 GPUs.  Reach: the measured
# HGX path is board traces (~85 ns a leg incl. switch), at or below the ROM light-FEC 130 ns class: fec="board" is the
# reach-matched default; fec="kp4" adds (209 - 130) ns per SerDes leg (rack-cable sensitivity).  The Tomahawk crossing
# is the SUE rack budget (3 m twinax .. 10 m SMF), already rack reach: fec does not apply to it.
_TAIL_US = 0.15
_BAR_RLX_US = (0.704 + 0.731) / 2                 # measured relaxed multimem.red barrier, flat for 2/4/8 GPUs
_BAR_SYS_US = (4.020 + 4.044) / 2                 # measured sys-scope release/acquire barrier
_NOTIFY_US = _BAR_RLX_US / 2                       # one hardware notification: half the relaxed barrier (~0.36 us)
# Tomahawk Ultra / SUE one-way crossing (Broadcom Scale-Up Ethernet Framework RM104, App. A, Fig. 22; VENDOR BUDGETS):
# endpoint bridge NoC<->Ethernet 100 ns (Tx+Rx) + endpoint Ethernet link+PHY 100 ns (Tx+Rx) + switch Tx+Rx 250 ns
# (includes its PHY/FEC) + 2 x cable (4.6 ns/m twinax, 4.96 ns/m SMF): 477.6 (3 m twinax) / 496 (5 m HCF) / 549.2 (10 m SMF)
TU = dict(endpoint_bridge_ns=100.0, endpoint_phy_ns=100.0, switch_ns=250.0, cable_ns=dict(twinax_3m=2 * 3 * 4.6,
          hcf_5m=2 * 5 * 4.6, smf_10m=2 * 10 * 4.96),
          port_gbps=800.0, ports_per_package=8, payload_eff=0.9,       # ASSUMED framing/header efficiency
          # HA2 measured endpoint reducer (results/rtl/hbm_accel_ha2_ar_20261004, main c7d138048/13b92e71e): golden
          # pairwise tree over the o-group's 8 contributors, ot_hdc_fp32_add_lat #(7), LAT x log2(8) = 21 cycles +
          # golden to_bf16 1 cycle, cut-through (a flit reduces as soon as its operands are slotted) at 1.2 GHz
          reducer_cycles=7 * 3 + 1, reducer_hz=1.2e9, inc_reduce_ns=50.0,  # in-switch reduce pipeline (ASSUMED, research note)
          src="results/uarch/hbm_switch_latency_range_20261004/switch_latency_research.md rows 21, 30 (RM104 App. A)")
TU["bw_Bps"] = TU["port_gbps"] * 1e9 / 8 * TU["ports_per_package"] * TU["payload_eff"]   # 720 GB/s striped payload
TU["reduce_ns"] = TU["reducer_cycles"] / TU["reducer_hz"] * 1e9


def tu_crossing_ns(cable="twinax_3m"):
    return TU["endpoint_bridge_ns"] + TU["endpoint_phy_ns"] + TU["switch_ns"] + TU["cable_ns"][cable]


def tu_transport_us(kind, nbytes, scenario="tomahawk_ultra_protocol", cable="twinax_3m", tail_us=_TAIL_US):
    """One W19 collective's transport time (us) on the Tomahawk Ultra tier at its actual bytes (P x op bytes)."""
    x = tu_crossing_ns(cable)
    ser = nbytes / TU["bw_Bps"] * 1e9
    if kind == "all_reduce":
        if scenario == "tomahawk_ultra_inc":       # push to the switch, reduce in-switch, multicast: 1 crossing
            ns = x + TU["inc_reduce_ns"] + 2 * ser
        else:                                      # RS (1 crossing) + owner reduce + cut-through multicast (crossing 2)
            ns = 2 * x + TU["reduce_ns"] + 2 * ser
    else:                                          # gather / kv gather / top-k merge: one multicast crossing
        ns = x + ser
    return ns * 1e-3 + tail_us


HBM_SWITCH_LATENCY = dict(
    push_optimistic=dict(ar_us=dict(small=0.783 + _NOTIFY_US + _TAIL_US, kb32=1.136 + _NOTIFY_US + _TAIL_US),
             ag_us=dict(small=0.762 + _NOTIFY_US + _TAIL_US, kb32=0.762 + 0.209 + _NOTIFY_US + _TAIL_US),
             legs_ar=8, legs_ag=4, basis="MEASURED data path + DERIVED notification",
             mechanism="in-switch data path only (multimem.ld_reduce slice + multimem.st, measured 783-1,136 ns = "
                       "one-shot relaxed AR minus its 2 barriers) + ONE hardware notification (~0.36 us = half the "
                       "measured relaxed barrier).  Gather: one multicast store (measured relaxed one-way store 762 ns; "
                       "32 KB adds the measured AG size increment 0.209 us) + notification -- DERIVED"),
    nvls_measured=dict(ar_us=dict(small=2.244 + _TAIL_US, kb32=2.597 + _TAIL_US),
                 ag_us=dict(small=1.382 + _TAIL_US, kb32=1.590 + _TAIL_US),
                 legs_ar=10, legs_ag=6, basis="MEASURED",
                 mechanism="measured one-shot NVLS all-reduce with relaxed hardware-path sync (barrier + ld_reduce "
                           "slice + multimem.st + barrier), 2,244 ns (128 B) - 2,597 ns (32 KB) at 8 GPUs, flat in "
                           "group size; gathers: measured multimem.st all-gather 1,382 (128 B) / 1,590 ns (32 KB "
                           "total).  Relaxed sync bounds the HARDWARE path (not memory-model-guaranteed)"),
    gpu_fenced=dict(ar_us=dict(small=8.904 + _TAIL_US, kb32=9.144 + _TAIL_US),
              ag_us=dict(small=1.382 + 2 * (_BAR_SYS_US - _BAR_RLX_US) + _TAIL_US,
                         kb32=1.590 + 2 * (_BAR_SYS_US - _BAR_RLX_US) + _TAIL_US),
              legs_ar=10, legs_ag=6, basis="MEASURED (AR); DERIVED (AG: measured relaxed AG + 2 x (sys - relaxed "
                                           "barrier))",
              mechanism="measured one-shot NVLS all-reduce with GPU-correct sys-scope release/acquire sync, "
                        "8,904-9,144 ns: what GPU software pays without special hardware"),
    tomahawk_ultra_protocol=dict(per_op=True, basis="VENDOR BUDGET (SUE RM104 crossing) + MEASURED (HA2 reducer) + "
                                 "DERIVED (serialisation, tail)",
                                 mechanism="stock Tomahawk Ultra tier + our protocol: AR = 2 crossings + golden-order "
                                           "owner reduction + 2 x serialisation; gather = 1 crossing + serialisation; "
                                           "+ 0.15 us striping tail over ~8 chips"),
    tomahawk_ultra_inc=dict(per_op=True, basis="SENSITIVITY: in-switch reduction, reduction order unpublished",
                            mechanism="AR = 1 crossing + in-switch reduce (~50 ns ASSUMED) + 2 x serialisation + tail"),
    w15=dict(basis="SUPERSEDED RTL model: 2 x 209 + 250 = 668 ns switch (V41_HBM_FABRIC_US lump); W15 fit fixed "
                   "AR 823.6 / AG 777.0 ns (the W19 parts embed it)"),
    generation="NVLS anchors: NVLink4 / H100 SXM5 HGX (NVSwitch gen3), measured 2026-10-04; not NVLink5 / NVL72. "
               "Tomahawk Ultra: vendor budget (RM104), not measured",
    tail_us=_TAIL_US, tail_range_us=[0.1, 0.2], notify_us=_NOTIFY_US,
    barrier_relaxed_us=_BAR_RLX_US, barrier_sys_us=_BAR_SYS_US, tomahawk=TU,
    retry_tail_us=[0.2, 0.5], kp4_leg_ns=209.0, light_leg_ns=130.0,
    w15_fixed_ns=dict(ar=988.74 / 1.20048019208, ag=932.8 / 1.20048019208),   # W19_COLL_FIT (hbm_p48_ss)
    w19_mix=dict(all_reduce=40, gather_like=225),
    src="results/measured/h100_nvls_20261004/README.md")
HBM_SWITCH_ALIASES = dict(low="push_optimistic", central="nvls_measured", high="gpu_fenced")
HBM_SWITCH_LATENCY_LITERATURE_SUPERSEDED = dict(
    low=dict(ar_us=0.65, ag_us=0.60, traversals_ar=1, traversals_ag=1),
    central=dict(ar_us=1.40, ag_us=1.20, traversals_ar=1, traversals_ag=1, ar_range_us=[1.3, 1.5]),
    high=dict(ar_us=3.25, ag_us=2.0, traversals_ar=4, traversals_ag=2, ar_range_us=[3.0, 3.5]),
    superseded_by="results/uarch/hbm_switch_latency_authoritative_20261004",
    src="results/uarch/hbm_switch_latency_range_20261004/switch_latency_research.md (sec. 2)")
# AUTHORITATIVE DEFAULTS (owner 2026-10-04): ablation = measured NVLS hardware path; accelerator = Tomahawk Ultra +
# our protocol; GPU-faithful = GPU-correct fenced + measured H100 grid sync.  "w15" restores the superseded lump.
HBM_SWITCH_DEFAULTS = dict(ablation="nvls_measured", accelerator="tomahawk_ultra_protocol", gpu_faithful="gpu_fenced")
_HBM_SWITCH = HBM_SWITCH_DEFAULTS["ablation"]   # the scenario v41_hbm_chain (the GPU-organised ablation) prices
_HBM_FEC = "board"        # as measured (HGX board reach, ROM-matched); "kp4" = rack-cable sensitivity
W19_PROGRAM = "results/rtl/w19_hbm_tp96_program_oreduce.json"
W19_COLL_RECORD = "results/uarch/w19_hbm_token_ar.json"
_W19_OPS = None


def w19_collective_ops():
    """The W19 program's on-path collectives (265: 40 o-group AR + 225 gather-like), as w19_hbm_token_compose walks them."""
    global _W19_OPS
    if _W19_OPS is None:
        import w19_hbm_token_compose as W
        prog = json.loads((ROOT / W19_PROGRAM).read_text())
        coll = json.loads((ROOT / W19_COLL_RECORD).read_text())["result"]["collective_model"]
        ops = [op for lay in prog["layers"] for op in lay["ops"]
               if op["kind"] in ("all_gather", "all_reduce", "topk_merge", "kv_gather")
               and not op["tag"].startswith(W.OFF_PATH_COLL)]
        _W19_OPS = (ops, coll, W)
    return _W19_OPS


def w19_transport_us(P=1, scenario="w15", fec="board", cable="twinax_3m"):
    """Sum of the W19 on-path collectives' TRANSPORT time (us) for a pass of P positions: the W15 product-port pricing
    (fixed + slope) without the top-k merges' select term (compute, kept unchanged), or a scenario's.  NVLS-class
    scenarios replace the fixed term only; Tomahawk Ultra prices every op at its P x bytes."""
    ops, coll, W = w19_collective_ops()
    hz = coll["hz"]
    tot = 0.0
    for op in ops:
        us, _ = W.prod_us(op, coll, P)
        if op["kind"] == "topk_merge" and op.get("what") in ("sel", "cand"):
            us -= 9 * (W.TP * op["k"] / 64) * P / hz * 1e6
        kind = "ar" if op["kind"] == "all_reduce" else "ag"
        if scenario in ("tomahawk_ultra_protocol", "tomahawk_ultra_inc"):
            us = tu_transport_us(op["kind"], P * op["bytes"], scenario, cable)
        elif scenario != "w15" or fec != "kp4":
            fixed = (coll["ar"]["fixed_cycles"] if kind == "ar" else coll["ag"]["fixed_cycles"]) / hz * 1e6
            us += hbm_switch_collective_us(scenario, kind, fec) - fixed
        tot += us
    return tot


def hbm_switch_collective_us(scenario, kind="ar", fec="board", msg="small"):
    """Fixed latency (us) of one TP-96 collective, kind "ar" or "ag" (gather-like), msg "small" (<= 512 B, primary for
    the NVLS scenarios: W15 slopes carry the bytes) or "32KB" (bracket).  Tomahawk Ultra: transport at msg bytes
    (small = 512 B; 32KB = 32,768 B)."""
    scenario = HBM_SWITCH_ALIASES.get(scenario, scenario)
    if scenario == "w15":
        f = HBM_SWITCH_LATENCY["w15_fixed_ns"]["ag" if kind == "ag" else "ar"] * 1e-3
        return f - (0.0 if fec == "kp4" else 2 * (HBM_SWITCH_LATENCY["kp4_leg_ns"] - HBM_SWITCH_LATENCY["light_leg_ns"]) * 1e-3)
    if scenario in ("tomahawk_ultra_protocol", "tomahawk_ultra_inc"):
        return tu_transport_us("all_reduce" if kind == "ar" else "all_gather", 32768 if msg == "32KB" else 512, scenario)
    sc = HBM_SWITCH_LATENCY[scenario]
    key = "ag" if kind == "ag" else "ar"
    v = sc[key + "_us"]["kb32" if msg == "32KB" else "small"]
    d = HBM_SWITCH_LATENCY["kp4_leg_ns"] - HBM_SWITCH_LATENCY["light_leg_ns"]
    return v + (sc["legs_" + key] * d * 1e-3 if fec == "kp4" else 0.0)


def hbm_switch_mix_us(scenario, fec="board", msg="small"):
    """Per-collective latency at the W19 mix (40 all-reduce + 225 gather-like); Tomahawk Ultra: the W19 on-path ops'
    mean transport at their actual bytes."""
    scenario = HBM_SWITCH_ALIASES.get(scenario, scenario)
    if scenario in ("tomahawk_ultra_protocol", "tomahawk_ultra_inc"):
        return w19_transport_us(1, scenario) / len(w19_collective_ops()[0])
    mx = HBM_SWITCH_LATENCY["w19_mix"]
    n = mx["all_reduce"] + mx["gather_like"]
    return (mx["all_reduce"] * hbm_switch_collective_us(scenario, "ar", fec, msg)
            + mx["gather_like"] * hbm_switch_collective_us(scenario, "ag", fec, msg)) / n


def v41_hbm_fabric_us(switch=None, fec="board"):
    """The legacy fabric lump (V41_HBM_FABRIC_US: ~188 collectives x 0.668 us).  switch=None or "w15" keeps it
    exactly; a scenario prices each collective at its W19-mix per-collective latency.  Bytes, pipeline hops and
    control are kept."""
    f = dict(V41_HBM_FABRIC_US)
    if switch and switch != "w15":
        f["collective_latency"] = f["collective_latency"] / 0.668 * hbm_switch_mix_us(switch, fec)
    return f


# Opt-in owner/ACK/fence and refresh-live first-access hypothesis from the retained
# v41_hbm_service_term_20261003 proposal. Existing callers retain the exact off path.
V41_HBM_SERVICE = dict(
    off=dict(boundary_cycles=0, routed_fetch_ns=0.0),
    low=dict(boundary_cycles=2, routed_fetch_ns=133.2 + 5.4),
    central=dict(boundary_cycles=4, routed_fetch_ns=469.5 + 6.4 + 0.1),
    high=dict(boundary_cycles=6, routed_fetch_ns=526.4 + 7.4 + 18.3),
)


def v41_hbm_chain(group_slot: bool, positions: int = 1, barrier_cycles=None, service="off", switch=None, fec=None):
    """V4.1 HBM token on the SM design, K-chain aware: the arch DAG's critical path at 1M with every matvec
    re-priced as an SM op on its 1/96 row slice (sm_op_cycles), the dedicated units' nodes (W11 spec widths)
    at their arch price, one barrier per global boundary, and the comparator's switched-fabric terms.  The
    weight sweep streams under the chain.  With speculation, `positions` verify positions ride the MMA
    columns (one weight fetch); the dedicated units issue each position's work (their issue time repeats,
    their depth is paid once)."""
    d = hbm_gpu_design("v41")
    clock = d["clock_hz"]
    arch, b = arch_graph(1048576)
    g = b.g
    path = g.path(b.sink)
    mv = other = extra = xfill = 0.0
    for x in path:
        nd = g.nodes[x]
        t = sum(g.contrib[x].values())
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / V41_HBM_DIES
            mv += sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], d["drain_cycles"], group_slot) / clock
            # every SM needs the whole x (its rows span all of K): after the collective gathers it, the
            # die's x broadcast (X_BCAST_BPC) fills the 32 SM x stores -- BF16, every verify position
            xfill += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock
        elif nd["kind"] in ("collective", "hop"):
            continue                                   # replaced by the comparator's fabric terms
        else:
            other += t
            if positions > 1:
                extra += (positions - 1) * nd.get("issue", 0.0)
    nb = v41_boundaries(path, g.nodes)
    bc = d["barrier"]["boundary_cycles"] if barrier_cycles is None else barrier_cycles
    parts = dict(sm_matvec=mv * 1e6, x_broadcast_fill=xfill * 1e6, dedicated_and_su=other * 1e6,
                 verify_extra_issue=extra * 1e6, barrier=nb * bc / clock * 1e6,
                 **v41_hbm_fabric_us(switch or _HBM_SWITCH, fec or _HBM_FEC))
    parts["collective_bytes"] *= positions             # every position's activations cross the fabric
    sv = V41_HBM_SERVICE[service]  # named, source-priced profiles only
    if sv["boundary_cycles"] or sv["routed_fetch_ns"]:
        n_routed = sum(1 for x in path if x.endswith(".ffn.experts_gu"))
        parts["boundary_service"] = nb * sv["boundary_cycles"] / clock * 1e6
        parts["routed_fetch"] = n_routed * sv["routed_fetch_ns"] * 1e-3
    chain = sum(parts.values())
    T = max(chain, 37.4)
    return T, parts, nb


def v41_hbm_rows():
    """V4.1 HBM die token (G=96, 1M).  Headline: the K-chain-aware SM chain (v41_hbm_chain), row-slot and
    group-slot issue.  Kept for reference, labelled: the published additive breakdown (W9 handoff 8: compute
    chain 111.7, weight sweep 37.4, collective latency 125.9, bytes 1.5, hops 0.9, control 2.0 us, priced at
    die-pooled widths), and the no-prefetch forms."""
    base = dict(compute_chain=111.7, weight_sweep=37.4, **V41_HBM_FABRIC_US)
    clock = 1.0339e9
    arch, b = arch_graph(1048576)
    path = b.g.path(b.sink)
    boundaries = v41_boundaries(path, b.g.nodes)
    per_die_Bpc = 3.6e12 / clock
    bnd = hbm_gpu_design("v41")["barrier"]["boundary_cycles"]
    rows = []
    for tag, gs, bc in (("v41_hbm_gpu_rowslot", False, None), ("v41_hbm_gpu_groupslot", True, None),
                        (f"v41_hbm_gpu_groupslot_grid_sync_{_grid_tag()}", True, GPU["barrier_ns_grid"] * 1e-9 * clock)):
        # the GPU-faithful (grid-sync) row prices its collectives at the GPU-correct fenced scenario
        sw = HBM_SWITCH_DEFAULTS["gpu_faithful"] if (bc is not None and _HBM_SWITCH != "w15") else None
        T, parts, nb = v41_hbm_chain(gs, 1, bc, switch=sw)
        rows.append(dict(design=tag, T_us=round(T, 1), tokens_s=round(1e6 / T, 1), supply_frac=1.0, boundaries=nb,
                         form="K-chain-aware SM chain, prefetching bulk copy",
                         breakdown_us={k: round(x, 1) for k, x in parts.items()}))
    for tag, supply, barrier_s, prefetch in (
            ("v41_hbm_published", 1.0, 0.0, False),
            ("v41_hbm_pooled_chain_prefetch", 1.0, (bnd - GPU["seq_gap_cycles"]) / clock, True),
            ("v41_hbm_adapter_as_built_no_prefetch", GPU["adapter_measured_Bpc"] / per_die_Bpc, 0.0, False),
            ("v41_hbm_gpu_derived_barrier_no_prefetch", 1.0, (bnd - GPU["seq_gap_cycles"]) / clock, False),
            ("v41_hbm_gpu_assumed200_no_prefetch", 1.0, (GPU["barrier_cycles_hw"] - GPU["seq_gap_cycles"]) / clock, False)):
        parts = dict(base, weight_sweep=base["weight_sweep"] / supply, barrier=boundaries * barrier_s * 1e6)
        if prefetch:
            chain = sum(v for k, v in parts.items() if k != "weight_sweep")
            T = max(parts["weight_sweep"], chain)
            parts["weight_sweep_exposed"] = round(T - chain, 3)
        else:
            T = sum(parts.values())
        rows.append(dict(design=tag, T_us=round(T, 1), tokens_s=round(1e6 / T, 1), supply_frac=round(supply, 4),
                         boundaries=boundaries, form=("pooled-width chain (superseded upper bound)" if prefetch
                                                      else "additive"),
                         breakdown_us={k: round(x, 1) for k, x in parts.items()}))
    return rows


# ---------------------------------------------------------------------------------------------------------
# GPU-organised HBM die, microarchitecture (W13).  The rows above price the token with two free parameters
# (supply fraction, barrier cycles).  This section sizes the element and the networks that set them:
#   element   the SM: 4 sub-partitions of an exact Tensor-Core-style MMA (lanes x columns), its x store and
#             weight staging in SMEM, SIMT FP32 lanes for the stream-unit work, one fixed pairwise FP32 tree
#             per column across the SM's lanes and a streaming pairwise stack behind it, so a row's whole K
#             and its golden tree stay inside one SM (rtl/gpu/ot_gpu_mma.sv).
#   count     the smallest symmetric SM count whose token is within 0.5% of an unbounded SM array, with the
#             weight stream overlapping every dependent boundary through the SMEM staging.
#   bulk copy HBM bandwidth x loaded latency in flight (Little's law), split over the SMs, in 64 B sectors.
#   staging   SMEM that keeps the prefetching stream running through a boundary (fluid simulation below).
#   barrier   arrival tree + release broadcast over the floorplan distances (tools/hbm_gpu_floorplan.py),
#             at the loaded wire constant, plus the node registers, plus the x-broadcast tail.
# ---------------------------------------------------------------------------------------------------------
HBM_DIE = dict(
    w_um=31800.0, h_um=815e6 / 31800.0,          # 815 mm2 outline shared with W1/W5 (qwen_o4_floorplan.DIE_W)
    stacks=4, phy_um=(12000.096, 833.49),        # ot_hbm3e_phy LEF: two on each long (north/south) edge = 48 mm
    core=(1213.488, 1555.2, 31780.0, 24078.0),   # W5 hbm_die.frame core after PHY rows, service bands, UCIe
    src="results/floorplan/qwen_o4/floorplan.json designs['hbm_die.frame']",
)
HBM_LOADED_LAT_NS = 500.0     # ASSUMED loaded HBM read latency incl. controller queue: the model's 1.8 MB in
                              # flight at 3.6 TB/s (v41 first-access 1 us is the data-dependent gather case)
SECTOR_B = 64                 # HBM3E pseudo-channel access (BL8 x 64 bit)
GPU_UNIT_UM2 = dict(
    lane=8449.0 / 16,         # ot_hdc_lane_copy: exact BF16 mul -> circulating FP32 add (IL 8), 16 lanes 8,449 um2,
                              # closed 0.9 ns (results/physical_abi3/asap7/hdc/ot_hdc_lane_copy/physical.json)
    int8_decode=40.0,         # ASSUMED registered INT8 -> BF16 decode per lane (replaced by the hardened TC)
    fp32_add=UNIT["fp32_add_um2"], fp32_mul=UNIT["fp32_mul_um2"], blockdot=UNIT["blockdot_um2"],
    simt_lane=UNIT["fp32_mac_um2"],
    sram32k=SRAM_256B_MACRO["um2"],
    dff=DFF_UM2,
)
SRAM_128X256_UM2 = 94.824 * 41.04   # ot_sram_1r1w_128x256_m1_r2c2 (physical/asap7_memory_macros)
GPU_LOGIC_UTIL = 0.5          # std-cell placement density (W5 convention; replaced by the hardened macro)
GPU_MACRO_PACK = 1.31         # macro footprint / macro area (W5 tile calibration)

SM_ELEM = {
    # Qwen3-8B: INT8 weight codes, 128 B/clk of weights = 128 lanes; 16 columns = the DFlash b16 verify block
    # (design point block 5) and batch <= 16 without re-streaming weights
    "qwen": dict(subparts=4, int8_lanes=128, bf16_lanes=0, blockdot_lanes=0, cols=16, il=8, ingest_Bpc=128,
                 k_max=12288, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=5),
    # DeepSeek-V4.1: FP4 routed experts (8 block-dot lanes = 256 FP4 weights = 128 B/clk), FP8 dense at the same
    # 128 B/clk on 4 of them, BF16 matrices on 64 lanes; 8 columns cover MTP (m+1 = 7 positions); the group-slot
    # x store delivers all 8 columns' fragment every cycle (16 columns would double it to 197 macros)
    "v41": dict(subparts=4, int8_lanes=0, bf16_lanes=64, blockdot_lanes=8, cols=8, il=8, ingest_Bpc=128,
                k_max=5120, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=3,
                # group-slot issue: a row's K groups on different accumulator slots, so a 1-2-row slice is not a
                # K-chain; the x store must then deliver a new fragment every cycle for up to gs_cols columns
                group_slot=True, gs_cols=8),
}


def gpu_hardened_columns():
    """Routed (flat, ASAP7, 0.92 ns, closed) column areas that replace the unit-sum estimate:
    ot_gpu_tc_col at 16 lanes (lanes + 15-adder tree) and ot_gpu_bd_col at 2 block-dot lanes (+ tree)."""
    out = {}
    for key, rec, lanes in (("lane_with_tree", "ot_gpu_tc_col_l16_092", 16), ("blockdot_with_tree", "ot_gpu_bd_col_lb2_092", 2)):
        p = ROOT / f"results/physical_abi3/asap7/gpu/{rec}/physical.json"
        if p.exists():
            r = json.loads(p.read_text())
            if r.get("status") == "pass" and r["design"].get("closed"):
                out[key] = r["design"]["area_um2"] / lanes
                out[key + "_source"] = str(p.relative_to(ROOT))
    return out


def sm_area(e: dict, staging_kb: float):
    """SM element area (mm2) by resource; logic placed at GPU_LOGIC_UTIL, SRAM at GPU_MACRO_PACK.  Where a
    column has been routed (gpu_hardened_columns) its measured area per lane replaces lanes + tree."""
    u = GPU_UNIT_UM2
    c = e["cols"]
    lanes = e["int8_lanes"] + e["bf16_lanes"]
    hc = gpu_hardened_columns()
    if "lane_with_tree" in hc:
        lane_tree = c * (e["int8_lanes"] * (hc["lane_with_tree"] + u["int8_decode"])
                         + e["bf16_lanes"] * hc["lane_with_tree"])
    else:
        lane_tree = c * (e["int8_lanes"] * (u["lane"] + u["int8_decode"]) + e["bf16_lanes"] * u["lane"]) \
            + c * (max(lanes, 1) - 1) * (u["fp32_add"] + 32 * u["dff"]) * (1 if lanes else 0)
    if "blockdot_with_tree" in hc:
        bd = c * e["blockdot_lanes"] * hc["blockdot_with_tree"]
    else:
        bd = c * e["blockdot_lanes"] * (u["blockdot"] + u["fp32_add"] + 8 * 32 * u["dff"]) \
            + (c * (e["blockdot_lanes"] - 1) * (u["fp32_add"] + 32 * u["dff"]) if e["blockdot_lanes"] and not lanes else 0)
    logic = dict(
        mma_lanes_and_trees=lane_tree,
        blockdot_and_trees=bd,
        stack=c * e["stack_levels"] * (u["fp32_add"] + 2 * 34 * u["dff"]),
        row_scale=c * u["fp32_mul"],
        simt=e["simt_lanes"] * u["simt_lane"],
        x_operand_regs=2 * max(lanes * 16, e["blockdot_lanes"] * 264) * c * u["dff"],   # double-buffered x fragment
    )
    x_kb = e["k_max"] * c * e["x_bytes"] / 1024
    sram_kb = dict(x_store=x_kb, staging=staging_kb, scratch=e["scratch_kb"])
    macros = {k: math.ceil(v / 32) for k, v in sram_kb.items()}
    # the x store must also deliver one x fragment (every lane, every column) per slot revolution (IL cycles):
    # 256-bit macros read every cycle into a double-buffered fragment register
    frag_bits = c * (lanes * 16 + e["blockdot_lanes"] * 266)
    macros["x_store"] = max(macros["x_store"], math.ceil(frag_bits / e["il"] / 256))
    sram_um2 = {k: u["sram32k"] for k in macros}
    if e.get("group_slot"):
        # group-slot reads a whole gs_cols-column fragment every cycle: shallow 128 x 256 macros (4 KB each)
        per_col = lanes * 16 + e["blockdot_lanes"] * 266
        bw = math.ceil(e["gs_cols"] * per_col / 256)
        macros["x_store"] = max(bw, math.ceil(x_kb / 4))
        sram_um2["x_store"] = SRAM_128X256_UM2
    logic_mm2 = sum(logic.values()) / 1e6
    sram_mm2 = sum(macros[k] * sram_um2[k] for k in macros) * GPU_MACRO_PACK / 1e6
    return dict(logic_um2={k: round(v) for k, v in logic.items()}, logic_mm2=round(logic_mm2, 3),
                hardened_columns=hc,
                footprint_logic_mm2=round(logic_mm2 / GPU_LOGIC_UTIL, 3), sram_kb=sram_kb, sram_macros=macros,
                sram_mm2=round(sram_mm2, 3), total_mm2=round(logic_mm2 / GPU_LOGIC_UTIL + sram_mm2, 3),
                macs_per_clk=c * (lanes + 32 * e["blockdot_lanes"]))


def stream_overlap(ops, r_hbm, r_sm, staging_B, chunk_B=262144):
    """Fluid simulation of one token: a prefetching bulk-copy stream (rate r_hbm B/cycle) filling SMEM staging
    of staging_B bytes, consumed by the SMs (rate r_sm) op by op; each op's first byte waits for the previous
    op's dependent latency.  ops: [(bytes, latency_after_cycles)].  Returns (cycles, peak staging bytes)."""
    deliver, consume = [], []
    t_free = 0.0            # consumer ready time
    last_d = 0.0
    peak = 0.0
    slots = max(1, int(staging_B // chunk_B))
    for by, lat in ops:
        n = max(0, math.ceil(by / chunk_B))
        start = t_free
        for i in range(n):
            c = min(chunk_B, by - i * chunk_B)
            j = len(consume)
            d = last_d + c / r_hbm
            if j >= slots:
                d = max(d, consume[j - slots])
            last_d = d
            deliver.append(d)
            t = max((consume[-1] if consume and i else start) + c / r_sm, d + 1)
            consume.append(t)
        end = consume[-1] if n else start
        t_free = end + lat
        # occupancy: chunks delivered but not consumed at the op's end
        k = len(consume)
        occ = sum(1 for x in deliver[max(0, k - slots):] if x <= end) * chunk_B if k else 0
        peak = max(peak, occ)
    return t_free, peak


def qwen_hbm_ops(e: dict, boundary_cycles: float, drain_cycles: float, cols: int = 1, ctx: int = 8192):
    """The Qwen3-8B token on one TP-2 die as (bytes, dependent latency after) in program order.  Stream-unit
    latencies are the reference graph's (qwen3_budget dependency_chain 8192/spec_widths_reference_graph);
    every MMA op ends with its drain and a global boundary (barrier + x broadcast tail)."""
    import arch_budget_qwen3 as Q
    rec = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    st = {s["stage"] + (f"#{i}" if s["stage"] == "residual+sumsq" else ""): s["exposed_latency"] + s["throughput"]
          for i, s in enumerate(rec["dependency_chain"][f"{ctx}/spec_widths_reference_graph"]["stages"])}
    exch = Q.tp_exchanges(Q.clock_hz())["per_exchange_cycles"]
    H, KV, HD, NH, FF = 4096, 8, 128, 32, 12288
    kv_bytes = 2 * (KV // 2) * HD * ctx            # FP8 K and V of one layer, this die's 4 KV heads
    sc = 2                                          # BF16 row scale per weight row
    b = boundary_cycles + drain_cycles
    su = lambda *names: sum(v for k, v in st.items() if k.split("#")[0] in names)   # noqa: E731
    res = [v for k, v in st.items() if k.startswith("residual+sumsq")]
    ops = []
    for _ in range(36):
        ops.append((0, su("attn_norm.rsqrt", "attn_norm.scale")))
        ops.append(((NH + 2 * KV) // 2 * HD * (H + sc), b + su("qk_norm.sumsq", "qk_norm.rsqrt", "qk_norm.scale", "rope")))
        # heads are SM-local: scores -> softmax -> pv inside the SM pair of a head; one boundary after pv
        ops.append((kv_bytes // 2, drain_cycles + su("softmax.max", "softmax.exp_sum", "softmax.recip", "softmax.scale")))
        ops.append((kv_bytes // 2, b))
        ops.append((H * (H // 2 + sc), b + exch + res[0] + su("ffn_norm.rsqrt", "ffn_norm.scale")))
        ops.append((2 * (FF // 2) * (H + sc), b + su("silu_mul")))
        ops.append((H * (FF // 2 + sc), b + exch + res[1]))
    ops.append((151936 // 2 * (H + sc), b))        # lm_head slice (row-split vocabulary) + argmax
    return ops


def hbm_floorplan_record(model: str):
    p = ROOT / f"results/floorplan/hbm_gpu/{model}_hbm_die.json"
    return json.loads(p.read_text()) if p.exists() else None


WIRE_REACH_SS_UM = 504.0   # measured (W15): routed register-to-register reach per stage at 0.833 ns, SS corner


def barrier_network(model: str, clock: float, n_sm: int):
    """Barrier latency derived from the floorplan: SM -> quadrant node -> root (arrival AND-tree) and back
    (release), every wire segment registered at the loaded channel constant, one register per tree node.
    Uses the placed floorplan record when present; otherwise the analytical central-island geometry."""
    fp = hbm_floorplan_record(model)
    if fp:
        g = fp["barrier_network"]
        src = f"results/floorplan/hbm_gpu/{model}_hbm_die.json"
        leaf_um, trunk_um, levels = g["max_leaf_um"], g["max_trunk_um"], g["levels"]
    else:
        src = "analytical: 8 x 4 SM island centred on the die, node per quadrant, root at the centre"
        sm_mm2 = 3.0
        side = math.sqrt(sm_mm2) * 1e3
        leaf_um = 2 * side + 1.5 * side                          # farthest SM of a 4 x 2 quadrant to its node
        trunk_um = 2 * side + 1 * side                           # quadrant node to root
        levels = 2
    w = lambda um: max(1, math.ceil(um / WIRE_REACH_SS_UM))  # noqa: E731  (1.2 GHz at SS, W15 reach)
    arrive = w(leaf_um) + w(trunk_um) + levels + 1               # + the SM's local all-subpartitions-done flop
    release = w(leaf_um) + w(trunk_um) + levels
    return dict(arrive_cycles=arrive, release_cycles=release, round_trip_cycles=arrive + release,
                max_leaf_um=round(leaf_um, 1), max_trunk_um=round(trunk_um, 1), levels=levels, source=src)


def gpu_measured():
    """RTL measurements that replace formula terms, read from the committed records when present:
    the SM drain (last weight line -> last row result; max over the exactness campaign's cases of the
    element's format) and the barrier round trip on the floorplan's wire stages."""
    out = dict(qwen_drain_cycles=None, v41_drain_cycles=None, qwen_barrier_cycles=None, v41_barrier_cycles=None,
               sources=[])
    for rec, key, pred in (("results/rtl/gpu_sm_exact.json", "qwen_drain_cycles", lambda c: c["fmt"] == "qwen_int8"),
                           ("results/rtl/gpu_sm_exact.json", "v41_drain_cycles", lambda c: c["fmt"] == "v41_bf16"),
                           ("results/rtl/gpu_sm_blockdot_exact.json", "v41_drain_cycles", lambda c: True)):
        p = ROOT / rec
        if p.exists():
            r = json.loads(p.read_text())
            if r.get("status") == "pass":
                d = [c["rtl"].get("drain_last_line_to_last_result") for c in r["cases"] if pred(c)]
                d = [x for x in d if x is not None]
                if d:
                    out[key] = max(d + [out[key] or 0])
                    out["sources"].append(rec)
    p = ROOT / "results/rtl/gpu_supply_barrier.json"
    if p.exists():
        r = json.loads(p.read_text())
        if r.get("status") == "pass":
            for b in r["barrier"]:
                out[f"{b['model']}_barrier_cycles"] = b["max"]
            out["sources"].append("results/rtl/gpu_supply_barrier.json")
    return out


def mma_drain_cycles(e: dict):
    """Last weight into the MMA -> row result written to SMEM, from the element's pipeline at 1.2 GHz SS (W13b
    2026-09-30: FP32 add and mul 5 -> 7, W11's keep-prefix LAT 7; block-dot term 12 = W10 bterm2 11 + a lane input
    register): decode 1, multiply 7, circulating add 7 (or the block-dot 12), then log2(lanes) tree levels and the stack
    levels at 7, row scale 7, output register 2.  Replaced by the RTL measurement when recorded (gpu_measured: Qwen
    89, V4.1 95 on main)."""
    lanes = max(e["int8_lanes"] + e["bf16_lanes"], e["blockdot_lanes"])
    front = 12 if e["blockdot_lanes"] and not e["int8_lanes"] else 15      # block-dot term, or lane decode+mul+add
    return front + 7 * math.ceil(math.log2(lanes)) + 7 * e["stack_levels"] + 7 + 2


def gpu_payload_transport_model(payloads=24, tag_depth=16):
    """W19 opt-in V4.1 transport candidate, sized before RTL; no headline adoption.

    Load-time swizzle: issue-order 128-B weights + eight UE8M0 bytes,
    tightly concatenated, padded only at the descriptor's final 128-B line.
    The existing fetch ring supplies four 32-B sectors per ordered line.
    A finite 16-sector (512-B) window joins those bytes to an SM request-tag FIFO.
    """
    if payloads <= 0 or tag_depth < 2 or tag_depth & (tag_depth - 1):
        raise ValueError("positive payload count and power-of-two tag depth required")
    physical_lines = math.ceil(payloads * 136 / 128)
    # ASSUMED mux area: 0.2 um2 per 2:1 bit mux. Five sector reads from
    # a 16-sector window, four 8-B phases, and the bounded tag FIFO.
    mux_bits = 5 * 256 * 15 + 1088 * 2 + 1088 * (tag_depth - 1)
    storage_bits = 4096 + tag_depth * 10 + 5 * 24 + 128
    logic_um2 = storage_bits * DFF_UM2 + mux_bits * 0.2 + 512
    footprint_mm2 = logic_um2 / GPU_LOGIC_UTIL / 1e6
    tracks = 1024 + 1088 + 4 * (24 + 16) + 2 * (32 + 10 + 24) + 16
    channel_tracks = int(64 * 4 / 0.08)
    # Added supply service versus an ideal 128-B payload. Existing MMA
    # drain remains unchanged; this is not a composed token measurement.
    service_cycles = physical_lines + 1
    layer_extra = 12 * (math.ceil(24 * 136 / 128) + 1 - 24) + 6 * (math.ceil(32 * 136 / 128) + 1 - 32)
    return dict(schema="opentallas.uarch.gpu_payload_transport.v1", enabled_default=False,
        scope="V4.1 HBM candidate only; Qwen/ROM ports unchanged", payloads=payloads,
        layout="136-B records in golden SM issue order; final line padding only",
        compute=dict(macs_per_cycle=0, intensity_macs_per_byte=0, arithmetic="none"),
        ports_Bpc=dict(fetch_read=128, reservoir_write=128, reservoir_read=136, sm_response_write=136),
        boundaries_bits_pc=dict(fetch=1024, sm=1088, request_tag=42),
        replicas_per_die=32, tag_depth=tag_depth, reservoir_bytes=512, sector_window=16,
        assembly="five 32-B sectors per 136-B record; four 8-B phases; per-sector duplicate/epoch validation",
        mux_bit_equivalents=mux_bits, storage_bits=storage_bits,
        fanout="SM-local ready/valid; no new die-wide broadcast", demux="one local SM response",
        footprint_mm2_per_sm=round(footprint_mm2, 6), footprint_mm2_die=round(32 * footprint_mm2, 4),
        area_basis="ASSUMED 0.2 um2 bit mux + DFFHQNx1 0.2916 um2 + 512 um2 control, 50% utilisation",
        slot_fit="reserve this footprint inside existing W13 SM slot; measured contextual fit pending",
        routing=dict(tracks=tracks, channel_capacity_tracks=channel_tracks, fits=tracks <= channel_tracks,
            basis="ASSUMED 64 um local channel, four existing signal layers, 80 nm pitch; no hub layer change"),
        physical_lines=physical_lines, transferred_bytes=physical_lines * 128,
        padded_fixture_bytes=payloads * 256, service_cycles_no_stalls=service_cycles,
        ideal_128B_payload_cycles=payloads, extra_service_cycles=service_cycles - payloads,
        steady_payloads_pc=16/17, first_payload_after_two_line_landings_cycles=1,
        composed_path=dict(layers=40, expert_ops_per_layer=18, added_supply_cycles_upper_bound=40 * layer_extra,
            added_supply_us_upper_bound=round(40 * layer_extra / 1.2e9 * 1e6, 3),
            basis="serial sum for all routed w1/w3/w2 busiest-SM slices; overlap may hide service; excludes HBM wait"),
        adoption="OFF: exact, in-context SS/FF and measured token gain gates required; no token-rate restatement")


def hbm_gpu_design(model: str):
    """Size the GPU-organised HBM die for `model` ('qwen' | 'v41')."""
    import arch_budget_qwen3 as Q
    e = dict(SM_ELEM[model])
    if model == "qwen":
        clock = Q.clock_hz()
        r_hbm = 3.6e12 / clock                   # 4 stacks x 0.9 TB/s sustained per die
    else:
        clock = 1.0339e9
        r_hbm = 3.6e12 / clock
    in_flight_B = 3.6e12 * HBM_LOADED_LAT_NS * 1e-9
    meas = gpu_measured()
    drain = meas[f"{model}_drain_cycles"] or mma_drain_cycles(e)
    out = dict(model=model, clock_hz=clock, hbm_Bpc=round(r_hbm, 1), element=e, drain_cycles=drain,
               drain_basis="measured (RTL)" if meas[f"{model}_drain_cycles"] else "formula",
               drain_formula_cycles=mma_drain_cycles(e), measured=meas)
    # ---- SM count: smallest multiple of the stack count within 0.5% of an unbounded array (Qwen token) ----
    rows = []
    n_choice = None
    if model == "qwen":
        bn = barrier_network(model, clock, 32)
        x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
        boundary = (meas["qwen_barrier_cycles"] or bn["round_trip_cycles"]) + x_tail
        ops = qwen_hbm_ops(e, boundary, drain)
        t_inf, _ = stream_overlap(ops, r_hbm, 1e12, 1e15)
        for n in range(8, 65, 4):
            t, _ = stream_overlap(ops, r_hbm, n * e["ingest_Bpc"], 1e15)
            rows.append(dict(n_sm=n, cycles=round(t), tokens_s_pkg=round(clock / t, 1)))
            if n_choice is None and t <= 1.005 * t_inf:
                n_choice = n
        out["sm_count_sweep"] = rows
        out["sm_count_min"] = n_choice
    # symmetric choice: 8 SMs per HBM stack quadrant (4 x 2 per quadrant), power of two for the barrier tree
    n_sm = 32
    out["sm_count"] = n_sm
    out["sm_count_basis"] = ("8 per stack quadrant; >= the 0.5%-of-unbounded minimum" if model == "qwen" else
                             "same element count as Qwen: HBM ingest 3,482 B/clk / 128 B/clk = 27.2 -> 32")
    # ---- bulk copy: Little's law in flight, per SM, in sectors ----
    out["bulk_copy"] = dict(in_flight_B_die=in_flight_B, in_flight_B_sm=in_flight_B / n_sm,
                            outstanding_sectors_sm=math.ceil(in_flight_B / n_sm / SECTOR_B),
                            descriptor_bytes=4096,
                            outstanding_descriptors_sm=math.ceil(in_flight_B / n_sm / 4096),
                            basis=f"3.6 TB/s x {HBM_LOADED_LAT_NS:.0f} ns (ASSUMED loaded latency)")
    sp = ROOT / "results/rtl/gpu_supply_barrier.json"
    if sp.exists():
        sr = json.loads(sp.read_text())
        if sr.get("status") == "pass":
            m = [dict(outstanding_lines=x["max_out"], B_per_cycle=x["B_per_cycle"],
                      share_B_per_cycle=x["share_B_per_cycle"]) for x in sr["supply"]]
            full = [x for x in m if x["B_per_cycle"] >= 0.995 * x["share_B_per_cycle"]]
            out["bulk_copy"].update(
                measured=m, measured_source="results/rtl/gpu_supply_barrier.json (ot_gpu_bulk_copy, 128 B lines, "
                                             "500 ns +- 50 ns loaded latency)",
                outstanding_lines_sm=min(x["outstanding_lines"] for x in full) if full else None,
                note="Little's law gives 440 lines of 128 B; with latency jitter the full share needs 512")
    bn = barrier_network(model, clock, n_sm)
    x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
    rt_meas = meas[f"{model}_barrier_cycles"]
    out["barrier"] = dict(bn, x_broadcast_tail_cycles=x_tail,
                          measured_round_trip_cycles=rt_meas,
                          boundary_cycles=(rt_meas or bn["round_trip_cycles"]) + x_tail,
                          basis=("derived from the floorplan, measured in RTL (tb_gpu_barrier)" if rt_meas
                                 else "derived from the floorplan"))
    boundary = out["barrier"]["boundary_cycles"]
    if model == "qwen":
        ops = qwen_hbm_ops(e, boundary, drain)
        t_inf, _ = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], 1e15)
        st = []
        s_choice = None
        for kb in (16, 32, 64, 128, 256, 512, 1024):
            S = kb * 1024 * n_sm
            t, pk = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], S)
            st.append(dict(staging_kb_per_sm=kb, cycles=round(t), tokens_s=round(clock / t, 1)))
            if s_choice is None and t <= 1.005 * t_inf:
                s_choice = kb
        out["staging_sweep"] = st
        staging_kb = max(s_choice or 1024, math.ceil(in_flight_B / n_sm / 1024 / 32) * 32)
        t_hbm = sum(b for b, _ in ops) / r_hbm
        t_chain = sum(b for b, _ in ops) / (n_sm * e["ingest_Bpc"]) + sum(lat for _, lat in ops)
        t_tok, _ = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], staging_kb * 1024 * n_sm)
        boundaries = 5 * 36 + 1          # qkv, attention (pv), o, gate_up, down per layer + lm_head (qwen_hbm_ops)
        out["token"] = dict(
            cycles=round(t_tok), tokens_s=round(clock / t_tok, 1), hbm_cycles=round(t_hbm),
            chain_cycles_if_serial=round(t_chain), boundaries=boundaries,
            exposed_over_hbm_cycles=round(t_tok - t_hbm),
            additive_model_tokens_s=round(clock / (t_hbm + boundaries * boundary + Q.tp_exchanges(clock)["cycles"]), 1),
            note="the stream prefetches through every boundary; only what the SMEM staging cannot absorb and the "
                 "last op's tail are exposed")
    else:
        # no op-level stream model for V4.1 yet: the measured in-flight need (512 lines = 64 KB) plus the same
        # again to run through a boundary, as the Qwen sweep requires
        staging_kb = 2 * 64
    out["staging_kb_per_sm"] = staging_kb
    out["sm_area"] = sm_area(e, staging_kb)
    # ---- L2 slices and NoC ----
    out["l2"] = dict(slices=HBM_DIE["stacks"], mb_per_slice=2, macros=HBM_DIE["stacks"] * 64,
                     mm2=round(HBM_DIE["stacks"] * 64 * GPU_UNIT_UM2["sram32k"] * GPU_MACRO_PACK / 1e6, 2),
                     role="x/result gather and broadcast, TP-exchange staging, KV-write coalescing; weights "
                          "bypass it (bulk copy lands in SM SMEM, no reuse at decode)")
    out["noc"] = dict(weight_port_bits_per_sm=e["ingest_Bpc"] * 8 + 64,
                      weight_wires_per_quadrant=(n_sm // 4) * (e["ingest_Bpc"] * 8 + 64),
                      x_broadcast_bits=X_BCAST_BPC * 8, result_gather_bits_per_sm=256,
                      mapping="each SM's weight rows live in its own quadrant's stack: no weight byte crosses "
                              "the die")
    if model == "v41":
        pr = area_ledger(copy.deepcopy(PRESETS["proposal"]))
        units = dict(indexer=pr["indexer"], attention=pr["attention"], su=pr["su_lanes"], sfu=pr["sfu_lanes"],
                     hc_fp32_lanes=5120 * UNIT["fp32_mac_um2"] / 1e6,
                     sinkhorn_select_engram=(UNIT["sinkhorn_um2"] + UNIT["select_k512_um2"]
                                             + UNIT["engram_hash_um2"] + UNIT["tselect16_um2"]) / 1e6)
        out["dedicated_units_mm2"] = {k: round(v, 3) for k, v in units.items()}
        out["dedicated_units_footprint_mm2"] = round(sum(units.values()) / GPU_LOGIC_UTIL, 2)
        out["dedicated_units_source"] = "spec widths as in results/uarch/v41_rom.json proposal hub (W11 builds them)"
    sm_fp = out["sm_area"]["total_mm2"]
    out["die_fit"] = dict(sm_array_mm2=round(n_sm * sm_fp, 2), l2_mm2=out["l2"]["mm2"],
                          dedicated_mm2=out.get("dedicated_units_footprint_mm2", 0.0),
                          core_avail_mm2=round((HBM_DIE["core"][2] - HBM_DIE["core"][0])
                                               * (HBM_DIE["core"][3] - HBM_DIE["core"][1]) / 1e6, 2))
    f = out["die_fit"]
    f["used_mm2"] = round(f["sm_array_mm2"] + f["l2_mm2"] + f["dedicated_mm2"], 2)
    f["fits"] = f["used_mm2"] <= f["core_avail_mm2"]
    return out


H_X_TAIL_B = 16 * 128 * 2     # the last SM's last row block (8 rows x 16 cols... bounded by one 16-col x 128-row
                              # BF16 block) that every SM must receive before the next op's first MMA
X_BCAST_BPC = 256             # x broadcast network width (2,048 wires), root -> every SM, pipelined with release


# ---------------------------------------------------------------------------------------------------------
# Speculation (MTP / DFlash): verify p positions per step with m MAC lanes per weight word (docs/MICROARCH_MODEL.md)
# ---------------------------------------------------------------------------------------------------------
# m counts the positions that multiply one ROM weight word IN THE SAME CYCLE.  m = 1 runs the p positions through
# the existing lanes one after another: the weight words are re-read (cheap) and only issue time multiplies, while
# pipeline fill, wire stages and dependency latency are paid once per verify pass.  m >= 2 replicates every
# element's lanes beside its macro (x13,798 on a V4.1 die), plus wider x broadcast and return.
V41_TAU = 3.649        # DSpark gamma 5 (6 verified positions), results/speculative/v41_flash_dspark_onpolicy_greedy.json
V41_POSITIONS = 6
V41_DRAFT_FRACTION = 3 / 40   # ASSUMED: the 3 built-in draft blocks (mtp.0-2) ~ 3 of 40 layers of an AR token
# SUCCESSOR (2026-10-04): the V4.1 ROM draft TIME is the MEASURED DSpark step (52 bit-exact minimum-component slices,
# transferred to S81 full shape; context-independent, it runs on the head dies), not a fraction of AR.  The HBM rows
# and the energy terms keep V41_DRAFT_FRACTION.  --v41-rom-draft assumed reproduces records made before this flag.
V41_ROM_DRAFT_RECORD = ROOT / "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"
V41_ROM_DRAFT_VARIANTS = {"as_built": "as_built_chain", "l1": "fused_head"}   # l1: fused bias + argmax head (L1)
V41_ROM_DRAFT = "as_built"     # --v41-rom-draft {as_built, l1, assumed}


def v41_rom_draft_s(T1):
    """Draft time (s) of the V4.1 ROM MTP step: measured (V41_ROM_DRAFT_RECORD) or the legacy assumed fraction."""
    if V41_ROM_DRAFT == "assumed":
        return V41_DRAFT_FRACTION * T1
    ctx = json.loads(V41_ROM_DRAFT_RECORD.read_text())["full_shape"]["ctx"]
    return next(iter(ctx.values()))[V41_ROM_DRAFT_VARIANTS[V41_ROM_DRAFT]]["draft_us"] * 1e-6


def v41_verify_T(d, p, lm, ctx=1048576):
    """Verify-pass time of the V4.1 ROM design for p positions with lane multiplier lm."""
    r = evaluate(copy.deepcopy(d), ctx)
    g = r.pop("_g")
    E = A._env()
    clock, c = E["clock"], E["c"]
    cyc = 1.0 / clock
    rep = math.ceil(p / lm)
    for name, nd in g.nodes.items():
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            nd["issue"] = max(u["t_read"] * rep, u["t_x"] * p, u["t_ret"] * p, u["t_mac"] * rep) * cyc
        elif k in ("vector", "reduce", "select", "collective"):
            nd["issue"] *= p
        elif k == "kvscan":
            if name.endswith("idx.score"):
                n = int(nd["desc"].split()[2])
                by = n * A.IDX_KEY_B
                macs = n * c["index_heads"] * c["index_head_dim"]
                rd = d["idx_reader_Bpc"] or (3.6e12 / clock)
                nd["issue"] = max(by / rd, p * macs / (d["idx_macs"] * lm)) * cyc   # keys read once per pass
            else:
                nd["issue"] *= rep
        elif k == "matvec" and name.endswith("hc.fn"):
            nd["issue"] *= rep
    fin = g.solve(True)
    return fin[[n for n in g.nodes if n.endswith("token.return")][0]], r["T_us"] * 1e-6


def speculation_rows():
    rows = []
    d = copy.deepcopy(PRESETS["proposal"])
    for lm in (1, 2, V41_POSITIONS):
        Tp, T1 = v41_verify_T(d, V41_POSITIONS, lm)
        Td = v41_rom_draft_s(T1)
        rate = V41_TAU / (Tp + Td)
        extra_mm2 = (lm - 1) * (area_ledger(d)["blockdot_lanes"] + area_ledger(d)["bf16_lanes"])
        rows.append(dict(design=f"v41_rom_mtp_m{lm}", positions=V41_POSITIONS, lane_mult=lm, tau=V41_TAU,
                         ar_tokens_s=round(1 / T1, 1), verify_over_ar=round(Tp / T1, 3),
                         tokens_s=round(rate, 1), speedup=round(rate * T1, 3),
                         extra_lane_area_mm2=round(extra_mm2, 1),
                         fits=bool(area_ledger(d)["rom_field_strip_used_mm2"] + extra_mm2
                                   <= FLOORPLAN["rom_field_strip_mm2"])))
    # Qwen ROM: the RTL-calibrated serial draft/verify/commit step (tools/dflash_step_timing.py) prices m = 1 and 5
    q = json.loads((ROOT / "results/speculative/dflash_step_timing.json").read_text())["rom"]
    for m in ("m1", "m5"):
        blk = q[f"8192/fp8/{m}"]["blocks"] if "blocks" in q[f"8192/fp8/{m}"] else None
        src = q[f"8192/fp8/{m}"]
        best = None
        for key in src:
            if isinstance(src[key], list):
                for b in src[key]:
                    if best is None or b["tokens_s"] > best["tokens_s"]:
                        best = b
        rows.append(dict(design=f"qwen_rom_dflash_{m}", lane_mult=int(m[1:]), best_block=best["block"],
                         tokens_s=best["tokens_s"], speedup=best["speedup"], ar_tokens_s=src["plain_tokens_s"],
                         extra_lane_area_mm2=0.0 if m == "m1" else 178.66,
                         drafter_rom_mm2=29.0, basis="results/speculative/dflash_step_timing.json (m=1 never beats "
                         "AR: the Qwen token is lane-bound; weight issue is ~36% of the step)"))
    for r in rows:
        print(r)
    return rows


def hbm_speculation_rows():
    """Speculation on the GPU-organised HBM dies (user decision 2026-09-29).  The verify positions ride the
    SM's MMA columns (16 built), so one weight fetch serves the whole block with each column in its own
    golden order.
    Qwen DFlash (z-lab/Qwen3-8B-DFlash-b16): step = draft + verify + commit on the prefetching stream.  Draft
    bytes per die: the drafter's 1.05 B parameters (INT8, ASSUMED the target's format) and the shared lm_head
    over the draft slots (re-read, 311 MB); verify bytes are the AR token's (weights + one KV read); the
    in-block causal attention and the accept compare add no bytes.  tau is measured per block
    (results/speculative/dflash_block_acceptance.json, primary, cycle-weighted).
    V4.1 DSpark MTP (gamma 5, 6 positions, tau 3.649): verify = the K-chain-aware SM chain with 6 positions
    (matvecs once on the columns, the dedicated units' issue repeated); draft = V41_DRAFT_FRACTION of an AR
    token (ASSUMED, as the ROM rows)."""
    import arch_budget_qwen3 as Q
    rows = []
    dq = hbm_gpu_design("qwen")
    clock = dq["clock_hz"]
    budget = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    acc = json.loads((ROOT / "results/speculative/dflash_block_acceptance.json").read_text())["blocks"]
    ops = qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])
    ar_bytes = sum(b for b, _ in ops)
    t_ar, _ = stream_overlap(ops, dq["hbm_Bpc"], dq["sm_count"] * 128, dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    draft_B = budget["dflash"]["drafter_parameters"] / 2 + 151936 // 2 * (4096 + 2)
    rows.append(dict(design="qwen_hbm_ar", block=1, tau=1.0, step_cycles=round(t_ar), tokens_s=round(clock / t_ar, 1)))
    best = None
    for b, v in sorted(acc.items(), key=lambda kv: int(kv[0])):
        b = int(b)
        if b > dq["element"]["cols"]:
            continue
        tau = v["pooled"]["primary"]["tau_direct_cycle_weighted"]
        # the draft precedes the verify (it needs the previous verify's hidden states): its stream is one more
        # op sequence; the weight streams of both prefetch, so the step is their bytes at the stream rate plus
        # the same exposed boundaries
        t_step = t_ar * (ar_bytes + draft_B) / ar_bytes + 2 * 12 * dq["barrier"]["boundary_cycles"]
        r = dict(design=f"qwen_hbm_dflash_b{b}", block=b, tau=tau, step_cycles=round(t_step),
                 tokens_s=round(tau * clock / t_step, 1), speedup=round(tau * t_ar / t_step, 3),
                 draft_bytes_per_die=draft_B, verify_bytes_per_die=ar_bytes)
        rows.append(r)
        if best is None or r["tokens_s"] > best["tokens_s"]:
            best = r
    rows.append(dict(best, design="qwen_hbm_dflash_best"))
    T_ar, parts_ar, _ = v41_hbm_chain(True, 1)
    T_v, parts_v, _ = v41_hbm_chain(True, V41_POSITIONS)
    Td = V41_DRAFT_FRACTION * T_ar
    rows.append(dict(design="v41_hbm_ar", tokens_s=round(1e6 / T_ar, 1), T_us=round(T_ar, 1)))
    rows.append(dict(design="v41_hbm_mtp", positions=V41_POSITIONS, tau=V41_TAU, verify_us=round(T_v, 1),
                     draft_us=round(Td, 1), tokens_s=round(V41_TAU * 1e6 / (T_v + Td), 1),
                     speedup=round(V41_TAU * T_ar / (T_v + Td), 3),
                     verify_breakdown_us={k: round(x, 1) for k, x in parts_v.items()}))
    return rows


V41_HBM_DSPARK_REC = ROOT / "results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json"


def v41_hbm_dspark_rows(ctx=1048576):
    """OPT-IN (--v41-hbm-dspark; never on a default path): the V4.1 HBM comparator's DSpark rows with the drafter
    priced from its real structure (3 stages x 5 slots + LM head + 5 serial Markov argmaxes) and the verify pass's
    MEASURED expert union, on W19's composer (tools/v41_hbm_speculation_methods.py).  V4.1's built-in 'MTP' is
    DSpark: these rows re-price the existing headline's terms; HBM_W19 and V41_DRAFT_FRACTION are unchanged."""
    rec = json.loads(V41_HBM_DSPARK_REC.read_text())
    c = rec["contexts"][str(ctx)]
    rows = [dict(design="v41_hbm_ar_w19", ctx=ctx, tokens_s=c["ar_tokens_s"], T_us=c["ar_us"])]
    for k, v in c["headline_comparison_tau_3649_gamma5"].items():
        rows.append(dict(design=f"v41_hbm_dspark_g5_tau3649_{k}", ctx=ctx, tokens_s=v["tokens_s"], step_us=v["step_us"]))
    for ts, r in c["rates"].items():
        for x in r["by_gamma"]:
            rows.append(dict(design=f"v41_hbm_dspark_g{x['gamma']}", tau_set=ts, ctx=ctx, **x))
    return rows


# ---------------------------------------------------------------------------------------------------------
# Fabric sensitivity and GPU tiers (user request 2026-09-29)
# ---------------------------------------------------------------------------------------------------------
# Every multi-die design here assumes deterministic hardware collectives at link latency (a 668 ns switched
# hop for V4.1, a ~17.5 ns UCIe exchange for the Qwen TP-2 pair).  The sweep re-prices each design as that latency
# grows toward NCCL-class software collectives; the tiers put the designs beside what GPUs measurably do.
GPU_CAL = json.loads((ROOT / "results/arch/qwen_gpu_calibration.json").read_text())
GPU_FIT = GPU_CAL["fit"]              # t = fixed + seconds_per_weight_byte x bytes (H200 NIM fit, BF16/FP8 pair)
H200_BW = 4.8e12
B200_BW = 8.0e12                       # per GPU (NVIDIA B200 datasheet)
# GPU-baseline small all-reduce (owner 2026-10-04: GPU rows use MEASURED GPU software costs).  Default: the measured
# GPU-correct (sys-scope release/acquire) one-shot NVLS all-reduce on H100 HGX, 8.904-9.144 us (mid 9.024 us), i.e.
# what a graph-captured custom kernel pays.  NCCL all_reduce_perf WITHOUT a CUDA graph measured 32-36 us (launch-bound;
# NCCL with graphs hung, not measured) and is the stock-software sensitivity.  Was 8 us ASSUMED.  NVLink4 / H100
# generation; the tier-2 rows are 8x B200 (NVLink5 not measured).  results/measured/h100_nvls_20261004.
NCCL_ALLREDUCE_S = (8.904e-6 + 9.144e-6) / 2
NCCL_ALLREDUCE_ASSUMED_SUPERSEDED_S = 8e-6
NCCL_ALLREDUCE_MEASURED_H100_S = dict(oneshot_nvls_sys_sync=(8.904e-6, 9.144e-6), nccl_no_graph=(32e-6, 36e-6))
DFLASH_PAPER = ("Z. Chen, Liang, Liu, 'DFlash: Block Diffusion for Flash Speculative Decoding', arXiv 2602.06036, "
                "Table 3 (SGLang, FA4 backend, single B200, thinking disabled, temperature 0)")
# AUTHORITATIVE Qwen3-8B GPU baseline (owner 2026-10-04): MEASURED on the rented 8x H100 SXM5 HGX node, vLLM 0.11.0
# (torch 2.8 cu128, CUDA graphs, V1 engine), batch-1 decode, 128 in / 512 out, 2 warmup + 5 iterations; tok/s = 512 /
# mean end-to-end latency (prefill < 1%).  results/measured/h100_nvls_20261004/README.md.  The B200 rows stay as the
# labelled model / published anchors.
QWEN_GPU_H100_MEASURED = dict(
    bf16={1: 138.1, 2: 195.5, 4: 259.7, 8: 293.4}, fp8={1: 194.1, 2: 242.1, 4: 275.4, 8: 305.7},
    latency_s=dict(bf16={1: 3.708, 2: 2.619, 4: 1.972, 8: 1.745}, fp8={1: 2.637, 2: 2.115, 4: 1.859, 8: 1.675}),
    workload="batch 1, 128 in / 512 out (short context); 8K-context and EAGLE-3 runs pending",
    src="results/measured/h100_nvls_20261004/README.md")
TIER1 = [
    *[dict(tier=1, design=f"Qwen3-8B, {tp}x H100 SXM (TP{tp}), vLLM 0.11 {fmt.upper()}, AR, batch 1 (MEASURED)",
           tokens_s=QWEN_GPU_H100_MEASURED[fmt][tp], authoritative_qwen_gpu_baseline=(tp == 1 and fmt == "fp8"),
           source=QWEN_GPU_H100_MEASURED["src"])
      for fmt in ("fp8", "bf16") for tp in (1, 2, 4, 8)],
    dict(tier=1, design="Qwen3-8B-class, H200, NIM FP8, AR", tokens_s=GPU_CAL["nim_h200"]["fp8_tok_s"],
         source=GPU_CAL["nim_h200"]["source"]),
    dict(tier=1, design="Qwen3-8B, RTX PRO 6000 (this lab), FP8 AR",
         tokens_s=GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]["ar_tok_s"],
         source="results/gpu/qwen3_rtx_pro_6000_decode.json"),
    dict(tier=1, design="Qwen3-8B, RTX PRO 6000 (this lab), FP8 DFlash",
         tokens_s=GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]["dflash_tok_s"],
         source="results/gpu/qwen3_rtx_pro_6000_decode.json"),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, BF16, AR (DFlash paper Table 3, Math500)", tokens_s=230.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, Math500 (tau 8.01, 5.1x)", tokens_s=1175.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, HumanEval (tau 6.50, 4.2x)", tokens_s=955.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="DeepSeek-R1 (V4.1-class anchor), 8x B200, TensorRT-LLM min-latency, 3 MTP layers "
                        "(relaxed acceptance)", tokens_s=368.0,
         source="https://nvidia.github.io/TensorRT-LLM/blogs/tech_blog/"
                "blog1_Pushing_Latency_Boundaries_Optimizing_DeepSeek-R1_Performance_on_NVIDIA_B200_GPUs.html"),
]


def v41_gpu_index_scan(ctx, *, candidate_gather=True, c=None):
    """Per-token index reads using the SAME source modes as the ROM budget.

    Only index-owner layers scan; other layers reuse their selections. Keys
    reside at the preceding KV owner. Candidate gather on the last four scans
    is the analytical budget's explicit software assumption, NOT an assertion
    that the current full-score golden/native program performs that gather.
    candidate_gather=False retains their literal full-score read sensitivity.
    """
    if type(ctx) is not int or ctx <= 0:
        raise ValueError("positive integer decode context required")
    c = c if c is not None else A._env()["c"]
    golden = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json").read_text())
    scans = [L for L in range(c["num_layers"]) if c["modes"][L].get("scans_index")]
    if (scans != golden["index_source_layers"] or scans != c["index_source_layer_ids"]
            or c["kv_source_layer_ids"] != golden["kv_source_layers"]
            or c["candidate_source_layer_id"] != golden["candidate_source_layer"]
            or c["index_head_dim"] != golden["index_head_dim"]
            or A.IDX_KEY_B != golden["index_head_dim"] // 2 + golden["index_head_dim"] // 32
            or c["compress_ratios"][:c["num_layers"]] != golden["compress_ratios"][:golden["n_layers"]]):
        raise ValueError("analytical index modes differ from golden source/ratio/KV ownership")
    rows = []
    for L in scans:
        ratio = c["compress_ratios"][L]
        owner = max(s for s in c["kv_source_layer_ids"] if s <= L)
        if ratio <= 0 or ratio != c["compress_ratios"][owner]:
            raise ValueError("invalid shared index-key compression identity")
        full = ctx // ratio
        cap = c["modes"][L].get("index_scan_entries_cap") or 0
        if cap and (L <= c["candidate_source_layer_id"] or
                    cap != golden["candidate_topk_blocks"] * golden["candidate_block_size"]):
            raise ValueError("candidate cap lacks preceding source selection")
        count = min(full, cap) if cap and candidate_gather else full
        rows.append(dict(layer=L, KV_source_layer=owner, compression_ratio=ratio,
                         full_source_entries=full, candidate_cap=cap,
                         entries=count, bytes=count * A.IDX_KEY_B))
    return dict(context=ctx, scanning_layers=scans, per_layer=rows,
                entries=sum(r["entries"] for r in rows), bytes=sum(r["bytes"] for r in rows),
                key_bytes=A.IDX_KEY_B, candidate_gather=candidate_gather,
                scope="tier-2 analytical read budget; candidate gather conditional; no native execution/clock claim")


def gpu_tier2():
    """GPU-calibrated projection, anchored on B200 measurements.
    Qwen3-8B: the per-token fixed cost keeps the H200 fit (1.464 ms: launches and syncs, 36 layers), and the per-byte
    cost is re-fitted so that BF16 weights reproduce the measured B200 SGLang AR rate (230 tok/s, DFlash paper
    Table 3); FP8 weights and 8K FP8 KV then project the FP8 rate.  Speculation multiplies by the measured GPU
    speedup at two acceptance regimes: this lab's reasoning mix (tau ~3.7, 2.58x on the RTX PRO 6000) and the
    paper's math/code (tau 6.5-8.0, 4.2-5.1x on B200).
    V4.1-Flash: 8x B200 (TP 8), the same per-layer fixed cost and per-byte cost, NCCL-class all-reduce (5 per layer)
    and its 1M index-key reads; MTP at the HBM machine's modelled 1.94x.  Check: DeepSeek-R1 on 8x B200 measures
    368 tok/s/user with 3 MTP layers (tier 1)."""
    fixed = GPU_FIT["fixed_seconds_qwen"]
    bf16_bytes = 2 * GPU_FIT["qwen_fp8_weight_bytes"]
    s_per_B = (1 / 230.0 - fixed) / bf16_bytes                   # B200 per-byte cost, fitted
    q_bytes = GPU_FIT["qwen_fp8_weight_bytes"] + GPU_FIT["qwen_fp8_kv_bytes_8k"]
    tq = fixed + s_per_B * q_bytes
    loc = GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]
    spec_lab = loc["dflash_tok_s"] / loc["ar_tok_s"]
    fixed_layer = fixed / 36
    index_scan = v41_gpu_index_scan(1048576)
    v_bytes = (13.03e9 + index_scan["bytes"]) / 8   # weights + source-owned index reads
    tv = 40 * fixed_layer + s_per_B * v_bytes + 40 * 5 * NCCL_ALLREDUCE_S
    return [dict(tier=2, design="Qwen3-8B on 1x B200, FP8 weights, 8K, calibrated", tokens_s=round(1 / tq, 1),
                 spec_tokens_s_reasoning_mix=round(spec_lab / tq, 1),
                 spec_tokens_s_math_code=[round(4.2 / tq, 1), round(5.1 / tq, 1)],
                 effective_bandwidth_TBps=round(1 / s_per_B / 1e12, 2),
                 terms_us=dict(fixed=round(fixed * 1e6), bytes=round(s_per_B * q_bytes * 1e6))),
            dict(tier=2, design="DeepSeek-V4.1-Flash on 8x B200, calibrated", tokens_s=round(1 / tv, 1),
                 spec_tokens_s=round(1.94 / tv, 1),
                 terms_us=dict(fixed=round(40 * fixed_layer * 1e6), bytes=round(s_per_B * v_bytes * 1e6),
                               collectives=round(40 * 5 * NCCL_ALLREDUCE_S * 1e6)),
                 index_scan=index_scan,
                 check="DeepSeek-R1 on 8x B200 measures 368 tok/s/user with MTP (tier 1)")]


def qwen_hbm_tau_sensitivity():
    """Tier 3 (idealised HBM) Qwen DFlash at the paper's acceptance: the SM verify cost is flat to 16 columns, so the
    step rate scales with tau (W13 model: block 16 at tau 3.656 -> 2,671 tok/s)."""
    base_tau, base = 3.656, 2671.0
    return [dict(tier=3, design=f"Qwen HBM (idealised) DFlash b16 at tau {t}", tokens_s=round(base * t / base_tau, 1),
                 tau=t) for t in (3.656, 6.50, 8.01)]


FABRIC_SWEEP_S = (0.15e-6, 0.668e-6, 1e-6, 2e-6, 5e-6, 10e-6)   # 0.15 us ~ the ROM array's own board/UCIe links
                                                                # (arch-priced collective depth 145-165 cycles);
                                                                # 0.668 us = the HBM comparator's NVL-class switch
QWEN_UCIE_SWEEP_S = (17.5e-9, 100e-9, 500e-9, 1e-6, 5e-6)


# W15 (results/rtl/w15_collectives.json): collectives MEASURED end to end in RTL on physical-link models --
# per-die clocks, UCIe-A and 112G light-FEC link layers, floorplan wire stages, deterministic release.  Each
# config's latency (issue -> last VM commit on the slowest die) is fitted as fixed + per-word x words-per-rank over
# a 1..320-word payload sweep; a DAG collective is priced at its own payload (words = payload / 64 B for an
# all-reduce, payload / span / 64 B per rank for an all-gather).
W15_RECORD = ROOT / "results/rtl/w15_collectives.json"
_W15 = {}


def w15_record():
    if "r" not in _W15:
        _W15["r"] = json.loads(W15_RECORD.read_text())
    return _W15["r"]


def w15_collective_s(cfg, op, payload, span):
    c = w15_record()["configs"]
    rec = c.get(cfg + "_sweep") or c[cfg]
    f = rec["fit"]["all_reduce" if op == "all_reduce" else "all_gather"]
    words = math.ceil(payload / 64) if op == "all_reduce" else math.ceil(payload / max(1, span) / 64)
    return (f["fixed_cycles"] + f["cycles_per_word"] * max(1, words)) / rec["clock_hz"]


W15_V41 = (("v41_r1d256", "as-built placement (hub collective, edge PHYs 22/29 wire stages), relay, depth 256"),
           ("v41_r0d256", "as-built placement, direct T1 (no relay), depth 256"),
           ("v41_r0d1024", "as-built placement, direct T1, depth 1024"),
           ("v41p17_r0d256", "W3 proposed placement (collective at the channel crossing, 17 stages), direct T1, "
                             "depth 256"),
           ("v41p17_r0d1024", "W3 proposed placement, direct T1, depth 1024"))
W15_QWEN = (("q16d16", "host binding: 16 lanes, depth 16"), ("q16d128", "16 lanes, depth 128"),
            ("q256d64", "256 lanes, depth 64 (ADOPTED)"),
            ("q256d16", "256 lanes, depth 16"), ("q256d128", "256 lanes, depth 128"),
            ("q1024", "1,024 lanes (UCIe rate), depth 16"))


def w15_rows():
    """Token rates with the W15-measured collectives in place of the assumed latencies."""
    rows = []
    if not W15_RECORD.exists():
        return rows
    cf = w15_record()["configs"]
    d = copy.deepcopy(PRESETS["proposal"])
    for cfg, what in W15_V41:
        if cfg not in cf:
            continue
        r = evaluate(dict(d, collective_w15=cfg), 1048576)
        r.pop("_g", None)
        rows.append(dict(design="v41_rom_ar", w15_config=cfg, what=what, tokens_s=round(r["tokens_s"], 1),
                         collective_latency_us=r["breakdown_us"].get("collective_latency"),
                         T_us=round(r["T_us"], 3)))
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    x = wire_cycles(27000.0, clock, WIRE_PS_PER_UM_LOADED) - 1
    ucie_wire = round(QWEN_WIRE["ucie_wire_per_token"] * x / QWEN_WIRE["x_stages_extra"])
    assumed = Q.tp_exchanges(clock)["exchange_cycles"] + ucie_wire     # 73 x 19.27 + the wire term
    for cfg, what in W15_QWEN:
        if cfg not in cf:
            continue
        meas = cf[cfg]["exchanges"]["token_exchange_cycles"]
        cyc = qwen_eval(6144, 1024, pruned=True, exchange=cfg)["cycles"]
        rows.append(dict(design="qwen_rom_ar_G6144", w15_config=cfg, what=what, tokens_s=round(clock / cyc, 1),
                         exchange_cycles_per_token_measured=meas, exchange_cycles_per_token_assumed=assumed,
                         per_allreduce_cycles=cf[cfg]["exchanges"]["allreduce_cycles_mean"]))
    return rows


def fabric_sweep():
    rows = []
    # V4.1 ROM: re-solve the priced DAG with every collective's latency set to L (+ the measured engine cycles)
    d = copy.deepcopy(PRESETS["proposal"])
    r0 = evaluate(copy.deepcopy(d), 1048576)
    r0.pop("_g", None)
    rows.append(dict(design="v41_rom_ar", collective_latency_us="baseline (W15 measured, adopted placement)",
                     tokens_s=round(r0["tokens_s"], 1)))
    for L in FABRIC_SWEEP_S:
        r = evaluate(dict(d, collective_latency_s=L), 1048576)
        r.pop("_g", None)
        rows.append(dict(design="v41_rom_ar", collective_latency_us=L * 1e6, tokens_s=round(r["tokens_s"], 1)))
    # V4.1 HBM: its fabric term is 125.9 us at the 668 ns hop, i.e. ~188 collectives on the path
    base = [r for r in v41_hbm_rows() if r["design"] == "v41_hbm_gpu_groupslot"]
    ncoll = V41_HBM_FABRIC_US["collective_latency"] / 0.668
    cur = v41_hbm_fabric_us(_HBM_SWITCH, _HBM_FEC)["collective_latency"] / ncoll    # the default per-collective term
    for b in base:
        for L in FABRIC_SWEEP_S:
            T = b["T_us"] + ncoll * (L * 1e6 - cur)
            rows.append(dict(design=b["design"], collective_latency_us=L * 1e6, tokens_s=round(1e6 / T, 1)))
    # Qwen ROM and HBM: 73 serial UCIe exchanges per token on the TP-2 pair
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    qr = qwen_eval(6144, 1024, pruned=True, exchange=None)   # the sweep prices exchanges at L
    qh = [r for r in qwen_hbm_rows() if r["design"] == "qwen_hbm_gpu"][0]
    for L in QWEN_UCIE_SWEEP_S:
        add = 73 * (L - 19.27 / clock)
        rows.append(dict(design="qwen_rom_ar_G6144", exchange_latency_us=L * 1e6,
                         tokens_s=round(1 / (qr["cycles"] / clock + add), 1)))
        rows.append(dict(design=qh["design"], exchange_latency_us=L * 1e6,
                         tokens_s=round(1 / (qh["T_us"] * 1e-6 + add), 1)))
    for r in w15_rows():
        rows.append(dict(r, source="W15 measured (results/rtl/w15_collectives.json)"))
    for r in rows:
        print(r)
    return rows


# ---------------------------------------------------------------------------------------------------------
# Economics: batch, energy, cost (W14; user positioning decision 2026-09-29).  The paper claims single-user
# speed against GPUs, makes energy per token and cost first-class, and reports aggregate throughput under
# batching.  This section prices all four designs and the GPU tiers on the same three axes:
#   batch    per-user tok/s, aggregate tok/s and per-user latency from batch 1 to the per-user state capacity;
#   energy   J per token at batch 1 and at the saturated batch, whole system (all dies, HBM stacks, links);
#   cost     die / package / stack / ROM mask-set counts and a dollar estimate per unit of throughput.
# It calls the sections above and does not change them.  Every constant here cites its source; ASSUMED marks
# the ones with none in the repository.
# ---------------------------------------------------------------------------------------------------------
ECON_BATCHES = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
ECON_SLO_TOKENS_S_PER_USER = 100.0   # ASSUMED illustrative interactivity floor for the "aggregate at an SLO" column
MAC_OPS = 2                   # technology.json mac_energy_j_per_op is per OPERATION and a MAC is 2 of them (as
                              # arch_budget_v41.energy_per_token).  power_ledger above charges 1 op per MAC: this
                              # section uses 2 (the V4.1 ROM MAC energy is < 1% of its token either way)
HBM_STACK_B = 22.5e9          # arch_budget_v41.hbm_comparator stack_capacity_B (HBM3E 24 GB class)
HBM_CAP_EFF = 0.9             # technology.json efficiencies.hbm_capacity (runtime reserve)
HBM_STACK_BPS = 1.0e12 * 0.9  # arch_budget_qwen3.HBM: 1.0 TB/s a stack, 0.90 sustained
B200_HBM_B = 180e9            # DGX B200: 1,440 GB HBM3E over 8 GPUs (NVIDIA DGX B200 datasheet)
B200_W_DECODE = TECH["power"]["gpu_reference_power"]["b200_measured_decode_w"]["value"]    # 689 W measured
B200_W_TDP = TECH["power"]["gpu_reference_power"]["b200_tdp_nvl72_w"]["value"]             # 1,200 W published
DFLASH_T3_B200 = {1: 230.0, 4: 861.0, 8: 1666.0, 16: 3133.0, 32: 5694.0}   # DFLASH_PAPER Table 3: B200 AR
                              # baselines at concurrency 1..32 (aggregate tok/s, SGLang FA4, BF16, Math500)
V41_ROM_SYSTEM = dict(packages=94, dies=188, layer_dies=112, head_dies=4, table_dies=72, stacks=464,
                      src="results/arch/v41_rack.json comparison[0] and logical.roles")
E_LINK = dict(ucie=TECH["energy"]["link_j_per_bit"]["ucie_advanced"]["value"],
              board=TECH["energy"]["link_j_per_bit"]["board_serdes_112g"]["value"])
V41_TP = 4                    # dies per pipeline stage (TP-4): the uarch graph is one die's work
V41_STAGES = 28
QWEN_ROM_AREA_DIE = dict(rom=265.0,                          # W12 integer placement, 34,669 macros (MICROARCH_MODEL)
                         logic=6144 * 18063.0 / 1e6 + 12.8 + 4 * 10.0 + 10.0,   # pruned groups + SU spill +
                                                             # 4 HBM PHY + UCIe PHY (arch_budget_qwen3 area constants)
                         sram=6144 * 94.824 * 41.04 / 1e6)  # KV ring SRAM per group (QWEN_AREA kv_sram_group_um2)
# ---- cost inputs (every dollar figure is ASSUMED in the repository or here) ----
_ARCHS = json.loads((ROOT / "configs/hardware/architectures.json").read_text())
_TIN = json.loads((ROOT / "configs/hardware/technology_inputs.json").read_text())["runtime_and_cost_assumptions"]


def _arch_cost(name):
    stack = [_ARCHS]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("name") == name and "cost_per_device" in o:
                return o["cost_per_device"]
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    raise KeyError(name)


COST = dict(
    package_usd=_arch_cost("NVIDIA-B200-x1"),
    package_basis="iso-package: every two-reticle + 8-HBM3E CoWoS-L-class package (the ROM packages, the HBM "
                  "comparator packages and a B200 alike) at the repository's B200 device price "
                  "(configs/hardware/architectures.json NVIDIA-B200-x1 cost_per_device, graded assumed)",
    silicon_usd_per_mm2=_TIN["wafer_cost_per_device"] / TECH["wafer"]["area_mm2"]["value"],
    silicon_basis="technology_inputs.json wafer_cost_per_device (assumed) over the 46,225 mm2 wafer-scale device",
    hbm_stack_usd=360.0,      # ASSUMED: 24 GB x ~$15/GB HBM3E (2025 analyst estimates, TrendForce / Silicon Analysts;
                              # no public spot price exists)
    mask_set_usd=15e6,        # ASSUMED: a full 5 nm-class mask set, $5-15M+ (SemiAnalysis, "The Dark Side of the
                              # Semiconductor Design Renaissance"); the upper end
    rom_coding_fraction=0.10,  # ASSUMED low case: a ROM die's weights live in its coding (via/metal) layers, ~10% of a
                              # full set; the base layers are shared by dies of one role
    production_units=_TIN["production_units"],   # technology_inputs.json (assumed): NRE amortisation volume
)


def _curve(T1_s, sat_tok_s, cap, bound, extra=None):
    """Batch sweep of a design whose users interleave on one machine: per-user rate is the single-user rate until
    the machine's busiest resource saturates, then the saturated aggregate shared by the batch."""
    rows = []
    bs = [b for b in ECON_BATCHES if b <= cap] + ([cap] if cap not in ECON_BATCHES else [])
    for B in sorted(set(bs)):
        pu = min(1.0 / T1_s, sat_tok_s / B)
        rows.append(dict(batch=B, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(B * pu, 1),
                         per_user_ms_per_token=round(1e3 / pu, 4),
                         binding="single-user chain" if 1.0 / T1_s <= sat_tok_s / B else bound,
                         **(extra(B) if extra else {})))
    return rows


def _sat_batch(rows):
    top = max(r["aggregate_tokens_s"] for r in rows)
    return next(r for r in rows if r["aggregate_tokens_s"] >= 0.999 * top)


# ---- V4.1 ROM: the priced graph, per die, by energy category and stage occupancy ----
_CONS_CTX = 1048576   # the V4.1 context of _v41_graph / the consolidation HBM chain (W16's short-context rows set it)


def _v41_graph(d, positions=1):
    """The proposal's priced graph; with positions > 1 the MTP verify pass at m = 1 (the issue scaling of
    v41_verify_T, which returns only times)."""
    r = evaluate(copy.deepcopy(d), _CONS_CTX)
    g = r.pop("_g")
    if positions > 1:
        E = A._env()
        clock, c = E["clock"], E["c"]
        cyc = 1.0 / clock
        p = positions
        for name, nd in g.nodes.items():
            k = nd["kind"]
            u = nd.get("_uarch")
            if u:
                nd["issue"] = max(u["t_read"] * p, u["t_x"] * p, u["t_ret"] * p, u["t_mac"] * p) * cyc
            elif k in ("vector", "reduce", "select", "collective"):
                nd["issue"] *= p
            elif k == "kvscan":
                if name.endswith("idx.score"):
                    n = int(nd["desc"].split()[2])
                    rd = d["idx_reader_Bpc"] or (3.6e12 / clock)
                    nd["issue"] = max(n * A.IDX_KEY_B / rd,
                                      p * n * c["index_heads"] * c["index_head_dim"] / d["idx_macs"]) * cyc
                else:
                    nd["issue"] *= p
            elif k == "matvec" and name.endswith("hc.fn"):
                nd["issue"] *= p
        g.solve(True)                               # re-time the path (contrib, fin) for the verify pass
    return r, g


def v41_rom_ledger(g, mac_ops=MAC_OPS, wire_j=WIRE_J_PER_BIT_MM):
    """Per-layer (one die) energy by category and stage occupancy: power_ledger's terms, split so that a verify
    pass can scale them (compute x positions, HBM once per pass).  The ROM field is the measured pair (PAIR_W):
    'field' is its busy excess over the clocked-idle floor.  With mac_ops=1 the busiest stage's on-die sum equals
    power_ledger's energy_per_token_uJ (tests/test_uarch_economics.py)."""
    field_mm = FLOORPLAN["cols"] * 25.628 + 20.0
    pp = pair_power(A._env()["clock"])
    lay, occ = {}, {}
    for name, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0:
            continue
        e = lay.setdefault(L, dict(mac=0.0, field=0.0, xnet=0.0, units=0.0, hbm_if=0.0, stack=0.0, link=0.0))
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            # measured pairs (PAIR_W): busy excess over the clocked idle floor, which is the die's static clock
            e["field"] += busy_pairs(nd) * nd["issue"] * (pp["busy"] - pp["clock"])
            e["xnet"] += xnet_energy(u, field_mm, wire_j)
        elif k == "matvec" and name.endswith("hc.fn"):
            e["mac"] += nd["sweep"]["macs"] * mac_ops * E_MAC["fp32"]
        elif k in ("vector", "reduce") and nd.get("_work"):
            cls, n_el = nd["_work"]
            e["units"] += n_el * E_MAC["fp32"] * (SFU_OPS_PER_ELEM if cls == "sfu" else 1) + n_el * 4 * 2 * E_SRAM_B
        elif k == "kvscan" and nd.get("_work"):
            cls, macs = nd["_work"]
            e["units"] += macs * mac_ops * (E_MAC["fp4"] if cls == "idx" else E_MAC["bf16"])
            hb = (int(nd["desc"].split()[2]) * A.IDX_KEY_B if name.endswith("idx.score")
                  else 640 * A.WIN_ROW_B / 4 if name.endswith(".scores") else 0)
            e["hbm_if"] += hb * E_HBM_IF_B
            e["stack"] += hb * (E_HBM_B - E_HBM_IF_B)
        elif k == "collective":
            e["link"] += nd.get("payload", 0) * 8 * E_LINK_BIT
        if k not in ("collective", "hop"):
            occ[L] = occ.get(L, 0.0) + nd["issue"]
    lps = 40 / V41_STAGES
    st_e, st_o = {}, {}
    for L in lay:
        s = int(L / lps)
        st_e[s] = st_e.get(s, 0.0) + sum(v for kk, v in lay[L].items() if kk != "stack")
        st_o[s] = st_o.get(s, 0.0) + occ.get(L, 0.0)
    cats = {kk: sum(x[kk] for x in lay.values()) for kk in ("mac", "field", "xnet", "units", "hbm_if", "stack", "link")}
    return dict(per_die_categories_J=cats, stage_die_energy_J=st_e, stage_occupancy_s=st_o)


def v41_rom_economics():
    d = copy.deepcopy(PRESETS["proposal"])
    r1, g1 = _v41_graph(d, 1)
    T1 = r1["T_us"] * 1e-6
    led = v41_rom_ledger(g1)
    area = area_ledger(d)
    pw = power_ledger(d, g1, r1["clock_hz"], r1["tokens_s"], area)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    link_static_die = rack["per_die"]["static_w"]["serdes_always_on"] + rack["per_die"]["static_w"]["ucie_idle"]
    die_static = pw["clock_w"] + pw["leakage_w"] + pw["hbm_idle_w"] + link_static_die
    static_w = dict(layer_dies=round(V41_ROM_SYSTEM["layer_dies"] * die_static, 1),
                    head_dies=round(rack["static"]["head_dies"], 1), table_dies=round(rack["static"]["table_dies"], 1))
    P_static = sum(static_w.values())
    cats = {k: V41_TP * v for k, v in led["per_die_categories_J"].items()}      # all 4 dies of every stage
    dyn_die = sum(v for k, v in cats.items() if k != "stack")
    sat = 1.0 / max(led["stage_occupancy_s"].values())
    cap = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["capacity"]["1048576"]["rom_users"]

    def e_ar(B):
        agg = min(B / T1, sat)
        return dict(energy_mJ_per_token=round((dyn_die + cats["stack"] + P_static / agg) * 1e3, 3),
                    system_w=round(P_static + (dyn_die + cats["stack"]) * agg, 0))
    ar = _curve(T1, sat, cap, "busiest stage occupancy", e_ar)
    # MTP m = 1: 6 positions per verify pass; compute terms x positions, HBM keys and rows once per pass
    Tp, _ = v41_verify_T(d, V41_POSITIONS, 1)
    Td = v41_rom_draft_s(T1)
    _, gv = _v41_graph(d, V41_POSITIONS)
    ledv = v41_rom_ledger(gv)
    head = max(ledv["stage_occupancy_s"])
    occ_v = dict(ledv["stage_occupancy_s"])
    occ_v[head] = occ_v[head] + Td                  # the draft runs on the head (+DSpark) dies (ASSUMED serial there)
    step_sat = max(occ_v.values())
    sat_m = V41_TAU / step_sat
    step1 = Tp + Td
    P = V41_POSITIONS
    e_pass = sum(v * (1 if k in ("hbm_if", "stack") else P) for k, v in cats.items())
    dyn_m = (e_pass + V41_DRAFT_FRACTION * (dyn_die + cats["stack"])) / V41_TAU

    def e_m(B):
        agg = min(B * V41_TAU / step1, sat_m)
        return dict(energy_mJ_per_token=round((dyn_m + P_static / agg) * 1e3, 3),
                    system_w=round(P_static + dyn_m * agg, 0))
    mtp = _curve(step1 / V41_TAU, sat_m, cap, "busiest stage occupancy (verify pass)", e_m)
    return dict(
        design="V4.1 ROM array (proposal, 1M context)", system=V41_ROM_SYSTEM,
        ar=dict(tokens_s_b1=round(1 / T1, 1), saturated_tokens_s=round(sat, 1), rows=ar,
                sat_batch=_sat_batch(ar)["batch"]),
        mtp_m1=dict(tokens_s_b1=round(V41_TAU / step1, 1), saturated_tokens_s=round(sat_m, 1), rows=mtp,
                    sat_batch=_sat_batch(mtp)["batch"], tau=V41_TAU, positions=P, verify_us=round(Tp * 1e6, 1),
                    draft_us=round(Td * 1e6, 1)),
        capacity_users=cap, capacity_basis="results/arch/arch_budget_v41.json capacity[1048576].rom_users (KV + index "
                                           "keys of the busiest layer-20 group in its 4 HBM3E stacks per die, 90% usable)",
        energy=dict(dynamic_mJ_per_token_die=round(dyn_die * 1e3, 3), stack_mJ_per_token=round(cats["stack"] * 1e3, 3),
                    categories_mJ_per_token={k: round(v * 1e3, 4) for k, v in cats.items()},
                    static_w=static_w, static_w_total=round(P_static, 1),
                    layer_die_static_w=dict(clock=pw["clock_w"], leakage=pw["leakage_w"], field_clock=pw["field"]["clock_w"],
                                            hub_clock_uncalibrated=pw["hub"]["clock_w"], hbm_interface_idle=pw["hbm_idle_w"],
                                            links=round(link_static_die, 3)),
                    mtp_dynamic_mJ_per_token=round(dyn_m * 1e3, 3),
                    basis="power_ledger terms on every stage x 4 TP dies (the uarch graph is one die, busiest-die "
                          "macros for every layer); ROM field = the MEASURED pair (PAIR_W, W18): dynamic 'field' = busy "
                          "excess over the clocked-idle floor; layer-die static = the ledger's clock + leakage (field "
                          "measured per placed pair, ungated; hub from area, UNCALIBRATED) + HBM interface idle, plus "
                          "the rack's always-on SerDes and UCIe; head and Engram-table dies' "
                          "static from results/arch/v41_rack.json power.static; HBM stack DRAM energy of the index "
                          "and KV reads; stack background (refresh) power not charged"),
        stage_occupancy_us={str(k): round(v * 1e6, 2) for k, v in sorted(led["stage_occupancy_s"].items())})


# ---- Qwen3-8B ROM package (AR, G = 6,144 pruned, 8K) ----
def _qwen_wl():
    import arch_budget_qwen3 as Q
    wl = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())["workload"]["8192"]
    return wl, Q.kv_bytes(wl, Q.KV_FMT_SPEC)


def _static_w(logic, rom, sram, clock, stacks):
    return dict(clock=CLOCK_J_MM2 * clock * (logic + 0.15 * (rom + sram)),
                leakage=logic * LEAK["logic"] + rom * LEAK["rom_array"] + sram * LEAK["sram_array"],
                hbm_interface_idle=stacks * HBM_IDLE_W_STACK)


# ROOT / USER DECISION 2026-09-30 (W16): the Qwen ROM product is option C -- two B200-class packages, 4 dies,
# TP-4 with one package crossing (W15's measured TP-4 board exchange), G = 6,144 a die (W12's die), W12 floorplan
# wires, ROM at the storage-only density (75.0 Mbit/mm2 + SECDED) -- because the two-reticle package does not hold
# the AR-only ROM at that density (tools/uarch_model.py qwen_rom_options).  The 2-die W5-wire row (9,851 tok/s) is
# superseded; qwen_eval keeps both wire calibrations (w5 9,851, w12 9,194 at the 2-die reference).
QWEN_ROM_PRODUCT = dict(k=4, G=6144, link="board", packages=2, stacks_per_die=4)


def _qwen_rom_product():
    P = QWEN_ROM_PRODUCT
    q = qwen_tp_point(P["k"], P["G"], P["link"])
    a = dict(logic=P["G"] * 18063.0 / 1e6 + QWEN_TILE_FIXED_MM2, rom=q["rom_mm2_per_die"],
             sram=P["G"] * QWEN_AREA["kv_sram_group_um2"] / 1e6)
    return q, a


def qwen_rom_economics():
    import arch_budget_qwen3 as Q
    P = QWEN_ROM_PRODUCT
    q, a = _qwen_rom_product()
    clock = q["clock_hz"]
    ub = q["unit_busy"]
    T1 = q["cycles"] / clock
    wl, kvb = _qwen_wl()
    bounds = dict(q["bounds"])                  # lanes, stream unit, KV stream (4 stacks a die, its own KV heads)
    bind = min(bounds, key=bounds.get)
    sat = bounds[bind]
    cap = q["capacity_users"]
    st = {k: P["k"] * v for k, v in _static_w(a["logic"], a["rom"], a["sram"], clock, P["stacks_per_die"]).items()}
    P_static = sum(st.values())
    macs = wl["weight_macs"] + wl["attention_macs"]
    tpx = Q.tp_exchanges(clock)
    cats = dict(mac=macs * MAC_OPS * E_MAC["bf16"],                 # the lane is an exact BF16 product of a decoded INT8
                rom=wl["bytes"]["weights_rom_format"] * (E_ROM_B + E_DELIVER_B),
                kv_on_die=kvb * (E_HBM_IF_B + E_DELIVER_B + 2 * E_SRAM_B),   # PHY/controller, ring SRAM, delivery
                stream=wl["elementwise_total"] * (E_MAC["fp32"] + 2 * 4 * E_SRAM_B),
                ucie=tpx["bytes_per_direction"] * 2 * 8 * E_LINK["board"] * (P["k"] - 1),   # TP-4 exchanges
                stack=kvb * (E_HBM_B - E_HBM_IF_B))
    dyn = sum(cats.values())

    def e(B):
        agg = min(B / T1, sat)
        return dict(energy_mJ_per_token=round((dyn + P_static / agg) * 1e3, 3), package_w=round(P_static + dyn * agg, 1))
    rows = _curve(T1, sat, cap, bind.replace("_", " "), e)
    return dict(design="Qwen3-8B ROM, option C (2 packages, 4 dies, TP-4, G = 6,144 pruned, W12 wires, 8K)",
                system=dict(packages=P["packages"], dies=P["k"], stacks=P["k"] * P["stacks_per_die"]),
                product=dict(QWEN_ROM_PRODUCT, exchange=q["exchange"], wire_model="w12",
                             superseded="2-die package, W5 wires: 9,851 tok/s (does not fit at 75 Mbit/mm2)"),
                ar=dict(tokens_s_b1=round(1 / T1, 1), saturated_tokens_s=round(sat, 1), rows=rows,
                        sat_batch=_sat_batch(rows)["batch"]),
                bounds_tokens_s={k: round(v, 1) for k, v in bounds.items()}, binding=bind,
                unit_busy_cycles_per_die=ub, token_cycles=q["cycles"], capacity_users=cap,
                capacity_basis="each die's 4 HBM3E stacks x 22.5 GB x 0.90 over its 2 of 8 KV heads of one 8K user "
                               f"({kvb / 1e6:.1f} MB a user)",
                energy=dict(dynamic_mJ_per_token=round(dyn * 1e3, 3),
                            categories_mJ_per_token={k: round(v * 1e3, 4) for k, v in cats.items()},
                            static_w={k: round(v, 2) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            area_mm2_per_die={k: round(v, 1) for k, v in a.items()},
                            basis="the uarch constants (technology.json), 2 ops per MAC, all 4 dies; ROM area at the "
                                  "storage-only density"),
                note="m = 1: batching reuses no weight word, so the lanes, the stream unit and the KV stream each cap "
                     "the aggregate; the KV stream (each user's 604 MB of 8K FP8 KV per token over 16 stacks) binds first")



# ---- HBM comparators (tier 3, the GPU-organised dies) ----
def qwen_hbm_economics():
    dq = hbm_gpu_design("qwen")
    clock = dq["clock_hz"]
    r = dq["hbm_Bpc"]
    cols = dq["element"]["cols"]
    ops = qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])
    ar_bytes = sum(b for b, _ in ops)
    t_ar, _ = stream_overlap(ops, r, dq["sm_count"] * 128, dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    wl, kvb = _qwen_wl()
    kv_die = kvb / 2
    w_die = ar_bytes - kv_die
    cap = int((8 * HBM_STACK_B * HBM_CAP_EFF - 2 * w_die) // kvb)
    sa = dq["sm_area"]
    n = dq["sm_count"]
    st = {k: 2 * v for k, v in _static_w(n * sa["logic_mm2"] + 4 * 10.0 + 10.0, 0.0,
                                         n * sa["sram_mm2"] + dq["l2"]["mm2"], clock, 4).items()}
    P_static = sum(st.values())
    macs = wl["weight_macs"] + wl["attention_macs"]
    spec = {x["block"]: x for x in hbm_speculation_rows() if x["design"].startswith("qwen_hbm_dflash_b")}

    def step(B, b, s1, draft):
        passes = math.ceil(B * b / cols)
        cyc = s1 + ((passes - 1) * (w_die + draft) + (B - 1) * kv_die) / r
        byt = 2 * (passes * (w_die + draft) + B * kv_die)
        e = (B * b * (macs + 2 * draft) * MAC_OPS * E_MAC["bf16"] + byt * E_HBM_B
             + 2 * passes * (w_die + draft) * 2 * E_SRAM_B + B * b * wl["elementwise_total"] * (E_MAC["fp32"] + 8 * E_SRAM_B))
        return cyc, e

    def rows_for(pick):
        out = []
        for B in sorted(set([b for b in ECON_BATCHES if b <= cap] + [cap])):
            cyc, e, tau, blk = pick(B)
            t = cyc / clock
            pu = tau / t
            agg = B * pu
            out.append(dict(batch=B, block=blk, tau=tau, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(agg, 1),
                            per_user_ms_per_token=round(1e3 / pu, 4),
                            binding="weight stream" if B * blk <= cols else "weight re-stream + KV stream",
                            energy_mJ_per_token=round((e / (B * tau) + P_static / agg) * 1e3, 3),
                            package_w=round(P_static + e / t, 1)))
        return out

    def ar_pick(B):
        c, e = step(B, 1, t_ar, 0.0)
        return c, e, 1.0, 1

    def df_pick(B):
        best = None
        for b, x in spec.items():
            c, e = step(B, b, x["step_cycles"], x["draft_bytes_per_die"])
            if best is None or x["tau"] / c > best[2] / best[0]:
                best = (c, e, x["tau"], b)
        return best
    ar = rows_for(ar_pick)
    df = rows_for(df_pick)
    return dict(design="Qwen3-8B HBM comparator, GPU organisation (tier 3, 8K)", system=dict(packages=1, dies=2, stacks=8),
                ar=dict(tokens_s_b1=ar[0]["per_user_tokens_s"], rows=ar, saturated_tokens_s=max(x["aggregate_tokens_s"] for x in ar),
                        sat_batch=_sat_batch(ar)["batch"]),
                dflash=dict(tokens_s_b1=df[0]["per_user_tokens_s"], rows=df,
                            saturated_tokens_s=max(x["aggregate_tokens_s"] for x in df), sat_batch=_sat_batch(df)["batch"],
                            note="best block per batch (tau per block from results/speculative/dflash_block_acceptance.json); "
                                 "users x block positions share the 16 MMA columns, a pass per 16"),
                capacity_users=cap, capacity_basis="8 stacks x 22.5 GB x 0.90 less the INT8 weights, over 604 MB per user",
                energy=dict(static_w={k: round(v, 2) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            basis="SM MACs (2 ops, BF16 lane) + the whole HBM path per byte (technology.json "
                                  "hbm_j_per_byte, die + stack) + SMEM staging write and read + stream elements; "
                                  "static: SM logic, SMEM + L2 SRAM, 4 HBM PHY + UCIe as logic, HBM interface idle"))


def _v41_weight_split():
    E = A._env()
    c = E["c"]
    tot, _ = A.token_workload(c, 1048576)
    routed = c["num_layers"] * c["experts_per_token"] * 3 * c["moe_intermediate_size"] * c["hidden_size"] * A.FP4
    return tot, tot["bytes"]["rom"] - routed, routed, c


def _v41_weight_bytes(tokens):
    tot, dense, routed, c = _v41_weight_split()
    U = A.distinct_experts(tokens, c["num_routed_experts"], c["experts_per_token"])
    return dense + routed * U / c["experts_per_token"]


def _v41_system_macs_j():
    tot, *_ = _v41_weight_split()
    fmt = lambda k: "w4a8" if k == "weight:fp4" else {"fp8": "fp8", "fp4": "fp4", "fp32": "fp32"}.get(k.split(":")[1], "bf16")  # noqa: E731
    return sum(v * MAC_OPS * E_MAC[fmt(k)] for k, v in tot["macs"].items())


def v41_hbm_economics(rom_units_j_per_token):
    dv = hbm_gpu_design("v41")
    clock = dv["clock_hz"]
    sweep1 = 37.4                                       # us: the weight sweep of one token (v41_hbm_chain)
    w1 = _v41_weight_bytes(1)
    sweep = lambda toks: sweep1 * _v41_weight_bytes(toks) / w1   # noqa: E731
    cols = dv["element"]["cols"]
    cache = {}

    def chain(P):
        if P not in cache:
            _, parts, _ = v41_hbm_chain(True, P)
            cache[P] = parts
        return cache[P]
    issue1 = chain(2)["verify_extra_issue"]             # one more user's dedicated-unit issue (us)

    def T(P, toks):
        return max(sum(chain(P).values()), sweep(toks))

    def occ(P, toks):
        p = chain(P)
        return max(p["sm_matvec"] + p["x_broadcast_fill"] + p["barrier"], P * issue1, sweep(toks))
    tot, *_ = _v41_weight_split()
    per_user_hbm = tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]
    macs_j = _v41_system_macs_j()
    coll_b = tot["collective_bytes"]
    n = V41_HBM_DIES
    sa = dv["sm_area"]
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    st1 = _static_w(dv["sm_count"] * sa["logic_mm2"] + dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL + 40.0, 0.0,
                    dv["sm_count"] * sa["sram_mm2"] + dv["l2"]["mm2"], clock, 4)
    st1["links"] = rack["serdes_always_on"] + rack["ucie_idle"]      # ASSUMED: the same link class as a ROM layer die
    st = {k: n * v for k, v in st1.items()}
    P_static = sum(st.values())
    cap = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["capacity"]["1048576"]["hbm_users"]

    def energy(B, P, draft_frac):
        """One step's dynamic energy: every column pass reads the union of ITS tokens' experts."""
        toks = B * P
        per = max(1, cols // P)
        passes = math.ceil(B / per)
        wb = passes * _v41_weight_bytes(min(B, per) * P)
        e = (toks * macs_j + (wb + B * per_user_hbm) * E_HBM_B + wb * 2 * E_SRAM_B + toks * rom_units_j_per_token
             + toks * coll_b * 8 * E_LINK["board"] * 2)          # ASSUMED: two switch hops at 112G SerDes energy
        return e * (1 + draft_frac)

    def rows(P, tau, draft_frac):
        out = []
        per = max(1, cols // P)                           # users per column pass
        Td = draft_frac * T(1, 1)
        for B in sorted(set([b for b in ECON_BATCHES if b <= cap] + [cap])):
            if B <= per:
                t = T(B * P, B * P) + Td
            else:
                t = max(T(per * P, per * P) + Td, math.ceil(B / per) * (occ(per * P, per * P) + Td))
            t *= 1e-6
            pu = tau / t
            agg = B * pu
            e = energy(B, P, draft_frac)
            out.append(dict(batch=B, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(agg, 1),
                            per_user_ms_per_token=round(1e3 / pu, 4),
                            binding="chain (latency)" if B <= per else "busiest resource per column pass",
                            energy_mJ_per_token=round((e / (B * tau) + P_static / agg) * 1e3, 3),
                            system_w=round(P_static + e / t, 0)))
        return out
    ar = rows(1, 1.0, 0.0)
    mtp = rows(V41_POSITIONS, V41_TAU, V41_DRAFT_FRACTION)
    return dict(design="V4.1 HBM comparator, GPU organisation (tier 3, 96 dies, 1M)",
                system=dict(packages=n // 2, dies=n, stacks=4 * n),
                ar=dict(tokens_s_b1=ar[0]["per_user_tokens_s"], rows=ar, saturated_tokens_s=max(x["aggregate_tokens_s"] for x in ar),
                        sat_batch=_sat_batch(ar)["batch"]),
                mtp=dict(tokens_s_b1=mtp[0]["per_user_tokens_s"], rows=mtp,
                         saturated_tokens_s=max(x["aggregate_tokens_s"] for x in mtp), sat_batch=_sat_batch(mtp)["batch"],
                         tau=V41_TAU, positions=V41_POSITIONS),
                capacity_users=cap, capacity_basis="results/arch/arch_budget_v41.json capacity[1048576].hbm_users",
                occupancy_us_per_pass=dict(ar_8_users=round(occ(8, 8), 1), mtp_1_user=round(occ(6, 6), 1),
                                           dedicated_issue_per_user=round(issue1, 1)),
                energy=dict(static_w={k: round(v, 1) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            basis="system MACs by format (2 ops), weights (routed union over the pass) and per-user "
                                  "KV + index keys over the whole HBM path, SMEM staging, the ROM array's dedicated-"
                                  "unit energy per token (same units), fabric bytes over two switch hops; static per die: "
                                  "SM + dedicated-unit logic, SMEM + L2, 4 PHY, HBM interface idle, links; the NVL-class "
                                  "switch itself not charged"),
                note="B <= 8 users ride the 8 MMA columns on one weight fetch (the chain re-priced with B columns: "
                     "dedicated-unit issue repeats per user); beyond, column passes interleave and the busiest of SM "
                     "time, dedicated-unit issue and the weight sweep bounds the step")


# ---- GPU tiers ----
def _fit_line(pts):
    xs = list(pts)
    ts = [b / pts[b] for b in xs]
    n = len(xs)
    mx, mt = sum(xs) / n, sum(ts) / n
    b = sum((x - mx) * (t - mt) for x, t in zip(xs, ts)) / sum((x - mx) ** 2 for x in xs)
    a = mt - b * mx
    return a, b, {x: round(x / (a + b * x), 1) for x in xs}


def gpu_economics():
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    wl, kvb = _qwen_wl()
    t1 = fixed + s_per_B * (GPU_FIT["qwen_fp8_weight_bytes"] + GPU_FIT["qwen_fp8_kv_bytes_8k"])
    a, b, fitted = _fit_line(DFLASH_T3_B200)
    inc = max(b, s_per_B * kvb)
    capq = int((B200_HBM_B * HBM_CAP_EFF - GPU_FIT["qwen_fp8_weight_bytes"]) // kvb)

    def q_rows(W):
        out = []
        for B in sorted(set([x for x in ECON_BATCHES if x <= capq] + [capq])):
            t = t1 + (B - 1) * inc
            out.append(dict(batch=B, per_user_tokens_s=round(1 / t, 1), aggregate_tokens_s=round(B / t, 1),
                            per_user_ms_per_token=round(t * 1e3, 4),
                            energy_mJ_per_token=round(W * t / B * 1e3, 2)))
        return out
    q = q_rows(B200_W_DECODE)
    q_tdp = q_rows(B200_W_TDP)
    # V4.1-Flash on 8x B200 (tier 2 form): weights read once a step (routed union over the batch), each user's
    # index keys and KV, NCCL-class all-reduces
    tot, dense, routed, c = _v41_weight_split()
    fixed_layer = fixed / 36
    index_scan = v41_gpu_index_scan(1048576, c=c)
    idx_user = index_scan["bytes"]
    state_user = 0.0
    for L in range(c["num_layers"]):
        r = c["compress_ratios"][L]
        if L in c["kv_source_layer_ids"] and r:
            state_user += 1048576 // r * (A.CKV_ROW_B + A.IDX_KEY_B)
        state_user += c["window_tokens"] * A.WIN_ROW_B
    ckpt = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())["checkpoint_bytes"]
    capv = int((8 * B200_HBM_B * HBM_CAP_EFF - ckpt) // state_user)
    v = []
    for B in sorted(set([x for x in ECON_BATCHES if x <= capv] + [capv])):
        t = (40 * fixed_layer + s_per_B * (_v41_weight_bytes(B) + B * idx_user) / 8 + 40 * 5 * NCCL_ALLREDUCE_S)
        v.append(dict(batch=B, per_user_tokens_s=round(1 / t, 1), aggregate_tokens_s=round(B / t, 1),
                      per_user_ms_per_token=round(t * 1e3, 4),
                      energy_mJ_per_token=round(8 * B200_W_DECODE * t / B * 1e3, 2)))
    t2 = {x["design"]: x for x in gpu_tier2()}
    qs = t2["Qwen3-8B on 1x B200, FP8 weights, 8K, calibrated"]
    vs = t2["DeepSeek-V4.1-Flash on 8x B200, calibrated"]
    anchors = [dict(tier=1, design=f"Qwen3-8B, 1x B200, SGLang FA4, BF16, AR, concurrency {B} (DFlash paper Table 3)",
                    batch=B, aggregate_tokens_s=x, per_user_tokens_s=round(x / B, 1),
                    energy_mJ_per_token_at_689W=round(B200_W_DECODE / x * 1e3, 1), line_fit_tokens_s=fitted[B])
               for B, x in DFLASH_T3_B200.items()]
    anchors += [dict(tier=1, design=x["design"], batch=1, aggregate_tokens_s=x["tokens_s"], per_user_tokens_s=x["tokens_s"],
                     energy_mJ_per_token_at_689W=round(B200_W_DECODE * (8 if "8x B200" in x["design"] else 1)
                                                      / x["tokens_s"] * 1e3, 1))
                for x in TIER1 if "B200" in x["design"] and "concurrency" not in x["design"] and "AR (DFlash" not in x["design"]]
    return dict(
        qwen=dict(design="Qwen3-8B on 1x B200, FP8, 8K (tier 2)", system=dict(gpus=1, packages=1, dies=2, stacks=8),
                  rows=q, rows_at_tdp=q_tdp, tokens_s_b1=q[0]["per_user_tokens_s"],
                  saturated_tokens_s=max(x["aggregate_tokens_s"] for x in q), sat_batch=_sat_batch(q)["batch"],
                  dflash_b1=dict(reasoning_mix=qs["spec_tokens_s_reasoning_mix"], math_code=qs["spec_tokens_s_math_code"]),
                  calibration=dict(paper_line_fixed_ms=round(a * 1e3, 4), paper_line_per_user_us=round(b * 1e6, 2),
                                   fitted_tokens_s=fitted, measured_tokens_s=DFLASH_T3_B200,
                                   per_user_increment_8k_us=round(inc * 1e6, 2),
                                   kv_8k_fp8_us=round(s_per_B * kvb * 1e6, 2),
                                   rule="step(B) = tier-2 step(1) + (B - 1) x max(the paper's fitted per-user increment, "
                                        "one 8K FP8 user's KV at the fitted B200 bytes rate); the paper's increment "
                                        "includes its own (shorter-context) KV, so the max is GPU-favourable"),
                  capacity_users=capq, capacity_basis="180 GB x 0.90 less FP8 weights over 604 MB per user"),
        v41=dict(design="DeepSeek-V4.1-Flash on 8x B200, 1M (tier 2)", system=dict(gpus=8, packages=8, dies=16, stacks=64),
                 rows=v, tokens_s_b1=v[0]["per_user_tokens_s"], saturated_tokens_s=max(x["aggregate_tokens_s"] for x in v),
                 sat_batch=_sat_batch(v)["batch"], mtp_b1=vs["spec_tokens_s"], capacity_users=capv,
                 per_user_state_bytes=state_user,
                 index_scan=index_scan,
                 capacity_basis="8 x 180 GB x 0.90 less the 510.3 GB checkpoint over each user's CKV + index keys "
                                "(KV-owner layers 2, 8, 14, 20) and 40 windows"),
        anchors=anchors, power=dict(decode_w=B200_W_DECODE, tdp_w=B200_W_TDP,
                                    source="technology.json power.gpu_reference_power (measured decode 689 W; NVL72 TDP)"))


# ---- cost ----
def cost_row(name, system, rom_mask_sets, b1, sat, model_nre=True):
    pk = system["packages"]
    hw = pk * COST["package_usd"]
    comp = system["dies"] * 815.0 * COST["silicon_usd_per_mm2"] + system["stacks"] * COST["hbm_stack_usd"]
    nre_hi = rom_mask_sets * COST["mask_set_usd"]
    nre_lo = rom_mask_sets * COST["mask_set_usd"] * COST["rom_coding_fraction"]
    per_sys_hi = nre_hi / COST["production_units"]
    per_sys_lo = nre_lo / COST["production_units"]
    tot_lo, tot_hi = hw + per_sys_lo, hw + per_sys_hi
    return dict(design=name, packages=pk, dies=system["dies"], silicon_mm2=system["dies"] * 815.0,
                hbm_stacks=system["stacks"], rom_mask_sets=rom_mask_sets,
                hardware_usd_iso_package=hw, component_usd_silicon_and_stacks=round(comp),
                rom_nre_usd=dict(coding_layers_only=nre_lo, full_mask_sets=nre_hi),
                rom_nre_per_system_usd=dict(coding_layers_only=per_sys_lo, full_mask_sets=per_sys_hi),
                capex_per_system_usd=dict(low=round(tot_lo), high=round(tot_hi)),
                tokens_s_b1=b1, tokens_s_saturated=sat,
                usd_per_tokens_s_b1=dict(low=round(tot_lo / b1, 2), high=round(tot_hi / b1, 2)),
                usd_per_tokens_s_saturated=dict(low=round(tot_lo / sat, 2), high=round(tot_hi / sat, 2)))


def economics():
    v41r = v41_rom_economics()
    units_j = v41r["energy"]["categories_mJ_per_token"]["units"] * 1e-3
    qr = qwen_rom_economics()
    qh = qwen_hbm_economics()
    vh = v41_hbm_economics(units_j)
    gp = gpu_economics()

    def pick(rows, B):
        return next(x for x in rows if x["batch"] == B)
    summary = []
    for name, blk, rows_key in (("Qwen ROM AR (G = 6,144)", qr["ar"], "rows"), ("Qwen HBM tier 3 AR", qh["ar"], "rows"),
                                ("Qwen HBM tier 3 DFlash", qh["dflash"], "rows"), ("Qwen 1x B200 AR (tier 2)", gp["qwen"], "rows"),
                                ("V4.1 ROM AR", v41r["ar"], "rows"), ("V4.1 ROM MTP m = 1", v41r["mtp_m1"], "rows"),
                                ("V4.1 HBM tier 3 AR", vh["ar"], "rows"), ("V4.1 HBM tier 3 MTP", vh["mtp"], "rows"),
                                ("V4.1 8x B200 AR (tier 2)", gp["v41"], "rows")):
        rows = blk[rows_key]
        s = _sat_batch(rows)
        summary.append(dict(design=name, tokens_s_b1=rows[0]["per_user_tokens_s"], energy_mJ_b1=rows[0]["energy_mJ_per_token"],
                            sat_batch=s["batch"], sat_aggregate_tokens_s=s["aggregate_tokens_s"],
                            sat_per_user_tokens_s=s["per_user_tokens_s"], energy_mJ_sat=s["energy_mJ_per_token"],
                            capacity_users=rows[-1]["batch"]))
    S = {x["design"]: x for x in summary}
    R = {x["design"]: x for x in summary}
    modes = dict(zip([x["design"] for x in summary],
                     [qr["ar"]["rows"], qh["ar"]["rows"], qh["dflash"]["rows"], gp["qwen"]["rows"], v41r["ar"]["rows"],
                      v41r["mtp_m1"]["rows"], vh["ar"]["rows"], vh["mtp"]["rows"], gp["v41"]["rows"]]))

    def slo(names):
        """Largest aggregate with every user at >= ECON_SLO_TOKENS_S_PER_USER, over the design's modes."""
        best = 0.0
        for n_ in names:
            ok = [x["aggregate_tokens_s"] for x in modes[n_] if x["per_user_tokens_s"] >= ECON_SLO_TOKENS_S_PER_USER]
            best = max([best] + ok)
        return best or None
    systems = (("Qwen ROM (AR, G = 6,144)", qr["system"], qr["system"]["dies"], ["Qwen ROM AR (G = 6,144)"]),
               ("Qwen HBM tier 3 (AR / DFlash)", qh["system"], 0, ["Qwen HBM tier 3 AR", "Qwen HBM tier 3 DFlash"]),
               ("Qwen 1x B200 (tier 2, AR)", gp["qwen"]["system"], 0, ["Qwen 1x B200 AR (tier 2)"]),
               ("V4.1 ROM array (AR / MTP m = 1)", V41_ROM_SYSTEM, V41_ROM_SYSTEM["dies"], ["V4.1 ROM AR", "V4.1 ROM MTP m = 1"]),
               ("V4.1 HBM tier 3 (AR / MTP)", vh["system"], 0, ["V4.1 HBM tier 3 AR", "V4.1 HBM tier 3 MTP"]),
               ("V4.1 8x B200 (tier 2, AR)", gp["v41"]["system"], 0, ["V4.1 8x B200 AR (tier 2)"]))
    cost = []
    for name, system, masks, names in systems:
        b1 = max(R[n_]["tokens_s_b1"] for n_ in names)
        sat = max(x["aggregate_tokens_s"] for n_ in names for x in modes[n_])
        c_ = cost_row(name, system, masks, b1, sat)
        s_ = slo(names)
        c_["tokens_s_at_slo"] = s_
        c_["usd_per_tokens_s_at_slo"] = (dict(low=round(c_["capex_per_system_usd"]["low"] / s_, 2),
                                              high=round(c_["capex_per_system_usd"]["high"] / s_, 2)) if s_ else None)
        c_["modes"] = names
        cost.append(c_)
    return dict(summary=summary, qwen_rom=qr, qwen_hbm=qh, v41_rom=v41r, v41_hbm=vh, gpu=gp, cost=cost,
                cost_inputs=COST, mac_ops=MAC_OPS, slo_tokens_s_per_user=ECON_SLO_TOKENS_S_PER_USER,
                cost_rule="best mode of each design at each point: b1 = its fastest single-user mode, saturated = its "
                          "largest aggregate within the per-user state capacity; capex = packages at the iso-package "
                          "price + ROM mask NRE / production units (low: coding layers only; high: full mask sets)")


ECON_SOURCES = ("tools/uarch_model.py", "tools/arch_budget_v41.py", "tools/arch_budget_qwen3.py",
                "configs/hardware/technology.json", "configs/hardware/architectures.json",
                "configs/hardware/technology_inputs.json", "results/arch/arch_budget_v41.json",
                "results/arch/qwen3_budget.json", "results/arch/v41_rack.json", "results/arch/qwen_gpu_calibration.json",
                "results/arch/v41_hbm_region_preflight.json", "results/speculative/dflash_block_acceptance.json",
                "results/rtl/gpu_sm_exact.json", "results/rtl/gpu_sm_blockdot_exact.json",
                "results/rtl/gpu_supply_barrier.json", "configs/models/candidates/deepseek-v4.1-flash.json")


# ---------------------------------------------------------------------------------------------------------
# Economics levers (W14b; root 2026-09-29): V4.1 ROM static-power reduction, the adaptive MTP policy, and
# via-programmable ROM mask cost.  Calls the sections above; changes none of them.
# ---------------------------------------------------------------------------------------------------------
# Power-state constants.  ReGate = Y. Xue and J. Huang, "ReGate: Enabling Power Gating in Neural Processing Units",
# MICRO 2025 (arXiv 2508.02536): 7 nm prototype, Table 3 and section 6.1.
PG = dict(
    logic_residual=0.03,          # ReGate 6.1: power-gated logic leaks 3% of its ON static power
    sram_sleep_residual=0.25,     # ReGate 6.1: sleep-mode (retention) SRAM 25%
    sram_off_residual=0.002,      # ReGate 6.1: powered-off SRAM 0.2%
    rom_residual=0.03,            # ASSUMED: a mask ROM holds no state, so its array and periphery gate like logic
    hbm_if_residual=0.03,         # ReGate 3/4: HBM controller + PHY low-power mode (the DRAM self-refreshes); gated
                                  # like logic
    serdes_lpi_residual=0.10,     # ASSUMED: 112G PAM4 SerDes in low-power idle keeps ~10% (CDR/bias kept warm)
    cg_residual=0.10,             # ASSUMED: clock power left when a region's ICGs are closed (global spine, enables)
    stage_wake_s=1e-6,            # ASSUMED: an 815 mm2 stage domain woken as ~100 staggered sub-domains of ReGate's
                                  # 10-cycle SA-class domains to bound rush current (di/dt): ~1,000 cycles
    stage_wake_s_c6=133e-6,       # sensitivity: Haswell C6 worst-case wake (Schoene et al., "Wake-up latencies for
                                  # processor idle states on current x86 processors", 2015) -- includes state
                                  # save/restore a stateless ROM stage does not need; an upper bound
    stage_bet_s=0.5e-6,           # ASSUMED: break-even time at die scale ~ ReGate Table 3's 412-469 cycles (HBM, ICI,
                                  # whole SA) at 1 GHz; the gating overhead energy is leakage x BET (its definition)
    hbm_wake_cycles=60,           # ReGate Table 3: HBM controller & PHY power on/off delay 60 cycles
    serdes_wake_s=5e-6,           # IEEE 802.3bj EEE: Tw_PHY targeted at ~5 us for a 100 Gb/s PHY
)


# MEASURED clock-gated idle of one ROM element pair (2026-10-04, results/rtl/rom_stage_power_gating_20261004,
# route R3, OpenSTA TT on routed SPEF + gate-level SAIF at 1.2 GHz): 3.005 mW per pair (0.243 mW of it leakage).  The
# ledger used to charge PG["cg_residual"] (10%, ASSUMED) of the ungated pair clock (79.2 mW at 1.034 GHz) + 0.22 mW
# leakage = 8.14 mW per clock-gated idle pair.  The ROM field's idle clock now uses the measured residual clock
# (scaled linearly with the clock, as pair_power does); the hub keeps the ASSUMED 10% (not measured).
def _pair_cg_idle_measured():
    v = json.loads((ROOT / "results/rtl/rom_stage_power_gating_20261004/verdict.json").read_text())["power_w"]["cg_idle"]
    return dict(total_w=v["total"], leak_w=v["leakage"], clock_w=v["total"] - v["leakage"], clock_hz=1.2e9,
                src="results/rtl/rom_stage_power_gating_20261004/verdict.json power_w.cg_idle (route R3, TT)")


PAIR_CG_IDLE = _pair_cg_idle_measured()


def field_cg_residual(clock):
    """The ROM field's clock-gated idle clock as a fraction of the ungated pair clock at `clock` (MEASURED numerator)."""
    return PAIR_CG_IDLE["clock_w"] * clock / PAIR_CG_IDLE["clock_hz"] / pair_power(clock)["clock"]


def _stage_windows(g):
    """Per-stage time on the single-user critical path (the stage's active window at batch 1; the head stage
    carries the embed and argmax), and each stage's start time on the path."""
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    lps = 40 / V41_STAGES
    win, start, t = {}, {}, 0.0
    for n in g.path(sink):
        L = g.nodes[n]["layer"]
        c = sum(g.contrib[n].values())
        s = V41_STAGES if (L is None or L < 0) else int(L / lps)
        win[s] = win.get(s, 0.0) + c
        start.setdefault(s, t)
        t += c
    return win, start, t


def _region_busy(g):
    """Per-stage, per-die busy time of the ROM field (weight matvecs) and the hub (every other issued unit).  The
    field's is pair-weighted (busy pair-seconds / placed pairs): with the per-pair ICG only an op's holding pairs
    clock, so region clock gating (policy 2) charges the field clock for that equivalent full-field time."""
    lps = 40 / V41_STAGES
    out = {}
    for n, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0 or nd["kind"] in ("collective", "hop"):
            continue
        s = int(L / lps)
        b = out.setdefault(s, dict(field=0.0, hub=0.0))
        if nd.get("_uarch"):
            b["field"] += nd["issue"] * busy_pairs(nd) / PAIR_W["placed_pairs"]
        else:
            b["hub"] += nd["issue"]
    return out


def v41_die_static_parts(d):
    """One layer die's static power by region and class, from the area ledger and the uarch constants (their sum is
    the economics section's ungated die static)."""
    E = A._env()
    clock = E["clock"]
    a = area_ledger(d)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    cl = CLOCK_J_MM2 * clock
    N = PAIR_W["placed_pairs"]
    return dict(
        # ROM field MEASURED per pair (PAIR_W); hub from its area, UNCALIBRATED
        field=dict(clock=N * pair_power(clock)["clock"], leak_logic=N * PAIR_W["leak_cell"], leak_rom=N * PAIR_W["leak_rom"]),
        field_cg_residual=field_cg_residual(clock),     # MEASURED pair clock-gated idle (PAIR_CG_IDLE)
        hub=dict(clock=cl * (a["hub_logic_mm2"] + 0.15 * a["vm_ports"]),
                 leak_logic=a["hub_logic_mm2"] * LEAK["logic"], leak_sram=a["vm_ports"] * LEAK["sram_array"]),
        hbm_if=4 * HBM_IDLE_W_STACK, serdes=rack["serdes_always_on"], ucie=rack["ucie_idle"])


def _die_energy(p, period, window, busy, policy, wake_s, pg_ok):
    """Static energy of one die over one token period: `window` s active (at batch 1 the critical-path window, at
    saturation the stage's occupancy), `busy` = region busy times inside it, the rest idle.
    policies: 0 ungated; 1 stage clock gating; 2 + region clock gating inside the window; 3 + power gating of the
    idle stage (retention SRAM, gated logic and ROM, HBM PHY power-down, SerDes / UCIe low-power idle) when the
    idle gap fits the wake-up and the break-even time."""
    rk = dict(field=p.get("field_cg_residual", PG["cg_residual"]), hub=PG["cg_residual"])
    idle = max(0.0, period - window)
    clk = p["field"]["clock"] + p["hub"]["clock"]
    clk_r = rk["field"] * p["field"]["clock"] + rk["hub"] * p["hub"]["clock"]     # clock left with the ICGs closed
    leak = p["field"]["leak_logic"] + p["field"]["leak_rom"] + p["hub"]["leak_logic"] + p["hub"]["leak_sram"]
    io = p["hbm_if"] + p["serdes"] + p["ucie"]
    if policy == 0:
        return (clk + leak + io) * period
    if policy == 1:
        e_clk = clk * window + clk_r * idle
    else:
        e_clk = sum(p[k]["clock"] * (min(busy[k], window) + rk[k] * (window - min(busy[k], window))) for k in ("field", "hub")) \
            + clk_r * idle
    if policy < 3 or not pg_ok:
        return e_clk + (leak + io) * period
    on = window + wake_s                      # the wake-up runs with the stage leaking at its ON level
    off = max(0.0, period - on)
    leak_off = (p["field"]["leak_logic"] * PG["logic_residual"] + p["field"]["leak_rom"] * PG["rom_residual"]
                + p["hub"]["leak_logic"] * PG["logic_residual"] + p["hub"]["leak_sram"] * PG["sram_sleep_residual"])
    io_off = p["hbm_if"] * PG["hbm_if_residual"] + (p["serdes"] + p["ucie"]) * PG["serdes_lpi_residual"]
    serdes_on = min(period, window + PG["serdes_wake_s"])
    e_io = p["hbm_if"] * on + p["hbm_if"] * PG["hbm_if_residual"] * off \
        + (p["serdes"] + p["ucie"]) * (serdes_on + PG["serdes_lpi_residual"] * (period - serdes_on))
    e_clk -= clk_r * off                      # a power-gated stage has no clock at all
    return e_clk + leak * on + leak_off * off + leak * PG["stage_bet_s"] + e_io


POLICIES = ("ungated", "stage clock gating", "+ region clock gating", "+ stage power gating (retention)")


def v41_static_power(ec=None):
    """V4.1 ROM array static energy per token under the four policies, at batch 1 (AR and MTP m = 1) and at
    saturation, with the wake-up schedule check (no wake may land on the single-user token path)."""
    ec = ec or economics()
    v = ec["v41_rom"]
    d = copy.deepcopy(PRESETS["proposal"])
    p = v41_die_static_parts(d)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    ungated_die = sum(p["field"].values()) + sum(p["hub"].values()) + p["hbm_if"] + p["serdes"] + p["ucie"]
    assert abs(ungated_die * V41_ROM_SYSTEM["layer_dies"] / v["energy"]["static_w"]["layer_dies"] - 1) < 0.005
    table_leak = rack["per_die"]["table_leakage_w"]
    table_other = rack["per_die"]["table_static_w"] - table_leak
    head_w = rack["static"]["head_dies"] / V41_ROM_SYSTEM["head_dies"]
    out = {}
    for mode, P in (("ar", 1), ("mtp_m1", V41_POSITIONS)):
        _, g = _v41_graph(d, P)
        win, start, T = _stage_windows(g)
        busy = _region_busy(g)
        if P > 1:                                   # the MTP step adds the draft on the head dies
            Td = v41_rom_draft_s(v["ar"]["rows"][0]["per_user_ms_per_token"] * 1e-3)
            win[V41_STAGES] += Td
            T += Td
        tau = V41_TAU if P > 1 else 1.0
        dyn = (v["energy"]["mtp_dynamic_mJ_per_token"] if P > 1 else
               v["energy"]["dynamic_mJ_per_token_die"] + v["energy"]["stack_mJ_per_token"]) * 1e-3
        occ = dict(v41_rom_ledger(g)["stage_occupancy_s"])
        if P > 1:
            occ[max(occ)] += Td
        per_sat = max(occ.values())
        res = {}
        for label, wake in (("wake_1us", PG["stage_wake_s"]), ("wake_c6_133us", PG["stage_wake_s_c6"])):
            pts = {}
            for point, period, act in (("batch1", T, win), ("saturated", per_sat, occ)):
                rows = []
                for pol in range(4):
                    e_layer = e_head = e_tab = 0.0
                    gated = 0
                    for s in range(V41_STAGES + 1):
                        w = act.get(s, 0.0)
                        b = busy.get(s, dict(field=w, hub=w))
                        ok = period - w >= wake + PG["stage_bet_s"]
                        gated += bool(ok and pol == 3)
                        e = _die_energy(p, period, w, b, pol, wake, ok)
                        if s < V41_STAGES:
                            e_layer += V41_TP * e
                        else:                       # head dies: the rack's static, scaled by the layer-die policy ratio
                            e_head += V41_ROM_SYSTEM["head_dies"] * head_w * period * e / (ungated_die * period)
                    # Engram table dies: ROM tables, no state; active for the gathers (L1, L14) + wake, else gated
                    tw = 2 * 0.5e-6 * (P if point == "saturated" else 1)
                    t_on = min(period, tw + wake) if pol == 3 else period
                    e_tab = V41_ROM_SYSTEM["table_dies"] * (
                        table_other * period + table_leak * (t_on + PG["logic_residual"] * (period - t_on)))
                    e_static = e_layer + e_head + e_tab
                    rate_tokens = tau / period
                    rows.append(dict(policy=POLICIES[pol], static_mJ_per_token=round(e_static / tau * 1e3, 2),
                                     energy_mJ_per_token=round((e_static / tau + dyn) * 1e3, 2),
                                     static_w=round(e_static / period, 0), stages_power_gated=gated,
                                     tokens_s=round(rate_tokens, 1)))
                pts[point] = rows
            # the wake schedule: every stage is woken `wake` before its window opens.  At batch 1 the schedule is
            # static and periodic, so a wake never lands on the token path while wake + BET <= the stage's idle
            idle_min = min(T - w for s, w in win.items())
            pts["wake_on_token_path_us"] = 0.0 if idle_min >= wake + PG["stage_bet_s"] else round((wake + PG["stage_bet_s"] - idle_min) * 1e6, 2)
            pts["min_idle_batch1_us"] = round(idle_min * 1e6, 2)
            pts["serdes_prewake_fits"] = bool(idle_min >= PG["serdes_wake_s"])
            res[label] = pts
        out[mode] = dict(period_batch1_us=round(T * 1e6, 2), period_saturated_us=round(per_sat * 1e6, 3),
                         dynamic_mJ_per_token=round(dyn * 1e3, 3),
                         window_us={str(k): round(x * 1e6, 2) for k, x in sorted(win.items())},
                         start_us={str(k): round(x * 1e6, 2) for k, x in sorted(start.items())}, **res)
    return dict(policies=POLICIES, constants=PG, die_static_w={k: (round(x, 3) if not isinstance(x, dict) else
                                                                {kk: round(vv, 3) for kk, vv in x.items()})
                                                            for k, x in p.items()},
                basis="per layer die: ROM field clock and leakage MEASURED per pair (PAIR_W, W18: 7,102 placed pairs; "
                      "region clock gating = the per-pair ICG, charged for the pair-weighted busy time); hub (dedicated "
                      "units + VM ports) clock and leakage from its area, UNCALIBRATED; HBM interface idle, always-on SerDes and UCIe from "
                      "results/arch/v41_rack.json; head dies at the rack's static scaled by the layer-die policy "
                      "ratio; Engram table dies at the rack's leakage, gated outside their gathers; dynamic "
                      "energy unchanged from the economics section", **out)


def adaptive_mtp(ec=None):
    """MTP while it gives the larger aggregate (few users), AR beyond: the per-batch best of the two curves."""
    ec = ec or economics()
    out = {}
    for key, ar, mtp in (("v41_rom", ec["v41_rom"]["ar"]["rows"], ec["v41_rom"]["mtp_m1"]["rows"]),
                         ("v41_hbm", ec["v41_hbm"]["ar"]["rows"], ec["v41_hbm"]["mtp"]["rows"])):
        A_ = {r["batch"]: r for r in ar}
        M_ = {r["batch"]: r for r in mtp}
        rows = []
        for B in sorted(A_):
            a, m = A_[B], M_[B]
            pick, mode = (m, "MTP") if m["aggregate_tokens_s"] > a["aggregate_tokens_s"] else (a, "AR")
            rows.append(dict(batch=B, mode=mode, per_user_tokens_s=pick["per_user_tokens_s"],
                             aggregate_tokens_s=pick["aggregate_tokens_s"],
                             per_user_ms_per_token=pick["per_user_ms_per_token"],
                             energy_mJ_per_token=pick["energy_mJ_per_token"],
                             ar_aggregate_tokens_s=a["aggregate_tokens_s"], mtp_aggregate_tokens_s=m["aggregate_tokens_s"]))
        # the exact switch: MTP's aggregate B x r_mtp (until it saturates) against AR's B x r_ar
        r_ar, s_ar = ar[0]["per_user_tokens_s"], max(r["aggregate_tokens_s"] for r in ar)
        r_m, s_m = mtp[0]["per_user_tokens_s"], max(r["aggregate_tokens_s"] for r in mtp)
        # AR's per-user rate is flat until its own saturation on the ROM array, so the crossing is exact there
        # (B x r_ar = MTP's saturated aggregate); where AR's per-user rate falls with batch (the HBM chain) the
        # sweep brackets it
        flat = all(abs(r["per_user_tokens_s"] - r_ar) < 0.5 for r in ar if r["batch"] * r_ar <= s_m)
        switch = s_m / r_ar if (s_m < s_ar and flat) else None
        first_ar = next((r["batch"] for r in rows if r["mode"] == "AR"), None)
        prev = max([r["batch"] for r in rows if first_ar and r["batch"] < first_ar], default=None)
        out[key] = dict(rows=rows, switch_users=round(switch, 2) if switch else None,
                        switch_bracket=[prev, first_ar],
                        rule="MTP while batch < switch_users, AR at and above it", ar_b1=r_ar, mtp_b1=r_m,
                        ar_saturated=s_ar, mtp_saturated=s_m)
    return out


MASK = dict(
    full_set_usd=COST["mask_set_usd"],
    single_mask_usd=(0.5e6, 1.0e6),   # a single EUV mask $0.5-1M (SemiEngineering, "Mask Complexity, Cost, And Change";
                                      # siliconmasters.co 2025 guide); a coding via/metal layer at the lower metals is EUV
    coding_masks_per_die=(1, 2),      # Taalas HC1: a model changes TWO metal masks (EE Times, "Taalas Specializes to
                                      # Extremes for Extraordinary Token Speed"); one via mask is the lower bound
    v41_base_designs=3,               # layer, head (+DSpark), Engram table dies: each a shared base mask set
    qwen_base_designs=1,              # both Qwen dies share one base
)


def rom_mask_sensitivity(ec=None):
    """ROM mask NRE and V4.1 / Qwen ROM $ per tok/s under via-programmable ROM: shared base masks per die role plus
    1-2 coding masks per distinct die, against the economics section's full-set and 10%-coding cases."""
    ec = ec or economics()
    c = {r["design"]: r for r in ec["cost"]}
    out = []
    for name, dies, bases in (("V4.1 ROM array (AR / MTP m = 1)", V41_ROM_SYSTEM["dies"], MASK["v41_base_designs"]),
                              ("Qwen ROM (AR, G = 6,144)", QWEN_ROM_PRODUCT["k"], MASK["qwen_base_designs"])):
        r = c[name]
        hw = r["hardware_usd_iso_package"]
        cases = [("full mask set per die (economics high)", dies * MASK["full_set_usd"], None),
                 ("10% of a set per die (economics low)", dies * MASK["full_set_usd"] * COST["rom_coding_fraction"], None)]
        for n in MASK["coding_masks_per_die"]:
            for pm in MASK["single_mask_usd"]:
                cases.append((f"via-programmable: {n} coding mask(s) x ${pm / 1e6:.1f}M per die + shared bases",
                              bases * MASK["full_set_usd"] + dies * n * pm, bases * MASK["full_set_usd"]))
        for label, nre, base in cases:
            per_sys = nre / COST["production_units"]
            per_sys_nb = (nre - base) / COST["production_units"] if base is not None else None
            tot = hw + per_sys
            out.append(dict(design=name, case=label, nre_usd=nre, nre_per_system_usd=round(per_sys),
                            capex_per_system_usd=round(tot),
                            usd_per_tokens_s_b1=round(tot / r["tokens_s_b1"], 2),
                            usd_per_tokens_s_saturated=round(tot / r["tokens_s_saturated"], 2),
                            usd_per_tokens_s_saturated_base_excluded=(round((hw + per_sys_nb) / r["tokens_s_saturated"], 2)
                                                                      if per_sys_nb is not None else None)))
    g = c["V4.1 8x B200 (tier 2, AR)"]
    return dict(rows=out, inputs=MASK, production_units=COST["production_units"],
                gpu_reference=dict(design=g["design"], usd_per_tokens_s_saturated=g["usd_per_tokens_s_saturated"]["low"],
                                   usd_per_tokens_s_at_slo=g["usd_per_tokens_s_at_slo"]["low"]),
                note="base_excluded: the shared base masks amortised over later models (a new model re-spins only the "
                     "coding masks)")


def economics_levers(ec=None, gated=True):
    ec = ec or economics()
    lv = dict(static_power=v41_static_power(ec), adaptive_mtp=adaptive_mtp(ec), rom_masks=rom_mask_sensitivity(ec))
    if gated:
        lv["gated_alike"] = gated_energy_table(ec, lv)
    return lv


LEVER_SOURCES = ECON_SOURCES


# ---------------------------------------------------------------------------------------------------------
# Gated alike (W14c; root 2026-09-29 fairness follow-up): the adopted gating policies (clock gating with the
# ICG residual; power gating of idle domains with the cited residuals; a wake scheduled from the static schedule
# only into idle gaps that fit wake + break-even, so no wake lands on the token path) applied to every design:
# the tier-3 HBM comparators (SMs, dedicated units, L2, HBM PHY, SerDes / UCIe) and the Qwen ROM package, beside
# the V4.1 ROM array's stage gating.  The same PG constants; GPU rows stay measured.
# ---------------------------------------------------------------------------------------------------------
CORE_WAKE = dict(wake=PG["stage_wake_s"], bet=PG["stage_bet_s"])          # SM array, dedicated units, lanes, SU, L2
LINK_WAKE = dict(wake=PG["serdes_wake_s"], bet=PG["stage_bet_s"])          # SerDes and UCIe low-power idle


def _hbm_wake(clock):
    return dict(wake=PG["hbm_wake_cycles"] / clock, bet=412 / clock)      # ReGate Table 3 (HBM ctrl + PHY)


def _domain(logic=0.0, rom=0.0, sram=0.0, io_w=0.0, io_res=None, clock=1e9, sram_retain=True, **wk):
    """A power domain's static parts from its area by class (uarch constants) plus interface power io_w."""
    cl = CLOCK_J_MM2 * clock
    leak = logic * LEAK["logic"] + rom * LEAK["rom_array"] + sram * LEAK["sram_array"]
    leak_off = (logic * LEAK["logic"] * PG["logic_residual"] + rom * LEAK["rom_array"] * PG["rom_residual"]
                + sram * LEAK["sram_array"] * (PG["sram_sleep_residual"] if sram_retain else PG["sram_off_residual"]))
    return dict(clock=cl * (logic + 0.15 * (rom + sram)), leak=leak, leak_off=leak_off, io=io_w,
                io_off=io_w * (PG["logic_residual"] if io_res is None else io_res), **wk)


def _domain_energy(dm, period, busy, gaps, policy):
    """Static energy of one domain over `period` with `busy` s active and the idle split into `gaps`.
    policy 0 ungated; 1 clock gating (ICG residual in idle); 2 + power gating of every gap >= wake + BET (the
    wake completes at the gap's end, so it never delays the next busy phase; overhead = static x BET)."""
    r = PG["cg_residual"]
    on = dm["leak"] + dm["io"]
    if policy == 0:
        return (dm["clock"] + on) * period
    e = (dm["clock"] + on) * busy
    for g in gaps:
        if policy == 2 and g >= dm["wake"] + dm["bet"]:
            off = g - dm["wake"]
            e += (r * dm["clock"] + on) * dm["wake"] + (dm["leak_off"] + dm["io_off"]) * off + on * dm["bet"]
        else:
            e += (r * dm["clock"] + on) * g
    return e


def _even_gaps(period, busy, n):
    idle = max(0.0, period - busy)
    return [idle / n] * n if n and idle > 0 else []


def _gaps_of(segs, dom, T):
    """Idle gaps of `dom` in an ordered segment list [(duration, {busy domains})] over one period T (the gap
    that wraps across the token boundary is one gap)."""
    gaps, cur, busy, first = [], 0.0, 0.0, None
    for dur, doms in segs:
        if dom in doms:
            if first is None:
                first = cur
            elif cur > 0:
                gaps.append(cur)
            busy += dur
            cur = 0.0
        else:
            cur += dur
    if first is None:
        return 0.0, [T]
    gaps.append(cur + first + max(0.0, T - sum(d for d, _ in segs)))
    return busy, [g for g in gaps if g > 0]


def v41_hbm_timeline(positions=1):
    """The V4.1 HBM chain (v41_hbm_chain, group-slot) as an ordered segment list: each matvec an SM op (+ its x
    fill and barrier; the HBM streams its weights), each dedicated-unit node its path time (+ the other
    positions' issue; an index scan also holds HBM), each collective its share of the fabric terms (SerDes)."""
    dv = hbm_gpu_design("v41")
    clock = dv["clock_hz"]
    _, b = arch_graph(1048576)
    g = b.g
    path = g.path(b.sink)
    bc = dv["barrier"]["boundary_cycles"] / clock
    ncoll = sum(1 for x in path if g.nodes[x]["kind"] in ("collective", "hop"))
    fb = v41_hbm_fabric_us(_HBM_SWITCH, _HBM_FEC)
    fab = sum(fb.values()) + fb["collective_bytes"] * (positions - 1)
    segs = []
    for x in path:
        nd = g.nodes[x]
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / V41_HBM_DIES
            t = sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], dv["drain_cycles"], True) / clock
            t += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock + bc
            segs.append((t, {"sm", "hbm", "l2"}))
        elif nd["kind"] in ("collective", "hop"):
            segs.append((fab * 1e-6 / ncoll, {"links", "l2"}))
        else:
            t = sum(g.contrib[x].values()) + (positions - 1) * nd.get("issue", 0.0)
            if x.endswith((".attn.scores", ".idx.topk_final")) or x == "argmax":
                t += bc
            segs.append((t, {"du", "hbm"} if x.endswith("idx.score") else {"du"}))
    return segs, clock, dv


def gated_energy_table(ec=None, lv=None):
    ec = ec or economics()
    lv = lv or economics_levers(ec, gated=False)
    import arch_budget_qwen3 as Q
    rows = []

    def add(design, point, tokens_s, dyn_J, parts):
        """parts: [(count, domain, period_s, busy_s, gaps)] for one period that emits tokens_s x period tokens."""
        out = dict(design=design, point=point, tokens_s=round(tokens_s, 1))
        for pol, name in ((0, "ungated"), (1, "clock_gated"), (2, "clock_and_power_gated")):
            e = sum(n * _domain_energy(dm, T, busy, gaps, pol) for n, dm, T, busy, gaps in parts)
            T0 = parts[0][2]
            out[f"{name}_static_w"] = round(e / T0, 1)
            out[f"{name}_mJ_per_token"] = round((e / (tokens_s * T0) + dyn_J) * 1e3, 2)
        rows.append(out)

    # ---- Qwen ROM package (2 dies): lanes + ROM + KV ring, stream unit, HBM PHY, UCIe ----
    qr = ec["qwen_rom"]
    qe, a = _qwen_rom_product()
    nq = QWEN_ROM_PRODUCT["k"]
    clock = qe["clock_hz"]
    ub = qe["unit_busy"]
    wl, kvb = _qwen_wl()
    grp = QWEN_ROM_PRODUCT["G"] * 18063.0 / 1e6
    dq = dict(lanes=_domain(logic=grp, rom=a["rom"], sram=a["sram"], clock=clock, **CORE_WAKE),
              su=_domain(logic=12.8, clock=clock, **CORE_WAKE),
              hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
              ucie=_domain(logic=10.0, clock=clock, **LINK_WAKE))
    tpx = Q.tp_exchanges(clock)
    ops = 5 * 36 + 1
    for point, T, tok in (("batch1", qe["cycles"] / clock, 1.0), ("saturated", 1 / qr["ar"]["saturated_tokens_s"], 1.0)):
        busy = dict(lanes=(ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]) / clock,
                    su=ub["stream"] / clock, hbm=min(T, kvb / nq / (4 * HBM_STACK_BPS)),
                    ucie=qe["exchange"]["token_cycles"] / clock)
        gaps = dict(lanes=ops, su=ops, hbm=36, ucie=tpx["exchanges"])
        dyn = qr["energy"]["dynamic_mJ_per_token"] * 1e-3
        add("Qwen ROM AR (G = 6,144)", point, tok / T, dyn,
            [(nq, dq[k], T, min(T, busy[k]), _even_gaps(T, min(T, busy[k]), gaps[k])) for k in dq])
    # ---- Qwen HBM tier 3 (2 dies): SMs, L2, HBM PHY, UCIe ----
    qh = ec["qwen_hbm"]
    dh = hbm_gpu_design("qwen")
    clock = dh["clock_hz"]
    sa, n = dh["sm_area"], dh["sm_count"]
    dm = dict(sm=_domain(logic=n * sa["logic_mm2"], sram=n * sa["sram_mm2"] , clock=clock, **CORE_WAKE),
              l2=_domain(sram=dh["l2"]["mm2"], clock=clock, **CORE_WAKE),
              hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
              ucie=_domain(logic=10.0, clock=clock, **LINK_WAKE))
    qops = qwen_hbm_ops(dh["element"], dh["barrier"]["boundary_cycles"], dh["drain_cycles"])
    ar_bytes = sum(b_ for b_, _ in qops)
    kv_die = kvb / 2
    w_die = ar_bytes - kv_die
    spec = {x["block"]: x for x in hbm_speculation_rows() if x["design"].startswith("qwen_hbm_dflash_b")}
    for mode, rws in (("AR", qh["ar"]["rows"]), ("DFlash", qh["dflash"]["rows"])):
        for point, r_ in (("batch1", rws[0]), ("saturated", _sat_batch(rws))):
            B, blk = r_["batch"], r_.get("block", 1)
            tau = r_.get("tau", 1.0)
            T = B * tau / r_["aggregate_tokens_s"]
            draft = spec[blk]["draft_bytes_per_die"] if mode == "DFlash" else 0.0
            passes = math.ceil(B * blk / dh["element"]["cols"])
            byt = passes * (w_die + draft) + B * kv_die
            busy = dict(sm=byt / (n * dh["element"]["ingest_Bpc"]) / clock, hbm=byt / dh["hbm_Bpc"] / clock,
                        l2=ops * dh["barrier"]["boundary_cycles"] / clock, ucie=Q.tp_exchanges(clock)["cycles"] / clock)
            gaps = dict(sm=ops, hbm=ops, l2=ops, ucie=Q.tp_exchanges(clock)["exchanges"])
            dyn = r_["energy_mJ_per_token"] * 1e-3 - qh["energy"]["static_w_total"] / r_["aggregate_tokens_s"]
            add(f"Qwen HBM tier 3 {mode}", point, r_["aggregate_tokens_s"], dyn,
                [(2, dm[k], T, min(T, busy[k]), _even_gaps(T, min(T, busy[k]), gaps[k])) for k in dm])
    # ---- V4.1 HBM tier 3 (96 dies): SMs, dedicated units, L2, HBM PHY, SerDes + UCIe ----
    vh = ec["v41_hbm"]
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    for mode, P, tau, rws in (("AR", 1, 1.0, vh["ar"]["rows"]), ("MTP", V41_POSITIONS, V41_TAU, vh["mtp"]["rows"])):
        segs, clock, dv = v41_hbm_timeline(P)
        sa = dv["sm_area"]
        dm = dict(sm=_domain(logic=dv["sm_count"] * sa["logic_mm2"], sram=dv["sm_count"] * sa["sram_mm2"], clock=clock,
                             **CORE_WAKE),
                  du=_domain(logic=dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL, clock=clock, **CORE_WAKE),
                  l2=_domain(sram=dv["l2"]["mm2"], clock=clock, **CORE_WAKE),
                  hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
                  links=_domain(io_w=rack["serdes_always_on"] + rack["ucie_idle"], io_res=PG["serdes_lpi_residual"],
                                clock=clock, **LINK_WAKE))
        Tseg = sum(d_ for d_, _ in segs)
        for point, r_ in (("batch1", rws[0]), ("saturated", _sat_batch(rws))):
            T = r_["batch"] * tau / r_["aggregate_tokens_s"]
            if point == "batch1":
                parts = [(V41_HBM_DIES, dm[k], T) + _gaps_of(segs, k, T) for k in dm]
            else:
                # one column pass per period, each domain's idle one contiguous gap (as the ROM's saturation rule)
                per = max(1, dv["element"]["cols"] // P)
                npass = math.ceil(r_["batch"] / per)
                Tp = T / npass
                frac = {k: _gaps_of(segs, k, Tseg)[0] / Tseg for k in dm}
                occ = vh["occupancy_us_per_pass"]
                sm_busy = min(Tp, frac["sm"] * Tseg)
                du_busy = min(Tp, per * P * occ["dedicated_issue_per_user"] * 1e-6)
                busy = dict(sm=sm_busy, du=du_busy, l2=min(Tp, frac["l2"] * Tseg), hbm=min(Tp, frac["hbm"] * Tseg),
                            links=min(Tp, frac["links"] * Tseg))
                parts = [(V41_HBM_DIES, dm[k], Tp, busy[k], _even_gaps(Tp, busy[k], 1)) for k in dm]
                T = Tp
            dyn = r_["energy_mJ_per_token"] * 1e-3 - vh["energy"]["static_w_total"] / r_["aggregate_tokens_s"]
            add(f"V4.1 HBM tier 3 {mode}", point, r_["aggregate_tokens_s"], dyn, parts)
    # ---- V4.1 ROM array: the adopted stage policies (economics_levers) ----
    sp = lv["static_power"]
    for mode, key in (("AR", "ar"), ("MTP m = 1", "mtp_m1")):
        for point in ("batch1", "saturated"):
            p_ = sp[key]["wake_1us"][point]
            summ = {x["design"]: x for x in ec["summary"]}[f"V4.1 ROM {mode}"]
            tok = summ["tokens_s_b1"] if point == "batch1" else summ["sat_aggregate_tokens_s"]
            rows.append(dict(design=f"V4.1 ROM {mode}", point=point, tokens_s=tok,
                             ungated_static_w=p_[0]["static_w"], ungated_mJ_per_token=p_[0]["energy_mJ_per_token"],
                             clock_gated_static_w=p_[2]["static_w"], clock_gated_mJ_per_token=p_[2]["energy_mJ_per_token"],
                             clock_and_power_gated_static_w=p_[3]["static_w"],
                             clock_and_power_gated_mJ_per_token=p_[3]["energy_mJ_per_token"]))
    # ---- GPUs: measured board power (whatever the GPU gates is already inside it) ----
    for name, blk, n_gpu in (("Qwen 1x B200 AR (tier 2)", ec["gpu"]["qwen"], 1), ("V4.1 8x B200 AR (tier 2)", ec["gpu"]["v41"], 8)):
        for point, r_ in (("batch1", blk["rows"][0]), ("saturated", _sat_batch(blk["rows"]))):
            e = r_["energy_mJ_per_token"]
            rows.append(dict(design=name, point=point, tokens_s=r_["aggregate_tokens_s"], ungated_mJ_per_token=e,
                             clock_gated_mJ_per_token=e, clock_and_power_gated_mJ_per_token=e,
                             measured=f"{n_gpu} x {B200_W_DECODE:.0f} W measured decode power"))
    return dict(rows=rows, policies=("ungated", "clock gated (ICG residual 10%)",
                                     "clock + power gated (cited residuals, wake only into gaps >= wake + BET)"),
                domains=dict(core=CORE_WAKE, links=LINK_WAKE, hbm="ReGate Table 3: 60-cycle wake, 412-cycle BET"),
                basis="per domain: clock and leakage from its area by class (technology.json via the uarch constants), "
                      "interface power (HBM idle, SerDes / UCIe); busy time and idle gaps from each design's own "
                      "schedule: the V4.1 HBM chain walked node by node; Qwen dies with their ops' gaps split evenly "
                      "(181 op boundaries, 36 KV streams, 73 UCIe exchanges); at saturation one contiguous idle gap "
                      "per pass or token, as the ROM array's rule")


# ---------------------------------------------------------------------------------------------------------
# Consolidation (W16; user-approved study 2026-09-30).  The physical floorplans leave spare area the analytical
# die ledger did not predict.  This section re-derives the V4.1 ROM die count from the placed field geometry, the
# Engram table dies from their own (strip-free) floorplan, right-sizes the GPU-organised HBM dies to their PHY
# shoreline, sweeps the V4.1 HBM comparator's die count, re-prices cost on die area with a yield model, and
# re-examines the comparison rule.  It calls the sections above and changes none of them.
#
# DENSITY RULE (root, 2026-09-30): the product die count is stated at the ANALYTICAL ROM density (75.0 Mbit/mm2,
# the envelope the ROM designs are built on; results/floorplan/v41_rom_capacity.json forbids substituting the
# predictive macro area).  The ASAP7 predictive macro (~150 Mbit/mm2 raw) is physical feasibility only, and ROMA's
# TSMC 7 nm compiler (57.8 Mbit/mm2) is the conservative case; both are sensitivities in every table.
# ---------------------------------------------------------------------------------------------------------
import contextlib  # noqa: E402

_V41_CFG = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())
_V41_ASM = json.loads((ROOT / "results/arch/v41_die_assembly.json").read_text())["ledger"]["layer"]
_V41_PLACE = json.loads((ROOT / "results/arch/v41_die_placement.json").read_text())

# The W10 layer-die re-fit, REPRODUCED here (the record is not committed): tools/v41_floorplan_refit.py at
# claude/w10-v41-rom-element 1f598e0b, --q-pair and --bf-pair both pair_final_physical_p5 (no placed BF16 pair
# exists: q2 stopped at detailed placement with 184 overlaps), hub from W11 proposal_w11_p6.  p5 is NOT closed.
CONS_REFIT = dict(
    slots=9931, used_pair_rows_busiest=7102,
    busiest_macros=dict(expert=13296, dense_qe=464, me=128, vm_constant=82, engram_spill=233),
    pair_footprint_mm2=416.76 / 7102,        # pair row = 2 ot_rom_8192x274_m8 + its 225.07 um MAC strip (485.136 x 120.96 um)
    strip_pitch_um=225.072, pair_pitch_um=485.136, rom_v_pitch_um=120.96,
    hub_mm2=75.878, edge_io_mm2=64.984, hbm_service_mm2=10.368, channels_mm2=13.701,
    whitespace_mm2=233.291, unused_slots_mm2=166.012, die_mm2=814.982,
    tool="tools/v41_floorplan_refit.py", tool_sha256="77d5ee466fa70ea447e3dc3a5a57459307d68afa3914515ac62493fc48cb663c",
    branch="claude/w10-v41-rom-element", commit="1f598e0b",
    element_pair=dict(record="results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json",
                      sha256="4ddaf275d54096663c6918776405dbd6ffdc21e576de9a00cb67323eba7b29c7",
                      fmax_hz=886002000.0, setup_wns_ns=-0.208666, drc=1, logic_utilisation=0.801, closed=False),
    committed=False,
    caveats=["the re-fit record is not committed: reproduced from the W10 branch (tool + p5 sha pinned here)",
             "p5 is not closed (886 MHz, WNS -209 ps, 1 DRC): a wider strip to close it lowers the slot count",
             "no placed BF16 pair exists (q2 failed at detailed placement): p5 stands in for the BF16 columns"])
CONS_FIELD_MM2 = CONS_REFIT["slots"] * CONS_REFIT["pair_footprint_mm2"]           # the ROM/MAC slot field, 582.8 mm2
# ROOT RULING 2026-10-01 (option a): the measured VM-H SU+VM block is the product's hub block -- 128 lane-group tiles
# (8 SU lanes + 12 ot_sram_1r1w_256x256 each), 38.95 mm2 at 6,365 x 6,119 um (claude/w11-vmh-land 3cc18731
# results/uarch/w11_vm_options.json options.H_rtl: footprint 38.951, SRAM 10.893, network footprint 2.624 mm2).  It
# replaces the dedicated-unit row's lane-only stream unit (14.249 mm2; W11: measured light lane 9,536 um2 cells, x2.3
# the ledger's 4,085).  The re-fit's hub partition SU_VECTOR is the stream unit x (1 + SWITCH_FRACTION 0.05,
# tools/v41_floorplan_refit.py), so the slot field gives up (38.951 - 14.249) x 1.05 = 25.9 mm2 on the 815 mm2 basis
# (dies are free: the stage fit grows instead of the die)
VMH_BLOCK = dict(block_mm2=38.951, w_um=6365.0, h_um=6119.5, sram_mm2=10.893, network_footprint_mm2=2.624,
                 stream_unit_ledger_mm2=14.249, switch_fraction=0.05, budget_mm2=45.0,
                 src="claude/w11-vmh-land 3cc18731 results/uarch/w11_vm_options.json options.H_rtl (root ruling "
                     "2026-10-01, option a; budget 38-45 mm2 with W11's measured lanes at 50% utilisation)")
VMH_BLOCK["field_loss_mm2"] = round((VMH_BLOCK["block_mm2"] - VMH_BLOCK["stream_unit_ledger_mm2"])
                                    * (1 + VMH_BLOCK["switch_fraction"]), 3)
VMH_BLOCK["option"] = "H_rtl"
# ROOT RULING 2026-10-01 (after the VM waterfall): W11's C_rotate is the PRODUCT's VM -- central: the lane array as a
# 4,890 um square with the VM strip (1,536 SRAM macros + VM logic + rotate/Benes network, 3,004 um deep) along one
# side; 38.60 mm2 (claude/w11-vmh-land 3cc18731 w11_vm_options.json options.C_rotate).  VM-H stays a REFERENCE row
VMC_BLOCK = dict(block_mm2=38.601, lane_array_mm2=23.913, lane_side_um=4890.1, vm_block_mm2=14.688, vm_depth_um=3003.7,
                 sram_mm2=10.893, network_footprint_mm2=2.274, stream_unit_ledger_mm2=14.249, switch_fraction=0.05,
                 option="C_rotate",
                 src="claude/w11-vmh-land 3cc18731 results/uarch/w11_vm_options.json options.C_rotate (root ruling "
                     "2026-10-01: the product's VM)")
VMC_BLOCK["field_loss_mm2"] = round((VMC_BLOCK["block_mm2"] - VMC_BLOCK["stream_unit_ledger_mm2"])
                                    * (1 + VMC_BLOCK["switch_fraction"]), 3)
CONS_SLIVER_MM2 = CONS_REFIT["whitespace_mm2"] - CONS_REFIT["unused_slots_mm2"]   # whitespace outside the field
# Where that whitespace is (measured on the reproduced re-fit's rectangles): the die-edge ring outside the core
# (1.02-1.09 mm wide: die 814.98 - core 696.56 = 118.43 mm2) less the edge I/O instances in it (HBM PHYs, SerDes,
# UCIe: 64.90 mm2, all in the ring) = 53.52 mm2; and gaps inside the core (core - slot field - hub - HBM service -
# channels = 13.84 mm2: hub halos and field-edge fragments).  Neither is ROM field: no whole macro column fits the
# ~1 mm ring beside the PHYs, and the core gaps are halos.  They can hold only the NON-distributed overhead (I/O and
# ESD, PLLs, seal ring, edge decap); clock buffers, DFT/MBIST and field decap are distributed over the field.
CONS_GEOM = dict(
    w10_refit=dict(field_mm2=CONS_FIELD_MM2, ring_free_mm2=118.426 - 64.902, core_gap_mm2=13.84,
                   src="W10 re-fit reproduced (claude/w10-v41-rom-element 1f598e0b), v1 HBM PHY 12.0 x 0.833 mm"),
    w10_refit_vmh=dict(field_mm2=CONS_FIELD_MM2 - VMH_BLOCK["field_loss_mm2"], ring_free_mm2=118.426 - 64.902,
                       core_gap_mm2=13.84,
                       src="the W10 re-fit with the measured VM-H SU+VM block as the SU_VECTOR hub partition (root "
                           "ruling 2026-10-01): the field less (38.951 - 14.249) x 1.05 mm2"),
    w10_refit_crot=dict(field_mm2=CONS_FIELD_MM2 - VMC_BLOCK["field_loss_mm2"], ring_free_mm2=118.426 - 64.902,
                        core_gap_mm2=13.84,
                        src="the W10 re-fit with W11's C_rotate SU+VM block as the SU_VECTOR hub partition (root "
                            "ruling 2026-10-01, the product): the field less (38.601 - 14.249) x 1.05 mm2"),
    w18_legal_phy=dict(field_mm2=9637 * CONS_REFIT["pair_footprint_mm2"], ring_free_mm2=138.836 - 65.001,
                       core_gap_mm2=13.72,
                       src="claude/w18-die-assembly 4f9de5b5 results/floorplan/v41_pack_refit_w18_e8p5.json (sha256 "
                           "472e9f5e9ba4a462b9042ec19d7048fd33cbc64623e2640f3c66cc3e1077afbb): the legal 8.5 mm PHY "
                           "abstract is taller, so 185 ROM rows and 9,637 slots; not on main"),
)
# ROOT RULING 2026-09-30: ring-only credit (the core halo gaps are not field; distributed overhead comes out of the
# field); the conservative case gives no credit
CONS_CREDIT = dict(ring=("ring_free_mm2",), none=())
# Element-pair pitch.  w10_budget: root's hard budget for W10's closed pair (485 x 121 um, abutment pins, no
# channel), the pack's pitch.  w18_measured: W18's tiling of the W10 p5 abstract with an 8.64 um pin channel under
# every row (claude/w18-die-assembly d1e3c0aa, results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json
# sha256 2218b6efbff9cf7bba5d7984014352f3d26ffdf75a8a481b33706cf7f5cd3f04, tiling die_floorplan_ch8.64:
# 522.72 x 140.40 um = +7.75% x +16.07%, area x 1.2507; ch4.32 x 1.2122, ch17.28 x 1.3276).  p5 is not closed.
CONS_PITCH = dict(w10_budget=dict(q_um=(485.136, 120.96), src="root hard budget for W10 p9/q7 (the pack pitch)"),
                  w18_measured=dict(q_um=(522.72, 140.40), src="W18 d1e3c0aa pair_w10p5_abstract.json tiling ch8.64"),
                  w10_q_1p2=dict(q_um=(476.0, 126.9), src="W10 (2026-09-30): the q pair at 1.2 GHz, 4096m8 ping-pong, WC "
                                                          "floorplan cells 21.9k um2 at 85% logic utilisation"),
                  w10b_q=dict(q_um=(510.84, 126.9), src="W10b (2026-10-01): the q pair widened 7.3% after p12q3/p12qm63 "
                                                        "failed CTS legalisation at 91-93% strip utilisation; p12q4 "
                                                        "routes at this fixed --die-area (closure pending)",
                              bf16_outline_um=(1002.89, 142.56)),
                  w10_iii_1p2=dict(q_um=(574.0, 126.9), src="W10 (2026-09-30): the BF16_PAIR (iii) pair at 1.2 GHz, 32.3k "
                                                            "um2 cells (+20.7% tile)"))
# ROOT RULING 2026-09-30: the 1,024 BF16-capable pairs (2,048 BF16 macros) sit in their own columns at a 1,019 um
# pitch (the BF16 element strip), at the row pitch of the variant
CONS_BF16 = dict(
    pairs=1024,
    columns_outline_um=(1063.7, 131.76),   # W10's planned outline: the named steps before the W10b re-fit
    columns_outline_w10b_um=(1002.89, 142.56),   # W10b (2026-10-01): c4/c5 route at this fixed --die-area, density
                                                 # 0.5 (BF16 split 8x4 + 8x4, still 5 cycles); the product's outline
    columns_src="W10 (root relay 2026-09-30): the BF16 pair's PLANNED outline, 1,063.7 x 131.76 um = 0.1402 mm2 "
                "(four 12 um capture channels + margins), until q7 confirms; the earlier 1,019 um x row pitch is "
                "superseded",
    standard_pair_src="W10 (ab1146e5, 2026-09-30), ADOPTED by root: BF16 on the standard FP8/FP4 pair at the budget "
                      "pitch -- 16 BF16 weights a word read once per 8 cycles into 2 exact BF16 multipliers per "
                      "macro and the existing chain adders; exact (golden csum order unchanged); ~+1.1-1.3 k um2 "
                      "per pair (+5-6% of p8's 20.3 k, 85-87% utilisation: a closure risk); only wo_a slows, "
                      "~+48 cycles a layer (~-1% tok/s); not built",
    standard_pair_wo_a_extra_cycles=48,
    # ROOT DECISION 2026-09-30: option (ii) ADOPTED -- q pairs + 2 exact BF16 multipliers a macro, word cap (cap 2 was
    # +250 um2 a macro, +3.45 mm2 a die); W10 measured the BF16 ops at L = 8: wo_a 256 -> 384, cmp.wk 64 -> 128,
    # router 80 -> 128 cycles (busiest die 3,585 tok/s against 3,760 on columns)
    option_ii_extra_cycles={"wo_a": 128, "cmp.wk": 64, "router": 48}, option_ii_area_mm2=16.0,
    # USER DECISION 2026-09-30: maximum per-user rate, die count not a constraint -> option (iii) is the PRODUCT:
    # 4 BF16 multipliers a macro, 4-cycle hold, 4 chains at NCH = 24, W10's measured 574 x 126.9 um tile (every pair);
    # W10's per-op issue for the BF16 ops (cycles, busiest die): wo_a 192, cmp.wk 64, router 80, a_proj 160
    option_iii_issue_cycles={"wo_a": 192, "cmp.wk": 64, "router": 80, "a_proj": 160},
    # ROOT 2026-09-30 (update): option (ii) becomes cap 3 / NCH = 24 (cap 2 cannot place wo_a): busiest die 3,503 tok/s
    # (W10), ~+16 mm2 a die routed (ESTIMATE; W10 p12 measures it); the op cycles above are cap 2's, pending p12
)
BF16_MODES = ("standard_pair", "columns")
# ROM macro depth (W10 study, claude/w10-v41-rom-element c673fd43, results/uarch/v41_rom_depth_study.json): single-
# cycle SS limit and density per macro; element count unchanged (2 or 4 macros per element slot)
ROM_DEPTH_OPTS = {
    "8192m8": dict(ss_ghz=0.918, tt_ghz=1.14, mb_per_mm2=149.6, macros_per_slot=1, field_delta_mm2=0.0),
    "4096m8": dict(ss_ghz=1.206, tt_ghz=1.48, mb_per_mm2=142.4, macros_per_slot=2, field_delta_mm2=10.5),
    "2048m4": dict(ss_ghz=1.324, tt_ghz=1.654, mb_per_mm2=136.1, macros_per_slot=4, field_delta_mm2=20.52),
}
ROM_DEPTH_SRC = ("claude/w10-v41-rom-element c673fd43 results/uarch/v41_rom_depth_study.json (rom_gen analytical "
                 "compile, the shipped macro's calibrated generator); per-slot mux / select logic for 2-4 macros a slot "
                 "NOT included (W10 to state)")
SS_DERATE_MEASURED = 1.43   # W13 (root relay 2026-09-30): the TT-closed tc16 FP32 column re-timed at SS on its routed odb,
                            # setup -398 ps -> 759 MHz; pessimistic for logic re-hardened at WC
# W15 (root relay 2026-09-30): measured SS wire reach, period = 261 ps + 1.135 ps/um x L (routed 547-bit spans, SS setup,
# FF hold, 60/25): 504 um a stage at 0.833 ns, 748 um at 1.111 ns (the 1,118 um TT fit it replaces)
SS_REACH_UM = {1.2e9: 504.0, 0.9e9: 748.0}
MTP_KV_PER_POSITION = True    # W11 / root 2026-09-30: verify KV rows are per position (6 x 645 rows a pass), not shared
W15_V41_COLL_STAGES_SS = 48      # W18b MEASURED (claude/w18-die-assembly b359e69e die_route_layer_split.json): collective
                                 # -> farthest SerDes 48 stages at the SS reach (UCIe 37); the v41p17 fit carries 17
W18B_EXPERT_WIRE = 36 + 40       # W18b measured, M8/M9 trunks: VM x root -> farthest cluster 36 + farthest cluster -> VM
                                 # 40 (PLACEHOLDER cycles until W15's M8/M9-only reach lands; the routed lengths stand)
W11_SERIAL_MUL_EXTRA = 1         # W11 3bc74342: a LAT-3 mul misses 0.9 GHz by 17 ps -> LAT 4, +1 cycle a multiply in the
                                 # SU/SFU/softplus/Sinkhorn chains; priced as +1 slow cycle a chain node (a LOWER BOUND:
                                 # the per-node multiply count is not in the graph)
# W11 MEASURED serial build (claude/w11-suclose ddd2f725, results/physical_abi3/asap7/hdc/v41x/w11_serial/summary.json;
# root 2026-09-30): the SU light lane CLOSES at 1.111 ns SS / FF hold, 60/25 (929 MHz, sc_l5) with MLAT 5 (input-cut
# multiply) and ALAT 4.  Measured depths before -> after, in 0.9 GHz cycles: linear op 21 -> 30, exp 49 -> 71,
# sigmoid/silu 71 -> 94, rsqrt 37 -> 58, sqrt(softplus) 162 -> 216, Engram gate 104 -> 127, divide 19 -> 19, reducer
# tap 26 -> 35 and 3 -> 4 a tree/time level.  Folded as these added slow cycles on the serial-chain nodes IN PLACE OF
# the W11_SERIAL_MUL_EXTRA lower bound (the measured build already carries the slower multiply); the Sinkhorn unit
# itself is not in the serial build, so it keeps the +1 lower bound, and its SFU front (row max + exp) takes the exp
# delta.
W11_SERIAL_MEASURED = dict(linear=9, exp=22, sigmoid=23, silu=23, rsqrt=21, softplus=54, gate=23, div=0,
                           reduce_tap=9, reduce_per_level=1, sinkhorn_front_exp=22, sinkhorn_unit=W11_SERIAL_MUL_EXTRA,
                           light_lane_ss_mhz=929.0, period_ns=1.111, mlat=5, alat=4,
                           src="claude/w11-suclose ddd2f725 results/physical_abi3/asap7/hdc/v41x/w11_serial/summary.json "
                               "(depths.serial_build, added_cycles; sc_l5 pass)")


def _w11_serial_cycles(name, nd, levels):
    """Added 0.9 GHz cycles of one serial-chain node under W11's measured serial build."""
    m = W11_SERIAL_MEASURED
    if nd["kind"] == "sinkhorn":
        return m["sinkhorn_front_exp"] + m["sinkhorn_unit"]
    if nd["kind"] == "reduce":
        return m["reduce_tap"] + m["reduce_per_level"] * levels.get(name, 0)
    leaf = name.split(".")[-1]
    if leaf == "gate" and name.startswith("E"):
        return m["gate"]
    fn = A.SFU_NODE.get(leaf)
    if fn:
        return m[fn]
    return m["rsqrt"] if leaf == "rsqrt" else m["linear"]


# ROOT RULING 2026-09-30 (die size): the layer die is still sized by the old pack (815 mm2, 7,628 pair slots; W18b
# 510f376e die_assembly.json), while the product owner file needs 5,289 pairs a die (1,024 BF16 columns;
# results/arch/v41_stage_owner_product.json, max pairs_per_die_by_stage).  Shrink to 5,289 + ~10% margin; W18b
# floorplans it.  Until its crossings land, a SENSITIVITY row scales every on-die crossing by sqrt(area ratio).
DIE_SHRINK = dict(slots_now=7628, pairs_needed=5289, margin=0.10,
                  src="root ruling 2026-09-30; W18b claude/w18-die-assembly 510f376e; v41_stage_owner_product.json")
DIE_SHRINK["area_ratio"] = DIE_SHRINK["pairs_needed"] * (1 + DIE_SHRINK["margin"]) / DIE_SHRINK["slots_now"]
DIE_SHRINK["crossing_scale"] = math.sqrt(DIE_SHRINK["area_ratio"])
PRODUCT_SERIAL = "w11_measured"
SERIAL_TAG = ("ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, "
              "light lane 929 MHz)")
# W18b INTERIM shrunk layer die (claude/w18-die-assembly 996f7982, results/physical_abi3/asap7/chip/v41_w18/
# shrink_p5_interim/shrunk_die.json, crossings_layer_split; root die-size ruling): 28.82 x 23.22 mm = 669 mm2 (linear
# scale 0.9062), 5,968 pair + 1,160 BF16 slots, 0 overflow.  Crossings at 504 um/stage: VM x root -> farthest cluster
# 30 (was 36), farthest cluster -> VM 33 (40), collective -> SerDes 45 (48), -> UCIe 34 (37); HBM window 25, index
# keys 39, top-k 38, selected KV 24 (not separately priced in the graph).  The field broadcast/return regions take
# the die's linear scale.  Die area, cost and power stay on the 815 mm2 ledger until the p12 floorplan lands.
DIE_OLD = dict(expert_wire=W18B_EXPERT_WIRE, coll_stages=W15_V41_COLL_STAGES_SS, field_scale=1.0,
               ucie_stages=37, serdes_stages=48)
DIE_SHRUNK_INTERIM = dict(expert_wire=30 + 33, coll_stages=45, field_scale=0.9062, mm2=669.255, pair_slots=5968,
                          bf16_slots=1160, ucie_stages=34, serdes_stages=45,
                          src="claude/w18-die-assembly 996f7982 shrink_p5_interim/shrunk_die.json")

# Routed endpoint lengths, converted at the SS 504 um/stage reach. This is a
# geometry/stage constraint, not a new SS/FF closure or a measured 83 ns link.
HUB_EDGE_WIRE_SOURCE = dict(
    revision="996f7982ce92a534e54722867ef8bba56b2cf417",
    path="results/physical_abi3/asap7/chip/v41_w18/shrink_p5_interim/shrunk_die.json",
    sha256="87e4170066f87d0532672a06bbc67621543017c326f8d1f4a3e119f79848c94c")
UCIE_LEGACY_ONDIE_S = 1.5e-9  # technology.json's 10 ns hop includes this proxy


def hub_edge_hop_wire_s(hop, clock, die=None, ucie_fanout=False):
    """Replace the embedded routing proxy with BOTH routed endpoint paths.

    Board paths pay SerDes endpoints; package paths pay UCIe endpoints. Board
    transit/serialization stays in ArrayFabric. No intermediate hub is assumed.
    Field trees and measured collective wires are separately priced already.
    """
    dv = die or DIE_OLD
    package = hop["link"] == "UCIe"
    stages = dv["ucie_stages" if package else "serdes_stages"]
    if clock <= 0 or stages <= 0:
        raise ValueError("positive endpoint wire stages and clock required")
    proxy = UCIE_LEGACY_ONDIE_S if package or ucie_fanout else 0.0
    return 2 * stages / clock - proxy
SHRINK_TAG = SERIAL_TAG + " + W18b shrunk-die interim crossings (669 mm2)"
# W11-stream (claude/w11-stream 540ef71c; record tool formulas at the shipped shape, idx_tail closed 1,249 MHz SS,
# chunk and tile routes PENDING): indexer key -> score 48 -> 100 (+52; chunk 39 -> 83, the tail's +8 is already in
# SOFTPLUS_FIX), attention tile input -> ov at TD 32 33 -> 72 (+39), engine bank guard 20 -> 44 (+24); W11 (answer,
# 2026-09-30): both are engine pipeline depths, paid once a scores pass AND once a p.v pass (the p.v pass reuses the
# tile after the softmax); throughput (II 1) unchanged
W11_STREAM_SS = {"suffix:idx.score": 52, "suffix:.attn.scores": 39 + 24, "suffix:.attn.pv": 39 + 24}
STREAM_TAG = SHRINK_TAG + " + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass)"
# W11 VM-H (claude/w11-vmh-land 3cc18731 results/uarch/w11_vm_options.json, option H_rtl; W11 answer 2026-10-01): the
# distributed VM's client stages replace VM_DIST one-for-one in SLOW (0.9 GHz) cycles at 748 um/stage -- x gather
# 6 -> 12, result scatter 6 -> 12, collective write 6 -> 12 -- and every SU op pays the per-op network average of the
# full-shape L0 program (control broadcast 5 + hold, per-class network stages, result tree 8): +36.706 slow cycles a
# vector op, +44.909 a reduction, issue x1.1687 (unpacked layout).  The graph's SU nodes carry no su_bcast / su_ret
# stages, so nothing is double counted; the CDC stays W18's FIFO.  Cross-check: die decode +5.0% vs flat (W11).
VMH = dict(x_gather=12, ret_scatter=12, coll_write=12, su_op_extra=36.706, su_red_extra=44.909, su_issue=1.1687,
           src="claude/w11-vmh-land 3cc18731 results/uarch/w11_vm_options.json (H_rtl)")
VMH_TAG = STREAM_TAG + " + W11 VM-H (12/12/12 slow stages, SU op +36.7 / red +44.9, issue x1.169)"
# W11 C_rotate (3cc18731 options.C_rotate design_keys): client stages 8/8/8 slow cycles; per SU op the control
# broadcast 5 + operand read 16 + element write 16 = 37, a reduction 5 + 16 + result tree 8 = 29; issue ratio 1.0
VMC = dict(x_gather=8, ret_scatter=8, coll_write=8, su_op_extra=37, su_red_extra=29, su_issue=1.0,
           src="claude/w11-vmh-land 3cc18731 results/uarch/w11_vm_options.json (C_rotate)")
PRODUCT_PITCH = "w10b_q"
VMH_REF_GEOM = "w10_refit_vmh"   # the measured VM-H block (reference row)
PRODUCT_GEOM = "w10_refit_crot"  # ROOT RULING 2026-10-01: W11's C_rotate SU+VM block in the hub (the product)
PRODUCT_HUB = VMC_BLOCK
W10B_TAG = "W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um)"
VMH_REF_TAG = (VMH_TAG + f" + {W10B_TAG} and the VM-H hub block (SU+VM 38.95 mm2): one stage re-fit -- REFERENCE "
               "(measured VM-H)")
CROT_SQ_TAG = (STREAM_TAG + f" + W11 C_rotate VM, square layout (8/8/8 slow stages, SU op +37 / red +29, issue x1.0) + "
               f"{W10B_TAG} and the C_rotate hub block (SU+VM 38.60 mm2) -- SUPERSEDED (unplaced geometry)")
# ROOT RULING 2026-10-01 (after the head-to-head): C_rotate stays (no issue penalty; it wins the saturated rate), priced
# on W18b's PLACED compact hub at 748 um a stage: +42 an op / +32 a reduction (W11 claude/w11-crot provisional)
CROT_TAG = (STREAM_TAG + f" + W11 C_rotate VM on W18b's compact hub (x 8 / scatter 7 / collective 13 slow stages, SU op "
            f"+42 / red +32, issue x1.0) + {W10B_TAG} and the C_rotate hub block (SU+VM 38.60 mm2): one stage re-fit")
# USER RULE (AGENTS.md a6e86359) / ROOT RULING 2026-10-01: lane-local operator fusion is a named product step, the
# conservative mode the headline and the optimistic mode its bound; "modelled; RTL pending" until W11 / W12b measure it
FUSION_LABEL = "modelled; RTL pending"
# ROOT RULING 2026-10-01: W18b's PLUS-shaped hub (claude/w18-die-assembly dfce8d40: a 3.93 mm central bank square,
# four 1.6 mm lane arms; worst bank -> lane 9,058 um) at W11's square-hub stages (claude/w11-crot 57318ff3,
# --stage-set square_hub, 748 um a stage): LEAD 6 / read 16 / write 15 / result 6 -> +37 an op, +28 a reduction; the
# index top-k crossing +1 cycle on the plus die (38 vs 37); the strip (42 / 32) stays a reference row
PLUS_TAG = (STREAM_TAG + f" + W11 C_rotate VM on W18b's plus hub (SU op +37 / red +28, issue x1.0; index top-k +1) + "
            f"{W10B_TAG} and the C_rotate hub block (SU+VM 38.60 mm2): one stage re-fit")
PRODUCT_TAG = PLUS_TAG + f" + lane-local operator fusion on W11's fused families (conservative; {FUSION_LABEL})"
FUSED_OPT_TAG = PLUS_TAG + f" + lane-local operator fusion on W11's fused families, optimistic (BOUND; {FUSION_LABEL})"
CROT_FUSED_TAG = CROT_TAG + f" + lane-local operator fusion on W11's fused families (conservative; {FUSION_LABEL})"
PLUS_LAT = {"suffix:idx.topk_merge": 1}
QWEN_W12_TP4_ME_EXTRA_SS = 41 + 5 * 5 + 38 + 1 + 7   # W12 c6e6b845 at the 504 um reach: 112 cycles an ME op
PRODUCT_CLOCK_HZ = 1.2e9   # USER DECISION (AGENTS.md e7479589): 0.833 ns at SS for all logic in all four designs
PRODUCT_DYN_SCALE = 1.16   # root 2026-09-30: dynamic energy about +16% at 1.2 GHz (ASSUMED: the voltage for the clock)
SS_CURVE_GHZ = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35)
SS_DERATE = 1.27     # USER DECISION 2026-09-30: sign-off at SS (setup) / FF (hold); logic without its own SS closure
                     # is derated by the ROM macro's SS/TT ratio (8192m8: 1.14 / 0.918 = 1.24; root: use 1.27)


def _cons_pair_mm2(pitch, bf16=False):
    x, y = CONS_PITCH[pitch]["q_um"]
    if bf16:
        # the BF16 column outline travels with the tile variant: W10b's pair carries its own measured column outline
        bx, by = CONS_PITCH[pitch].get("bf16_outline_um", CONS_BF16["columns_outline_um"])
        return bx * by / 1e6
    return x * y / 1e6
CONS_MACRO_MM2 = ROM_MACRO_UM2 / 1e6
CONS_STRIP_PER_PAIR_MM2 = CONS_REFIT["pair_footprint_mm2"] - 2 * CONS_MACRO_MM2    # MAC strip + gaps of one pair
CONS_TABLE_MACRO_MM2 = (CONS_REFIT["pair_pitch_um"] - CONS_REFIT["strip_pitch_um"]) * CONS_REFIT["rom_v_pitch_um"] / 2e6
CONS_TABLE_MACRO_B = 8192 * 33            # an Engram word: 264 payload bits of the 274-bit macro word (8 words a row)
CONS = dict(
    fill=0.90,                            # the study's slot fill (user instruction)
    overhead=0.125, overhead_band=(0.10, 0.15),
    overhead_basis=("per-die PDN bumps, IO/ESD, DFT, clock, decap not held by the floorplan.  On-chip decap alone "
                    "takes 'as much as 10%' of die area (M. Popovich, A. Mezhiba, E. Friedman, Power Distribution "
                    "Networks with On-Chip Decoupling Capacitors, Springer 2008) and 15-20% in high-performance "
                    "processors; technology.json floorplan.overhead_area_fraction is 0.10 (assumed, sweep "
                    "0.06-0.15).  ASSUMED 12.5%, band 10-15%.  The re-fit's edge slivers (whitespace outside the slot "
                    "field) hold it first ('partly holds'); the conservative case gives them no credit."),
    table_io_mm2=0.4 + 0.3888 * 1.043,    # 1 SerDes lane per table die (2 per table package, rack C4) at 0.4 mm2 +
                                          # one UCIe-A x64 module to its package peer
    table_logic_mm2=1.0,                  # ASSUMED: 24 gather slices + assembler (0.03 mm2 placed) + control, rounded up
)
# analytical: the layer-die ledger's mask-ROM area over its payload (checkpoint / 188, incl. SECDED 266/256)
CONS_A_ANALYTICAL = _V41_ASM["rom_mm2"] / (_V41_CFG["checkpoint_bytes"] / 188)
DENSITY = dict(
    analytical=dict(mm2_per_B=CONS_A_ANALYTICAL, mbit_mm2=round(_V41_ASM["rom_density_mbit_per_mm2"], 2),
                    basis="STORAGE-ONLY N5 (1 bit a mask-ROM cell): results/arch/v41_die_assembly.json ledger.layer, "
                          "N5 6T 0.021 um2 x ROMA's ROM/SRAM 0.33 / array efficiency 0.52, SECDED 266/256; the one "
                          "fit basis for both ROM designs (root ruling 2026-09-30).  Not HC1-derived: HC1 is a "
                          "cross-check only (4.31 MB/mm2 whole die)"),
    roma=dict(mm2_per_B=CONS_A_ANALYTICAL * _V41_ASM["rom_density_mbit_per_mm2"] / 57.8, mbit_mm2=57.8,
              basis="Wang et al., ROMA, ASP-DAC 2026 (TSMC 7 nm memory compiler, 8192x64: 57.8 Mbit/mm2; "
                    "technology.json rom entry): conservative sensitivity"),
    asap7=dict(mm2_per_B=None, mbit_mm2=round(8192 * 274 / ROM_MACRO_UM2, 1),
               basis="placed predictive ASAP7 ot_rom_8192x274_m8 macros of the integer macro map (physical "
                     "feasibility only; not substituted into the analytical total)"),
)


def _cons_nonexpert_macros():
    """Per-die non-expert macros (dense QE, ME, VM constants) of the integer macro map, and the expert macros."""
    mm = json.loads((ROOT / "results/floorplan/v41_die_macromap_expanded_woa.json").read_text())
    tot = {}
    for d in mm["layer_dies"]:
        for g_, v in d["macros_by_group"].items():
            tot[g_] = tot.get(g_, 0) + sum(v.values())
    return tot


def cons_stage_plan(S: int):
    """The 40 layers' ROM bytes laid out in layer order and cut into S equal-byte TP-4 stages (the placement rule of
    tools/v41_die_placement.py); a layer's fraction per stage, its start stage, and each stage's per-die macros
    (experts: 384 x 24 macros a layer a die; the non-expert macros spread over the layers by dense bytes)."""
    dense, routed = _V41_CFG["layer_dense_weight_bytes"], _V41_CFG["layer_routed_weight_bytes"]
    nl = len(dense)
    lay = [dense[L] + routed[L] for L in range(nl)]
    cap = sum(lay) / S
    tot = _cons_nonexpert_macros()
    nonexp = (tot["ROM_MAC.dense_QE"] + tot["ROM_MAC.ME"] + tot["VM.CONSTANT_HE"]) / 4
    exp_l = tot["ROM_MAC.expert"] / 4 / nl
    mac_l = [exp_l + nonexp * dense[L] / sum(dense) for L in range(nl)]
    frac, start, x = {}, {}, 0.0
    for L in range(nl):
        a, b = x, x + lay[L]
        s = int(a / cap + 1e-9)
        start[L] = min(s, S - 1)
        while a < b - 1e-6 and s < S:
            e = min(b, (s + 1) * cap)
            frac.setdefault(L, []).append((s, (e - a) / lay[L]))
            a, s = e, s + 1
        x = b
    macros = [0.0] * S
    for L, parts in frac.items():
        for s, f in parts:
            macros[s] += f * mac_l[L]
    return dict(S=S, frac=frac, start=start, macros_per_die=macros, busiest_macros=max(macros),
                payload_per_die_B=cap / 4, layers_per_stage=nl / S)


def _cons_busiest_macros(S):
    """Busiest layer die's macros at S stages, anchored to the re-fit's busiest die at 28 (layer macros, no spill)."""
    b = CONS_REFIT["busiest_macros"]
    anchor = b["expert"] + b["dense_qe"] + b["me"] + b["vm_constant"]
    return anchor * cons_stage_plan(S)["busiest_macros"] / cons_stage_plan(28)["busiest_macros"]


def _cons_need(pairs, payload_B, density, pitch, bf_pairs, depth="8192m8", extra_mm2=0.0):
    """ROM + element-strip area of `pairs` element pairs (bf_pairs of them BF16 column pairs) holding payload_B;
    `depth` scales the ROM area by the macro's density against the shipped 8192m8 (storage-only / ROMA: the array
    efficiency; ASAP7: the macro area)."""
    nq, nb = pairs - bf_pairs, bf_pairs
    fq, fb = _cons_pair_mm2(pitch), _cons_pair_mm2(pitch, True)
    dr = ROM_DEPTH_OPTS["8192m8"]["mb_per_mm2"] / ROM_DEPTH_OPTS[depth]["mb_per_mm2"]
    rom = (2 * pairs * CONS_MACRO_MM2 if density == "asap7" else payload_B * DENSITY[density]["mm2_per_B"])
    return rom * dr + nq * (fq - 2 * CONS_MACRO_MM2) + nb * (fb - 2 * CONS_MACRO_MM2) + extra_mm2


def cons_field_need_mm2(S, density, pitch="w10_budget", bf16="standard_pair", depth="8192m8"):
    """Slot-field area the busiest layer die needs at S stages: ASAP7 = its placed pair rows (FP8/FP4 pairs at the
    variant's pitch, the 1,024 BF16 pairs at 1,019 um); storage-only / ROMA = the payload at that density plus each
    pair's element strip (its footprint less its two ASAP7 macros; the element count is the read-width choice)."""
    pairs = _cons_busiest_macros(S) / 2
    return _cons_need(pairs, cons_stage_plan(S)["payload_per_die_B"], density, pitch,
                      CONS_BF16["pairs"] if bf16 == "columns" else 0, depth,
                      cons_bf16_hub_mm2(density) if bf16 == "hub_unit" else
                      CONS_BF16["option_ii_area_mm2"] if bf16 == "option_ii" else 0.0)


def cons_bf16_hub_mm2(density="analytical"):
    """Option (c) of root's BF16 lever: the BF16 weights (wo_a, router, a_proj's BF16 rows, cmp.wk: ~10.3 M a die,
    W10) in a small dedicated hub unit instead of the field -- BF16 MACs sized to keep wo_a at its 256-cycle issue
    (8.39 M products / 256 = 32,768 MACs at 509 um2, the closed mac_bf16_fp32_pipe_round_stage) plus their ROM at the
    density in shallow banks (1024x274 m8: 109.9 against 149.6 Mbit/mm2, ASSUMED to read 2,048 words a cycle)."""
    macs = 8.39e6 / 256 * 509e-6
    rom_b = 10.3e6 * 2
    dr = ROM_DEPTH_OPTS["8192m8"]["mb_per_mm2"] / 109.9
    rom = rom_b * 8 / 149.6e6 if density == "asap7" else rom_b * DENSITY[density]["mm2_per_B"]
    return macs + rom * dr


def cons_field_usable_mm2(overhead=None, credit="ring", geom="w10_refit"):
    """Usable slot field: the overhead reserve is charged to the credited whitespace first (ring: the die-edge ring
    outside the core, less its I/O instances; none), the rest to the field, then the fill factor."""
    o = CONS["overhead"] if overhead is None else overhead
    G = CONS_GEOM[geom]
    charge = max(0.0, o * FLOORPLAN["die_mm2"] - sum(G[k] for k in CONS_CREDIT[credit]))
    return CONS["fill"] * (G["field_mm2"] - charge)


def cons_min_stages(density, overhead=None, credit="ring", geom="w10_refit", pitch="w10_budget", bf16="standard_pair",
                    depth="8192m8"):
    u = cons_field_usable_mm2(overhead, credit, geom)
    return next(S for S in range(8, 90) if cons_field_need_mm2(S, density, pitch, bf16, depth) <= u)


def cons_head_dies(density, overhead=None, credit="ring", geom="w10_refit", pitch="w10_budget", depth="8192m8"):
    """The head group (lm_head, embedding, DSpark MTP; layer engines): TP-4 groups of the layer die's field."""
    b = _V41_PLACE["bytes"]
    per_die = (b["embed"] + b["head"] + b["mtp"]) / 4
    # the embedding is a row table (one row a token, no MACs): only lm_head and the drafter carry MAC strips
    m = (b["head"] + b["mtp"]) / 4 * _cons_busiest_macros(28) / cons_stage_plan(28)["payload_per_die_B"]
    need = _cons_need(m / 2, per_die, density, pitch, 0, depth)
    return 4 * math.ceil(need / cons_field_usable_mm2(overhead, credit, geom) - 1e-9)


def cons_head_need_ratio(pitch, overhead=None, credit="ring", geom="w10_refit", depth="8192m8"):
    """The head group's storage-only need against ONE TP-4 group of usable field (1 - this is the 4-die margin)."""
    b = _V41_PLACE["bytes"]
    per_die = (b["embed"] + b["head"] + b["mtp"]) / 4
    m = (b["head"] + b["mtp"]) / 4 * _cons_busiest_macros(28) / cons_stage_plan(28)["payload_per_die_B"]
    return _cons_need(m / 2, per_die, "analytical", pitch, 0, depth) / cons_field_usable_mm2(overhead, credit, geom)


def cons_table_dies(density, overhead=None):
    """Engram table dies: ROM, gather slices and links only (no MAC strips, hub, HBM); no floorplan exists, so the
    overhead gets no sliver credit and the layer die's channels are charged."""
    o = CONS["overhead"] if overhead is None else overhead
    usable = CONS["fill"] * (FLOORPLAN["die_mm2"] - CONS["table_io_mm2"] - CONS["table_logic_mm2"]
                             - CONS_REFIT["channels_mm2"] - o * FLOORPLAN["die_mm2"])
    cap = (usable / CONS_TABLE_MACRO_MM2 * CONS_TABLE_MACRO_B if density == "asap7"
           else usable / DENSITY[density]["mm2_per_B"])
    tb = _V41_PLACE["bytes"]["engram_table_L1"] + _V41_PLACE["bytes"]["engram_table_L14"]
    n = math.ceil(tb / cap)
    return dict(dies=n + (n % 2), usable_mm2=round(usable, 1), bytes_per_die=cap, table_bytes=tb)


def cons_engram_path(n_table, rates):
    """Engram gathers on fewer table dies: the switched path (rack record), rows per die, link load per package."""
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())
    p, tr = rack["paths"], rack["traffic"]["rows"]["T3_engram"]
    lane = rack["lanes"]["lane_net_Bps"]
    rows = 2 * A._env()["c"]["engram_hash_columns"]
    per_table = n_table // 2                                     # each Engram layer's table on half the dies
    maxrows = expected_max_load(rows // 2, per_table)
    pkgs = n_table // 2
    by_tok = tr["bytes_per_token"] - (72 + 4) * 16 + (n_table + 4) * 16    # token-id multicast to fewer dies
    out = dict(table_dies=n_table, table_packages=pkgs, rows_per_token=rows,
               expected_max_rows_per_die_per_layer=round(maxrows, 2),
               engram_l1_latency_us=round(p["engram_l1_s"] * 1e6, 3),
               engram_l1_slack_us=3.57, engram_l14_slack_us=round(p["engram_l14_slack_s"] * 1e6, 1),
               hops="unchanged: table package -> one 51.2T switch -> layer package (2 switched legs)",
               latency_basis="rack critical_paths: 2 switched legs + the 396 ns port read of all 48 rows at ONE port "
                             "(an upper bound for any table-die count) + serialisation into the consumer port",
               bytes_per_token=by_tok, link_Bps_per_package=2 * lane)
    for k, r in rates.items():
        load = r * by_tok / pkgs
        out[f"link_utilisation_{k}"] = round(load / (2 * lane), 4)
    return out


def cons_engram_slack(g):
    """Slack of each Engram delivery on the priced token DAG: the time its consumer's other input is ready minus the
    time the Engram value arrives (the DAG's E{L}.deliver hop: 2 board legs), and whether any Engram node is on the
    critical path.  The table-die count does not enter the DAG: the gather is token-addressed and prefetched."""
    fin = g.solve(True)
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    path = set(g.path(sink))
    out = {}
    for L in A._env()["c"]["engram_layer_ids"]:
        eng = f"E{L}.deliver" if f"E{L}.deliver" in g.nodes else f"E{L}.knorm"
        cons = f"L{L}.eng.dot"
        other = [x for x in g.nodes[cons]["deps"] if not x.startswith("E")]
        out[f"L{L}"] = dict(engram_ready_us=round(fin[eng] * 1e6, 3),
                            residual_ready_us=round(max(fin[x] for x in other) * 1e6, 3),
                            slack_us=round((max(fin[x] for x in other) - fin[eng]) * 1e6, 3),
                            on_critical_path=any(n.startswith(f"E{L}.") for n in path))
    return out


# ---- re-pricing the V4.1 ROM array at S stages: the arch DAG rebuilt with the packed placement at S groups ----
@contextlib.contextmanager
def _cons_stages(S):
    """Rebuild the arch DAG with the packed placement cut into S TP-4 groups: decode_critical_path.v41_machine is
    called with units = checkpoint x 4S / layer bytes (packed_placement's capacity rule), so every stage and
    substage hop moves to the new boundaries; no other node changes (tests/test_uarch_consolidation.py).  The arch
    cache is swapped for the duration and restored."""
    D_ = A.D
    orig = D_.v41_machine
    lt = sum(_V41_CFG["layer_dense_weight_bytes"]) + sum(_V41_CFG["layer_routed_weight_bytes"])
    units = _V41_CFG["checkpoint_bytes"] * 4 * S / lt

    def vm(*a, **k):
        if a and a[0] == "array" and "units" not in k:
            k["units"] = units
        return orig(*a, **k)
    saved = dict(_ARCH_CACHE)
    _ARCH_CACHE.clear()
    D_.v41_machine = vm
    try:
        yield units
    finally:
        D_.v41_machine = orig
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)


@contextlib.contextmanager
def _cons_clock(hz):
    """Price the V4.1 ROM at clock `hz`: the arch environment's clock (every cycle-counted node, wire stages at the
    new period) and the W15 V4.1 collective fits' clock (their measured cycles take hz's period: conservative for the
    link flight part).  Restored on exit."""
    if hz is None:
        yield None
        return
    E = A._env()
    old = (E["clock"], E["p"])
    cf = w15_record()["configs"]
    oldw = {k: v["clock_hz"] for k, v in cf.items() if k.startswith("v41")}
    saved = dict(_ARCH_CACHE)
    _ARCH_CACHE.clear()
    E["clock"], E["p"] = hz, dataclasses.replace(E["p"], clock_hz=hz)
    for k in oldw:
        cf[k]["clock_hz"] = hz
    try:
        yield hz
    finally:
        E["clock"], E["p"] = old
        for k, v in oldw.items():
            cf[k]["clock_hz"] = v
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)


def _cons_stage_of(name, nd, plan):
    L = nd["layer"]
    if L is None or L < 0 or L >= len(_V41_CFG["layer_dense_weight_bytes"]):
        return "head"
    return plan["start"][L]


def _cons_cooling(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S, tot):
    """Layer-die power at the saturated rate under the adopted per-pair ICG: die static without the field clock +
    the on-die dynamic energy (incl. the busy pairs' clock) at the rate.  Mean die, and the busiest stage (its own
    pair-seconds and hub share).  cooling_ungated: the same with every idle pair clocked (the pre-fix accounting)."""
    on_die = sum(v for k, v in cats.items() if k != "stack")
    mean_dyn = on_die * sat / (4 * S)
    busiest = max(tot, key=tot.get)
    b_pair = pair_s.get(busiest, 0.0) * pp["clock"] * dyn_scale
    share = (on_die - cats["field_clock_busy"]) / (4 * S) * max(tot.values()) / (sum(tot.values()) / len(tot))
    busiest_dyn = (share + b_pair) * sat
    return dict(limit_w_per_die=COOLING_LIMIT_W, dyn_scale=dyn_scale, busiest_stage=busiest,
                layer_die_static_w=round(die_static, 1),
                layer_die_mean_w_saturated=round(die_static + mean_dyn, 1),
                layer_die_busiest_w_saturated=round(die_static + busiest_dyn, 1),
                fits=bool(die_static + busiest_dyn <= COOLING_LIMIT_W),
                cooling_ungated=dict(static_w=round(die_static_ungated, 1),
                                     mean_w=round(die_static_ungated + mean_dyn - cats["field_clock_busy"] * sat / (4 * S), 1)),
                basis="per-pair ICG adopted: die static less the field clock + on-die dynamic energy (busy pairs' "
                      "clock included) at the saturated rate; busiest = its own pair-seconds + its occupancy share "
                      "of the rest")


def _cons_occupancy(g, plan):
    """Per-die issue seconds per stage, split ROM field / hub: routed experts over their stages in the placement's
    byte fractions, every other node on its layer's start stage (A.stage_occupancy's rule)."""
    occ = {}
    for name, nd in g.nodes.items():
        if nd["kind"] in ("collective", "hop"):
            continue
        s0 = _cons_stage_of(name, nd, plan)
        parts = ([(s, f) for s, f in plan["frac"][nd["layer"]]] if s0 != "head" and name.endswith(A.EXPERT_NODES)
                 else [(s0, 1.0)])
        for s, f in parts:
            b = occ.setdefault(s, dict(field=0.0, hub=0.0))
            b["field" if nd.get("_uarch") else "hub"] += nd["issue"] * f
    return occ


def _cons_windows(g, plan):
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    win, t = {}, 0.0
    for n in g.path(sink):
        c = sum(g.contrib[n].values())
        s = _cons_stage_of(n, g.nodes[n], plan)
        win[s] = win.get(s, 0.0) + c
        t += c
    return win, t


# Latency inventory (root 2026-09-30, user clock decision 1.2 GHz SS): every stream reports block | SS fmax | gap |
# fix | ADDED LATENCY CYCLES; the added cycles are folded in here as extra depth on the named node families (node
# name suffix -> cycles).  Empty until the inventories land.
V41_ADDED_LATENCY = {}
# W11 (a70c5d91, 2026-09-30): hub units at 1.2 GHz SS, ESTIMATES from TT x 1/1.43 until WC runs land.  The shared
# fast FP32 add/mul goes 3 -> ~6 stages; per dependent op: SU linear +12 (21 -> 33), SU reducer 26+3L -> 40+5L
# (+22 at L = 4), SFU exp +21, divide +8, sigmoid/silu +29, softplus +68, indexer +28, attention tile pass +17.
# Keys: "kind:<k>" (non-SFU nodes of that kind), "sfu:<class>" (SFU_NODE classes), "suffix:<name suffix>".
W11_LATENCY_SS_1P2 = {"kind:vector": 12, "kind:reduce": 22, "sfu:exp": 21, "sfu:div": 8, "sfu:sigmoid": 29,
                      "sfu:silu": 29, "sfu:softplus": 68, "suffix:idx.score": 28, "suffix:.attn.scores": 17}


def _cons_top(g, n=8):
    """The critical path's largest node families (us), after re-timing."""
    sink = [x for x in g.nodes if x.endswith("token.return")][0]
    fam = {}
    for x in g.path(sink):
        tail = x.split(".", 1)[1] if x.startswith(("L", "E")) and "." in x else x
        fam[tail] = fam.get(tail, 0.0) + sum(g.contrib[x].values())
    return {k: round(v * 1e6, 2) for k, v in sorted(fam.items(), key=lambda kv: -kv[1])[:n]}


def _lat_cycles(name, nd, lat):
    if not lat:
        return 0
    c = 0
    fn = A.SFU_NODE.get(name.split(".")[-1])
    if nd["kind"] in ("vector", "reduce"):
        c += lat.get(f"sfu:{fn}", 0) if fn else lat.get(f"kind:{nd['kind']}", 0)
    for k, v in lat.items():
        if k.startswith("suffix:") and name.endswith(k[7:]):
            c += v
        elif not k.startswith(("kind:", "sfu:", "suffix:")) and name.endswith(k):
            c += v
    return c
FIELD_CONCURRENCY = 0.5   # W18 (92d7f4f8 results/physical_abi3/asap7/chip/v41_w18/peak_current.json): a field-wide
                          # matvec draws 2,263 A a die (1.5x a B200-class package); adopted fix: at most 50% of the
                          # pairs read concurrently (+ a droop detector) -- the field's read time doubles


CDC_W18 = dict(fast_to_slow_slow_cycles=4, slow_to_fast_fast_cycles=5,
               vm_port_widening=dict(factor=4 / 3, bits_before_after={"VM x read": (549, 732), "result write": (4096, 5461),
                                                                      "attention scores/PV": (512, 683)},
                                     area_mm2_added=None, note="every slow-side port at a crossing 4/3 wider (no 25% "
                                                               "stalls); priced in consolidation()"),
               src="W18 cbaf864f results/physical_abi3/asap7/chip/v41_w18/clock_plan.json")
SLOW_KINDS = ("vector", "reduce", "sinkhorn")   # the serial-chain units: SU, SFU, softplus, reducer, Sinkhorn


# W11 MEASURED (root relay 2026-09-30, rtl/hdc/ot_hdc_fp32_add_lat.sv, routed at WC/SS, bit-identical LAT 3-7):
# the FP32 add's SS fmax and ns per dependent add.  1.2 GHz needs ~8-9 stages (~7-7.5 ns per add); SS/TT ~1.6.
FP32_ADD_SS = {3: (906e6, 3.31), 4: (939e6, 4.26), 5: (892e6, 5.61), 6: (889e6, 6.75), 7: (1208e6, 5.79),
               "ieee5": (992e6, 5.04)}
MODEL_CHAIN_ADD_STAGES = 3      # the model's hub chain units are priced with the 3-stage fast FP (ADD_LAT fastfp)
MODEL_ELEM_ADD_STAGES = FADD_PIPE   # the field element's chain adder (ot_fp32_add_rne_pipe, 5)
# root 2026-09-30: the old ot_hdc_softplus depth (259) is replaced by the SU's v41x softplus (162, ot_hdc_v41x_sfu.sv):
# 97 cycles a layer recovered
SOFTPLUS_FIX = {"suffix:softplus_sqrt": -97, "suffix:idx.topk_local": 8}   # + W11: idx_tail latency 8 -> 16   # ROOT RULING 2026-09-30: arch_budget_v41's SFU_DEPTH / V41 softplus
# 259 is the LEGACY standalone unit; the product uses the SU's v41x softplus (162) through this correction only.
# arch_budget_v41 stays FROZEN as the spec basis (the hardware is built to its derived widths; folding it there
# re-derives weight_macs 264,960 -> 246,528 etc.); the full re-baseline waits for the headline-restatement pass.


SU_KINDS = ("vector", "reduce")
# Lane-local fusion (USER RULE, AGENTS.md 2026-10-01: operator fusion through lane-local registers).  Per-op network
# stage classes, slow cycles.  C_rotate (W11 3cc18731): control broadcast 5, operand read 16, element write 16, result
# tree 8 (its op +37 = 5 + 16 + 16, reduction +29 = 5 + 16 + 8).  VM-H has no single read/write class (its +36.7 /
# +44.9 are program averages over local, scalar, rotate and gather reads): split symmetrically, a vector op's
# (36.7 - 5) / 2 each way, a reduction's read 44.9 - 5 - 8.
FUSION_C_ROTATE = dict(bcast=5, read=16, read_red=16, write=16, result=8)
FUSION_VMH = dict(bcast=5, read=(36.706 - 5) / 2, read_red=44.909 - 5 - 8, write=(36.706 - 5) / 2, result=8)
FUSION_MODES = dict(
    conservative=dict(bcast_heads_only=False, rope_lane_paired=False, quant_segmented=True,
                      note="control broadcast every op; RoPE rotate-half is a cross-lane rotation (operand read); "
                           "every quantise / qdq pays a segmented block-absmax tree (result 8)"),
    optimistic=dict(bcast_heads_only=True, rope_lane_paired=True, quant_segmented=True,
                    note="one control broadcast a fused chain; RoPE pairs co-located in a lane (layout choice); "
                         "quantise still pays its segmented absmax tree"))
_SU_FUSION_CACHE = {}
# W11 C_rotate worker (claude/w11-crot results/floorplan/v41_vm_crot_stages.json, tools/w11_vm_crot_stages.py;
# PROVISIONAL, RTL gates running) on W18b's compact hub (claude/w18-die-assembly 32155a8f: VM strip 2,163 x 7,273 um
# between two 1,787 um SU halves), 748 um a stage at 1.111 ns (W15's 0.9 GHz SS reach): the rotate realises every
# (bank slot, lane) pair, so a fixed-latency strip pays the hub's worst bank -> lane run (10,735 um) on every op --
# broadcast 7, operand read 18, element write 17, result 7, x gather 8, scatter 7, collective write 13: +42 an unfused op,
# +32 a reduction.  THE PRODUCT (root ruling 2026-10-01); the square layout's 37 / 29 (VMC) is superseded
FUSION_C_ROTATE_COMPACT = dict(bcast=7, read=18, read_red=18, write=17, result=7)
VMC_COMPACT = dict(x_gather=8, ret_scatter=7, coll_write=13, su_op_extra=42, su_red_extra=32, su_issue=1.0,
                   src="claude/w11-crot results/floorplan/v41_vm_crot_stages.json (PROVISIONAL) on W18b 32155a8f")
VMC_COMPACT_FUSED = dict(VMC_COMPACT, fusion=dict(FUSION_C_ROTATE_COMPACT, mode="conservative"))
# W11 square_hub stages on W18b's plus hub (claude/w11-crot 57318ff3); the client stages (x gather 8 / scatter 7 /
# collective write 13) are carried from the strip until W11 re-derives them for the plus
FUSION_C_ROTATE_PLUS = dict(bcast=6, read=16, read_red=16, write=15, result=6)
VMC_PLUS = dict(x_gather=8, ret_scatter=7, coll_write=13, su_op_extra=37, su_red_extra=28, su_issue=1.0,
                src="claude/w11-crot 57318ff3 (--stage-set square_hub) on W18b dfce8d40 plus hub; client stages from the strip")
VMC_FUSED = dict(VMC_PLUS, fusion=dict(FUSION_C_ROTATE_PLUS, mode="conservative"))
VMC_FUSED_OPT = dict(VMC_PLUS, fusion=dict(FUSION_C_ROTATE_PLUS, mode="optimistic"))


def w11_fusable(name):
    """ROOT RULING 2026-10-01: fusion is priced only on the families W11's measured pass fuses on the shipped program
    (claude/w11-fuse a8ce0e4d results/rtl/w11_su_fuse_stats_shipped.json: 700 edges -- hc_post 246, rmsnorm hc_pre ->
    norm out 243, moe expert sum 200, compressor 7, index_key 4); softmax, router, SwiGLU and the quantisers fuse
    nothing (their consumers change layout, read broadcasts or gather).  The priced graph does not carry the 240
    expert-sum adds nor hc_post's sub-ops, so this undercounts (raise only when the graph carries them and RTL confirms)."""
    t = name.split(".", 1)[1] if name.startswith(("L", "E")) and "." in name else name
    return (t in ("attn.hc_post", "ffn.hc_post", "attn.hc_pre", "ffn.hc_pre", "hc_pre", "head.hc_pre", "ffn.route_w")
            or t.startswith(("attn.norm.", "ffn.norm.", "head.norm.", "norm.", "attn.cmp.k_norm"))
            or (t.startswith("attn.cmp.") and "qdq" not in t))


def su_fusion_classes(g):
    """Classify every SU op (vector / reduce) of a priced graph for lane-local chaining: it needs the VM operand read
    when any input comes from outside the SU (a matvec, collective, scan, select, Sinkhorn or hop result, all in the
    VM) or it is a RoPE rotation; the element write when any consumer is outside the SU (or none); a reduction pays its
    result tree, a quantise its segmented absmax tree.  Returns name -> class dict with extra_cycles(stage_classes+mode)."""
    key = id(g)
    if key in _SU_FUSION_CACHE and _SU_FUSION_CACHE[key][0] is g:
        return _SU_FUSION_CACHE[key][1]
    succ = {k: [] for k in g.nodes}
    for k, nd in g.nodes.items():
        for x in nd["deps"]:
            succ[x].append(k)
    out = {}
    for name, nd in g.nodes.items():
        if nd["kind"] not in SU_KINDS:
            continue
        leaf = name.rsplit(".", 1)[-1]
        fus = w11_fusable(name)
        # a chain boundary: any input from outside the SU or from an SU op W11's pass does not fuse; the same for outputs
        head = (not fus or not nd["deps"]
                or any(g.nodes[x]["kind"] not in SU_KINDS or not w11_fusable(x) for x in nd["deps"]))
        tail = (not fus or not succ[name]
                or any(g.nodes[x]["kind"] not in SU_KINDS or not w11_fusable(x) for x in succ[name]))
        rope = "rope" in leaf
        quant = "quant" in leaf or leaf.endswith("qdq")
        red = nd["kind"] == "reduce"

        def extra(fz, head=head, tail=tail, rope=rope, quant=quant, red=red, fus_=fus):
            m = FUSION_MODES[fz["mode"]]
            rd = fz["read_red" if red else "read"] if (head or (rope and not m["rope_lane_paired"])) else 0.0
            bc = fz["bcast"] if (head or not m["bcast_heads_only"]) else 0.0
            if not fus_:
                return fz["bcast"] + fz["read_red" if red else "read"] + (fz["result"] if red else fz["write"])
            wr = fz["result"] if red else (fz["write"] if tail else 0.0)
            seg = fz["result"] if (quant and m["quant_segmented"]) else 0.0
            return bc + rd + wr + seg
        cls = ("not fused (outside W11's fused families)" if not fus else "cross-lane: reduction" if red else "cross-lane: RoPE rotation" if rope else
               "cross-lane: segmented quantise" if quant else
               "chain boundary: VM read" if head else "chain boundary: VM write" if tail else "lane-local chained")
        out[name] = dict(kind=nd["kind"], head=head, tail=tail, rope=rope, quant=quant, fusable=fus, cls=cls,
                         extra_cycles=extra)
    _SU_FUSION_CACHE.clear()
    _SU_FUSION_CACHE[key] = (g, out)
    return out


def _cons_adjust(g, P, clock, bf16, fc, lat, slow=None, chain_stages=None, elem_stages=None, ss_wire=False, d=None,
                 serial=None, die=None, vmh=None):
    """Re-time a priced V4.1 graph (one pass of P positions): the field-concurrency cap on every field read, W10's
    two-pass BF16 on wo_a, the latency inventory, and optionally a slower clock domain for the serial-chain units
    (slow = (hz, cdc_cycles)): their issue and depth stretch by clock / hz, and each crossing into the domain adds
    cdc_cycles of the slow clock (ASSUMED synchroniser); returns the pass time."""
    cyc = 1.0 / clock
    # Every placement pays hub -> edge -> hub, including stage/head/substage,
    # Engram and token-return hops. This is independent of the optional field
    # SS retiming switch: disabling it cannot erase physical endpoint wires.
    fabric = A.D.ArrayFabric(A.links_for(A.BASELINE), 2, "mesh", 4)
    for nd in g.nodes.values():
        if nd["kind"] == "hop":
            hop = fabric.hop(nd["hop_kind"], nd["payload"], nd.get("stage"))
            fan = ("UCIe fan-out" in hop["link"] and fabric.dp > 1)
            wire = hub_edge_hop_wire_s(hop, clock, die, fan)
            nd["depth"] += wire
            nd["_hub_edge_s"] = wire
            nd["_hub_edge_link"] = hop["link"]
            nd["_hub_edge_die"] = die or DIE_OLD
    # the reducers' adder-tree levels, from the graph's as-priced depth (decode_critical_path: red_tail + FADD x levels)
    levels = {name: max(0, round((nd["depth"] * clock - A.D.K["red_tail"]) / A.D.FADD)) for name, nd in g.nodes.items()
              if nd["kind"] == "reduce"} if serial else {}
    # softplus correction and the latency inventory first (cycles at the model's 3-stage arithmetic), then the
    # serial-chain units' depth at chain_stages-deep adds (x chain_stages / 3), then the slow domain
    for name, nd in g.nodes.items():
        nd["depth"] = max(0.0, nd["depth"] + _lat_cycles(name, nd, lat) * cyc)
    if chain_stages:
        for name, nd in g.nodes.items():
            if nd["kind"] in SLOW_KINDS:
                nd["depth"] *= chain_stages / MODEL_CHAIN_ADD_STAGES
    if slow:
        # W11's domain map: the SU, SFU, reducer, Sinkhorn, the VM-H rotate network and group tiles run in the slow
        # domain; the crossing sits at the VM port, both ways (field x / results, attention, indexer, collectives):
        # every dependency edge between the domains pays cdc_cycles of the slow clock (FIFO latency, W18 to state)
        # W18 clock plan (cbaf864f, results/physical_abi3/asap7/chip/v41_w18/clock_plan.json): one PLL, 3.6 GHz /3 and
        # /4, STA-timed crossings; ratio-FIFO latency fast->slow 3.0-3.75 slow cycles (charge 4), slow->fast
        # 3.67-4.34 fast cycles (charge 5); slow = (hz, "w18") uses them, (hz, n) charges n slow cycles each way
        hz, cdc = slow
        f2s, s2f = ((CDC_W18["fast_to_slow_slow_cycles"] / hz, CDC_W18["slow_to_fast_fast_cycles"] / clock)
                    if cdc == "w18" else (cdc / hz, cdc / hz))
        for name, nd in g.nodes.items():
            sl = nd["kind"] in SLOW_KINDS
            if sl:
                nd["issue"] *= clock / hz
                nd["depth"] *= clock / hz
            if nd["kind"] not in ("hop",) and any((g.nodes[x]["kind"] in SLOW_KINDS) != sl for x in nd["deps"]):
                nd["depth"] += f2s if sl else s2f
    if ss_wire:
        # named step (root 2026-09-30): W15's SS reach -- every field broadcast/return wire term at ceil(L / 504 um)
        # (both ways) instead of the TT fit, every collective +2 x (30 - 17) stages to the link PHY, and the W11
        # LAT-4 serial multiply (+1 slow cycle a chain node)
        reach = SS_REACH_UM[1.2e9]
        dv = die or DIE_OLD
        for name, nd in g.nodes.items():
            u = nd.get("_uarch")
            if u:
                new = (dv["expert_wire"] if u["region"] == "expert" else
                       2 * math.ceil(d["bcast_um"][u["region"]] * dv["field_scale"] / reach))
                old = u["wire"] - d.get("vm_x_gather_stages", 0) - d.get("vm_ret_scatter_stages", 0)
                nd["depth"] += max(0, new - old) * cyc
            elif nd["kind"] == "collective":
                nd["depth"] += 2 * (dv["coll_stages"] - 17) * cyc
            elif nd["kind"] in SLOW_KINDS and slow and not serial:
                nd["depth"] += W11_SERIAL_MUL_EXTRA / slow[0]
    if serial == "w11_measured" and slow:
        # named step (root 2026-09-30): W11's MEASURED serial build at 1.111 ns SS replaces the 3-stage-add depths
        for name, nd in g.nodes.items():
            if nd["kind"] in SLOW_KINDS:
                nd["depth"] += _w11_serial_cycles(name, nd, levels) / slow[0]
    if vmh and slow:
        # W11 VM-H: client stages in slow cycles replace VM_DIST's (fast-cycle) 6/6/6; per-op network extras on SU ops
        hz = slow[0]
        for name, nd in g.nodes.items():
            u = nd.get("_uarch")
            if u:
                nd["depth"] += ((vmh["x_gather"] + vmh["ret_scatter"]) / hz
                                - (d.get("vm_x_gather_stages", 0) + d.get("vm_ret_scatter_stages", 0)) * cyc)
            elif nd["kind"] == "collective" and d.get("vm_coll_write_stages"):
                nd["depth"] += vmh["coll_write"] / hz - d["vm_coll_write_stages"] * cyc
            elif nd["kind"] in SU_KINDS and vmh.get("fusion"):
                # USER RULE (AGENTS.md, 2026-10-01): operator fusion through lane-local registers -- the VM network is
                # paid only at chain boundaries and at true cross-lane moves (su_fusion_classes)
                c = su_fusion_classes(g)[name]
                nd["depth"] += c["extra_cycles"](vmh["fusion"]) / hz
                nd["issue"] *= vmh["su_issue"]
            elif nd["kind"] == "vector":
                nd["depth"] += vmh["su_op_extra"] / hz
                nd["issue"] *= vmh["su_issue"]
            elif nd["kind"] == "reduce":
                nd["depth"] += vmh["su_red_extra"] / hz
                nd["issue"] *= vmh["su_issue"]
    es = elem_stages or MODEL_ELEM_ADD_STAGES
    for name, nd in g.nodes.items():
        u = nd.get("_uarch")
        if u:
            # the element's chunk-8 chain floor and its K-split adder levels at es-stage adds
            t_read = max(u["t_read"], 8 * es) if u["t_read"] >= CHAIN_FLOOR else u["t_read"]
            nd["issue"] = max(t_read * P / fc, u["t_x"] * P, u["t_ret"] * P, u["t_mac"] * P) * cyc
            nd["depth"] += u["adder_levels"] * (es - MODEL_ELEM_ADD_STAGES) * cyc
            if bf16 == "standard_pair" and u["key"] == "wo_a":
                nd["issue"] += P * CONS_BF16["standard_pair_wo_a_extra_cycles"] * cyc
            if bf16 == "option_ii" and u["key"] in CONS_BF16["option_ii_extra_cycles"]:
                nd["issue"] += P * CONS_BF16["option_ii_extra_cycles"][u["key"]] * cyc
            if bf16 == "option_iii" and u["key"] in CONS_BF16["option_iii_issue_cycles"]:
                nd["issue"] = max(nd["issue"], P * CONS_BF16["option_iii_issue_cycles"][u["key"]] / fc * cyc)
    fin = g.solve(True)
    return fin[[n for n in g.nodes if n.endswith("token.return")][0]]


def cons_v41_rom(S, n_head=4, n_table=72, table_leak_scale=1.0, label=None, bf16="columns", clock_hz=None,
                 field_concurrency=1.0, added_latency=None, dyn_scale=1.0, slow_domain=None, chain_stages=None,
                 elem_stages=None, ss_wire=False, serial=None, die=None, vmh=None, hub_block=None):
    """The V4.1 ROM array at S TP-4 stages, n_head head dies and n_table Engram table dies: AR and MTP m = 1 per
    user, the busiest-stage saturated aggregate, energy (ungated and the adopted stage power gating, 1 us wake),
    KV capacity, HBM stacks and die counts.  Same model pieces as the economics and levers sections."""
    plan = cons_stage_plan(S)
    lat = V41_ADDED_LATENCY if added_latency is None else added_latency
    with _cons_clock(clock_hz), _cons_stages(S):
        d = copy.deepcopy(PRESETS["proposal"])
        d["macros"] = round(BASE["macros"] * plan["busiest_macros"] / cons_stage_plan(28)["busiest_macros"])
        d["vmh_block"] = hub_block or None   # the measured SU+VM block's area in the hub (power; root 2026-10-01)
        r1, g1 = _v41_graph(d, 1)
        # energy BEFORE re-timing: the field's pair-seconds per token are the work, not the (capped, stretched)
        # issue time -- the 50% cap halves the concurrent pairs and doubles the time, same pair-seconds
        led = v41_rom_ledger(g1)
        area = area_ledger(d)
        pw = power_ledger(d, g1, r1["clock_hz"], r1["tokens_s"], area)
        pp = pair_power(r1["clock_hz"])
        pair_s = {}
        for name, nd in g1.nodes.items():
            if nd.get("_uarch") and _cons_stage_of(name, nd, plan) != "head":
                for s0, f in ([(s, f) for s, f in plan["frac"][nd["layer"]]] if name.endswith(A.EXPERT_NODES)
                              else [(_cons_stage_of(name, nd, plan), 1.0)]):
                    pair_s[s0] = pair_s.get(s0, 0.0) + busy_pairs(nd) * nd["issue"] * f
        T1 = _cons_adjust(g1, 1, r1["clock_hz"], bf16, field_concurrency, lat, slow_domain, chain_stages, elem_stages,
                          ss_wire, d, serial, die, vmh)
        r1["T_us"], r1["tokens_s"] = T1 * 1e6, 1 / T1
        occ = _cons_occupancy(g1, plan)
        _, gv = _v41_graph(d, V41_POSITIONS)
        Tp = _cons_adjust(gv, V41_POSITIONS, r1["clock_hz"], bf16, field_concurrency, lat, slow_domain, chain_stages,
                          elem_stages, ss_wire, d, serial, die, vmh)
        occ_v = _cons_occupancy(gv, plan)
        win1, _ = _cons_windows(g1, plan)
        fstarts = cons_field_starts(g1, plan, r1["clock_hz"])
        eslack = cons_engram_slack(g1)
        winv, _ = _cons_windows(gv, plan)
    Td = v41_rom_draft_s(T1)
    step1 = Tp + Td
    occ_v.setdefault("head", dict(field=0.0, hub=0.0))["hub"] += Td
    tot = {s: v["field"] + v["hub"] for s, v in occ.items()}
    tot_v = {s: v["field"] + v["hub"] for s, v in occ_v.items()}
    sat, sat_m = 1.0 / max(tot.values()), V41_TAU / max(tot_v.values())
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    link_die = rack["per_die"]["static_w"]["serdes_always_on"] + rack["per_die"]["static_w"]["ucie_idle"]
    # ADOPTED per-pair ICG (W18 / power-cal): an idle pair keeps only its 0.22 mW leakage; a busy pair's clock is
    # dynamic (pair-seconds x its clock power).  The ungated form (every idle pair clocked, 0.092 W at 1.2 GHz) is
    # kept as `cooling_ungated` for the waterfall only.
    # 2026-10-04: the idle pair's ICG does not stop its whole clock: the MEASURED clock-gated idle pair keeps
    # PAIR_CG_IDLE clock_w (2.76 mW at 1.2 GHz) besides its leakage, so that residual stays static.
    field_clock_ungated = pw["field"]["clock_w"]
    field_cg_w = PAIR_W["placed_pairs"] * field_cg_residual(r1["clock_hz"]) * pp["clock"]
    die_static_ungated = pw["clock_w"] + pw["leakage_w"] + pw["hbm_idle_w"] + link_die
    die_static = die_static_ungated - field_clock_ungated + field_cg_w
    head_w = rack["static"]["head_dies"] / V41_ROM_SYSTEM["head_dies"]
    tl = rack["per_die"]["table_leakage_w"] * V41_ROM_SYSTEM["table_dies"] * table_leak_scale
    to = (rack["per_die"]["table_static_w"] - rack["per_die"]["table_leakage_w"]) * n_table
    static = dict(layer_dies=4 * S * die_static, head_dies=n_head * head_w, table_dies=tl + to)
    P_static = sum(static.values())
    cats = {k: V41_TP * v * (dyn_scale if k != "stack" else 1.0) for k, v in led["per_die_categories_J"].items()}
    cats["field_clock_busy"] = V41_TP * sum(pair_s.values()) * pp["clock"] * dyn_scale    # ICG: busy pairs' clock
    dyn = sum(v for k, v in cats.items() if k != "stack") + cats["stack"]
    e_pass = sum(v * (1 if k in ("hbm_if", "stack") else V41_POSITIONS) for k, v in cats.items())
    # W11 (root 2026-09-30): each verify position attends its OWN window (w_{p-127}..w_p) and its own index selection,
    # so the attention KV rows are NOT shared across the 6 positions -- 6 x the rows a pass (the index keys stay once
    # a pass).  The attention job's time already repeats per position; the correction is the rows' HBM energy.
    kv_rows_J = V41_TP * sum(640 * A.WIN_ROW_B / 4 for n in g1.nodes if n.endswith(".attn.scores")) * E_HBM_B
    if MTP_KV_PER_POSITION:
        e_pass += (V41_POSITIONS - 1) * kv_rows_J
    dyn_m = (e_pass + V41_DRAFT_FRACTION * dyn) / V41_TAU
    # gated (the adopted stage power gating, 1 us wake): v41_static_power's rule on this plan's stages
    p = v41_die_static_parts(d)
    p["field"]["clock"] = field_cg_w   # per-pair ICG: the busy clock is dynamic (cats field_clock_busy); the MEASURED
    p["field_cg_residual"] = 1.0       # clock-gated idle clock stays (and goes with the stage when it is power gated)
    ungated_die = sum(p["field"].values()) + sum(p["hub"].values()) + p["hbm_if"] + p["serdes"] + p["ucie"]
    table_leak_die, table_other_die = tl / max(1, n_table), to / max(1, n_table)
    wake = PG["stage_wake_s"]

    def gated(period, act, busy, P):
        out = {}
        for pol in (0, 3):
            e = 0.0
            for s in list(range(S)) + ["head"]:
                w = act.get(s, 0.0)
                b = busy.get(s, dict(field=w, hub=w))
                ok = period - w >= wake + PG["stage_bet_s"]
                ed = _die_energy(p, period, w, b, pol, wake, ok)
                e += 4 * ed if s != "head" else n_head * head_w * ed / ungated_die
            tw = 2 * 0.5e-6 * P
            t_on = min(period, tw + wake) if pol == 3 else period
            e += n_table * (table_other_die * period + table_leak_die * (t_on + PG["logic_residual"] * (period - t_on)))
            out[pol] = e
        return out
    win1["head"] = win1.get("head", 0.0)
    winv["head"] = winv.get("head", 0.0) + Td
    pts = {}
    for key, period, act, busy, P, tau, dy in (
            ("ar_b1", T1, win1, occ, 1, 1.0, dyn), ("ar_sat", 1 / sat, tot, occ, 1, 1.0, dyn),
            ("mtp_b1", step1, winv, occ_v, 1, V41_TAU, dyn_m), ("mtp_sat", V41_TAU / sat_m, tot_v, occ_v, V41_POSITIONS, V41_TAU, dyn_m)):
        e = gated(period, act, busy, P)
        rate = tau / period
        pts[key] = dict(tokens_s=round(rate, 1), ungated_mJ=round((e[0] / tau + dy) * 1e3, 2),
                        gated_mJ=round((e[3] / tau + dy) * 1e3, 2), ungated_static_w=round(e[0] / period, 1),
                        gated_static_w=round(e[3] / period, 1), gated_system_w=round(e[3] / period + dy * rate, 1))
    rows_ = _CONS_CTX
    windows_rings = max(2, math.ceil(plan["layers_per_stage"]))
    per_user = rows_ * (A.CKV_ROW_B + A.IDX_KEY_B) / 4 + _V41_CFG_WINDOW() * A.WIN_ROW_B * windows_rings
    users = int(HBM_CAP_EFF * A.ROM_DIE_HBM_STACKS * HBM_STACK_B // per_user)
    dies = 4 * S + n_head + n_table
    return dict(label=label or f"S = {S}", stages=S, bf16=bf16, clock_hz=r1["clock_hz"], layer_dies=4 * S, head_dies=n_head, table_dies=n_table,
                dies=dies, packages=dies // 2, hbm_stacks=4 * (4 * S + n_head), busiest_die_macros=d["macros"],
                ar_tokens_s_b1=round(1 / T1, 1), mtp_tokens_s_b1=round(V41_TAU / step1, 1),
                ar_saturated_tokens_s=round(sat, 1), mtp_saturated_tokens_s=round(sat_m, 1),
                stage_hops=sum(1 for n in g1.nodes.values() if n["kind"] == "hop" and n.get("hop_kind") in ("stage", "substage")),
                pipeline_hops_us=round(sum(sum(g1.contrib[n].values()) for n in g1.path(
                    next(n for n in g1.nodes if n.endswith("token.return")))
                    if g1.nodes[n]["kind"] == "hop") * 1e6, 3),
                cooling=_cons_cooling(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S, tot),
                field_concurrency=field_concurrency, added_latency=dict(lat), slow_domain=slow_domain,
                chain_stages=chain_stages, elem_stages=elem_stages, field_starts=fstarts, ss_wire=ss_wire, serial=serial,
                die=(die or DIE_OLD), vmh=vmh, hub_block=(hub_block or {}).get("option"),
                critical_path_top_us=_cons_top(g1),
                capacity_users_1m=users, static_w_ungated=dict({k: round(v, 1) for k, v in static.items()},
                                                             total=round(P_static, 1)),
                energy=pts, busiest_stage=max(tot, key=tot.get), busiest_stage_us=round(max(tot.values()) * 1e6, 2),
                layers_per_stage=round(plan["layers_per_stage"], 3), engram_dag_slack=eslack)


def _V41_CFG_WINDOW():
    return A._env()["c"]["window_tokens"]


# ---- cost: die area with a yield model (replaces the iso-package B200 price) ----
FAB = dict(
    wafer_usd=16988.0, wafer_basis="S. Khan, A. Mann, 'AI Chips: What They Are and Why They Matter', CSET 2020: TSMC "
                                   "5 nm wafer ~ $16,988 (estimate; cited)",
    wafer_d_mm=300.0, edge_exclusion_mm=3.0,           # ASSUMED edge exclusion
    d0_per_cm2=0.10, d0_basis="TSMC 2020 Technology Symposium: N5 D0 ~0.10-0.11 /cm2 at the HVM ramp, < 0.1 after "
                              "(reported by AnandTech / Tom's Hardware); cited",
    alpha=3.0, alpha_basis="ASSUMED negative-binomial clustering (Stapper); no harvesting or redundancy on any design",
    package_usd=dict(cowos_l_2die=1100.0, cowos_s_1die=750.0),
    package_basis="Raymond James via Silicon Analysts: CoWoS-S ~$750 (H100: 814 mm2 + 5-6 HBM stacks, ~2,500 mm2 "
                  "interposer), CoWoS-L ~$1,100 (B200); cited analyst estimates",
    test_assembly_usd=920.0, test_basis="Raymond James (H100 test and assembly ~$920 a package); cited analyst estimate",
    hbm_stack_usd=COST["hbm_stack_usd"], hbm_basis="economics section (ASSUMED $360 a 24 GB stack; RJ's H100 80 GB "
                                                   "HBM3 at ~$1,350 is ~$17/GB)",
    mask_sets=dict(v41_rom_bases=MASK["v41_base_designs"], hbm_die=1, qwen_rom_bases=MASK["qwen_base_designs"]),
    mask_basis="via-programmable ROM (adopted): base sets x $15M + 1 x $0.5M (low) .. 2 x $1M (high) coding masks per "
               "ROM die; every HBM comparator die design also pays one full set; / 1,000 production units",
)


def die_cost(area_mm2):
    r = FAB["wafer_d_mm"] / 2 - FAB["edge_exclusion_mm"]
    dpw = math.pi * r * r / area_mm2 - math.pi * 2 * r / math.sqrt(2 * area_mm2)
    y = (1 + area_mm2 / 100 * FAB["d0_per_cm2"] / FAB["alpha"]) ** (-FAB["alpha"])
    return dict(area_mm2=round(area_mm2, 1), dies_per_wafer=round(dpw, 1), yield_=round(y, 4),
                usd=round(FAB["wafer_usd"] / (dpw * y), 1))


def mfg_cost(dies, packages, stacks, rom_dies=0, rom_bases=0, hbm_designs=0):
    """dies: [(count, mm2)]; packages: [(count, class)].  Returns low/high capex per system (NRE amortised)."""
    si = sum(n * die_cost(a)["usd"] for n, a in dies)
    pk = sum(n * (FAB["package_usd"][c] + FAB["test_assembly_usd"]) for n, c in packages)
    st = stacks * FAB["hbm_stack_usd"]
    base = (rom_bases + hbm_designs) * MASK["full_set_usd"]
    nre_lo = base + rom_dies * MASK["coding_masks_per_die"][0] * MASK["single_mask_usd"][0]
    nre_hi = base + rom_dies * MASK["coding_masks_per_die"][1] * MASK["single_mask_usd"][1]
    u = COST["production_units"]
    hw = si + pk + st
    return dict(silicon_usd=round(si), package_usd=round(pk), hbm_usd=round(st), hardware_usd=round(hw),
                nre_usd=dict(low=nre_lo, high=nre_hi), capex_usd=dict(low=round(hw + nre_lo / u), high=round(hw + nre_hi / u)),
                silicon_mm2=round(sum(n * a for n, a in dies), 1))


# ---- HBM dies right-sized to their PHY shoreline ----
HBM_SHORE = dict(
    phy_edge_mm=8.5, phy_edge_basis="root 2026-09-30: NVIDIA H200 = the GH100 die (~814 mm2) with six HBM3e stacks, "
                                    "three per long edge (H100: the same 6 sites, 5 active); ~8-9 mm of edge per "
                                    "HBM3E PHY = GH100 long edge / 3 (Tom's Hardware, 'Nvidia H200 GPU announced'; "
                                    "NVIDIA H200 materials).  The repository's 12 mm is a placeholder (sensitivity)",
    phy_mm2=10.0, phy_basis="technology.json hbm.hbm3e phy_area_mm2_per_stack 10 (assumed, 8-15): depth = 10 / edge",
    service_band_mm=0.63072, service_basis="results/floorplan/hbm_gpu svc_south / svc_north band height",
    corner_mm=1.0, corner_basis="ASSUMED corner keep-out per long edge end",
    demonstrated_stacks_per_die=6,
    demonstrated_note="6 stacks on one die demonstrated (GH100/H200, 3 per long edge); 8 on one die is not (B200 "
                      "splits 8 across 2 dies); more than 6 is marked not demonstrated",
    reticle_mm=(26.0, 33.0),
    route_factor_basis="the placed SM array's block over its tiles (hbm_gpu floorplan: 13,990 x 12,649 um over "
                       "32 x 4.861 mm2 = 1.138)",
)


def right_size_hbm_die(model, stacks, phy_edge_mm=None, overhead=None):
    """Smallest die that holds `stacks` HBM3E PHYs on its long edges (ceil(stacks/2) a side) and the logic of the
    model's SM element array sized to them (8 SMs a stack, W13's rule), plus L2, hub, IO and the overhead reserve."""
    dv = hbm_gpu_design(model)
    fp = json.loads((ROOT / f"results/floorplan/hbm_gpu/{model}_hbm_die.json").read_text())
    tile = fp["sm_tile"]["w"] * fp["sm_tile"]["h"] / 1e6
    route = 13990.320000000002 * 12648.960000000001 / 1e6 / (32 * 1652.4 * 2941.92 / 1e6)
    n_sm = 8 * stacks
    l2 = dv["l2"]["mm2"] * stacks / 4 + 0.0
    hub = dv.get("dedicated_units_footprint_mm2", 0.0)
    io = 10.0 + (18.0 if model == "v41" else 0.0)     # host/UCIe 10 mm2 ledger; V4.1 fabric SerDes 18 mm2 (floorplan)
    logic = n_sm * tile * route + l2 + hub + io
    e = HBM_SHORE["phy_edge_mm"] if phy_edge_mm is None else phy_edge_mm
    o = CONS["overhead"] if overhead is None else overhead
    k = math.ceil(stacks / 2)
    W = k * e + 2 * HBM_SHORE["corner_mm"]
    depth = HBM_SHORE["phy_mm2"] / e
    bands = 2 * W * (depth + HBM_SHORE["service_band_mm"])
    area = (logic + bands) / (1 - o)
    H = area / W
    fits_reticle = (max(W, H) <= HBM_SHORE["reticle_mm"][1] and min(W, H) <= HBM_SHORE["reticle_mm"][0])
    return dict(model=model, stacks=stacks, sm_count=n_sm, logic_mm2=round(logic, 1), shoreline_mm=round(W, 2),
                die_w_mm=round(W, 2), die_h_mm=round(H, 2), die_mm2=round(area, 1), fits_reticle=fits_reticle,
                demonstrated=stacks <= HBM_SHORE["demonstrated_stacks_per_die"],
                package=("1 die + %d stacks (CoWoS-S, H100/H200 class)" % stacks if stacks == 6 else
                         "2 dies + 8 stacks (CoWoS-L, B200 class)" if stacks == 4 else "not demonstrated"),
                floorplan_815_logic_used_mm2=round(sum(fp["area_used"].values()), 1))


# ---- the V4.1 HBM comparator at N dies (TP-N) ----
_HBM_CHAIN_CACHE = {}


def _hbm_chain_n(N, n_sm, positions=1):
    """v41_hbm_chain at TP-N with n_sm SMs a die (group-slot).  Equal to v41_hbm_chain at N = 96, n_sm = 32."""
    key = (N, n_sm, positions, _CONS_CTX, _HBM_SWITCH, _HBM_FEC)
    if key not in _HBM_CHAIN_CACHE:
        _HBM_CHAIN_CACHE[key] = _hbm_chain_n_uncached(N, n_sm, positions)
    return dict(_HBM_CHAIN_CACHE[key])


def _hbm_chain_n_uncached(N, n_sm, positions):
    d = hbm_gpu_design("v41")
    clock = d["clock_hz"]
    arch, b = arch_graph(_CONS_CTX)
    g = b.g
    path = g.path(b.sink)
    mv = other = extra = xfill = 0.0
    for x in path:
        nd = g.nodes[x]
        t = sum(g.contrib[x].values())
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / N
            mv += sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], d["drain_cycles"], True, n_sm) / clock
            xfill += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock
        elif nd["kind"] in ("collective", "hop"):
            continue
        else:
            other += t
            if positions > 1:
                extra += (positions - 1) * nd.get("issue", 0.0)
    nb = v41_boundaries(path, g.nodes)
    parts = dict(sm_matvec=mv * 1e6, x_broadcast_fill=xfill * 1e6, dedicated_and_su=other * 1e6,
                 verify_extra_issue=extra * 1e6, barrier=nb * d["barrier"]["boundary_cycles"] / clock * 1e6,
                 **v41_hbm_fabric_us(_HBM_SWITCH, _HBM_FEC))
    parts["collective_bytes"] *= positions
    return parts


def _v41_state_user():
    c = A._env()["c"]
    s = 0.0
    for L in range(c["num_layers"]):
        r = c["compress_ratios"][L]
        if L in c["kv_source_layer_ids"] and r:
            s += 1048576 // r * (A.CKV_ROW_B + A.IDX_KEY_B)
        s += c["window_tokens"] * A.WIN_ROW_B
    return s


_HBM_N_CACHE = {}


def hbm_ss_wire_delta(stacks):
    """The V4.1 HBM die's barrier / x-broadcast / TP-root crossings at W15's SS reach (504 um), on the right-sized die
    (the 815 mm2 floorplan's distances scaled by the linear size ratio), against the floorplan's TT stage counts."""
    fp = json.loads((ROOT / "results/floorplan/hbm_gpu/v41_hbm_die.json").read_text())
    k = math.sqrt(right_size_hbm_die("v41", stacks)["die_mm2"] / 815.0)
    X = {c["name"]: c for c in fp["crossings"]}
    r = SS_REACH_UM[1.2e9]

    def st(name):
        return math.ceil(X[name]["distance_um"] * k / r)
    one_way = st("barrier_leaf") + st("barrier_trunk")
    old_one = X["barrier_leaf"]["cycles_one_way"] + X["barrier_trunk"]["cycles_one_way"]
    bnd = 2 * (one_way - old_one) + (st("x_broadcast_root_to_sm") - X["x_broadcast_root_to_sm"]["cycles_one_way"])
    coll = 2 * max(0, st("tp_root_to_ucie") - X["tp_root_to_ucie"]["cycles_one_way"])
    return dict(scale=round(k, 3), boundary_extra_cycles=bnd, collective_extra_cycles=coll,
                collectives=round(V41_HBM_FABRIC_US["collective_latency"] / 0.668))


def v41_hbm_n(N, stacks, ec, gated_rows, replicas=1, clock_hz=None):
    key = (N, stacks, replicas, id(ec), clock_hz, _CONS_CTX)
    if key not in _HBM_N_CACHE:
        _HBM_N_CACHE[key] = _v41_hbm_n(N, stacks, ec, gated_rows, replicas, clock_hz)
    return copy.deepcopy(_HBM_N_CACHE[key])


def _v41_hbm_n(N, stacks, ec, gated_rows, replicas=1, clock_hz=None):
    """V4.1 HBM comparator: `replicas` TP-N groups of dies with `stacks` HBM3E each (8 SMs a stack), 1M.  Per user
    (AR, MTP), the saturated aggregate (column passes, v41_hbm_economics' rule), capacity (every die holds 1/N of
    every layer's KV: TP-N), energy with the 96-die design's gated/ungated static ratio, power, area, cost."""
    dv = hbm_gpu_design("v41")
    cols = dv["element"]["cols"]
    n_sm = 8 * stacks
    sweep1 = 37.4 * (V41_HBM_DIES * 4) / (N * stacks)
    w1 = _v41_weight_bytes(1)
    sweep = lambda toks: sweep1 * _v41_weight_bytes(toks) / w1   # noqa: E731
    cache = {}

    ck = (dv["clock_hz"] / clock_hz) if clock_hz else 1.0   # cycle-counted terms at another clock (the fabric and
                                                             # the HBM weight sweep keep their seconds)
    bwire = hbm_ss_wire_delta(stacks) if clock_hz else None

    def chain(P):
        if P not in cache:
            c = _hbm_chain_n(N, n_sm, P)
            for k_ in ("sm_matvec", "x_broadcast_fill", "dedicated_and_su", "verify_extra_issue", "barrier"):
                c[k_] *= ck
            if bwire:          # W15 SS reach on the right-sized die: every boundary and collective grows
                bc = dv["barrier"]["boundary_cycles"]
                c["barrier"] *= (bc + bwire["boundary_extra_cycles"]) / bc
                c["collective_latency"] += bwire["collectives"] * bwire["collective_extra_cycles"] / clock_hz * 1e6
            cache[P] = c
        return cache[P]
    issue1 = chain(2)["verify_extra_issue"]

    def T(P, toks):
        return max(sum(chain(P).values()), sweep(toks))

    def occ(P, toks):
        p = chain(P)
        return max(p["sm_matvec"] + p["x_broadcast_fill"] + p["barrier"], P * issue1, sweep(toks))
    tot, *_ = _v41_weight_split()
    per_user_hbm = tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]
    macs_j = _v41_system_macs_j()
    coll_b = tot["collective_bytes"]
    units_j = ec["v41_rom"]["energy"]["categories_mJ_per_token"]["units"] * 1e-3
    W = _V41_CFG["checkpoint_bytes"]
    cap = int((N * stacks * HBM_STACK_B * HBM_CAP_EFF - W) // _v41_state_user())
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    sa = dv["sm_area"]
    st1 = _static_w(n_sm * sa["logic_mm2"] + dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL + 10.0 * stacks, 0.0,
                    n_sm * sa["sram_mm2"] + dv["l2"]["mm2"] * stacks / 4, clock_hz or dv["clock_hz"], stacks)
    st1["links"] = rack["serdes_always_on"] + rack["ucie_idle"]
    P_static = replicas * N * sum(st1.values())
    gr = {(r["design"], r["point"]): r for r in gated_rows}

    def ratio(mode, point):
        r = gr[(f"V4.1 HBM tier 3 {mode}", point)]
        return r["clock_and_power_gated_static_w"] / r["ungated_static_w"]

    def energy(B, P, draft_frac):
        toks = B * P
        per = max(1, cols // P)
        passes = math.ceil(B / per)
        wb = passes * _v41_weight_bytes(min(B, per) * P)
        kvp = tot["bytes"]["kv_hbm"] * (P if MTP_KV_PER_POSITION else 1) + tot["bytes"]["idx"]
        e = (toks * macs_j + (wb + B * kvp) * E_HBM_B + wb * 2 * E_SRAM_B + toks * units_j
             + toks * coll_b * 8 * E_LINK["board"] * 2)
        return e * (1 + draft_frac)
    out = {}
    for mode, P, tau, df in (("AR", 1, 1.0, 0.0), ("MTP", V41_POSITIONS, V41_TAU, V41_DRAFT_FRACTION)):
        per = max(1, cols // P)
        Td = df * T(1, 1)
        best = None
        rows = []
        for B in sorted(set([b for b in ECON_BATCHES if b <= max(1, cap)] + [max(1, cap)])):
            t = (T(B * P, B * P) + Td if B <= per else
                 max(T(per * P, per * P) + Td, math.ceil(B / per) * (occ(per * P, per * P) + Td))) * 1e-6
            pu = tau / t
            e_dyn = energy(B, P, df) / (B * tau)
            rows.append(dict(batch=B, per_user=pu, agg=replicas * B * pu, t=t, e_dyn=e_dyn))
        b1 = rows[0]
        best = max(rows, key=lambda r: r["agg"])
        pts = {}
        for point, r in (("batch1", b1), ("saturated", best)):
            agg = r["agg"] if point == "saturated" else r["per_user"]
            stat = P_static              # the whole system is powered, for a lone user too
            g_ = ratio(mode, point)
            pts[point] = dict(batch=r["batch"] * (replicas if point == "saturated" else 1),
                              per_user_tokens_s=round(r["per_user"], 1), aggregate_tokens_s=round(agg, 1),
                              ungated_mJ=round((r["e_dyn"] + stat / agg) * 1e3, 2),
                              gated_mJ=round((r["e_dyn"] + g_ * stat / agg) * 1e3, 2),
                              gated_system_w=round(g_ * stat + r["e_dyn"] * agg, 0))
        out[mode] = pts
    die = right_size_hbm_die("v41", stacks)
    per_pkg = 1 if stacks == 6 else 2
    n_d = replicas * N
    cost = mfg_cost([(n_d, die["die_mm2"])],
                    [(math.ceil(n_d / per_pkg), "cowos_s_1die" if per_pkg == 1 else "cowos_l_2die")],
                    n_d * stacks, hbm_designs=1)
    return dict(dies=n_d, tp=N, replicas=replicas, stacks_per_die=stacks, sm_per_die=n_sm, capacity_users_1m=cap * replicas,
                capacity_users_per_group=cap, feasible=cap >= 1, weight_sweep_us=round(sweep1, 1),
                chain_us_ar=round(sum(chain(1).values()), 1), die_mm2=die["die_mm2"],
                silicon_mm2=round(n_d * die["die_mm2"], 1), static_w_ungated=round(P_static, 1),
                ar=out["AR"], mtp=out["MTP"], cost=cost)


# ---- the study ----
def consolidation(ec=None, lv=None):
    ec = ec or economics()
    lv = lv or economics_levers(ec)
    gr = lv["gated_alike"]["rows"]
    # 1. V4.1 ROM: die counts per density basis and overhead
    counts = []
    for bf in BF16_MODES + ("hub_unit",):
        for pitch in CONS_PITCH:
            for dens in ("analytical", "asap7", "roma"):
                for o in (CONS["overhead_band"][0], CONS["overhead"], CONS["overhead_band"][1]):
                    for credit in CONS_CREDIT:
                        S = cons_min_stages(dens, o, credit, "w10_refit", pitch, bf)
                        t = cons_table_dies(dens, o)
                        h = cons_head_dies(dens, o, credit, "w10_refit", pitch)
                        u = cons_field_usable_mm2(o, credit)
                        counts.append(dict(bf16=bf, pitch=pitch, density=dens, overhead=o, sliver_credit=credit,
                                           stages=S, layer_dies=4 * S, head_dies=h, table_dies=t["dies"],
                                           dies=4 * S + h + t["dies"], field_usable_mm2=round(u, 1),
                                           field_need_mm2_at_28=round(cons_field_need_mm2(28, dens, pitch, bf), 1),
                                           margin_at_28_mm2=round(u - cons_field_need_mm2(28, dens, pitch, bf), 2),
                                           table_bytes_per_die_GB=round(t["bytes_per_die"] / 1e9, 2)))
    C = {(r["bf16"], r["pitch"], r["density"], r["overhead"], r["sliver_credit"]): r for r in counts}
    PB = ("standard_pair", "w10_budget", "analytical", CONS["overhead"], "ring")      # the product basis (root)
    base = C[PB]
    stage_table = []
    for bf in BF16_MODES:
        for pitch in CONS_PITCH:
            for o in (CONS["overhead_band"][0], CONS["overhead"], CONS["overhead_band"][1]):
                for credit in CONS_CREDIT:
                    row = dict(bf16=bf, pitch=pitch, overhead=o, credit=credit)
                    for dens in ("analytical", "asap7", "roma"):
                        c = C[(bf, pitch, dens, o, credit)]
                        row[dens] = dict(stages=c["stages"], layer_dies=c["layer_dies"], head_dies=c["head_dies"],
                                         table_dies=c["table_dies"], margin_at_28_mm2=c["margin_at_28_mm2"])
                    stage_table.append(row)
    legal_phy = [dict(pitch=pitch, overhead=CONS["overhead"], credit=cr, bf16="standard_pair",
                      analytical_stages=cons_min_stages("analytical", CONS["overhead"], cr, "w18_legal_phy", pitch))
                 for pitch in CONS_PITCH for cr in CONS_CREDIT]
    # table-die ROM leakage follows the ROM area at each density (the rack's leakage is the analytical area)
    leak = dict(analytical=1.0, roma=DENSITY["roma"]["mm2_per_B"] / CONS_A_ANALYTICAL,
                asap7=CONS_TABLE_MACRO_MM2 / CONS_TABLE_MACRO_B / CONS_A_ANALYTICAL)
    pcache = {}

    def price(tag, S, h, t, dens, bf, clock=None, **meta):
        key = (S, h, t, leak[dens], bf if bf != "hub_unit" else "columns", clock)
        if key not in pcache:
            pcache[key] = cons_v41_rom(S, h, t, leak[dens], None, key[4], clock)
        pt = copy.deepcopy(pcache[key])
        pt.update(label=tag, density=dens, bf16_mode=bf, **meta)
        return pt
    t_a = C[PB]["table_dies"]
    points = [price("as placed (188 dies, BF16 columns in the model's timing, TT)", 28, 4, 72, "analytical", "columns",
                    role="reference")]
    # root's BF16 lever at the product basis (TT): (a) BF16 columns, (b) two-pass BF16 on the standard pair, (c) hub
    for bf in ("columns", "standard_pair", "hub_unit"):
        c = C[(bf,) + PB[1:]]
        points.append(price(f"BF16 lever: {bf}", c["stages"], c["head_dies"], c["table_dies"], "analytical", bf,
                            role="bf16_lever"))
    # 28 against 34 stages (TT, standard pair): more hand-offs against shallower stages
    for S in (28, 34):
        points.append(price(f"{S} stages (stage-count comparison)", S, 4, t_a, "analytical", "standard_pair",
                            role="stage_count"))
    # density sensitivities at the product basis (TT)
    for dens in ("asap7", "roma"):
        c = C[("standard_pair", "w10_budget", dens, CONS["overhead"], "ring")]
        points.append(price(f"density {dens}", c["stages"], c["head_dies"], c["table_dies"], dens, "standard_pair",
                            role="density"))
    # USER DECISION: sign-off at SS.  Macro depth x clock: logic derated SS/TT = 1.27 (no logic block has an SS
    # closure), and the upper bound where the logic is re-closed at the macro's SS clock
    tt = A._env()["clock"]
    ss_logic = tt / SS_DERATE
    ss_rows = []
    for depth, dv in ROM_DEPTH_OPTS.items():
        S = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", "standard_pair", depth)
        h = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", depth)
        for mode, hz in (("(i) ROM-limited SS clock, logic ASSUMED re-hardened at WC to meet it", dv["ss_ghz"] * 1e9),
                         ("(ii) TT-closed logic derated 1.43x (MEASURED: W13 tc16 re-timed at SS, 759 MHz)",
                          min(dv["ss_ghz"] * 1e9, tt / SS_DERATE_MEASURED)),
                         ("(iii) TT-closed logic derated 1.27x (the ROM macro's ratio)",
                          min(dv["ss_ghz"] * 1e9, ss_logic))):
            binds = ("the ROM macro (%s SS single-cycle %.3f GHz)" % (depth, dv["ss_ghz"]) if hz >= dv["ss_ghz"] * 1e9 - 1
                     else "the TT-closed logic, derated: the model clock's slowest routed block %s (%.4f GHz TT)"
                     % (min(A._env()["clock_rows"], key=lambda r: r["fmax_hz"])["block"], tt / 1e9))
            pt = price(f"SS {depth}, {mode}", S, h, t_a, "analytical", "standard_pair", clock=hz, role="ss",
                       depth=depth, clock_mode=mode, macro_ss_ghz=dv["ss_ghz"], clock_binds=binds)
            points.append(pt)
            ss_rows.append(pt)
    # USER DECISION (AGENTS.md e7479589): the V4.1 product basis is 4096m8, 2 macros a slot, at 1.2 GHz SS, BF16 on
    # the standard pair; W18's 50% field-concurrency cap adopted; dynamic energy +16% at 1.2 GHz (root, ASSUMED);
    # the latency inventory folds in as it lands (W11 hub estimates so far)
    # USER DECISION 2026-09-30: BF16 option (iii) at W10's measured 574 x 126.9 um tile (max per-user rate)
    # USER DECISION 2026-09-30 (final): maximum per-user rate, die count free -> BF16 COLUMNS are the product: on the
    # full-token basis they beat (iii) and (ii) (the busiest-die op cycles favoured (iii), but its +20.7% pair pitch
    # adds stages, i.e. hops, and its BF16 issue floors sit above the columns' full-width BF16 lanes)
    Sp = cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, PRODUCT_PITCH, "columns", "4096m8")
    # the W10b tiles alone (the 815 mm2 field with the ledger hub): 39 stages; with the C_rotate block: Sp; with the
    # VM-H block (reference row): Sh
    Sp_w10b = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", PRODUCT_PITCH, "columns", "4096m8")
    Sh = cons_min_stages("analytical", CONS["overhead"], "ring", VMH_REF_GEOM, PRODUCT_PITCH, "columns", "4096m8")
    hh = cons_head_dies("analytical", CONS["overhead"], "ring", VMH_REF_GEOM, PRODUCT_PITCH, "8192m8")
    # the named steps before the W10b tile re-fit run at the previous q pitch (W10 476 x 126.9 um)
    Sp_prev = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_q_1p2", "columns", "4096m8")
    hp_prev = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_q_1p2", "8192m8")
    # ROOT 2026-09-30: the head group on 8192m8 WITH ping-pong (2 macros a slot, alternate reads, 2-cycle macro path:
    # 1,667 ps against 8192m8's SS clk->q 1,004 + 25 + 60 ps) fits 4 dies -- 0.4% margin at the storage-only density,
    # 13.3% at W18's floorplan (claude/w18-die-assembly 4ed60cbb head_table_fit.json): CONFIRMED at floorplan level
    hp = cons_head_dies("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, PRODUCT_PITCH, "8192m8")
    # W10b (2026-10-01): the wider q pair (510.84 um) takes the head group's storage-only need from 99.6% to 105.2% of
    # one TP-4 group, so the model's rule gives 8 head dies.  W18's floorplan margin (13.3% at the 476 um pair) scaled
    # by the same need ratio is ~8% -- an ESTIMATE, not a floorplan; the product follows the model's rule until W18b
    # re-fits the head group at the W10b tile (root to rule)
    r_prev, r_new = cons_head_need_ratio("w10_q_1p2"), cons_head_need_ratio(PRODUCT_PITCH, geom=PRODUCT_GEOM)
    head_fit = dict(dies=hp, depth="8192m8 ping-pong", margin_storage_only=round(1 - r_new, 4),
                    margin_storage_only_w10_q=round(1 - r_prev, 4), margin_w18_floorplan_w10_q=0.133,
                    margin_w18_floorplan_scaled_estimate=round(1 - (1 - 0.133) * r_new / r_prev, 3),
                    dies_at_w10_q=hp_prev,
                    on_4096m8=cons_head_dies("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, PRODUCT_PITCH, "4096m8"),
                    stages_w10b_tiles_only=Sp_w10b, stages_vmh_reference=Sh, hub_block=PRODUCT_HUB,
                    status=(f"{hp} dies on the model's storage-only rule at the W10b tile (need {r_new:.1%} of one "
                            f"TP-4 group; {hp_prev} at W10's 476 um pair, CONFIRMED at floorplan level by W18 "
                            f"4ed60cbb).  W18's 13.3% floorplan margin scaled by the need ratio is ~"
                            f"{1 - (1 - 0.133) * r_new / r_prev:.1%} (ESTIMATE): 4 head dies would likely hold at "
                            "floorplan level -- pending a W18b head re-fit at the W10b tile and a root ruling"),
                    table_dies_asap7_floorplan=dict(dies=20, src="W18 4ed60cbb head_table_fit.json (ASAP7 geometry "
                                                                 "feasibility row); the product stays 36 (storage-only)"))
    bf16_ref = {k: cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, pt, bfm, "4096m8")
                for k, pt, bfm in (("option_ii cap 3 (reference)", PRODUCT_PITCH, "option_ii"),
                                   ("option_iii BF16_PAIR (reference)", "w10_iii_1p2", "option_iii"),
                                   ("columns (product)", PRODUCT_PITCH, "columns"))}
    bf16_full_token = {}
    for k, pt_, bfm in (("option_ii cap 3", PRODUCT_PITCH, "option_ii"), ("option_iii", "w10_iii_1p2", "option_iii")):
        S_ = cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, pt_, bfm, "4096m8")
        q_ = cons_v41_rom(S_, 4, cons_table_dies("analytical")["dies"], 1.0, None, bfm, PRODUCT_CLOCK_HZ,
                          FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT), PRODUCT_DYN_SCALE,
                          (0.9e9, "w18"), None, 7, True, PRODUCT_SERIAL, DIE_SHRUNK_INTERIM, VMC_FUSED, PRODUCT_HUB)
        bf16_full_token[k] = dict(stages=S_, dies=q_["dies"], ar=q_["ar_tokens_s_b1"], mtp=q_["mtp_tokens_s_b1"],
                                  saturated=q_["ar_saturated_tokens_s"], pipeline_hops_us=q_["pipeline_hops_us"])
    prod = {}
    for tag, fc, lat, cs, es in (("ideal depths, no concurrency cap", 1.0, SOFTPLUS_FIX, None, None),
                                 ("50% field-concurrency cap (W18, adopted)", FIELD_CONCURRENCY, SOFTPLUS_FIX, None, None),
                                 ("cap + W11 hub latency inventory (estimates)", FIELD_CONCURRENCY,
                                  dict(W11_LATENCY_SS_1P2, **SOFTPLUS_FIX), None, None),
                                 ("cap + measured FP32 add: chain and element adds 8 stages", FIELD_CONCURRENCY,
                                  SOFTPLUS_FIX, 8, 8),
                                 ("ADOPTED (AGENTS.md c0894b1c): cap + 1.2 GHz streaming domain (LAT-7 adds, W11: "
                                  "1,208 MHz SS) + 0.9 GHz chain domain (LAT 3), W18 ratio-FIFO CDC",
                                  FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),  # CDC per W18 (4 slow / 5 fast)
                                 ("ADOPTED + W15 SS wire reach (504 um) + W11 LAT-4 serial mul", FIELD_CONCURRENCY,
                                  SOFTPLUS_FIX, None, 7),
                                 (SERIAL_TAG, FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),
                                 (SHRINK_TAG, FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),
                                 (STREAM_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (VMH_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (VMH_REF_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (CROT_SQ_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (CROT_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (CROT_FUSED_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7),
                                 (PLUS_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT), None, 7),
                                 (PRODUCT_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT), None, 7),
                                 (FUSED_OPT_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT), None,
                                  7)):
        fin = tag == PRODUCT_TAG
        S_, h_, vm_, blk_ = ({PRODUCT_TAG: (Sp, hp, VMC_FUSED, PRODUCT_HUB), FUSED_OPT_TAG: (Sp, hp, VMC_FUSED_OPT, PRODUCT_HUB),
                              CROT_TAG: (Sp, hp, VMC_COMPACT, PRODUCT_HUB), CROT_SQ_TAG: (Sp, hp, VMC, PRODUCT_HUB),
                              CROT_FUSED_TAG: (Sp, hp, VMC_COMPACT_FUSED, PRODUCT_HUB),
                              PLUS_TAG: (Sp, hp, VMC_PLUS, PRODUCT_HUB),
                              VMH_REF_TAG: (Sh, hh, VMH, VMH_BLOCK)}.get(tag)
                             or (Sp_prev, hp_prev, VMH if "VM-H" in tag else None, None))
        pt = cons_v41_rom(S_, h_, t_a, 1.0, None, "columns", PRODUCT_CLOCK_HZ,
                          fc, lat, PRODUCT_DYN_SCALE,
                          (0.9e9, "w18") if tag.startswith("ADOPTED") else None, cs, es, "SS wire" in tag,
                          PRODUCT_SERIAL if "MEASURED serial" in tag else None,
                          DIE_SHRUNK_INTERIM if "shrunk-die" in tag else None, vm_, blk_)
        pt["vm_option"] = (blk_ or {}).get("option") or ("H_rtl" if vm_ is VMH else None)
        pt["fusion"] = (vm_ or {}).get("fusion", {}).get("mode")
        pt["fusion_label"] = FUSION_LABEL if pt["fusion"] else None
        pt["product_final"] = tag == PRODUCT_TAG
        pt.update(label=f"PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: {tag}", density="analytical",
                  bf16_mode="columns", role="product", depth="4096m8", bf16_stage_reference=bf16_ref)
        prod[tag] = pt
        points.append(pt)
    # the SS-clock curve (root 2026-09-30): tok/s against the logic's SS clock, capped at each macro's SS limit, so
    # the depth can be read off when the WC-hardened blocks report their SS fmax
    ss_curve = []
    for depth, dv in ROM_DEPTH_OPTS.items():
        S = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", "standard_pair", depth)
        h = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", depth)
        for f in SS_CURVE_GHZ:
            hz = min(f, dv["ss_ghz"]) * 1e9
            pt = price(f"curve {depth} logic {f:.2f} GHz", S, h, t_a, "analytical", "standard_pair", clock=hz)
            ss_curve.append(dict(depth=depth, logic_ss_ghz=f, clock_ghz=round(hz / 1e9, 4),
                                 capped_by_macro=f > dv["ss_ghz"], stages=S, dies=pt["dies"],
                                 ar_tokens_s_b1=pt["ar_tokens_s_b1"], mtp_tokens_s_b1=pt["mtp_tokens_s_b1"],
                                 ar_saturated_tokens_s=pt["ar_saturated_tokens_s"],
                                 gated_mJ_b1=pt["energy"]["ar_b1"]["gated_mJ"],
                                 gated_mJ_saturated=pt["energy"]["ar_sat"]["gated_mJ"]))
    for pt in points:
        rate = dict(ar_saturated=pt["ar_saturated_tokens_s"], mtp_saturated=pt["mtp_saturated_tokens_s"] * V41_POSITIONS / V41_TAU)
        pt["engram"] = cons_engram_path(pt["table_dies"], rate)
        pt["cost"] = mfg_cost([(pt["dies"], FLOORPLAN["die_mm2"])],
                              [((pt["layer_dies"] + pt["head_dies"]) // 2, "cowos_l_2die"), (pt["table_dies"] // 2, "cowos_l_2die")],
                              pt["hbm_stacks"], rom_dies=pt["dies"], rom_bases=FAB["mask_sets"]["v41_rom_bases"])
        pt["cost_iso_package_usd"] = pt["packages"] * COST["package_usd"]
        pt["silicon_mm2"] = pt["dies"] * FLOORPLAN["die_mm2"]
    # the comparison-rule reference: the product basis at TT (PROVISIONAL: the product die count is open until the
    # closed pair's pitch lands, root 2026-09-30)
    head = prod[PRODUCT_TAG]   # final: SS wires and W11's measured serial build in
    die_shrink = dict(DIE_SHRINK, interim=DIE_SHRUNK_INTERIM, role="ruling",
                      note="the product row carries W18b's interim shrunk-die crossings (996f7982); the sqrt(area) "
                           "sensitivity of 9bde5a55 is superseded; die area, cost and power re-price on the p12 floorplan")
    # 2. HBM dies right-sized; the V4.1 HBM sweep; Qwen HBM
    dies = {f"{m}_{s}": right_size_hbm_die(m, s) for m in ("qwen", "v41") for s in (4, 6)}
    dies["v41_4_phy12mm"] = right_size_hbm_die("v41", 4, 12.0)
    dies["qwen_6_phy12mm"] = right_size_hbm_die("qwen", 6, 12.0)
    minN = {s: math.ceil(_V41_CFG["checkpoint_bytes"] / (s * HBM_STACK_B * HBM_CAP_EFF)) for s in (4, 6)}
    sweep = []
    for s in (4, 6):
        Ns = sorted(set([minN[s], minN[s] + 1, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96]))
        for N in Ns:
            if N < minN[s]:
                continue
            r = v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
            r["capacity_minimum"] = N == minN[s]
            sweep.append(r)
    users_866 = {}
    for s in (4, 6):
        N = minN[s]
        while v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)["capacity_users_1m"] < head["capacity_users_1m"]:
            N += 1
        users_866[s] = N
    for s in (4, 6):
        if not any(r["tp"] == users_866[s] and r["stacks_per_die"] == s for r in sweep):
            r = v41_hbm_n(users_866[s], s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
            r["capacity_minimum"] = False
            sweep.append(r)
    sweep.sort(key=lambda r: (r["stacks_per_die"], r["dies"]))
    # 3. the comparison rule: equal area, equal cost, equal power against the consolidated ROM array
    def budget_N(s, key, target):
        best = None
        for N in range(minN[s], 97):
            r = v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ) if key != "area" else None
            val = (N * right_size_hbm_die("v41", s)["die_mm2"] if key == "area" else
                   r["cost"]["capex_usd"]["low"] if key == "cost" else r["ar"]["saturated"]["gated_system_w"])
            if val <= target:
                best = N
            elif key == "area":
                break
        return best
    rule = []
    tgt = dict(area=head["silicon_mm2"], cost=head["cost"]["capex_usd"]["low"],
               power=head["energy"]["ar_sat"]["gated_system_w"])
    for key in ("area", "cost", "power"):
        for s in (4, 6):
            per_die = right_size_hbm_die("v41", s)["die_mm2"]
            if key == "area" and tgt["area"] >= 96 * per_die:
                N, rep = 96, int(tgt["area"] // (96 * per_die))
            else:
                N, rep = budget_N(s, key, tgt[key]), 1
                if key != "area" and N == 96:
                    r96 = v41_hbm_n(96, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
                    unit = r96["cost"]["capex_usd"]["low"] if key == "cost" else r96["ar"]["saturated"]["gated_system_w"]
                    rep = max(1, int(tgt[key] // unit))
            if N is None:
                rule.append(dict(rule=f"equal {key}", stacks_per_die=s, feasible=False, target=tgt[key]))
                continue
            r = v41_hbm_n(N, s, ec, gr, replicas=rep, clock_hz=PRODUCT_CLOCK_HZ)
            rule.append(dict(rule=f"equal {key}", target=tgt[key], **r))
    # Qwen: ROM package vs right-sized HBM packages (bandwidth-bound: tok/s scales with stacks)
    qh = ec["qwen_hbm"]
    wl, kvb = _qwen_wl()
    dq = hbm_gpu_design("qwen")
    w_B = sum(b_ for b_, _ in qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])) - kvb / 2
    w_total = 2 * w_B
    qg = {(r["design"], r["point"]): r for r in gr}
    qwen = []
    # the Qwen ROM PRODUCT (root, 2026-09-30): option C, 2 B200-class packages, TP-4, G = 6,144 a die, W12 wires
    qo = qwen_rom_options(ec)
    pc = next(r for r in qo["options"]["C"]["rows"] if r["G"] == 6144)
    q_rom_cost = dict(capex_usd=pc["capex_usd"], hardware_usd=pc["hardware_usd"])
    qwen.append(dict(design="Qwen ROM product: option C (2 B200-class packages, 4 x 815 mm2, 16 stacks, TP-4, G 6,144)",
                     dies=4, stacks=16, silicon_mm2=4 * FLOORPLAN["die_mm2"], ar_tokens_s_b1=pc["tokens_s_b1"],
                     saturated_tokens_s=pc["saturated_tokens_s"], capacity_users=pc["capacity_users"],
                     gated_mJ_b1=pc["mJ_b1"], gated_mJ_sat=pc["mJ_saturated"],
                     gated_system_w=round(pc["mJ_saturated"] * pc["saturated_tokens_s"] / 1e3, 1), cost=q_rom_cost,
                     wire_calibration="W12 floorplan wires (9,194 tok/s at the 2-die reference); the economics "
                                      "section's W5 wires give 9,851 there"))
    for k, s in ((1, 6), (2, 4), (1, 4)):
        die = right_size_hbm_die("qwen", s)
        f = k * s / 8
        ar_b1 = qh["ar"]["tokens_s_b1"] * f
        df_b1 = qh["dflash"]["tokens_s_b1"] * f
        sat = max(qh["ar"]["saturated_tokens_s"], qh["dflash"]["saturated_tokens_s"]) * f
        cap = int((k * s * HBM_STACK_B * HBM_CAP_EFF - w_total) // kvb)
        g1 = qg[("Qwen HBM tier 3 DFlash", "batch1")]
        gs = qg[("Qwen HBM tier 3 DFlash", "saturated")]
        # dynamic energy per token is unchanged (same bytes); static scales with the SMs (8 a stack) and the stacks
        stat_scale = k * s / 8
        e_b1 = (g1["clock_and_power_gated_mJ_per_token"] - g1["clock_and_power_gated_static_w"] / g1["tokens_s"] * 1e3
                + g1["clock_and_power_gated_static_w"] * stat_scale / df_b1 * 1e3)
        e_sat = (gs["clock_and_power_gated_mJ_per_token"] - gs["clock_and_power_gated_static_w"] / gs["tokens_s"] * 1e3
                 + gs["clock_and_power_gated_static_w"] * stat_scale / sat * 1e3)
        cost = mfg_cost([(k, die["die_mm2"])], [(1, "cowos_s_1die" if k == 1 else "cowos_l_2die")], k * s, hbm_designs=1)
        qwen.append(dict(design=f"Qwen HBM, {k} right-sized die(s) x {s} stacks ({die['die_mm2']} mm2 each)", dies=k,
                         stacks=k * s, silicon_mm2=round(k * die["die_mm2"], 1), ar_tokens_s_b1=round(ar_b1, 1),
                         dflash_tokens_s_b1=round(df_b1, 1), saturated_tokens_s=round(sat, 1), capacity_users=cap,
                         gated_mJ_b1=round(e_b1, 1), gated_mJ_sat=round(e_sat, 1),
                         gated_system_w=round(e_sat * sat / 1e3, 1), cost=cost, demonstrated=die["demonstrated"],
                         basis="bandwidth-bound: tok/s x (stacks / 8) of the 2-die W13 design (its barrier and TP "
                               "exchange are hidden under the stream); DFlash at its best block"))
    q_rule = []
    rom_q = qwen[0]
    for key, tv in (("area", rom_q["silicon_mm2"]), ("cost", rom_q["cost"]["capex_usd"]["low"]),
                    ("power", rom_q["gated_system_w"])):
        for row in qwen[1:3]:
            unit = (row["silicon_mm2"] if key == "area" else row["cost"]["capex_usd"]["low"] if key == "cost"
                    else row["gated_system_w"])
            n = int(tv // unit)
            q_rule.append(dict(rule=f"equal {key}", design=row["design"], packages=n,
                               per_user_dflash_b1=row["dflash_tokens_s_b1"], per_user_ar_b1=row["ar_tokens_s_b1"],
                               aggregate_tokens_s=round(n * row["saturated_tokens_s"], 1),
                               capacity_users=n * row["capacity_users"]))
    return dict(
        v41_rom=dict(die_shrink_sensitivity=die_shrink, counts=counts, stage_table=stage_table, legal_phy_sensitivity=legal_phy,
                     product_basis=dict(zip(("bf16", "pitch", "density", "overhead", "credit"), PB)),
                     droop=dict(DROOP, product=cons_droop(head)), fp32_add_ss=FP32_ADD_SS,
                     cdc=dict(CDC_W18, vm_port_area_mm2=dict(
                         before=area_ledger(PRESETS["proposal"])["vm_ports"],
                         after=round(area_ledger(PRESETS["proposal"])["vm_ports"] * 4 / 3, 3)),
                              added_wires={k: b - a for k, (a, b) in CDC_W18["vm_port_widening"]["bits_before_after"].items()}),
                     ss=dict(rows=[p["label"] for p in ss_rows], curve=ss_curve, tt_clock_hz=tt, ss_logic_clock_hz=ss_logic,
                             derate=SS_DERATE, derate_measured=SS_DERATE_MEASURED,
                             depth_options=ROM_DEPTH_OPTS, depth_src=ROM_DEPTH_SRC),
                     bf16_hub_unit_mm2=round(cons_bf16_hub_mm2(), 2),
                     product=dict(status=f"{head['dies']} dies: {head['stages']} TP-4 stages ({head['layer_dies']} layer "
                                         "dies, BF16 COLUMNS (1,024 at W10b's 1,002.89 x 142.56 um column outline) with q "
                                         "pairs at W10b's 510.84 x 126.9 um tile (floorplan sizes; routed closure "
                                         "pending p12q4 / c5) and W11's C_rotate SU+VM hub block (38.60 mm2; root "
                                         "rulings 2026-10-01: on W18b's plus hub, op +37 / red +28; lane-local fusion on W11's families, modelled, RTL pending; "
                                         "measured VM-H kept as the comparison row) -- USER DECISION: maximum per-user rate, die "
                                         f"count free) + {head['head_dies']} head dies (8192m8 ping-pong; see head_fit: "
                                         f"{hp_prev} at W10's tile, re-fit pending) + {head['table_dies']} Engram table dies (storage-only basis; "
                                         "ASAP7 feasibility 20).  Why the columns: on the full-token basis they give the "
                                         "highest per-user rate; W10's busiest-die op cycles favoured (iii), but its +20.7% "
                                         "pair pitch adds stages (hops) and its BF16 issue floors exceed the columns' "
                                         "full-width BF16 lanes.  References in bf16_full_token",
                                  bf16_full_token=bf16_full_token,
                                  option_ii_area_breakeven_mm2_for_31_stages=11.4,
                                  head_fit=head_fit,
                                  reference_for_comparisons=dict(stages=head["stages"], layer_dies=head["layer_dies"],
                                                                 head_dies=head["head_dies"],
                                                                 table_dies=head["table_dies"], dies=head["dies"],
                                                                 label=head["label"],
                                                                 basis="storage-only 75.0, BF16 on the standard pair, "
                                                                       "W10 budget pitch, 12.5%, ring credit, 4096m8")),
                     points=points, refit=CONS_REFIT, geometries=CONS_GEOM, credit_modes=CONS_CREDIT,
                     pitches=CONS_PITCH, bf16=CONS_BF16, field_mm2=round(CONS_FIELD_MM2, 2), sliver_mm2=round(CONS_SLIVER_MM2, 2),
                     strip_per_pair_mm2=round(CONS_STRIP_PER_PAIR_MM2, 6), table_macro_mm2=round(CONS_TABLE_MACRO_MM2, 6),
                     density=DENSITY, constants=CONS),
        hbm=dict(right_sized=dies, shoreline=HBM_SHORE, v41_sweep=sweep, v41_capacity_min_dies=minN,
                 v41_dies_for_rom_users=users_866, qwen=qwen, existing_rule_note=(
                     "arch_budget_v41.hbm_comparator sizes 99 (model: 96) dies by ISO LOGIC AREA with the ROM array's "
                     "188 dies of analytical logic; capacity_limit's hbm_users (811) uses the busiest-die rule of a "
                     "pipelined placement, whereas the TP-96 comparator holds 1/96 of every layer's KV per die")),
        headline_table=cons_headline_table(head, rule, qwen, ec, pc),
        tau_sweep_1m=cons_tau_sweep([(x["design"], dict(mtp=x.get("per_user_mtp")))
                                     for x in cons_headline_table(head, rule, qwen, ec, pc)["v41"]]),
        short_context_8k=cons_short_context(Sp, hp, t_a, head, ec, gr, 8192),
        gpu_calibration=gpu_calibration_row(ec),
        qwen_context_sweep=qwen_context_sweep(ec),
        qwen_helix_200k=qwen_helix_scaleout(ec),
        qwen_product_ss=qwen_product_ss(), qwen_l0_rtl_vs_model=qwen_l0_rtl_vs_model(),
        hbm_collective_sensitivity=dict(model=188, audit=228, w19_exact_minimised=265, w19_exact_unfused=305,
                                        audit_central_ar=2394.5, at_265_ar=round(1 / (1 / 2394.5 + 37 * 0.83e-6), 1),
                                        at_305_ar=round(1 / (1 / 2394.5 + 77 * 0.83e-6), 1),
                                        src="W19 claude/w19-hbm-token f364f884 (exact TP-96 program, layer 0 bit-exact); "
                                            "collectives at the audit's 0.83 us scratch switch latency; PENDING W19's "
                                            "final count and W15's P = 48 fit"),
        comparison_rule=dict(v41_targets=tgt, v41=rule, qwen=q_rule,
                             basis="ROM = the consolidated analytical headline; power = the gated saturated AR system "
                                   "power (both sides, the adopted gated-alike policies); cost = manufacturing capex "
                                   "low (die area x yield, packages, stacks, NRE / 1,000); HBM beyond 96 dies adds "
                                   "whole TP-96 replicas"),
        karb=cons_karb_delta(Sp, clock_hz=PRODUCT_CLOCK_HZ),
        model_caveats=MODEL_CAVEATS,
        clock_basis=dict(clock_hz=PRODUCT_CLOCK_HZ, note="USER DECISION (AGENTS.md e7479589): every design at 1.2 GHz SS "
                         "for equal footing -- V4.1 ROM product rows, the V4.1 HBM sweep and comparison rule (cycle terms "
                         "comparator is HBM-bandwidth bound, so its rate does not move with the clock",
                         v41_hbm_96x4_tt=v41_hbm_n(96, 4, ec, gr)["ar"]["batch1"]["per_user_tokens_s"],
                         v41_hbm_96x4_1p2=v41_hbm_n(96, 4, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)["ar"]["batch1"]["per_user_tokens_s"],
                         qwen_rom_c_1p2=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ)["tokens_s_b1"],
                         qwen_rom_c_1p2_w12_tp4_wires=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ,
                                                                    me_lat_extra=QWEN_W12_TP4_ME_EXTRA)["tokens_s_b1"],
                         qwen_rom_c_1p2_w12_tp4_ss_reach=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ,
                                                                       me_lat_extra=QWEN_W12_TP4_ME_EXTRA_SS)["tokens_s_b1"],
                         v41_hbm_w13_ss_note="W13 at SS pre-layout: an 8-stage fp32_add_rne_pipe breaks the IL = 8 "
                                             "circulating accumulator; IL = 16 gives V4.1 HBM ~2,500 AR (from ~2,920); "
                                             "a 7-stage adder keeps IL = 8 (W13 estimate, not priced here)",
                         qwen_rom_c_tt=pc["tokens_s_b1"]),
        clock_domain_cases=cons_clock_cases(Sp, hp, t_a),
        qwen_rom=dict(product="C", product_row=pc, options=qo, small_die=qwen_small_die(),
                      alternatives=dict(A="alternative: fastest per dollar, but an undemonstrated 3-reticle 12-stack "
                                          "package", B="alternative: 3 single-die packages, TP-3 over board links",
                                        D="alternative: the 2-die reference, fits only with the compute-in-ROM "
                                          "UPSIDE (assumed cell multiplier, unimplemented mechanism)"),
                      sensitivity="G 7,168 a die (9,597 tok/s, 18.6% bank padding): a new die for +2.4%"),
        fab=FAB,
        die_costs={f"{a:g} mm2": die_cost(a) for a in (815.0,) + tuple(sorted({v["die_mm2"] for v in dies.values()}))})


# ---- Qwen ROM at the storage-only density (root ruling 2026-09-30): the dies it needs, and the options priced ----
QWEN_DENSITY = dict(
    storage_n5=dict(mbit_mm2=None, label="storage-only N5 (75.0 Mbit/mm2, the ruled basis) + SECDED 266/256"),
    roma=dict(mbit_mm2=57.8, label="ROMA TSMC 7 nm compiler (conservative sensitivity) + SECDED"),
    cirom_upside=dict(mbit_mm2=None, label="compute-in-ROM UPSIDE: the Qwen ledger's 148 Mbit/mm2 = N6 storage / an "
                                         "ASSUMED 1.6x cell multiplier x a vendor-quoted 4 bits a cell; unimplemented "
                                         "mechanism (no compute-in-ROM cell in this repository's RTL)"),
)
QWEN_TILE_FIXED_MM2 = 4 * 10.0 + 10.0 + 12.8      # 4 HBM PHY + UCIe PHY + stream-unit spill: per die, not per group
QWEN_ECC = 266 / 256


def _qwen_rom_bits():
    qp = json.loads((ROOT / "results/floorplan/qwen_o4_rom_placement.json").read_text())
    t, cr = qp["totals"], qp["code_rom"]
    drafter = cr["drafter_words"] * cr["word_columns"] * 256
    return dict(stored_bits_per_die=t["stored_bits"], drafter_bits_per_die=drafter,
                target_bits_total=2 * (t["stored_bits"] - drafter),
                cirom_mbit_mm2=t["stored_bits"] / t["ledger_rom_mm2_n6"] / 1e6)


def qwen_rom_area_per_group_mm2():
    """Non-ROM tile area per group (pruned group logic at 50% + KV ring SRAM), from the G = 6,144 fit (552.9 mm2 of
    which 265.0 ROM and QWEN_TILE_FIXED_MM2 fixed)."""
    return (552.9 - QWEN_ROM_AREA_DIE["rom"] - QWEN_TILE_FIXED_MM2) / 6144


def qwen_rom_need_mm2(k, G, density="storage_n5"):
    b = _qwen_rom_bits()
    m = (_V41_ASM["rom_density_mbit_per_mm2"] if density == "storage_n5" else
         b["cirom_mbit_mm2"] if density == "cirom_upside" else QWEN_DENSITY[density]["mbit_mm2"])
    ecc = 1.0 if density == "cirom_upside" else QWEN_ECC
    rom = b["target_bits_total"] * ecc / (m * 1e6) / k
    return dict(rom_mm2=rom, need_mm2=QWEN_TILE_FIXED_MM2 + qwen_rom_area_per_group_mm2() * G + rom,
                avail_mm2=QWEN_AREA["array_mm2"])


QWEN_TP_SHAPE = {2: (16, 4), 3: (12, 3), 4: (8, 2)}   # busiest die's (query heads, KV heads): GQA groups of 4 whole


def _qwen_exchange(kind, k, clock):
    """Per-token exchange cycles (72 all-reduces + the argmax gather) and the embedding handoff, by link class."""
    cf = w15_record()["configs"]
    ref = cf[QWEN_EXCHANGE]["exchanges"]
    if kind == "ucie_measured":
        ar, ga, src = ref["allreduce_cycles_mean"], ref["argmax_gather_cycles"], "MEASURED (W15 q256d64, TP-2 UCIe)"
    elif kind == "ucie_tp3_assumed":
        ar, ga = ref["allreduce_cycles_mean"] + FADD_PIPE, ref["argmax_gather_cycles"]
        src = ("ASSUMED from the W15 TP-2 measurement: a one-shot to 2 peers over direct UCIe adds one FP32 add stage "
               "(+5 cycles) to the 71-cycle all-reduce")
    else:
        # the V4.1 TP-4 group measured over direct T1 board links (2 packages x 2 dies), W3 placement, depth 1,024:
        # transferred to the Qwen payload (H = 4,096 FP32 partials) and clock
        ar = w15_collective_s("v41p17_r0d1024", "all_reduce", 4096 * 4, 4) * clock
        ga = w15_collective_s("v41p17_r0d1024", "all_gather", 8 * k, k) * clock
        src = ("MEASURED on the V4.1 TP-4 group (W15 v41p17_r0d1024 fit: 2 packages x 2 dies, direct T1 board links), "
               "transferred to the Qwen payload and clock" + ("" if k == 4 else "; TP-3 over board links ASSUMED at the "
                                                               "TP-4 fit"))
    tok = (2 * 36) * ar + ga
    return dict(per_allreduce_cycles=round(ar, 1), argmax_gather_cycles=round(ga, 1), token_cycles=round(tok),
                source=src, per_allreduce_ns=round(ar / clock * 1e9, 1))


QWEN_W12_TP4_ME_EXTRA = 24 + 3 * 5 + 22 + 4 + 1   # W12 (a760c255, 2026-09-30): at TP-4, BD 24, NWS 3 x 5 levels,
                                                  # TWS 22, ORD 4, + MEM_EXTRA 1 (the 4096x266 pin-capture register
                                                  # b274bda5, needed at SS) = 66 cycles an ME op (W12 2-die: 81)


def qwen_tp_point(k, G, link, wire_model="w12", clock_hz=None, me_lat_extra=None, ctx=8192, su_width=1024):
    """Qwen3-8B ROM on k dies (TP-k), G groups a die, 8K, AR: the calibrated replay of the busiest die's slice, the
    W12 floorplan wires, and the exchange of the given link class."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    Q.CLOCK[0] = clock_hz or Q.clock_hz()
    clock = Q.CLOCK[0]
    cf = w15_record()["configs"]
    oldw = {n: v["clock_hz"] for n, v in cf.items() if n.startswith("v41")}
    if clock_hz:                   # SS: the measured board-exchange cycles take the SS period (as the V4.1 SS pass)
        for n in oldw:
            cf[n]["clock_hz"] = clock_hz
    nh, kv = QWEN_TP_SHAPE[k]
    shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // k), V=-(-Q.Q["V"] // k))
    k0 = dict(T.K)
    try:
        if wire_model == "w12":
            T.K["me_lat"] = k0["me_lat"] + (QWEN_WIRE_W12["me_lat_extra"] if me_lat_extra is None else me_lat_extra)
        r = Q.as_built(ctx, groups=G, su_width=su_width, shape=shp, ucie=False)
    finally:
        T.K.clear()
        T.K.update(k0)
    x = _qwen_exchange(link, k, clock)
    emb = Q.tp_exchanges(clock)["embedding_handoff_cycles"]
    if link not in ("ucie_measured", "ucie_tp3_assumed"):
        emb += w15_collective_s("v41p17_r0d1024", "all_gather", 8, k) * clock    # the row crosses a board link
    for n, v in oldw.items():
        cf[n]["clock_hz"] = v
    cycles = r["cycles"] + x["token_cycles"] + math.ceil(emb)
    ub = r["unit_busy"]
    wl, kvb = _qwen_wl()
    kvfrac = kv / Q.Q["KV"]
    lanes = ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]
    bounds = dict(lanes=clock / lanes, stream_unit=clock / ub["stream"], kv_stream=4 * HBM_STACK_BPS / (kvb * kvfrac))
    sat = min(bounds.values())
    users = int(4 * HBM_STACK_B * HBM_CAP_EFF // (kvb * kvfrac))
    # integer banks: a group-pair column holds its share of the target words in whole 4,096-deep banks
    words = 38880 * (2 / k) * 6144 / G
    banks = math.ceil(words / 4096)
    area = qwen_rom_need_mm2(k, G)
    rom_mm2 = area["rom_mm2"]
    st = _static_w(G * QWEN_AREA["logic_group_pruned_um2"] / 1e6 + QWEN_TILE_FIXED_MM2, rom_mm2,
                   G * QWEN_AREA["kv_sram_group_um2"] / 1e6, clock, 4)
    return dict(k=k, G=G, link=link, cycles=cycles, tokens_s_b1=round(clock / cycles, 1), clock_hz=clock, unit_busy=ub,
                layer_chain_cycles=r["layer_chain"]["cycles"], ctx=ctx, su_width=su_width,
                exchange=x, saturated_tokens_s=round(sat, 1), bounds={a: round(b, 1) for a, b in bounds.items()},
                binding=min(bounds, key=bounds.get), capacity_users=users,
                banks_per_column=banks, column_words=round(words), bank_padding=round(1 - words / (banks * 4096), 4),
                static_w_per_die=round(sum(st.values()), 2), area_need_mm2_per_die=round(area["need_mm2"], 1),
                rom_mm2_per_die=round(rom_mm2, 1), fits_storage_n5=area["need_mm2"] <= area["avail_mm2"])


def qwen_rom_options(ec=None):
    """Root 2026-09-30: the Qwen ROM does not fit two reticles at the storage-only density; price the options."""
    ec = ec or economics()
    qr = ec["qwen_rom"]
    ucie_ref_j = qr["energy"]["categories_mJ_per_token"]["ucie"] * 1e-3
    dyn_ref = qr["energy"]["dynamic_mJ_per_token"] * 1e-3
    import arch_budget_qwen3 as Q
    xbytes = Q.tp_exchanges(Q.clock_hz())["bytes_per_direction"]
    opts = dict(
        A=dict(k=3, link="ucie_tp3_assumed", packages=[(1, "cowos_l_3die")], demonstrated=False,
               what="3 dies in ONE package (12 stacks; not demonstrated), TP-3 over UCIe"),
        B=dict(k=3, link="board", packages=[(3, "cowos_s_1die")], demonstrated=True,
               what="3 single-die packages (4 stacks each, H100-class), TP-3 over board links"),
        C=dict(k=4, link="board", packages=[(2, "cowos_l_2die")], demonstrated=True,
               what="2 B200-class packages (2 dies + 8 stacks each), TP-4 with one package crossing"),
        D=dict(k=2, link="ucie_measured", packages=[(1, "cowos_l_2die")], demonstrated=True,
               what="the 2-die reference: fits only with the compute-in-ROM UPSIDE (148 Mbit/mm2; assumed cell "
                    "multiplier, unimplemented mechanism)"),
    )
    pk_usd = dict(FAB["package_usd"], cowos_l_3die=1.5 * FAB["package_usd"]["cowos_l_2die"])
    out = {}
    for key, o in opts.items():
        k = o["k"]
        rows = []
        for G in (2048, 3072, 4096, 5120, 6144, 7168, 8192):
            dens = "cirom_upside" if key == "D" else "storage_n5"
            fit = qwen_rom_need_mm2(k, G, dens)
            if fit["need_mm2"] > fit["avail_mm2"] and not (G == 12288 // k):
                continue
            p = qwen_tp_point(k, G, o["link"])
            p["fits"] = fit["need_mm2"] <= fit["avail_mm2"]
            p["area_need_mm2_per_die"] = round(fit["need_mm2"], 1)
            link_j = E_LINK["ucie"] if o["link"].startswith("ucie") else E_LINK["board"]
            dyn = dyn_ref - ucie_ref_j + xbytes * 2 * 8 * link_j * (k - 1)
            P_st = k * p["static_w_per_die"]
            hw = mfg_cost([(k, FLOORPLAN["die_mm2"])], [], 4 * k, rom_dies=k,
                          rom_bases=FAB["mask_sets"]["qwen_rom_bases"])
            pkg = sum(n * (pk_usd[c] + FAB["test_assembly_usd"]) for n, c in o["packages"])
            capex = dict(low=hw["capex_usd"]["low"] + round(pkg), high=hw["capex_usd"]["high"] + round(pkg))
            hw_usd = hw["hardware_usd"] + round(pkg)
            p.update(system_static_w=round(P_st, 1), dynamic_mJ=round(dyn * 1e3, 2),
                     mJ_b1=round((dyn + P_st / p["tokens_s_b1"]) * 1e3, 2),
                     mJ_saturated=round((dyn + P_st / p["saturated_tokens_s"]) * 1e3, 2),
                     die_usd=round(k * die_cost(FLOORPLAN["die_mm2"])["usd"]), package_usd=round(pkg),
                     hbm_usd=4 * k * FAB["hbm_stack_usd"], hardware_usd=hw_usd, capex_usd=capex,
                     tokens_s_per_kusd=round(p["tokens_s_b1"] / hw_usd * 1e3, 2))
            rows.append(p)
        tot = next((r for r in rows if r["G"] * k == 12288), None)
        fitting = [r for r in rows if r["fits"]]
        best = max(fitting, key=lambda r: r["tokens_s_b1"] / r["hardware_usd"]) if fitting else None
        out[key] = dict(o, total_G_12288=tot, best_tokens_s_per_usd=best, rows=rows,
                        gated_note="gated = ungated: the Qwen ROM's idle gaps are shorter than wake + break-even "
                                   "(gated-alike table)")
    import arch_budget_qwen3 as Q2
    ss_hz = Q2.clock_hz() / SS_DERATE
    ss = []
    for G, tag in ((6144, "product (option C, G 6,144)"), (4928, "ROMA-safe sensitivity (G 4,928)")):
        for hz, corner in ((None, "TT"), (ss_hz, "SS (logic derated 1.27)")):
            p = qwen_tp_point(4, G, "board", clock_hz=hz)
            ss.append(dict(point=tag, corner=corner, clock_hz=p["clock_hz"], tokens_s_b1=p["tokens_s_b1"],
                           saturated_tokens_s=p["saturated_tokens_s"], binding=p["binding"]))
    Q2.CLOCK[0] = Q2.clock_hz()
    g_search = dict(finding="the TP-4 token is not lane-bound: G 6,144 -> 6,336 buys +0.04% (9,367.6 -> 9,371.4 tok/s) "
                            "and the saturated rate is KV-stream bound at every G >= 4,096, so extra area does not buy "
                            "per-user speed; legal G step is 64 groups (the program's embedding-word rule)",
                    chosen=6144, largest_with_2pct_margin=6336, roma_safe=4928)
    return dict(options=out, rom_bits=_qwen_rom_bits(), corners=ss, g_search=g_search, per_group_mm2=round(qwen_rom_area_per_group_mm2(), 6),
                fixed_mm2=QWEN_TILE_FIXED_MM2, densities=QWEN_DENSITY,
                fit_by_density={d: {k: round(qwen_rom_need_mm2(k, 12288 // k, d)["need_mm2"], 1) for k in (2, 3, 4)}
                                for d in QWEN_DENSITY},
                package_basis=dict(FAB["package_basis"], cowos_l_3die="ASSUMED 1.5 x the 2-die CoWoS-L (no 3-reticle "
                                                                       "package is demonstrated)")
                if isinstance(FAB["package_basis"], dict) else FAB["package_basis"]
                + "; 3-die CoWoS-L ASSUMED 1.5 x the 2-die price (no 3-reticle package is demonstrated)")


# ---- K arbiter round trip (W18, root relay 2026-09-30) ----
KARB = dict(base_cycles=7, per_hop_cycles=2,
            region_distance_mm=(3.5, 2.5, 1.5, 0.5, 0.5, 1.5, 2.5, 3.5),
            reach_mm_tt=1.0, reach_mm_ss=0.75,
            src="W18: the pipelined, credited K arbiter's uncontended added K round trip is 7 + 2 x (hops - 1) cycles; "
                "regions along the 8.5 mm PHY edge give 13/11/9/7/7/9/11/13 cycles at 1 mm hops (TT), up to 15 at the "
                "likely SS reach of 0.75 mm (W15 measuring); region distances here reproduce those counts")


# W18b e909156c (root relay 2026-10-01): MERGE2 alone fails SS (-212 ps); MERGE2 + HEADREG (54/54 equivalence-clean,
# P&R running) adds +2 to the K round trip on the shrunk die (MERGE2's 19/15/13/9/9/13/15/19 superseded until the P&R
# verdict)
KARB_W18B_HEADREG = (21, 17, 15, 11, 11, 15, 17, 21)   # W18b f53e3be0: pregion centre queue, +3 (was +2: 20/16/...)


def karb_region_cycles(reach_mm):
    return [KARB["base_cycles"] + KARB["per_hop_cycles"] * (math.ceil(d / reach_mm - 1e-9) - 1)
            for d in KARB["region_distance_mm"]]


def cons_karb_delta(S=None, reach_mm=None, clock_hz=None):
    """Token-path cost of the K arbiter round trip: every HBM-touching node on the critical path (the index-selected
    row gathers, the index-key scans, the window-row score reads) pays the round trip once (its stream is then
    pipelined).  Worst region (all requests from the farthest region) and region mean; the model charged none."""
    S = S or cons_min_stages("analytical")
    with _cons_stages(S):
        r, b = arch_graph(1048576)
        g = b.g
        path = g.path(b.sink)
    n = sum(1 for x in path if x.endswith((".gather", "idx.score", ".attn.scores")))
    clock = clock_hz or A._env()["clock"]
    T = r["T_s"]
    out = {}
    for tag, reach in (("tt_1mm", KARB["reach_mm_tt"]), ("ss_0p75mm", KARB["reach_mm_ss"])) + (
            (("custom", reach_mm),) if reach_mm else ()):
        cyc = karb_region_cycles(reach)
        for kind, c in (("worst", max(cyc)), ("mean", sum(cyc) / len(cyc))):
            dt = n * c / clock
            out[f"{tag}_{kind}"] = dict(reach_mm=reach, cycles_per_request=round(c, 2), requests_on_path=n,
                                        added_us=round(dt * 1e6, 3), tokens_s_delta_pct=round(-dt / (T + dt) * 100, 3))
    # W18b (f53e3be0 results/rtl/chip_v41x_karb_pipe_equiv_w18_cq.json, 54/54): MERGE2 + HEADREG + the pregion centre
    # queue: the K round trip is 21/17/15/11/11/15/17/21 (regions 0-7, +3); pregion still fails SS (-224 ps); a row
    # only, not in the product
    cyc = KARB_W18B_HEADREG
    for kind, c in (("worst", max(cyc)), ("mean", sum(cyc) / len(cyc))):
        dt = n * c / clock
        out[f"w18b_merge2_headreg_{kind}"] = dict(cycles_per_request=round(c, 2), requests_on_path=n, added_us=round(dt * 1e6, 3),
                                          tokens_s_delta_pct=round(-dt / (T + dt) * 100, 3))
    return dict(rows=out, regions_w18b_merge2_headreg=list(KARB_W18B_HEADREG), regions_tt=karb_region_cycles(KARB["reach_mm_tt"]),
                regions_ss=karb_region_cycles(KARB["reach_mm_ss"]), stages=S, basis=KARB)


# W19 HBM feasibility audit (claude/w19-hbm-audit aa0ac6bd, results/uarch/hbm_feasibility_audit.json; root 2026-09-30):
# central estimates against main's model at 1.2 GHz (3,071.7 AR / 6,206.0 MTP): 2,394.5 AR / 5,227.7 MTP (range AR
# 2,196-2,905, MTP 4,951-6,161).  Optimistic terms: routed-expert fetch after the router, measured switch latency,
# +1 gather a MoE layer for the exact expert order, 34.6 distinct experts a layer over 6 positions, serial units in the
# 0.9 GHz domain, the drafter on the 96-die graph; pessimistic: indexer at 1/96 keys, 1 head a die.  Applied here as
# ratios to the tier-3 per-user rates (the saturated column is left at the model's pass bound, labelled).
HBM_AUDIT = dict(ar=2394.5 / 3071.7, mtp=5227.7 / 6206.0, ar_range=(2196.2 / 3071.7, 2905.0 / 3071.7),
                 mtp_range=(4951.1 / 6206.0, 6160.6 / 6206.0), qwen_dflash=0.86, qwen_dflash_block12=2296.0,
                 src="claude/w19-hbm-audit aa0ac6bd results/uarch/hbm_feasibility_audit.json (summary.realistic_range)",
                 rom_side="the exact-order extra gather does not apply to the ROM array: a macro sums its experts in id "
                          "order inside the element and the TP-4 combine is a fixed-order all-reduce (no cross-die "
                          "expert partials to re-order); the 0.9 GHz serial domain is already in the ROM product")


# W19 COMPOSED V4.1 HBM token (claude/w19-hbm-token 71b3ffc5, results/uarch/w19_hbm_token_{ar,ar_fused,mtp,mtp_fused}_wsel256
# .json; supersedes a88743ff / d5ce14e7 / d1cc2234 / 23648fc3 / c350be7f): every term priced along the executed TP-96 program,
# collectives on W15b's committed P=48 NVLS record and W15b's MEASURED WIDE 96-way top-k select (P = 1,024 / PF = 256:
# 419 cycles, claude/w15-ss 082f11b2; one unit, the MTP pass's 6 positions in series; the P = 64 unit's 3,875 cycles
# stays W19's narrow variant).  The baseline includes the FP8 activation quantisers.  Lane-local fusion (USER RULE, the
# same as the ROM's for fairness): AR 458.46 -> 442.14 us, MTP verify pass 747.31 -> 715.82 us; MTP adds the audit's
# drafter 49.9 us.  Still labelled: the grouped o-reduce is extrapolated from the all-reduce fit.
HBM_W19 = dict(ar_us=442.14, ar_unfused_us=458.46, mtp_pass_us=715.82, mtp_pass_unfused_us=747.31, drafter_us=49.9,
               collectives=265,
               parts_us_fused=dict(sm=70.58, barrier=22.29, collective=240.46, local=103.48, fetch=5.33),
               parts_us_unfused=dict(sm=70.58, barrier=22.29, collective=240.46, local=119.8, fetch=5.33),
               mtp_parts_us_fused=dict(sm=128.11, barrier=22.29, collective=326.81, local=199.64, fetch=38.97),
               fusion=f"conservative-equivalent ({FUSION_LABEL})",
               src="claude/w19-hbm-token 71b3ffc5 results/uarch/w19_hbm_token_{ar,ar_fused,mtp,mtp_fused}_wsel256.json "
                   "(result.total_us, result.parts_us); wide select PF = 256 MEASURED claude/w15-ss 082f11b2")
HBM_W19["ar_tokens_s"] = 1e6 / HBM_W19["ar_us"]
HBM_W19["ar_tokens_s_unfused"] = 1e6 / HBM_W19["ar_unfused_us"]
HBM_W19["mtp_tokens_s"] = V41_TAU * 1e6 / (HBM_W19["mtp_pass_us"] + HBM_W19["drafter_us"])
HBM_W19["mtp_tokens_s_unfused"] = V41_TAU * 1e6 / (HBM_W19["mtp_pass_unfused_us"] + HBM_W19["drafter_us"])
# Dataflow level H5 (GPU-real; USER DECISION AGENTS.md a4f314fb): a TMEM-style accumulator memory with register
# epilogues on the HBM SM's column outputs (W13b claude/w13-blockdot12 f984ba8d results/uarch/hbm_sm_epilogue_study.json,
# model-level): norm sum-of-squares partials, block-32 quantise and the residual / mHC-post add leave the path.  AR saves
# 11.6 us on W13b's own basis (356.9 -> 345.3 us, +3.4%); FA's re-pricing on W19's program (claude/fusion-audit a86b17cd)
# gives 6.1 us AR / 11.8 us a verify pass.  Charged here: W13b's 11.6 us AR, FA's 11.8 us MTP pass.  Qwen HBM: 0 (the
# token is HBM-bound).  modelled; RTL pending
HBM_TMEM = dict(ar_us=11.6, ar_us_fa_w19_program=6.1, mtp_pass_us=11.8, qwen_us=0.0, area_mm2_per_die_v41=1.37,
                src="W13b claude/w13-blockdot12 f984ba8d hbm_sm_epilogue_study.json; FA a86b17cd fusion_audit.json (H5)")
# FA (claude/fusion-audit a86b17cd, results/uarch/fusion_audit.json v41_rom rows): the product graph's solve assumes
# perfect SU interleaving; the die issues SU ops in order and drains on a dependent pair.  An in-order SU in graph
# emission order adds 37.05 us to the AR token if pipelined and 86.99 us if blocking (MTP pass +81.62 / +141.18 us),
# measured on the L1 fused product.  ROOT RULING 2026-10-01: a caveat row, applied additively to the headline.
# W11's u2517 reduced historical vehicle measured 398,676 cycles against 344,131 model cycles (overall FAIL).
# That trace scopes a reduced-vehicle caveat; it cannot replace this product exposure with a raw ratio.
FA_INORDER = dict(ar_us_pipelined=37.054, ar_us_blocking=86.991, mtp_pass_us_pipelined=81.616, mtp_pass_us_blocking=141.184,
                  src="claude/fusion-audit a86b17cd results/uarch/fusion_audit.json v41_rom.rows (L4_in_order_*)")


def cons_in_order_caveat(ar, mtp):
    """The FA in-order SU exposure on a V4.1 ROM row: AR period and the MTP effective period (tau / rate) + FA's us."""
    out = {}
    for k in ("pipelined", "blocking"):
        a = 1 / (1 / ar + FA_INORDER[f"ar_us_{k}"] * 1e-6)
        m = V41_TAU / (V41_TAU / mtp + FA_INORDER[f"mtp_pass_us_{k}"] * 1e-6)
        out[k] = dict(ar_tokens_s_b1=round(a, 1), mtp_tokens_s_b1=round(m, 1), ar_pct=round(100 * (a / ar - 1), 1),
                      mtp_pct=round(100 * (m / mtp - 1), 1))
    return dict(out, basis=FA_INORDER, label="CAVEAT (FA): in-order SU issue with drain on dependence; product overlap "
                                             "remains uncalibrated. W11 u2517 is a reduced historical vehicle "
                                             "with overall FAIL; its model / RTL ratio is not a product correction")


def cons_headline_table(head, rule, qwen, ec, pc):
    """USER OBJECTIVE: minimum single-user decode latency first; saturated throughput is secondary.
    Energy and cost comparisons use EQUAL MANUFACTURING COST; per-user speed is claimed against real GPUs
    (tier 1 measured, tier 2 calibrated) and
    reported against the idealised HBM machine (tier 3).  Qwen ROM keeps its per-user claim.  Every row names its
    point; ROM energies include the adopted 256-cycle pre-ramp."""
    dr = cons_droop(head)["50% cap + 256-cycle pre-ramp"]
    g = ec["gpu"]
    cst = {c["design"]: c for c in ec["cost"]}
    v41 = [dict(design="V4.1 ROM array (product basis, 1.2 GHz SS, SS wires, 50% cap + pre-ramp)", tier="ROM",
                per_user_ar=head["ar_tokens_s_b1"], per_user_mtp=head["mtp_tokens_s_b1"],
                per_user_mtp_headline_tau_3p78=round(head["mtp_tokens_s_b1"] * 3.78 / V41_TAU, 1),
                saturated_tokens_s=head["ar_saturated_tokens_s"], mJ_b1=dr["gated_mJ_b1"], mJ_saturated=dr["gated_mJ_saturated"],
                capex_usd=head["cost"]["capex_usd"], silicon_mm2=head["silicon_mm2"], users_1m=head["capacity_users_1m"],
                system_w_saturated=head["energy"]["ar_sat"]["gated_system_w"], fusion_label=FUSION_LABEL,
                in_order_su_caveat=cons_in_order_caveat(head["ar_tokens_s_b1"], head["mtp_tokens_s_b1"]))]
    for x in rule:
        if x.get("stacks_per_die") == 4 and "ar" in x:
            v41.append(dict(design=f"V4.1 HBM tier 3 (idealised), {x['rule']}: {x['replicas']} x TP-{x['tp']} ({x['dies']} "
                                   f"right-sized dies, 1.2 GHz, SS wires; W19 composed token)", tier="3",
                            per_user_ar=round(HBM_W19["ar_tokens_s"], 1), per_user_mtp=round(HBM_W19["mtp_tokens_s"], 1),
                            fusion=HBM_W19["fusion"],
                            per_user_ar_tmem_h5=round(1e6 / (HBM_W19["ar_us"] - HBM_TMEM["ar_us"]), 1),
                            per_user_mtp_tmem_h5=round(V41_TAU * 1e6 / (HBM_W19["mtp_pass_us"] - HBM_TMEM["mtp_pass_us"]
                                                                       + HBM_W19["drafter_us"]), 1),
                            tmem_h5_label=f"H5 TMEM-style epilogue ({FUSION_LABEL}): only the us DELTA is applied to W19's "
                                          "composition -- AR -11.6 us (W13b's dependent latency removed; W13b's absolute "
                                          "basis 356.9 -> 345.3 us differs from W19's 442.1 us and is not used), MTP pass "
                                          "-11.8 us (FA's H5 on W19's program)",
                            per_user_ar_unfused=round(HBM_W19["ar_tokens_s_unfused"], 1),
                            per_user_mtp_unfused=round(HBM_W19["mtp_tokens_s_unfused"], 1),
                            select_note="W15b's WIDE 96 x 512 top-k select MEASURED (419 cycles at P = 1,024 / PF = "
                                        "256); one unit, the MTP pass's 6 positions in series",
                            per_user_ar_audit_central=round(x["ar"]["batch1"]["per_user_tokens_s"] * HBM_AUDIT["ar"], 1),
                            per_user_mtp_audit_central=round(x["mtp"]["batch1"]["per_user_tokens_s"] * HBM_AUDIT["mtp"], 1),
                            per_user_ar_model=x["ar"]["batch1"]["per_user_tokens_s"],
                            per_user_mtp_model=x["mtp"]["batch1"]["per_user_tokens_s"],
                            per_user_ar_audit_range=[round(x["ar"]["batch1"]["per_user_tokens_s"] * f, 1)
                                                     for f in HBM_AUDIT["ar_range"]],
                            per_user_mtp_audit_range=[round(x["mtp"]["batch1"]["per_user_tokens_s"] * f, 1)
                                                      for f in HBM_AUDIT["mtp_range"]],
                            saturated_note="the model's column-pass bound (the audit prices single-user latency)",
                            saturated_tokens_s=x["ar"]["saturated"]["aggregate_tokens_s"],
                            mJ_b1=x["ar"]["batch1"]["gated_mJ"], mJ_saturated=x["ar"]["saturated"]["gated_mJ"],
                            capex_usd=x["cost"]["capex_usd"], silicon_mm2=x["silicon_mm2"], users_1m=x["capacity_users_1m"]))
    gv = g["v41"]
    v41.append(dict(design="DeepSeek-V4.1-Flash on 8x B200 (tier 2, calibrated)", tier="2", per_user_ar=gv["tokens_s_b1"],
                    per_user_mtp=gv.get("mtp_b1"), saturated_tokens_s=gv["saturated_tokens_s"],
                    mJ_b1=gv["rows"][0]["energy_mJ_per_token"], mJ_saturated=_sat_batch(gv["rows"])["energy_mJ_per_token"],
                    capex_usd=cst["V4.1 8x B200 (tier 2, AR)"]["capex_per_system_usd"], users_1m=gv["capacity_users"],
                    cost_basis="purchase price (iso-package $25k a B200), not manufacturing cost"))
    for a in g["anchors"]:
        if "DeepSeek" in a["design"]:
            v41.append(dict(design=a["design"], tier="1", per_user_mtp=a["per_user_tokens_s"],
                            mJ_b1=a["energy_mJ_per_token_at_689W"]))
    qs = qwen_product_ss()
    q = [dict(design="Qwen ROM option C (4 dies, 2 packages, TP-4, G 6,144), TT", tier="ROM",
              per_user_ar=pc["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"], mJ_b1=pc["mJ_b1"],
              mJ_saturated=pc["mJ_saturated"], capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"]),
         dict(design="Qwen ROM option C at 1.2 GHz SS (W12 SS wires, LAT-7 ME, KV_PREP, droop cap75 + preramp256)", tier="ROM",
              per_user_ar=qs["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"],
              mJ_b1=round(pc["mJ_b1"] + QWEN_SS["droop_mJ"], 1), mJ_saturated=round(pc["mJ_saturated"] + QWEN_SS["droop_mJ"], 1),
              capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"]),
         *[dict(design=f"Qwen ROM option C at 1.2 GHz SS, {qs[k]['label']}", tier="ROM",
                per_user_ar=qs[k]["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"],
                capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"])
           for k in ("rtl_attributed_as_built", "rtl_attributed_body_only")]]
    for row in qwen[1:3]:
        q.append(dict(design=row["design"] + " (tier 3, idealised; DFlash W19 audit -14%)", tier="3",
                      per_user_ar=row["ar_tokens_s_b1"],
                      per_user_dflash=round(row["dflash_tokens_s_b1"] * HBM_AUDIT["qwen_dflash"], 1),
                      per_user_dflash_model=row["dflash_tokens_s_b1"], saturated_tokens_s=row["saturated_tokens_s"],
                      mJ_b1=row["gated_mJ_b1"], mJ_saturated=row["gated_mJ_sat"], capex_usd=row["cost"]["capex_usd"],
                      users_8k=row["capacity_users"]))
    gq = g["qwen"]
    q.append(dict(design="Qwen3-8B on 1x B200, FP8 (tier 2, calibrated)", tier="2", per_user_ar=gq["tokens_s_b1"],
                  per_user_dflash=gq["dflash_b1"], saturated_tokens_s=gq["saturated_tokens_s"],
                  mJ_b1=gq["rows"][0]["energy_mJ_per_token"], mJ_saturated=_sat_batch(gq["rows"])["energy_mJ_per_token"],
                  capex_usd=cst["Qwen 1x B200 (tier 2, AR)"]["capex_per_system_usd"], users_8k=gq["capacity_users"],
                  cost_basis="purchase price"))
    for a in g["anchors"]:
        if "Qwen" in a["design"] and a["batch"] == 1:
            q.append(dict(design=a["design"], tier="1", per_user_ar=a["per_user_tokens_s"],
                          mJ_b1=a["energy_mJ_per_token_at_689W"]))
    return dict(v41=v41, qwen=q, hbm_audit=HBM_AUDIT, rule="USER DECISION 2026-09-30: V4.1 ROM headline = saturated throughput, J/token and "
                                     "cost at equal manufacturing cost; per-user speed claimed against GPUs (tier 1-2) "
                                     "only; Qwen ROM keeps its per-user claim")


def cons_clock_cases(S, h, t):
    """Root 2026-09-30, with W11's MEASURED ns per dependent FP32 add (FP32_ADD_SS).  Every case carries the 50%
    field-concurrency cap and the softplus correction.
    (a) everything at 1.2 GHz: the serial-chain units' adds at 8 or 9 stages (6.7 / 7.5 ns an add), the field
        element's adds at 8 (its chunk-8 chain floor and K-split levels);
    (b) the field, elements, index scan and attention tiles at 1.2 GHz (element adds 8 stages); the serial-chain units
        (SU, SFU, softplus, reducer, Sinkhorn) at 0.9 GHz with LAT 3 (906 MHz SS measured, 3:4) or 0.8 GHz (2:3);
        CDC 2 slow cycles a crossing (ASSUMED);
    (c) everything at 0.9 GHz, LAT 3 (element adds IEEE 5-stage, 992 MHz SS)."""
    out = {}
    for tag, hz, dyn, slow, cs, es in (
            ("a: all 1.2 GHz, chain adds 8 stages", 1.2e9, 1.16, None, 8, 8),
            ("a: all 1.2 GHz, chain adds 9 stages", 1.2e9, 1.16, None, 9, 8),
            ("b: 1.2 GHz field (LAT 7) + 0.9 GHz chain units (LAT 3), W18 CDC", 1.2e9, 1.16, (0.9e9, "w18"), None, 7),
            ("b: 1.2 GHz field (LAT 7) + 0.8 GHz chain units (LAT 3), W18 CDC", 1.2e9, 1.16, (0.8e9, "w18"), None, 7),
            ("c: all 0.9 GHz, LAT 3", 0.9e9, 1.0, None, None, None)):
        p = cons_v41_rom(S, h, t, 1.0, None, "option_iii", hz, FIELD_CONCURRENCY, SOFTPLUS_FIX, dyn, slow, cs, es)
        out[tag] = dict(ar_tokens_s_b1=p["ar_tokens_s_b1"], mtp_tokens_s_b1=p["mtp_tokens_s_b1"],
                        ar_saturated_tokens_s=p["ar_saturated_tokens_s"], mtp_saturated_tokens_s=p["mtp_saturated_tokens_s"],
                        gated_mJ_b1=p["energy"]["ar_b1"]["gated_mJ"], gated_mJ_saturated=p["energy"]["ar_sat"]["gated_mJ"],
                        busiest_stage_us=p["busiest_stage_us"], critical_path_top_us=p["critical_path_top_us"],
                        droop=cons_droop(p))
    return out


# ---- droop at 1.2 GHz (W18 67b0bd49 results/physical_abi3/asap7/chip/v41_w18/droop_schemes_1p2ghz.json) ----
DROOP = dict(field_ops_per_layer_die_per_token=6,
             schemes={"50% cap + 256-cycle pre-ramp": dict(mJ_per_op_start=0.098, extra_latency="the cap's (priced)"),
                      "1,024-cycle pre-ramp, no cap": dict(mJ_per_op_start=0.78, extra_latency=0),
                      "256-cycle pre-ramp, no cap (64 mV at 2 pH: fails 35 mV)": dict(mJ_per_op_start=0.196,
                                                                                      extra_latency=0)},
             src="W18 (root relay 2026-09-30): no fast-start scheme meets 35 mV at L_eff 1-10 pH; a schedule-driven "
                 "pre-ramp dummy-clocks the next op's pairs ahead of time")


PRERAMP_TAU_CYCLES = 256    # ASSUMED droop time constant: a field op after an idle gap longer than the pre-ramp
                            # window needs a ramp (W18 to state the current-decay constant)


def cons_field_starts(g, plan, clock):
    """Field-op starts per layer die per token on the priced single-user graph, and those that follow an idle field
    gap longer than the droop time constant (the only ones that need a pre-ramp; back-to-back field ops keep the
    current up).  A field op is a weight matvec on the ROM field; its start is its finish less its issue and depth."""
    fin = g.solve(True)
    per = {}
    for name, nd in g.nodes.items():
        if not nd.get("_uarch"):
            continue
        s0 = _cons_stage_of(name, nd, plan)
        if s0 == "head":
            continue
        end = fin[name]
        start = end - nd["issue"] - nd["depth"]
        per.setdefault(s0, []).append((start, end))
    tau = PRERAMP_TAU_CYCLES / clock
    out = dict(starts={}, ramps={}, held={})
    for s0, ops in per.items():
        ops.sort()
        ramps, busy_end, held = 1, ops[0][1], 0.0
        for st, en in ops[1:]:
            gap = st - busy_end
            if gap > tau:
                ramps += 1
            elif gap > 0:
                held += gap                  # W18's gap policy: the field is held on through a short gap
            busy_end = max(busy_end, en)
        out["starts"][s0] = len(ops)
        out["ramps"][s0] = ramps
        out["held"][s0] = held * clock
    n = len(per)
    return dict(mean_starts_per_die=round(sum(out["starts"].values()) / n, 2),
                mean_ramps_per_die=round(sum(out["ramps"].values()) / n, 2),
                held_cycles_per_token=round(4 * sum(out["held"].values())),
                max_ramps_per_die=max(out["ramps"].values()), tau_cycles=PRERAMP_TAU_CYCLES,
                layer_die_ramps_per_token=4 * sum(out["ramps"].values()),
                layer_die_starts_per_token=4 * sum(out["starts"].values()))


def cons_droop(p):
    """Pre-ramp energy per token on the layer dies: ops a layer die a token x layer dies x mJ an op start."""
    n = DROOP["field_ops_per_layer_die_per_token"] * p["layer_dies"]
    fs = p.get("field_starts")
    out = {}
    for k, v in DROOP["schemes"].items():
        e = n * v["mJ_per_op_start"]
        row = dict(pre_ramp_mJ_per_token=round(e, 1),
                   gated_mJ_b1=round(p["energy"]["ar_b1"]["gated_mJ"] + e, 1),
                   gated_mJ_saturated=round(p["energy"]["ar_sat"]["gated_mJ"] + e, 1))
        if fs:      # ramp only after an idle gap (root lever / W18's gap policy), counted on the priced graph; a held
                    # gap costs the ramp's energy per cycle (cfg_gap ~ cfg_ramp is energy-optimal, W18)
            eg = fs["layer_die_ramps_per_token"] * v["mJ_per_op_start"] + \
                fs.get("held_cycles_per_token", 0) * v["mJ_per_op_start"] / PRERAMP_TAU_CYCLES
            row.update(gap_only_pre_ramp_mJ_per_token=round(eg, 1),
                       gap_only_gated_mJ_b1=round(p["energy"]["ar_b1"]["gated_mJ"] + eg, 1),
                       gap_only_gated_mJ_saturated=round(p["energy"]["ar_sat"]["gated_mJ"] + eg, 1))
        out[k] = row
    return out


# ---- a smaller Qwen die (root 2026-09-30): the area extra G does not use ----
def qwen_small_die(tiles_mm2=(308.0, 359.0), spine_mm=1.4, margin=0.10):
    """Size the option-C Qwen die to its placed tiles (W12's TP-4 estimate, 1,536 tiles, 308-359 mm2; the routed
    tile area replaces it when it lands) + spine + 4 HBM PHY + UCIe + stream-unit spill + 10% margin, with 4 stacks'
    PHYs on the long edges (2 a side at 8.5 mm).  Also at the ruled storage-only density (the model's tile need)."""
    fixed = QWEN_TILE_FIXED_MM2
    W = 2 * HBM_SHORE["phy_edge_mm"] + 2 * HBM_SHORE["corner_mm"]
    rows = []
    rom75 = qwen_rom_need_mm2(4, 6144)
    pad = qwen_tp_point(4, 6144, "board")["bank_padding"]
    ruled = rom75["need_mm2"] - rom75["rom_mm2"] + rom75["rom_mm2"] / (1 - pad) - fixed
    for tag, t in [(f"W12 estimate {x:g} mm2 (ASAP7 tiles)", x) for x in tiles_mm2] + [
            ("storage-only 75 + ECC tile need (the ruled basis)", ruled)]:
        H, Wd = 0.0, W
        for _ in range(30):                          # the spine runs the die's length; the PHY edge grows past
            area = (t + spine_mm * max(Wd, H) + fixed) * (1 + margin)   # 19 mm when the other side would exceed 26
            Wd = max(W, area / 26.0)
            H = area / Wd
        L = max(Wd, H)
        dc = die_cost(area)
        hw = 4 * dc["usd"] + 2 * (FAB["package_usd"]["cowos_l_2die"] + FAB["test_assembly_usd"]) + 16 * FAB["hbm_stack_usd"]
        rows.append(dict(basis=tag, tiles_mm2=round(t, 1), die_mm2=round(area, 1), outline_mm=(round(Wd, 2), round(H, 2)),
                         fits_reticle=L <= 33.0 and min(Wd, H) <= 26.0, phy_edge_ok=Wd >= W - 1e-9,
                         yield_=dc["yield_"], die_usd=dc["usd"], hardware_usd_4die=round(hw)))
    ref = die_cost(FLOORPLAN["die_mm2"])
    rows.append(dict(basis="815 mm2 reference", die_mm2=815.0, yield_=ref["yield_"], die_usd=ref["usd"],
                     hardware_usd_4die=round(4 * ref["usd"] + 2 * (FAB["package_usd"]["cowos_l_2die"]
                                                                   + FAB["test_assembly_usd"]) + 16 * FAB["hbm_stack_usd"])))
    return dict(rows=rows, spine_mm=spine_mm, margin=margin, phy_long_edge_mm=W,
                note="the die keeps its 4 PHYs on the long edges (2 x 8.5 mm + corners = 19 mm); the smaller die is "
                     "priced at the same G = 6,144 and tok/s")


# ---------------------------------------------------------------------------------------------------------
# W16 follow-ups (root, 2026-09-30): the product stage-owner file, the MTP tau sweep, short-context rows, the GPU
# calibration row, and the Qwen context sweep.
# ---------------------------------------------------------------------------------------------------------
# MTP acceptance (root / user direction 2026-09-30): the headline tau is third-party.  LMSYS, "DSpark in SGLang"
# (https://www.lmsys.org/blog/2026-07-06-dspark-sglang/, Figure 4, reproduction appendix): DeepSeek-V4-FLASH, H200,
# TP4 + DP-attention, draft block 6 (gamma = 5), cap-accept verify mode ("to expose the acceptance ceiling"):
# gsm8k 5.24, arena-hard 3.78, poetry 2.91.  V4-Flash, not V4.1-Flash; our measured 3.649 corroborates.
TAU_SWEEP = (("poetry (creative, lower; LMSYS V4-Flash)", 2.91),
             ("measured on V4.1-Flash, reasoning mix (OpenTallas; corroboration)", V41_TAU),
             ("HEADLINE: arena-hard (general chat; LMSYS V4-Flash, cap-accept ceiling)", 3.78),
             ("4.5 (interpolated)", 4.5),
             ("gsm8k (math, upper; LMSYS V4-Flash)", 5.24))
TAU_SRC = ("LMSYS, 'DSpark in SGLang' (2026-07-06), https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ Figure 4: "
           "DeepSeek-V4-Flash, H200 TP4 DP-attention, block 6, cap-accept verify (acceptance ceiling)")


def cons_tau_sweep(rows, positions=V41_POSITIONS):
    """MTP per-user rate at each tau from the rows' measured-tau MTP rate: a verify step's time does not depend on how
    many positions are accepted, so tok/s scales with tau / V41_TAU (tau <= gamma + 1 = positions)."""
    out = []
    for name, x in rows:
        base = x.get("mtp")
        if base is None:
            continue
        r = dict(design=name)
        for lab, tau in TAU_SWEEP:
            assert tau <= positions, "tau above gamma + 1 is impossible"
            r[f"tau_{tau:g}"] = round(base * tau / V41_TAU, 1)
        out.append(r)
    return dict(rows=out, taus={lab: t for lab, t in TAU_SWEEP}, headline_tau=3.78, source=TAU_SRC,
                gamma=positions - 1, note="tau <= gamma + 1 = 6 always holds here; GPU rows scale their tier-2 MTP "
                                          "the same way (their draft is modelled per step)")


@contextlib.contextmanager
def _cons_ctx(ctx):
    """Price the V4.1 graphs at context `ctx` instead of 1M (the consolidation section's own graphs only)."""
    global _CONS_CTX
    old = _CONS_CTX
    _CONS_CTX = ctx
    _HBM_CHAIN_CACHE.clear()
    _HBM_N_CACHE.clear()
    try:
        yield ctx
    finally:
        _CONS_CTX = old
        _HBM_CHAIN_CACHE.clear()
        _HBM_N_CACHE.clear()


# public GPU single-user records (root 2026-09-30).  TensorRT-LLM tech blog 1, "Pushing Latency Boundaries: Optimizing
# DeepSeek-R1 Performance on NVIDIA B200 GPUs": 8x B200, ISL 1K / OSL 2K, FP4, MTP extended to 3 layers (relaxed
# acceptance), 368 tok/s a user.  TensorRT-LLM blog 15 (DeepSeek-V3.2 on Blackwell): B200 min-latency ~312 tok/s a
# user with MTP-3.  NVIDIA's 1,038 tok/s a user on one DGX B200 is Llama 4 Maverick (not DeepSeek).  B300: the public
# interactivity points (SemiAnalysis InferenceX) are 73-150 tok/s a user at throughput-optimal settings; no
# min-latency B300 DeepSeek record was found.
GPU_PUBLIC = [
    dict(design="DeepSeek-R1 (671B), 8x B200, TensorRT-LLM min-latency", tok_s_user=368.0, ctx=3072, mtp_layers=3,
         src="TensorRT-LLM tech blog 1 (ISL 1K / OSL 2K, FP4)"),
    dict(design="DeepSeek-V3.2, B200, TensorRT-LLM min-latency", tok_s_user=312.0, ctx=None, mtp_layers=3,
         src="TensorRT-LLM tech blog 15"),
    dict(design="Llama 4 Maverick (400B MoE, 17B active), 1x DGX B200", tok_s_user=1038.0, ctx=None, mtp_layers=None,
         src="NVIDIA / Tom's Hardware, 2025-05: the ~1,000 tok/s/user public record is NOT a DeepSeek model"),
]
B300_OVER_B200 = dict(hbm_bw=8.0 / 8.0, note="B300 keeps 8 TB/s of HBM3E a GPU (288 GB); per-user decode at low batch "
                                             "is bandwidth- and latency-bound, so the tier-2 B300 row equals B200 "
                                             "within the model (ASSUMED; no public min-latency B300 DeepSeek record)")


def gpu_tier2_v41_ctx(ctx, positions=1, *, candidate_gather=True):
    """Tier-2 8x B200 V4.1-Flash step at context ctx (gpu_economics' form: fixed per layer + weight + index/KV bytes
    at the fitted B200 byte rate + NCCL-class all-reduces), batch 1."""
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    c = A._env()["c"]
    idx_user = v41_gpu_index_scan(ctx, candidate_gather=candidate_gather, c=c)["bytes"]
    t = (40 * fixed / 36 + s_per_B * (_v41_weight_bytes(positions) + idx_user) / 8 + 40 * 5 * NCCL_ALLREDUCE_S)
    return t


def cons_short_context(Sp, hp, t_a, head, ec, gr, ctx=8192):
    """Short-context rows (root 2026-09-30): the public GPU records are short-context, and the 1M headline is dominated
    by the index scan and attention.  The ROM product, the HBM tier 3 at equal cost (audited) and GPU tier 2, at ctx."""
    with _cons_ctx(ctx):
        p = cons_v41_rom(Sp, hp, t_a, 1.0, None, "columns", PRODUCT_CLOCK_HZ, FIELD_CONCURRENCY,
                         dict(SOFTPLUS_FIX, **W11_STREAM_SS), PRODUCT_DYN_SCALE, (0.9e9, "w18"), None, 7, True,
                         PRODUCT_SERIAL, DIE_SHRUNK_INTERIM)
        h = v41_hbm_n(96, 4, ec, gr, replicas=2, clock_hz=PRODUCT_CLOCK_HZ)
    h1 = v41_hbm_n(96, 4, ec, gr, replicas=2, clock_hz=PRODUCT_CLOCK_HZ)      # 1M: the W19 composition's context
    w_ar = HBM_W19["ar_tokens_s"] / h1["ar"]["batch1"]["per_user_tokens_s"]
    w_mtp = HBM_W19["mtp_tokens_s"] / h1["mtp"]["batch1"]["per_user_tokens_s"]
    t_ar = gpu_tier2_v41_ctx(ctx)
    gv = ec["gpu"]["v41"]
    mtp_ratio = gv["mtp_b1"] / gv["tokens_s_b1"]
    return dict(ctx=ctx, rows=[
        dict(design="V4.1 ROM product (columns, 1.2 GHz SS)", ar=p["ar_tokens_s_b1"], mtp=p["mtp_tokens_s_b1"],
             saturated=p["ar_saturated_tokens_s"], dies=p["dies"], silicon_mm2=p["dies"] * FLOORPLAN["die_mm2"],
             capex_usd=head["cost"]["capex_usd"]["low"], users=p["capacity_users_1m"]),
        dict(design="V4.1 HBM tier 3, equal cost (2 x TP-96), W19 composed/model ratio at 1M applied at ctx", ar=round(
            h["ar"]["batch1"]["per_user_tokens_s"] * w_ar, 1),
             mtp=round(h["mtp"]["batch1"]["per_user_tokens_s"] * w_mtp, 1), w19_ratio_ar=round(w_ar, 4),
             w19_ratio_mtp=round(w_mtp, 4),
             saturated=h["ar"]["saturated"]["aggregate_tokens_s"], dies=h["dies"], silicon_mm2=h["silicon_mm2"],
             capex_usd=h["cost"]["capex_usd"]["low"], users=h["capacity_users_1m"]),
        dict(design="V4.1-Flash, 8x B200 (tier 2, calibrated)", ar=round(1 / t_ar, 1), mtp=round(mtp_ratio / t_ar, 1),
             gpus=8, silicon_mm2=16 * 800.0, capex_usd=8 * COST["package_usd"], cost_basis="purchase price"),
        dict(design="V4.1-Flash, 8x B300 (tier 2; = B200 within the model, ASSUMED)", ar=round(1 / t_ar, 1),
             mtp=round(mtp_ratio / t_ar, 1), gpus=8, silicon_mm2=16 * 800.0, note=B300_OVER_B200["note"])])


def gpu_calibration_row(ec):
    """Our tier-2 model at DeepSeek-R1's published min-latency conditions (8x B200, ~3K context, MTP-3) against its
    368 tok/s: R1 is 671B / 37B active (FP4 in the record) against V4.1-Flash's 284B / 13B, so the row reports the
    model's V4.1 short-context step and states the model mismatch."""
    t = gpu_tier2_v41_ctx(3072)
    gv = ec["gpu"]["v41"]
    mtp = gv["mtp_b1"] / gv["tokens_s_b1"] / t
    return dict(conditions="8x B200, context ~3K (ISL 1K / OSL 2K), MTP", published=GPU_PUBLIC,
                model_v41_ar=round(1 / t, 1), model_v41_mtp=round(mtp, 1),
                error_vs_r1_record=round(mtp / 368.0 - 1, 3),
                note="the model prices V4.1-Flash (13B active) and R1 is 37B active: a like-for-like error needs an R1 "
                     "run of the tier-2 form; the ratio shown mixes model size with model error")


QWEN_CTX_SWEEP = (8192, 32768, 131072, 200000)
QWEN_CTX_NOTE = ("W12b context audit (claude/w12-qwen-rom b4d2715f): KV read 18,432 x T bytes a token a die; HBM "
                 "binds from ~32K (W12b ~1.4k tok/s at 128K, ~0.9k at 200K with SW 1,024, matching this sweep); 32K "
                 "needs parameters and 2 larger SRAMs (+~10 mm2 a die); 128K and 200K need a 27-bit address and a "
                 "larger VM (or head-serial scores).  "
                 "Qwen3-8B is natively 32K and 128K with YaRN; 200K is beyond official support.  FP8 KV (baseline); "
                 "the FP4/INT4-KV rows halve the KV bytes and are QUALITY-UNTESTED")


def qwen_context_sweep(ec):
    """Qwen3-8B per-user AR, KV bytes a token and KV read time, users that fit, saturated tok/s and J/token at 8K-200K
    for the ROM product (option C: TP-4, 4 x 4 stacks), its 6-stack-a-die and FP4-KV sensitivities, the HBM tier 3
    (2 x 4-stack right-sized dies) and GPU tier 2 (1x B200).  Rule: a token is the longer of the replayed compute
    chain at ctx (the attention work grows with ctx) and the KV stream of the busiest die (overlapped, ASSUMED)."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    wl, kvb8 = _qwen_wl()
    qr, qh = ec["qwen_rom"], ec["qwen_hbm"]
    cats = qr["energy"]["categories_mJ_per_token"]
    kv_e8 = (cats["kv_on_die"] + cats["stack"]) * 1e-3
    other_e = sum(v for k, v in cats.items() if k not in ("kv_on_die", "stack")) * 1e-3
    P_static = qr["energy"]["static_w_total"]
    dq = hbm_gpu_design("qwen")
    w_B = sum(b_ for b_, _ in qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])) - kvb8 / 2
    w_total = 2 * w_B
    t_h8 = 1 / qh["ar"]["tokens_s_b1"]
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    rows = []
    for ctx in QWEN_CTX_SWEEP:
        k0 = dict(T.K)
        Q.CLOCK[0] = Q.clock_hz()
        clock = Q.CLOCK[0]
        try:
            T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
            nh, kv = QWEN_TP_SHAPE[4]
            shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // 4), V=-(-Q.Q["V"] // 4))
            r = Q.as_built(ctx, groups=6144, su_width=1024, shape=shp, ucie=False)
        finally:
            T.K.clear()
            T.K.update(k0)
        x = _qwen_exchange("board", 4, clock)
        chain = (r["cycles"] + x["token_cycles"]) / clock
        for tag, stacks, kvf in (("ROM option C (4 stacks a die, FP8 KV)", 4, 1.0),
                                 ("ROM option C, 6 stacks a die", 6, 1.0),
                                 ("ROM option C, FP4/INT4 KV (quality untested)", 4, 0.5)):
            kvb = kvb8 * ctx / 8192 * kvf
            kv_die = kvb * kv / Q.Q["KV"]
            t_kv = kv_die / (stacks * HBM_STACK_BPS)
            t = max(chain, t_kv)
            users = int(stacks * HBM_STACK_B * HBM_CAP_EFF // kv_die)
            ub = r["unit_busy"]
            lanes = ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]
            sat = min(clock / lanes, clock / ub["stream"], stacks * HBM_STACK_BPS / kv_die)
            dyn = other_e + kv_e8 * kvb / kvb8
            rows.append(dict(ctx=ctx, design=tag, ar_tokens_s=round(1 / t, 1), kv_bytes_per_token=round(kvb),
                             kv_read_us=round(t_kv * 1e6, 1), chain_us=round(chain * 1e6, 1),
                             binding="KV stream" if t_kv > chain else "compute chain", users=users,
                             saturated_tokens_s=round(min(sat, users / t), 1),
                             mJ_b1=round((dyn + P_static * t) * 1e3, 1),
                             mJ_saturated=round((dyn + P_static / min(sat, users / t)) * 1e3, 1)))
        kvb = kvb8 * ctx / 8192
        t_h = t_h8 * (w_total + kvb) / (w_total + kvb8)
        users_h = int((8 * HBM_STACK_B * HBM_CAP_EFF - w_total) // kvb)
        rows.append(dict(ctx=ctx, design="Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR", ar_tokens_s=round(1 / t_h, 1),
                         kv_bytes_per_token=round(kvb), kv_read_us=round(t_h * kvb / (w_total + kvb) * 1e6, 1),
                         binding="HBM stream", users=users_h))
        t_g = fixed + s_per_B * (GPU_FIT["qwen_fp8_weight_bytes"] + kvb)
        users_g = int((B200_HBM_B * HBM_CAP_EFF - GPU_FIT["qwen_fp8_weight_bytes"]) // kvb)
        rows.append(dict(ctx=ctx, design="Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR", ar_tokens_s=round(1 / t_g, 1),
                         kv_bytes_per_token=round(kvb), kv_read_us=round(s_per_B * kvb * 1e6, 1), users=users_g,
                         mJ_b1=round(B200_W_DECODE * t_g * 1e3, 1)))
    return dict(rows=rows, note=QWEN_CTX_NOTE,
                rule="per-user token = max(replayed compute chain at ctx, busiest die's KV stream) for the ROM; the HBM "
                     "tier 3 and GPU scale their 8K step by the streamed bytes (weights + KV)")


# Qwen ROM product at 1.2 GHz SS (root 2026-09-30, W12b claude/w12-qwen-rom 8289866f): W12's TP-4 wire stages at the SS
# reach (112 cycles an ME op incl. MEM_EXTRA) + LAT-7 ME adders (+54 an op), and the droop product choice cap75 +
# preramp256 (x0.956 tok/s, +22.2 mJ a token of ramp energy; results/floorplan/qwen_rom_w12/droop_1p2ghz.json)
QWEN_SS = dict(me_lat_extra=QWEN_W12_TP4_ME_EXTRA_SS + 54, droop_rate=0.956, droop_mJ=22.2,
               src="W12b 775f5279 / 8289866f: LAT-7 ME +54 cycles an op; droop cap75 + preramp256")


# W12b (claude/w12-qwen-rom 42ecf382, root relay 2026-09-30): 1.2 GHz ME deltas -- LAT-7 adders +54 an ME op (ALREADY in
# QWEN_SS since 775f5279, not added again), KV_PREP +3 a KV op (+216 a token), FAST_ISSUE 0
QWEN_KV_PREP_CYCLES_TOKEN = 216
# W12b MEASURED (42ecf382 results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64.json, status pass): TP-4 layer 0
# bit-exact on 4 dies, G 6,144, SU width 64, SS wire stages (BD 41, NWS 5, TWS 38, ORD 7, MEM_EXTRA 1 = ME extra 112),
# N=4 oneshot collective at LAT 339 / DEPTH 1024, ME adders and issue loop the originals: 4,669 cycles
QWEN_L0_RTL = dict(cycles=4669, total_cycles=4676, collective_lat_cycles=339, su_width=64, groups=6144, tp=4,
                   me_extra=QWEN_W12_TP4_ME_EXTRA_SS, position=0,
                   src="claude/w12-qwen-rom 42ecf382 results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64.json "
                       "(stages.L0.cycles)")


# W12b ATTRIBUTION (claude/w12-qwen-rom a17a3c79, itrace results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64_itrace.txt):
# each all-reduce is 2 serialized 128-word TP segments (8-bit count field), ~497 cycles each -> 991 an all-reduce, 1,982
# a layer against the model's 884 (1,098 of the 1,325-cycle gap); the body excluding collectives is 2,687 cycles against
# the model's 2,460 (+9.2%, ME latency per op).  Stage spans: QKV 431, attn 87, PV+O ME 769, O AR 991, post 69, gate/up
# 528, SiLU 119, down 480, down AR 991, tail 222.  W12b's one-segment fix (79783ff9: a 256-word all-reduce is ONE TP
# segment, count 0 encodes 256) is NOT measured (estimate ~620 an all-reduce at LAT 339; TP-4 L0 re-run pending)
QWEN_L0_ATTR = dict(body_cycles=2687, allreduce_cycles=991, allreduces_per_layer=2, segments_per_allreduce=2,
                    segment_cycles=497,
                    spans=dict(qkv=431, attn=87, pv_o_me=769, o_ar=991, post=69, gate_up=528, silu=119, down=480,
                               down_ar=991, tail=222),
                    src="claude/w12-qwen-rom a17a3c79 results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64_itrace.txt",
                    fix_pending="claude/w12-qwen-rom 79783ff9 one-segment all-reduce, NOT measured (est. ~620 cycles)")


def qwen_l0_rtl_vs_model():
    """The model's layer at W12b's RTL configuration (position 0, SU width 64, ME extra 112, TP-4, G 6,144, SS) against
    the measured layer 0: the layer chain plus its two all-reduces, with W12b's per-stage attribution (body and
    all-reduces separately), which replaces the single RTL-calibrated ratio (root 2026-10-01)."""
    m = QWEN_L0_RTL
    p = qwen_tp_point(4, m["groups"], "board", clock_hz=PRODUCT_CLOCK_HZ, me_lat_extra=m["me_extra"], ctx=1,
                      su_width=m["su_width"])
    ar = p["exchange"]["per_allreduce_cycles"]
    model = p["layer_chain_cycles"] + 2 * ar
    model_rtl_coll = p["layer_chain_cycles"] + 2 * m["collective_lat_cycles"]
    return dict(rtl=m, model_layer_chain_cycles=p["layer_chain_cycles"], model_allreduce_cycles=ar,
                model_layer_cycles=round(model, 1), ratio=round(m["cycles"] / model, 4),
                model_short_pct=round(100 * (1 - model / m["cycles"]), 1),
                model_layer_cycles_at_rtl_collective=round(model_rtl_coll, 1),
                gap_cycles_at_rtl_collective=round(m["cycles"] - model_rtl_coll, 1),
                attribution=dict(QWEN_L0_ATTR, model_body_cycles=p["layer_chain_cycles"],
                                 body_ratio=round(QWEN_L0_ATTR["body_cycles"] / p["layer_chain_cycles"], 4),
                                 allreduce_gap_cycles=round(2 * (QWEN_L0_ATTR["allreduce_cycles"] - ar), 1),
                                 body_gap_cycles=round(QWEN_L0_ATTR["body_cycles"] - p["layer_chain_cycles"], 1)),
                status="ATTRIBUTED (W12b a17a3c79): body +9.2% (ME latency per op), all-reduce 2 serialized TP segments")


def qwen_product_ss():
    p = qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ, me_lat_extra=QWEN_SS["me_lat_extra"])
    cyc = p["cycles"] + QWEN_KV_PREP_CYCLES_TOKEN
    out = dict(p, cycles=cyc, tokens_s_b1=round(p["clock_hz"] / cyc * QWEN_SS["droop_rate"], 1), droop=QWEN_SS,
               kv_prep_cycles=QWEN_KV_PREP_CYCLES_TOKEN)
    # RTL-ATTRIBUTED rows (root 2026-10-01, replacing the single RTL-calibrated ratio): the layer chain (body) x W12b's
    # measured body / the model's body at the L0 configuration, and the two all-reduces a layer either as built
    # (2 serialized TP segments, 991 cycles each) or at the model's latency (W12b's one-segment fix, unmeasured);
    # the head, embedding and KV_PREP stay at the model
    cal = qwen_l0_rtl_vs_model()
    att = cal["attribution"]
    chain, ar = p["layer_chain_cycles"], p["exchange"]["per_allreduce_cycles"]
    body_add = 36 * chain * (att["body_ratio"] - 1)
    ar_add = 36 * 2 * (QWEN_L0_ATTR["allreduce_cycles"] - ar)
    for key, c, lab in (
            ("rtl_attributed_as_built", cyc + body_add + ar_add,
             f"RTL-attributed, as built: per-layer body x {att['body_ratio']} (W12b {QWEN_L0_ATTR['body_cycles']:,} / "
             f"model {att['model_body_cycles']:,.0f}) + 2 all-reduces at the measured {QWEN_L0_ATTR['allreduce_cycles']} "
             "cycles (2 serialized 128-word TP segments; W12b a17a3c79)"),
            ("rtl_attributed_body_only", cyc + body_add,
             f"RTL-attributed, body only: per-layer body x {att['body_ratio']}; all-reduces at the model's "
             f"{ar:,.0f} cycles, PENDING W12b's one-segment fix (79783ff9, unmeasured; est. ~620 at LAT 339)")):
        out[key] = dict(cycles=round(c), body_ratio=att["body_ratio"],
                        tokens_s_b1=round(p["clock_hz"] / c * QWEN_SS["droop_rate"], 1), label=lab)
    # USER DECISION (AGENTS.md a4f314fb): dataflow levels as named steps, "modelled; RTL pending" (W12b corrected,
    # claude/w12-qwen-rom 800717d0 results/uarch/qwen_su_overlap_spec.md): L1 lane registers alone save ~0 cycles (the
    # vstream drains on every SFU class change; port and energy saving only); L1 with overlap (per-element class tag,
    # per-vector KR credit, SU -> SU chase) ~5,600 cycles a token (estimate over 254 dependent pairs); the one-segment
    # all-reduce (QWEN_O4_AR_WORDS=256) ~740 cycles a layer on the as-built 2-segment all-reduce (L0 re-measure running;
    # the model row already prices the model's single all-reduce, so it applies to the as-built row only)
    steps = {}
    for key, base, ar_fix in (("model", cyc, 0), ("as_built", out["rtl_attributed_as_built"]["cycles"], 36 * 740)):
        rows = []
        for nm, dc in (("L1 lane registers (KR), no overlap", 0), ("L1 + overlap (KR credit, SU chase), estimate", 5600),
                       ("+ one-segment all-reduce (as built), estimate", ar_fix)):
            base -= dc
            r = round(p["clock_hz"] / base * QWEN_SS["droop_rate"], 1)
            rows.append(dict(step=nm, cycles=round(base), tokens_s_b1=r, label=FUSION_LABEL))
        steps[key] = rows
    out["dataflow_steps"] = dict(steps, src="W12b corrected 2026-10-01 (800717d0); 13,455 / 11,346 bounds WITHDRAWN")
    return out


# The model's own caveats: lessons where its pricing hid a cost that a measurement or a finer model exposed
MODEL_CAVEATS = [
    dict(id="vm_per_op_latency",
         lesson="Per-op network latency on the latency-bound SU chain was invisible in the throughput-style VM pricing. "
                "The VM was priced by port widths (vm_read_elems / vm_write_elems) and a few client wire stages, i.e. "
                "as bandwidth; the SU softmax / norm / Sinkhorn chains are dependent ops, so each op pays the VM "
                "network's full latency (control broadcast, operand read, element write or result tree).  W11's VM-H "
                "measured that at +36.7 slow cycles a vector op and +44.9 a reduction: -14.5% AR on the full-shape "
                "token, 82% of the 3,153 -> 2,680 drop (results/uarch/v41_vm_waterfall.json); more lanes or ports buy "
                "nothing (issue is not the bind).  Rule: any shared network on a dependent chain is priced as "
                "per-op latency on the chain, not as bandwidth.",
         src="root 2026-10-01; W11 claude/w11-vmh-land 3cc18731; W16b waterfall"),
    dict(id="rotate_span_is_the_hub_diameter",
         lesson="A rotate network's latency is set by the hub's diameter, not by the lane-to-strip distance.  The rotate "
                "maps element slot p to lane (p - base) mod 1,024 and every (slot, lane) pair is realised by some base, "
                "so a fixed-latency strip pays the worst bank -> lane run on every op.  W18b's compact placement brought "
                "every lane within 1,787 um of the strip, yet C_rotate's per-op extra rose from the unplaced 37 to 42 "
                "(10,735 um bank -> lane at 748 um a stage).  Rule: price a network from the placed worst path of the "
                "access pattern it must serve, never from an unplaced geometry.",
         src="W11 claude/w11-crot v41_vm_crot_stages.json; W18b 32155a8f; root 2026-10-01"),
]


def _vm_waterfall_job(job):
    tag, vmh, pitch, block, lanes, hub = job
    if lanes:
        PRESETS["proposal"] = dict(PRESETS["proposal"], su_lanes=lanes[0], sfu_lanes=lanes[1])
    g = CONS_GEOM["w10_refit"]
    f0 = g["field_mm2"]
    loss = 0.0 if block is None else (block - 14.249) * 1.05
    g["field_mm2"] = f0 - loss
    try:
        S = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", pitch, "columns", "4096m8")
        H = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", pitch, "8192m8")
    finally:
        g["field_mm2"] = f0
    hubd = dict(hub, block_mm2=block) if hub else None
    p = cons_v41_rom(S, H, cons_table_dies("analytical")["dies"], 1.0, None, "columns", PRODUCT_CLOCK_HZ,
                     FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), PRODUCT_DYN_SCALE, (0.9e9, "w18"), None,
                     7, True, PRODUCT_SERIAL, DIE_SHRUNK_INTERIM, vmh, hubd)
    return tag, dict(stages=S, dies=p["dies"], hub_block_mm2=block, ar_tokens_s_b1=round(p["ar_tokens_s_b1"], 1),
                     mtp_tokens_s_b1=round(p["mtp_tokens_s_b1"], 1),
                     ar_saturated_tokens_s=round(p["ar_saturated_tokens_s"], 1), vm=vmh)


def cons_vm_waterfall(procs=None):
    """Root 2026-10-01: the waterfall from the pre-VM-H product (3,153 AR) to the measured VM-H product, component by
    component, and the VM levers at the product basis (W10b tiles, the block's hub area, 0.9 GHz SU domain)."""
    from multiprocessing import get_context
    novm = dict(x_gather=6 * 0.9 / 1.2, ret_scatter=6 * 0.9 / 1.2, coll_write=6 * 0.9 / 1.2, su_op_extra=0.0,
                su_red_extra=0.0, su_issue=1.0, src="VM_DIST 6/6/6 fast cycles (no VM-H)")
    H = dict(VMH)
    C = dict(VMC)
    CX = dict(x_gather=18, ret_scatter=18, coll_write=18, su_op_extra=57, su_red_extra=49, su_issue=1.0,
              src="W11 3cc18731 options.C (central full crossbar, 74.66 mm2)")
    steps, cum = [("previous product (VM_DIST 6/6/6, ledger hub, W10 q 476 um)", None, "w10_q_1p2", None, None, None)], dict(novm)
    names = dict(x_gather="VM-H x gather 6 -> 12 stages", ret_scatter="VM-H result scatter 6 -> 12",
                 coll_write="VM-H collective write 6 -> 12", su_op_extra="VM-H SU op network latency +36.7 slow cycles",
                 su_red_extra="VM-H reduction network latency +44.9", su_issue="VM-H issue x1.169")
    for k in ("x_gather", "ret_scatter", "coll_write", "su_op_extra", "su_red_extra", "su_issue"):
        cum = dict(cum, **{k: H[k]})
        steps.append((names[k], dict(cum), "w10_q_1p2", None, None, None))
    steps.append(("W10b tiles (q 510.84 um): 37 -> 39 stages", H, PRODUCT_PITCH, None, None, None))
    steps.append(("VM-H hub block 38.95 mm2: 39 -> 41 stages (measured VM-H reference)", H, PRODUCT_PITCH,
                  VMH_BLOCK["block_mm2"], None, VMH_BLOCK))
    shrink = lambda f: dict(H, su_op_extra=5 + (H["su_op_extra"] - 5) * f, su_red_extra=5 + (H["su_red_extra"] - 5) * f)
    levers = [
        ("(a) C_rotate, W11 square layout (37 / 29): SUPERSEDED, unplaced geometry", C, PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) C_rotate on W18b's strip hub (42 / 32), unfused: reference", VMC_COMPACT, PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) C_rotate on W18b's strip hub, fused conservative: reference", VMC_COMPACT_FUSED, PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) C_rotate on W18b's plus hub (37 / 28), unfused: PRODUCT basis", VMC_PLUS, PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) C_rotate on W18b's plus hub, fused conservative: PRODUCT (modelled; RTL pending)", VMC_FUSED,
         PRODUCT_PITCH, VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) C_rotate on W18b's plus hub, fused optimistic: BOUND", VMC_FUSED_OPT, PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(a) VM-H, fused conservative (comparison)", dict(H, fusion=dict(FUSION_VMH, mode="conservative")),
         PRODUCT_PITCH, VMH_BLOCK["block_mm2"], None, VMH_BLOCK),
        ("(a) C_rotate on the compact hub at 481 um a stage (61 / 46; sensitivity: the 1.2 GHz reach)",
         dict(x_gather=11, ret_scatter=10, coll_write=20, su_op_extra=61, su_red_extra=46, su_issue=1.0), PRODUCT_PITCH,
         VMC_BLOCK["block_mm2"], None, VMC_BLOCK),
        ("(b) SU 2,048 / SFU 512 lanes, network unchanged (optimistic; block ~63 mm2)", H, PRODUCT_PITCH,
         VMH_BLOCK["block_mm2"] + 24.0, (2048, 512), VMH_BLOCK),
        ("(b) SU 2,048 / SFU 512 lanes, network stages x1.41", dict(shrink(1.41), x_gather=17, ret_scatter=17,
                                                                    coll_write=17), PRODUCT_PITCH,
         VMH_BLOCK["block_mm2"] + 24.0, (2048, 512), VMH_BLOCK),
        ("(c) flat VM as buildable = W11 option C (central crossbar, 74.66 mm2)", CX, PRODUCT_PITCH, 74.664, None,
         VMH_BLOCK),
        ("(c) flat VM with no network (NOT physical; reference)", None, PRODUCT_PITCH, VMH_BLOCK["block_mm2"], None,
         VMH_BLOCK),
        ("(d) VM-H per-op network latency -25%", shrink(0.75), PRODUCT_PITCH, VMH_BLOCK["block_mm2"], None, VMH_BLOCK),
        ("(d) VM-H per-op network latency -50%", shrink(0.5), PRODUCT_PITCH, VMH_BLOCK["block_mm2"], None, VMH_BLOCK),
        ("(d) VM-H client stages 12 -> 8 only", dict(H, x_gather=8, ret_scatter=8, coll_write=8), PRODUCT_PITCH,
         VMH_BLOCK["block_mm2"], None, VMH_BLOCK),
        ("(d) VM-H issue x1.169 -> 1.0 only", dict(H, su_issue=1.0), PRODUCT_PITCH, VMH_BLOCK["block_mm2"], None,
         VMH_BLOCK),
        ("(d) W11's 3,850 um sensitivity (one-way 8, op / red +21): SUPERSEDED -- the rotate pays the hub diameter",
         dict(C, su_op_extra=21, su_red_extra=21), PRODUCT_PITCH, VMC_BLOCK["block_mm2"], None, VMC_BLOCK)]
    jobs = steps + levers
    with get_context("fork").Pool(procs or len(jobs)) as pool:
        res = dict(pool.map(_vm_waterfall_job, jobs))
    wf, prev = [], None
    for j in steps:
        r = dict(res[j[0]], step=j[0])
        r["delta_ar"] = None if prev is None else round(r["ar_tokens_s_b1"] - prev, 1)
        prev = r["ar_tokens_s_b1"]
        wf.append(r)
    ref = wf[-1]["ar_tokens_s_b1"]
    lv = [dict(res[j[0]], lever=j[0], vs_vmh_reference_pct=round(100 * (res[j[0]]["ar_tokens_s_b1"] / ref - 1), 1))
          for j in levers]
    return dict(schema="opentallas.uarch.v41_vm_waterfall.v1", waterfall=wf, levers=lv,
                total_drop_ar=round(wf[-1]["ar_tokens_s_b1"] - wf[0]["ar_tokens_s_b1"], 1),
                ruling="ROOT 2026-10-01: C_rotate stays (no issue penalty; it wins the saturated rate), priced on W18b's "
                       "placed compact hub at 748 um a stage (+42 / +32) with lane-local fusion as a named step "
                       "(modelled; RTL pending); the square layout's 37 / 29 is superseded; VM-H is the comparison row; "
                       "W11's aligned-base near / far allocator becomes an upside row when it lands",
                caveat=MODEL_CAVEATS[0]["lesson"],
                source_sha256={"tools/uarch_model.py": hashlib.sha256((ROOT / "tools/uarch_model.py").read_bytes()).hexdigest()})


def qwen_helix_scaleout(ec, ctx=200000, extra=(0, 4, 8, 16)):
    """Long-context KV scale-out (root 2026-09-30): extra HBM + attention dies hold context slices (KV split by
    position, Helix-style) with an exact ordered merge of the partial softmax; weights stay on the 4 ROM dies.  Per
    user at ctx: max(compute chain, KV stream over all dies' stacks) + one ordered merge a layer (a board all-gather of
    the partial (max, sum, output) vectors, W15's measured TP-4 board fit, ASSUMED to span the added dies)."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    wl, kvb8 = _qwen_wl()
    Q.CLOCK[0] = Q.clock_hz()
    clock = Q.CLOCK[0]
    k0 = dict(T.K)
    try:
        T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
        nh, kv = QWEN_TP_SHAPE[4]
        shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // 4), V=-(-Q.Q["V"] // 4))
        r = Q.as_built(ctx, groups=6144, su_width=1024, shape=shp, ucie=False)
    finally:
        T.K.clear()
        T.K.update(k0)
    chain = (r["cycles"] + _qwen_exchange("board", 4, clock)["token_cycles"]) / clock
    kvb = kvb8 * ctx / 8192
    merge = w15_collective_s("v41p17_r0d1024", "all_gather", Q.Q["H"] * 4 + 64, 4)
    rows = []
    for n in extra:
        stacks = 4 * (4 + n)
        t_kv = kvb / (stacks * HBM_STACK_BPS)
        t = max(chain, t_kv) + (Q.Q["L"] * merge if n else 0.0)
        rows.append(dict(extra_kv_dies=n, total_dies=4 + n, ar_tokens_s=round(1 / t, 1), kv_read_us=round(t_kv * 1e6, 1),
                         merge_us=round(Q.Q["L"] * merge * 1e6, 1) if n else 0.0,
                         users=int(stacks * HBM_STACK_B * HBM_CAP_EFF // kvb)))
    return dict(ctx=ctx, rows=rows, chain_us=round(chain * 1e6, 1),
                rule="KV split by position over the 4 ROM dies + n KV dies (4 stacks each); one ordered partial-softmax "
                     "merge a layer on the board fit (ASSUMED); weights stay on the ROM dies")


CONS_SOURCES = ECON_SOURCES + ("results/arch/v41_die_assembly.json", "results/arch/v41_die_placement.json",
                               "results/floorplan/v41_die_macromap_expanded_woa.json",
                               "results/floorplan/v41_rom_capacity.json", "results/floorplan/qwen_o4_rom_placement.json",
                               "results/floorplan/hbm_gpu/qwen_hbm_die.json", "results/floorplan/hbm_gpu/v41_hbm_die.json",
                               "tools/decode_critical_path.py")


def sweep(ctx: int):
    """Design-point search over the microarchitecture knobs that the evaluation shows binding."""
    rows = []
    base = PRESETS["proposal"]
    for vm in (16, 32, 64, 128, 256):
        for nb in (1024, 2048, 3072, 4096):
            d = dict(base, name=f"sweep_vm{vm}_bf{nb or 'all'}", vm_read_elems=vm, vm_write_elems=2 * vm,
                     bf16_stripe_macros=nb)
            r = evaluate(d, ctx)
            clock = r["clock_hz"]
            rows.append(dict(vm_read_elems=vm, vm_write_elems=2 * vm, bf16_stripe_macros=nb or d["macros"],
                             tokens_s=round(r["tokens_s"], 1), T_us=round(r["T_us"], 2),
                             weight_sweep_us=r["breakdown_us"].get("weight_sweep"),
                             area=area_ledger(d), network=network_ledger(d, clock)))
            print(f"vm{vm:4d} bf16 {nb or 'all':>5}: {r['tokens_s']:8.1f} tok/s  strip "
                  f"{rows[-1]['area']['rom_field_strip_used_mm2']:6.1f}  hub {rows[-1]['area']['hub_logic_mm2']:6.1f}"
                  f"  spines {rows[-1]['network']['spine_corridors_needed']}  col util "
                  f"{rows[-1]['network']['column_utilisation']}")
    return rows


POWER_CLOCKS = (1.25e9, 1.5e9)


def power_clock_sensitivity(name="proposal", ctx=1048576, clocks=POWER_CLOCKS):
    """The design re-priced at a faster clock (the architecture DAG rebuilt at that clock, then the uarch pricing;
    wire flight, HBM streams and the W15 collectives keep their times) with the measured pair power scaled linearly
    with the clock at the same 0.7 V (ASSUMED: a faster clock may need a higher supply, which this under-states)."""
    E = A._env()
    base = E["clock"]
    saved = dict(_ARCH_CACHE)
    rows = []
    try:
        for f in clocks:
            E["clock"] = f
            _ARCH_CACHE.clear()                  # the architecture DAG prices cycle terms at E["clock"]
            d = copy.deepcopy(PRESETS[name])
            r = evaluate(d, ctx)
            g = r.pop("_g")
            pw = power_ledger(d, g, f, r["tokens_s"], area_ledger(d))
            rows.append(dict(clock_hz=f, tokens_s=round(r["tokens_s"], 1), power=pw))
    finally:
        E["clock"] = base
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)
    return dict(design=name, basis="architecture DAG and uarch pricing rebuilt at each clock; pair power x f / "
                                   "1.087 GHz at 0.7 V (ASSUMED)", rows=rows)


def w10_frontend_model():
    """Bounded FRONT_PAR opt-in: parallel class addresses, then one-bit class selection.

    Pre-RTL sizing only. No new memory, rounding point, pipeline stage or protocol.
    Area uses a deliberately conservative 12 DFF-equivalents per full-adder bit
    and 4 per equality bit; physical qualification must replace these estimates.
    """
    n, width = 8, 8
    extra_add_bits = (n - 1) * width
    extra_compare_bits = (n - 1) * width
    # Preserve truncation to 8 bits BEFORE comparison (pair addresses wrap).
    extra_area = (12 * extra_add_bits + 4 * extra_compare_bits + 4 * n) * DFF_UM2
    tile = 510.84 * 126.9
    macros = 4 * 7881.4  # ROM depth study: two 4096-row banks per macro, NB=2
    strip = tile - macros
    # Local replicated buses only; external hub/field wires are identical.
    local_wires = n * (width + width + 1) + 3
    local_tracks = FLOORPLAN["over_rom_tracks_per_100um"] * 238.68 / 100 * 0.5
    s = cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM,
                        PRODUCT_PITCH, "columns", "4096m8")
    h = cons_head_dies("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, PRODUCT_PITCH, "8192m8")
    def price(clock):
        p = cons_v41_rom(s, h, cons_table_dies("analytical")["dies"], bf16="columns", clock_hz=clock,
                         field_concurrency=FIELD_CONCURRENCY, added_latency=dict(SOFTPLUS_FIX, **W11_STREAM_SS),
                         dyn_scale=PRODUCT_DYN_SCALE, slow_domain=(0.9e9, "w18"), elem_stages=7,
                         ss_wire=True, serial=PRODUCT_SERIAL, die=DIE_SHRUNK_INTERIM, vmh=VMC_FUSED,
                         hub_block=PRODUCT_HUB)
        return dict(ar_tokens_s=p["ar_tokens_s_b1"], token_us=1e6 / p["ar_tokens_s_b1"],
                    frontend_added_cycles=0, frontend_added_token_us=0)
    target = price(PRODUCT_CLOCK_HZ)
    # A sensitivity, NOT an operating point: adding reported slack to the period
    # ignores re-CTS and every other critical path. Never adopt this as closure.
    sensitivity = price(1e9 / (0.833 + 0.15986))
    gain = target["ar_tokens_s"] / sensitivity["ar_tokens_s"] - 1
    return dict(schema="opentallas.w10.frontend.model.v1", parameter="FRONT_PAR", default=0,
                verdict="PASS_SIZING_ONLY", adoption="PENDING_RTL_GAIN_AND_SS_FF_IN_CONTEXT",
                scope="separate W10 module namespace; existing main RTL and W16 model preserved",
                integration=dict(base_commit="1be527dbc20e655b26dc4a236c5802aba0b3f710",
                                 preserved_model_sha256="c85d9588ffd08641af364151bc7e0923324eea3520a63d41451e11716a62312f",
                                 product_vm="VMC_FUSED"),
                other_designs={k: "unchanged; FRONT_PAR is ROM-specific" for k in ("qwen_rom", "qwen_hbm", "v41_hbm")},
                baseline_commit="66b0bee616464920080aa2c44189c4287a6ec1b4",
                arithmetic="8-bit modular pair-address sum; all FP arithmetic and golden reduction orders unchanged",
                compute=dict(macs_per_cycle_delta=0, control_matches_per_cycle=n, latency_cycles_delta=0,
                             initiation_interval_cycles=1, compute_intensity_delta=0, communication_intensity_delta=0),
                ports=dict(rom_bytes_per_cycle_per_macro=274 / 8, rom_bytes_per_cycle_delta=0,
                           activation_bytes_per_cycle_delta=0, shared_memory_bytes_per_cycle_delta=0),
                boundaries=dict(external_bits_per_cycle_delta=0, local_replicated_wires=local_wires,
                                local_tracks_available_estimate=local_tracks,
                                local_track_utilisation_estimate=local_wires / local_tracks,
                                hub_routing_layers="unchanged; local strip only; physical layer audit pending"),
                mux=dict(baseline="8:1 eight-bit base mux -> eight-bit add -> compare",
                         candidate="8 parallel eight-bit add/compare cones -> class-qualified one-bit OR",
                         replicas=n, extra_add_bits=extra_add_bits, extra_compare_bits=extra_compare_bits,
                         demux_delta=0, q_j_and_xs_p_bit_fanout=n,
                         class_select_fanout_per_bit=n // 2,
                         walker_update_fanout="unchanged nA/nB and walker control sinks; must measure in context"),
                area=dict(extra_register_bits=0, extra_logic_um2_upper_estimate=extra_area,
                          estimate_basis="12 DFF equivalents/add bit, 4/compare bit, 4/class selection; ASSUMED",
                          tile_um2=tile, macro_um2=macros, strip_um2=strip,
                          incremental_strip_fraction=extra_area / strip,
                          density_target=0.6, estimated_extra_placement_um2=extra_area / 0.6,
                          fit="incremental estimate only; existing strip is congested; route required"),
                composition=dict(stages=s, head_dies=h, target=target,
                                 failed_path_period_sensitivity=sensitivity,
                                 conditional_rate_gain_fraction=gain, minimum_adoption_gain_fraction=0.01,
                                 sensitivity_caveat="hypothetical streaming clock recovery only; not measured gain or closure"),
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                               ("tools/uarch_model.py", "results/uarch/v41_rom_depth_study.json",
                                "rtl/v41rom/ot_v41_rom_elem.sv", "rtl/v41rom/ot_v41_rom_elem_q.sv")})


def w10_baseline_model():
    """Audit the existing FAST/PP/BP element, without adopting or retuning a lever.

    The default CUT has seven asserted cuts plus the base stage: LAT=8.
    Keep the product LAT=7 row intact; expose the LAT=8 composition separately.
    The pre-existing elem_fill=78 still requires whole-field RTL calibration.
    """
    cut, nb = 0b101111011, 2
    lat = 1 + cut.bit_count()
    stages = cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM,
                             PRODUCT_PITCH, "columns", "4096m8")
    head = cons_head_dies("analytical", CONS["overhead"], "ring", PRODUCT_GEOM,
                         PRODUCT_PITCH, "8192m8")
    def price(es):
        r = cons_v41_rom(stages, head, cons_table_dies("analytical")["dies"], bf16="columns",
                         clock_hz=PRODUCT_CLOCK_HZ, field_concurrency=FIELD_CONCURRENCY,
                         added_latency=dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT),
                         dyn_scale=PRODUCT_DYN_SCALE, slow_domain=(0.9e9, "w18"), elem_stages=es,
                         ss_wire=True, serial=PRODUCT_SERIAL, die=DIE_SHRUNK_INTERIM,
                         vmh=VMC_FUSED, hub_block=PRODUCT_HUB)
        return dict(ar_tokens_s=r["ar_tokens_s_b1"], token_us=1e6/r["ar_tokens_s_b1"],
                    dies=r["dies"], element_adder_stages=es)
    q = CONS_PITCH[PRODUCT_PITCH]["q_um"]
    bf = CONS_PITCH[PRODUCT_PITCH]["bf16_outline_um"]
    tracks = FLOORPLAN["over_rom_tracks_per_100um"] * min(q[0], bf[0]) / 100 * 0.5
    modes = {"columns": dict(bp=0, hold=1, macs=16*nb),
             "pair_option_iii": dict(bp=1, hold=4, macs=4*nb),
             "pair_option_ii": dict(bp=2, hold=8, macs=2*nb)}
    for m in modes.values():
        m.update(bf16_weight_bytes_per_cycle=2*m["macs"],
                 activation_macs_per_byte=0.5, status="existing exact gate; contextual SS/FF pending")
    return dict(schema="opentallas.w10.baseline.model.v1", verdict="AUDIT_ONLY_NO_NEW_BUILD",
                scope="existing FAST/PP/BP baseline; FRONT_PAR rejected and fixed off",
                defaults=dict(FAST=0, PP=0, BP=0, FRONT_PAR=0),
                qualification=dict(FAST=1, PP=1, BP=0, NB=nb, CUT=cut, LAT=lat),
                protocol=dict(registered_input_cycles=1, issue_to_capture_cycles=3,
                              bterm_latency_cycles=11, adder_recurrence_cycles=lat,
                              golden_chunk_terms=8, minimum_chunk_round_cycles=8*lat,
                              fifo_issue_order="unchanged", arithmetic="golden chunk8 rounding/tree unchanged"),
                compute=dict(fp4_macs_per_cycle=64*nb, fp8_macs_per_cycle=32*nb,
                             fp4_weight_macs_per_byte=128/(274*nb/8),
                             fp8_weight_macs_per_byte=64/(274*nb/8), bf16_modes=modes),
                ports=dict(rom_effective_bytes_per_cycle=274*nb/8,
                           physical_rom_ports=2*nb, bytes_per_port_per_two_cycle_read=274/8,
                           quantized_x_payload_bytes_per_cycle=64, quantized_x_exponent_bits=20,
                           bf16_column_x_bytes_per_cycle=128, partial_data_bytes_per_cycle=4*nb,
                           partial_metadata_bits_per_cycle=(16+5+5+1+3)*nb),
                boundaries=dict(rom_capture_bits_per_cycle=274*nb, quantized_x_payload_bits=512,
                                bf16_x_payload_bits=1024, added_hub_bits=0,
                                estimated_local_channel_tracks=tracks, local_rom_plus_bf16_tracks=274*nb+1024,
                                fits_estimated_channel=(274*nb+1024)<=tracks,
                                basis="existing over-ROM track estimate, 50% availability; routed layer audit pending"),
                replication=dict(macros_per_pair=2*nb, pp_word_mux_2to1_bits=274*nb,
                                 pp_select_logical_fanout_per_macro=274,
                                 frontend_base_mux="8:1 x 8-bit; original selected-address cone",
                                 demux="two alternate macro enables per logical bank",
                                 frontend_parallel_replicas=0),
                area=dict(q_tile_um2=q[0]*q[1], column_tile_um2=bf[0]*bf[1],
                          rom_macro_um2=2*nb*7881.4, planned_new_hardware_um2=0,
                          fit="existing outlines; c8 is column qualification, not q tile signoff"),
                composition=dict(product_unchanged_lat7=price(7), checked_in_lat8_audit=price(lat),
                                 product_adoption=False, stage_count=stages,
                                 pending="whole-field fill/return calibration: inherited elem_fill=78 is not remeasured here"),
                other_designs={k:"unchanged" for k in ("qwen_rom", "qwen_hbm", "v41_hbm")},
                qualification_policy="reuse live c8; no new PnR, no FRONT_PAR retry, no headline restatement")


def w10_capacity_diagnosis(inputs):
    """Read-only c8 failure audit: bulk slot capacity does not prove pin access.

    Geometry is from the saved global-route DB, never a qualified final abstract.
    The channel reservation is an analytical contingency for parent review,
    not a new route recipe, an orientation change, or a retry of c8.
    """
    import re
    lef = (ROOT / inputs["macro_lef"]).read_text()
    width, height = map(float, re.search(r"SIZE ([0-9.]+) BY ([0-9.]+)", lef).groups())
    ports = []
    for name, body in re.findall(r"  PIN (.*?)\n(.*?)  END ", lef, re.S):
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        box = re.search(r"RECT ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+)", body)
        if box:
            ports.append((name, [round(float(v)*1000) for v in box.groups()]))
    track = inputs["tracks"]["M4"]
    access = []
    for macro in inputs["macros"]:
        x0, y0 = macro["location_nm"]
        aligned = intersecting = 0
        offsets = set()
        edge_counts = {"left": 0, "right": 0}
        failures = []
        for name, (xl, yl, xh, yh) in ports:
            if macro["orientation"] in ("MX", "R180"):
                yl, yh = round(height*1000)-yh, round(height*1000)-yl
            if macro["orientation"] in ("MY", "R180"):
                xl, xh = round(width*1000)-xh, round(width*1000)-xl
            yc = y0 + (yl+yh)/2
            residual = (yc-track["y_origin_nm"]) % track["y_pitch_nm"]
            offset = min(residual, track["y_pitch_nm"]-residual)
            offsets.add(offset)
            aligned += offset == 0
            first = math.ceil((y0+yl-track["y_origin_nm"])/track["y_pitch_nm"])
            last = math.floor((y0+yh-track["y_origin_nm"])/track["y_pitch_nm"])
            intersecting += last >= first
            edge_counts["left" if (xl+xh)/2 < width*500 else "right"] += 1
            if name in ("rd_out[171]", "rd_out[254]"):
                failures.append(dict(port=name, center_y_um=yc/1000, center_offset_nm=offset,
                                     intersecting_horizontal_tracks=max(0,last-first+1)))
        warn = inputs["center_warning_counts"].get(macro["name"], 0)
        access.append(dict(macro=macro["name"], orientation=macro["orientation"], signal_pins=len(ports),
                           center_aligned=aligned, center_off_grid=len(ports)-aligned,
                           intersecting_track_exists=intersecting, center_offsets_nm=sorted(offsets),
                           edge_pins=edge_counts, observed_center_warnings=warn,
                           warning_count_matches=(warn==len(ports)-aligned), selected_ports=failures))
    c = inputs["cts"]
    core = c["cts__design__core__area"]
    cells = c["cts__design__instance__area__stdcell"]
    macros = c["cts__design__instance__area__macros"]
    slot = _cons_pair_mm2(PRODUCT_PITCH, True)
    max_edge = max(max(m["edge_pins"].values()) for m in access)
    # All edge pins on parallel M5 tracks is a conservative channel reservation,
    # not a measured lower bound; local captures may need fewer long tracks.
    channel = max_edge * inputs["tracks"]["M5"]["x_pitch_nm"] / 1000 / 0.5
    reserve = 2 * len(access) * channel * height
    bx, by = CONS_PITCH[PRODUCT_PITCH]["bf16_outline_um"]
    widened = bx + reserve/by
    key = "w10_read_only_channel_reservation"
    if key in CONS_PITCH:
        raise ValueError("diagnostic key already exists")
    CONS_PITCH[key] = dict(CONS_PITCH[PRODUCT_PITCH], bf16_outline_um=(widened, by))
    try:
        stages = cons_min_stages("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, key, "columns", "4096m8")
        need = cons_field_need_mm2(stages, "analytical", key, "columns", "4096m8")
        head = cons_head_dies("analytical", CONS["overhead"], "ring", PRODUCT_GEOM, PRODUCT_PITCH, "8192m8")
        composed = cons_v41_rom(stages, head, cons_table_dies("analytical")["dies"], bf16="columns",
            clock_hz=PRODUCT_CLOCK_HZ, field_concurrency=FIELD_CONCURRENCY,
            added_latency=dict(SOFTPLUS_FIX, **W11_STREAM_SS, **PLUS_LAT), dyn_scale=PRODUCT_DYN_SCALE,
            slow_domain=(0.9e9, "w18"), elem_stages=8, ss_wire=True, serial=PRODUCT_SERIAL,
            die=DIE_SHRUNK_INTERIM, vmh=VMC_FUSED, hub_block=PRODUCT_HUB)
    finally:
        del CONS_PITCH[key]
    baseline = w10_baseline_model()["composition"]
    return dict(schema="opentallas.w10.floorplan_capacity_diagnosis.v1", verdict="FAILED_BASELINE_DIAGNOSIS_ONLY",
        terminal="c8 rc1 DRT-0255; recovery BLOCKED_INPUTS; FRONT_PAR rejected independently",
        pinned_originals_unchanged=True, pin_access=access, failed_net_fanout=inputs["failed_nets"],
        finding="All 576 center warnings match mirrored pin phases; failed nets have one sink each. Every pin rectangle still intersects a track: off-center warnings alone do not prove the maze failure cause.",
        capacity=dict(reserved_bf16_slot_mm2=slot, actual_die_mm2=c["cts__design__die__area"]/1e6,
                      core_um2=core, macro_um2=macros, stdcell_um2=cells,
                      stdcell_utilization_outside_macros=cells/(core-macros), unoccupied_core_um2=core-cells-macros,
                      bulk_tracks=w10_baseline_model()["boundaries"],
                      physical_PP_ROM_routes=sum(x["total_sinks"] for x in inputs["fanout"].values()),
                      all_payload_wire_sum=sum(x["total_sinks"] for x in inputs["fanout"].values())+1024+512,
                      payload_utilization_if_one_shared_corridor=(sum(x["total_sinks"] for x in inputs["fanout"].values())+1024+512)/w10_baseline_model()["boundaries"]["estimated_local_channel_tracks"],
                      omitted_from_that_sum="capture-to-mux links, metadata/control/clock, vias/PDN/OBS and detours",
                      correction="old 1572-wire bound is effective ROM data + BF16 input only; PP has both physical bank buses and quantized input wiring. Actual corridor crossings still require topology assignment, not a global wire sum.",
                      qualification="area and bulk tracks fit estimates; local escape/vias/PDN/DRC are not covered"),
        reservation_contingency=dict(max_signals_per_macro_edge=max_edge, assumed_track_availability=0.5,
            raw_M5_pitch_nm=inputs["tracks"]["M5"]["x_pitch_nm"], per_edge_channel_um=channel,
            eight_edge_gross_area_um2=reserve, added_latency_cycles=0,
            fit_inside_existing_slot="gross area can fit unoccupied area; local contiguity and cell displacement unproven",
            if_fully_additive_outline_um=[widened,by], extra_mm2_per_die=reserve*CONS_BF16["pairs"]/1e6,
            composed_analytical_stages=stages, composed_field_need_mm2=need,
            token_pricing=dict(baseline=baseline["checked_in_lat8_audit"],
                reservation=dict(ar_tokens_s=composed["ar_tokens_s_b1"], token_us=1e6/composed["ar_tokens_s_b1"],
                                 dies=composed["dies"], pipeline_hops_us=composed["pipeline_hops_us"]),
                extra_stage_count=stages-baseline["stage_count"],
                composed_token_us_delta=1e6/composed["ar_tokens_s_b1"]-baseline["checked_in_lat8_audit"]["token_us"],
                basis="existing graph repriced at its minimum stage count; zero local cycle delta, stage hops composed; no clock recovery credited; wire/layout recalibration pending"),
            not_adopted=True, basis="conservative reservation only, not measured requirement or a c8 tuning recipe"),
        next_admissible_step="Parent reviews macro-interface contract: prove legal access for all supported orientations including PDN/via enclosure; reserve escape and local capture space in the composed model before any new companion macro/floorplan build.",
        requirements_before_build=["an immutable new companion view if pin geometry changes; preserve original LEF",
            "actual pin access/PDN/via-capacity proof, not only bus-width divided by pitch",
            "explicit priced slot geometry and latency, including full-field LAT8 calibration",
            "parent architecture review before RTL; separate future exact and SS/FF contextual qualification"],
        no_new_pnr=True, no_retry_or_tuning=True, final_abstract_qualified=False)


def w10_pinaccess_contract_review(inputs):
    """Necessary interface constraints and wake-aware capacity, without a new flow.

    This does not assert full DRC legality: detailed signal occupation, cut/EOL
    rules and all simultaneous escapes require a separate parent-reviewed proof.
    """
    import re
    geo, wake = inputs["geometry"], inputs["wake"]
    lef = (ROOT/geo["macro_lef"]).read_text()
    if hashlib.sha256(lef.encode()).hexdigest() != geo["macro_lef_sha256"]:
        raise ValueError("pinned macro LEF mismatch")
    height = round(float(re.search(r"SIZE [0-9.]+ BY ([0-9.]+)", lef)[1])*1000)
    py = geo["tracks"]["M4"]["y_pitch_nm"]
    origin = geo["tracks"]["M4"]["y_origin_nm"]
    pin_phase = 12  # all 288 signal/clock centers verified in previous geometric audit
    mirrored_phase = (height-pin_phase) % py
    required_origin = (origin-mirrored_phase) % py
    site = geo["site"]
    feasible = (required_origin-site["origin_nm"][1]) % math.gcd(site["height_nm"],py)==0
    rules, via = inputs["rules"], inputs["via45"]
    min_lengths = {m:math.ceil(rules[m]["getArea"]/rules[m]["getWidth"]) for m in ("M4","M5")}
    pin_size = [24,24]
    via_m4 = [via["M4"][2]-via["M4"][0], via["M4"][3]-via["M4"][1]]
    column = wake["elements"]["column"]
    reserve = 6957.34272  # prior 144-track/edge, 50%-availability reservation, not measured demand
    added = reserve+column["incremental_placement_um2_at_50pct"]
    bx,by = CONS_PITCH[PRODUCT_PITCH]["bf16_outline_um"]
    key = "w10_wake_access_contingency"
    if key in CONS_PITCH:
        raise ValueError("diagnostic key already present")
    CONS_PITCH[key] = dict(CONS_PITCH[PRODUCT_PITCH],bf16_outline_um=(bx+added/by,by))
    try:
        stages = cons_min_stages("analytical",CONS["overhead"],"ring",PRODUCT_GEOM,key,"columns","4096m8")
        head = cons_head_dies("analytical",CONS["overhead"],"ring",PRODUCT_GEOM,PRODUCT_PITCH,"8192m8")
        r = cons_v41_rom(stages,head,cons_table_dies("analytical")["dies"],bf16="columns",
            clock_hz=PRODUCT_CLOCK_HZ,field_concurrency=FIELD_CONCURRENCY,
            added_latency=dict(SOFTPLUS_FIX,**W11_STREAM_SS,**PLUS_LAT),dyn_scale=PRODUCT_DYN_SCALE,
            slow_domain=(0.9e9,"w18"),elem_stages=8,ss_wire=True,serial=PRODUCT_SERIAL,
            die=DIE_SHRUNK_INTERIM,vmh=VMC_FUSED,hub_block=PRODUCT_HUB)
    finally:
        del CONS_PITCH[key]
    expanded_half_span = (bx+added/by)/2
    extra_wire_stage = max(0,math.ceil(expanded_half_span/WIRE_REACH_SS_UM)-1)
    g = evaluate(copy.deepcopy(PRESETS["proposal"]))["_g"]
    families = {n.split(".",1)[1] if n.startswith(("L","E")) and "." in n else n
                for n,nd in g.nodes.items() if nd.get("_uarch")}
    assert all(nd["kind"]=="matvec" for n,nd in g.nodes.items()
               if any(n.endswith(f) for f in families))
    guarded = cons_v41_rom(stages,head,cons_table_dies("analytical")["dies"],bf16="columns",
        clock_hz=PRODUCT_CLOCK_HZ,field_concurrency=FIELD_CONCURRENCY,
        added_latency=dict(SOFTPLUS_FIX,**W11_STREAM_SS,**PLUS_LAT,
                           **{"suffix:"+f:extra_wire_stage for f in families}),
        dyn_scale=PRODUCT_DYN_SCALE,slow_domain=(0.9e9,"w18"),elem_stages=8,ss_wire=True,
        serial=PRODUCT_SERIAL,die=DIE_SHRUNK_INTERIM,vmh=VMC_FUSED,hub_block=PRODUCT_HUB)
    return dict(schema="opentallas.w10.pinaccess_contract_review.v1",verdict="NECESSARY_CONSTRAINTS_PROVED_FULL_ACCESS_PENDING",
        failed_baseline="c8 terminal rc1 DRT-0255, final abstract BLOCKED_INPUTS; no retry/tuning/rebase",
        exclusive_wake_owner=inputs["owner"],wake_source_commits=inputs["owner_commits"],
        inherited_pin_boundary=dict(same_LEF=True,same_executable_placement_body=inputs["wake_macro_placement_body_matches_failed_c8"],
            same_orientations=["R0","MX","MY","R180"],fixed_capture_flops=0,
            note="wake/leaf ICG and XF8 FIFO correctness do not establish ROM output access"),
        necessary_constraints=dict(pin_um=[v/1000 for v in pin_size],via45_M4_enclosure_um=[v/1000 for v in via_m4],
            direct_via_fits_port_rectangle=all(a<=b for a,b in zip(via_m4,pin_size)),
            minimum_metal_area_nm2={m:rules[m]["getArea"] for m in ("M4","M5")},
            minimum_straight_24nm_metal_length_nm=min_lengths,
            mirrored_center_phase_nm=mirrored_phase,M4_track_origin_nm=origin,
            required_mirrored_origin_phase_nm=required_origin,
            compatible_with_placement_site_lattice=feasible,
            common_site_track_period_nm=math.lcm(site["height_nm"],py),
            explanation="math feasibility is not a placement recipe; VIA45 overhang and minimum-area escape metal remain necessary"),
        local_power_observation=dict(M5_boxes=inputs["local_PG"],M4_special_metal_in_inspected_window=False,
            scope="only x139.3..141.7um/y123..132um near two failed outputs; not all-pin DRC"),
        capacity=dict(wake_column_XF=8,wake_incremental_placement_um2=column["incremental_placement_um2_at_50pct"],
            current_gross_spare_um2=column["spare_placement_um2"],escape_reservation_um2=reserve,
            combined_reserved_um2=added,gross_spare_after_both_um2=column["spare_placement_um2"]-added,
            fits_gross_existing_slot=added<=column["spare_placement_um2"],local_contiguity_proved=False,
            fifo_storage_bits_are_not_corridor_tracks="depth changes local storage/mux cost; crossing width depends on topology, not storage-bit sum"),
        fully_additive_contingency=dict(outline_um=[bx+added/by,by],extra_mm2_per_layer_die=added*1024/1e6,
            stages=stages,total_dies=r["dies"],ar_tokens_s=r["ar_tokens_s_b1"],token_us=1e6/r["ar_tokens_s_b1"],
            local_latency_delta_cycles="zero only for local capture/escape; long-span routing is conditional below",
            SS_wire_sensitivity=dict(expanded_half_span_um=expanded_half_span,measured_reach_um=WIRE_REACH_SS_UM,
                extra_stage_if_halfspan_crossed=extra_wire_stage,
                conservative_all_matvec_one_cycle=dict(ar_tokens_s=guarded["ar_tokens_s_b1"],
                    token_us=1e6/guarded["ar_tokens_s_b1"]),
                column_boundary_register_bits_upper=1616*extra_wire_stage,
                column_extra_placement_um2_at_50pct=1616*extra_wire_stage*DFF_UM2*2,
                basis="conditional upper bound; actual net topology must establish stage necessity; registers must fit local reserve or geometry be repriced before build"),
            added_stage_hops_included=True,
            basis="conservative all-additive reservation, no clock recovery; wire recalibration and actual local fit pending",adopted=False),
        admissible_next_step="Parent reviews a macro interface escape contract: actual VIA45 enclosure, minimum area, cut/EOL/spacing, PDN and simultaneous-bank captures at preserved throughput/rounding. Owner keeps existing wake jobs; no independent new candidate.",
        full_legal_access_proved=False,SS_FF_qualified=False,
        prohibitions=["no current macro relocation or source edit","no c8/FRONT_PAR retry","no duplicate wake or parity qualification","no calibration v2 refresh or duplicate v3"],
        missing_proof=["all orientations and all 288 ports, including via/cut/EOL rules",
            "simultaneous escapes and actual capture/mux endpoint congestion",
            "routed contextual SS/FF and qualified final abstract"],
        source_sha256=inputs["sources_sha256"])


def dsrom_s81_components(ctx=1048576):
    """Selected S81 component composition; unbound provider costs stay unknown."""
    from dsrom_s81_unified_components import build
    return build(ROOT, ctx=ctx)


def dsrom_s81_minimum_group(ctx=1048576):
    """Named minimum W11 construction branch, preserving the r4 historical floor."""
    from dsrom_s81_minimum_protected_group import build
    out = dsrom_s81_components(ctx)
    out['selected_minimum_W11_group'] = build(ROOT)
    out['selected_minimum_W11_group']['unified_S81']['global_r4_floor_not_added_to_new_group'] = True
    return out


def dsrom_s82_rows():
    """Opt-in retained-RD64 conditional composition; defaults are unchanged."""
    from dsrom_s82_token_pricing import build
    return build(ROOT)


def qwen_posted_kv_model(records):
    """Size the default-off posted-write issue gate, retaining retirement fences.

    The existing 64-entry write table and token assembly buffer retain ownership.
    This candidate removes only the HBM-ACK dependency of an ordinary SU issue;
    it keeps SU idle, barriers, END, and layer-context reuse checks unchanged.
    Stall counters give an opportunity bound, not a measured speedup.
    """
    rows = []
    pins = {}
    for filename in records:
        path = Path(filename)
        rec = json.loads(path.read_text())
        if rec.get("configuration") != "REAL_MEM":
            raise ValueError("posted-write sizing requires a REAL_MEM record")
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for stage, data in rec["stages"].items():
            if stage == "E":
                continue
            cycles = data["cycles"]
            opportunity = max(m["stall_drain"] for m in data["memory"].values())
            rows.append(dict(position=rec["position"], stage=stage, baseline_cycles=cycles,
                             baseline_qualified=rec["status"] == "pass" and rec["source_stable"],
                             possible_saved_cycles=[0, opportunity],
                             counter_opportunity_cycles=[cycles - opportunity, cycles],
                             counter_opportunity_rate_pct=100 * opportunity / (cycles - opportunity),
                             measured_saved_cycles=None))
    return dict(schema="opentallas.uarch.qwen_posted_kv.v1", rows=rows, source_sha256=pins,
                candidate="POSTED_KV=0 by default; release ordinary SU issue from write-done",
                fences=["SU idle before next ordinary SU operation",
                        "real tagged/generation-checked write-done before every barrier and END",
                        "retire all old read/write/assembly debt before layer-context reuse",
                        "next-token row reads and rollback cannot cross the retained END fence"],
                resources=dict(replicas=4, new_macs_per_cycle=0, new_memory_bytes_per_cycle=0,
                               new_boundary_bits_per_cycle=0, new_routing_tracks=0,
                               new_muxes=0, new_demuxes=0, new_fanout_loads=0,
                               new_storage_bits=0, incremental_area_mm2=0,
                               area_basis="compile-time issue predicate specialization; existing buffers unchanged",
                               slot_fit="reuse current core and KV service slots",
                               existing_write_entries_per_die=64,
                               existing_su_input_bytes_per_cycle=256,
                               existing_hbm_write_sector_bytes=32,
                               token_write_sectors_per_die=136),
                latency=dict(added_cycles=0, saved_cycles="bounded by measured stall_drain; fence residual unknown",
                             stream_hz=1.2e9, serial_hz=0.9e9,
                             clock_policy="SS setup 60ps / FF hold 25ps; unchanged, contextual closure pending"),
                bridge_pipeline="not included: ordinary issue still requires su_idle; needs separate credit sizing",
                adoption=False, measured_composed_gain_pct=None,
                qualification=["all pinned baseline runs terminal before successor launch",
                               "P0/P255/P1023 X and HBM writeback exact; no early visibility or rollback",
                               "measured gain >=1% after token composition", "contextual SS/FF and hub routing"])


SWITCH_RANGE_DIR = "results/uarch/hbm_switch_latency_range_20261004"            # literature range (SUPERSEDED)
SWITCH_AUTH_DIR = "results/uarch/hbm_switch_latency_authoritative_20261004"     # AUTHORITATIVE (owner 2026-10-04)
DSROM_WAVEFRONT = "results/rtl/dsrom_wavefront_verify_20261004/record.json"   # S81 + wavefront (ROM, light FEC)
DSROM_DRAFT_MEASURED = "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"   # measured draft (9ea29b069)
DSROM_DRAFT_L1L2 = "results/rtl/dsrom_dspark_l1l2_20261004/expected.json"     # L1 fused / L2 batched (EXPECTED, 2a235a9fe)
def dsrom_wavefront_mtp_tok_s(rom, rk):
    """DS ROM S81 + wavefront MTP tok/s (occupancy rule): the measured-draft composition (V41_ROM_DRAFT_RECORD,
    variant V41_ROM_DRAFT) unless --v41-rom-draft assumed, which keeps the record's assumed 0.1173 x AR draft."""
    if V41_ROM_DRAFT == "assumed":
        return rom[rk]["wavefront_occupancy"]["mtp_tok_s"]
    ctx = json.loads(V41_ROM_DRAFT_RECORD.read_text())["full_shape"]["ctx"][rk]
    return ctx[V41_ROM_DRAFT_VARIANTS[V41_ROM_DRAFT]]["wavefront_occupancy"]["mtp_tok_s"]


TAU_OWNER6 = 4.159      # SUPERSEDED 2026-10-04 (owner rule: tau from published third-party sources only). Our equal
                        # 6-class blend, gamma 5 (results/speculative/v41_mtp_acceptance_qualified_20261003/
                        # blend_owner6.json blends."owner 6-class equal".greedy.tau_blend_harmonic); kept for reproduction.
import third_party_tau as _TPT                                                     # noqa: E402
TAU_DS = _TPT.tau_ds_v41(5)               # DEFAULT: published third-party DSpark gamma-5 tau (OT_TAU_SOURCE=self_measured -> 4.159)
TAU_DS_SRC = _TPT.tau_src("deepseek_v41", 5)
NVLS_SCEN = ("push_optimistic", "nvls_measured", "gpu_fenced")
TU_SCEN = ("tomahawk_ultra_protocol", "tomahawk_ultra_inc")


def hbm_switch_latency_authoritative():
    """AUTHORITATIVE DS-V4.1 HBM per-user AR / MTP (tau TAU_DS = third-party published, gamma 5) at 1M and 200K under every switch scenario, for
    the W19 GPU-organised ablation, the accelerator (frozen HA firm ladder without R2 -- the switch tier is retained --
    and, under a replaced transport, without R3a, whose endpoint cut-through the replacement already contains), the
    measured composition and the GPU-faithful R0 row (every boundary a MEASURED H100 1.097 us grid sync); ROM:HBM
    against DS ROM S81 + wavefront with the MEASURED draft.  Default rows: ablation @ nvls_measured, accelerator @
    tomahawk_ultra_protocol, GPU-faithful @ gpu_fenced.  The collective TRANSPORT of each pass is re-priced per W19 op;
    the top-k merges' select compute is unchanged."""
    from hbm_accelerator_model import _load_study, COMPOSITION
    m, _, ds, _ = _load_study(ROOT)
    n = m.W19_COLL_COUNT
    n_draft = n["total"] * m.DRAFT_PARTS["collective"] / m.W19_AR["collective"]   # ASSUMED: same per-collective mix
    T = m.T
    base = {P: w19_transport_us(P, "w15", "kp4") for P in (1, 6)}
    sel = {P: m.VERIFY_PARTS[P]["collective"] - base[P] for P in (1, 6)}

    def delta(scen, fec="board", gathers="measured_ag", msg="small", cable="twinax_3m", P=1):
        """us added to a W19 pass of P positions (all 265 on-path collectives) by re-pricing their transport."""
        if scen in TU_SCEN:
            ops, _, _ = w19_collective_ops()
            return sum(tu_transport_us(o["kind"], P * o["bytes"], scen, cable) for o in ops) - base[P] \
                if cable != "twinax_3m" else w19_transport_us(P, scen) - base[P]
        if scen == "w15":
            return w19_transport_us(P, "w15", fec) - base[P] if fec == "kp4" else \
                -n["total"] * 2 * (HBM_SWITCH_LATENCY["kp4_leg_ns"] - HBM_SWITCH_LATENCY["light_leg_ns"]) * 1e-3
        fit = HBM_SWITCH_LATENCY["w15_fixed_ns"]
        ar = hbm_switch_collective_us(scen, "ar", fec, msg) - fit["ar"] * 1e-3
        ag = hbm_switch_collective_us(scen, "ag" if gathers == "measured_ag" else "ar", fec, msg) - fit["ag"] * 1e-3
        return n["all_reduce"] * ar + n["gather_like"] * ag

    rungs = {r: s for r, s, _ in m.ds_rungs(1, include_conditional=False)}
    rungs6 = {r: s for r, s, _ in m.ds_rungs(6, include_conditional=False)}
    hw_b = m.W19_BOUNDARY_CYC / m.F_FAST * 1e6

    def gpu_extra(parts, grid_ns):
        return parts["barrier"] / hw_b * (grid_ns * 1e-3 - hw_b)       # every boundary a grid sync

    def accel(replaced):
        keep = [r for r in rungs if r != "R2" and not (replaced and r == "R3a")]
        d = dict(m.DRAFT_PARTS)
        if not replaced:
            d["collective"] *= 1 - rungs["R3a"] / m.W19_AR["collective"]
        d["barrier"] *= (m.W19_BOUNDARY_CYC - m.W19_BARRIER_RELEASE_CYC) / m.W19_BOUNDARY_CYC
        return dict(ar=T(m.VERIFY_PARTS[1]) - sum(rungs[r] for r in keep),
                    ver=T(m.VERIFY_PARTS[6]) - sum(rungs6[r] for r in keep), draft=T(d), rungs=keep)
    g_new, g_old = GPU["barrier_ns_grid_h100_measured"], GPU["barrier_ns_grid_v100_superseded"]
    comp = json.loads((ROOT / COMPOSITION).read_text())["revisions"][-1]
    measured = sum(r["measured_gain_us"] for r in comp["rows"]
                   if r["measured_gain_us"] and not r["verdict"].startswith("REJECT"))
    gf = lambda g: dict(ar=T(m.VERIFY_PARTS[1]) + gpu_extra(m.VERIFY_PARTS[1], g),          # noqa: E731
                        ver=T(m.VERIFY_PARTS[6]) + gpu_extra(m.VERIFY_PARTS[6], g),
                        draft=T(m.DRAFT_PARTS) + gpu_extra(m.DRAFT_PARTS, g))
    designs = dict(
        ablation_w19=dict(ar=T(m.VERIFY_PARTS[1]), ver=T(m.VERIFY_PARTS[6]), draft=T(m.DRAFT_PARTS),
                          default=HBM_SWITCH_DEFAULTS["ablation"],
                          what="W19 composed GPU-organised HBM ablation (custom 62-cycle barrier; not GPU-real)"),
        accelerator_firm_switch=dict(default=HBM_SWITCH_DEFAULTS["accelerator"],
                                     what="frozen HA firm ladder (R0c..R6a, no R7a) WITHOUT R2 (the switch tier is "
                                          "retained; direct mesh owner-rejected) and, under a replaced transport, "
                                          "WITHOUT R3a (already inside it); UNVALIDATED hypothesis"),
        accelerator_measured_composition=dict(ar=T(m.VERIFY_PARTS[1]) - measured, ver=T(m.VERIFY_PARTS[6]) - measured,
                                              draft=T(m.DRAFT_PARTS), measured_gain_us=measured,
                                              default=HBM_SWITCH_DEFAULTS["accelerator"],
                                              what=f"W19 minus measured, non-rejected rung gains ({COMPOSITION} "
                                                   f"r{comp['revision']}: R5a 13.381 us, exact+measured, NOT adopted)"),
        gpu_faithful_r0=dict(**gf(g_new), default=HBM_SWITCH_DEFAULTS["gpu_faithful"],
                             what="W19 with every boundary a MEASURED H100 cooperative grid.sync (1.097 us, 132 SMs), "
                                  "study R0, GPU-faithful"),
        gpu_faithful_r0_v100_superseded=dict(**gf(g_old), default=HBM_SWITCH_DEFAULTS["gpu_faithful"],
                                             what="SUPERSEDED: the same row at the V100 1.43 us grid sync"))
    rom = json.loads((ROOT / DSROM_WAVEFRONT).read_text())["composition"]["ctx"]
    dft = json.loads((ROOT / DSROM_DRAFT_MEASURED).read_text())["full_shape"]["ctx"]
    l12 = json.loads((ROOT / DSROM_DRAFT_L1L2).read_text())["result"]["levers"]
    ctxs = {"1M": ("1048576", 1.0), "200K": ("200000", m.CTX_200K_RATIO)}
    romv = {c: dict(ar_tok_s=rom[rk]["ar_tok_s"],
                    mtp_as_built_tok_s=dft[rk]["as_built_chain"]["wavefront_occupancy"]["mtp_tok_s"],
                    mtp_fused_head_tok_s=dft[rk]["fused_head"]["wavefront_occupancy"]["mtp_tok_s"],
                    mtp_old_assumed_draft_tok_s=rom[rk]["wavefront_occupancy"]["mtp_tok_s"],
                    mtp_l1l2_rom_read_k5_tok_s=l12["l1l2/rom_read/k5"]["ctx"][rk]["occupancy"]["mtp_tok_s"],
                    mtp_l2_rom_read_k5_tok_s=l12["l2/rom_read/k5"]["ctx"][rk]["occupancy"]["mtp_tok_s"],
                    mtp_l1l2_mac_bound_tok_s=l12["l1l2/mac/k5"]["ctx"][rk]["occupancy"]["mtp_tok_s"])
            for c, (rk, _) in ctxs.items()}
    variants = [("w15", dict(fec="kp4")), ("w15", dict(fec="board"))]
    for sc in NVLS_SCEN:
        for fec in ("board", "kp4"):
            for gathers in ("measured_ag", "all_at_ar"):
                for msg in ("small", "32KB"):
                    variants.append((sc, dict(fec=fec, gathers=gathers, msg=msg)))
    for sc in TU_SCEN:
        for cable in ("twinax_3m", "smf_10m"):
            variants.append((sc, dict(cable=cable)))
    rows = []
    for ctx, (rk, k) in ctxs.items():
        rv = romv[ctx]
        for name, d0 in designs.items():
            for sc, kw in variants:
                dd = accel(sc != "w15") if name == "accelerator_firm_switch" else d0
                d1, d6 = delta(sc, P=1, **kw), delta(sc, P=6, **kw)
                ar = dd["ar"] * k + d1
                step = (dd["ver"] + dd["draft"]) * k + d6 + d1 * n_draft / n["total"]
                ar_r, mtp_r = 1e6 / ar, TAU_DS * 1e6 / step
                primary = kw.get("fec", "board") == "board" and kw.get("gathers", "measured_ag") == "measured_ag" \
                    and kw.get("msg", "small") == "small" and kw.get("cable", "twinax_3m") == "twinax_3m"
                rows.append(dict(ctx=ctx, design=name, scenario=sc, **kw, primary=primary,
                                 authoritative_default=primary and sc == d0["default"],
                                 ar_us=round(ar, 2), ar_tok_s=round(ar_r, 1), mtp_step_us=round(step, 2),
                                 mtp_tok_s=round(mtp_r, 1), rom_over_hbm_ar=round(rv["ar_tok_s"] / ar_r, 3),
                                 rom_over_hbm_mtp_as_built=round(rv["mtp_as_built_tok_s"] / mtp_r, 3),
                                 rom_over_hbm_mtp_fused_head=round(rv["mtp_fused_head_tok_s"] / mtp_r, 3),
                                 rom_over_hbm_mtp_l1l2_k5=round(rv["mtp_l1l2_rom_read_k5_tok_s"] / mtp_r, 3)))
    # ---- cross-checks: every transport figure computed a second way ----
    ops, _, _ = w19_collective_ops()
    import collections
    grp = collections.Counter((o["kind"], o["bytes"]) for o in ops)
    tu_grouped = {P: sum(c * tu_transport_us(kd, P * b) for (kd, b), c in grp.items()) for P in (1, 6)}
    xa = HBM_SWITCH_LATENCY["w15_fixed_ns"]
    checks = dict(
        w19_transport_plus_select_equals_study_collective={
            P: dict(transport=round(base[P], 3), select=round(sel[P], 3), study=m.VERIFY_PARTS[P]["collective"],
                    select_wsel256_expected=round(8 * 419 * P / m.F_FAST * 1e6, 3)) for P in (1, 6)},
        tomahawk_per_op_vs_grouped={P: [round(w19_transport_us(P, "tomahawk_ultra_protocol"), 6),
                                        round(tu_grouped[P], 6)] for P in (1, 6)},
        nvls_per_op_vs_count_formula={sc: [round(w19_transport_us(1, sc) - base[1], 6),
                                           round(n["all_reduce"] * (hbm_switch_collective_us(sc, "ar") - xa["ar"] * 1e-3)
                                                 + n["gather_like"] * (hbm_switch_collective_us(sc, "ag") - xa["ag"] * 1e-3), 6)]
                                      for sc in NVLS_SCEN},
        tomahawk_ar32k_by_hand_us=round((2 * 477.6 + 22 / 1.2 + 2 * 32768 / 720.0 + 150) * 1e-3, 6),
        tomahawk_ar32k_model_us=round(tu_transport_us("all_reduce", 32768), 6),
        collective_counts=dict(total=len(ops), all_reduce=sum(o["kind"] == "all_reduce" for o in ops)))
    tu_op_table = sorted([dict(kind=kd, bytes=b, count=c, tomahawk_us_p1=round(tu_transport_us(kd, b), 4),
                               tomahawk_us_p6=round(tu_transport_us(kd, 6 * b), 4),
                               inc_us_p1=round(tu_transport_us(kd, b, "tomahawk_ultra_inc"), 4))
                          for (kd, b), c in grp.items()], key=lambda r: (-r["count"], r["bytes"]))
    # default movement and the Qwen / GPU-baseline checks (every published default against the superseded one)
    global _HBM_SWITCH, NCCL_ALLREDUCE_S
    saved, nsaved, gsave = _HBM_SWITCH, NCCL_ALLREDUCE_S, GPU["barrier_ns_grid"]
    try:
        _HBM_SWITCH, NCCL_ALLREDUCE_S, GPU["barrier_ns_grid"] = "w15", NCCL_ALLREDUCE_ASSUMED_SUPERSEDED_S, g_old
        v_old, q_old, t_old = v41_hbm_rows(), qwen_hbm_rows(), gpu_tier2()
    finally:
        _HBM_SWITCH, NCCL_ALLREDUCE_S, GPU["barrier_ns_grid"] = saved, nsaved, gsave
    v_new, q_new, t_new = v41_hbm_rows(), qwen_hbm_rows(), gpu_tier2()
    pair = lambda o, w: [dict(design_superseded=a["design"], design=b["design"],          # noqa: E731
                              tokens_s_superseded=a.get("tokens_s"), tokens_s=b.get("tokens_s"))
                         for a, b in zip(o, w)]
    gb = {}
    for tag, val in (("superseded_assumed_8us", 8e-6), ("default_h100_fenced_oneshot_9p024us", NCCL_ALLREDUCE_S),
                     ("sensitivity_h100_nccl_no_graph_32us", 32e-6), ("sensitivity_h100_nccl_no_graph_36us", 36e-6)):
        NCCL_ALLREDUCE_S = val
        try:
            t2 = {x["design"]: x for x in gpu_tier2()}["DeepSeek-V4.1-Flash on 8x B200, calibrated"]
            gb[tag] = dict(per_ar_us=round(val * 1e6, 3), tokens_s=t2["tokens_s"], spec_tokens_s=t2["spec_tokens_s"],
                           collectives_us=t2["terms_us"]["collectives"],
                           ctx_1M_tok_s=round(1 / gpu_tier2_v41_ctx(1048576), 1),
                           ctx_200K_tok_s=round(1 / gpu_tier2_v41_ctx(200000), 1))
        finally:
            NCCL_ALLREDUCE_S = nsaved
    per_coll = {}
    for sc in ("w15",) + NVLS_SCEN + TU_SCEN:
        per_coll[sc] = {fec: {msg: dict(ar_us=round(hbm_switch_collective_us(sc, "ar", fec, msg), 4),
                                        ag_us=round(hbm_switch_collective_us(sc, "ag", fec, msg), 4))
                              for msg in ("small", "32KB")} for fec in ("board", "kp4")}
        per_coll[sc]["w19_mix_us_board_small"] = round(hbm_switch_mix_us(sc), 4)
    return dict(schema="opentallas.uarch.hbm_switch_latency_authoritative.v1", status="AUTHORITATIVE (owner 2026-10-04)",
                evidence="MODEL on MEASURED anchors (H100 NVLS) and VENDOR BUDGETS (Tomahawk Ultra / SUE RM104)",
                defaults=HBM_SWITCH_DEFAULTS, default_fec=_HBM_FEC, generation=HBM_SWITCH_LATENCY["generation"],
                measured_record="results/measured/h100_nvls_20261004/README.md",
                scenarios=HBM_SWITCH_LATENCY, aliases=HBM_SWITCH_ALIASES,
                superseded=dict(literature_range=HBM_SWITCH_LATENCY_LITERATURE_SUPERSEDED,
                                w15_switch_us=0.668, grid_sync_v100_ns=g_old,
                                nccl_assumed_us=NCCL_ALLREDUCE_ASSUMED_SUPERSEDED_S * 1e6),
                per_collective_us=per_coll, tomahawk_ops_w19=tu_op_table,
                tomahawk_derivation=dict(crossing_ns={c: tu_crossing_ns(c) for c in TU["cable_ns"]},
                                         reduce_ns=round(TU["reduce_ns"], 3), bw_GBps=TU["bw_Bps"] / 1e9,
                                         ar_32KB_us=round(tu_transport_us("all_reduce", 32768), 4),
                                         ar_32KB_smf10m_us=round(tu_transport_us("all_reduce", 32768, cable="smf_10m"), 4),
                                         gather_1536B_us=round(tu_transport_us("all_gather", 1536), 4),
                                         gather_10240B_us=round(tu_transport_us("all_gather", 10240), 4),
                                         gather_32256B_us=round(tu_transport_us("all_gather", 32256), 4),
                                         inc_ar_32KB_us=round(tu_transport_us("all_reduce", 32768, "tomahawk_ultra_inc"), 4),
                                         labels=dict(endpoint_bridge="VENDOR BUDGET", endpoint_phy="VENDOR BUDGET",
                                                     switch="VENDOR BUDGET", cable="RM104 per-metre",
                                                     reducer="MEASURED (HA2 RTL, LAT 7 x 3 + to_bf16)",
                                                     payload_eff="ASSUMED 0.9", tail="ASSUMED 0.15 (0.1-0.2)")),
                cross_checks=checks,
                collective_counts=dict(w19_pass=n, draft_assumed=round(n_draft, 2),
                                       draft_basis="W19 per-collective mix at P = 1 bytes x DRAFT_PARTS.collective / "
                                                   "W19 collective"),
                tau=TAU_DS, gamma=5, tau_src=TAU_DS_SRC, tau_superseded=dict(tau=TAU_OWNER6, src="results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json (self-measured)"),
                rom_records=dict(ar=DSROM_WAVEFRONT, mtp=DSROM_DRAFT_MEASURED, l1l2=DSROM_DRAFT_L1L2), rom_fec="light (130 ns board link)",
                rom=romv, rom_projections_note="L1 fused head = the measured-draft record's fused_head (= L1, 7,186 at "
                                               "1M); L2 batched head and L1+L2 = EXPECTED projections (no lever "
                                               "measured) from " + DSROM_DRAFT_L1L2 + ": rom_read-bound k5 shown; "
                                               "if the batched head is MAC-bound, L2 gains nothing",
                hbm_draft_note="the HBM draft is still the W19-record DRAFT_PARTS (51.88 us, 26.3 collectives "
                               "ASSUMED); the ROM draft is MEASURED (105.6 fused / 144.4 us as built at 1M)",
                designs={k: {x: (round(y, 3) if isinstance(y, float) else y) for x, y in v.items()}
                         for k, v in dict(designs, accelerator_firm_switch=dict(
                             designs["accelerator_firm_switch"], replaced=accel(True), w15=accel(False))).items()},
                grid_sync_ns=dict(h100_measured=g_new, v100_superseded=g_old),
                published_default_movement=dict(
                    v41_hbm_rows=pair(v_old, v_new), qwen_hbm_rows=pair(q_old, q_new), gpu_tier2=pair(t_old, t_new),
                    qwen_headline_unchanged=q_old[1]["tokens_s"] == q_new[1]["tokens_s"],
                    basis="superseded = w15 switch lump, NCCL 8 us assumed, V100 1.43 us grid sync"),
                qwen_gpu_baseline=dict(QWEN_GPU_H100_MEASURED, authoritative="1x H100 SXM, vLLM FP8, batch 1: "
                                       f"{QWEN_GPU_H100_MEASURED['fp8'][1]} tok/s (TP8 FP8 {QWEN_GPU_H100_MEASURED['fp8'][8]})",
                                       qwen_hbm_headline_tok_s=q_new[1]["tokens_s"],
                                       qwen_hbm_over_h100_fp8_tp1=round(q_new[1]["tokens_s"] / QWEN_GPU_H100_MEASURED["fp8"][1], 3),
                                       qwen_hbm_over_h100_fp8_tp8=round(q_new[1]["tokens_s"] / QWEN_GPU_H100_MEASURED["fp8"][8], 3),
                                       b200_model_row=[x for x in t_new if x["design"].startswith("Qwen3-8B")][0],
                                       note="the Qwen HBM die is at 8K context; the H100 rows are short context "
                                            "(128 in / 512 out) -- 8K runs pending"),
                gpu_baseline_check=dict(rows=gb, kernel_launch_ns=GPU["kernel_launch_ns_h100_measured"],
                                        graph_node_ns=GPU["graph_node_ns_h100_measured"],
                                        basis="tier-2 8x B200 V4.1 row: 40 layers x 5 all-reduces x NCCL_ALLREDUCE_S. "
                                              "Its fixed term is a fitted measurement (H200 NIM), so launch / graph "
                                              "overheads are already inside it; not added again"),
                retry_tail=dict(per_event_us=HBM_SWITCH_LATENCY["retry_tail_us"],
                                rule="p99-p99.9 LLR term; not in the median rows"),
                fec_rule="NVLS scenarios: fec=board (default) is the measured HGX board-reach path (reach-matched to "
                         "the ROM light-FEC board link); fec=kp4 adds (209-130) ns per SerDes leg.  Tomahawk Ultra: "
                         "the SUE rack budget (3 m twinax primary, 10 m SMF bracket); fec does not apply",
                rows=rows)


def hbm_switch_latency_range():
    """SUPERSEDED names: the switch-latency record is now the authoritative one."""
    return hbm_switch_latency_authoritative()


hbm_switch_latency_measured = hbm_switch_latency_range


HBM_DRAFT_MEASURED = "results/rtl/dshbm_dspark_draft_20261004/composition.json"   # MEASURED DS HBM draft (successor)


def hbm_mtp_both_drafts_measured():
    """SUCCESSOR (owner 2026-10-04) to the authoritative record's MTP columns: the DS HBM DSpark draft is MEASURED the
    way the ROM's is (tools/dshbm_dspark_draft_chain.py: closed-loop RTL chain bit-exact on the reduced vehicle,
    full-shape SM / argmax cycles, every draft collective counted and priced with the authoritative transports) and
    replaces DRAFT_PARTS (51.88 us, ASSUMED).  Step = verify(P=6) + draft + seed_commit on both sides (the ROM's
    seed_commit term; HBM: main_proj, main_x gather, main_norm, the stages' window rows, ctl commit).  The AR rows,
    the verify passes and hbm_switch_latency_authoritative() itself are unchanged."""
    rec = json.loads((ROOT / HBM_DRAFT_MEASURED).read_text())
    pick = lambda r, v: dict(draft_us=r[v]["draft_us"], step_us=r[v]["step_us"], mtp_tok_s=r[v]["mtp_tok_s"],  # noqa: E731
                             rom_over_hbm_mtp=r[v]["rom_over_hbm_mtp"])
    rows = [dict(ctx=r["ctx"], design=r["design"], scenario=r["scenario"], ar_tok_s=r["ar_tok_s"],
                 rom_over_hbm_ar=r["rom_over_hbm_ar"], seed_commit_us=r["seed_commit_us"],
                 model_draft_us=r["model_draft_us"], mtp_tok_s_model_draft=r["old_mtp_tok_s"],
                 as_built=pick(r, "as_built"), per_step_head=pick(r, "per_step_head"))
            for r in rec["rows"] if r["authoritative_default"]]
    return dict(schema="opentallas.uarch.hbm_mtp_both_drafts_measured.v1",
                status="AUTHORITATIVE successor for MTP (owner 2026-10-04); AR unchanged",
                hbm_draft_record=HBM_DRAFT_MEASURED, rom_draft_record=DSROM_DRAFT_MEASURED, tau=rec["tau"],
                hbm_variants=dict(as_built="the HBM design as built (ctl DHEAD = one 5-column head pass; bias + argmax "
                                           "fused in the SM epilogue): HBM already has the ROM's L1 and L2",
                                  per_step_head="the ROM as-built structure on HBM (one 1-column head pass a chain "
                                                "step), the like-for-like structural row"),
                rom_columns=dict(rom_as_built="ROM as built (measured)", rom_l1="ROM L1 fused head (measured record)",
                                 rom_l1l2_expected="ROM L1+L2 k=5 (EXPECTED projection)"),
                collective_count=rec["collective_count"], rows=rows)


def hbm_accel_rows():
    """Default-off HA0/HA10 hypotheses; no measured/adopted accelerator rate."""
    from hbm_accelerator_model import build
    return build(sys.modules[__name__])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hbrom-inputs", help="default-off ROM-fed reusable-compute cluster model input JSON")
    ap.add_argument("--ctx", type=int, default=1048576)
    ap.add_argument("--v41-rom-draft", choices=("as_built", "l1", "assumed"), default="as_built",
                    help="V4.1 ROM MTP draft time: MEASURED DSpark step (as_built, or l1 fused head) or the legacy "
                         "assumed 3/40 x AR (reproduces records made before 2026-10-04)")
    ap.add_argument("--dsrom-s81-minimum-group", action="store_true", help="selected W11 minimum protected group cuts/II/slot; target clocks, no fit or rate credit")
    ap.add_argument("--dsrom-s81-components", action="store_true", help="selected S81 measured component and finite VM r4 composition; no rate admission")
    ap.add_argument("--dsrom-s82", action="store_true", help="conditional S82 RD64 serial-path components; no full-token/physical admission")
    ap.add_argument("--w10-pinaccess-contract", help="bounded wake-aware interface review JSON")
    ap.add_argument("--w10-capacity", help="read-only c8 geometry JSON for capacity diagnosis")
    ap.add_argument("--w10-baseline", action="store_true", help="audit existing FAST/PP/BP baseline only")
    ap.add_argument("--w10-frontend", action="store_true", help="size the separate opt-in W10 frontend only")
    ap.add_argument("--preset", action="append")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--qwen", action="store_true", help="the Qwen3-8B ROM die rows only")
    ap.add_argument("--qwen-posted-kv-baseline", action="append", help="REAL_MEM record for default-off posted-write sizing")
    ap.add_argument("--hbm", action="store_true", help="the GPU-organised HBM ablation only")
    ap.add_argument("--hbm-accel", action="store_true",
                    help="default-off UNVALIDATED HBM accelerator ladder and fairness hypotheses")
    ap.add_argument("--hbm-switch-latency-authoritative", "--hbm-switch-latency-range", "--hbm-switch-latency-measured",
                    dest="hbm_switch_latency_range", action="store_true",
                    help="AUTHORITATIVE HBM switch collective record: every scenario, DS HBM AR/MTP, ROM:HBM, "
                         "GPU-faithful, GPU baseline and Qwen checks")
    ap.add_argument("--hbm-mtp-drafts-measured", action="store_true",
                    help="SUCCESSOR MTP rows: DS HBM and ROM drafts both MEASURED (results/rtl/dshbm_dspark_draft_20261004)")
    ap.add_argument("--hbm-switch-latency", choices=("w15", "push_optimistic", "nvls_measured", "gpu_fenced",
                                                     "tomahawk_ultra_protocol", "tomahawk_ultra_inc",
                                                     "low", "central", "high"),
                    help="the GPU-organised V4.1 HBM chain's switch scenario (default nvls_measured; with --hbm-accel "
                         "the accelerator's, default tomahawk_ultra_protocol; w15 = superseded 0.668 us)")
    ap.add_argument("--hbm-fec", choices=("board", "kp4"),
                    help="with --hbm-switch-latency: reach class (default board = as measured; kp4 = rack cable)")
    ap.add_argument("--fec-fairness", action="store_true", help="same-FEC ROM board/NVLink-class switch model-only timing rows")
    ap.add_argument("--spec", action="store_true", help="speculation (MTP / DFlash) rows")
    ap.add_argument("--v41-hbm-dspark", action="store_true", help="OPT-IN: V4.1 HBM DSpark rows (priced draft, "
                    "measured expert union) from results/speculative/v41_hbm_speculation_methods_20261003")
    ap.add_argument("--fabric", action="store_true", help="collective-latency sweep and GPU tiers")
    ap.add_argument("--dedicated", action="store_true", help="the dedicated-unit ledger (W11) of each preset only")
    ap.add_argument("--vm-waterfall", action="store_true", help="the VM waterfall and levers (root 2026-10-01)")
    ap.add_argument("--economics", action="store_true", help="batch, energy and cost of every design and GPU tier")
    ap.add_argument("--levers", action="store_true", help="V4.1 static-power gating, adaptive MTP, ROM mask cost")
    ap.add_argument("--consolidation", action="store_true",
                    help="V4.1 ROM die consolidation, right-sized HBM dies, HBM die-count sweep, comparison rule")
    a = ap.parse_args(argv)
    if a.hbrom_inputs:
        import hbrom_model
        inputs = json.loads(Path(a.hbrom_inputs).read_text())
        result = hbrom_model.sweep(inputs)
        payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    global V41_ROM_DRAFT
    V41_ROM_DRAFT = a.v41_rom_draft
    global _HBM_SWITCH, _HBM_FEC
    _HBM_SWITCH = HBM_SWITCH_ALIASES.get(a.hbm_switch_latency, a.hbm_switch_latency) or _HBM_SWITCH
    _HBM_FEC = a.hbm_fec or _HBM_FEC
    if a.hbm_mtp_drafts_measured:
        payload = json.dumps(hbm_mtp_both_drafts_measured(), indent=1, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.hbm_switch_latency_range:
        payload = json.dumps(hbm_switch_latency_range(), indent=1, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.fec_fairness:
        from fec_class_fairness import policy
        payload = json.dumps(policy(ROOT), indent=2, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.dsrom_s81_minimum_group:
        payload = json.dumps(dsrom_s81_minimum_group(a.ctx), indent=2, sort_keys=True, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.dsrom_s81_components:
        payload = json.dumps(dsrom_s81_components(a.ctx), indent=2, sort_keys=True, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.hbm_accel:
        acc = hbm_accel_rows()
        # AUTHORITATIVE (owner 2026-10-04): the accelerator's published rows ride Tomahawk Ultra + our protocol;
        # --hbm-switch-latency selects another scenario's rows
        sc = HBM_SWITCH_ALIASES.get(a.hbm_switch_latency, a.hbm_switch_latency) or HBM_SWITCH_DEFAULTS["accelerator"]
        rng = hbm_switch_latency_authoritative()
        acc["switch_latency_scenario"] = dict(scenario=sc, src=SWITCH_AUTH_DIR, default=HBM_SWITCH_DEFAULTS["accelerator"],
            rows=[r for r in rng["rows"] if r["scenario"] == sc and r["primary"]
                  and r["design"].startswith("accelerator")])
        payload = json.dumps(acc, indent=2, allow_nan=False) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.dsrom_s82 or a.qwen_posted_kv_baseline:
        if a.dsrom_s82:
            payload = json.dumps(dsrom_s82_rows(), indent=2, sort_keys=True) + "\n"
        else:
            payload = json.dumps(qwen_posted_kv_model(a.qwen_posted_kv_baseline), indent=2) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.w10_pinaccess_contract:
        payload = json.dumps(w10_pinaccess_contract_review(json.loads(Path(a.w10_pinaccess_contract).read_text())), indent=2) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.w10_capacity:
        payload = json.dumps(w10_capacity_diagnosis(json.loads(Path(a.w10_capacity).read_text())), indent=2) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.w10_baseline:
        payload = json.dumps(w10_baseline_model(), indent=2) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.w10_frontend:
        r = w10_frontend_model()
        payload = json.dumps(r, indent=2) + "\n"
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(payload)
        print(payload)
        return
    if a.consolidation:
        import hashlib
        cs = consolidation()
        for r in cs["v41_rom"]["points"]:
            print(f"ROM {r['label']:44s} dies {r['dies']:4d} (L {r['layer_dies']} H {r['head_dies']} T {r['table_dies']})  "
                  f"AR {r['ar_tokens_s_b1']:8.1f} MTP {r['mtp_tokens_s_b1']:8.1f}  sat {r['ar_saturated_tokens_s']:9.1f}  "
                  f"gated mJ b1 {r['energy']['ar_b1']['gated_mJ']:8.1f} sat {r['energy']['ar_sat']['gated_mJ']:7.1f}  "
                  f"capex ${r['cost']['capex_usd']['low']:,}-{r['cost']['capex_usd']['high']:,}")
        for r in cs["hbm"]["v41_sweep"]:
            print(f"HBM N={r['dies']:3d} x{r['stacks_per_die']}  users {r['capacity_users_1m']:6d}  AR {r['ar']['batch1']['per_user_tokens_s']:8.1f}"
                  f"  MTP {r['mtp']['batch1']['per_user_tokens_s']:8.1f}  sat {r['ar']['saturated']['aggregate_tokens_s']:9.1f}"
                  f"  gated mJ b1 {r['ar']['batch1']['gated_mJ']:8.1f}  capex ${r['cost']['capex_usd']['low']:,}")
        for r in cs["comparison_rule"]["v41"]:
            print("RULE", r["rule"], r["stacks_per_die"], r.get("dies"), r.get("replicas"),
                  r.get("ar", {}).get("batch1", {}).get("per_user_tokens_s"), r.get("ar", {}).get("saturated", {}).get("aggregate_tokens_s"))
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in CONS_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.consolidation.v1", **cs, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.levers:
        import hashlib
        lv = economics_levers()
        sp = lv["static_power"]
        for mode in ("ar", "mtp_m1"):
            for wk in ("wake_1us", "wake_c6_133us"):
                for pt in ("batch1", "saturated"):
                    for r in sp[mode][wk][pt]:
                        print(f"{mode:6s} {wk:14s} {pt:9s} {r['policy']:34s} static {r['static_mJ_per_token']:9.2f} mJ  "
                              f"total {r['energy_mJ_per_token']:9.2f} mJ  {r['static_w']:8.0f} W  gated {r['stages_power_gated']}")
                print(f"   wake on token path {sp[mode][wk]['wake_on_token_path_us']} us, min idle {sp[mode][wk]['min_idle_batch1_us']} us")
        for r in lv["gated_alike"]["rows"]:
            print(f"GATED {r['design']:28s} {r['point']:9s} {r['tokens_s']:9.1f} tok/s  ungated {r['ungated_mJ_per_token']:9.2f}"
                  f"  clock {r['clock_gated_mJ_per_token']:9.2f}  clock+power {r['clock_and_power_gated_mJ_per_token']:9.2f} mJ")
        for k, v in lv["adaptive_mtp"].items():
            print(k, "switch", v["switch_users"], [(r["batch"], r["mode"], r["per_user_tokens_s"], r["aggregate_tokens_s"]) for r in v["rows"]])
        for r in lv["rom_masks"]["rows"]:
            print(f"{r['design'][:10]:10s} {r['case']:70s} NRE {r['nre_usd'] / 1e6:8.1f}M  capex {r['capex_per_system_usd']:>10,}  "
                  f"$/tok/s b1 {r['usd_per_tokens_s_b1']:8.2f} sat {r['usd_per_tokens_s_saturated']:7.2f} "
                  f"(base excl. {r['usd_per_tokens_s_saturated_base_excluded']})")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in LEVER_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.economics_levers.v1", **lv, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.economics:
        import hashlib
        ec = economics()
        for r in ec["summary"]:
            print(f"{r['design']:28s} b1 {r['tokens_s_b1']:9.1f} tok/s {r['energy_mJ_b1']:9.2f} mJ | sat B={r['sat_batch']:4d} "
                  f"{r['sat_aggregate_tokens_s']:10.1f} tok/s ({r['sat_per_user_tokens_s']:8.1f}/user) "
                  f"{r['energy_mJ_sat']:8.2f} mJ | cap {r['capacity_users']}")
        for r in ec["cost"]:
            print(f"{r['design']:32s} ${r['capex_per_system_usd']['low']:>12,}-{r['capex_per_system_usd']['high']:>12,}  "
                  f"$/tok/s b1 {r['usd_per_tokens_s_b1']}  sat {r['usd_per_tokens_s_saturated']}  "
                  f"slo {r['tokens_s_at_slo']} {r['usd_per_tokens_s_at_slo']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in ECON_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.economics.v1", **ec, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.fabric:
        t2 = gpu_tier2()
        t3 = qwen_hbm_tau_sensitivity()
        for r in TIER1 + t2 + t3:
            print(r)
        rows = fabric_sweep()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.fabric.v1", tier1=TIER1, tier2=t2,
                                                   tier3_qwen_tau=t3,
                                                   sweep=rows, nccl_allreduce_s_assumed=NCCL_ALLREDUCE_S),
                                              indent=1, default=str) + "\n")
        return
    if a.vm_waterfall:
        w = cons_vm_waterfall()
        for r in w["waterfall"]:
            print(f"{r['ar_tokens_s_b1']:8.1f} {r['delta_ar'] or 0:+8.1f}  {r['stages']} / {r['dies']}  {r['step']}")
        for r in w["levers"]:
            print(f"{r['ar_tokens_s_b1']:8.1f} {r['vs_vmh_reference_pct']:+6.1f}%  {r['stages']} / {r['dies']}  {r['lever']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(w, indent=1, default=str) + "\n")
        return
    if a.dedicated:
        rows = [dedicated_ledger(copy.deepcopy(PRESETS[n]), a.ctx) for n in (a.preset or ("as_built", "proposal"))]
        # root decisions of 2026-09-29 (W11): 16 NK=4 index slices, NL=4 attention with the two-word loader;
        # single position and the MTP verify pass (6 positions, m = 1)
        w11 = dict(copy.deepcopy(PRESETS["proposal"]), idx_macs=262144, att_macs=32768, att_pwords=2,
                   su_bcast_stages=SU_BCAST_STAGES_W1, su_ret_stages=SU_RET_STAGES_W1,
                   vmh_block=PRODUCT_HUB)   # ROOT RULINGS 2026-10-01: the product's SU+VM block (W18b packs this row)
        for P in (1, 6):
            rows.append(dedicated_ledger(dict(w11, name=f"proposal_w11_p{P}"), a.ctx, positions=P))
        for r in rows:
            print(f"{r['design']:14s} hub {r['hub_logic_mm2']:7.2f}/{r['hub_avail_mm2']} mm2  "
                  + "  ".join(f"{k}:{v['area_mm2'] if 'area_mm2' in v else '-'}" for k, v in r["units"].items())
                  + (f"  DISCREPANCIES {r['discrepancies']}" if r["discrepancies"] else ""))
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            import hashlib
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in (
                "tools/uarch_model.py", "tools/arch_budget_v41.py", "tools/rtl_hdc_v41x_vec_campaign.py",
                "results/arch/arch_budget_v41.json")}
            for u in DEDICATED.values():
                for k, q in u.items():
                    if k.startswith(("hardened_record", "measured_record")) and (ROOT / q).exists():
                        pins[q] = hashlib.sha256((ROOT / q).read_bytes()).hexdigest()
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.v41_dedicated.v1", ctx=a.ctx, rows=rows,
                                                   elements=DEDICATED, source_sha256=pins), indent=1, default=str)
                                   + "\n")
        return
    if a.spec:
        rows = speculation_rows()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.speculation.v1", rows=rows,
                                                   decisions=dict(v41_rom="MTP m=1 time-multiplexed",
                                                                  qwen_rom="AR only (no drafter in ROM)",
                                                                  hbm="DFlash / MTP on the SM design (W13)")),
                                              indent=1, default=str) + "\n")
        return
    if a.hbm:
        rows = qwen_hbm_rows() + v41_hbm_rows()
        dq = hbm_gpu_design("qwen")
        spec = hbm_speculation_rows()
        for r in spec:
            print(f"   spec {r['design']:24s} {r['tokens_s']:9.1f} tok/s  tau {r.get('tau', 1.0)}  speedup {r.get('speedup', 1.0)}")
        for r in rows:
            print(f"{r['design']:30s} {r['tokens_s']:9.1f} tok/s  T {r['T_us']:9.1f} us  supply {r['supply_frac']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.hbm_gpu.v2", rows=rows, gpu=GPU,
                                                   speculation=spec,
                                                   designs=dict(qwen=dq, v41=hbm_gpu_design("v41"))),
                                              indent=1, default=str) + "\n")
        return
    if a.qwen:
        rows = qwen_rows()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.qwen_rom.v1", rows=rows,
                                                   wire=QWEN_WIRE, area=QWEN_AREA), indent=1, default=str) + "\n")
        return
    names = a.preset or list(PRESETS)
    rows = []
    for n in names:
        d = copy.deepcopy(PRESETS[n])
        r = evaluate(d, a.ctx)
        r["params"] = {k: v for k, v in d.items()}
        r["area"] = area_ledger(d)
        r["network"] = network_ledger(d, r["clock_hz"])
        g = r.pop("_g")
        r["power"] = power_ledger(d, g, r["clock_hz"], r["tokens_s"], r["area"])
        r["power_wire_0p4"] = power_ledger(d, g, r["clock_hz"], r["tokens_s"], r["area"], wire_j=0.4e-12)
        rows.append(r)
        print(f"{n:22s} T={r['T_us']:9.1f} us  {r['tokens_s']:8.1f} tok/s   (arch {r['arch_tokens_s']:.0f})"
              f"  strip {r['area']['rom_field_strip_used_mm2']}/{r['area']['rom_field_strip_avail_mm2']}"
              f"  hub {r['area']['hub_logic_mm2']}/{r['area']['hub_avail_mm2']}"
              f"  P1 {r['power']['total_w_single_user']} W  Psat {r['power']['total_w_saturated']} W")
        print("   ", {k: v for k, v in list(r["breakdown_us"].items())[:6]})
        print("   top:", list(r["critical_path_by_node_us"].items())[:8])
    out = dict(schema="opentallas.uarch.v41_rom.v1", ctx=a.ctx, rows=rows)
    if "proposal" in names:
        out["power_clock_sensitivity"] = power_clock_sensitivity("proposal", a.ctx)
    if a.sweep:
        out["sweep"] = sweep(a.ctx)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


def dsrom_s81_native_su_prefix():
    """Selected SUN256 leaf and its explicit minimum-component staging costs.

    Functional operand staging is charged separately from the existing SU.
    Unbound arbitration, routes and visibility prohibit product-rate credit.
    """
    path = Path(__file__).resolve().parents[1] / 'results/uarch/dsrom_sun256_native_prefix_20261004/model.json'
    selected = json.loads(path.read_text())
    staging = selected['extra_staging']
    state_bits = (staging['payload_bits'] + staging['address_valid_metadata_floor_bits']
                  + staging['output_collect_data_address_bits'] + staging['descriptor_hold_bits'])
    return dict(schema='opentallas.dsrom.S81.native-SU-prefix.v1',
        adopted=False, scope='Selected native leaf/component integration; no token-rate or physical admission',
        selected_model=str(path.relative_to(path.parents[3])),
        parameters=selected['parameters'], ports=selected['ports'],
        MACs_per_cycle_peak=selected['parameters']['N'],
        operand_bytes_per_edge_peak=selected['ports']['native_operand_bits'] // 8,
        compute_intensity_MACs_per_operand_byte=selected['parameters']['N'] / (selected['ports']['native_operand_bits'] // 8),
        native_write_bytes_per_edge_peak=4 * (selected['ports']['native_VM_write_lanes'] + selected['ports']['native_reducer_write_lanes']),
        prefix_operations=selected['prefix_operations'],
        adapter_calendar=selected['adapter_calendar'],
        staging=staging, state_bits_floor=state_bits,
        staging_DFF_floor_mm2=state_bits * DFF_UM2 / 1e6,
        replicas_per_rank=1, TP=4,
        routing_tracks_data_bundle_floor=selected['ports']['native_operand_bits'],
        corridor_capacity=None, slot_fit=False, SS_FF_in_context=False,
        mux_fanout_cost='Actual staged operand read ports and retained native writes; no additional unlimited VM port',
        missing_costs=selected['missing_costs'],
        combined_single_user_added_us=None, overlap_credit_us=0)


def dsrom_s81_native_su_ik128():
    """Opt-in literal I36 IK128 address selection; existing SUN256 body costs.

    KVT_SH is a compile-time wire shift into the unchanged address adders.
    This selects the D128 writer layout, not dynamic format selection or a
    strobe remap. Existing prefix defaults and headline rows stay unchanged.
    """
    base = dsrom_s81_native_su_prefix()
    selected = copy.deepcopy(base)
    selected['schema'] = 'opentallas.dsrom.S81.native-SU-IK128.v1'
    selected['parameters']['KVT_SH'] = 11
    source_paths = (
        'rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv',
        'tools/runtime/dsrom/s81_minimum_l20_index_writer.cpp',
    )
    selected.update(
        scope='Opt-in minimum native L20.I36 IK128 SUN256 SH11 source binding; not a final S81 headline change',
        literal_source='L20.I36 unit2 dst3 nin128 nout1 abase94496 asi1 obase0; actual DY4 GLOBAL row = position; backend local record is separate',
        literal_word_sha256='436e442bdf1b4743ac79abc55ab08892561afe7bfdf29803d631ed531180c072',
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
        IK_dimensions=128, interleaved_rows=16, scalar_element_bits=32,
        prior_KVT_SH=9, selected_KVT_SH=11,
        prior_block_stride_elements=512, selected_block_stride_elements=2048,
        prior_block_stride_bytes=2048, selected_block_stride_bytes=8192,
        address_formula='obase + ((row >> 4) << KVT_SH) + (dimension << 4) + (row & 15)',
        prior_stride_collision={'row0_dimension32': 512, 'row16_dimension0': 512},
        target_global_position=1048575, target_DY4=1048575,
        target_dimension0_element_address=134215695,
        target_dimension127_element_address=134217727,
        selected_address_extent_bytes=536870912,
        address_extent_scope='Logical selected scalar-address extent, not physical replicated bank capacity',
        selected_body_delta=dict(MACs_per_cycle=0, memory_ports=0, boundary_bits=0,
                                 state_bits=0, replicas=0, mux_demux=0, fanout=0,
                                 address_adders=0, pipeline_cycles=0,
                                 new_body_area_mm2=0, single_user_added_latency_cycles=0),
        constant_wire_stride_delta='Existing row high bits align two positions higher into same AW30 adders; no dynamic shifter, added stage, new engine or strobe rewrite',
        routing_cost='Same bounded bus/port/replica inventory; selected wire endpoints differ. Exact placed routes and SS/FF remain unqualified, not zero-cost physical qualification.',
        all_KV_formats_qualified=False, physical_dynamic_selection_qualified=False,
        minimum_selected_build_model_ready=True,
        measured_runtime_qualified=False, measured_rate_credit=0,
    )
    return selected


def dsrom_s81_native_su_kvt_stride_policy():
    """Priced opt-in captured-ni fixed SH11/SH13 selector, before KVT add.

    Source scope is Arch's 82 selected KVT operations: D128 IK and D512 KT.
    Other formats are outside this selection. No extra register or engine.
    """
    base = dsrom_s81_native_su_prefix()
    lanes = base['parameters']['N']
    aw = base['parameters']['AW']
    cw = 24  # ot_hdc_v41x_vec.sv localparam CW; existing ni_e per lane.
    # Existing model uses ASSUMED 0.2 um2/2:1 bit mux (HBM mux screen).
    # Equality network proxy is explicit, not mapped area/timing evidence.
    mux_um2 = lanes * aw * 0.2
    compare_um2 = lanes * cw * 0.2
    return dict(
        schema='opentallas.dsrom.S81.native-SU-KVT-stride-policy.v1',
        adopted=False, model_ready_for_selected_RTL=True,
        source_scope='82 canonical KVT ops; L20.I21/I53 D512, L20.I36 D128',
        base_parameters=base['parameters'], ports=base['ports'],
        supported_dimensions=[128,512], shifts={128:11,512:13},
        block_stride_elements={128:2048,512:8192},
        selection='Captured ni_e==128 selects fixed (row_e>>4)<<11; otherwise selected D512 uses fixed <<13, before existing u_kv1. Unsupported dimensions are not enrolled.',
        arithmetic_order='Existing u_kv1 base+block_offset, then u_kv2 dimension<<4|row_low4 unchanged',
        defaultoff_required=True, captured_control='Existing CW24 ni_e in same emitting lane/stage; no new capture FF',
        MACs_per_cycle_peak=base['MACs_per_cycle_peak'],
        operand_bytes_per_edge_peak=base['operand_bytes_per_edge_peak'],
        native_write_bytes_per_edge_peak=base['native_write_bytes_per_edge_peak'],
        new_ports=0, new_queues=0, new_engine_replicas=0, new_FF_bits=0,
        new_address_adders=0, new_pipeline_cycles=0,
        replicas_per_rank=base['replicas_per_rank'], TP=base['TP'],
        mux_bits_per_lane=aw, mux_bits_per_rank=lanes*aw,
        equality_bits_per_lane=cw, equality_bits_per_rank=lanes*cw,
        local_select_fanout_per_lane=aw,
        extra_ni_bit_compare_loads_per_lane=1,
        extra_global_control_broadcast_bits=0,
        area_basis='ASSUMED analytical proxy 0.2um2/mux-bit and 0.2um2/equality-input-bit; no mapped/routed/SSFF claim',
        mux_proxy_um2_per_rank=mux_um2,
        equality_proxy_um2_per_rank=compare_um2,
        added_cell_proxy_mm2_per_rank=(mux_um2+compare_um2)/1e6,
        added_cell_proxy_mm2_TP4=4*(mux_um2+compare_um2)/1e6,
        loaded_path='ni_e -> CW24 equality -> AW30 fixed-offset mux -> existing u_kv1 -> u_kv2 -> same f_o register',
        loaded_path_SS_FF_closed=False, loaded_path_delay_ps=None,
        added_latency_cycles=0, added_physical_latency_ps=None,
        all_KV_formats_qualified=False, physical_dynamic_selection_qualified=False,
        measured_rate_credit=0,
        source_sha256=dsrom_s81_native_su_ik128()['source_sha256'],
        fixed_IK_SH11_minimum_build_independent=True,
    )


def dsrom_s81_native_he_bootstrap():
    """Native prefix leaves, reusing selected HE and SUN256 reducer arithmetic.

    A source-component gate, not another physical engine allocation. Actual
    VM/weight providers must supply fixed-latency reads and matched visibility.
    """
    return dict(schema='opentallas.dsrom.S81.native-HE-bootstrap.v1',
        all_numbers='SOURCE_BOUND_MODEL_NOT_MEASURED_TOKEN_RATE', adopted=False,
        HE=dict(source='rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv', HW=8, TL=9,
            KCMAX=2560, PMAX=2, MP=1, AW=30, NW=21, BAW=16,
            FP32_MAC_lanes=64, MACs_per_cycle_peak=64,
            VM_read_ports=8, VM_read_bytes_per_edge_peak=32,
            weight_read_banks=8, weight_bytes_per_edge_peak=256,
            weight_data_boundary_bits=2048, VM_read_data_boundary_bits=256,
            VM_read_address_boundary_bits=240, output_masked_data_boundary_bits=1024,
            output_address_bits=30, output_mask_bits=32,
            input_staging_BF16_bits=8*2*320*8*16,
            nout=24, K=20480, runs_per_row=320, input_LOAD_read_edges=2560,
            dot_products=491520, minimum_issue_edges=24*320,
            scalar_normalization_in_HE=False,
            LOAD_capture_edges=2, command_staging_edges=1,
            native_tail_and_result_drain_edges=None,
            ordered_arithmetic='chunk8 R-ARITH, sequential products per chunk then padded pairwise tree; raw mode scale=0',
            accepted_VM_visibility_not_engine_idle=True),
        SSX=dict(source='rtl/hdc/ot_hdc_vreduce.sv', SW=256, LV=7, AW=30,
            source_H_words=20480, source_H_base=0, result_address=40960,
            vector_accepts=80, VM_read_bytes_per_vector=1024,
            actual_target_read_span_words=16, staging_reads_per_vector=16,
            actual_target_read_span_beats=1280,
            actual_target_read_boundary_bits=512,
            assembly_rule='Each 256-word vector requires sixteen identity/address-qualified same-VM 16-word returns; valid only after complete assembly. No unlimited 256-lane target callback implied.',
            read_data_boundary_bits=8192, squared_multipliers=256,
            chain_adders=32*7, vector_tree_adders=31, time_tree_adders=7,
            MACs_per_cycle=0, multiplier_ops=20480,
            source_order='R-ARITH su csum over all H squared: contiguous8 sequential, padded pairwise tree; no interleaved partials or per-copy regrouping',
            first_input_to_output_pipeline_edges_model=3+1+21+5*4+7*4+1,
            no_stall_vector_issue_edges=80, actual_VM_read_and_visibility_edges=None,
            arithmetic_replica_count=1, already_selected_SUN256_reducer=True,
            additional_physical_MAC_or_reducer_area_charge_mm2=0),
        PF=dict(addresses=[41152,41153,41154,41155], raw_FP32_words=[1065353216]*4,
            role='Declared identity literals only, not trained/expected intermediate activation',
            native_VM_write_beats=4, accepted_visibility_required=True),
        adapter=dict(shared_clock_edges_only=True, holding_input_vector_bits=8192,
            holding_output_word_bits=32, saved_identity_bits=47,
            counters_and_flags_bits=33, reserved_HE_write_seats=32,
            HE_write_seat_bits=1024+30+32+47+2,
            minimum_added_state_bits=8192+32+47+33+32*(1024+30+32+47+2),
            DFF_cell_floor_mm2=(8192+32+47+33+32*(1024+30+32+47+2))*DFF_UM2/1e6,
            no_new_ROM_storage=True, borrowed_arithmetic_credit_not_extra_engine=True,
            VM_staging_arbitration_routes_area_mm2=None, replicas_per_rank=1, TP=4,
            route_tracks_minimum_data_bundle=8192, corridor_capacity=None,
            fanout_mux_cost='Bind existing VM read fabric and eight HE weight banks; no ideal unlimited provider or dropped fixed-latency response',
            slot_fit=False, SS_FF_in_context=False),
        cold_critical_path='embedding actual H visibility -> 80 accepted SSX vectors -> native SSX result -> actual VM SSX/PF visibility -> L0I0 -> I1 native HE -> remaining SU prefix. No CPU FP arithmetic or expected XN restore.',
        combined_single_user_added_us=None,
        overlap_credit_us=0, actual_provider_deadlines_required=True)


def dsrom_s81_native_he_bootstrap_source():
    """Additive corrected source-factory contract; prior component stays history."""
    row=copy.deepcopy(dsrom_s81_native_he_bootstrap())
    row['schema']='opentallas.dsrom.S81.native-HE-bootstrap.source-factory.v2'
    row['PF']['raw_FP32_words']=[1065353216,0,0,0]
    row['adapter'].update(explicit_bootstrap_arming=True, per_operation_inputs_ready=True,
        sole_edge_owner='bootstrap participant; HE participant only drives ports; zero prepare evals; one native eval per rising/falling edge',
        runtime_reserved_tag_namespace_only=True, grouped_scalar_acceptance_inferred=False,
        actual_same_VM_scalar_prefetch_words=20480,
        raw_cached_H_bytes=81920, raw_H_cache_register_floor_mm2=20480*32*DFF_UM2/1e6,
        source_VM_read_return_latency_edges=4, source_old_request_reuse_wait_required=True,
        scalar_serial_read_service_edges_model=20480*6,
        serial_read_edge_derivation='Request acceptedE; native target returnedatE+4postedge; bootstrap polls E+5prepare; next scalar starts E+6. One canonicalbank, no private grouped acceptance.',
        source_VM_capture_identity_callbacks_required=True,
        H_cache_reuse_for_HE='Only literalI1 under unchanged H lease; L0I0 writes RF40992, not H. No source-version substitution or host FP.',
        raw_HE_image_bytes=24*20480*4,
        actual_HE_image_required='hbank.hex plus hbank.source full revision/tensor/dtype/shape/HHW8 codec/SHA; no zero fallback',
        software_immutable_image_mirror_not_free_new_hardware_storage=True)
    row['corrected_source_factory_symbol']='dsrom_s81_bind_minimum_he_bootstrap'
    row['cold_critical_path']='Actual embedding publication -> explicit arm -> serialized actual H read returns -> 80 native SSX vectors -> native SSX/PF reserved scalar commands -> actual scalar ACKs -> per-op native inputs_ready -> L0I0/I1/remainingSU. Routes/provider/clock costs remain additive; no ideal native-port overlap.'
    return row


def dsrom_s81_embedding_bootstrap(inventory, rom_capture_cycles=8):
    """Cold token ROM lookup; retained dedicated storage, no field refit.

    One outstanding 256-bit lookup, then four 16-lane FP32 VM commits.
    Native backpressure adds cycles. Capture depth is an explicit unvalidated
    parameter, not a macro SS/FF qualification or a new headline rate.
    """
    storage = inventory['dedicated_storage']['global_tensors'][0]
    assert storage['tensor'] == 'embed.weight' and storage['shape'] == [129280, 5120]
    assert inventory['stages'] == 81 and storage['word_data_bits'] == 256
    words = 5120 // 16
    # RTL state is one response register plus identity, token/address, counters.
    state_bits = 256 + 47 + 26 + 19 + 9 + 2 + 2 + 2
    return dict(schema='opentallas.dsrom.S81.embedding-bootstrap.model.v1',
        all_numbers='MODEL_UNVALIDATED', adopted=False,
        source_inventory='results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json',
        retained_storage=storage, retained_storage_credit_mm2=0,
        geometry_changed=False, ROM_ECC=False, replicas=1, MACs_per_cycle=0,
        compute_intensity_MAC_per_byte=0, lookup_words_per_token=words,
        one_outstanding_request=True, rom_response_bytes=32,
        ROM_port_bytes_per_cycle_peak=32, VM_write_bytes_per_cycle_peak=64,
        VM_commits_per_token=words*4, VM_FP32_words_per_token=20480,
        clock_hz=1.2e9, rom_capture_cycles=rom_capture_cycles,
        no_stall_latency_cycles=1 + words*(1+rom_capture_cycles+4),
        no_stall_latency_us=(1 + words*(1+rom_capture_cycles+4))/1200,
        composed_single_user_contribution='Cold embedding before native SSX reduction/L0.I0; stalls and transport are additive',
        communication_intensity_FP32_output_bytes_per_source_byte=8,
        boundary_bits_per_cycle=dict(ROM_response=256, VM_commit=512,
            ROM_request=73, saved_context=47),
        routing_tracks_required=dict(ROM_response_data=256, VM_commit_data=512,
            VM_address=19, VM_identity=47, ROM_address=26),
        routing_channel_capacity=None, routing_fit_qualified=False,
        mux_demux_fanout='Single selected macro return mux retained in storage ledger; 16 BF16-to-FP32 wiring lanes, 4 sequential HC copies, one target VM endpoint at a time. TP4 fanout/delivery requires parent pricing.',
        state_bits=state_bits, register_cell_lower_bound_mm2=state_bits*DFF_UM2/1e6,
        unpriced_control_and_routes=['token/address decode and bounds', 'macro return mux/control',
            'VM 16-lane arbitration/commit port', 'dedicated-store to TP4 transport', 'CTS/PDN/routes'],
        floorplan_slot_fit=None, physical_SS_FF_qualified=False,
        numerical_work='Lossless BF16 bits <<16; no arithmetic, expected activation or CPU inference',
        required_next_native_producer='SSX = golden-order sum of H squared; never host-computed here')


def dsrom_s81_native_head_terminal():
    """Additive ordered-root/argmax leaf; not an enrolled head-ROM producer."""
    fifo=16; owner=47; rows=32320
    bits=16*(32+17+1)+9*17+6*32+47+1+1+2+15+5+4+4+5+32+32+17+1+1
    return dict(schema='opentallas.dsrom.S81.native-head-terminal.v1',
        status='MODEL_UNVALIDATED_COMPONENT_ONLY', opt_in_default=False,
        rows_global=129280, rows_per_rank=rows, ranks=4, K=5120,
        retained_head_pairs=2525, retained_head_macros=10100,
        retained_storage_increment_mm2=0, ROM_ECC=False,
        golden_merge='root4096 + ((root1024 + +0) + +0)',
        source_arithmetic='ot_hdc_fp32_add_fast unchanged; three LAT3 RNE adds; finite FP32 logits; +/-0 equal; lowest global ID on ties',
        MACs_per_cycle=0, FP32_adds_per_row=3, add_replicas=3,
        accepted_pair_II_cycles=1, pipeline_add_latency_cycles=9,
        comparator_update_cycles_after_last_add=1,
        reserved_logit_seats=fifo, owner_identity_bits=owner,
        root_input_bytes_per_cycle_peak=8, logit_output_bytes_per_cycle_peak=4,
        boundaries_bits=dict(root_pair=64, global_row=17, owner=owner,
                            held_logit=32+17+1, terminal=32+17+owner+1),
        tracks_required=dict(root_pair=64, root_owner=owner, global_row=17,
                            logit=50, terminal=97),
        state_FF_bits_lower_bound=bits,
        state_scope='External leaf registers only; unchanged three FP32 adder internal storage/logic separately unpriced',
        state_FF_cell_lower_bound_mm2=bits*DFF_UM2/1e6,
        compute_intensity_FP32_adds_per_input_byte=3/8,
        communication_intensity_output_bytes_per_input_byte=0.5,
        composed_single_user_cycles_lower_bound=rows+10,
        serial_clock_hz=0.9e9,
        composed_single_user_us_lower_bound=(rows+10)/900,
        latency_scope='From first accepted ordered root pair through local argmax; ROM/VM/subtree/link/CDC/held output ACK and four-rank gather additional, not zero',
        floorplan_slot_fit=None, routing_channel_capacity=None,
        new_adders_and_comparator_mapped_area_mm2=None,
        mux_fanout='One root pair per native edge; bounded16-seat logit FIFO; one scalar compare; owner47 held once; no array replication credited',
        actual_root_producer='Arch/Boole ordered K4096/K1024 native subtrees, still requires source-bound matched row/lease delivery',
        compiler_and_ROM_address_owner='Popper',
        core_connection='Current X_ROM1/X_ME0 e_am zeros and legacy EAM selection remain unchanged; explicit defaultoff successor connection required',
        physical_SS_FF=False, trained_payload_qualified=False, adopted=False)


def dsrom_s81_native_head_carried():
    """Selected successor: unchanged native ROM carried argmax, full envelope."""
    base=dsrom_s81_native_head_terminal()
    # Declared storage of the existing LANES16/DEPTH8 reducer. Two512+last
    # elastic registers in EACH of its input/output skids are counted.
    native_bits=32*(32+4+1)+3*5+5*32+5*8+65+8*73+4*4+32+1+4*514
    wrapper_bits=base['state_FF_bits_lower_bound']-82-2-1+64+1
    return dict(base, schema='opentallas.dsrom.S81.native-head-carried.v1',
        selected_comparator='rtl/rom/collectives/ot_rom_argmax_reduce.sv unchanged LANES16 DEPTH8',
        predecessor_new_comparator='Isolated component reference only, not selected/adopted',
        ranks=4, carried_chain_order=[0,1,2,3],
        identity_envelope=dict(owner=47,request_sequence=64,flit=512,last=1),
        packet_bits_with_envelope=624,
        sequence_scope='64-bit host/native command envelope; actual provider mapping and no-wrap/closed-owner lease must be enrolled before source execution. No truncation into native tag8.',
        local_tag8='constant0 internal only; full owner47+sequence64 checked at every accepted pair/upstream transfer and retained until actual downstream ACK',
        root_input_bytes_per_cycle_peak=8,logit_output_bytes_per_cycle_peak=4,
        accepted_frame_credits_per_rank=1,
        native_depth8_not_eight_new_owner_credits=True,
        native_declared_state_bits=native_bits,
        wrapper_state_bits=wrapper_bits,
        state_FF_bits_lower_bound=native_bits+wrapper_bits,
        state_FF_cell_lower_bound_mm2=(native_bits+wrapper_bits)*DFF_UM2/1e6,
        native_body_increment_if_already_charged_mm2=0,
        body_charge_rule='Replace prior selector charge with existing native reducer inventory exactly once; state count is inventory, not additional full-body area',
        global_flit_acceptance='Matching full owner/sequence only, rank-ascending source path, no second upstream frame. Native output held until local accepted logits all ACK and actual dn_ready.',
        composed_single_user_cycles_lower_bound=32320+17,
        composed_single_user_us_lower_bound=(32320+17)/900,
        latency_scope='MODEL lower bound for one local merge+LANES16 reducer;4-rank skids/link/CDC/held ACK additive, actual chain measurement next',
        fault_recovery='Sticky quarantine, drains accepted logit suffix; no restart or upstream-owner release on fault. Causal fault/recovery provider not invented.')


def dsrom_s81_head_result_hook(roots=128):
    """Selected actual ROM FP32 writer -> reused explicit-ID argmax hook."""
    assert roots in (64,128)
    levels=roots.bit_length()-1
    native_declared_bits=2*roots*(32+32+1)+3*(levels+1)+(levels+1)*40+65+8*73+49+4*514
    return dict(schema='opentallas.dsrom.S81.head-result-hook.v1',
        opt_in_default=False, MACs_per_cycle=0, new_dot_arithmetic=False,
        reused='ot_rom_argmax_reduce comparator, running best, FIFO and skid source; explicit actual row IDs replace inferred base+lane',
        roots=roots, native_argmax_lanes=roots, native_argmax_depth=8,
        source_input='Actual rom_we && capture_vm_accept, rom_wdata FP32, global ID=rank*32320+rom_waddr-head_obase*W',
        head_admission='Contiguous m_k5120 split0 round0 amax1 mmode0, formatter mode1. Released BF16 head-normalizer input proof remains compiler/provider responsibility.',
        native_tag8='Internal0; full capture_identity47 held/checked on carried input, never truncated',
        comparison_rule='Actual global ID tie at leaf tree, running best and carried join; signed zeros equal; native NaN faults, return poison/nonfinite quarantines final token',
        selected_storage_pairs=2525, selected_storage_macros=10100, retained_storage_increment_mm2=0,
        replicas=4, source_return_bytes_per_cycle=roots*4,
        source_return_boundary_bits=roots*(32+30+1),
        carried_boundary_bits=512+1+47,
        routing_tracks_required=dict(return_data=roots*32,return_mask=roots,carried_packet=513,carried_identity=47),
        native_declared_state_bits_per_rank=native_declared_bits,
        added_explicit_ID_state_bits_per_rank=2*roots*(32-levels),
        adapter_state_bits_per_rank=178,
        final_global_broadcast='Actual rank3 native record -> existing source multicast/collector, all4 core final_ready ACKs required; no local result accepted as global',
        existing_body_charge='Reuse/reconcile prior head selector/collective charge once; explicit-ID delta and adapter separately, no storage charge duplication',
        added_ID_FF_floor_mm2=2*roots*(32-levels)*DFF_UM2/1e6,
        source_VM_logit_writes_per_rank=32320,
        MACs_per_input_byte=0, comparator_intensity_per_input_byte=(roots-1)/(roots*4),
        native_last_writer_to_local_slice_cycles_lower_bound=levels+3,
        global_carried_edges='3rank boundaries plus actual native skids/link/CDC/ACK; no ideal overlap or physical0 assumption',
        routing_channel_capacity=None, floorplan_slot_fit=None, SS_FF=False,
        token_latency_in_model='Existing selected head dot/source delivery unchanged; native local slice tail levels+3 and carried transport/ACK additive; complete physical/token latency not qualified',
        source_binding='One active actual capture command; hold native core idle until carried DN matched acceptance. Fault never publishes a token or clears owner.')


if __name__ == "__main__":
    main()


def dsrom_s81_native_bf_head_producer():
    """Serialized native archive reuse vehicle, not a new parallel head engine."""
    rows, k, ranks = 32320, 5120, 4
    return {
        'schema': 'dsrom.s81.native_bf_head_producer.v1',
        'selected_storage': 'existing dedicated BF head2525pairs/10100macros; unchanged',
        'ranks': ranks, 'rows_per_rank': rows, 'k': k,
        'macs_per_rank': rows*k, 'macs_per_native_word_per_bank': 16,
        'native_macro_read_bits': 274, 'native_pair_read_bits': 548,
        'released_raw_bytes_per_native_word': 256,
        'released_raw_useful_bytes_per_native_word': 32,
        'released_provider_port_bytes_per_cycle': None,
        'native_rom_words_per_rank_per_bank': (rows//2)*320,
        'activation_snapshot_bytes_per_reused_vehicle': k*4,
        'ordered_root_staging_bits_per_vehicle': 2*2*32,
        'native_input_boundary_bits': 1024+32+4+3+3+1,
        'native_return': 'retained RD64 branch + D128/QD128 root, nseg1; no host arithmetic',
        'grain_issue_cycles_per_rowpair': [256,64],
        'grain_issue_lower_bound_cycles_per_rank': (rows//2)*320,
        'latency_terms': ['source XN acquisition5120 scalar words on actual ready',
                          'two actual CFG/GO/native BF phases per rowpair',
                          'PB lane recurrence LAT8, native EARLY tree',
                          'actual retained return/capture/drain before rebind',
                          'actual carried B+0+0 and A+B, finite in_ready',
                          'actual global argmax chain/final broadcast and VM ACK'],
        'replicas_in_reuse_vehicle': 1,
        'replicas_if_four_rank_host_participants': 4,
        'physical_parallel_head_replicas': None,
        'new_engine_area_mm2': 0,
        'simulation_snapshot_and_controls_are_not_hardware_free_area': True,
        'source_provider_routing_tracks': None, 'physical_slot_fit': None,
        'token_latency_ns': None, 'headline_or_rate_credit': False,
        'default_enabled': False,
    }


def hbm_dspark_ctl_fast_prefix_candidate():
    """FAST-only W16 carry repair, model before RTL; no clock/rate adoption.

    Existing control accepts the same commands and emits the same values on
    the same edges. Retain ctl_f1 output SS miss and full spec_f1 setup fail.
    """
    return dict(model_record="results/uarch/hbm_accel_fmax_ctl_20261004/prebuild_model.json",
                adopted=False, target_period_ps=833, SS_setup_uncertainty_ps=60,
                FF_hold_uncertainty_ps=25, replicas=1, MACs_per_cycle=0,
                new_memory_ports=0, new_boundary_bits=0, new_latency_cycles=0,
                single_user_token_latency_delta_cycles=0, FAST_default=0,
                retained_fast_fbase_FF_bits=16, repair_additional_FF_bits=0,
                carry_width=16, carry_levels=5, carry_prefix_nodes=54,
                local_kept_wire_bits=204, local_prefix_fanout_bound=2,
                gate_equivalent_upper=210, added_logic_proxy_um2=105,
                added_50pct_reservation_proxy_um2=210,
                area_basis="assumed0.5um2/gate; mapped/routed area not measured",
                required_leaf_area_growth_um2=210, physical_fit=False,
                SS_FF_closed=False, measured_gain=False)


def dsrom_wfc_local_control_price(maxu=866, nw=21, flit=512, txq=4):
    """Same-edge control locality repair for the measured reset-corrected WFC.

    Copies uchk2 inside each existing upos group, fed from uchk on the same
    edge. A one-hot write-bank mirror advances with the existing queue pointer.
    No reset-root replication, valid-mask removal, or pipeline edge is added.
    Cell footprints come from the pinned ASAP7 SS/FF cell-price record.
    This reservation is a prebuild estimate, not mapped area or timing credit.
    """
    groups = (maxu + 31) // 32
    ff = groups + txq
    # Three buffers per new FF (clock/reset/input), plus one per 32 queue bits.
    buffers = 3 * ff + txq * ((flit + 31) // 32)
    # Four NAND2 equivalents per bank-enable mux, one common inversion, and
    # eight per bank for local pointer/priority qualification. No removal credit.
    nand2 = 4 * txq + 1 + 8 * txq
    gross = ff * 0.37908 + buffers * 0.10206 + nand2 * 0.08748
    return dict(source='rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
                baseline_controller_sha256='26d07e2e852779ed85cf5538b205d1ded6cd593e3567012797a45e1c252975ba',
                price_source='results/uarch/dsrom_s81_minimum_protected_group_20261004/inputs/cell_prices.json',
                default_enabled=False, adopted=False, MACs_per_cycle=0,
                replicas=1, maxu=maxu, nw=nw, flit=flit, txq=txq,
                groups=groups, new_FF_bits=ff, read_control_FF_bits=groups,
                write_bank_FF_bits=txq, buffer_reservation_cells=buffers,
                NAND2_equivalent_reservation=nand2,
                gross_cell_reservation_um2=gross,
                additional_implementation_reservation_um2=gross,
                total_cell_growth_budget_um2=2*gross, old_cell_removal_credit_um2=0,
                SS_new_clock_pin_cap_fF=ff*0.433982,
                SS_new_reset_pin_cap_fF=ff*0.704025,
                SS_read_control_input_pin_cap_fF=groups*0.527811,
                new_external_boundary_bits_per_cycle=0, new_memory_ports=0,
                new_memory_bytes_per_cycle=0, new_pipeline_edges=0,
                single_user_token_latency_delta_cycles=0, issue_interval_delta_cycles=0,
                reset_root_copies=0, valid_mask_bits_removed=0,
                local_group_read_control_sink_bound=nw,
                write_bank_control_sink_bound=flit,
                write_bank_buffer_leaf_sink_reservation=32,
                additional_narrow_control_connections_bound=2*groups+3*txq,
                existing_stage_core_area_um2=37498,
                existing_stage_routed_cell_area_um2=15990.6,
                projected_cell_fraction_with_growth_budget=(15990.6+2*gross)/37498,
                existing_floorplan_retained=True, routing_capacity_proven=False,
                mapped_area_proven=False, SS_FF_closed=False,
                target_period_ps=833, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
                obligations='Keep each group copy local; preserve queue priority/debt and reset edges; measure the same fullshape context and routed channel/area limits. Reservation is not guaranteed physical fit.')




def dsrom_wfc_reset_release_gate_price():
    """Owner-supplied reset-release qualifiers, not a clock-domain change.

    The existing rst_q register still releases one edge after rst_n. Suppress
    all link admission/write and core-start terms during that existing edge;
    no new state or steady-state response edge is added.
    """
    signals = ['in_ready', 'rx_hdr', 'rx_res', 'rx_side', 'vm_we',
               'st_rx', 'st_new', 'st_q', 'st_fb', 'st_wk', 'core_start']
    nand2, buffers = 2*len(signals), 3*len(signals)
    gross = nand2*0.08748 + buffers*0.10206
    return dict(new_FF_bits=0, new_clock_pin_cap_fF_SS=0, new_memory_ports=0,
                new_memory_bytes_per_cycle=0, MACs_per_cycle=0, replicas=1,
                reset_qualified_terms=signals, added_pipeline_edges=0,
                reset_release_edges_after_rst_n=1, steady_state_cycle_delta=0,
                model_reference_cycle_contract='Existing registered-root +1 reset edge; SOURCE1 serial engine +3.7 cycles/issue historical until remeasured. Golden rounding and reductions unchanged.',
                NAND2_equivalent_reservation=nand2, buffer_reservation_cells=buffers,
                gross_cell_reservation_um2=gross, total_cell_growth_budget_um2=2*gross,
                original_clock_and_reset_register_unchanged=True,
                full_shape=dict(WIN=6,FLIT=512,NW=21,AW=30,VWA=15,USER_W=10,MAXU=866,KVW=32768),
                target_period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
                utilizations=[0.40,0.45,0.50], actual_route_fit_unknown=True,
                price_source='results/uarch/dsrom_s81_minimum_protected_group_20261004/inputs/cell_prices.json',
                prior_r12_source_sha256='26d07e2e852779ed85cf5538b205d1ded6cd593e3567012797a45e1c252975ba',
                physical_adopted=False)


def dsrom_wfc_typed_completion_price(idw=47, paw=14, nw=21):
    """Add one retained terminal kind to the finite END/result join.

    STAGE_HANDOFF never asserts token validity; token result still requires
    fresh native argmax. No reset/clock/cycle or arithmetic change.
    """
    base = dsrom_wfc_stage_completion_join_price(idw, paw, nw)
    nand2, buffers = 32, 3
    gross = 0.37908 + nand2*0.08748 + buffers*0.10206
    return dict(base=base, kind_bits=1, new_FF_bits=base['new_FF_bits']+1,
                kind_increment_NAND2_reservation=nand2,
                kind_increment_buffer_cells=buffers,
                kind_increment_gross_um2=gross,
                kind_increment_budget_um2=2*gross,
                total_cell_growth_budget_um2=base['total_cell_growth_budget_um2']+2*gross,
                added_response_edges=0, new_memory_ports=0,
                new_clock_pin_cap_fF_SS=0.433982,
                kinds={'TOKEN_RESULT': 0, 'STAGE_HANDOFF': 1},
                stage_handoff='Real bound END/context plus entire ordered coverage and real final fence/visibility; no argmax required and token_result_valid is always false.',
                token_result='Original fresh bound native argmax producer and END required.',
                physical_context_ready=False, SS_FF_closed=False)


def dsrom_wfc_stage_completion_parent_interface_price(idw=47, paw=14, nw=21):
    """Wire-only native source edge exports, before source overlay generation.

    Actual observed pins gain load; routing is not free even without new FFs.
    Buffer reservation is a model budget, not enrollment of a real consumer.
    """
    bits = 8 + 3*idw + 3*paw + nw + 32
    nand2 = 18  # qualifier AND gates, including three-input admission/launch
    buffers = 3*bits
    gross = nand2*0.08748 + buffers*0.10206
    return dict(replicas=1, new_FF_bits=0, new_clock_pin_cap_fF_SS=0,
                new_memory_ports=0, new_memory_bytes_per_cycle=0, MACs_per_cycle=0,
                new_output_boundary_bits=bits, added_response_edges=0,
                NAND2_equivalent_reservation=nand2, buffer_reservation_cells=buffers,
                gross_cell_reservation_um2=gross, total_cell_growth_budget_um2=2*gross,
                parent_source_clock='selected clk unchanged',
                actual_consumer_loads=None, routing_capacity_proven=False,
                physical_context_ready=False, SS_FF_closed=False,
                note='Actual descriptor admission, FIFO launch, registered engine start and retirement are distinct edges; exports do not assert wholeplan coverage.')


def dsrom_wfc_stage_completion_join_price(idw=47, paw=14, nw=21):
    """One finite retained stage result, qualified by real source-owned pins.

    Complete plan coverage and five visibility predicates are REQUIRED inputs;
    this join never counts a fragment END as whole-plan coverage. The selected
    native END/result and C8/capture/collective health bind inside the overlay.
    Functional implementation needs that contract, not prior STA arrival data.
    """
    metadata_bits = idw + 3*paw
    result_bits = nw + 32
    flags = 5  # active, fresh producer, END pending, result held, quarantine
    ff = metadata_bits + result_bits + flags
    compare_bits = 3*idw + 3*paw
    comparison_nand2 = 7*compare_bits + 8*paw
    control_nand2 = 128
    mux_nand2 = 4*ff
    buffers = 3*ff
    nand2 = comparison_nand2 + control_nand2 + mux_nand2
    gross = ff*0.37908 + buffers*0.10206 + nand2*0.08748
    return dict(default_enabled=False, adopted=False, replicas=1,
                retained_slots=1, new_FF_bits=ff, saved_metadata_bits=metadata_bits,
                retained_result_bits=result_bits, control_flags=flags,
                equality_compare_bits=compare_bits,
                comparison_NAND2_reservation=comparison_nand2,
                control_NAND2_reservation=control_nand2, mux_NAND2_reservation=mux_nand2,
                buffer_reservation_cells=buffers, NAND2_equivalent_reservation=nand2,
                gross_cell_reservation_um2=gross,
                additional_implementation_reservation_um2=gross,
                total_cell_growth_budget_um2=2*gross, old_cell_removal_credit_um2=0,
                MACs_per_cycle=0, new_memory_ports=0, new_memory_bytes_per_cycle=0,
                required_source_authority_input_bits=(2+metadata_bits)+(2+idw)+(2+idw+5),
                producer_data_bits_per_edge=result_bits, native_result_capture_words=1,
                added_response_edges_when_all_authorities_visible=0,
                response_basis='END is sampled on its native edge; following-cycle native done/data may bypass retention on the original response edge. Held data waits for real coverage/visibility/quiet, never a fixed timer.',
                coverage_counters_added=0, coverage_authority='Required identity-matched wholeplan coverage pin; actual owner hook remains unbound',
                warm_reset='Preserve retained metadata/data/debt and quarantine any active request; no reset retirement',
                clock='same selected native clk', new_clock_pin_cap_fF_SS=ff*0.433982,
                mapped_area_proven=False, routing_capacity_proven=False,
                source_contract_for_component_ready=True, physical_context_ready=False,
                actual_SS_FF_arrivals=None, SS_FF_closed=False,
                target_period_ps=833, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
                price_source='results/uarch/dsrom_s81_minimum_protected_group_20261004/inputs/cell_prices.json',
                physical_obligation='Charge this retained result and all comparators/enable/clock/reset buffers in actual parent slot and route required authority ports; no fulltop fit or signoff credit.')


def dsrom_wfc_completion_edge_price(nw=21, exposed_completions=6,
                                   measured_stage_cycles=73670):
    """Unselected one-edge completion alternatives, priced on a retained trace.

    This is a conditional calendar charge, not a changed RTL measurement.
    A one-bit hop requires source-held data and identity through the new edge.
    A finite capture holds the actual producer's token/value plus validity;
    neither alternative licenses new work to overwrite its request context.
    """
    payload = nw + 32
    choices = {}
    for name, data_bits in [('parent_held_data_hop', 0),
                            ('finite_result_capture', payload)]:
        ff = data_bits + 1
        # Payload uses unreset FFs, validity uses the existing reset cell type.
        nand2 = 4*data_bits + 32  # hold mux plus bounded local valid control
        buffers = 3*ff + 16      # clock/D/reset and distributed local control
        gross = data_bits*0.2916 + 0.37908 + nand2*0.08748 + buffers*0.10206
        choices[name] = dict(new_FF_bits=ff, retained_payload_bits=data_bits,
                            NAND2_reservation=nand2, buffer_reservation_cells=buffers,
                            gross_cell_reservation_um2=gross,
                            total_growth_budget_um2=2*gross,
                            old_cell_removal_credit_um2=0,
                            new_clock_pin_cap_fF_SS=data_bits*0.446638 + 0.433982,
                            new_reset_pin_cap_fF_SS=0.704025,
                            parent_result_hold_required=(data_bits == 0),
                            request_context_retention_required=True,
                            new_memory_ports=0, new_memory_bytes_per_cycle=0,
                            new_external_payload_bits_per_edge=0,
                            producer_payload_bits_per_capture=payload,
                            capture_data_local_wire_bits=data_bits,
                            local_valid_control_bits=1,
                            routing_capacity_proven=False,
                            actual_parent_loads=None,
                            budget_fraction_of_smallest_failed_cell_area=2*gross/15787.9,
                            actual_parent_slot_fit_proven=False,
                            excludes_separate_internal_control_repair=True,
                            added_completion_edges=1)
    return dict(schema='opentallas.dsrom.wfc.completion_edge_price.v1',
                model_only=True, implementation_selected=False, adopted=False,
                source='rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
                baseline_controller_sha256='601461579813e5d5f992c5ece1ac79c770b7e973ed87b4c913ea5c3f9655d099',
                source_terms=['core_done/core_next_token/core_next_val',
                              'job_done and TXQ payload capture',
                              'core_free/tx_reading/VM arbitration and request context'],
                choices=choices, MACs_per_cycle=0,
                target_period_ps=833, SS_setup_uncertainty_ps=60,
                FF_hold_uncertainty_ps=25, SS_FF_closed=False,
                calendar=dict(vehicle='original L20 stage9_w1 dependency retry PASS',
                              measured_stage_cycles=measured_stage_cycles,
                              actual_completion_events=exposed_completions,
                              added_edges_if_every_event_exposed=exposed_completions,
                              target_period_scale_only_added_ns=exposed_completions*0.833,
                              fractional_calendar_charge=exposed_completions/measured_stage_cycles,
                              rate_loss_if_other_edges_unchanged=exposed_completions/(measured_stage_cycles+exposed_completions),
                              whole_token_exposed_events=None,
                              whole_token_latency_delta_ns=None,
                              composition='deltaT=sum(exposed completion hops * actual controller period) + changed service/phase/credit waits; no free overlap or token extrapolation'),
                physical_gain_measured=False, actual_parent_launch_clock=None,
                actual_parent_result_hold_contract=None, mapped_area_proven=False,
                internal_user_position_path_repaired=False,
                reset_recovery_failure=False,
                owner_decision='CLAUDE chooses the actual completion/capture contract and separate internal-control repair. No RTL/campaign authorized by this model.',
                price_source='results/uarch/dsrom_s81_minimum_protected_group_20261004/inputs/cell_prices.json')


def dsrom_wfc_completion_ready_price(nw=21, txq=4):
    """Conditional same-edge completion-ready lookahead, not an adopted repair.

    A registered predicate must equal F(current state), computed from the
    exact next running/TX state/read-inflight/queue count on the preceding edge.
    Registering F(current state) instead adds an edge and is not this recipe.
    Actual parent completion/data launch clocks and arrivals remain required.
    """
    qb = max(1, (txq - 1).bit_length())
    count_bits = qb + 1
    arithmetic_nand2 = 2 * count_bits * 9
    state_mux_nand2 = 5 * 3 * 4
    running_mux_nand2 = 8
    predicate_nand2 = 24
    nand2 = arithmetic_nand2 + state_mux_nand2 + running_mux_nand2 + predicate_nand2
    ff = 1
    buffers = 3 + 16  # new CLK/reset/D plus distributed completion control.
    gross = ff*0.37908 + buffers*0.10206 + nand2*0.08748
    return dict(adopted=False, implementation_selected=False,
                source='rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
                baseline_controller_sha256='d02775f0047629d103892db3a9d04563b75cf922d899ffa48da435f41024e790',
                price_source='results/uarch/dsrom_s81_minimum_protected_group_20261004/inputs/cell_prices.json',
                target_period_ps=833, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
                replicas=1, MACs_per_cycle=0, new_FF_bits=ff,
                new_memory_ports=0, new_memory_bytes_per_cycle=0,
                new_external_boundary_bits_per_cycle=0,
                new_pipeline_edges=0, single_user_token_latency_delta_cycles=0,
                queue_depth_delta=0, accepted_debt_delta=0, reset_root_copies=0,
                arithmetic_NAND2_reservation=arithmetic_nand2,
                TX_state_mux_NAND2_reservation=state_mux_nand2,
                running_mux_NAND2_reservation=running_mux_nand2,
                predicate_NAND2_reservation=predicate_nand2,
                NAND2_equivalent_reservation=nand2, buffer_reservation_cells=buffers,
                gross_cell_reservation_um2=gross,
                additional_implementation_reservation_um2=gross,
                total_cell_growth_budget_um2=2*gross, old_cell_removal_credit_um2=0,
                new_clock_pin_cap_fF_SS=0.433982, new_reset_pin_cap_fF_SS=0.704025,
                new_predicate_D_pin_cap_fF_SS=0.527811,
                additional_state_control_connections_bound=1+3+1+count_bits+1+1,
                completion_control_buffer_leaf_sink_reservation=32,
                actual_parent_launch_clock=None, actual_parent_completion_max_arrival_ps=None,
                actual_parent_completion_min_arrival_ps=None,
                actual_parent_result_data_arrival_ps=None, actual_parent_routed_record=None,
                measured_gain_ps=None, routed_area_fit=False, routing_capacity_proven=False,
                component_exactness=False, SS_FF_closed=False, build_ready=False,
                blocker='Selected native parent completion/data launch-clock and min/max arrival binding absent. No uncontrolled capture edge or IO policy change.',
                semantics='ready_q(t)=running(t)&&TX_IDLE(t)&&!rd_inflight(t)&&(txq_n(t)+2<=TXQ); compute ready_q(t+1) from EXACT original next state including q_push/tx_pop and ordered assignments, clear with rst_q; job_done(t)=core_done(t)&&ready_q(t).')


def qwen_core_decode_pipeline_candidate(aw=24, nw=18, instruction_bits=1024, instructions=1, replicas=1):
    """Held FIFO word -> position -> selectors/shift -> /ODD -> NEXT.

    Upper additive latency: four edges per decoded instruction, including END.
    Preparation overlaps existing unit execution, but no overlap credit is taken.
    This is a clock-repair candidate, not an adopted performance lever.
    """
    state_bits = instruction_bits + 11*aw + 3*nw + 1 + 3
    return dict(default_enabled=False, MACs_per_cycle=0, new_memory_ports=0,
                new_boundary_bits=0, replicas=replicas,
                added_register_bits_per_core=state_bits,
                register_HQN_cell_area_um2=0.2916,
                added_register_cell_area_floor_um2=state_bits*0.2916,
                enable_mux_clock_reset_buffer_area_um2=None, mapped_area_um2=None,
                routing_tracks=None, channel_capacity=None, floorplan_fit=False,
                fifo_word_select_inputs=4, dynamic_selects=11,
                dynamic_select_fanin_baseline=8, dynamic_select_fanin_VPOS=64,
                additional_decode_edges=4, minimum_decode_initiation_interval=5,
                token_latency_delta_upper_cycles=4*instructions,
                token_latency_delta_upper_ns=4*instructions/1.2,
                latency_overlap_credit_cycles=0, clock_hz=1200000000,
                SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
                clock_closed=False, adopted=False,
                source='rtl/hdc/ot_hdc_core_vector_weight.sv',
                area_obligation='All held word, 11 DYN operands, position, shifted position, rounds, invalid and phase flops; map before slot fit',
                physical_obligation='Register /ODD alone still requires SS/FF measurement; no clock relaxation')


def qwen_combined_sequencer_la(*, fw=512, vwa=16, ntok=8, replicas=4):
    """Port of the adopted zero-edge ROM-VP LA controls to combined VP.

    Queues, ports, descriptors, tags, near service and arithmetic unchanged.
    This sizes source additions; routed ROM-VP closure is not combined closure.
    """
    cw = 13
    bits = fw + vwa + ntok + 2*cw + 7 + 32
    return dict(default_enabled=False, added_register_bits_per_die=bits,
                replicas=replicas, total_added_register_bits=replicas*bits,
                register_cell_area_floor_um2_per_die=bits*0.2916,
                area_floor_excludes='enable muxes, prefix logic, key trees, clock/reset/routing',
                MACs_per_cycle=0, extra_memory_ports=0,
                existing_VM_read_bytes_per_edge=fw//8,
                existing_collective_payload_bits_per_edge=fw,
                existing_collective_tag_bits=44, new_boundary_bits=0,
                added_instruction_or_collective_edges=0,
                composed_token_latency_delta_cycles=0,
                queue_depth_unchanged=4, clock_hz=1200000000,
                SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
                combined_context_clock_closed=False, floorplan_fit=False,
                adopted=False,
                source_reuse='rtl/rom/ot_qwen_tp_seq_w12_vp.sv LA=1 at 67b9aa4c1',
                physical_obligation='Original ROM-VP routed SS+4.56ps/FF+14.32ps does not qualify added combined NEAR/tag context')


def qwen_w12_lvl7_clock_cut_model(*, gt=6144, lanes=16, aw=24, nw=18,
                                  tcut=7, smin=7, tg=4, bd=41, nws=5,
                                  tws=38, mem_extra=1, mul_lat=5, acc_lat=5,
                                  tree_lat=3, depth=4, replicas=4):
    """Source-sized PART2 clock-cut input to the joint pre-RTL model.

    No arbitration, landing implementation, slot or schedule is assumed free.
    Defaults bind lp_build's retained geometry; the selected generated core's
    top.args must still match before authoring the wrapper. Existing e_v is
    active on EVERY source edge, including non-last iterations.
    """
    if depth != 4 or tcut != 7 or smin != 7:
        raise ValueError("This source carveout binds lvl7 / DEPTH4 only")
    if gt % (1 << tcut) or tg & (tg-1):
        raise ValueError("Integral groups and power-of-two tile groups required")
    groups = gt >> tcut
    tag = 5 + 4 + 4*aw + 3*(nw+1) + 1 + 3 + 1
    data = groups*lanes*32
    beat = data + tag + 2  # valid and fault; split is already inside e_tag
    xd = bd + (tcut - (tg.bit_length()-1))*nws + tws + mem_extra
    flight = mem_extra + 4 + mul_lat + acc_lat + (tree_lat+1)*tcut + xd
    aw_fifo = 2
    # wp/rp + peer samples, state + peer samples, HOLD2 counters + seen-down
    fifo_control = 4*(aw_fifo+1) + 8 + 4 + 2
    fifo_storage = 2*depth*beat
    return dict(
        status="PRE_RTL_SOURCE_INPUT_NOT_COMPOSED_ADMISSION", default_enabled=False,
        selected_cut="PART2 g_tin/lvl[7]", data_bits=data, canonical_tag_bits=tag,
        valid_bits=1, fault_bits=1, held_beat_bits=beat,
        groups_at_cut=groups, replicas=replicas, MACs_added_per_cycle=0,
        new_external_memory_ports=0, upper_tree_levels=list(range(tcut+1, (gt-1).bit_length()+1)),
        original_rounding_and_adjacent_pair_order_preserved=True,
        clock=dict(source_hz=1200000000, destination_hz=900000000,
                   VCO_hz=3600000000, related=True, false_paths_allowed=False,
                   setup_uncertainty_ps=60, hold_uncertainty_ps=25),
        boundary=dict(source_bits_per_active_cycle=beat, source_bytes_per_active_cycle=beat/8,
                      consumer_bits_per_accept_cycle=beat, consumer_bytes_per_accept_cycle=beat/8,
                      maximum_service_entries_per_second=900000000,
                      sustained_source_exceeds_service=True),
        crossing=dict(source="rtl/common/ot_ratio_cdc_fifo.sv", depth=depth, hold=2,
                      payload_and_shadow_ff=fifo_storage, control_ff=fifo_control,
                      total_ff=fifo_storage+fifo_control,
                      fifo_data_mux_fanin=depth, fifo_data_mux_output_bits=beat,
                      shadow_storage_entries=depth, shadow_copies_per_stored_bit=1,
                      crossing_data_tracks_per_entry=beat,
                      protected_route_channel_capacity_tracks=None,
                      forward_no_backpressure_ns=[5/3.6, 8/3.6],
                      reverse_no_backpressure_ns=[4/3.6, 6/3.6],
                      pipeline_backpressure_bound_ns=None),
        issue=dict(existing_release="e_v <= active every fast edge",
                   tile_issue="independent PART1 loops after delayed tgo",
                   xd_logical_fast_edges=xd, issue_to_cut_logical_fast_edges=flight,
                   reservation_required_before_irrevocable_issue=True,
                   depth4_alone_covers_flight=False,
                   full_rate_minimum_flight_reservations=flight,
                   additional_return_credit_and_edge_guard_reservations=None,
                   full_rate_flight_payload_bits_lower_bound=flight*beat,
                   full_rate_flight_storage_ff_delta=None,
                   selected_common_advance_requires_all_tiles_and_IL8_feedback_phase=True,
                   full_flight_alternate_selected=False,
                   ungated_service_capture_partition_required=True,
                   existing_tile_me_or_kv_active_enable_safe=False,
                   reservation_state_bits=None, accepted_tag_alignment_ff_delta=None),
        reset=dict(peer_down_wait_existing=True, producer_pipeline_quiescence_required=True,
                   discard_old_inflight_payload_and_tag_together=True,
                   accepted_write_debt_must_drain_before_new_epoch=True,
                   extra_quarantine_edges=None, extra_state_ff=None),
        area=dict(fifo_register_cell_floor_um2=(fifo_storage+fifo_control)*0.2916,
                  register_area_basis="DFFHQN 0.2916um2 proxy; not physical fit",
                  fifo_mux_clock_reset_wire_area_um2=None,
                  reservation_and_flight_landing_area_um2=None,
                  per_die_slot_um2=None, floorplan_fit=False),
        token=dict(selected_program_schedule=None, upper_tree_serial_edges_per_beat=(tree_lat+1)*((gt-1).bit_length()-tcut),
                   crossing_entries=None, credit_stall_ns=None, final_write_ack_ns=None,
                   composed_latency_delta_ns=None, headline_rate_credit=False),
        implementation_dependencies=["selected top.args verified; retain source-bound flight148",
                                     "Maxwell complete landing/credit/alignment/reset/mux/wire and literal schedule price",
                                     "owner-selected COMMON logical advance across PART1 tiles and PART2 tags",
                                     "actual serial result/scale grants and consumed write ACK",
                                     "source-sized slot and related-clock loaded SS/FF gate"],
        wrapper_rtl_admitted=False, physical_launch_admitted=False)


def qwen_combined_native_mp_commit(*, sw=64, aw=24, fill_lat=8, replicas=4,
                                   service_period_fs=833333, ack_tail_edges=0):
    """Additional alignment around the existing canonical MP commit element.

    A raw lane sampled E0 is decoded after E1 and enters service at E2.
    Compose the final lane's actual ACK tail with pipeline empty, never sum
    two edges onto every FILL stage or assume they are unhidden token delay.
    Canonical decoder/state area belongs to the existing element model.
    """
    bits=2*sw*aw+2
    old_empty=fill_lat+3
    new_empty=fill_lat+5
    before=max(old_empty,ack_tail_edges)
    after=max(new_empty,ack_tail_edges)
    return dict(default_enabled=False, replicas=replicas, MACs_per_cycle=0,
                added_register_bits_per_die=bits, total_added_register_bits=replicas*bits,
                register_cell_area_floor_um2_per_die=bits*0.2916,
                area_floor_excludes='canonical decoder/state, enable muxes, clock/reset/routing',
                initiation_interval_service_edges=1, added_lane_service_edges=2,
                existing_lane_address_bits_per_edge=sw*aw,
                existing_lane_data_bits_per_edge=sw*32,
                added_memory_ports=0, new_boundary_bits=0, routing_tracks_added=0,
                existing_lane_input_bytes_per_edge=sw*4,
                empty_pipeline_tail_service_edges=new_empty,
                actual_ack_tail_service_edges=ack_tail_edges,
                composed_tail_service_edges=after,
                composed_tail_delta_service_edges=after-before,
                composed_tail_delta_fs=(after-before)*service_period_fs,
                token_composition='per-layer max(actual native ACK tail, FILL_LAT+5); serialize only exposed fence tail',
                service_period_fs=service_period_fs,
                combined_context_clock_closed=False, floorplan_fit=False, adopted=False,
                source='rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_commit_service.sv')


def hbm_loader_install_contract(*, partitions=2, dies=2, queue_depth=4,
                                reorder_entries=16, cdc_aw=5, host_period_ns=1.0,
                                service_period_ns=0.833, existing_clients=4, partition_ports=1):
    """Item8(c) boot/restore/STORE boundaries, before successor RTL/build.

    The adapter distributes an ordered engine request stream to one finite
    client queue per 128-byte-interleaved partition. It does not invent an
    NS-fold increase in host bandwidth. STORE waits real AXI B completions.
    Clock periods are targets, not measured closures; no decode gain claimed.
    """
    assert partitions >= 1 and partitions & (partitions-1) == 0
    assert queue_depth >= 2 and queue_depth & (queue_depth-1) == 0
    assert cdc_aw >= 2
    request_bits=1+32+256+32+16
    response_bits=1+256+16
    queue_bits=partitions*queue_depth*request_bits
    reorder_bits=reorder_entries*(256+16+2)
    cdc_payload_bits=(1<<cdc_aw)*256+4*64+4*68
    return dict(default_enabled=False, MACs_per_cycle=0,
                dies=dies, partitions_per_die=partitions,
                additional_memory_clients_per_die=partition_ports,
                memory_clients_before=existing_clients,
                memory_clients_selected=existing_clients+partition_ports,
                request_bits_per_partition_boundary=request_bits,
                response_bits_per_partition_boundary=response_bits,
                peak_memory_payload_bytes_per_edge=32*partitions,
                ordered_engine_bytes_per_edge=32,
                host_payload_bits_per_edge=64, engine_payload_bits_per_edge=256,
                host_AXI_address_bits=64, host_AXI_response_bits=2,
                host_target_period_ns=host_period_ns,
                service_target_period_ns=service_period_ns,
                host_width_ceiling_GBps=8/host_period_ns, engine_width_ceiling_GBps=32/host_period_ns,
                installed_DMA_serialization="4 actual 64-bit beats per sector; read owner held through RLAST, write owner through B; actual PCIe/AXI response tail must be measured",
                PCIe5_x16_encoded_ceiling_GBps=32*16*(128/130)/8,
                PCIe_payload_after_packet_overhead_GBps=None,
                raw_partition_request_queue_bits_per_die=queue_bits if partition_ports>1 else 0,
                unselected_partition_recipe_queue_bits_per_die=queue_bits,
                raw_STORE_reorder_bits_per_die=reorder_bits,
                raw_STORE_CDC_payload_bits_per_die=cdc_payload_bits,
                queue_registered_edges=1 if partition_ports>1 else 0, added_CRC_edges=0,
                reorder_retirement_edges=1,
                CDC_latency='actual ot_gpu_cdc_fifo two synchronizer edges plus pointer/consumer edges in each direction; measure under both clocks',
                LOAD_completion='all engine write ACKs, optional ordered readback CRC, then actual completion CDC',
                STORE_completion='all matched MREQ reads, ordered CDC/W handshakes, all AXI B responses, matching payload/memory CRC',
                latency_formula='LOAD+STORE measured elapsed host edges*host_period; include finite queue, CDC, memory/refresh, AXI backpressure and B tail',
                steady_decode_added_cycles=0,
                steady_decode_clock_or_arbitration_delta='UNKNOWN until selected-context check',
                mux_demux_cost='installed: one loader client/die at NCL, ND+host AXI arbiter + BAR decoder; optional recipe partition queues are separate until selected',
                routing_tracks_required='UNKNOWN: boundary bit inventory above; floorplan/channel capacities needed',
                area_um2='UNKNOWN: queues/reorder/CDC plus control and muxes require actual synthesis',
                replica_cost='per die; no ROM/ECC changes', floorplan_fit=None,
                clock_closed=False, SS_setup_uncertainty_ps=60,
                FF_hold_uncertainty_ps=25, composed_decode_gain_percent=None,
                adopted=False,
                historical_single_client_GBps={'write_only':9.788,'with_readback':4.998},
                historical_record='results/rtl/tapeout_hbm_loader_20261004/record.json')


def hbm_stream_aq_current_hold_cut(*, queue_depth=4, pcs=128):
    """Exact current-queue bank mask cut for the retained AQ row controller.

    Register the OR of surviving slots plus an accepted push. This equals the
    current queue's bank set at every edge; the existing prior-cycle hold stays
    in PRE exclusion. No eligibility or row/column issue edge moves.
    """
    if queue_depth < 2 or queue_depth & (queue_depth-1) or pcs < 1:
        raise ValueError('retained AQ queue needs power-of-two depth >=2 and real PC count')
    bits = 32
    return dict(default_enabled=False, MACs_per_cycle=0, pcs=pcs,
                existing_queue_depth=queue_depth, added_state_bits_per_pc=bits,
                total_added_state_bits=pcs*bits,
                register_cell_area_floor_um2_per_pc=bits*0.2916,
                register_cell_area_floor_um2_total=pcs*bits*0.2916,
                area_floor_excludes='queue-survivor OR, push decode, enable mux, clock/reset/wires',
                mask_fanin_per_bank=queue_depth+1, late_pop_mux_bits=32,
                extra_memory_ports=0, extra_memory_bytes_per_cycle=0,
                boundary_bits_added=0, external_routing_tracks_added=0,
                local_registered_mask_bits=32, local_placement_fit='pending selected service route',
                added_row_command_cycles=0, added_column_command_cycles=0,
                composed_single_user_token_delta_cycles=0,
                composed_single_user_token_delta_ns=0,
                period_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                refresh_and_DRAM_eligibility='unchanged exact current and prior queue hold masks',
                interface_and_tags='unchanged accepted push/pop; no payload/visibility or grant changes',
                SSFF_closed=False, adopted=False,
                source_basis='svc/closure_handoff_20261004/source_snapshots/49fa1b0886e4_ot_hbm_r14_stream_pc.sv')


def hbm_loader_crc_literal_matrix_price(*, state_masks, word_masks, dies=2):
    """Source-bound recipe only; keep the installed loop until final route selects.

    Four existing folds/die: LOAD host/readback and STORE host/readback.
    Literal masks implement the same LSB-first CRC32 over one 256-bit sector.
    XOR inventory is an unshared structural ESTIMATE, not mapped area/timing.
    """
    import math
    if len(state_masks)!=32 or len(word_masks)!=32 or dies<1:
        raise ValueError('32 exact CRC masks and positive die count required')
    sp=[m.bit_count() for m in state_masks]
    wp=[m.bit_count() for m in word_masks]
    depth=max(max(math.ceil(math.log2(max(1,a))),
                  math.ceil(math.log2(max(1,b))))+1 for a,b in zip(sp,wp))
    xors=sum(max(0,a-1)+max(0,b-1)+1 for a,b in zip(sp,wp))
    sf=max(sum((m>>j)&1 for m in state_masks) for j in range(32))
    wf=max(sum((m>>j)&1 for m in word_masks) for j in range(256))
    return dict(recipe_selected=False, adopted=False, default_enabled=False,
                MACs_per_cycle=0, dies=dies, folds_per_die=4,
                host_folds_per_die=2, memory_folds_per_die=2,
                existing_CRC_state_bits_per_die=128, added_state_bits=0,
                sector_bytes_per_fold=32, initiation_interval_edges=1,
                added_fold_edges=0, added_memory_ports=0,
                added_bytes_per_memory_edge=0, new_boundary_bits=0,
                local_word_bits=256, local_state_bits=32,
                literal_constant_bits_per_fold=32*(256+32),
                literal_constants_are_storage=False,
                unshared_XOR2_equivalents_per_fold_ESTIMATE=xors,
                unshared_XOR2_equivalents_all_folds_ESTIMATE=xors*4*dies,
                maximum_balanced_parity_tree_levels_ESTIMATE=depth,
                maximum_state_bit_output_fanout=sf,
                maximum_word_bit_output_fanout=wf,
                mux_demux_delta='no new port mux; CRC function substitution only',
                acceptance_edge_and_CRC_order='unchanged real LOAD beat/readback retirement and STORE W/data retirement',
                composed_latency_delta_cycles=0,
                host_target_period_ns=1.0, memory_target_period_ns=0.833,
                setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                area_um2=None, area_status='UNKNOWN until synthesis; unshared XOR count is not area',
                routing_tracks=None, routing_status='UNKNOWN local CRC fanout/wire cost; no new external boundary',
                floorplan_fit=None, routed_SS_FF=None,
                composed_gain_percent=None,
                select_only_if='current installed route final critical path implicates CRC; never infer selection from preliminary floorplan repair')


def hbm_loader_crc_matrix_geometry_bound(price, *, xor2_max_area_um2,
        retained_vehicle_cell_area_um2, vehicle_core_area_um2,
        reserved_slot_area_um2=None, corridor_capacity_tracks=None,
        maximum_slot_cell_utilization=0.55):
    """Conservative pre-build cell/cross-cut requirement, never assume a slot.

    Add all matrix cells without credit for removing the installed loop.
    Clock/repair area is unknown. Twice each XOR plus CRC output sinks bounds
    the edges across ANY cut; conservative, not an expected wire demand.
    Actual consumer region assignment/available tracks are required to select.
    """
    folds=price['folds_per_die']
    cells=price['unshared_XOR2_equivalents_per_fold_ESTIMATE']
    added=cells*folds*xor2_max_area_um2
    area=retained_vehicle_cell_area_um2+added
    tracks=folds*(2*cells+32)
    slot_capacity=None if reserved_slot_area_um2 is None else reserved_slot_area_um2*maximum_slot_cell_utilization
    slot_ok=slot_capacity is not None and area<=slot_capacity
    corridor_ok=corridor_capacity_tracks is not None and tracks<=corridor_capacity_tracks
    return dict(added_matrix_cell_area_no_removal_credit_um2_ESTIMATE=added,
                retained_plus_matrix_cell_area_um2_ESTIMATE=area,
                repair_clock_buffer_area_um2=None,
                vehicle_core_area_um2=vehicle_core_area_um2,
                cell_utilization_before_additional_repair_ESTIMATE=area/vehicle_core_area_um2,
                vehicle_is_actual_top_slot=False,
                reserved_actual_top_slot_area_um2=reserved_slot_area_um2,
                maximum_slot_cell_utilization=maximum_slot_cell_utilization,
                required_slot_area_before_additional_repair_um2_ESTIMATE=area/maximum_slot_cell_utilization,
                available_slot_cell_area_um2=slot_capacity,
                additional_repair_cell_budget_um2=None if slot_capacity is None else slot_capacity-area,
                all_cut_edge_upper_bound_tracks=tracks,
                bound_basis='two input sinks per unshared XOR2 plus32 CRC outputs per fold; all four cones could span cut without region map',
                actual_corridor_capacity_tracks=corridor_capacity_tracks,
                slot_cell_bound_pass=slot_ok, corridor_bound_pass=corridor_ok,
                build_gate_pass=slot_ok and corridor_ok,
                routed_area_fit=False, adopted=False,
                unresolved='actual top reserved slot and CRC locality/corridor map; additional clock/buffer repair cannot be priced as zero')


def hbm_loader_high_address_price(*, byte_address_bits=37, stack_bits=2,
        service_sector_bits=34, stack_bytes=22500000000, dies=1):
    """Current per-die ND1 host hierarchy, explicit stack/local byte address.

    ADDR={stack,local_byte}; 32GiB encoded stride is not free storage: per-stack
    capacity is checked. CSR DADDR_HI exposes every high bit; NBYTES remains32
    so software explicitly chunks large transfers, never relies on an aperture.
    """
    local=byte_address_bits-stack_bits
    if not 32<=byte_address_bits<=64 or not 0<=stack_bits<=2 or local<5 or service_sector_bits<local-5:
        raise ValueError('address translation must be lossless')
    if stack_bytes>(1<<local):raise ValueError('stack capacity exceeds local address')
    delta=byte_address_bits-32
    return dict(default_enabled=False, selected=False, adopted=False,
                per_die_host_instances=1, engine_pairs_per_die=1, dies=dies,
                byte_address_bits=byte_address_bits, stack_bits=stack_bits,
                local_byte_bits=local, stack_capacity_bytes=stack_bytes,
                encoded_stack_stride_bytes=1<<local,
                flat_encoded_space_bytes=1<<byte_address_bits,
                translation='stack=ADDR[36:35], sector=zero_extend(ADDR[34:5]); literal bit wiring for37/2/34',
                address_holes='local offsets >=stack_bytes rejected; descriptor cannot cross a stack',
                CSR_high_offset=0x2c, CSR_high_bits=delta,
                reserved_high_CSR_bits='rejected before any DMA/MREQ, never silently discarded',
                DMA_host_address_bits=64, DMA_host_address_cost_delta_bits=0,
                DMA_translation='host address remains independent full64; width converter does not translate HBM addresses',
                tag_bits=16, tag_cost_delta_bits=0,
                tag_identity='retained LOAD/STORE classbit15, exact STORE lower15 tag/ROB matching',
                raw_added_descriptor_and_memory_base_bits_per_die=4*delta,
                raw_added_command_CDC_payload_bits_per_die=2*4*delta,
                added_address_storage_bits_per_die=12*delta+3,
                added_service_formatter_fault_flag_bits_per_die=1,
                added_reserved_HI_validity_flag_bits_per_die=2,
                request_internal_packet_bits=1+byte_address_bits+256+32+16,
                request_service_packet_bits=1+service_sector_bits+2+256+32+16,
                service_boundary_delta_bits_vs_byte32=service_sector_bits+2-32,
                response_packet_bits=1+16+256,
                ingress_DMA_payload_bits=64, engine_payload_bits=256,
                memory_bytes_per_accepted_edge=32, added_memory_ports=0,
                MACs_per_cycle=0, added_latency_cycles=0,
                initiation_interval='unchanged accepted request/ACK and W/B flow; no new engine',
                protection_cost='two widened byte-end and local-end comparisons; capacity/stack-cross, HI reserved-bit, alignment and full64 host-wrap guards; no parity/ECC substitution',
                mux_and_fanout_cost='widen descriptor/base/address mux+adder5bits perengine; reuse ND1 arbitration, response tags and heldowner',
                mapping_combinational_cost='wire slices/zero-extension only; no divide/remap/page engine',
                area_um2=None, area_status='ESTIMATE63 extra stored bits at37 plus widened arithmetic/guards/mux/CDC; mapped cost unknown',
                FF_area_floor_um2_ESTIMATE=(12*delta+3)*0.2916,
                corridor_capacity=None, slot_fit=False,
                clock_targets={'host_ns':1.0,'mem_ns':0.833},
                SS_setup_ps=60, FF_hold_ps=25, clock_closed=False,
                composed_decode_gain_percent=None,
                binding_required='Sagan confirms stack-high/local-byte mapping +service stack/sector ports; Kant actualservice.loader slot/corridor, priorCRCroute does not qualify widened source')


def dsrom_s81_native_port_hc_pair():
    """MODEL ONLY: retain first HC-pre mix intermediate beside the EXISTING SU lanes.

    Source: dshbm_baseline_measure.lower_hc_pre_norm, first two ops, both
    nout=1/nin=5120. The third op is segmented (8x640) and remains a VM
    boundary. No new arithmetic, numerical reordering, or global port widening.
    This is a conservative, matched native-port calendar, not replacement
    measurement or an incremental credit against the existing fused DAG.
    """
    n, lanes, word_bits, face_bits = 5120, 1024, 32, 1024
    hz, mlat, alat = 0.9e9, 5, 4
    beats = n * word_bits // face_bits
    # A face is counted as an aggregate bidirectional budget, conservatively.
    # A separate ready or instruction grant is never substituted for data.
    baseline_beats = [3 * beats, 3 * beats]
    candidate_beats = [2 * beats, 2 * beats]
    transport = FUSION_C_ROTATE_PLUS
    tail = 6 + 4 * mlat + alat  # existing vec.sv linear depth = 30
    # Preserve all fixed baseline stages, even for the retained local hop.
    # Added local bank-select/output register: one stage, charged once per op.
    fixed = SU_OP_ACCEPT + transport['bcast'] + transport['read'] + tail + transport['write']
    extra_local = 2
    baseline_cycles = sum(baseline_beats) + 2 * fixed
    candidate_cycles = sum(candidate_beats) + 2 * fixed + extra_local
    t_bits = n * word_bits
    # Local T: 1024 independent lane banks, five words each. Same lane and
    # address traversal in ops 0/1. Do not extend this binding to op2's RED tree.
    input_pack_bits = 4 * lanes * word_bits  # two ping-pong packets, two operands each
    output_pack_bits = lanes * word_bits
    # Four coefficient words; capture masks for two input packs/output pack;
    # five retained vector validity bits; sixteen phase/index/ownership bits.
    metadata_bits = 4 * word_bits + 5 * 32 + 5 + 16
    added_ff = t_bits + input_pack_bits + output_pack_bits + metadata_bits
    # Gross replacement allowance: no credit for any old mapped logic/staging.
    # W5 DFF area; NAND2 footprint from installed ASAP7 TT lib, footprint only.
    nand2_um2 = 0.08748
    mux2_um2 = 4 * nand2_um2
    local_read_mux2 = lanes * word_bits * (5 - 1)
    hold_mux2 = added_ff
    decode_nand2_allowance = 512
    ff_um2 = added_ff * DFF_UM2
    mux_um2 = (local_read_mux2 + hold_mux2) * mux2_um2
    decode_um2 = decode_nand2_allowance * nand2_um2
    cell_um2 = ff_um2 + mux_um2 + decode_um2
    slot_um2 = cell_um2 / 0.5  # explicit FF50/logic50 gross reservation
    saved_cycles = baseline_cycles - candidate_cycles
    return dict(
        schema='opentallas.dsrom.s81.native-port-hc-pair.v1',
        status='INTERFACE_FEASIBLE_MODEL_ONLY', adopted=False, rtl_authorized=False,
        scope='L20.attn.hc_pre ops0/1; one die, one invocation',
        graph_hook='L20.attn.hc_pre', composition_owner='Maxwell',
        exactness=dict(
            source='tools/dshbm_baseline_measure.py:lower_hc_pre_norm',
            op0='T1 = FP32_add(FP32_mul(H0,P0), FP32_mul(H1,P1))',
            op1='T2 = FP32_add(FP32_mul(H2,P2), T1)',
            round_points='Keep each separate FP32 mul/add; no FMA/BF16 conversion of T1/T2.',
            binding='Both ops1x5120, same lane/address traversal; T1 remains in that lane.',
            preserved_boundary='T2 writes VM. Third mix changes to8x640 and performs original BF16+RED_SUM/REDSQ/REDTREE; unchanged.',
            reduction_order_change=False, reduction_cycles_removed=0,
            coefficient_broadcast_change=False, coefficient_max_fanout=1024,
            class_='A intended; unvalidated'),
        resource=dict(
            reused='ot_hdc_v41x_vec/vec_lane M1/QM/AD; MLAT5/ALAT4 at0.9GHz',
            arithmetic_replicas_added=0, existing_lanes=lanes,
            sfu_replicas_added=0, new_sfu_calls=0,
            scalar_muls=3*n, scalar_adds=2*n, fused_fma=0,
            peak_lane_muls_per_cycle=2*lanes, peak_lane_adds_per_cycle=lanes,
            mean_scalar_fp_ops_per_candidate_cycle=5*n/candidate_cycles,
            fp_ops_per_global_byte_baseline=5*n/(6*n*4+16),
            fp_ops_per_global_byte_candidate=5*n/(4*n*4+16)),
        ports=dict(
            chosen_slot='Existing su_s/su_n lane owners; distribute retained words with their existing lane, without new inter-slab data path.',
            other_slot='Both existing1024bit VM faces retained; aggregate calendar uses1024bits, not summed2048bit bandwidth.',
            physical_lane_to_half_map_verified=False,
            domain_hz=hz, vm_face_bits=face_bits,
            vm_face_bytes_per_cycle=face_bits//8, aggregate_directions=True,
            payload_bandwidth_GBps=face_bits/8*hz/1e9,
            coefficient_read_bytes=16, coefficient_read_beats=1,
            coefficient_load_overlapped=False,
            global_signal_wires=face_bits, new_global_port_bits=0,
            face_layer='M5', existing_face_length_um=500,
            peak_staged_local_read_bits=lanes*word_bits,
            peak_staged_local_write_bits=lanes*word_bits,
            local_bus_note='32768 bits distributed as32 bits/lane; no32768bit VM corridor. T banks may retain T2 after matching T1 capture until ordered VM drain/ACK.',
            staging='32-lane groups filled one per VM beat; two ping-pong packets each with two operand capture masks; full1024-lane packet admitted only when complete. Hold the active pack through capture.',
            local_bank='1024 lane banks x5 FP32 words, one read and one write per bank; original packet sequence retained.',
            local_select='5:1 per bit; same-lane T1 read for op1, one priced select/capture stage.',
            prefetch_credit_required=True, finite_buffer_words=(t_bits+input_pack_bits+output_pack_bits)//32,
            new_cross_die_bits=0, new_cdc=False,
            new_global_routing_tracks=0, local_routing_track_capacity=None,
            local_read_selector_levels=3,
            coefficient_broadcast='Existing6-stage control/scalar distribution retained; no free broadcast or new cross-lane forwarding.'),
        calendar=dict(
            basis='Non-overlapped analytical face-serialization envelope; not RTL cycles.',
            face_only_baseline_beats=baseline_beats,
            face_only_candidate_beats=candidate_beats,
            op0='Baseline readsH0/H1,writesT1; candidate readsH0/H1 and retainsT1.',
            op1='Baseline readsH2/T1,writesT2; candidate readsH2 plus laneT1 and writesT2.',
            common_coefficient_load_cycles=1,
            acceptance_per_op=SU_OP_ACCEPT, broadcast_per_op=transport['bcast'],
            fetch_fixed_per_op=transport['read'], linear_tail_per_op=tail,
            return_fixed_per_op=transport['write'], fixed_per_op=fixed,
            added_local_bank_cycles=extra_local,
            baseline_cycles=baseline_cycles+1, candidate_cycles=candidate_cycles+1,
            baseline_us=(baseline_cycles+1)/hz*1e6,
            candidate_us=(candidate_cycles+1)/hz*1e6,
            same_port_model_saving_cycles=saved_cycles,
            same_port_model_saving_us=saved_cycles/hz*1e6,
            reduction_and_rsqrt='Outside pair; retained at original cost, no zero-filled full-norm price.',
            extra_global_transport_credit=0,
            removed_vm_bytes=2*n*4,
            source_program_issue_geometry_change=False,
            current_fused_DAG_incremental_gain_us=None,
            measured_675cycle_HC_chain_is_matched_native_baseline=False,
            token_gain_pct=None,
            composition_rule='Owner must use same1024bit native baseline AND candidate calendar; do not subtract from an already-fused edge or extrapolate all layers.'),
        storage=dict(
            intermediate_bits=t_bits, input_pack_bits=input_pack_bits,
            output_pack_bits=output_pack_bits, metadata_and_coeff_bits=metadata_bits,
            new_ff_bits=added_ff, new_clock_sinks=added_ff,
            retained_existing_arithmetic_clock_sinks=True,
            sram_macros_added=0, local_read_mux2=local_read_mux2,
            hold_mux2=hold_mux2, decode_nand2_allowance=decode_nand2_allowance,
            validity='Actual complete capture, same command owner, phase/lane/packet index; retain T1 until matching op1 read; outputs publish only after finite VM ACK.',
            protection='FF staging only; retain existing control/identity protection. Any SRAM substitution must separately include SRAM protection.'),
        area=dict(
            basis='Gross source-counted estimate; no subtraction from existing12.80594mm2 SU reservation.',
            dff_um2=DFF_UM2, nand2_footprint_um2=nand2_um2,
            nand2_basis='ASAP7 TT NAND2x1 footprint only, not SS timing',
            ff_um2=ff_um2, mux_um2=mux_um2, decode_um2=decode_um2,
            gross_cell_um2=cell_um2, utilization=0.5,
            additional_slot_reservation_mm2=slot_um2/1e6,
            existing_two_slab_SU_mm2=12.80594,
            two_slab_SU_with_known_reservation_mm2=12.80594+slot_um2/1e6,
            clock_reset_buffer_PDN_protection_area_um2=None,
            routing_channel_area_um2=None, mapped_area_um2=None,
            actual_spare_su_s_area_mm2=None, floorplan_fit=None,
            existing_slab_width_um=1015.2,
            added_subslot_height_um_total=math.ceil(slot_um2/1015.2/2.16)*2.16,
            illustrative_equal_half_height_um=math.ceil(slot_um2/2/1015.2/2.16)*2.16,
            half_allocation='Equalhalf dimensions are reservation illustration, not actual existing lane placement or spare-slot fit.',
            retained_spine_escape_gap_um=172.8,
            slot_rule='Owner assigns added gross area to existing lane-owner slabs; no existing spare-space assumption, new inter-slab bus or baseline deletion.'),
        adoption_gate=dict(
            at_least_one_percent_composed_gain=False,
            native_vm_arbitration_calendar_measured=False,
            local_storage_slot_and_tracks_qualified=False,
            exact_component_measured=False, SS_FF_closed=False,
            headline_unchanged=True,
            next_owner_action='Maxwell map native-port calendar onto real critical-chain exposure; Einstein review same-lane bank/packet binding; no RTL/build authorized by this model.'))


def qwen_me_bypass_capture_price(*, gt=6144, smin=6, tcut=6, tree_lat=7):
    """Default-off A1 bypass redistribution; source-counted, no timing claim.

    Same binary32 rounding/tree/cut order. Only the first capture's bypass
    payload changes from32 bits to two zero flags. Receiving-stage logic and
    load must close in the same selected tree; saved FF are not area credit.
    """
    if (gt, smin, tcut, tree_lat) != (6144, 6, 6, 7):
        raise ValueError('Only the frozen t3 source context is enrolled')
    lg = (gt - 1).bit_length()
    counts = [gt >> lv for lv in range(tcut + 1, lg)]
    n = sum(counts)
    nand2 = .08748  # installed ASAP7 footprint proxy, not SS delay
    and2_or2 = 2 * nand2
    mux2 = 4 * nand2
    shifted = 64 * and2_or2 + 32 * and2_or2 + 16 * mux2
    predicates = 5 * and2_or2
    # Gross local allowance: one BUF equivalent per selector destination (64 masks +16 exponent muxes).
    buffer_allowance = 80 * nand2
    gross = shifted + predicates + buffer_allowance
    return dict(
        schema='opentallas.qme.bypass-capture.v1', default_enabled=False,
        source='ot_hdc_fp32_add_lat A1 bypass_code -> existing u_ca -> A2 s1_code',
        source_context=dict(gt=gt,smin=smin,tcut=tcut,tree_lat=tree_lat,
                            tinreg=1,adders_per_level=counts,adders=n),
        arithmetic=dict(rounding_changed=False,reduction_order_changed=False,
                        macs_per_cycle=0,fp32_adds_per_adder_cycle=1),
        stages=dict(first_capture_before_bits=120,first_capture_after_bits=90,
                    unchanged_second_and_later_capture_bits=True,
                    latency_edges_planned=7,II_edges_planned=1,
                    added_token_edges_planned=0,latency_II_verified=False,
                    receiving_stage='Existing A2 alignment and s1 capture; no extra cut',
                    SS_setup_ps=60,FF_hold_ps=25,period_ps=833,
                    setup_hold_qualified=False),
        storage=dict(delta_raw_reset_ff_per_adder=-30,delta_tree_raw_ff=-30*n,
                     saved_FF_area_credit_um2=0,mutable_protection_changed=False),
        logic=dict(shifted_and2=64,shifted_or2=32,exponent_mux2=16,
                   predicate_gate_allowance=5,selector_buffer_allowance=80,
                   removed_first_stage_nested_mux2_upper_bound=96,
                   removed_mux_area_credit_um2=0,
                   selector_fanout_per_take=32,exponent_selector_fanout=8,
                   mantissa_exponent_additional_load=True),
        ports=dict(operand_bits=64,result_bits=32,error_bits=2,valid_bits=1,
                   memory_bytes_per_cycle=0,external_boundary_delta_bits=0,
                   first_internal_boundary_delta_bits_per_edge=-30,
                   CDC_added=0,routing_tracks_added_external=0,
                   local_tracks_and_capacitance_qualified=False),
        area=dict(basis='Gross NAND footprint allowances; no removed FF/mux credit',
                  nand2_um2=nand2,DFF_proxy_um2=DFF_UM2,
                  added_logic_gross_per_adder_um2=gross,
                  added_logic_tree_um2=gross*n,
                  additional_tree_reservation_um2=gross*n/.5,
                  utilization=.5,measured_predecessor_cell_um2=121989.113,
                  contextual_area_slot_fit=None,net_mapped_delta_um2=None),
        adoption=False,
        next_gate='Minimum same-adder old/off/on arithmetic and edge gate, then ONE frozen tree context SS/FF route; never timeout-only rerun')


def qwen_me_port_route_context(*, utilization=25):
    """Unchanged full TP2 port, prospective placement variant; NOT a new cut.

    Current t4 source-path is e_f[60] (ots bit3) through the 16-row CSA and
    final24-bit sum into a_qots[23]. The early tag->E->A boundaries and all
    result/argmax edges remain unchanged. Loaded SS/FF failures are retained.
    This prices a placement-only trial, never assumes that utilization fixes
    that cone. A future registered partial-sum repair needs its own model.
    """
    if utilization not in (25, 30, 35):
        raise ValueError('Only the owner supplied three placement utilizations')
    w, pq, aw, nw, gt, smin = 16, 4, 24, 18, 6144, 6
    lanes, groups = w*pq, gt >> smin
    replicas = groups // pq
    tag = 8 + 2*aw + 3*(nw+1)
    in_bits = 16 + lanes*32 + 1 + tag + lanes*16
    out_bits = pq + pq*aw + lanes + lanes*32 + (1+32+nw) + 1
    cells = 56431.7  # Actual t4 final routed port standard-cell footprint.
    # 15% additional implementation reserve, not measured buffer/clock savings.
    reserved = cells*1.15
    return dict(schema='opentallas.qme.port-route-context.v1',
        source='ot_qwen_me_spport_w12; unchanged v3 kept prefix/ring source',
        params=dict(W=w,IL=8,AW=aw,NW=nw,GT=gt,SMIN=smin,PQ=pq,TREE_LAT=7,SCALE_LAT=6),
        replicas=replicas, result_groups=groups, postscale_muls_per_port_edge=lanes,
        MACs_per_cycle=0, raw_result_bytes_per_port_edge=lanes*4,
        scale_bytes_per_port_edge=lanes*2, output_bytes_per_port_edge=lanes*4,
        added_memory_ports=0, added_external_boundary_bits=0,
        boundary=dict(input_bits_per_edge=in_bits,output_bits_per_edge=out_bits,
                      parent_registered=True,pt_id='static port-instance index in enclosing g_pt; never dynamic owner allocation'),
        address_cone=dict(ots_bits=aw,qrows=16,port_offset_sums=pq,
                          unbuffered_ots_bit_destination_upper_bound=16*pq,
                          registered_partials=False,
                          measured_SS_ps=-262.587738,measured_FF_ps=-.387551),
        ports_and_tracks=dict(top_signal_pins=in_bits+out_bits+2,
                              external_track_demand_upper_bound=in_bits+out_bits,
                              channel_capacity_and_loaded_cut_fit=None,
                              new_mux_demux_or_fanout=0),
        area=dict(actual_t4_cell_um2=cells,actual_t4_core_um2=146210,
                  gross_cell_reservation_um2=reserved,
                  planned_utilization_percent=utilization,
                  minimum_core_for_reserved_cells_um2=reserved/(utilization/100),
                  all24_port_cell_reservation_um2=replicas*reserved,
                  parent_slot_fit=None,additional_15_percent_is_reserve=True),
        latency=dict(added_edges=0,changed_II=0,changed_token_edges=0,
                     result_pipeline='existing E/A, SCALE_LAT6, two output captures; original golden tree/argmax order unchanged'),
        clock=dict(period_ps=833,SS_setup_ps=60,FF_hold_ps=25,relaxed=False),
        adoption=False, SSFF_qualified=False,
        physical_scope='one full64-lane port, not a whole-SM or whole-token qualification')


def dsrom_field_address_lookahead_price():
    """Current single S81 field issuer; new reservation, no existing-state credit.

    Cell constructions are conservative analytical estimates, not mapped counts.
    Named containment and loaded SS/FF remain physical requirements.
    """
    dff, nand, inv, xor, maj, buf = .2916, .08748, .04374, .16038, .13122, .11664
    cells = {"payload_ff": 47*dff, "capture_and_hold_mux": 146*(3*nand+inv),
             "address_add14": 14*(2*xor+maj), "index_add16": 16*(2*xor+maj),
             "equal16": 16*xor+15*nand, "buffer_allowance47": 47*buf}
    slot = 64.8*8.64
    return {"named_slot": "sp_capture/sp_pq_issuer", "instances_per_field_die": 1,
            "full_parameters": {"PHW":6,"SAW":14,"R":128,"VAW":19,"VRD":64,"KMAX":6144,"BST":2},
            "added_state_bits":47,"added_cycles":0,"initiation_interval":1,
            "added_macs_per_cycle":0,"added_memory_bytes_per_cycle":0,
            "added_external_boundary_bits_per_cycle":0,"added_ports":0,"added_cdc":0,
            "local_capture_bits":33,"local_address_bits":14,"existing_stream_bits":48,
            "cell_construction_um2":cells,"estimated_cell_um2":sum(cells.values()),
            "reservation_um2":slot,"reservation_mm2":slot/1e6,
            "slot_xy_um":[15186.96,13476.24,15251.76,13484.88],
            "placement_utilization_budget":.5,"cell_budget_um2":slot*.5,
            "remaining_cell_budget_um2":slot*.5-sum(cells.values()),
            "new_clock_sinks":47,"new_reset_sinks":0,
            "payload_reset_contract":"Existing reset clears sm_run/sw_v; payload captured before qualification. No unreset payload may assert valid.",
            "protection_contract":"All original fault/ownership predicates retained. Additional mandated protection/hold/clock/PG must fit remaining budget; not credited free.",
            "fanout_contract":"Descriptor becomes one local captured copy; mapped fanout and local wire/track allocation unmeasured.",
            "track_capacity_status":"Named 150 x 4 placement grid; occupied sites, routing tracks, PG and clock capacity require owner layout binding.",
            "component_functional_admitted":True,"physical_admitted":False,
            "clock_target_ns":.833333,"ss_setup_uncertainty_ns":.060,"ff_hold_uncertainty_ns":.025,
            "token_latency_delta_cycles":0,"performance_adopted":False}


def hbm_stream_aq_head_ready_cut(*, pcs=128, queue_depth=4):
    """Exact next-head readiness cut for mandatory AQ service closure.

    Register next_nonempty AND readiness(next_head, next_bank_state), using
    both existing next-head alternatives. This adds no command or ACK edge.
    Conservative logic inventory precedes synthesis sharing; loaded timing
    and clock/reset/buffer/route cost require the connected route.
    """
    if pcs < 1 or queue_depth < 2 or queue_depth & (queue_depth-1):
        raise ValueError('positive PC count and retained power-of-two queue required')
    return dict(default_enabled=False, MACs_per_cycle=0, pcs=pcs,
                queue_depth=queue_depth, added_state_bits_per_pc=1,
                total_added_state_bits=pcs, FF_cell_area_floor_um2=pcs*DFF_UM2,
                inherited_hold_cut_bits_per_pc=32,
                mask_AND_equivalents_per_pc=64, OR2_equivalents_per_pc=62,
                late_mux_bits_per_pc=1, nonempty_gate_bits_per_pc=1,
                next_readiness_extra_sinks_per_bank_max=2,
                next_head_onehot_extra_sinks_per_bit_max=1,
                head_ready_source_consumers=2,
                existing_wr_ok_fanout_retained=True,
                output_bytes_per_cycle_max_per_pc=32,
                extra_memory_ports=0, added_boundary_bits=0,
                added_external_tracks=0, added_row_command_cycles=0,
                added_column_command_cycles=0, added_ACK_cycles=0,
                composed_single_user_token_delta_cycles=0,
                added_memory_bytes_per_cycle=0,
                price_excludes_measured_credit='logic sharing, clock/reset buffers, local wires and loaded delay unknown until route',
                area_fit='one added FF/PC in existing service slot; mapped fit unqualified',
                invariant='q == wq_ne && OR(hb_oh & rdyr_q) after every edge for AQ',
                period_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                SSFF_closed=False, adopted=False)

def hbm_topk_predicate_lookahead_model():
    """Default-off N384/P16/K6 selector control successor; no adopted timing gain.

    Price before RTL: compare payloads before selecting one-bit predicates.
    Gross proxy deliberately takes no credit for removed wide compare-input muxes.
    0.2 um2/bit mux is the existing assumed mux basis in this unified model.
    Comparator budget: 32 XNOR + 32 decision gates per added comparator;
    use the same 0.2 um2 gate-equivalent screening basis, not mapped cell area.
    """
    comparators = 16
    gates = comparators*64 + 2*128 + 3*128
    proxy = gates*0.2
    return dict(default_enabled=False, N=384, P=16, K=6, IW=9,
                original_source_sha256='74a669e6d21b25945de777257813bfc4d9f6e7db25fdc261751d1381c9b742f2',
                MACs_per_cycle=0, memory_bytes_per_cycle=0,
                input_bits_per_cycle=512, output_bits_per_result=54,
                extra_boundary_bits=0, replicas=1, input_beats_per_vector=24,
                added_register_bits=0, added_queue_entries=0,
                extra_comparators_32bit=comparators,
                comparator_count_before=128, comparator_count_after=144,
                eligibility_AND_bits=256, one_bit_select_upper_bound=384,
                gross_added_gate_equivalents=gates,
                gross_added_cell_area_proxy_um2=proxy,
                area_proxy_basis='ASSUMED 0.2 um2/gate equivalent; no removed mux credit',
                original_synthesis_cell_area_um2=22760.02,
                cell_area_screen_um2=22760.02+proxy,
                original_routed_core_area_um2=83806.8,
                cell_utilization_screen=(22760.02+proxy)/83806.8,
                floorplan_screen_pass=(22760.02+proxy)/83806.8<0.30,
                incoming_key_compare_fanout_before=8,
                incoming_key_compare_fanout_after=9,
                registered_key_predicate_fanout=8,
                fresh_predicate_sinks=128, lane_fresh_predicate_sinks=8,
                routing_tracks_added_boundary=0,
                local_routing_and_buffer_area_measured=False,
                added_latency_cycles=0, initiation_interval_cycles=1,
                composed_token_latency_delta_cycles=0,
                setup_period_ps=833, setup_uncertainty_ps=60,
                hold_uncertainty_ps=25, io_delay_fraction=0.2,
                baseline_SS_slack_ps=-362.448517,
                baseline_FF_slack_ps=3.35,
                candidate_SSFF_closed=False, adopted=False)


def hbm_stream_aq_last_bound_predicate_cut(*, pcs=128):
    """Conditional mandatory PRE-bound decode repair; not implementation admission.

    Six predicates mirror S<=last on the same accepted descriptor edge.
    S=0 is constant and S=4 reuses last[2]. Encoded last and all other
    comparators remain. No row/column/grant edge changes are permitted.
    """
    if pcs < 1:
        raise ValueError('positive physical PC inventory required')
    return dict(default_enabled=False, candidate_selected=False,
                implementation_started=False, MACs_per_cycle=0, pcs=pcs,
                added_state_bits_per_pc=6, total_added_state_bits=6*pcs,
                FF_cell_area_floor_um2=6*pcs*DFF_UM2,
                capture_enable_muxes_per_pc_max=6,
                descriptor_decode_OR2_per_pc_max=5,
                descriptor_decode_AND2_per_pc_max=5,
                descriptor_bit_extra_loads_before_sharing=[4,6,6],
                predicate_fanout_to_bank_sneed=4,
                clock_reset_extra_sinks_per_pc=6,
                encoded_last_and_other_comparators_retained=True,
                new_memory_ports=0, extra_memory_bytes_per_cycle=0,
                added_boundary_bits=0, added_external_tracks=0,
                added_row_command_cycles=0, added_column_command_cycles=0,
                added_grant_cycles=0, added_ACK_cycles=0,
                composed_single_user_token_delta_cycles=0,
                output_bytes_per_cycle_max_per_pc=32,
                area_fit='6FF/PC body floor in existing service slot; full mapped/control/wire fit unknown',
                added_local_wire_tracks='unmeasured; six four-bank predicate fanouts and descriptor capture enable',
                loaded_comb_delay_ps=None, clock_reset_buffer_area_um2=None,
                invariant='ge_last[S] == (S <= last) at every edge including reset and zero-length descriptor underflow',
                update='same desc_acc as encoded last; reset0 for six nontrivial predicates',
                source_cone='last -> S<=last -> sneed -> PRE lowest-bank priority -> c_oh',
                period_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                SSFF_closed=False, adopted=False,
                build_condition='Only if current head-ready route final verdict requires remaining bounddecode repair')


def hbm_collective_tx_mask_lookahead(*, nl=128, lanes=16, rdup=8, endpoints_per_die=1):
    """Default-off local cut of the routed f12 XREG TX mask cone; not a TU replacement."""
    if nl != 128 or lanes != 16 or rdup != 8:
        raise ValueError('selected f12 context is NL128/LANES16/RDUP8')
    nw=(nl+lanes-1)//lanes
    copies_per_lane=4
    added=nl*copies_per_lane
    area=added*(0.2916+0.2+0.2)  # FF floor + AND + hold/accept selection proxy
    tracks=added+nl+nw*rdup+9
    capacity=int(64/0.08)*4
    return dict(default_enabled=False, adopted=False, MACs_per_cycle=0,
        endpoints_per_die=endpoints_per_die, added_state_bits_per_endpoint=added,
        original_mask_state_bits=nl, original_word_select_copies_bits=nw*rdup,
        original_state_removed_bits=0, added_capture_ANDs=added,
        added_hold_accept_mux_bit_equivalents=added,
        qualified_mask_data_fanout_bits=8, original_combined_mask_data_fanout_bits=32,
        original_mask_to_new_control_fanout=copies_per_lane,
        ingress_payload_bytes_per_accept=nl*4, ingress_count_bits=8,
        TX_payload_bytes_per_edge=lanes*4, TX_record_bits_per_edge=lanes*32+34,
        RX_record_bits_per_edge=lanes*32+34, response_payload_bytes=nl*4,
        added_external_ports=0, added_external_boundary_bits_per_edge=0,
        added_local_control_wires=tracks, assumed_local_channel_tracks=capacity,
        prospective_tracks_fit=tracks<=capacity,
        channel_basis='64um local channel, 80nm pitch, four signal layers; assumption, not placement proof',
        cell_area_proxy_um2_per_endpoint=area, footprint_proxy_um2_at_50pct=2*area,
        area_basis='0.2916um2 FF + 0.2um2 AND + 0.2um2 mux bit proxy; CTS/reset/wire displaced cells unmeasured',
        existing_context_die_um=[540,540], actual_slot_fit=False,
        measured_context_core_um2=287908, measured_context_cell_um2=29965.5,
        prospective_body_area_with_proxy_um2=29965.5+area,
        prospective_body_fit_at_50pct=(29965.5+area)<287908*0.5,
        existing_XREG_state_bits=539, XREG_state_paid_once=True,
        added_cycles_per_record=0, added_cycles_per_collective=0,
        added_token_latency_cycles=0, existing_XREG_added_collective_cycles=2,
        prospective_clock_hz=1200000000, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
        clock_closed=False,
        physical_failure='r6 XREG SS -4.23ps dmask24 -> TX FIFO mem2 bit265; FF +4.13ps',
        retained_owner_credit_CDC=True,
        parent_consumer='HA3=0 ot_hbm_accel_hbm_system.g_mux -> ot_gpu_coll_system.g_r.u_ep; not installed',
        DS_measured_consumer='dshbm_1m_coll.py -> ot_hbm_accel_tu_endpoint NC8/NOG8 or NC1/NOG96; separate',
        Qwen_measured_consumer='qwen_hbmacc_rt_token_w12.py -> ot_rom_oneshot_allreduce; separate',
        installed_parent_or_rate_credit=False)


def hbm_stream_aq_slot_ready_cut(*, pcs=128, queue_depth=4):
    """Mandatory exact slot-readiness alternative after head-ready input failure.

    Each valid slot mirrors its next bank's next readiness. Read-pointer and
    pop choice stay outside flag D. Invalid flags carry no ownership credit.
    This replaces the one-bit head cut, not the inherited 32-bit hold cut.
    """
    if pcs < 1 or queue_depth < 2 or queue_depth & (queue_depth-1):
        raise ValueError('positive PCs and retained power-of-two queue required')
    return dict(default_enabled=False, MACs_per_cycle=0, pcs=pcs,
                queue_depth=queue_depth, added_state_bits_per_pc=queue_depth,
                total_added_state_bits=pcs*queue_depth,
                replaces_head_ready_bits_per_pc=1,
                net_state_delta_vs_failed_head_cut=pcs*(queue_depth-1),
                FF_cell_area_floor_um2=pcs*queue_depth*DFF_UM2,
                slot_bank_mask_AND_per_pc=32*queue_depth,
                slot_bank_reduce_OR2_per_pc=31*queue_depth,
                accepted_push_bank_mux_bits_per_pc=32*queue_depth,
                accepted_push_slot_comparisons_per_pc=queue_depth,
                slot_live_capture_gates_per_pc=queue_depth,
                current_read_pointer_select_AND3_per_pc=queue_depth,
                current_read_pointer_select_OR2_per_pc=queue_depth-1,
                next_readiness_extra_sinks_per_bank=queue_depth,
                accepted_push_decode_extra_sinks_per_slot=32,
                clock_reset_extra_sinks_per_pc=queue_depth,
                inherited_hold_state_bits_per_pc=32,
                queue_payload_and_pop_order_unchanged=True,
                added_memory_ports=0, added_memory_bytes_per_cycle=0,
                added_boundary_bits=0, added_external_tracks=0,
                output_bytes_per_cycle_max_per_pc=32,
                added_command_cycles=0, added_grant_cycles=0, added_ACK_cycles=0,
                composed_single_user_token_delta_cycles=0,
                local_wire_and_buffer_area='unknown positive; per-slot flag D fanout, push decode and read-pointer select need route',
                loaded_delay_ps=None, SSFF_closed=False, adopted=False,
                area_fit='WQ flag FF/PC in same service slot; mapped/control/reset fit unknown',
                invariant='for every valid queue slot: ready_q[i] == OR(wq_boh[i] & rdyr_q); current head select equals original wr_bank_rdy',
                source_constraint='all grant/refresh/open/stale/tRCD next equations unchanged; no stale readiness or earlier visibility',
                period_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25)


def hbm_loader_crc_reserved_slot_price(price):
    """Kant05:12:22 corrected provisional four-cone allocation; estimates, not full fit.

    No original-loop removal credit. One ND1 facade per physical die. All four
    parity folds remain on their original acceptance edges and clock domains.
    """
    core=[8.64,8.64,567.648,567.648]
    regions={'load_host':[8.64,298.944,273.024,563.328],
             'store_host':[298.944,298.944,563.328,563.328],
             'load_mem':[8.64,8.64,273.024,273.024],
             'store_mem':[298.944,8.64,563.328,273.024]}
    costs={'retained_final_route':23294.1,'four_matrix_folds_no_removal_credit':3096.09216,
           'wide_address_state63':18.3708,'wide_guard_operator_proxy':944.43408,
           'fanout_1152_BUF24':503.8848,'twice_actual_route_repair_delta':2543.2}
    capacity=(core[2]-core[0])*(core[3]-core[1])*.55
    tracks=2*price['unshared_XOR2_equivalents_per_fold_ESTIMATE']+32+576+256+96
    assert price['folds_per_die']==4 and price['dies']==1
    return dict(schema='opentallas.loader.crc.reserved-slot.v1',
        binding='Kant codex_notes 2026-10-05T05:12:22.604282+00:00; provisional local slot',
        die_area_um=[0,0,576.288,576.288],core_area_um=core,regions_um=regions,
        ND=1,folds_per_die=4,added_MACs_per_cycle=0,added_state_bits=0,
        added_memory_ports=0,added_memory_bytes_per_cycle=0,added_boundary_bits=0,
        existing_internal_request_bits=342,existing_service_request_bits=341,response_bits=273,
        initiation_interval_edges=1,added_fold_edges=0,composed_latency_delta_cycles=0,
        exact_feedback='same polynomial04c11db7/LSB-first256bits/initFFFFFFFF/no finalxor; unchanged acceptance and retirement',
        per_cone_word_bits=256,per_cone_state_bits=32,
        parity_depth_ESTIMATE=price['maximum_balanced_parity_tree_levels_ESTIMATE'],
        state_fanout=price['maximum_state_bit_output_fanout'],word_fanout=price['maximum_word_bit_output_fanout'],
        tracks_per_cone_bound=tracks,track_components=dict(xor_edges=2*price['unshared_XOR2_equivalents_per_fold_ESTIMATE']+32,input_buffers=576,state_hold=256,clock_reset_enable=96),
        horizontal_signal_tracks_per_cone=9897,vertical_signal_tracks_per_cone=10143,
        layer_pitch_um=dict(M2=.27,M3=.036,M4=.048,M5=.048,M6=.064,M7=.064,M8=.080,M9=.080),
        signal_track_fraction=.5,locality_required=True,
        cell_costs_um2_ESTIMATE=costs,total_cell_budget_um2_ESTIMATE=sum(costs.values()),
        slot_cell_capacity_um2_ESTIMATE=capacity,maximum_slot_cell_utilization=.55,
        positive_remaining_cell_budget_um2_ESTIMATE=capacity-sum(costs.values()),
        component_build_admitted=sum(costs.values())<capacity and tracks<=min(9897,10143),
        recipe_selected_for_component=True,default_enabled=False,adopted=False,
        host_period_ns=1.0,mem_period_ns=.833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        mapped_wide_guard_area_um2=None,PDN_IR_qualified=False,full_parent_fit=False,
        routed_locality_qualified=False,SS_FF_qualified=False,composed_gain_percent=None,
        route_requires='source-pinned Kant quadrant placement and exact real port pins Tcl; one actual candidate route after component PASS')


def dsrom_field_static_provider_price(image_directory):
    """Current canonical immutable provider plus issuer reservation; no physical credit."""
    from dsrom_field_static_provider import model
    return model(image_directory)


def hbm_stream_aq_block_nonempty_choice(*, pcs=128):
    """Unselected zero-edge source choice after THREE failed AQ routes.

    Mirror OR(blk) with exactly the existing set/clear/hold priority, then
    substitute only ep_start's !OR(blk). No fourth RTL/route admission.
    Retain all bank-indexed blk consumers and the blk&open cancellation.
    """
    if pcs < 1:
        raise ValueError('positive PC inventory required')
    return dict(default_enabled=False, candidate_selected=False,
                implementation_started=False, route_admitted=False,
                selection_owner='CLAUDE at three-attempt boundary',
                objective='mandatory 833ps SS/FF baseline clock repair, not speed optimization',
                token_speedup_credit=0,
                pcs=pcs, added_state_bits_per_pc=1,
                total_added_state_bits=pcs,
                FF_cell_area_floor_um2=pcs*DFF_UM2,
                reset_FF_library_master='DFFASRHQNx1_ASAP7_75t_R',
                reset_FF_body_per_pc_um2=.37908,
                reset_FF_body_total_um2=pcs*.37908,
                reset_FF_clock_pin_cap_ff=.433982,
                reset_FF_reset_pin_cap_ff=.704025,
                reset_FF_tied_set_pin_cap_ff=1.02641,
                clock_reset_distribution_area_um2=None,
                capture_priority_muxes_per_pc_max=3,
                gross_logic_gate_equivalent_allowance_per_pc=16,
                gross_logic_area_proxy_per_pc_um2=16*0.2,
                gross_FF_plus_logic_area_proxy_um2=pcs*(DFF_UM2+16*0.2),
                reset_FF_plus_logic_body_proxy_um2=pcs*(.37908+16*0.2),
                extra_clock_sinks_per_pc=1, extra_reset_sinks_per_pc=1,
                predicate_consumers_per_pc=1,
                set_clear_control_extra_sinks_per_pc_max=3,
                existing_bank_indexed_blk_and_cancel_reduction_retained=True,
                removed_gate_area_credit_um2=0,
                MACs_per_cycle=0, output_bytes_per_cycle_max_per_pc=32,
                added_memory_bytes_per_cycle=0, added_memory_ports=0,
                added_boundary_bits_per_cycle=0, added_external_tracks=0,
                added_command_cycles=0, added_grant_cycles=0,
                added_ACK_cycles=0, composed_token_delta_cycles=0,
                zero_edge_price_conditional_on_exact_same_edge_invariant=True,
                invariant='blk_nonempty_q == OR(blk) after reset and every edge; ep_start and all actual grants unchanged',
                next_state_priority='REFPB accepted clear wins; otherwise same original LEAD/set, ep_start/set, cancellation/clear, hold',
                extra_edge_alternative=dict(selected=False,
                    minimum_added_readiness_edges=1,
                    composed_token_delta_cycles=None,
                    eligibility='must revalidate current block/open/timers; stale ready cannot grant',
                    exactness='unpriced latency-changing alternative; not zero-edge class-A admission'),
                local_wire_buffer_clock_reset_area_um2=None,
                loaded_delay_ps=None, full_slot_fit_qualified=False,
                period_ns=.833, setup_uncertainty_ps=60,
                hold_uncertainty_ps=25, SSFF_closed=False, adopted=False)


def hbm_stream_aq_block_nonempty_selected(*, pcs=128):
    """Owner-selected mandatory baseline repair; zero speed/adoption credit.

    Supersedes only model-only admission status. Original three failures and
    review choice remain immutable. Exactly one changed-source route allowed.
    """
    record = hbm_stream_aq_block_nonempty_choice(pcs=pcs)
    record.update(candidate_selected=True,
                  selection_owner='Explicit owner technical decision after three failed variants',
                  implementation_started=False, route_admitted=False,
                  source_gate_required=True,
                  qualified_route_count_allowed=1,
                  failure_policy='stop and report actual limiting cone; no rescue')
    return record


def hbm_topk_balanced_compare_model():
    """Second mandatory CTL repair, priced against retained route_r1 context.

    Gross count for each 42-bit balanced unsigned comparison: 42 generate
    ANDs +42 equality XNORs +41 internal nodes*(AND/OR/AND)=207 gates.
    No credit is taken for the existing 300 comparison cones removed.
    """
    logic = 300*207*0.2
    route = logic*0.20
    hold = 8*336*2*0.25
    total = 28519.8 + logic + route + hold + 0.2 + 55*2*0.25
    return dict(default_enabled=False, variant=2, N=384,P=16,K=6,IW=9,
                MACs_per_cycle=0, memory_bytes_per_cycle=0, replicas=1,
                input_bits_per_cycle=512, output_bits_per_result=54,
                extra_boundary_bits=0, added_register_bits=0,
                comparison_count=300, comparison_width=42,
                unsigned_compare_gross_gate_equivalents=300*207,
                logic_gross_proxy_um2=logic,
                local_route_buffer_reserve_um2=route,
                independent_hold_reserve_um2=hold,
                hold_reserve_basis='up to 2 assumed 0.25um2 buffers per 2688 leaf s0 destination bits',
                area_basis='ASSUMED0.2um2/gate and0.25um2/buffer; no removed-cone credit',
                routed_predecessor_stdcell_um2=28519.8,
                candidate_stdcell_upper_screen_um2=total,
                component_slot='CTL.TOPK_CTX384 retained component; parent slot binding pending Sagan',
                die_area_um=[0,0,290.54,290.54],
                core_area_um=[2.052,2.160,288.522,288.360],
                core_area_um2=81987.714,
                placement_density=0.55,
                cell_occupancy_screen=total/81987.714,
                fixed_component_screen_pass=total/81987.714<0.55,
                parent_slot_fit=False,
                compare_tree_internal_signal_bound=300*2*41,
                compare_tree_local_fanout_bound=3,
                compare_result_payload_fanout_max=84,
                added_clock_sinks=0,
                valid_pipeline_encoding='complemented; same logical reset and pulse edge',
                added_latency_cycles=0, initiation_interval_cycles=1,
                composed_token_latency_delta_cycles=0,
                setup_period_ps=833,setup_uncertainty_ps=60,
                hold_uncertainty_ps=25,io_delay_fraction=0.2,
                hold_repair_margin_ps=20, predecessor_hold_repair_margin_ps=10,
                SSFF_closed=False, adopted=False)


def qwen_rom_registered_issue_commit_price():
    """Source-counted mandatory core repair; no clock/adoption credit.

    Four head ME_AMAX instructions per TP rank in original P8191 AR manifest;
    four ranks execute in parallel. One positive833ps reservation cycle each.
    Descriptor stays in existing NEXT; measured stalls/context remain gates.
    """
    return json.loads((ROOT / "results/rtl/qwen_rom_core_takeover_20261005/issue_commit/prebuild.json").read_text())


def qwen_rom_receiver_fault_base_price():
    """No-cost definition of absent PART2 local fault levels; not timing credit."""
    return json.loads((ROOT / "results/rtl/qwen_rom_core_takeover_20261005/issue_commit/receiver_fault_base/prebuild.json").read_text())


def hbm_stream_aq_period_bound_candidate(*, exposed_service_cycles=None):
    """Unadopted slower-service bound from the failed two-PC extracted path.

    No SDC change, new hardware or route admission. N must be actual exposed
    critical-path service edges, not total issued traffic; absent journal
    keeps whole-token composition unknown. Existing overlap cannot be freed.
    """
    if exposed_service_cycles is not None and exposed_service_cycles < 0:
        raise ValueError('nonnegative actual exposed service cycles required')
    nominal_ps = 833.333
    measured_violation_ps = 21.277424
    bound_ps = nominal_ps + measured_violation_ps
    return dict(status='UNADOPTED_PERIOD_BOUND_ONLY', source_measured_pcs=2,
                nominal_target_period_ps=nominal_ps,
                actual_routed_period_ps=833.0,
                measured_SS_setup_ps=-measured_violation_ps,
                measured_FF_hold_ps=7.988277,
                setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                nominal_period_bound_ps=bound_ps,
                same_existing_SDC_linear_bound_ps=833.0+measured_violation_ps,
                candidate_service_frequency_MHz=1e6/bound_ps,
                service_time_multiplier=bound_ps/nominal_ps,
                service_only_time_increase_fraction=measured_violation_ps/nominal_ps,
                service_only_rate_loss_fraction=1-nominal_ps/bound_ps,
                actual_exposed_service_cycles=exposed_service_cycles,
                added_exposed_service_time_us=(None if exposed_service_cycles is None
                    else exposed_service_cycles*measured_violation_ps/1e6),
                composed_single_user_token_delta_us=None,
                composed_rate_prediction=None,full128_clock_qualified=False,
                additional_CDC_phase_wait_us=None, additional_overlap_credit_us=0,
                whole_token_composition='deltaT=N_exposed*21.277424ps + changed CDC/phase waits + changed competing-service waits; derive N and waits from accepted source calendar',
                selected_installed_service_period_changed=False,
                actual_selected_caller_clock_must_be_reconciled=True,
                added_state_bits=0, added_ports=0, added_area_um2=0,
                constraints_relaxed=False, adopted=False, route_admitted=False,
                timing_requalification='linear fixed-netlist bound only; changed clock/CTS/IO/CDC context not measured',
                limiting_cone='PC1 refwin -> wq_act / oldest pwin -> wab_oh[27]',
                physical_record='results/rtl/svc_aq_block_nonempty_cut_20261005/route_r1/terminal.json')


def qwen_service_aq_act_parent_clock_model():
    """Source-selected enrollment; fractional clock is not an ideal 1024ps clock."""
    return dict(default_enabled=False, MACs_per_cycle=0, stacks=4, pcs=128,
        added_state_bits=4096, register_area_floor_um2=1194.3936,
        area_excludes="local mask logic, enabled mux, clock/reset distribution and wires",
        added_memory_ports=0, added_boundary_bits=0, added_command_edges=0,
        composed_token_delta_edges=0, core_fs=833333, intended_average_ctl_fs=1024000,
        shortest_service_rising_edge_interval_fs=833333,
        longest_service_rising_edge_interval_fs=1666666,
        high_pulse_fs=416666.5, low_pulse_min_fs=416666.5,
        generated_clock="hclk=~clk & tick_q; tick_q selected at core rising edge by accumulator",
        clock_gate="raw AND, not installed ICG; tick-to-falling-edge stability and pulse width unqualified",
        replicas_clock_load="128 PC + four stack controllers + existing service rings; actual capacitance unknown",
        CDC="existing t_clk/hclk FIFOs and core/hclk landing/write handoff unchanged; actual phase/skew unqualified",
        IO="owning parent grants/credits/landing/ACK real wires preserved; actual arrival/load budgets unknown",
        checker_time="existing now=hcyc*1024ps differs from actual fractional edge timestamps",
        required_context="SS60/FF25 shortest833.333ps service edge; generated-clock waveform/pulse/IO/CDC and physical-time DRAM checks",
        command_calendar="same accepted-edge count; wall latency depends on actual accumulator phase and consumer stalls",
        SSFF_closed=False, adopted=False, full128_clock_credit=False,
        slower854_61_bound_selected=False)


def hbm_collective_txmask_physical_fanout():
    """Owner-directed geometry fanout of ONE exact endpoint, not new RTL variants."""
    body = hbm_collective_tx_mask_lookahead()
    mapped = 24753.8  # actual same-source r2 1_synth.json, endpoint+two-SM registered context
    return dict(schema='opentallas.collective.txmask.physical-fanout.v1',
        endpoint=body, geometry_changes_only=True, installed_parent=False,
        contexts=[dict(name='existing-r2', reuse_live=True, core_um2=287908,
                       measured_floorplan_cell_um2=25132, measured_utilization=.0872915),
                  *[dict(name='ctx-u'+str(u), reuse_live=False, core_utilization_pct=u,
                         mapped_cell_um2=mapped, estimated_core_um2=mapped/(u/100),
                         estimated_core_side_um=(mapped/(u/100))**.5,
                         placement_density=.55) for u in (12,15)]],
        standalone=dict(name='die-u12', core_utilization_pct=12, placement_density=.55,
                        conservative_cell_um2_upper_bound=mapped,
                        registered_parent_boundary_removed=True, actual_mapped_area=None),
        boundary=dict(context_ingress_bits=8192, response_bits=4096, link_record_bits=546,
                      IO_delay_fraction=.2, IO_false_paths=False,
                      clock_sm_ns=.833, clock_link_tied_for_physical_context=True,
                      setup_SS_ps=60, hold_FF_ps=25,
                      estimated_smallest_context_edge_track_capacity=4*(mapped/.15)**.5/.08,
                      context_port_bits=13411,
                      track_basis='All four edges, 80nm one-layer equivalent; pin/route legality measured by flow, no installed parent pin map credit'),
        cycles=dict(added_clk_sm_per_collective=2, added_per_record=0,
                    prospective_token_ns_265_collectives=265*2*(1000/1200),
                    clock_credit=False, actual_TU_consumer_timing=False),
        adoption=False, SS_FF_closed=False,
        actual_home_fit=False,
        scope='HA3=0 active baseline boundary; unused HA3 epilogue-only inputs excluded, no arithmetic/credit/CDC change. No actual TU clock substitution.')
def hbm_topk_balanced_fanout_model():
    """Same frozen balanced source; owner-directed concurrent utilization contexts.

    Actual retained 30% core is the footprint basis. Larger 25/20% contexts
    charge their full area and longer local wire reserve; parent fit unbound.
    No changed clock/IO, arithmetic, pipeline, replica or semantic admission.
    """
    base = hbm_topk_balanced_compare_model()
    contexts = []
    for util in (25, 20):
        scale = (30.0/util)**0.5
        x0,y0,x1,y1 = base['core_area_um']
        width,height = (x1-x0)*scale,(y1-y0)*scale
        core = [x0,y0,round(x0+width,6),round(y0+height,6)]
        die = [0,0,round(core[2]+2.018,6),round(core[3]+2.180,6)]
        route = base['local_route_buffer_reserve_um2']*scale
        area = base['candidate_stdcell_upper_screen_um2']-base['local_route_buffer_reserve_um2']+route
        contexts.append(dict(utilization_percent=util, core_area_um=core,
            die_area_um=die, core_area_um2=width*height,
            extra_core_area_vs_retained_um2=width*height-base['core_area_um2'],
            local_wire_length_scale=scale, routing_buffer_reserve_um2=route,
            independent_hold_reserve_um2=base['independent_hold_reserve_um2'],
            gross_cell_area_screen_um2=area, cell_occupancy=area/(width*height),
            place_density=0.55, component_screen_fit=area/(width*height)<0.55,
            parent_named_slot_fit=False, parent_routing_tracks_available=None,
            clock_period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            hold_repair_margin_ps=20, io_delay_fraction=0.2,
            replicas=1, MACs_per_cycle=0, added_memory_ports=0,
            input_bits_per_cycle=512, output_bits_per_result=54,
            added_latency_cycles=0, latency_cycles=23, initiation_interval_cycles=1,
            adopted=False, SSFF_closed=False))
    return dict(source_commit='5ee4cde5b11b31b7f45964f24165a46b9eb3f90d',
                source_and_common_helper_unchanged=True,
                retained_live_context='peirce-topk-balanced-route-r1',
                retained_supervisor=3271408, contexts=contexts)


def qwen_service_actual_edge_eligibility_model(exposed_column_transactions=None):
    """Observed clock-calendar failure and unadmitted conservative column-wait cost."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('qwen_service_actual_edge_calendar.py')
    spec = importlib.util.spec_from_file_location('qwen_actual_edge_calendar', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.model()
    result['observed_tCCD_S_violation'] = dict(interval_fs=833333, required_fs=1024000,
        columns=256, violations=194, actual_PC_source='rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv')
    result['conservative_column_guard_only'] = dict(pcs=128, added_FF_floor=128,
        area_floor_um2=128 * .2916, new_ports=0, added_boundary_bits=0,
        added_clock_reset_bits=128, mux_and_wire_and_slot_fit=None,
        extra_gap_edges_per_column=1, peak_bytes_per_PC_per_service_edge=16,
        other_DRAM_timing_repairs='not included; this guard alone is insufficient',
        adoption=False)
    result['exposed_column_transactions'] = exposed_column_transactions
    result['prospective_extra_exposed_service_edges'] = exposed_column_transactions
    result['composed_token_delta_s'] = None
    result['composition_missing'] = 'actual accepted column/refresh/return/credit calendar and generated edge phase; no free overlap assumption'
    return result


def hbm_loader_retained_token_host_price(*, mem_words, dies=2, slices=2):
    """Acceptance8c retained reduced HA3 fixture; boot is outside decode latency.
    No new engine/datapath. Actual LOAD_VERIFY and finite ACK/readback then
    code/command SRAM publication fence precede host SQ doorbell. Not a new
    full-target model or physical/adoption claim.
    """
    n=mem_words*dies*slices*32
    return dict(scope='retained reduced Qwen/V4.1 acceptance8c, HA3=0',
        added_MACs_per_cycle=0,added_engine_area_um2=0,new_engine_RTL=False,
        dies=dies,SMs_per_die=2,lanes_per_SM=128,slices_per_die=slices,
        mem_words_per_partition=mem_words,image_bytes=n,host_DMA_bits=64,
        host_DMA_bytes_per_edge=8,mem_payload_bits=256,mem_bytes_per_accepted_edge=32,
        internal_request_bits=337,response_bits=273,loader_clients_per_die=1,
        loader_write_debt_slots=96,loader_verify_read_slots=16,data_CDC_words=32,
        code_CDC_record_bits=97,code_CDC_words=8,
        loader_replica_count=dies,existing_dma_arbiter_clients=2*dies+1,
        host_period_ns=4.0,SM_period_ns=.833,mem_period_ns=1.0,link_period_ns=.9,
        minimum_host_read_boot_ns=n/8*4,boot_extra_verify_bytes=n,
        boot_latency_measured_ns=None,decode_latency_measured_cycles=None,
        decode_added_cycles=0,new_boundary_bits_per_cycle=0,new_ports=0,
        fence='real descriptorCRC/readback/status + matchedACKdebt; all accepted ld records applied and actual SRAM readback observed before SQ_TAIL',
        bytes_and_visibility='retained images only in host memory; no gpu_sys_mem_prefix, no hierarchical DUT assignment',
        existing_wire_CDC_credits_refresh='retained model RTL exercised, not zero-cost or physical signoff',
        unknowns='production PCIe tail, full-system physical CDC/slot/SSFF remain unqualified',
        adopted=False,physical_qualified=False,source_changed_datapath=False)


def ha2_tu_owner_adapter_model():
    """Additive runtime owner replacement, selected shared8 TU shape, unadopted."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('ha2_tu_owner_model.py')
    spec = importlib.util.spec_from_file_location('ha2_tu_owner_model', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.model()


def dshbm_expert_workgroup_model():
    """Actual matched-reference 12-matrix source layout, not a new SM datapath.

    Software loader/dispatch implementation uses existing per-SM descriptor and
    activation/weight ports. Dynamic hardware steering has not been synthesized.
    """
    return dict(dies=96, SM_per_die=32, active_SM_per_die=24, idle_SM_per_die=8,
        released_expert_count=384, routed_experts=6, matrices_per_expert=2, K=5120, matrix_rows=2304,
        rows_per_matrix_per_die=24, rows_per_active_SM=12, k32_blocks=160,
        exact_MACs_per_issued_line_active_column=8*32, native_columns=8,
        hardware_MACs_per_full_issued_line=8*32*8, line_payload_bits=1088,
        line_bytes_per_accepted_edge=136, simultaneous_weight_bits_per_die=24*1088,
        simultaneous_weight_bytes_per_die=24*136, per_SM_lines=12*3*8, per_SM_valid_row_blocks=12*160,
        per_SM_native_issue_groups=3, per_SM_issue_span_cycles=316,
        activation_port_bits=2048, activation_AR_beats_per_address=2,
        activation_AR_load_cycles_measured=49,
        AR_start_to_done_measured_shape_cycles=396,
        AR_start_to_done_actual_source_cycles=None,
        source_row_order='each matrix, ascending rows; original k32 block and csum order',
        existing_state_changed_bits=0, extra_payload_storage_bytes=0,
        descriptor_count_per_die=24, descriptor_hardware_area_mm2=None,
        activation_multicast_pipeline_cycles=None, boundary_routing_tracks=None,
        new_hardware=False, hardware_steering_implemented=False,
        physical_slot_fit=None, actual_1M_L20_exact=False, actual_1M_L3_exact=False,
        actual_composed_token_latency_ns=None, adopted=False)


def hbm_su_fused_endpoint_model():
    """Default-off actual fused-SU endpoint pre-build sizing; unqualified."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('hbm_accel_su_fused_model.py')
    spec = importlib.util.spec_from_file_location('hbm_su_fused_price', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.model()


def hbm_su_sqrt_prefix_round_model():
    """Same-cut opt-in repair of the measured side/softplus rounding ripple.

    Pricing precedes RTL. No exponent retiming, reset exception, or II change.
    Cell budget is a conservative prebuild reservation, not mapped area.
    """
    width = 24
    levels = (width + 1).bit_length() - 1
    if (1 << levels) < width + 1:
        levels += 1
    pairs = sum(width + 1 - (1 << level) for level in range(levels))
    return dict(schema='hbm_su_sqrt_prefix_round.v1',
                source='rtl/hdc/v41/ot_hdc_fsqrt.sv',
                baseline_SS_r2r_ps=dict(side=-167.446838, softplus=-112.847954),
                repair='24-bit kept prefix increment; carry becomes rounded[24]',
                AND2_nodes=pairs, XOR2_nodes=width, prefix_levels=levels,
                new_FF_bits=0, new_clock_reset_sinks=0,
                conservative_gross_logic_reservation_um2_per_sqrt=250,
                mapped_net_area_delta_um2=None,
                side_sqrt_replicas=3, standalone_softplus_sqrt_replicas=1,
                side_gross_reservation_um2=750, softplus_gross_reservation_um2=250,
                primitive_MACs_per_cycle=0, primitive_words_per_cycle=1,
                operand_port_bytes_per_cycle=4, result_port_bytes_per_cycle=4,
                boundary_bits_per_cycle=32, new_boundary_bits_per_cycle=0,
                prefix_local_fanout_bound=6,
                fanout_basis="Includes alias-collapsed pass-through levels plus final XOR; buffers remain physical cost",
                internal_prefix_node_tracks=pairs, routing_capacity_pass=None,
                carry_encode_fanout_and_loaded_wire_delay='unchanged downstream; route must measure',
                latency_edges=31, issue_interval_edges=1, added_chain_edges=0,
                single_user_latency_delta_ns=0,
                critical_cone='finish-1 f_trunc -> prefix/RNE -> exponent/select -> finish-2 y',
                exponent_encode='original signed 12-bit arithmetic unchanged',
                reset_recovery='original timed rst_n/vline; retained recovery FAIL remains blocking',
                exactness_required='same original code/fault/valid edge including bubbles and refusals',
                context_clock_ns=.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                area_slot_fit=None, SSFF_closed=False, adopted=False)



def hbm_su_kr_capture_split_model(lanes=1024):
    """Pre-mux BF16 metadata repair; physical KR40 witness is one lane."""
    return dict(schema='hbm_su_kr_capture_split.v1',
                source='rtl/hdc/v41x/ot_hdc_v41x_vec_lane_kr_f12.sv',
                measured_SS_capture_slack_ps=-46.211811,
                baseline='select 32-bit source then increment/reduce to X metadata',
                candidate='increment and guard/sticky each actual source, then select 17 metadata bits',
                kept_prefix_levels=5, AND2_nodes_gross=108, XOR2_nodes_gross=32,
                OR4_nodes_gross=10, AND2_guard_nodes=2, metadata_mux_bits=17,
                gross_logic_reservation_um2_per_lane=200,
                whole_lanes=lanes, gross_logic_reservation_um2=lanes*200,
                new_FF_bits=0, new_reset_clock_sinks=0,
                MACs_per_cycle=0, helper_input_bytes_per_cycle=8,
                helper_metadata_bits_per_cycle=17, new_external_port_bits=0,
                source_selector_metadata_fanout=17,
                selected_word_capture='original x_a source mux retained',
                internal_prefix_local_fanout_bound=6,
                fanout_basis="Includes alias-collapsed pass-through levels plus final XOR; buffers remain physical cost",
                internal_prefix_node_tracks_gross=108, routing_capacity_pass=None,
                latency_edges_added=0, issue_interval_edges=1,
                single_user_latency_delta_ns=0,
                BF16_semantics='same original unsigned upper-half increment and RNE decision for all 32-bit patterns; no new NaN policy',
                mutable_KR_owner='unchanged ck_r/kr_q association, no new reads or leases',
                clock_ns=.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                reset_exception_added=False, area_slot_fit=None,
                actual_area_delta_um2=None, SSFF_closed=False, adopted=False)



def hbm_su_command_bridge_model():
    """Pre-hardware actual command/scalar producer boundary sizing."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('hbm_accel_su_fused_model.py')
    spec = importlib.util.spec_from_file_location('hbm_su_command_bridge_price', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.command_bridge_model()


def hbm_su_finite_rf_provider_model():
    """Finite GPU RF working-set candidate, including staged publication cost."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('hbm_accel_su_fused_model.py')
    spec = importlib.util.spec_from_file_location('hbm_su_finite_rf_price', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.finite_rf_provider_model()


def hbm_su_finite_provider_tradeoff_model():
    """Selected sector path versus finite RF staging; no headline clock credit."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name('hbm_accel_su_fused_model.py')
    spec = importlib.util.spec_from_file_location('hbm_su_finite_provider_tradeoff', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.finite_provider_tradeoff_model()


def hbm_su_finite_native_parent_model():
    """Einstein's installed DS20 borrower: capacity, cuts, slot and finite IO."""
    import hbm_accel_su_fused_model
    return hbm_accel_su_fused_model.finite_native_parent_model()


def dshbm_wavepack_production_adapter_model():
    """Erdos's one-client production adapter, distinct from logical PQ gates."""
    import dshbm_wavepack_model
    return dshbm_wavepack_model.production_adapter_model()


def qwen_hbm_selected_activation_provider_model():
    """Reconcile the selected addressed-word VM ABI with the result-port model.

    This prices no new architecture. The host's independent word reads and
    result-port placement budget do not constitute a physical VM provider.
    """
    import hashlib
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    binding_path = 'results/rtl/qwen_hbm_opt3_activation_layout_20261005/selected_me_binding.json'
    port_path = 'results/rtl/qwen_hbm_final_tp4_20261005/existing_port_model.json'
    delta_path = 'results/rtl/qwen_hbm_final_tp4_20261005/model_delta.json'
    inventory_path = 'results/rtl/qwen_hbm_activation_vm_inventory_20261005/provider_inventory.json'
    binding = json.loads((root/binding_path).read_text())
    port = json.loads((root/port_path).read_text())
    delta = json.loads((root/delta_path).read_text())
    inventory = json.loads((root/inventory_path).read_text())
    host = inventory['host_provider']
    rf = inventory['existing_RF_namespace']
    assert inventory['selected_source']['pins'] == binding['selected_source']['pins']
    assert host['logical_words_per_die'] == 177808
    assert rf['geometry']['logical_FP32_words'] == 65536
    assert rf['source_only_timing']['best_read_II_edges'] == 3
    assert not rf['selected'] and not inventory['existing_DS_VM_reference']['selected']
    activation = binding['prebuild_model']['activation']
    n = activation['independently_enabled_word_ports_per_die']
    data = n*activation['word_bits']
    address = n*activation['address_bits']
    assert (n, data, address, n) == (2048, 65536, 49152, 2048)
    assert port['source_sha256'] == binding['selected_source']['pins']['rtl/hdc/ot_qwen_me_spine_h_w12.sv']
    assert delta['once_only_port_cell_reservation_per_die_um2'] == port['area']['all24_port_cell_reservation_um2']
    inputs = [binding_path, port_path, delta_path, inventory_path]
    for p, expected in binding['selected_source']['pins'].items():
        assert hashlib.sha256((root/p).read_bytes()).hexdigest() == expected, p
        inputs.append(p)
    return dict(scope='selected Qwen TP4 P8191 ME activation boundary; source reconciliation only',
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in inputs},
        compiled_SMAX=11, compiled_XVM=1, dies=4,
        independently_addressed_read_words_per_edge_capacity=n,
        data_bits_per_edge_capacity=data, data_bytes_per_edge_capacity=data//8,
        address_bits_per_edge_capacity=address, enable_bits_per_edge_capacity=n,
        request_signal_bits=address+n, response_signal_bits=data,
        total_logical_interface_signal_bits_per_die=data+address+n,
        actual_simultaneous_read_census=None,
        actual_distinct_words_per_accepted_event=None,
        source_affine_bank_row_lane_and_reuse_plan='results/rtl/qwen_hbm_activation_vm_realization_20261005/proposal.json',
        finite_provider_candidate=qwen_hbm_finite_activation_vm_model(),
        software_VM_words_per_die=host['logical_words_per_die'],
        software_VM_bytes_per_die=host['logical_bytes_per_die'],
        software_VM_bytes_TP4=host['total_TP4_logical_bytes'],
        software_capacity_is_physical_capacity=False,
        existing_RF_reference=dict(
            selected=False, module=rf['module'], caller=rf['caller'],
            logical_words=rf['geometry']['logical_FP32_words'],
            missing_backing_words=host['logical_words_per_die']-rf['geometry']['logical_FP32_words'],
            source_best_read_II_edges=rf['source_only_timing']['best_read_II_edges'],
            source_transactions=rf['selected_2048_word_best_byte_floor'],
            macro_body_mm2=rf['macro']['total_existing128_macro_body_um2']/1e6,
            physical_selected_provider=False,
            rule='Finite vector-addressed RF is not a 2048-word scatter provider; byte-volume floor applies only to distinct, vector-coalescible words within its capacity. Do not price every event as 2048 unique words.'),
        provider_risks=dict(
            capacity='177808 software words exceed existing RF backing by112272 words; actual live working set/reuse and full backing mapping require source-affine plan, not automatic replica selection',
            stalls='XVM1 fixed sampling has no selected bank grant/backpressure; repeated addresses may be reused/broadcast only with matched read-before-write/version semantics. Distinct words, collisions, queued reads and all writer publication must be counted per accepted event.',
            area='RF macro body is a reference only, not selected VM debit; storage copies, lane gather/mux/fanout, common SU/collective faces, native writer ports, clocks/CDC/corridors remain unpriced. Head/result port cost is not VM containment.',
            next_step='Arendt source-affine finite bank/row/lane, reuse and collision plan for actual program/ports; Maxwell sizes capacity/service/area/token cost before any provider RTL or P&R'),
        source_read='one enabled vx_re word reads host m.vm[vx_addr]; raw32 response through XVM1 and unchanged spine selection',
        native_source_not_physical_VM='std::vector host access has no installed bank grant/request-ready or physical simultaneous-port proof',
        selected_VM_provider_source=None, physical_VM_capacity_bytes=None,
        physical_VM_read_ports=None, physical_VM_bytes_per_cycle_guaranteed=None,
        VM_bank_decode_mux_fanout_area_mm2=None, VM_macro_and_replica_area_mm2=None,
        activation_channel_capacity_tracks=None, activation_loaded_route_and_CDC_edges=None,
        read_drain_and_write_publication_service_bound_us=None,
        result_port_budget=dict(source=port_path, replicas=port['replicas'],
            scope='24 postscale/result ports, each full64-lane; not activation VM bank/return infrastructure',
            retained_cell_reservation_per_die_mm2=port['area']['all24_port_cell_reservation_um2']/1e6,
            placement_reservation_per_die_mm2=24*port['area']['minimum_core_for_reserved_cells_um2']/1e6,
            retained_cell_reservation_TP4_mm2=delta['once_only_port_cell_reservation_tp4_um2']/1e6,
            one_port_external_tracks_upper_bound=port['ports_and_tracks']['external_track_demand_upper_bound'],
            one_port_channel_fit=port['ports_and_tracks']['channel_capacity_and_loaded_cut_fit'],
            SS_setup_ps=port['address_cone']['measured_SS_ps'],
            FF_hold_ps=port['address_cone']['measured_FF_ps'],
            SSFF_qualified=port['SSFF_qualified'],
            area_rule='retain result-port debit once; neither duplicate it nor treat it as containing unpriced VM/activation routes'),
        activation_route_accounting='116736 is logical request+response width, not a proven one-channel track allocation; no automatic transfer of result-port5466 tracks',
        opt3_verdict=binding['verdict'], opt3_enabled=False,
        opt3_incremental_area_mm2=0, opt3_cycles_saved=0,
        DS_8_4_3_beats_savings_transfer=False,
        generic_256bit_payload_only_read_beats_lower_bound=data//256,
        narrower_service_scope='256 beats is payload-only arithmetic, not an actual serialized service selection or compatible next-edge reply',
        actual_stage_measurements_retained=binding['retained_measurements']['stage_cycles'],
        stage_measurement_scope='unchanged representative L5/L20/head outputs; no layout-ON or full36layer token performance',
        whole_die_fit=None, provider_added_token_latency_us=None,
        physical_clock_qualified=False, headline_gain_percent=None,
        new_architecture_selected=False, new_RTL=False)


def qwen_hbm_finite_activation_vm_model():
    """One source-affine finite backing candidate; no replica/free-port credit.

    A logical-source edge is not a physical SRAM edge. All reads of an owned
    source frame sample the old image before its masked writers publish. The
    source freeze/XVM association is an implementation obligation, not an
    already functioning variable-latency SU interface.
    """
    import hashlib
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    path = 'results/rtl/qwen_hbm_activation_vm_realization_20261005/proposal.json'
    p = json.loads((root/path).read_text())
    m, ports, service = p['mapping'], p['ports'], p['finite_service']
    backend = 'rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv'
    assert m['injective'] and m['all_scalar_addresses_checked'] == 177808
    assert (m['full_existing_groups'], m['existing_macros']) == (16, 256)
    assert len(p['records']) == 220 and service['masked_r2_read_result_after_accept_edges'] == 4
    coded_frame_bits = 72*(ports['maximum_aggregate_snapshot_read_seats'] + ports['maximum_aggregate_write_seats'])
    protection_path = 'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    protection = json.loads((root/protection_path).read_text())['SRAM_protection_candidate']
    # One checked bank window at a time; no 64 read copies or raw ACK release.
    checked_read_edges, checked_write_edges = 9, 28
    codec_pairs = ports['maximum_aggregate_snapshot_read_seats'] + ports['maximum_aggregate_write_seats'] + 64
    cut_bits = 32*72*5
    codec_body = codec_pairs*protection['pair_cell_body_um2']/1e6
    control_bits = 8192  # positive bounded controller allowance, not mapped state
    frame_body = (coded_frame_bits+cut_bits+control_bits)*DFF_UM2/1e6
    mux_body = (coded_frame_bits+cut_bits+control_bits)*.2/1e6
    protected_macro_body = m['full_macro_body_area_um2']/1e6 + protection['sidecar_macro_body_mm2']
    placement = protected_macro_body + 2*(codec_body+frame_body+mux_body)*1.05
    stages = []
    for w in p['stage_read_workload']:
        if w['rank'] != 0:
            continue
        records = [r for r in p['records'] if r['stage'] == w['stage'] and r['rank'] == 0 and r['unit'] == 'ME']
        writes = sum(r['analysis']['write_events'] for r in records)
        # Serialized checked windows: no overlap credit. Source single-edge
        # issue is removed once; rawACK is not protected publication.
        read_extra = w['ds_read_issue_beats']*11 - w['logical_ME_read_edges']
        write_charge = w['ds_ME_write_beats']*30
        stages.append(dict(stage=w['stage'], logical_ME_read_edges=w['logical_ME_read_edges'],
            read_issue_beats=w['ds_read_issue_beats'], write_beats=w['ds_ME_write_beats'],
            write_events=writes, conservative_extra_read_service_edges=read_extra,
            conservative_write_visibility_service_edges=write_charge,
            isolated_serial_service_charge_us_at_target=(read_extra+write_charge)/1.2e3,
            scope='per-rank ME missed-window/flush subcomponent only, not a complete frame or actual accepted critical-path delta; scalar read/write slot walkers, skip/pack, SU/collective interference and crossings additional'))
    head = p['head_source_reuse_proposal']
    head_coded_bits = ((head['staging_data_bits']+63)//64)*72
    return dict(schema='opentallas.qwen-hbm.finite-activation-vm-candidate.v1',
        source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in (path, backend, protection_path)},
        provider=backend, selected_for_minimum_source_implementation=True,
        instantiated_in_selected_build=False, default_enabled=False, adopted=False,
        selection='ONE existing full16-group masked-visible provider, no read copies; six-group capacity-only geometry is not selected',
        DEPTH_GROUPS=16, AW=15, TAG_W=227, MASKED_VISIBLE=1,
        scalar_words=177808, physical_bytes=m['physical_bytes'], macros=256,
        mapping={k:m[k] for k in ('scalar_to_word','lane','bank','row','group','column')},
        MACs_per_cycle=0, provider_read_bytes_per_issue=256, provider_write_bytes_per_issue=256,
        physical_bank_write_bytes_per_issue=64, raw_macro_read_issue_II_edges=1, checked_read_service_II_edges=9,
        read_port='one base address -> four consecutive512-bit words; never four arbitrary addresses',
        write_ports='one masked512-bit row per physical bank per provider edge',
        frame_capacity=1,
        source_edge_policy='Reserve one complete snapshot before admitted source edge; hold the producer/response tags, engine state and native XVM1 together while physical service advances; no new source edge until real write ACKs retire this frame',
        SU_policy='Three operand windows collected into the same owned snapshot. Native SU has no active-op ready: implement opt-in matched state/read-response/write-strobe freeze, not a three-read image replication or source-progress-as-ACK shortcut.',
        old_read_and_writer_order='All frame old reads finish before writes; ME, MX, SU, reducer, collective scalar precedence retained. Equal-address later writer wins only with its actual commit.',
        hazard_policy='Track read macro accept+1 versus write macro accept+2 across commands; release after ACK+positive next-edge capture. No reliance on same-command collision flag alone.',
        read_calendar='CAP1 checked window: raw result4 +held decode3 +capture/nativeXVM2 =9 target edges per physical window; next window after release, notII1',
        write_calendar='CAP1 actual registered RMW handoff: postverifiedACK28 after accept; maskedflush30 extra beyond scalar slot walker. Replaces lower22edge sizing; rawACK not checked visibility',
        serial_frame_calendar=dict(capture_edges=1,read_slot_visits=ports['maximum_aggregate_snapshot_read_seats'],read_miss_extra_edges=11,write_slot_visits=ports['maximum_aggregate_write_seats'],masked_flush_extra_edges=30,admit_edges=1,
            formula='1+actual_read_slot_visits+11*window_misses+actual_write_slot_visits+30*masked_commands+1; skip/pack extra; empty/ownedreadonly fast path only under real source conditions',
            basis='Arendt14:39 literal controller source accounting, not runtime measurement'),
        peak_ME_windows=64, peak_W1_same_bank_write_beats=48,
        SU_operand_windows_per_source_edge=3,
        source_distinct_ME_words=sorted({r['analysis']['read_max']['distinct_scalars'] for r in p['records'] if r['unit']=='ME'}),
        source_workload=stages,
        macro_body_floor_mm2=m['full_macro_body_area_um2']/1e6,
        protected_service=dict(data_macros=256,check_macros=32,total_macros=288,
            macro_body_mm2=protected_macro_body,check_bits=2097152,
            bank_window_capacity=1,checked_read_edges=checked_read_edges,checked_write_service_II_edges=checked_write_edges,
            codec_encode_held_edges=2,codec_decode_held_edges=3,codec_pairs=codec_pairs,codec_body_mm2=codec_body,
            pipeline_cut_FF_bits=cut_bits,control_FF_allowance=control_bits,
            placement_estimate_mm2=placement,required_component_outline_um=[4000,1200],required_envelope_mm2=4.8,
            estimate_fits_required_envelope=placement<=4.8,parent_slot_reserved=False,
            timing_basis='retained W6 encode905.013ps/decode1633.328ps inclSS60 plus assumed250ps load; held2/3 edges at target1.2, not contextual closure',
            protection_implementation_present=False,
            exclusions='loaded CTS/PG/hold repair/long channels; optional head staging excluded; no source ACK as publication'),
        finite_snapshot_seats=dict(read=ports['maximum_aggregate_snapshot_read_seats'],
            write=ports['maximum_aggregate_write_seats'], protected_bits_floor=coded_frame_bits,
            protected_FF_body_floor_mm2=coded_frame_bits*DFF_UM2/1e6,
            basis='one72-bit W6 encoded64-bit seat for each raw32/address24/enable record; existing W6 mutable-state protection retained, decode/encode/control additional'),
        protection_source='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
        head_level2_candidate=dict(producer_pc=head['producer_pc'], consumer_pcs=head['consumer_pcs'],
            source_region=head['source_region'], readonly_after_actual_producer_visibility=True,
            words=4096, fill_issue_beats=64, conservative_fill_capture_alignment_edges=576,
            protected_staging_bits=head_coded_bits,
            protected_FF_body_floor_mm2=head_coded_bits*DFF_UM2/1e6,
            local_mux_assumed_floor_mm2=head['mux_body_assumed_um2']/1e6,
            gain_credited_us=0, selected_for_first_reuse_binding=True, physical_implementation_selected=False,
            parallel_decode_pairs_if_full2048word_read=2048,
            parallel_decode_conservative_pair_body_mm2=2048*protection['pair_cell_body_um2']/1e6,
            admission='all64 SU source vectors physically published/ACKed, region lease through PCs3..6, actual loaded selector/capture and native tag association; source chase counter alone is insufficient'),
        highest_exposed_risk='head no-reuse service; local readonly reuse is the first scoped candidate, no credited gain yet',
        target_provider_GHz=1.2, target_not_qualified=True,
        source_domain='selected functional commonclk; physical SU0.9/stream1.2 crossing remains a separate unimplemented binding, not zero-cost',
        SS_macro_clkq_ps=m['SS_macro_clkq_ps'], SS_macro_remaining_capture_budget_ps=m['macro_only_setup_budget_remaining_ps'],
        controller_codec_hold_gate_clock_route_area_mm2=None, loaded_corridor_tracks=None,
        area_slot_fit=None, token_added_latency_us=None, qualified_headline_rate=None,
        physical_clock_qualified=False, headline_gain_percent=None,
        next_implementation='Arendt minimum source wrapper with owned finite snapshot, ME_STALL conjunction of weight-ready and matched VM response-ready, explicit SU freeze and real masked-write ACK association; size control/codec and loaded boundary before component build; Ampere original unchanged')


def hbm_index_ordered_adapter_model():
    """Bounded source-compatible proposal, gated on the existing writer scope.

    Reuse W15's existing gather extent; one checked 512-bit load port and a
    registered ID tree. This selects a finite serial implementation budget,
    never the old 419-edge global rate or 96 simultaneous SRAM ports.
    """
    import hashlib
    import json
    import math
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    context = 'results/uarch/hbm_index_context_20261005/model.json'
    codec_path = 'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    original = 'rtl/chip/ot_w15_coll_dma.sv'
    merger = 'rtl/chip/ot_coll_topk_merge.sv'
    cm = json.loads((root/codec_path).read_text())['SRAM_protection_candidate']
    current = json.loads((root/context).read_text())
    ranks, words_per_rank, load_words = 96, 512, 6144
    selections = ranks*words_per_rank
    # Source proposal held context job32/gen4/pos20/rank7 plus ID20/score32.
    # One 512b word feeds eight64b heads; padded 128-leaf tree has127 nodes.
    context_bits = 32+4+20+7
    head_raw_bits = 96*(8*64+context_bits+9+3+8)
    tree_raw_bits = 127*(64+7+1)
    sink_raw_bits = 512*32
    ff = sum(math.ceil(x/64)*72 for x in (head_raw_bits, tree_raw_bits, sink_raw_bits, 512+context_bits))
    pairs = 8+1  # checked load stripes and one tree-result protection port
    # 95 meaningful ID comparators/muxes; use all127 padded nodes for cost.
    nand2 = 127*(20*12+64*3)+96*9*12+2048
    body = ff*.2916 + ff*.2 + nand2*.08748 + pairs*cm['pair_cell_body_um2'] + math.ceil((ff-1)/7)*.10206
    placement = 2*body*1.05/1e6
    checked_load_edges = 9  # raw4/heldW6decode3/capture+identity2
    selection_edges = 8  # seven registered levels plus positive retirement
    load_edges, select_edges = load_words*checked_load_edges, selections*selection_edges
    return dict(schema='hbm.index.ordered-adapter.minimum.v1',default_enabled=False,
        selection='one ID-ordered head/cursor adapter ahead of unchanged W15 merger; existing gather storage, single checked512b read port, no parallel96port assumption',
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in (context,codec_path,original,merger)},
        backing_bytes=393216,new_backing_storage_bytes=0,
        backing_reuse_condition='exclusive source VM gather extent lease, all accepted writers drained; physical SRAM/protection/arbiter must be bound by existing VM owner, not prepaid by this adapter',
        rank_heads=96,head_buffer_words64_per_rank=8,cursor_bits_per_rank=9,
        selected_ID_pairs=selections,SRAM_load_words512=load_words,
        SRAM_read_ports=1,SRAM_payload_bytes_per_issue=64,
        source_byte_order='ascending literal globalID, duplicate/descendingID faults retain debt; stride0 applies only logical merged slots, physical rank retained',
        real_comparators=95,padded_tree_nodes=127,registered_tree_levels=7,
        protected_FF=ff,codec_pairs=pairs,NAND2_allowance=nand2,
        placement_at50pct_mm2=placement,required_component_outline_um=[800,400],required_envelope_mm2=.32,
        estimate_fits_required_envelope=placement<=.32,parent_home_reserved=False,
        raw_output_sink_capacity_IDs=512,source_NO_READY_sink_reserved_before_GO=True,
        checked_load_service_edges=checked_load_edges,selection_service_edges=selection_edges,
        serial_load_edges=load_edges,serial_selection_edges=select_edges,
        actual_consumer_load_edges=load_words,
        serial_service_budget_edges=load_edges+select_edges+load_words,
        serial_service_budget_us_at_target_1p2=(load_edges+select_edges+load_words)/1200,
        target_clock_not_qualified=True,
        budget_excludes='input gather/held-source stalls, actual loaded tree/CDC/publication/positive credit return; 8edges is candidate register plan, not STA closure',
        current_index_footprint_mm2=current['area_screen']['minimum_footprint_at_explicit_50pct_utilization_mm2'],
        current_index_slot_mm2=current['area_screen']['r7_total_index_reservation_mm2'],
        footprint_with_adapter_floor_mm2=current['area_screen']['minimum_footprint_at_explicit_50pct_utilization_mm2']+placement,
        native_link_payload_metadata_minimum_edges=current['key_boundary']['old_link_payload_metadata_lower_bound_edges'],
        framed_native_link_edges=current['key_boundary']['whole_beat_framed_phase_edges'],
        source_preparation_permitted_if_unowned=True,
        implementation_writer_confirmation_required=True,
        physical_build_admitted=False,global_419_edge_credit=False,
        adopted=False,token_gain_us=None,
        next='Sagan/Rawls confirm no active ordered-gather writer before implementing bounded opt-in source; Claude must replace inadequate r7 slot; no widening or free SRAM ports selected')

def dshbm_expert_workgroup_interleave_model():
    """Opt4 source sizing before RTL: eight-sector A-layout successor.

    r2 matrix-per-SM numerical calibration does not qualify this dispatcher,
    landing or gearbox. No skew/x-load overlap is credited before measurement.
    """
    per_stack = dict(schedule=42*16, class_progress=6*3+7+6,
        pc_ptr_delta=64, pc_next_j0_keep=32*13,
        pc_tag_delta=32*(16*6-4*3+4), landing_cdc_delta=32*64*6,
        release_control=8*(2+3+5+8-10), task_fence=9,
        gearbox_per_active_sm=2080+3*9+3*3+2)
    extra_bits = sum(v for k,v in per_stack.items() if k!='gearbox_per_active_sm') + 6*per_stack['gearbox_per_active_sm']
    return dict(default_off=True,layout='A: six interleaved w1/w3 row pairs per slot/stack',
        dies=96,stacks_per_die=4,active_sms_per_stack=6,unused_sms_per_stack=2,
        rows_per_matrix_per_die=24,rows_per_sm=12,k=5120,fp4_blocks_per_row=160,
        macs_per_accepted_sm_line=256,full_nc8_macs_per_line=2048,
        hbm_bytes_per_expert_stack=32640,pad_bytes=128,
        source_lines_per_expert_stack=255,pad_lines=1,sm_lines=288,
        pc_sector_bits=256,pcs_per_stack=32,landing_cap_sectors_per_sm_edge=4,
        gearbox_in_bits=1024,gearbox_out_bits=1088,gearbox_storage_bits=2080,
        gearbox_max_buffered_bytes=260,gearbox_min_latency_edges=1,
        gearbox_deadzone_fix=dict(buffer_delta_bytes=4,extra_ff_bits_per_stack=6*32,
            extra_mux_bits_per_stack=6*32*8,added_edges=0,
            reachable_stall="132 buffered <136 next output; original input threshold128",
            minimum_capacity_proof="count/input/output lengths multiples4; largest residue below136 is132;132+128=260"),
        gearbox_mux_2to1_bits_per_sm_estimate=2080*8,
        gearbox_logic_area_estimate_mm2_per_stack=6*2080*8*3*0.04374/1e6,
        area_note="state additions conservative before mapped census; unused legacy picker removal not credited",
        descriptors_per_pc=42,gu_chunks_per_expert=4,sectors_per_gu_chunk=8,w2_sectors=17,
        w2_chunks_per_expert=3,w2_chunk_sectors=[8,8,1],w2_chunk_j0=[32,40,48],
        w2_payload_qualification=False,
        w2_stack0_source_bytes=14*1224,w2_stack0_tail_bytes=136*128,
        w2_stack0_complete_counts=[10,10,0,0,29,29,29,29],
        w2_seam_repacking_added_sectors=0,w2_seam_store_bits=0,
        w2_mapping_obligation="retain greedy row ownership and ALL W2 bytes; complete-tail cfg counts replace legacy seams; padded transport is not numeric qualification",
        same_bank_class_rule='finish all GU or all W2 chunks of an expert before next same-set expert; no row thrash',
        dispatcher_emission_edges=42,wait_for_six_accepted_ids=True,
        extra_state_bits_per_stack=extra_bits,extra_state_detail=per_stack,
        extra_state_bits_per_die=4*extra_bits,extra_state_bits_system=96*4*extra_bits,
        register_area_floor_mm2_per_stack=extra_bits*0.2916/1e6,
        floorplan_slot_fit=None,logic_mux_route_area=None,
        boundary_capacity_qualified=False,clock_setup_uncertainty_ps=60,clock_hold_uncertainty_ps=25,
        clock_target_ghz=1.2,measured_start_delay_ps=None,token_latency_delta_us=None,
        start_delay_estimate_us_NOT_CREDITED=1.8,x_load_overlap_credit_us=0,
        whole_token_rate_qualified=False,ss_ff_closed=False)


def qwen_rom_stream4_fulltoken_measurement():
    """Actual plain-AR full36+HEAD run; cycles do not qualify a clock or MTP."""
    import hashlib
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    folder = root/'results/rtl/qwen_plain_ar_stream4_P8191_20261005'
    terminal = json.loads((folder/'terminal.json').read_text())
    source = json.loads((folder/'source.json').read_text())
    assert terminal['status']=='PASS' and terminal['process_exit']==0
    assert terminal['position']==8191 and terminal['mode']['stream4']
    assert not terminal['mode']['near_hbm_compute'] and not terminal['mode']['dspark']
    assert terminal['layer_x']['checks']==144 and terminal['layer_x']['mismatches']==0
    assert terminal['current_kv']['checks']==144 and terminal['current_kv']['mismatches']==0
    assert terminal['head']['exact_all_ranks'] and terminal['writeback']['drained']
    assert len(terminal['stages'])==37 and terminal['stages'][-1]['stage']=='head'
    pins={}
    for name,expected in terminal['evidence_sha256'].items():
        actual=hashlib.sha256((folder/name).read_bytes()).hexdigest()
        if actual!=expected: raise ValueError('Fulltoken evidence changed: '+name)
        pins[str((folder/name).relative_to(root))]=actual
    for name in ('source.json','terminal.json'):
        pins[str((folder/name).relative_to(root))]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
    stages=terminal['stages']
    stage_cycles=sum(x['cycles'] for x in stages)
    initial=stages[0]['start_cycle']
    gaps=sum(b['start_cycle']-a['end_cycle'] for a,b in zip(stages,stages[1:]))
    assert stage_cycles+initial+gaps==terminal['total_cycles']
    return dict(schema='qwen.rom.stream4.actual-fulltoken.v1',
        operating_mode='plain AR; STREAM4; NEAR_HBM0; DSparkOFF',
        actual_fulltoken_cycles=terminal['total_cycles'],actual_scope=terminal['scope'],
        position=8191,input_token=terminal['input_token'],next_token=terminal['head']['next_token'],
        winning_logit_bits=terminal['head']['winning_logit_bits'],ranks=4,layers=36,
        layer_FP32_checks=144,current_KV_checks=144,writeback_drained=True,process_exit=0,
        initial_edges=initial,stage_handoff_edges=gaps,measured_stage_cycles=stage_cycles,
        L0_cycles=stages[0]['cycles'],chained_layer_cycles=[x['cycles'] for x in stages[1:-1]],
        head_cycles=stages[-1]['cycles'],
        selected_top=source['top'],selected_parameters=source['parameters'],
        executable_sha256=terminal['executable_sha256'],source_sha256=pins,
        clock_basis='actual functional cycle measurement only; no selected full-system SS/FF clock qualification',
        qualified_latency_us=None,qualified_rate_tok_s=None,MTP_credit=None,
        physical_qualified=False,
        limitations='No full-vocabulary-logit dump; exact argmax/winning logit/Xnorm plus all36 decoder outputs and all144 currentKV checks. No HBM activation-provider or DS optimization credit transferred.')


def hbm_index_ds20_gather_bridge_model():
    """Correctness-only installed-pool proposal for two NORMAL W15 gathers.

    All arena accesses use the existing single DS20 SM0 LSU. A backing extent
    is leased from a real installer book; sizing bytes is not allocation.
    This supersedes paired/rank-major layout assumptions for this caller only.
    """
    import hashlib
    import json
    import math
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    codec_path='results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    codec=json.loads((root/codec_path).read_text())['SRAM_protection_candidate']
    base=2952
    # Distinct payload seats for split-write and joined-read: do not silently
    # rely on an unproved register-sharing lifetime. Lease table is separate.
    payload_extra=8*72
    lease_bits=8*72
    bridge_ff=base+payload_extra+lease_bits
    shared_ledger_ff=36*72  # protected prior accepted owners, union once
    ff=bridge_ff+shared_ledger_ff
    pairs=8+8+11+36+8
    mux_bits=512+337+273+64*8
    nand2=4096+32*12*4+512  # bounds/tag/kind/lease/control positive allowance
    buffers=math.ceil((ff-1)/7)
    body=ff*.2916+(ff+mux_bits)*.2+nand2*.08748+buffers*.10206+pairs*codec['pair_cell_body_um2']
    placement=2*body*1.05/1e6
    counts=dict(producer_score_ID_reads=12288,gather_score_ID_writes=12288,
        gather_checked_readbacks=12288,formatter_two_plane_reads=24576,
        sink_ID_writes=64,sink_checked_readbacks=64)
    sectors=sum(counts.values())
    assert sectors==61568
    # These are local held cuts, not queue wait or a PHY throughput claim.
    local_per_sector=1+1+2+3+1
    word_handoffs=sectors//2
    admission_edges=8+2+3+3 # actual descriptor load/encode/validation/quiet
    final_release_edges=1+1
    local_edges=sectors*local_per_sector+word_handoffs+admission_edges+final_release_edges
    adapter=hbm_index_ordered_adapter_model()
    # Actual two-plane formatter6 internal edges and merger load1 per8pairs;
    # checked reads already priced as MREQ below, not added again as9edges.
    remaining_adapter_edges=adapter['serial_selection_edges']+6144*(6+1)
    paths=[codec_path,'rtl/chip/ot_w15_coll_dma.sv','rtl/chip/ot_coll_topk_merge.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
        'rtl/gpu_sys/ot_gpu_mreq_cdc.sv','rtl/gpu_sys/ot_gpu_cdc_fifo.sv',
        'rtl/gpu_sys/ot_gpu_memsys.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv']
    return dict(schema='hbm.index.ds20.normal-gather.minimum.v1',default_enabled=False,
        reported_source_construction=dict(owner='Rawls15:30/15:31 EXEC-only integration',
            protected_bridge_CP_shared_rows=49,protected_prior_native_rows=36,
            bridge_CP_shared_FF=3528,prior_native_FF=2592,total_FF=6120,
            existing_model_ceiling_FF=ff,within_existing_budget=6120<=ff,
            additional_coding_permission=True,duplicate_borrower_allowed=False,
            actual_prior_accept_to_original_response_consume_required=True,
            quiet_edges=3,grant_edges=1,captured_release_edges=2,
            placement_ceiling_mm2=placement,parent_slot_reserved=False,
            counts_basis='owner source-construction report; not mapped physical proof',
            rate_credit=False),
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
        source_owner='Rawls enclosing bridges/lease; Sagan plane-major formatter/adapter; Confucius selector unchanged',
        selected_scope='correctness-only, no419cycle or acceleration credit',
        provider='DS20 SM0 c_req/c_rsp337/273 -> existing g_cdc[0] AW3 -> u_mem; one outstanding sector',
        new_memory_ports=0,new_backing_SRAM_bytes=0,
        source_clock_target_ns=1/1.2,memory_source_clock_ns=1,clock_qualified=False,
        arena_bytes=393216,result_sink_bytes=2048,required_existing_pool_bytes=395264,
        actual_base=None,installed_pool_lease=False,
        admission='Pinned installer allocated/free book with byte-range/alignment/overflow checks; arena/sink/input nonoverlap, all prior accepted SM/SU/W2 owners drained; actual lease, not fixture-ready',
        normal_gathers=[dict(mode=1,topk=0,GW=1,n_words512_per_rank=32,plane='score',destination_byte_offset=0),
            dict(mode=1,topk=0,GW=1,n_words512_per_rank=32,plane='ID',destination_byte_offset=196608)],
        layout='PLANE_MAJOR, byte-addressed: score=BASE+rank*2048+64*(pairword>>1); ID=BASE+196608+rank*2048+64*(pairword>>1); half=pairword&1. Explicit /64 conversion at512b formatter face.',
        formatter_layout_gate='Sagan09ed rank-major live component cannot attach unchanged; bounded plane-major opt-in correction/caller binding required, original source and live test preserved',
        state=dict(Rawls_base_protected_FF=base,second_direction_payload_FF=payload_extra,
            lease_FF_allowance=lease_bits,bridge_FF=bridge_ff,shared_borrower_ledger_FF=shared_ledger_ff,
            total_with_shared_ledger_once=ff,capacity512_words_each_direction=1,
            descriptor_CMD64_capacity=8,provider_outstanding=1),
        protection=dict(W6_pairs=pairs,encode_held_edges=2,decode_held_edges=3,
            source_body_mm2=pairs*codec['pair_cell_body_um2']/1e6,
            basis='retained W6 source; positive250ps local loading estimate, held2/3 target edges; physical timing unqualified'),
        area=dict(placement_at50pct_mm2=placement,required_component_outline_um=[400,400],
            required_envelope_mm2=.16,estimate_fits_required_envelope=placement<=.16,
            parent_slot_reserved=False,shared_ledger_charge_once=True,
            additional_to_existing_adapter_and_formatter=True,
            exclusions='actual loaded CTS/PG/long channels/protected backing implementation, codec cut/hold excess; no parent-space fit claim'),
        physical_boundary_tracks_lower_bound=512+512+337+273,
        actual_channel_capacity=None,
        accepted_sector_actions=counts,total_sector_actions=sectors,
        total_physical_bytes=sectors*32,provider_byte_throughput_floor_us=sectors/1000,
        source_VM_producer_reads_included=True,
        full_sector_writes='All32 strobes on each accepted256b sector; no partial-sector RMW required. Changed mask requires actual extra oldread/RMW pricing.',
        protocol=dict(local_edges_per_sector=local_per_sector,descriptor_admission_edges=admission_edges,
            two_sector_word_handoff_edges=1,final_visible_release_edges=final_release_edges,
            local_bridge_edges=local_edges,adapter_tree_assembly_load_edges=remaining_adapter_edges,
            CDC_request_receiver_edges_minimum=3,CDC_response_receiver_edges_minimum=3,
            CDC_positive_minimum_ns=3*1+3/1.2,
            provider_roundtrip_ns_planning_range=[45,500],
            CDC_included_in_roundtrip=True,
            range_condition='exclusive/drained path, held sinks accept; CL/REQ/RSP+ACT/PRE/one refresh and CDC included once; not a bound under refusal/competing traffic/fault',
            checked_readback='Each pair of write sectorACKs precedes corresponding two readbacks/checked owner capture; whole score+ID arena visible before ordered adapter; result sink similarly checked before publication/reverse',
            borrowed_lease_release='Last matched checked VMvisible + positive captured reverse; ACK/done alone never frees arena or requester debt'),
        serialized_provider_planning_us_range=[(sectors*45+(local_edges+remaining_adapter_edges)/1.2)/1000,
            (sectors*500+(local_edges+remaining_adapter_edges)/1.2)/1000],
        memory_and_codec_publication_cost_counted_once=True,
        previous_formatter_9edge_service_not_added_again=True,
        static_source_implementation_permitted=True,functional_integration_permitted_after_layout_and_real_lease=True,
        physical_build_admitted=False,adopted=False,token_gain_us=None,
        next='Rawls implements priced opt-in loadedbook/lease+bridges; Sagan plane-major actual formatter. Missing installer must fail closed; no free arena/base or port. Compose actual accepted service after implementation, not model rate adoption.')


def qwen_w12_common_advance_composition():
    """Literal selected-program clock cut and finite publication pre-RTL budget."""
    from qwen_w12_clock_composition import model
    return model(Path(__file__).resolve().parents[1])


def qwen_rom_stream4_periodic_provider_model():
    """Periodic controller causal paths and protected finite-ring sizing."""
    from qwen_rom_periodic_provider_registration import model
    return model(Path(__file__).resolve().parents[1])


def hbm_attn_m6h1_replication_model():
    """Price the measured F12/LA6 one-head successor in the existing HBM tile slot.

    Core area alone is a lower bound on a macro footprint: a failed lower-bound
    fit blocks contextual P&R without inventing routing or halo capacity.
    Existing composed attention work and arithmetic order are unchanged.
    """
    import ast
    import hashlib
    import json
    import re
    root = Path(__file__).resolve().parents[1]
    leaf_path = root / 'results/uarch/hbm_attn_m6h1_replication_20261005/inputs/physical.json'
    corner_path = leaf_path.with_name('corner_sta.json')
    die_path = leaf_path.with_name('die_inventory.py')
    macro_path = root / 'physical/hbm_fmax_attn/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1.lef'
    width, height = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', macro_path.read_text()).groups())
    leaf = json.loads(leaf_path.read_text())
    corner = json.loads(corner_path.read_text())
    # Read the existing die composition's literal inventory; importing its CLI
    # or substituting a new die/floorplan would be an unrelated design study.
    blocks = next(n.value for n in ast.parse(die_path.read_text()).body
                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'BLOCKS'
                                                     for t in n.targets))
    slot_mm2 = ast.literal_eval(next(k.value for k in blocks.keywords if k.arg == 'attn_tile'))[0]
    groups, tiles = 16, 64
    tile_core_floor_mm2 = groups * leaf['design']['core_area_um2'] / 1e6
    # Keep the prior m4 contract's 5um halo; this lower bound still excludes
    # shared channels, pin access and clock distribution.
    tile_macro_halo_floor_mm2 = groups * (width + 10) * (height + 10) / 1e6
    fits = tile_macro_halo_floor_mm2 <= slot_mm2
    return dict(schema='opentallas.hbm-attn-m6h1-replication.v1', selected=False,
                leaf_evidence_origin='b32d59700 results/rtl/hbm_accel_fmax_inventory_20261004/attn/routes/claude_r1_m6h1_u30',
                existing_composition='DEDICATED.attention; tools/hbm_accel_die_fp.py BLOCKS.attn_tile',
                source_configuration='ot_attn_hgrp_m6h1 H16/HG1/TD32/NBANK5/PWORDS2/FPL6/FML8/F121',
                replicas=dict(head_groups_per_tile=groups, engine_tiles=tiles, engine_groups=groups*tiles,
                              products_per_cycle_per_group=32, products_per_cycle_per_tile=512),
                boundaries=dict(input_bits=1618, input_replica_fanout=groups,
                                leaf_input_branches=1618*groups, output_bits=529,
                                load_word_bytes_per_cycle=128, packed_ib_bytes_per_cycle=72,
                                wrapper_mux_bits=0, wrapper_ff_bits=0, wrapper_added_cycles=0,
                                physical_buffer_area_um2=None, routing_capacity_tracks=None),
                latency=dict(core_cycles=8+7*6+6*2, core_cycles_m4=6+7*4+4*2,
                             delta_cycles_vs_m4=20, wrapper_delta_cycles=0,
                             serial_job_composition='existing ot_hdc_v41x_attn_s FPL6/FML8 depth model',
                             full_job_cycles=None, full_engine_closed=False),
                floorplan=dict(existing_slot_mm2=slot_mm2,
                               leaf_core_area_um2=leaf['design']['core_area_um2'],
                               leaf_cell_area_um2=leaf['design']['area_um2'],
                               tile_core_area_lower_bound_mm2=tile_core_floor_mm2,
                               measured_macro_size_um=[width, height], halo_um=[5, 5],
                               tile_macro_halo_area_lower_bound_mm2=tile_macro_halo_floor_mm2,
                               tile_cell_area_mm2=groups*leaf['design']['area_um2']/1e6,
                               required_over_slot_lower_bound=tile_macro_halo_floor_mm2/slot_mm2,
                               engine_core_area_lower_bound_mm2=tiles*tile_core_floor_mm2,
                               existing_engine_slot_mm2=tiles*slot_mm2,
                               halo_and_wiring_area_mm2=None, slot_fit=fits),
                leaf_signoff=dict(SS_setup_ps=corner['setup_ss']['worst_reg_to_reg_slack_ps'],
                                  FF_hold_ps=corner['hold_ff']['worst_slack_ps'],
                                  closes_signoff=corner['closes_signoff'],
                                  false_path_io=leaf['design']['false_path_io'],
                                  period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25),
                contextual_pnr_admitted=False,
                blocker='Measured macro and existing halo exceed composed tile slot' if not fits
                        else 'Actual macro footprint, routing capacity and parent interface closure required',
                adopted=False, gain_claim=None,
                source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (leaf_path, corner_path, die_path, macro_path)})
