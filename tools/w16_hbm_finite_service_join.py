#!/usr/bin/env python3
"""Bind actual wholeprogram coverage to finite ordinary-GPU/RMW requirements.

No missing service ticks are invented. Serial lock scenarios are additive
partial-path costs under stated assumptions, not fulltoken clocks/rates.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PINS = {
 'coverage':('13299abb6','results/physical_abi3/asap7/gpu/w13_calendar_v2_and_row_placement_20261001/fullprogram_and_KV_admission_v2_summary.json'),
 'canonical':('2a648d7e2','results/physical_abi3/asap7/gpu/w13_calendar_v2_and_row_placement_20261001/failed_history_and_canonical_basis.json'),
 'RMW_position0':('c59e106d6','results/physical_abi3/asap7/gpu/w13_calendar_v2_and_row_placement_20261001/qwen_packed_KV_locked_RMW_position0.json'),
 'RMW_position1':('c59e106d6','results/physical_abi3/asap7/gpu/w13_calendar_v2_and_row_placement_20261001/qwen_packed_KV_locked_RMW_position1.json'),
 'DS_calendar':('1c37cdaa9','results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json'),
 'Qwen_terminal':('895605aad','results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1/admission.json'),
}

def build():
    records,pins={},{}
    for name,(commit,path) in PINS.items():
        full=subprocess.check_output(['git','rev-parse',commit],text=True).strip()
        raw=subprocess.check_output(['git','show',full+':'+path])
        records[name]=json.loads(raw)
        pins[name]=dict(commit=full,path=path,sha256=hashlib.sha256(raw).hexdigest())
    writers=[]
    for pos in (0,1):
        rec=records['RMW_position'+str(pos)]
        assert len(rec['rows'])==72
        for row in rec['rows']:
            commands=row['mixed_read_write_commands_by_stack']
            assert sum(commands)==528
            assert max(commands)==144
            writers.append(dict(position=pos,layer=row['layer'],die=row['die'],graph_op=row['graph_op'],
                commands_by_stack=commands, mixed_command_floor_cycles=max(commands),
                mean_command_count_per_stack=sum(commands)//4,
                port_payload_bytes=row['port_payload_bytes'],
                WRvisible_ACKs=row['write_visible_ACKs'], locked_RMWs=sum(row['locked_RMW_reads_by_stack']),
                integer_merge_warp_instructions=row['merge_two_source_integer_warp_instructions'],
                active_word_lanes_per_merge=8, RF2R1W=True,
                serial_one_warp_merge_issue_to_writeback_ticks=768*9*4,
                merge_RF_operand_bits=row['merge_RF_operand_bits'],
                merge_RF_write_bits=row['merge_RF_write_bits'],
                serial_one_global_lock_scenario_ticks=256*rec['sector_lock_timing_template']['total_ticks'],
                scenario_full_sector_V_service_ticks=None,
                actual_SM_quadrant_lane_RF_bank_assignment=None,
                finite_instruction_and_visibility_events=None))
    return dict(schema='opentallas.w16.hbm-whole-finite-service-join.v1',source_pins=pins,
        software_coverage=records['coverage'], ordinary_GPU_cost_basis=records['canonical'],
        Qwen_terminal_software_receipt=records['Qwen_terminal'],
        writers=writers, writers_count=len(writers),
        total_packed_KV_port_bytes=sum(w['port_payload_bytes'] for w in writers),
        total_packed_KV_mixed_commands=sum(sum(w['commands_by_stack']) for w in writers),
        command_floor_correction='Owner summary132 is a balanced mean, not the actual stack maximum: position0[128,128,144,128], position1[128,128,128,144]. Charge144 minimum stack command cycles per writer before competing weights/scales/refill.',
        service_capacity=dict(common_tick_hz=3600000000, fast_cycle_ticks=3, slow_cycle_ticks=4,
            shared_read_OR_write_commands_per_stack_per_fast_cycle=1,
            combined_read_response_and_write_payload_bytes_per_quad_fast_cycle=750,
            lane_credits=128, lane_packet_bits=320, sector_payload_bytes=32,
            RF_operand_ports=2, RF_writes_per_partition_per_slow_cycle=1,
            opcode_issues_per_partition_per_slow_cycle=1,
            shared_bank_count=32, shared_read_ports_per_bank=1,shared_write_ports_per_bank=1,
            readwrite_masks_sameaddress_forwarding_qualification=False),
        lock_context_allocation=records['RMW_position0']['candidate64_lock_contexts'],
        lock_scenario=records['RMW_position0']['sector_lock_timing_template'],
        single_global_lock_policy='Conservative nonoverlapped sizing scenario: one sector lock active across all stacks/SMs; sequentialread/merge/write/visibleACK.64context hardware cannot imply64way service or free concurrent issue.',
        serial_RMW_scenario_partial_ticks_by_token={str(p):sum(w['serial_one_global_lock_scenario_ticks'] for w in writers if w['position']==p) for p in (0,1)},
        obligatory_resource_edges=['sector_epoch_lock_acquire','read_request','shared_stack_read_command',
            'read_response','RF_import','two_source_XOR_AND_XOR_issue_and_writeback',
            'shared_stack_write_command','backend_WRvisible','reverse_ACK_CDC',
            'final_consumer_accept','lock_credit_release','KV_generation_publication'],
        fail_closed_dependencies=dict(
            controller='Actual physical read/write/refill/refresh/turnaround timing and visibility provider.',
            SM='Actual opcode/RF/shared-bank issue lists for all3474Q and2213DS instructions; no free SFU/variants.',
            DRAM_NoC='One combined service budget including weights/scales/collectives/KV, not separate750B budgets.',
            RMW='Maskless path requires read+merge+write, held sector/epoch identity and WRvisible reverse ACK.',
            physical='TC16 contextualSSFAIL retained; complete32SM abstracts/fit/RF coexistence unqualified.'),
        resource_calendar_closed=False, full_token_ticks=None,
        hardware_build_ready=False, physical_admission=False, headline_rate=None,
        jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
