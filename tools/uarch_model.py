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



def hbm_smh_result_valid_model(columns=8, row_bits=12):
    """Size the optional south-front result qualification before RTL changes."""
    if columns < 1 or row_bits < 1:
        raise ValueError("positive shape required")
    return dict(schema="opentallas.smh-result-valid.v1", opt_in_default=False,
        master="ot_hbm_accel_smh_front_s", columns=columns,
        macs_per_cycle=0, memory_bytes_per_cycle=0,
        existing_result_bits_per_cycle=columns*(34+row_bits),
        added_boundary_bits_per_cycle=0, added_data_registers=0,
        qualification_and_gates=columns,
        reduction_gate_upper_bound=4*columns, replicas=1,
        mux_demux_cost=0, control_fanout_max=2,
        local_routing_tracks_upper_bound=3*columns,
        floorplan_slot_fit="existing south-front result landing; <=5*columns small gates, physical route required",
        added_cycles=0, token_latency_added_ns=0.0,
        correctness="fault only with own-column valid; row retires only with all columns valid; any partial valid vector raises fault",
        physical_gate="refresh full NC8 front_s timing/DRC with RESULT_VALID=1; unchanged BE/tile closures do not qualify it")


def hbm_visibility_fence_pin_return_model():
    """Default-off output registers with registered accepted-beat credit return."""
    from tools.hbm_fence_pin_return_model import model
    return model()


def hbm_collective_port2_tiles_model():
    """Pair two independently hardened protected halves without seam traffic."""
    from tools.hbm_coll_port2_tiles_model import model
    return model()
<<<<<<< HEAD
=======


def qwen_ctrl_protected_model():
    """Two retained PC controllers with zero-cycle fail-closed qualification."""
    from uarch_model_qwen_ctrl_protected import model
    return model()


def qwen_ctrl_shift_queue_model():
    """Exact oldest-first write queue with stored onehot bank identities."""
    from uarch_model_qwen_ctrl_shift import model
    return model()


def qwen_ctrl_registered_head_model():
    """Exact zero-cycle PC FIFO-head and bank-eligibility closure candidate."""
    from uarch_model_qwen_ctrl_head import model
    return model()


def qwen_ctrl_pc_closure_model():
    """Default-off full-feature Qwen r14 command cut; unchanged JEDEC clock."""
    from uarch_model_qwen_ctrl_pc import model
    return model()


def qwen_final_pc_closure_composition(decode=False, controller=False, mapped_decode=False):
    """Compose each new pipeline once against the common pinned r21 baseline.

    Gross added edges are conservative until connected-token measurement exists;
    no baseline CDC or controller latency is subtracted or credited. Per-leaf
    percentages must never be added: select edge terms, sum, recompute rate.
    """
    import math
    base = 216713
    terms = {}
    if decode and mapped_decode:
        raise ValueError('mapped decoder replaces decoder; select one')
    if mapped_decode:
        terms['mapped_landing_decoder'] = qwen_kvc_mapped_pc_model()['added_token_cycles']
    if decode:
        terms['landing_decoder'] = 36 * qwen_kvc_decode_pc_model()['latency']['pipeline_edges']
    if controller:
        hbmedges = qwen_ctrl_pc_closure_model()['latency']['minimum_request_to_phy_added_edges']
        terms['controller_boundary'] = 36 * math.ceil(hbmedges * 1024 / (2500 / 3))
    extra = sum(terms.values())
    return dict(default_OFF=True, adopted=False, physical_closed=False,
        baseline_record='results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json',
        baseline_cycles=base, selected_delta_cycles=terms, added_cycles=extra,
        total_cycles=base + extra, clock_hz=1.2e9,
        ar_tokens_per_second=1.2e9/(base + extra),
        rate_cost_pct=100*(1-base/(base + extra)),
        pricing_basis=('gross eight-edge mapped decoder' if mapped_decode else 'gross four-edge decoder') + ' plus selected three-edge HBM wrapper (ceil to four core edges), each per36 layers; no overlap or removal credit',
        exact_connected_latency_measured=False,
        adoption_gate='connected service must measure actual delta vs pinned baseline, pass exactness and all real master SS/FF/die-context timing',
        excluded_unpriced='row arbitration, global descriptor fence, payload/tag/landing storage, die relay stages')


def qwen_kvc_mapped_pc_model():
    """Full-width exact option-M mapper followed by landing decoder."""
    from uarch_model_qwen_kvc_mapped import model
    return model()


def s81_bf_root_phase_model():
    """Clock-only successor of pinned BF HALF=1; no adoption or timing credit."""
    return {
        'baseline_source': '61c1cf23054e140ea7b4371bb931b82b2383e9a7',
        'default_off': True, 'adopted': False, 'physical_closed': False,
        'scope': 'full native BF pair HALF=1, dedicated phase-clock root branch',
        'added_cycles': 0, 'added_macs_per_cycle': 0,
        'memory_bytes_per_cycle_delta': 0, 'boundary_bits_per_cycle_delta': 0,
        'added_cells': {'INVx1_ASAP7_75t_R': 2},
        'additional_phase_registers': 0, 'replicas': 1,
        'fanout': {'first_inverter': 1, 'second_inverter': 1},
        'added_internal_clock_nets': 2,
        'routing': {'local_branch_max_span_um': 100, 'tracks_added': 2,
                    'capacity_and_actual_wire_length': 'must measure after placement'},
        'area_um2': 0.08748,
        'area_status': 'two actual ASAP7 INVx1 cells; incremental CTS/repair area pending',
        'area_capacity_record': 'physical/s81_bf_root_phase/area_capacity.json',
        'slot_um': [1002.888, 190.08],
        'baseline_stdcell_area_um2': 67096.1,
        'usable_stdcell_site_area_um2': 145342.231168,
        'headroom_at_55pct_um2': 12842.0396624,
        'slot_fit': 'fits at <55% even excluding all four ROM halos; verify actual legalization',
        'latency': 'zero logical delta from HALF baseline; existing half-rate cost retained',
        'physical_obligations': [
            'keep phase register and both branch inverters within 100um of root ICG',
            'generated divide-by-1 clock with propagated physical insertion',
            'retain phase-to-ICG setup/hold and all phase-to-output crossings',
            'fresh-session SS/FF >=15ps, DRC0, exact production clock protocol'],
    }


def hbm_sm_command_model(*, hops=8, depth=1, replicas=32):
    """Native-record command transport with conservative retirement ordering."""
    from hbm_sm_command_model import model
    return model(hops=hops, depth=depth, replicas=replicas)


def hbm_result_relay_stage_model():
    """Size all physical result-relay replicas before stage implementation."""
    from hbm_result_relay_model import hbm_result_relay_stage_model as model
    return model()


def hbm_smh_front_s_hold_model():
    """Price measured-endpoint hold repair without relaxing constraints."""
    from hbm_smh_front_s_hold_model import model
    return model()


def hbm_smh_front_s_fifo_model():
    """Price the registered-nonempty SM request-sink candidate."""
    from hbm_smh_front_s_fifo_model import model
    return model()


def hbm_smh_tile_headroom_model():
    """Measured tile-area alternatives, preserving existing BE masters."""
    from hbm_smh_tile_headroom_model import model
    return model()


def hbm_ha2_sender_capture_model():
    """Default-off HA2 capture candidate with measured finite-flight bound."""
    from ha2_sender_capture_model import model
    return model()


def hbm_su_divider_halfpair_model(serial_divides=1):
    """Prebuild bound for two alternating exact DIV31 cores, one beat per fast edge.

    This is a closure candidate, not a measured speed/area claim. The c12
    composition already carries DDIV through M1, sigmoid/SiLU, softplus and
    EGATE; selecting DDIV=64 prices each dependent divide at the same rounding
    point. ROM designs do not select this HBM lane implementation.
    """
    assert isinstance(serial_divides, int) and serial_divides >= 0
    fast_ghz = 1.2
    depth = 64
    old_full_area_um2 = 32015.784  # full31 d773c1033 mapped full-shape route
    wrapper_ff = 2 * (65 + 34 + 34 + 1 + 2)
    # Bound the extra pair by duplicating the ENTIRE measured full lane, not
    # merely its two dividers; therefore no unmeasured leaf area subtraction.
    cell_upper = 2 * old_full_area_um2 + wrapper_ff * .37908
    corridor_um = 32
    side_um = 400
    tracks = int(corridor_um / .072)  # conservative >=72nm track pitch
    return dict(schema='opentallas.hbm.su.divider_halfpair.prebuild.v1',
        selected=False, adopted=False, default_parameter=dict(DDIV=21),
        proposed_parameter=dict(DDIV=depth), MACs_per_cycle=0,
        divides_per_fast_cycle=1, compute_intensity_divides_per_payload_byte=1/12,
        memory_ports=dict(new_ports=0, bytes_per_fast_cycle=0),
        boundary_bits_per_fast_cycle=dict(input=65, output=34, new_external_bits=0),
        replicas=dict(cores_per_divider=2, divider_instances_per_full_lane=2,
            input_capture_fanout=2, output_mux='34 parallel 2:1 muxes per divider',
            demux='alternating physical clock gates; every input captured once',
            added_wrapper_ff_bound=wrapper_ff),
        clocks=dict(fast_ghz=fast_ghz, each_core_ghz=fast_ghz/2,
            duty='one 50-percent-fast-clock high pulse every two fast periods',
            phase0_master_edges=[1,2,5], phase1_master_edges=[3,4,7],
            crossings='one fast input register; opposite-bank capture then output register',
            setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            no_relaxation_of_fast_crossings=True),
        area=dict(measured_full31_um2=old_full_area_um2,
            conservative_cell_upper_um2=cell_upper,
            source='EPYC3 full31 d773c1033 physical.json; not a divider-only estimate',
            proposed_slot_um=[side_um,side_um], reserved_corridor_um=corridor_um,
            planned_utilization_with_corridor=(cell_upper+corridor_um*side_um)/side_um**2,
            target_utilization=.55, old_slot_um=[346.008,347.736],
            old_slot_fit_with_corridor=False, proposed_slot_fit=(cell_upper+corridor_um*side_um)/side_um**2 <= .55),
        routing=dict(bank_boundary_tracks_needed=2*(65+34)+2,
            conservative_channel_track_capacity=tracks,
            track_pitch_assumption_um=.072, requires_physical_validation=True),
        latency=dict(divider_fast_cycles=depth, core_slow_cycles=31,
            extra_vs_DDIV21=depth-21, extra_vs_DDIV31=depth-31,
            serial_divides=serial_divides,
            serial_chain_added_fast_cycles=serial_divides*(depth-21),
            serial_chain_added_ns=serial_divides*(depth-21)/fast_ghz,
            M1_and_SFU_both_divide_extra_cycles=2*(depth-21),
            composed_by='tools/hbm_su_c12.py:set_c12 DDIV=64; controller H_MD/D_SIG/D_SP/D_EG',
            per_design_selection={'Qwen3-8B ROM':False,'DeepSeek-V4.1 ROM':False,
                'Qwen3-8B HBM':'conditional DDIV64','DeepSeek-V4.1 HBM':'conditional DDIV64'}),
        adoption_gates=['small divider transaction scoreboard incl faults/reset/bubbles and negative',
            'c12 controller/lane exact composition at DDIV64',
            'full-lane physical shape SS>=15ps/FF>=15ps/DRC0 with generated clocks',
            'expanded slot installed in die context and latency ledger recomposed'])


def qwen_core_separate_load_model(*, non_end_instructions, replicas=4):
    """Split instruction issue from the next LOAD; no arithmetic or new state.

    Count must come from the program being measured; a component count is not
    a complete token schedule. Intrinsic bubbles are priced separately from altered readiness sampling.
    External time-varying stalls can add further cycles; no token bound is claimed.
    """
    if not isinstance(non_end_instructions, int) or non_end_instructions < 0:
        raise ValueError('non_end_instructions must be a nonnegative integer')
    if not isinstance(replicas, int) or replicas < 1:
        raise ValueError('replicas must be positive')
    return dict(default_enabled=False, adopted=False, physical_signoff=False,
        MACs_per_cycle=0, new_memory_ports=0, new_boundary_bits=0,
        added_register_bits=0, replicas=replicas, new_mux_inputs=0,
        intrinsic_bubble_cycles=non_end_instructions,
        intrinsic_bubble_ns=non_end_instructions/1.2,
        token_latency_delta_upper_cycles=None,
        token_latency_delta_upper_ns=None,
        token_composition_status="requires actual readiness trace; no universal bound",
        measured_component_64=dict(no_stall_delta_cycles=64, periodic_ready_delta_cycles=71),
        minimum_issue_interval_cycles=2, clock_hz=1200000000,
        setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        added_register_cell_area_um2=0,
        measured_predecessor_cell_area_um2=8277.71,
        measured_predecessor_core_area_um2=24642.1,
        new_external_routing_tracks=0, original_slot_unchanged=True,
        successor_slot_fit_measured=False,
        load_fanout='Existing NEXT and descriptor captures; issue cone removed from LOAD enable',
        measured_failure='SU go to kvd_tiles D: SS -155.059418ps, 1578 failing endpoints from SU go and122 from ME taken',
        remaining_obligations=['Actual selected token instruction count',
          'Issue-side consumers and output-pin timing', 'Input hold at actual die budget',
          'Full controller route at SS/FF and exact ordered-instruction gate'])


def qwen_core_separate_load_schedule(contexts=(1, 8192)):
    """Compose the candidate in the current analytical TP4 controller schedule.

    No deployed-program identity or other uncomposed physical interface delay
    is inferred from this analytical program. Exact fullshape RTL gates remain
    separate; this is the model's before/after issue-spacing price.
    """
    import hashlib
    import json
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    import hdc_isa as I
    import hdc_program as P
    shape = dict(Q.Q, NH=8, KV=2, FF=Q.Q['FF']//4, V=Q.Q['V']//4)
    old = I.SU_WIDTH
    try:
        I.SU_WIDTH = 64
        program = P.build_program(Q.capped_layout(6144, None, shape))
    finally:
        I.SU_WIDTH = old
    rows = []
    for context in contexts:
        cycles = []
        for gap in (1, 2):
            k = dict(T.K, me_lat=T.K['me_lat'] + QWEN_SS['me_lat_extra'] + Q.SCALE_MUL_CYCLES,
                     red_lv=7, seq_gap=gap)
            _, total = T.simulate(program, context-1, groups=6144,
                dyn_shape=dict(H=Q.Q['H'], half=Q.Q['HD']//2, HD=Q.Q['HD']), su_width=64, k=k)
            cycles.append(total)
        rows.append(dict(context=context, baseline_cycles=cycles[0], candidate_cycles=cycles[1],
                         delta_cycles=cycles[1]-cycles[0], delta_ns=(cycles[1]-cycles[0])/1.2))
    return dict(adopted=False, scope='current analytical TP4 program; deployed identity not inferred',
                instruction_count=len(program), rows=rows,
                program_sha256=hashlib.sha256(json.dumps(program, sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest())


def qwen_embedding_ingress_island_model(address_bits=18):
    """Move existing embedding capture FFs into a separately hardened pin island.

    Measured 860d3eb7c input holds fail by32.38/36.34ps; inserting another
    same-clock input stage would not repair those first endpoints. This sizes
    the existing capture state as its own small clock-tree/floorplan element.
    No shorter insertion or closed timing is assumed before measurement.
    """
    if address_bits not in (12, 18):
        raise ValueError('Only actual code12 and scale18 ingress shapes qualify')
    rails = 2 * (address_bits + 2)
    # Exact pinned ASAP7 SS areas: DFFHQN0.2916, DFFASRHQN0.37908,
    # BUFx2 0.0729, BUFx12f0.26244, BUFx24 0.4374 square micrometres.
    ff_area = 2*address_bits*0.2916 + 4*0.37908
    reserved_hold_buffers = 6*rails
    reserved_output_buffers = rails
    area = ff_area + reserved_hold_buffers*0.0729 + rails*0.26244 + 4*0.4374
    frame, core = 15.12, 10.8
    return dict(schema='opentallas.qwen.embedding_ingress_island.v1', adopted=False,
        address_bits=address_bits, MACs_per_cycle=0, compute_intensity_MAC_per_byte=0,
        memory_port_bytes_per_cycle=0,
        communication_intensity='One existing address/valid/credit capture every rising edge; no queue or added protocol',
        boundary_bits_per_cycle=dict(inputs=address_bits+2,outputs=rails,clock=1,reset=1),
        state=dict(moved_existing_FFs=rails,added_FFs=0,primary_shadow_separate=True),
        replica_count=2374 if address_bits==12 else 3,
        mux_demux_fanout=dict(new_muxes=0,new_demuxes=0,clock_sinks=rails,
                             input_fanout=2,output_obligation_fF=80),
        area=dict(FF_um2=ff_area,reserved_hold_buffers=reserved_hold_buffers,
                  reserved_output_buffers=reserved_output_buffers,clock_buffer_reserve=4,
                  reserved_cell_um2=area,frame_um=[frame,frame],core_um=[core,core],
                  utilisation_ceiling=.60,planned_utilisation=area/core**2,
                  slot_fit=area<=.60*core**2,
                  leaf_slot='Inside existing logic strip above ROM: scale y70 and code y80; no die-area credit until legal placement'),
        routing=dict(pin_pitch_um=.096,output_tracks=rails,usable_face_um=core,
                     face_track_capacity=int(core/.096),planned_face_fit=rails<=int(core/.096),
                     final_parent_wire_target_um=100,parent_pin_binding='OPEN until real island view'),
        clock_plan=dict(domain='stream1p2',period_ps=833.333,setup_uncertainty_ps=60,
                        hold_uncertainty_ps=25,input_transition_ps=150,
                        local_clock_tree='One separately hardened island; capture FFs moved out of payload leaf CTS',
                        interface_budget='Unchanged die 166.667ps outside plus150ps inter-region and50ps hold skew; reference actual valid_q clock arrival',
                        measured_insertion_required=True,exceptions_added=[]),
        latency=dict(moved_capture_cycles=1,added_cycles=0,leaf_cycles=7,II=2,
                     composed_root_bound_cycles=19,shared_service_cycles=801),
        remaining=['Island SS/FF+15ps/DRC0 under real IO',
                   'Bind island LEF/LIB/clock and pin placement inside full leaf',
                   'Full leaf reset-removal and reg-to-reg hold remain independently open'],
        physical_closed=False,rate_credit=0)


def s81_pq_r128_expanded_model():
    """Area-only successor of measured d0178820d R128/PQ screen, not a parent die."""
    side = 550.368
    core_w, core_h = 546.048, 545.94  # ASAP7 0.054um site / 0.270um row snapping
    area = core_w * core_h
    baseline_cells = 148012.0
    bw = sum((1, 6, 3, 1, 1, 2, 1, 8, 3, 2, 256, 10, 256, 10, 3, 3, 1, 3, 4, 32, 1024))
    input_bits = 1+6+3+4*19+2+64*32+128*69+1
    output_bits = 3+19+128*(1+19+32)+bw+2
    return dict(schema='opentallas.s81.pq_r128_expanded.v1', adopted=False,
        scope='Standalone screen PHW6 SAW8 KMAX256 R128 PQ1; ROM register models, not production parent',
        source_commit='d0178820d', replica_count=1, production_replicas=None,
        compute=dict(MACs_per_cycle_delta=0, arithmetic_unchanged=True,
                     intensity_delta=0, note='Control/quantization spine; no added matrix MAC engine'),
        memory=dict(vector_read_bytes_per_cycle=256,vector_write_bytes_per_cycle_max=512,
                    phase_ROM_bytes_per_cycle=16,stream_ROM_bytes_per_cycle=6,
                    bytes_per_cycle_delta=0),
        boundary=dict(functional_input_bits_per_cycle=input_bits,functional_output_bits_per_cycle=output_bits,
                      return_bits_per_cycle=128*69,fixture_ROM_write_bits=74,
                      clock_reset_bits=2,bits_per_cycle_delta=0),
        fanout=dict(added_muxes=0,added_demuxes=0,added_replicas=0,added_clock_sinks=0,
                    observed_baseline_clock_buffers=16885,observed_baseline_clock_inverters=5454,
                    note='New CTS insertion, repair count and energy must be measured'),
        geometry=dict(die_um=[side,side],core_box_um=[2.16,2.16,548.208,548.10],
                      core_area_um2=area,baseline_die_area_um2=230400,
                      die_area_delta_um2=side**2-230400,
                      measured_baseline_cell_area_um2=baseline_cells,
                      measured_baseline_core_area_um2=226149,
                      baseline_utilisation=baseline_cells/226149,
                      projected_same_cell_utilisation=baseline_cells/area,
                      repair_reserve_to_55pct_um2=.55*area-baseline_cells,
                      repair_reserve_to_60pct_um2=.60*area-baseline_cells,
                      slot_fit=baseline_cells<.55*area,parent_slot_assigned=False),
        routing=dict(added_logical_tracks=0,baseline_ports_including_fixture=19357,
                     M4_vertical_pitch_um=.036,M5_horizontal_pitch_um=.048,
                     raw_edge_track_capacity=2*int(core_w/.036)+2*int(core_h/.048),
                     note='Raw capacity before power/keepouts; legal pin assignment/congestion requires route; no parent corridor claimed'),
        timing=dict(route_period_ps=770,signoff_period_ps=833.333,setup_uncertainty_ps=60,
                    hold_uncertainty_ps=25,minimum_SS_FF_slack_ps=15,required_DRC=0,
                    IO_max_ps=250,IO_min_ps=-50,
                    input_clock_reference='q_go/CLK measured per corner',
                    output_clock_reference='o_ready/CLK measured per corner',
                    constraints_changed=False),
        latency=dict(added_cycles=0,token_delta_ns=0,qualification='Source-identical logical schedule; no frequency or performance credit before closure'),
        energy=dict(added_logic=0,physical_wire_clock_energy_delta=None,measurement_required=True),
        physical_closed=False,remaining=['Fresh SS/FF timing including input and R2R hold',
        'DRC, pin legality, real clock insertion, area and energy',
        'Separate production parent mapping/ROM macro binding and released phase count'])


def qwen_core_kv_boundary_model(*, sw=64, replicas=4, kv_write_instructions=108):
    """Bank the existing KV write-history reduction without shifting its epoch.

    Raw per-lane writes are grouped into eight-lane ORs before capture. The
    bank registers replace the existing history vector; its any-write predicate
    and following history bit remain cycle-identical. Flush uses the captured
    bank bits and an equally delayed SU-idle bit, shifting that level one cycle.
    """
    if sw < 8 or sw % 8:raise ValueError('SW must be a multiple of eight')
    banks=sw//8
    return dict(default_enabled=False,adopted=False,physical_signoff=False,
        MACs_per_cycle=0,new_memory_ports=0,new_boundary_bits=0,replicas=replicas,
        old_history_registers=sw,new_history_and_idle_registers=banks+1,
        register_delta=banks+1-sw,input_reduction_fanin=8,post_capture_reduction_fanin=banks,
        new_external_routing_tracks=0,original_slot_unchanged=True,
        predicate_epoch_delta_cycles=0,flush_latency_delta_cycles=1,
        analytical_program_kv_write_instructions=kv_write_instructions,
        continuous_ready_token_delta_upper_cycles=kv_write_instructions,
        stall_sensitive_token_delta_cycles=None,
        program_scope='Current analytical TP4 program833 instructions; no deployed program identity claim',
        modeled_remaining_obligations=['Registered flush with actual vector bridge/RMW adapter',
          'Arrival-side hold margin','ME write-enable boundary packet/gating separation',
          'SS/FF actual interface timing'],clock_hz=1200000000,
        setup_uncertainty_ps=60,hold_uncertainty_ps=25)


def hbm_smh_front_s_hold_model():
    """Full front_s zero-cycle boundary-delay budget; fresh corner closure pending."""
    from hbm_smh_front_s_hold_model import model
    return model()


def qwen_rom_vm_ingress_capture_candidate():
    """Existing-seat raw-ME qualification candidate; physical/parent join unqualified."""
    from qwen_vm_rom_ingress_model import model
    return model()


def qwen_rom_vm_request_normalization_candidate():
    """Full-shape default-off request normalizer inventory; physical join unqualified."""
    from qwen_rom_vm_request_normalizer_model import model
    return model()


def qwen_embedding_padded_ingress_model(address_bits=18):
    """Price ten physical BUFx2 stages on each ingress pin before building.

    Endpoint delta estimates are retained in embedding_pad10_20261007 evidence.
    They replace only measured predecessor buffer delays; no signoff credit.
    """
    m=qwen_embedding_ingress_island_model(address_bits)
    count=10*(address_bits+3)
    m['schema']='opentallas.qwen.embedding_padded_ingress.v1'
    m['input_padding']=dict(stages_per_input=10,input_bits=address_bits+3,
        fixed_buffer_cells=count,cell_type='BUFx2_ASAP7_75t_R',
        fixed_buffer_area_um2=count*.0729,reset_included=True,
        new_cycle_latency=0,physical_retention_required=True)
    # Fixed cells consume part of the existing six-per-rail hold-cell reserve.
    assert count<=m['area']['reserved_hold_buffers']
    m['area']['remaining_hold_buffer_reserve']=m['area']['reserved_hold_buffers']-count
    m['mux_demux_fanout']['input_fanout']=1
    m['replicated_fixed_buffer_area_um2']=count*.0729*m['replica_count']
    m['timing_estimate']=dict(min_guarded_SS_ps=59.8785642953 if address_bits==12 else 56.7648613579,
        min_guarded_FF_ps=19.5207286031 if address_bits==12 else 21.5235240262,
        analytical_guard_SS_ps=30,analytical_guard_FF_ps=15,
        constraints_changed=False,setup_hold_closed=False,
        limitations='Per-endpoint NLDM delta, below-table load extrapolation; placement/clock and routed delays remain unqualified')
    m['remaining'].insert(0,'Verify all ten fixed buffer stages per input in synthesis and final routed netlists')
    return m


def s81_pq_return_delay_model(regions, selected_chain_counts):
    """Size identity-function input delay stations on the unchanged standalone screen.

    Counts must come from matched SS/FF front-return endpoint inventories. Cell
    characterization is a prebuild bound; closure is measured after routing.
    """
    if regions not in (16, 128):
        raise ValueError('Only measured R16/R128 screen vehicles are supported')
    counts = {int(k): int(v) for k, v in selected_chain_counts.items()}
    if any(k not in (3, 4) or v < 0 for k, v in counts.items()):
        raise ValueError('Only characterized three/four-HB4 chains are supported')
    endpoints = sum(counts.values())
    if endpoints > 69*regions:
        raise ValueError('Selected endpoints exceed actual return boundary width')
    cells = sum(k*v for k, v in counts.items())
    old_cells = 89698 if regions == 16 else 148012
    core_area = 196407 if regions == 16 else s81_pq_r128_expanded_model()['geometry']['core_area_um2']
    new_area = cells*.10206
    return dict(schema='opentallas.s81.pq_return_delay.v1', adopted=False, physical_closed=False,
        scope='Physical-only identity buffer station on d017 standalone registered screen; no production parent claim',
        regions=regions, chain_counts=counts, selected_endpoints=endpoints,
        MACs_per_cycle_delta=0,compute_intensity_delta=0,memory_bytes_per_cycle_delta=0,
        boundary_bits_per_cycle=69*regions,boundary_bits_per_cycle_delta=0,
        replica_count=endpoints, mux_count=0,demux_count=0,
        fanout=dict(each_HB4_output=1,new_clock_sinks=0,source_buffer_loading='Must preserve original input buffer and check new first-cell capacitance'),
        area=dict(cell='HB4xp67_ASAP7_75t_R',cell_count=cells,cell_area_um2=.10206,
                  added_cell_um2=new_area,baseline_measured_cell_um2=old_cells,
                  core_area_um2=core_area,projected_utilisation=(old_cells+new_area)/core_area,
                  headroom_to_55pct_um2=.55*core_area-old_cells-new_area,
                  fits_55pct=old_cells+new_area<=.55*core_area,
                  parent_slot_assigned=False),
        routing=dict(new_internal_nets=cells,new_external_tracks=0,per_link_wire_target_um=5,
                     M3_cap_fF_per_um=.156,characterized_extra_cap_fF_per_net=.78,
                     local_chain_tracks_per_endpoint=1,minimum_track_pitch_um=.036,
                     minimum_station_track_capacity=int(5/.036),
                     condition='Keep each chain beside its capture pin; actual legalization, congestion and wire RC must pass'),
        clock=dict(period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                   added_clock_domains=0,added_clock_exceptions=0,reference_clock_unchanged=True),
        latency=dict(added_cycles=0,token_delta_ns=0,II_unchanged=True,qualification='Identity cells only; actual timing and topology must qualify'),
        characterization=dict(three_HB4_min_FF_hold_gain_ps=117.875009,
                              three_HB4_max_SS_setup_cost_ps=339.820038,
                              four_HB4_min_FF_hold_gain_ps=156.516676,
                              four_HB4_max_SS_setup_cost_ps=454.61435,
                              input_slew_ps=[0,5,20],wire_cap_fF=[0,.2,.78],
                              three_HB4_original_cap_max_fF=5.75,three_HB4_retained_cap_delta_limit_fF=.78,
                              three_HB4_retained_wire_source='results/uarch/s81_pq_delay_chain_20261007/retained_wire_sweep/record.json',
                              source='results/uarch/s81_pq_delay_chain_20261007/loaded_sweep/record.json',
                              measured_route=False),
        remaining=['Matched original SS/FF endpoint table and source hashes',
                   'Real buffer topology positive/negative gate and source identity',
                   'Routed SS/FF+15ps DRC0 including R2R holds outside return station',
                   'Actual wire/clock energy and full production parent integration'])


def ha2_truecredit_parent_clock_model():
    """Price the actual ring-delay/launch-register closure candidate; not adopted."""
    from tools.ha2_truecredit_parent_clock_model import model
    return model()


def qwen_core_vm_raw_boundary_model(*, groups=48, lanes=16, aw=24):
    """Move existing ME strobes' enable qualification into owned VM capture.

    Raw mode cannot be adopted standalone: source_me_wanted must be the
    original enable before any VM lease/native_tick feedback, and the actual
    capture collar must qualify all ME/MX lanes at the existing CAP epoch.
    """
    packet=1+aw+lanes+lanes*32
    return dict(default_enabled=False,adopted=False,raw_mode_requires_capture_collar=True,
        MACs_per_cycle=0,new_memory_ports=0,new_boundary_payload_bits=0,required_new_control_ports=2,
        lease_binding_cost="Original-intent output and direct ME-lease input; one effective-enable AND plus fanout to existing execution/acceptance loads. This binding is not implemented by raw-write transform.",
        source_register_delta=0,owned_capture_register_delta=0,
        source_native_cycle_delta=0,replicas=4,me_groups=groups,lanes_per_group=lanes,
        moved_enable_terms=groups+1,me_write_seats=groups*lanes+lanes,
        source_enable='Original pre-lease supply/idle/wake enable; never post-admission lease',
        immutable_epoch='Captured enable/address/mask/data are held through checked ACK; current me enable cannot requalify them',
        fallback=dict(packet_bits_per_group=packet,me_only_register_bits=groups*packet,register_bits_including_mx=(groups+1)*packet,
                      register_cell_area_floor_um2_including_mx=(groups+1)*packet*0.2916,write_visibility_delta_cycles=1),
        physical_status='Core and actual ingress collar must both close SS/FF with real interface budgets',
        final_clock_enrollment='Parent wrapper and collective peers must share checked native epoch; not supplied by this boundary transform')


def hbm_su_installed_span_model():
    """Price checked published-span scalar reads before endpoint construction."""
    from tools.hbm_su_installed_span_model import model
    return model()


def qwen_core_meif_idle_capture_model(*, nw=18, aw=24, replicas=4):
    """Remove return-status cone from the existing MEIF payload capture mux.

    Speculate only while no ME command is pending; hold the complete packet
    until its enabled engine edge. Both issue epoch and payload acceptance stay
    unchanged. Active consumer uses must remain go-qualified.
    """
    bits=3*nw+13*aw+13
    return dict(default_enabled=False,adopted=False,physical_signoff=False,
        mechanism='Existing payload registers capture decoded input while !me_gop; freeze while pending',
        MACs_per_cycle=0,new_memory_ports=0,new_memory_bytes_per_cycle=0,
        added_boundary_bits_per_cycle=0,added_routing_tracks=0,replicas=replicas,
        payload_register_bits=bits,register_delta=0,mux_register_delta=0,
        removed_enable_cone='SU take/status/ready to combined ME go to payload capture mux',
        new_enable_cone='Local registered me_gop inversion to existing payload mux',
        area_delta_first_order_um2=0,original_floorplan_slot_unchanged=True,
        native_cycle_delta_per_instruction=0,token_latency_delta_cycles=0,
        speculative_switching='Payload may update on other instruction epochs when no ME command is pending; no claim of energy saving',
        exactness_obligations=['Full controller ME/SU accepted payload equality under source-enable stalls','Freeze packet over pending go','Actual instruction broadcast samples packet with matching go','Negative unconditional capture must fail'],
        inherited_open_physical_obligations=['ME write ingress collar','prog_q and other input minimum delay','Clock output insertion/phase contract','SS/FF setup/hold +15ps and DRC0'])


def qwen_ctrl_write_ledger_model():
    """Source-bound native controller ownership/cancellation composition."""
    from uarch_model_qwen_ctrl_write_ledger import qwen_ctrl_write_ledger_model as impl
    return impl()


def qwen_ctrl_write_service_model():
    """Source-bound native controller ownership/cancellation composition."""
    from uarch_model_qwen_ctrl_write_service import qwen_ctrl_write_service_model as impl
    return impl()


def qwen_ctrl_write_cancel_model():
    """Source-bound native controller ownership/cancellation composition."""
    from uarch_model_qwen_ctrl_write_cancel import qwen_ctrl_write_cancel_model as impl
    return impl()


def qwen_ctrl_write_cancel_service_model():
    """Source-bound native controller ownership/cancellation composition."""
    from uarch_model_qwen_ctrl_write_cancel import qwen_ctrl_write_cancel_service_model as impl
    return impl()



def hbm_su_div64_closure_successor_model():
    """Price the gather-stage successor against immutable failed route evidence."""
    from tools.hbm_su_div64_closure_successor_model import model
    return model()

def ha2_truecredit_protection_model():
    """Size encoded HA2 storage and explicit unresolved physical obligations."""
    from tools.ha2_truecredit_protection_model import model
    return model()




def hbm_norm_split_model(**kwargs):
    """Size the inherited G8/G16 norm hard groups and price exposed hops."""
    from tools.hbm_norm_split_model import model
    return model(**kwargs)


def hbm_indexer_die_interface_model(**kwargs):
    """Unified full-shape interface and finite-credit sizing, no closure credit."""
    from tools.hbm_indexer_r25i_model import hbm_indexer_die_interface_model as model
    return model(**kwargs)


def hbm_control_robustness_model():
    """HBM reset sequencer and SRAM/transport fault aggregation before build."""
    from tools.hbm_control_robustness_model import model
    return model()


def hbm_write_source_transport_model():
    """Source bits stay with accepted write until its actual PC completion."""
    from tools.hbm_write_source_transport_model import model
    return model()


def dsrom_markov_row_model(**kwargs):
    """Released256-term DSpark second dot and separate logit add; no rate credit."""
    from dsrom_markov_model import model
    return model(**kwargs)


def qwen_embedding_hbm_closure_model(strip_side_um=600.0):
    """Price the static-row HBM successor, including measured serial latency and pin-fit obligations."""
    from tools.qwen_embedding_hbm_model import model
    return model(strip_side_um=strip_side_um)


def hbm_coll_port_interior_model():
    """Full-shape SRAM port placement successor; no closure credit."""
    from tools.hbm_coll_port_interior_model import model
    return model()



def dsrom_head_input_staging_model(**kwargs):
    """Aligned hbglue-to-A input transport; proposed stages require routed qualification."""
    from dsrom_head_input_staging_model import model
    return model(**kwargs)


def qwen_kv_merge_skid_model(depth=8):
    """Finite Q4 landing queue, row round trip and exposed credit throttling."""
    from uarch_model_qwen_kv_skid import model
    return model(depth, dff_um2=DFF_UM2)

def qwen_su_kv624_model():
    """Q3 full lane-address validation and exact on-grid FP8 packet."""
    from uarch_model_qwen_kv_packet import model
    return model(dff_um2=DFF_UM2)

def qwen_system_physical_model():
    """Q1 CROM48 and Q2 full-context control sizing, no speculative route credit."""
    from uarch_qwen_system_physical import model
    return model()

def hbm_dskv_shadow_sram_model(*, utilisation=0.55, macro_capture_cycles=1):
    """F04/R3 prebuild successor: 8 x 17 sectors; no qualification credit."""
    if not 0 < utilisation <= .60 or macro_capture_cycles < 1:
        raise ValueError('conservative slot/capture contract required')
    macro_area = 94.824 * 41.040
    # One transaction at a time. Request/response credit returned only on consume.
    write_cycles = 4  # accept, encode, macro write, response consume
    read_cycles = macro_capture_cycles + 5  # accept, issue, capture, decoder2, consume
    return dict(scope='prebuild estimate; opt-in, unqualified',
        arithmetic=dict(MACs_per_cycle=0, compute_intensity=0),
        memory=dict(logical_sectors=136, logical_bytes=4352, data_macros=2,
            macro_depth=128, macro_width_bits=256, allocated_bytes=8192,
            SECDED_sidecar_bits=136*10, valid_dualrail_bits=136*2,
            bytes_per_cycle_read=32, bytes_per_cycle_write=32),
        boundaries=dict(request_bits=1+3+5+256, response_bits=256+1,
            storage_tracks_required=2*(256+256+256+7+7+2),
            track_capacity='pending real slot routing, no fit credit'),
        replication=dict(storage_pairs=1, bank_decode_fanout=2,
            data_mux_inputs=2, write_demux_outputs=2),
        floorplan=dict(macro_area_um2=2*macro_area,
            minimum_macro_only_slot_um2=2*macro_area/utilisation,
            logic_area='pending measured synthesis; cannot claim slot fit',
            utilisation=utilisation),
        latency=dict(write_cycles=write_cycles, read_cycles=read_cycles,
            preload_cycles_upper_bound=17*(write_cycles+2),
            key_merge_2sector_cycles_upper_bound=2*(read_cycles+write_cycles+5),
            key_merge_3sector_cycles_upper_bound=3*(read_cycles+write_cycles+5),
            upper_added_cycles_per_token_8_index_layers=8*3*(read_cycles+write_cycles+5),
            upper_added_ns_per_token_1p2GHz=8*3*(read_cycles+write_cycles+5)/1.2,
            note='full key golden mapping unchanged; stalls add actual consumer delay'))

def hbm_dskv_shadow_sram_hub_model(*, RI_AW=5, utilisation=.55):
    """Full R3 route vehicle includes FIFO, assembler, storage, mapper and credits."""
    storage=hbm_dskv_shadow_sram_model(utilisation=utilisation)
    ff_payload=(1<<RI_AW)*257+4352+4352+259+4*292+3*256
    return dict(storage=storage, replicas_per_die=1,
        payload_FF_inventory=ff_payload,
        control_and_sidecar_FF_upper_estimate=5000,
        descriptor_guard=dict(layer_bound=40, index_slot_bound=8, die_bound=96,
            complete_shadow_dualrail_bits=16, extra_cycles=0,
            rule="reject reserved kind, bounds and uninitialized owner key before any SRAM/HBM write"),
        FF_total_upper_estimate=ff_payload+5000,
        inventory_note="upper allocation includes SECDED pipeline data/check registers, 1360 check FFs, 272 valid FFs, CDC counts, controller rails and address/control registers",
        boundary_bits=dict(ri=258,ri_credit=1,sector_links=4*292,
            service_count_returns=4*16,die_identity=7,visibility_counts=33),
        floorplan_status='two real macros plus measured full hub logic required; no fit/closure claim',
        latency=storage['latency'],
        measured_component=dict(source='results/rtl/dskv_wb_sram_gate_20261008/dskv-wb-sram-gate-20261008-r4.json', clock_ps=833, key_updates=64, sectors_per_key=3, posted_sectors=218, max_row_cycles_with_bench_stalls=41, max_preload_cycles=69, stall_cycles=340, physical_credit=False),
        adoption='full hub SS/FF timing/DRC and golden row/shadow/credit/fence gate pending')

def hbm_index_selector_capture_model(read_latency=2, slot_width_um=1399.656, slot_height_um=844.56, score_fifo_aw=7):
    """Opt-in macro capture: unchanged issue width, finite existing reservations.

    One capture stage isolates 405/545 ps TT macro clk->q from selector mux.
    Each sweep adds one drain cycle; finite reservation recycling can add
    stalls. Use measured stage deltas before publishing a token rate.
    """
    if read_latency not in (1, 2):
        raise ValueError("selector read latency must be 1 or 2")
    if score_fifo_aw not in (6, 7):
        raise ValueError("score FIFO sizing is LA6 historical or LA7 native deep-credit variant")
    extra = read_latency - 1
    added_landing_bits = 4 * ((1 << score_fifo_aw) - 64) * 609
    # Existing unified-model proxies: actual DFFHQN area, assumed 0.2um2 mux bit.
    # Each added FIFO bit needs a write-enable mux and one added read-tree node.
    landing_ff_floor_um2 = added_landing_bits * .2916
    landing_mux_proxy_um2 = 2 * added_landing_bits * .2
    capture_ff_floor_um2 = 4 * (592 + 68 + 8) * extra * .2916
    macro_names = [(256, 12), (1024, 4)]
    macro_area = 0.0
    for depth, count in macro_names:
        name = f"ot_sram_1r1w_{depth}x256_m2_r2c2"
        record = json.loads((ROOT / "physical/asap7_memory_macros" / name / (name + ".json")).read_text())
        macro_area += count * record["area"]["macro_area_um2"]
    slot_area = slot_width_um * slot_height_um
    published_cell_estimate = 400000.0 + landing_ff_floor_um2 + landing_mux_proxy_um2 + capture_ff_floor_um2  # physical/hbm_accel_die_views/index/DESIGN.md, estimate only
    return dict(read_latency_cycles=read_latency, extra_cycles_per_sweep=extra,
        token_extra_cycles_formula="sum(measured_selector_cycle_deltas per token stage)",
        additional_credit_recycle_cycles=extra,
        nominal_drain_cycles_formula="(gc_sweeps + pass2_sweeps + pass3_sweeps + emit_sweeps) * extra_cycles_per_sweep",
        token_gain_claim=False, macs_per_cycle=0, replicas=4,
        memory=dict(score_fifo_address_bits=score_fifo_aw, score_credits=1 << score_fifo_aw,
                    score_landing_bits=4*(1 << score_fifo_aw)*609,
                    added_score_landing_bits=added_landing_bits,
                    topk_bytes_per_cycle=74, candidate_bytes_per_cycle=8.5,
                    topk_bits_per_cycle=592, candidate_bits_per_cycle=68),
        capture_payload_bits=4*(592+68)*extra, capture_metadata_bits=4*4*2*extra,
        mux_demux_added=0, cross_boundary_bits_added=0, routing_tracks_added=0,
        reservations=dict(gc_lines=8, output_beats=4,
                          policy="issue counts outstanding until pack exit/output enqueue; capture included"),
        area=dict(capture_flops=4*(592+68+8)*extra,
                  capture_cell_um2="unmapped; DFF floor only until synthesis", capture_ff_floor_um2=capture_ff_floor_um2,
                  added_landing_ff_floor_um2=landing_ff_floor_um2,
                  added_landing_mux_proxy_um2=landing_mux_proxy_um2,
                  mux_proxy_basis="ASSUMED 0.2um2 per mux bit; one write-enable and one read-tree node per added FIFO bit",
                  standard_cell_estimate_um2=published_cell_estimate,
                  macro_area_um2=macro_area, macro_count=16,
                  proposed_slot_width_um=slot_width_um, proposed_slot_height_um=slot_height_um,
                  proposed_slot_area_um2=slot_area,
                  estimated_total_fill=(published_cell_estimate+macro_area)/slot_area,
                  cell_capacity_at_55pct_um2=.55*(slot_area-macro_area),
                  capture_and_repair_reserve_at_55pct_um2=.55*(slot_area-macro_area)-published_cell_estimate,
                  estimate_fits=published_cell_estimate<.55*(slot_area-macro_area),
                  floorplan_fit="R25I prototype from hbm_wiring; real pins and mapped capture area still required"),
        latency_clock_ns=0.8333333333333334,
        physical_status="candidate; macro output must terminate at capture D pins")

def dsrom_wfc_prompt_pipe_model():
    """Approved DR5 SOURCE/token read extra cycle, physical margin and ownership."""
    from dsrom_wfc_prompt_pipe_model import model
    return model()

def dsrom_wfc_token_hard_model():
    """Size the four-edge token lookup before RTL; no physical credit."""
    entry_bits = 43
    added_bits = 36 + 8 * (entry_bits + 1) + 2 * 26
    return dict(schema='opentallas.dsrom.wfc-token-hard.v1', adopted=False,
        default_enabled=False, clock_ghz=1.2, macs_per_cycle=0,
        compute_intensity=0, communication_intensity='one request/response per cycle',
        memory_ports=dict(token_read_bytes_per_cycle=8*44/8,
                          draft_write_bytes_per_cycle=5*44/8),
        boundaries_bits_per_cycle=dict(draft=513, request=36, response=22, config=55),
        routing_tracks=dict(draft=2052, request=144, response=88, config=220),
        replicas=dict(stores=1, user_read_banks=8),
        mux=dict(per_user_entries=16, final_users=8, data_width=44,
                 request_address_fanout_banks=8, draft_write_slots=5),
        area=dict(predecessor_measured_cells_um2=7145,
                  added_register_bits_upper=added_bits,
                  added_cells_proxy_um2=added_bits*2,
                  outline_um=[162,151.2],
                  estimated_fill=(7145+added_bits*2)/(162*151.2),
                  proxy_is_not_physical_measurement=True),
        latency=dict(response_edges=4, original_edges=1, r3_edges=2,
                     added_cycles_original=3, added_cycles_r3=2,
                     added_ns_original=3/1.2, initiation_interval_cycles=1,
                     draft_visibility_edges=2,
                     source_matching_metadata_required=True),
        measured_latency=dict(original_ingress_edges=0, original_read_response_edges=1,
                              r3_ingress_edges=0, r3_read_response_edges=2,
                              hard_ingress_edges=1, hard_read_response_edges=3,
                              hard_total_edges=4, delta_original_edges=3,
                              delta_r3_edges=2,
                              evidence='results/rtl/dsrom_wfc_token_hard_20261009/'
                                       'baselines_5d64607cd/summary.json'),
        finite_flow=dict(token_inflight_slots=4, initiation_interval_cycles=1,
                         fixed_response_no_backpressure=True,
                         source_return_queue_entries=4,
                         source_metadata_extra_stages_required=2),
        failure_path=dict(start='f_pr[25]', end='u_tok.pr_q[16]',
            report='mtp_wfc_tok_a_e1c20dfb6_tc/physical_artifacts/6_finish.rpt',
            historical_tt_setup_ps=-478.67),
        qualification='Remote exact/mutant minimum gate, matched SOURCE integration, '
                      'and own TT/FF/DRC route with SS sensitivity remain required')

def s81_ctrl_die_model(column_width_um, role='layer', stage_handoffs=121):
    """RQ-DSC1/2 native controller shell sizing before build; closure credit is zero."""
    if column_width_um <= 0 or role not in ('layer', 'source', 'head'):
        raise ValueError('positive controller slot width and a native role required')
    area_mm2 = 0.15
    return dict(schema='opentallas.uarch.s81-ctrl-die.v1', enabled_default=False,
        macs_per_cycle=0, compute_intensity=0, clock_ghz=1.2, replicas_per_die=1,
        area_mm2_nominal=area_mm2, slot_width_um=column_width_um,
        slot_height_um=area_mm2*1e6/column_width_um,
        program_bits=128*28, sequencer_queue_bits=12*4*84, engine_queue_bits=12*8*84,
        command_boundary_bits_per_cycle=12*85, done_boundary_bits_per_cycle=12*9,
        message_bits_per_cycle_each_direction=515,
        vm_port_bytes_per_cycle=dict(write=64, read=64),
        vm_write_control_bits_per_cycle=15, vm_read_control_bits_per_cycle=15,
        nominal_endpoint_tracks=dict(command=1020, done=108, message_each_direction=515,
                                     vm_write=527, vm_read_request=15, vm_read_response=512),
        routing_capacity_verdict='PENDING_FLOORPLAN_PIN_AND_CHANNEL_CHECK',
        fanout='12 independent descriptor lanes; engine completion supplies credit',
        stage_handoff_added_cycles=3, stage_handoffs=stage_handoffs,
        ar_added_cycles=3*stage_handoffs+(1 if role == 'head' else 0),
        engine_cdc_added_cycles='PENDING_REAL_ADAPTER',
        physical_qualification='PENDING', evidence_scope='native-shell-contract and nominal reservation')

def hbm_expert_steering_model():
    """Full-shape L1 descriptor and tagged result steering, default off."""
    from hbm_expert_steering_model import model
    return model()

def hbm_link_retry_pipeline_model(payload_bits=545, seq_bits=12, session_bits=24,
                                  depth=512, ports=8):
    """Closure successor: four-edge paced admission and pipelined feedback."""
    record = payload_bits + seq_bits + session_bits
    chunks = (record + 255) // 256
    macros = ((chunks * 266 + 255) // 256) * (depth // 128)
    return dict(design_applicability={'Qwen3-8B ROM': False,
        'DeepSeek-V4.1 ROM': False, 'Qwen3-8B HBM': True,
        'DeepSeek-V4.1 HBM': True}, macs_per_cycle=0,
        payload_bits=payload_bits, record_bits=record, depth=depth,
        replicas=ports, admission_interval_cycles=4,
        normal_forward_added_cycles_min=1, normal_forward_added_cycles_max=4,
        forward_bits_per_cycle=record/4,
        reverse_bits_per_cycle=seq_bits+session_bits+1,
        SRAM_port_bytes_per_cycle_peak=record/8,
        SRAM_port_bytes_per_cycle_normal_mean=record/32,
        SRAM_macros_per_port=macros, SRAM_macros_per_die=macros*ports,
        SRAM_area_per_port_um2=macros*3891.57696,
        pathfinding_slot_um=[690,460], slot_area_per_die_um2=690*460*ports,
        macro_utilization=macros*3891.57696/(690*460),
        payload_register_bits_per_port=2*payload_bits,
        new_stage_protection='32-bit payload parity groups, tag/control parity and classified-control complements; detect/poison',
        parity_register_bits_per_port=2*((payload_bits+31)//32)+8,
        feedback_latency_cycles=4, replay_SRAM_read_latency_cycles=4,
        serial_token_cost='For N framed records on a contended hop, '
            'service is 4*N stream edges plus 1..4 entry edges; '
            'actual hop/FEC/ACK round trip must be composed before adoption.',
        routing_tracks_required=record*2+seq_bits+session_bits+1,
        routing_capacity_checked=False, actual_pin_budget_known=False,
        physical_qualified=False, default_enabled=False)


def hbm_link_retry_model(payload_bits=551, seq_bits=12, session_bits=16,
                         ports=8, rtt_cycles=None, depth=None):
    """RQ-HS7 go-back-N sizing. RTT must include real relay/FEC/ACK path.

    An unspecified physical RTT cannot qualify replay capacity or rate.
    Storage includes the full unchanged TU record and transaction sequence.
    SRAM macro and SECDED read pipeline are integration obligations.
    """
    if min(payload_bits, seq_bits, session_bits, ports) < 1:
        raise ValueError("positive dimensions required")
    if rtt_cycles is not None and rtt_cycles < 1:
        raise ValueError("positive RTT required")
    required = None if rtt_cycles is None else 2*rtt_cycles
    if depth is None and required is not None:
        depth = 1 << (required-1).bit_length()
    if depth is not None and (depth < 2 or depth & (depth-1) or depth >= 2**(seq_bits-1)):
        raise ValueError("power-of-two replay depth below half sequence space required")
    return dict(candidate="HBM_LINK_RETRY", default_enabled=False,
        payload_bits=payload_bits, sequence_bits=seq_bits, session_bits=session_bits,
        replicas=ports, macs_per_cycle=0, compute_intensity=0,
        communication_bits_per_cycle=payload_bits,
        memory_write_bits_per_cycle=payload_bits, memory_read_bits_per_cycle=payload_bits,
        forward_bits_per_cycle=payload_bits+seq_bits+session_bits,
        reverse_bits_per_cycle=seq_bits+session_bits+1,
        replay_depth=depth, required_replay_depth=required, rtt_cycles=rtt_cycles,
        replay_payload_bits_per_die=None if depth is None else ports*depth*payload_bits,
        routing_tracks_needed=payload_bits+2*seq_bits+2*session_bits+1,
        channel_capacity=None, floorplan_slot_fit=None, area_um2=None,
        fault_free_added_cycles=0, replay_mux_inputs=2, descriptor_fanout=ports,
        capacity_qualified=required is not None and depth is not None and depth>=required,
        physical_qualified=False, sram_secded_integrated=False,
        composed_token_latency_added_cycles=0,
        adoption="OPEN: physical RTT, protected SRAM, die ports, SS/FF route required")

def hbm_link_replay_sram_model(payload_bits=551, seq_bits=12, session_bits=16,
                              depth=512, ports=8):
    """Protected replay successor: payload AND transaction identity in SRAM.

    Physical macro inventory is real 128x256 ASAP7 1R1W; registered write
    pins and read capture, followed by the shipped two-edge SECDED decoder.
    Decoder/mux timing remains an SS/FF qualification obligation.
    """
    if depth < 128 or depth % 128 or depth & (depth-1):
        raise ValueError("power-of-two depth >=128 required")
    record_bits=payload_bits+seq_bits+session_bits
    chunks=math.ceil(record_bits/256)
    coded_bits=chunks*266
    macros_per_bank=math.ceil(coded_bits/256)
    banks=depth//128
    macro_count=banks*macros_per_bank*ports
    macro_area=3891.57696 # pinned physical/asap7_memory_macros/128x256 JSON
    return dict(candidate="HBM_LINK_REPLAY_SECDED_SRAM",default_enabled=False,
        payload_bits=payload_bits,identity_bits=seq_bits+session_bits,record_bits=record_bits,
        secded_chunks=chunks,coded_bits=coded_bits,macros_per_bank=macros_per_bank,
        banks_per_port=banks,macros_per_port=banks*macros_per_bank,ports=ports,
        macro_count=macro_count,macro_area_um2=macro_area,
        SRAM_area_um2=macro_count*macro_area,slot_reservation_um2=macro_count*macro_area/0.55,
        decoder_logic_area_um2=None,slot_fit=None,physical_qualified=False,
        macs_per_cycle=0,write_records_per_cycle=1,read_records_per_cycle=1,
        write_encoded_bits_per_cycle=coded_bits,read_encoded_bits_per_cycle=coded_bits,
        routing_tracks_needed=2*record_bits+2*math.ceil(math.log2(depth))+2,
        channel_capacity=None,read_bank_mux_inputs=banks,
        replicas=dict(encoder=chunks*ports,decoder=chunks*ports),
        write_commit_edges=1,read_response_edges=4,minimum_write_read_request_gap_edges=2,
        fault_free_forward_added_edges=0,replay_initial_read_edges=6,
        replay_scheduler_outstanding_reads=1, replay_head_records=1,
        replay_steady_records_per_cycle=1/7,
        token_fault_free_added_cycles=0,
        adoption="OPEN: replay scheduler, credits, SS/FF and die integration")


def hbm_ta15_clock_boundary_model(link_ports=9, stages=3):
    """Unified entry for before-build TA15 digital clock/reset boundary sizing."""
    from tools.hbm_ta15_clock_boundary_model import hbm_ta15_clock_boundary_model as model
    return model(link_ports, stages)

def hbm_indexer_r25i_physical_model():
    from hbm_indexer_r25i_model import hbm_indexer_r25i_physical_model as impl
    return impl()


def qwen_q5_landing_model():
    from uarch_qwen_q5_landing_model import model
    return model()


def qwen_r25_su_dispatch_contract_model():
    """Full p4 finite-window consumer and four-quarter native dispatch sizing."""
    try:
        from tools.qwen_r25_su_dispatch_model import model
    except ModuleNotFoundError:
        from qwen_r25_su_dispatch_model import model
    return model()


def dsrom_mtp_p2_transport_model():
    """Individual expert FP32 returns preserve the released golden sum order."""
    from dsrom_mtp_p2_transport_model import model
    return model()


def hbm_loader_native_service_model():
    """Finite deployment ingress; unresolved transport never earns token credit."""
    from hbm_loader_native_service_model import model
    result = model()
    result['design_applicability'] = {
        'Qwen3-8B ROM': False, 'DeepSeek-V4.1 ROM': False,
        'Qwen3-8B HBM': True, 'DeepSeek-V4.1 HBM': True,
    }
    result['physical_measurement'] = dict(
        source_commit='05c0a8a00', per_PC_FF=316,
        per_PC_routed_cell_area_um2=395.862, PCs_per_stack=32,
        stacks_per_die=4, per_die_lease_cell_area_um2=395.862*32*4,
        evidence='results/hbm_loader_native_pc_pathfinding_r2_20261009',
        scope='generic IO primitive pathfinding; actual loaded pins and clock unresolved',
        SS_setup_ps=-207.1, TT_setup_ps=58.1045, FF_hold_ps=34.03,
        headline_closed=False)
    result['unresolved_composition'] = dict(
        dispatcher='actual landing coordinates, registered relay hops and channel occupancy required',
        writes='actual external producer/link pending fence and configured capacity inventory required',
        floorplan='station reservations must include existing PC/line logic occupancy',
        token_delta='runtime native access not admitted or credited until measured arbitration is composed')
    return result


def hbm_native_index_control_model():
    """Dynamic frame metadata and retained native source lease, before build."""
    from tools.hbm_native_index_control_model import model
    return model()


def qwen_kv_row_model():
    """Full32-PC option-M row mechanism and merged-word prepaid credits."""
    from uarch_model_qwen_kv_row import model
    return model(DFF_UM2)


def s81_native_ingest_contract_model():
    """Actual host sector and perPC source-owned native controller service."""
    from s81_native_ingest_model import model
    return model()


def qwen_dspark_native_model():
    from uarch_qwen_dspark_native_model import model
    return model()


def dsrom_hc_mean_capture_model():
    """Mandatory full-rank L37/38/39 INPUT residual means and seed framing."""
    from tools.dsrom_hc_mean_capture_model import model
    return model()


def dsrom_hc_input_reader_model():
    """Finite native VM reader; port ownership and H mapping remain explicit."""
    from tools.dsrom_hc_mean_capture_model import input_reader_model
    return input_reader_model()


def hbm_native_token_join_model(qwen=False):
    """Native Qwen/DeepSeek real two-half AR token runtime; qualification pending."""
    from hbm_native_token_join_model import model
    return model(qwen=qwen)


def hbm_native_mtp_stop_model(tw=17):
    """Full-context native MTP stop/ready successor with composed ACK cycles."""
    from hbm_native_mtp_stop_model import model
    return model(tw=tw)


def s81_control_transport_model(**kwargs):
    """Real native queue/CDC, control lane and HC/seed adapters before build."""
    from tools.s81_ctrl.control_transport_model import model
    return model(**kwargs)


def dsrom_hc_seed_join_model():
    """Protected head join of three independently placed input-layer means."""
    from tools.dsrom_hc_mean_capture_model import seed_join_model
    return seed_join_model()


def qwen_r25_su_quarter_contract_model():
    """Real N256/M64 c12 quarters and finite native service calendar."""
    from tools.qwen_r25_su_quarter_model import model
    return model()


def hbm_production_clock_control_model():
    from hbm_production_clock_control_model import model
    return model()


def hbm_indexer_service_transport_model():
    from hbm_indexer_r25i_model import hbm_indexer_service_transport_model as impl
    return impl()


def hbm_coll_capture_placement_model():
    """Same full collective port with measured legal direct SRAM captures."""
    from tools.hbm_coll_capture_placement_model import model
    return model()


def dsrom_mtp_seed_qs5f_candidate():
    """Before-build sizing for minimum seed gate on exact selected native QS5f.

    Parent baseline aligned experiment is historical QX9; this candidate has
    exact pinnedfa27 source/params and does not inherit a closedphysical view.
    """
    return dict(adopted=False,source_commit='fa27bd60819f9bf61483d5605a02837fe6a34088',
        native_master='ot_v41_rom_elem_q_qxpq_w10',NB=2,MTP=1,EARLY=1,FAST=1,PP=1,
        QTIMING_FIX=1,QPIPE=1,QP_XS=1,QP_CAP=0,QP_P1=1,QP_CSAM=10,QZ=1,QZ_NS=8,QZ_NE=4,QY=1,QX=10,PQ=1,QW=0,QM=5,QS=5,
        native_physical_closed=False,known_physical_FF_hold_ps=-111.3,
        element_scope='one native NB2 pair, two releasedrows fullK15360, four sequentialaligned phases and LAT8actualFP32joins',
        segment_K=[4096,4096,4096,3072],MACs=30720,MACs_per_issue_cycle=64,
        weight_bytes_per_issue_cycle=64,ROM_boundary_bits_per_issue_cycle=548,
        activation=dict(quantisers=2,blocks32=480,words_per_cycle=64,VM_bytes_per_cycle=256,buffer_bytes=15960),
        collector=dict(root_storage_bits=256,FP32_add_operations=6,adder_instances=1,adder_LAT=8,minimum_serial_join_cycles=48),
        partial_phase_fmt_fp32=[True,True],final_projection_rounding='BF16 once after balanced full root, before main_norm',
        config_cycles=100,phase_quiet_fence_cycles=128,measured_complete_column_cycles=None,
        PQ_shadow_replay=dict(words_per_phase=17,phases=4,QM5_read_stages=2,
            input_pipeline_fence_cycles=6,post_replay_settle_fence_cycles=6,
            go_condition='registered sh_free && !walking, then settle fence',
            load_condition='registered bank_free && sh_free',
            replay_latency_overlap='none in this minimum serial bench; actual status wait is included in measured complete cycles'),
        latency_contribution='measure actualselectedminimum; wholematrix, HCmean, main_norm, rankgather and6position sharing remainunqualified',
        storage=dict(logical8192x32B_rowbanks_per_rank=75,nativeNB2pairs_per_rank=38,physical4096macros_per_rank=152),
        qualification=dict(whole_field_descriptor=False,parallel_engine_count=False,six_positions=False,new_collector_physical_closed=False))


def hbm_index_global_order_model():
    """Actual TP96 candidate packets and finite canonical gather before build."""
    from tools.hbm_index_global_order_model import model
    return model()


def hbm_index_global_order_scan_model():
    """Canonical static ID scan with actual sparse protected rank heads."""
    from tools.hbm_index_global_order_model import model
    return model(static_scan=True)


def hbm_collective_vm_publication_model(words=4096,lanes=16,quarters=4):
    """Actual req337/rsp273 VM lease, fully published before TU indexed reads.

    Source compiler d5225192c graph all_reduce_o/down: FP32 4096 words,
    q1024 disjoint word ranges. No native TU descriptor opcode exists yet.
    Read tags have QID2/sequence14; no in-band fault, only separate abort.
    """
    if words!=4096 or lanes!=16 or quarters!=4:
        raise ValueError('only authoritative full4096/fourquarter contract sized')
    flits=words//lanes;sectors=words//8
    # Two parity-sector masters for each of two native injector read lanes.
    # Each word256+seq12+epoch24 occupies two266-bit codes in three macros.
    macros=2*2*(flits//128)*3
    return dict(candidate='HBM_FULL_QUARTER_VM_PUBLICATION',default_enabled=False,
        adopted=False,MACs_per_cycle=0,FP32_words=words,FW=512,PFMAX=flits,
        quarter_words=1024,rank_order=[0,1,2,3],VM_base_word=233472,
        VM_read_requests=sectors,VM_request_bits=337,VM_response_bits=273,
        max_outstanding_requests=1,request_tag='QID2 + sequence14',
        actual_Qwen_owner_bits=74,legacy_owner_default_bits=73,
        response_fault_field=False,external_fault_requires_abort=True,
        requested_bytes_per_sector=32,total_load_bytes=words*4,
        publication_overlap_credit=0,minimum_load_cycles=2*sectors+2,
        actual_load_cycles='sum measured request-ready and matched response latency for512 sectors +2write visibility edges',
        injector_read_lanes=2,bytes_per_cycle_per_injector=64,
        injector_request_to_response_edges=4,mutable_payload_protection='real SRAM SECDED on data+flitindex+24bit session',
        protected_SRAM_masters=4,real_SRAM_macros=macros,
        SRAM_macro_area_um2=macros*3891.57696,
        SRAM_area_reservation_at_55_percent_um2=macros*3891.57696/.55,
        forward_VM_boundary_bits=quarters*337,reverse_VM_boundary_bits=quarters*273,
        producer_mux='one registered selected QID; held request, one outstanding, no same-cycle long ready chain',
        fanout='write each sector to both read-lane replicas; no broadcast payload to fourquarters',
        lease='allproducer writeACK and same-sector visibility under matching owner/op/PC/query precede publication start; stable readlease until TU release',
        native_endpoint_successor='PFMAX256, indexed response fouredges after request; currentPFMAX64/samecycleinjdata cannot bind',
        integration_open=['TU descriptor ISA/header and production SM publication grant','VM read arbiter and source fault transport','actual full shape native endpoint queue/relay inventory','descriptor/control-state protection and warm-abort drain','SS/FF15ps DRC0 with actual FF capture budgets'],physical_qualified=False)


def hbm_collective_native_publication_endpoint_model():
    """Source-sized successor of fixedPF64/same-edge injector native parent."""
    return dict(candidate='HBM_NATIVE_FULL4096_INDEXED_RETURN',default_enabled=False,
        adopted=False,physical_qualified=False,MACs_per_cycle=0,FW=512,PWT=545,
        PFMAX=256,INJ=2,NPT=8,RXAW=8,QAW=7,TXAW=6,
        partial_result_delivery_queue_depth=128,
        native_source_landing_credit_window=64,
        protected_RX_landing_depth=64,
        queue_storage='new128-depth source successor; same3 real256x256 macros/queue, halfrowsused; original64-only contract preserved',
        synchronous_packet_queues=25,synchronous_packet_macros=75,
        additional_protected_landing_queues=8,additional_landing_macros=24,
        publication=hbm_collective_vm_publication_model(),
        injector_response_edges=4,added_request_to_hub_capture_edges=5,
        injector_metadata_pipeline_register_bits=2*5*(32+1+1),
        geometric_WSTG=22,protected_flight_instances=16,
        geometric_flight_flit_seats=16*22,
        geometric_flight_payload_bits=16*22*545,
        RTT_cycles=None,RTT_qualified=False,
        relay_basis='currentR25I max430-budget22 stages; uniform22 pathfinding, actual perport FF stations and ACK RTT not yet bound',
        token_delta='512 actualVM sector reads before go +5sourcecore edges vs historicalsameedgeinjdata +8PHYingressedges perhop; compose actual measured stagecalendar, no invented overlap',
        mutable_control='new valid/tag pipeline parity detects corruption before hub capture; broader native descriptor/control qualification open',
        integration_open=['actual TUdescriptor/compiler production grant','actual perport PHYretry and separate control transport','actual source landing credit64 vs PHYcandidate256 must compose','source-sized full256 flit exactness and allnegative controls','real macro placement and SS/FF15ps DRC0'])


def hbm_native_mtp_transaction_model():
    """Full native command ownership/reset epoch join model."""
    from hbm_native_mtp_transaction_model import model
    return model()


def hbm_native_mtp_emit_model(depth=8):
    """Finite native emitted-token sink model."""
    from hbm_native_mtp_emit_model import model
    return model(depth)


def hbm_w2_phase_seat_model(no=2):
    """Full-shaped default-off W2 phase locality and held-delay seats."""
    from w2_phase_seat_model import model
    return model(no)


def mtp_ring_dyn_model():
    """Price one-position ring addressing independently of multi-token slot state."""
    return json.loads((ROOT / 'physical/mtp_ring_dyn/model.json').read_text())


def hgi_attention_row_sources_model():
    """HGI-1 G12 ordered-row frontend; arithmetic and gather engines unchanged."""
    return dict(schema='hgi.att-row-sources.v1', enable_default=False,
        model_before_build=True, MACs_per_cycle=0, arithmetic_order='B then C; existing tile chunk8/tree unchanged',
        full_shape=dict(Qwen_rows=8192, maximum_linear_rows=1048576, effective_count_bits=21, DS_window_rows=128, DS_selected_rows=2048, row_index_bits=20),
        replicas=4, placement='one frontend per HBM stack, upstream of existing gather reader',
        ports=dict(command_bits=85, selected_id_bits_per_cycle=32, request_bits_per_cycle=43,
                   selected_ID_bytes_per_cycle=4, HBM_payload_bytes_per_cycle=0),
        boundary_bits_per_cycle=43, mux_cost='one B/C row-index mux; no payload mux',
        fanout='local command registers only, 4 independent replicas',
        latency_cycles=dict(command_to_first_request=3, initiation_interval=1,
                            added_row_payload_cycles=0, post_command_tail=0),
        token_latency='Three frontend command edges per attention invocation; existing gather/tile/formatter separately priced; no ideal throughput credit',
        slot_um=[120,120], initial_state_bit_upper_bound=384, area_measured_um2=None,
        floorplan_utilisation_target=0.55, fit='pending synthesis and route, no physical claim',
        routing=dict(signal_bits_estimate=220, pin_layers=2, pitch_um=0.48,
                     perimeter_tracks_capacity=1000, capacity_fraction=0.22,
                     actual_pin_lint='required before route'),
        source_binding='B ring physical index; C existing selected-ID stream, does not replace DS nine-sector gather reader',
        clock_ns=0.833333, setup_uncertainty_ps=60, hold_uncertainty_ps=25)


def hgi_attention_record_adapter_model():
    """Normative ATT records to G12 row front + existing ATT controller, no payload arithmetic."""
    return dict(schema='hgi.att-record-adapter.v1',model_before_build=True,
        transport_ABI='valid1/header128/SUT256/MDESC1024 actual3fae tuple; normative fields required',
        upstream_gap='3fae sequencer is legacy fields/count20; Claude must supply normative header and full typed counts',
        sideband_bits=dict(POS1=21,effective_B_count=32,effective_C_count=32),
        replicas=4,MACs_per_cycle=0,memory_bytes_per_cycle=0,
        record_payload_bits=1408,record_transport_bytes=176,
        ATT_setup_payload_bits=1152,row_command_payload_bits=85,
        state_bits_upper_bound=2656,mux_fanout='one local record station, no wide payload arithmetic or inter-stack broadcast',
        slot_variants_um=[[320,320],[360,360]],stdcell_area_measured_um2=None,utilisation_target=0.55,
        routing=dict(total_signal_bits_estimate=2800,pin_layers=2,pitch_um=0.48,
                     perimeter_track_capacity_320=5266,max_face_ATT_descriptor_bits=1024,
                     face_capacity_320=1316,actual_submit_lint='mandatory'),
        latency_cycles=dict(added_record_command_edges=3,record_to_first_row_edges_including_G12=6,row_II=1),
        token_charge=dict(DS_40_layers_QK_PV=240,Qwen_36_layers_two_local_KV_heads_QK_PV=432),
        retirement='rows_done AND actual_ATT_done; sticky fault halts CP without completion; recovery only by externally drained reset',
        selected_ID_and_payload_binding='External existing selected-ID and nine-sector gather reader; no indexed-PS reader introduced',
        physical_ready=False,clock_ns=0.833333,setup_uncertainty_ps=60,hold_uncertainty_ps=25)


def hgi_quant_vm_transport_model(depth=32, vm_rtt=4):
    """HGI QDQ component using existing CP 337/273 byte-sector ABI."""
    if depth < 24 or vm_rtt < 1:
        raise ValueError("result reservation must cover nonelastic 23-edge pipe")
    return dict(candidate="HGI_QUANT_VM_TRANSPORT", default_enabled=False,
        clock_domain="opt-in stream1p2 pending TT/FF physical qualification; legacy serial0p9 unchanged",
        CDC_qualified=False, command_capture_validate_edges=2,
        replicas=1, MACs_per_cycle=0, compute="existing 32-lane QDQ core,23 edges,II1",
        input_words_per_beat=32, read_sector_bytes=32, write_sector_bytes=32,
        max_VM_bytes_per_cycle=32, request_bits=337, response_bits=273,
        core_input_bits=1024, core_output_bits=512, record_bits=1409,
        output_queue_depth=depth, output_queue_flop_bits=depth*512,
        output_queue_SRAM_macros=0, input_assembly_flop_bits=1024, request_boundary_flop_bits=338, response_boundary_flop_bits=274,
        held_descriptors_flop_bits=512, held_header_flop_bits=128,
        address_count_control_declared_flop_bits=716,
        declared_adapter_flop_bits_excluding_core=19376,
        note_storage="preoptimization declared register inventory; unused descriptor fields may optimize away; actual mapped sequential cells govern floorplan",
        result_capacity_rule="reserve before first read; release only after final write ACK",
        maximum_reserved_beats=depth, VM_outstanding_requests=1,
        throughput_bound_beats_per_cycle=1/(8*(vm_rtt+1)),
        latency_cycles_first_result="min(record_beats,depth)*4*(VM_RTT+3)read edges + max(23-drain overlap,0) +4*(VM_RTT+3)ACK edges; measure component",
        legal_shapes="UE n%32=0;E4 n%16=0;VM FP32 input/BF16-or-FP32 output; multirow/innerstride/broadcast fallback",
        fallback="one word selected per physical32byte sector; widenedFP32word mask writes; boundedonependingACK",
        strided_latency="up to64*(VM_RTT+3)+23 edges per32element block, preservegoldenblockorder",
        address_registers="two32bit currentword addresses androwbases, two20bit row/col cursors, two16bit innerstrides, two32bit rowstrides",
        E4_tail="two8word sectors;zero-fill absent half;publish exactly16 widenedBF16 words",
        routing_tracks_boundary_bits=337+273+1409+6,
        routing_tracks_required=2030, corridor_capacity_tracks="two layer faces; cmd0.4003/req0.7152/rsp0.5794 b/um/layer vs currentflow12limit",
        slot_area_um2=496080, legacy_die_slot_area_um2=500000, required_die_slot_delta_um2=0,
        current_die_slot_fit="outline fits1814.376x276.456; rails/halos/pinmap pending", die_geometry_adoption_requires_coordinator=True,
        actual_stdcell_area_um2=29130.81084, actual_cells=200951,
        slot_fit_proven=True, slot_fit_source="2cb556822 actualTTsizing fitcompact1800x275.6; physicalqualification pending",
        floorplan_requirement="size from synthesized flop/core area at55percent before route",
        fanout="record header held once;one selected result queue mux; no payload ECC on flops",
        token_latency="sum actual 8sector handshakes perfull beat +23edges, no invented overlap credit",
        physical_qualified=False)

def hgi_quant_decode_model():
    """Owner-approved G8: existing DS arithmetic, generic record dispatch."""
    return dict(element='ot_hgi_quant_decode', replicas=1, macs_per_cycle=0,
        elements_per_cycle=32, memory_ports=dict(A_native_bytes_per_beat=128,
            O_native_BF16_bytes_per_beat=64,O_VM_FP32_bytes_per_beat=128,
            VM_assembly_and_publication="external finite transport: four8word reads/four8word writes; separately priced"),
        boundary_bits=dict(A=1024,O=512,record=128), input_decode_fanout=2,
        max_reduction_inputs=32, output_mux_inputs=2, additional_register_bits=15*(512+2)+23*2,
        ue8m0_latency_edges=23,e4m3_native_latency_edges=8,e4m3_latency_edges=23,
        e4m3_added_edges_per_record=15, ds_token_added_edges_upper_bound=40*15,
        ds_token_reference_cycles=461646, ds_token_added_fraction_upper_bound=600/461646,
        ds_default='legacy fp4 input selects unchanged margin core with generic_enable=0',
        provisional_slot_um=[1800,600], provisional_area_mm2=1.08,
        slot_basis='historical quant reservation 0.502mm2 plus second existing DS fp4 engine and alignment flops; measurement required',
        two_layer_pin_spread=True, tracks_required_per_face=1024,
        tracks_capacity_basis='route fp_lint must verify actual M4/M5 pitch/channel, no assumed pass',
        new_numerical_format=False, performance_gain_claim=None,
        adoption='mandatory approved interface conformance; TT>=0 FF>=0 DRC0 exact+mutant')

def hgi_token18_contract_model():
    """HGI-1 token endpoints: size before build; estimated area, zero new cycles.

    Wrapper on the released FAST1/PRL2 DS control. Acceptance uses the plain
    NSLOT8 leaf, not the historical protected/leased accept implementation.
    """
    tw, slots = 18, 8
    accept_inputs = 2 + 4 + 3 * tw + 3 * 3
    accept_outputs = 2 * slots * tw + 2 + 3 + 4 + tw
    extra_accept_ff = 2 * slots + 1  # one widened bit per slot + bonus
    return dict(schema='opentallas.hgi_token18.v1', default_off=True,
        model_scope=['DeepSeek-V4.1 HBM', 'Qwen3-8B HBM AR'],
        qwen_rom_mtp=False, replicas_per_die=1, MACs_per_cycle=0,
        memory_ports_bytes_per_cycle=0, memory_storage='none',
        accept=dict(input_bits=accept_inputs, output_bits=accept_outputs,
                    slot_count=slots, storage_bits=2*slots*tw+tw,
                    extra_ff_vs_17=extra_accept_ff,
                    latency_cycles=1, added_cycles_vs_DS17=0,
                    comparators=slots-1, comparator_width=tw,
                    mux_inputs=slots, mux_width=tw),
        control=dict(qualified_FAST=1, qualified_PRL=2, token_width=tw,
                     token_ports=['p_tok','f_tok','e_tok','cmd_tok1','am_idx','tw_tok'],
                     operand_bus_bits=slots*tw, added_cycles_vs_DS17=0,
                     added_boundary_bits=6+slots),
        routing=dict(assumed_slot_um=[466.56,200.88],
                     two_layer_pitch_um=.064, reserve_fraction=.30,
                     channel_tracks=int(2*200.88/.064*.70),
                     accept_boundary_tracks=accept_inputs+accept_outputs,
                     extra_control_boundary_tracks=6+slots),
        area=dict(estimated_accept_widening_um2=extra_accept_ff*DFF_UM2,
                  slot_area_um2=466.56*200.88,
                  estimate_only=True, route_required=True),
        latency=dict(token_added_cycles=0, accept_cycles=1,
                     control_read_wait_cycles=2),
        fanout=dict(replica_mux_demux=0, token_bit_max_accept_compare_fanout=1),
        exact_gate='DS17 lockstep + upper-bit mismatch + accept lengths0..7 + true mutants')


def hgi_token18_accept_seat_model():
    """Physical boundary repair, priced before RTL: parallel command pin seat."""
    d=hgi_token18_contract_model()
    seat_bits=4+3*18+3*3
    d['accept'].update(pin_seat_bits=seat_bits, extra_ff_with_seat=17+seat_bits,
                       latency_cycles=2, added_cycles_vs_DS17=1)
    d['latency'].update(accept_cycles=2, token_added_cycles=1)
    d['area'].update(estimated_accept_widening_um2=(17+seat_bits)*DFF_UM2)
    d['physical_measured_base']=dict(stdcell_area_um2=263.752, cells=2137,
        peak_floorplan_kib=322588, source='377249427', evidence='43b313543')
    d['reason']='rtl_boundary actual source377 input->register34 levels; inputseat required'
    return d


def hgi_token18_fullcore_model():
    """Reuse qualified hfd_mtp_core register/skid/read contract, not naked ctl."""
    return dict(schema='opentallas.hgi_mtp_fullcore18.v1',default_off=True,
        models=['DeepSeek-V4.1 HBM MTP'],replicas_per_die=1,
        topology='qualified ot_hfd_mtp_core TW18 XSEL1',
        MACs_per_cycle=0, fp32_bias_adds_per_cycle=8,
        memory_ports_bytes_per_cycle=0, history_token_bits=16*18,
        local_logit_input_bits_per_cycle=2*8*32+8+3,
        command_operand_bits=8*18, token_port_bits=18,
        source_selector_inputs=6*9, local_expert_selectors=0,
        window_ring_slots=256, sliding_window_rows=128,
        compressor_ring_slots=10, layers=40, model_maxpos=1048576,
        added_cycles_vs_qualified_DS_core=0,
        qualified_boundary_edges=4, qualified_prompt_read_wait=2,
        added_token_cycles_vs_bare_controller=4,
        slot_um=[466.56,200.88], area_slot_um2=466.56*200.88,
        estimated_token_widening_ff=128,
        estimated_width_area_um2=128*DFF_UM2,
        routing_tracks_available=int(2*200.88/.064*.70),
        routing_boundary_tracks_estimate=1200, macro_replicas=1,
        replica_mux_demux=0, new_token_ff_fanout=1,
        exact_state_binding='SPECF0 recipe039ca63d6; SPECF1 requires separate matched proof',
        physical_fit_measured=False, routes_required=2,
        exact_gate='matching fullcore TW18 XSEL1 traces + genuine rollback mutant')


def qwen_result_slot_conveyor_model(ns=8, db=64, rs=42, crb=16):
    """Full-shape structural successor; price before RTL, no adoption credit."""
    assert ns == 8 and db == 64 and crb >= ns
    latency = 2*ns + 5
    slot_w, slot_h = 259.2, 324.0
    boundary = 1+3+6 + 1+1+1+20+16+512
    ff = 64*38 + 3*557 + 2*551 + 8*38 + 38 + 2*10 + 32
    return dict(schema='opentallas.qwen_result_slot_conveyor.v1',
        adopted=False, default_off=True, models=['Qwen3-8B ROM'],
        MACs_per_cycle=0, compute_intensity_MACs_per_byte=0,
        replicas=dict(bands=6,slots_per_band=ns,total_slot_macros=6*ns),
        memory=dict(bytes_per_write_cycle=64,bytes_per_read_cycle=64,
                    macro='ot_sram_1r1w_64x512_m1_r2c2',depth=db),
        boundary=dict(request_bits_per_cycle=10,response_bits_per_cycle=551,
                      producer_bits_per_slot=557,credit_bits_per_cycle=1),
        routing=dict(estimated_tracks=boundary,available_tracks=int(2*slot_h/.064*.70),
                     pin_layers=['M4','M6','M5','M7']),
        replicas_cost=dict(global_data_mux_inputs=0,local_response_mux_inputs=2,
                            metadata_read_mux_levels=[8,8],control_fanout='local pin seat per slot'),
        area=dict(slot_um=[slot_w,slot_h],slot_area_um2=slot_w*slot_h,
                  macro_area_um2=171.288*77.760,estimated_FF=ff,
                  FF_area_proxy_um2=ff*DFF_UM2,controller_slot_um=[216,216],
                  band_area_um2=ns*slot_w*slot_h+216*216,physical_fit=False),
        latency=dict(request_to_response_cycles=latency,burst_issue_cycles=ns,
                     worst_full_burst_response_cycles=latency+ns-1,
                     ingress_to_request_cycles=3,ingress_to_first_slot0_output_cycles=latency+3,
                     ingress_to_first_slot7_or_empty_output_cycles=latency+10,
                     baseline_first_beat_cycles=5,added_first_beat_cycles_min=latency+3-5,
                     added_first_beat_cycles_max=latency+10-5,
                     token_cost='+19..26 first-beat edges according to first used slot; sparse slots still consume issue tokens; measured landed token bench required',
                     stall_budget_edges=rs,store_headroom_bursts=5,
                     ready_threshold=db-rs-5),
        capacity=dict(credits=crb,reserve_per_request=1,disabled_slot_refund=True,
                      measured_full_burst_span_cycles=4311/359,
                      measured_empty_burst_span_cycles=4139/359,
                      measured_profile_bursts=360,
                      profile_scope='saturated element, immediate consumer credit, full shape actual SRAM model; not token rate'),
        exact_gate='full NS8 DB64 RS42 CRB16 ordered burst scoreboard, stalls, wrap, pause, reset, true mutants')
>>>>>>> e47d30cf8 (Price full and empty result bursts against measured finite-credit service)
