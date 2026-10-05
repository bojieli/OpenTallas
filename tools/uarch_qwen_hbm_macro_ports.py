#!/usr/bin/env python3
"""Bind finite GPU service storage to actual 1R1W macro ports before RTL."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REV='4535be1001d69bc43669e0fdf0401896be4034a6'
DIR=ROOT/'results/uarch/qwen_hbm_connected_20261001'
MACRO='physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/'
def get(p):return subprocess.check_output(['git','show',REV+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def compose():
    v=get(MACRO+'ot_sram_1r1w_1024x256_m2_r2c2.v')
    j=get(MACRO+'ot_sram_1r1w_1024x256_m2_r2c2.json')
    for declaration in [b'[9:0] r_addr_in',b'[255:0] rd_out',b'[9:0] w_addr_in',b'[255:0] wd_in',b'[255:0] w_mask_in']:assert declaration in v
    ingress=json.loads((DIR/'HBM_ingress_before_RTL_r2.json').read_text())
    l2=json.loads((DIR/'L2_injector_before_RTL_r2.json').read_text())
    macro_um2=json.loads(j)['area']['macro_area_um2']
    old_macros=ingress['area']['additional_data_macros_32KB']
    per_macro_footprint=ingress['area']['additional_data_SRAM_footprint_mm2']/old_macros
    assert abs(per_macro_footprint-macro_um2*1.31/1e6)<1e-10
    gather=36*4;queues=4*32*2;actual=gather+queues
    increment=(actual-old_macros)*per_macro_footprint
    return dict(schema='opentallas.qwen-hbm-real-macro-port-composition.v1',revision=REV,
        status='MODEL_PORT_SIZING_CORRECTION_PENDING_FULL_COMPOSITION',adoption=False,
        physical_build_ready=False,engine_RTL_build_ready=False,full_token=False,
        macro=dict(name='ot_sram_1r1w_1024x256_m2_r2c2',depth=1024,width_bits=256,
            read_ports=1,write_ports=1,read_latency_cycles=1,write_mask_bits=256,
            area_um2=macro_um2,footprint_mm2=per_macro_footprint,
            collision='Model reads pre-write value at same edge; controller must stall same-address read/write until required committed value is visible'),
        L2=dict(slices=4,banks_per_slice=8,macros_per_bank=8,total_macros=256,
            scalar_write_bits_per_bank_cycle=32,scalar_mask_bits=32,
            read_bits_per_bank_cycle=256,word_addr_bits=10,macro_select_bits=3,
            valid_mapping='Scalar row[15:13] macro, row[12:3] word, row[2:0] lane; all 32 lane mask bits set only for selected FP32 lane',
            line_assembly='128B injector line requires four 256bit bank reads; finite four-cycle assembler, no fictional 1024bit macro read'),
        gather=dict(clients=36,macros_per_client=4,total_macros=gather,
            logical_lines_per_client=512,physical_line_slots_per_client=1024,
            physical_bytes_per_client=131072,logical_credited_bytes_per_client=65536,
            read_bits_per_client_cycle=1024,
            sector_write='Sector offset[1:0] selects one of four macros, line slot selects macro word. At most one accepted sector per macro per cycle; conflicts backpressure per-PC return queue',
            completion='Four-sector bitmap plus retained generation/tag required before reading complete line; stalled output retains FIFO/credit'),
        backend_queues=dict(stacks=4,pseudochannels_per_stack=32,
            request_macros_per_PC=1,return_macros_per_PC=1,total_macros=queues,
            queue_logical_depth=512,macro_physical_depth=1024,
            simultaneous_ports='Separate request and return 1R1W macros each sustain one enqueue and one dequeue per PC cycle; unallocated half of each macro is charged, not free port sharing',
            request_wdata_bits=256,return_data_bits=256,
            queue_credit='No dequeue into a blocked downstream landing FIFO; DRAM return scheduled only against reserved return credit'),
        area=dict(historical_capacity_only_macros=old_macros,required_port_banked_macros=actual,
            extra_macros=actual-old_macros,additional_port_banking_footprint_mm2=increment,
            composed_storage_corrected_die_mm2=ingress['area']['composed_die_mm2']+increment,
            core_available_mm2=ingress['area']['core_available_mm2'],SM_slot_fit=False,
            remaining_unpriced='32-PC to 36-client/four-sector gather crossbar, landing FIFO controls, write-ACK buffering and RF/vector/TP consumer service; no build admission until these are model composed'),
        finite_services=dict(read_ingress_Bpc_die=4096,uncoalesced_Bpc_die=512,
            LENW5_Bpc_die=2048,credit_limited_read_service_Bpc=ingress['performance']['selected_service_ceiling_Bpc'],
            no_new_performance_credit=True,
            remaining='Sector conflicts and gather ready stalls consume actual cycles; existing service ceiling is only an upper bound. Crossbar lane policy, FIFO depth and arbitration latency must be priced before RTL'),
        source_sha256={MACRO+'ot_sram_1r1w_1024x256_m2_r2c2.v':sha(v),
            MACRO+'ot_sram_1r1w_1024x256_m2_r2c2.json':sha(j),
            'results/uarch/qwen_hbm_connected_20261001/HBM_ingress_before_RTL_r2.json':sha((DIR/'HBM_ingress_before_RTL_r2.json').read_bytes()),
            'results/uarch/qwen_hbm_connected_20261001/L2_injector_before_RTL_r2.json':sha((DIR/'L2_injector_before_RTL_r2.json').read_bytes()),
            'tools/uarch_qwen_hbm_macro_ports.py':sha(Path(__file__).read_bytes())})
if __name__=='__main__':
    x=compose()
    assert x['area']['required_port_banked_macros']==400
    assert x['L2']['total_macros']*32768==8*1024*1024
    assert x['gather']['read_bits_per_client_cycle']==128*8
    with (DIR/'real_macro_ports_before_RTL.json').open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(x['area'],indent=2))
