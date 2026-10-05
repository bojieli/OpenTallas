#!/usr/bin/env python3
"""Price mandatory local counter reset priority, independently of die power."""
import argparse,json,hashlib,subprocess
from decimal import Decimal as D
from pathlib import Path

SOURCE=('9345c1fc048b2e19255e5c27b2bfde6f64360f29','rtl/chip/ot_chip_v41x_ckv_die_service.sv')

def next_count(previous,nwr,new_selection,kw=10):
    if not 0<=previous<2**(kw+1) or not 0<=nwr<=5:
        raise ValueError('outside existing counter/source widths')
    return 0 if new_selection else (previous+nwr)%(2**(kw+1))

def build():
    raw=subprocess.check_output(['git','show',SOURCE[0]+':'+SOURCE[1]])
    text=raw.decode()
    assert 'npresent <= npresent + (KW+1)\'(nwr);' in text
    assert 'if (sel_v && !rd_act) begin' in text
    k=512;kw=(k).bit_length();bits=kw+1
    gates=4*bits+1
    failure_pin=('ef81265e7307f17f10ecd5c852e3105c61677031','results/rtl/w17_connected_token_preparation_20261001/ckv_collector_clear_counterexample.json')
    failure_raw=subprocess.check_output(['git','show',failure_pin[0]+':'+failure_pin[1]])
    failure=json.loads(failure_raw)
    assert hashlib.sha256(raw).hexdigest()==failure['source_pins'][SOURCE[1]]['sha256']
    return dict(schema='opentallas.w17.ckv-counter-priority-model.v1',
        source_pin=dict(commit=SOURCE[0],path=SOURCE[1],sha256=hashlib.sha256(raw).hexdigest()),
        correctness='Mandatory baseline fix: new selection reset wins over trailing unconditional count update.',
        actual_failure_source_pin=dict(commit=failure_pin[0],path=failure_pin[1],sha256=hashlib.sha256(failure_raw).hexdigest()),
        actual_original_counterexample=dict(previous_count=1,present_after_clear=0,nwr=0,
            original_next_count=1,required_next_count=0),
        proposed_next='new_selection ? 0 : old_count+nwr; new_selection=sel_v&&!rd_act',
        K=k,KW=kw,counter_bits=bits, existing_counter_FF_bits=bits, added_FF_bits=0,
        added_memory_ports=0,added_boundary_bits=0,added_clock_endpoints=0,
        added_pipeline_cycles=0,combinational_selector_NAND_levels=2,
        conservative_mux_gate_screen=dict(two_input_mux_bits=bits,NAND2_equivalents=gates,
            area_per_NAND2_um2='.23328',density='.5',
            allocated_area_um2=str(D(gates)*D('.23328')/D('.5')),
            allocated_area_mm2=str(D(gates)*D('.23328')/D('.5')/D(1000000)),
            source='Same primitive gate-screen coefficient as bounded W17 descriptor/fanout model; not mapped cells.'),
        same_edge_arrival_guard=dict(policy='On new selection, block all five collector writes/count/stat updates and fault if any wv source asserted. Do not forgive old epoch/peer traffic.',
            existing_write_enable_sources=5, added_clocked_state_bits=0,
            extra_NAND2_equivalent_allocation=32,
            counter_and_collision_guard_total_allocated_area_um2=str(D(gates+32)*D('.23328')/D('.5')),
            counter_and_collision_guard_total_allocated_area_mm2=str(D(gates+32)*D('.23328')/D('.5')/D(1000000)),
            scope='Control enable/OR/fault gate screen only; existing512x2304 array/write data unchanged. No timing/power closure.'),
        extra_data_switching_power_W=None,contextual_SS_FF=None,
        local_companion_RTL_exact_gate_ready=True,local_measured_adoption=False,
        whole_candidate_power_not_a_dependency_of_local_exactness=True,
        required_local_gate=['Newsel with old count1 and nwr0 resets0.',
            'Newsel with old count512 and nwr0 resets0.',
            'No newsel retains unchanged0..5 count addition.',
            'Keep same ports, arrays and old pinned source; opt-in isolated companion.',
            'On newsel+wv!=0 block collector writes and assert sticky fault; never allow present[] reset override.',
            'Clear+noarrival, normalincrement and sameedgearrival negative gates before local exactness.'],
        broad_admission=False,
        broad_remaining=['512*2304 collector data and512present existing storage; five candidatewrites/fourmerge reads need explicit ports.',
            'C/P/W/B old-job/drain and512*9 worst CKVsector service.',
            'Three peer copies/ownedrow, finite held credits/generation/clear ordering.',
            'Nine actual backend write-visible ACKs, reverse CDC and final attention descriptor/engine retirement.'],
        jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
