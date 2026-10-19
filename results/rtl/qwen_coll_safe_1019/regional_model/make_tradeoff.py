#!/usr/bin/env python3
"""One source compiler schedule and explicit model-only state/area ledger."""
import hashlib
import itertools
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'tools'))
from qwen_coll_tp8_static_bench import schedule
BASE = Path(__file__).resolve().parent
widths = [150]*4 + [152]*4 + [154,153,153,153] + [139,139,139,138]
rows = []
for label, delta in [('current',0),('A_unqualified_E2_target',8),('B_gated_final_capture_model',12)]:
    lu, ls = 53+delta, 378+delta
    spans = {}
    for name, modes, words in [('AR256',[0],[256]),('ARGMAX1',[1],[1]),
                               ('AR256x2',[0,0],[256,256]),
                               ('AR256x2_ARGMAX1',[0,0,1],[256,256,1])]:
        prog = schedule(modes,words,lu,ls,shared_ucie=True)
        spans[name] = max(p['last_out'] for p in prog)-prog[0]['first_slot']+1
        (BASE/(label+'_'+name+'_program.json')).write_text(json.dumps(prog,indent=2)+'\n')
    rows.append(dict(variant=label,LU=lu,LS=ls,spans=spans,
        P_R_banks_per_ring=2 if lu+2<=64 else 4,
        P_R_total_macro_area_um2=(4 if lu+2<=64 else 8)*177.768*81))
for row in rows:
    da = row['spans']['AR256']-rows[0]['spans']['AR256']
    dg = row['spans']['ARGMAX1']-rows[0]['spans']['ARGMAX1']
    added = 72*da+dg
    row.update(token_added_cycles=added,token_cycles=249577+added,
        added_cycles_percent=100*added/249577,
        throughput_loss_percent=100*added/(249577+added))
ledger = dict(schema='opentallas.safe_collective.regional_model.v1',
    status='MODEL_ONLY_NO_IMPLEMENTATION_OR_GATE_ADOPTION',rows=rows,
    landing_lane_widths=widths,total_bundle_bits=sum(widths),
    target_A_payload_state_bits=5*sum(widths),
    target_A_full_metadata_state='UNDEFINED UNTIL INDEPENDENT RTL/SAFETY QUALIFICATION; payload count is not total',
    concrete_B_FIRST1_state_upper_bits=sum(9*w+5*((w+15)//16)+68 for w in widths),
    concrete_B_FIRST0_state_upper_bits=sum(9*w+5*((w+15)//16)+66 for w in widths),
    concrete_B_ICG_latches_FIRST1=9*len(widths),
    concrete_B_local_SRAM_macro_area_um2=0,
    B_W180_measured_mapped_state_bits=1746,B_W180_measured_area_um2=616.2237,
    B_W180_measured_area_source='SAFE-QW-LAND 62708ac8f W180; ff0368257 reset fix rebench live; smaller widths unmeasured',
    B_added_P_R_macros=4,B_added_P_R_storage_bits=4*32*546,
    B_added_P_R_macro_area_um2=4*177.768*81,
    note='A targets four crossings x2 added edges; B models x3 final-capture increments. Neither is an observed integrated calendar; root phase, startup, first operation and steady workloads require proof.')
ledger['core_cmd_free_boundary'] = dict(
    status='MODEL_ONLY_NO_LIVE_SOURCE_RETIMING',
    source_owner='ot_coll_tp8_static cmd_free_next via qfd_io_collective_static',
    consumers='ot_coll_cmd_issue -> ot_qwen_fixed_issue available/end_ok; qfd_seq_su_collective_calendar wraps same issuer',
    use='Compiled-cycle issue is unconditional; availability/end_ok only set sticky fault',
    existing_semantics='combinational one-edge-next availability compensates existing command-pin capture',
    blind_capture='INVALID: adds one status-age edge and can false-fault legal free transition',
    predictor_option=dict(capture_edges_added=1,lookahead_transitions=2,new_boundary_flops=1,
        command_payload_cycles_added_if_proved=0,mapped_area='UNMEASURED',
        proof='two-step state includes current pin-command and external command; actual root-age alignment required'),
    delayed_diagnostic_option=dict(capture_edges_added=1,diagnostic_edges_added=1,
        command_payload_cycles_added=0,completion_guard='must include pending end/status fault',
        shared_issuer_source_change='requires coordination; not implemented'),
    clock_warning='10190 soft sinks/large-outline advisory; actual TT/FF pin spread and linked references decide acceptance')

ledger['shared_32x64_option'] = dict(
    status='UNQUALIFIED_COMPOSITION_OPTION_ONLY',
    macro_source='b65718325',geometry_source='7549fae73',wrapper_source='e0d4d194a',
    macro_path='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1',
    lef_sha256='783546b59561cdeb3a09e912973286a9d38cdd2ced58391f7ab9aa74b38f3d02',
    model_sha256='9286563862a9cac862351ef03094fab7f53edd82c38784349d588e0958e0bde2',
    native_macro_shape_um=[31.968,17.28],native_macro_area_um2=31.968*17.28,
    native_pins_W=103,native_pins_E=102,
    native_pins_per_um_W=103/17.28,native_pins_per_um_E=102/17.28,
    banks_per_logical_546=9,upper_padding_zero_mask_bits=30,
    raw_area_per_logical_546_um2=9*31.968*17.28,
    B_logical_banks=8,B_native_banks=72,
    B_total_raw_macro_area_um2=72*31.968*17.28,
    group_reservation_shape_um=[302.4,172.8],
    B_gross_group_reservation_um2=8*302.4*172.8,
    current4groups_raw_area_um2=36*31.968*17.28,
    B_added4groups_raw_area_um2=36*31.968*17.28,
    B_added4groups_SRAM_bits=36*32*64,
    native_latency='1 synchronous edge, true1R1W, read-before-write',
    composition_added_edges_analytical=0,
    integrated_calendar_status='LU65/LS390 unchanged by composition alone ONLY IF exact native latency/collision/phase witnesses pass',
    source_clock_contract='Current wrapper scalar clk fans9 actual g_bank[0..8].u_m.clk sinks; no9clock vector override or proven regional interception',
    B_P_R_macro_clock_pin_references=72,
    B_all_core_clock_pin_references=72+5+8+1,
    B_logical_top_clock_ports_if_scalar_groups=22,
    B_top_ports_if_independent_native_roots=86,
    qualification='Wrapper unit/fullwidth goldens, native72bank production, per-pin TT/FF clock arrivals, reset, PG/viaescape and GRT/DRC pin access all pending; old5widebank proof is unrelated',
    old_wide_shape_um=[177.768,81],old_wide_W_pins=826,old_wide_E_pins=825,
    old_wide_W_pins_per_um=826/81,old_wide_E_pins_per_um=825/81,
    old_wide_escape_status='10.2pins/um raw-face density; independent escape proof pending')

(BASE/'tradeoff.json').write_text(json.dumps(ledger,indent=2)+'\n')
print(json.dumps(ledger,indent=2))
