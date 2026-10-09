#!/usr/bin/env python3
"""Model and generate plain transient-control AR quarter; external SRAM stays protected."""
import argparse,hashlib,json
from pathlib import Path

def model():
    reads,writes=1280,544
    seats=2*reads+writes+29+15
    return dict(schema='opentallas.qwen.r25.quarter_mx1.v1',adopted=False,
        native=dict(N=256,M=64,quarters=4,MACs_per_virtual_edge=256,MLAT=6,ALAT=6,CTL12=2),
        storage=dict(transient_seats=seats,plain_bits=seats*64,
            removed_transient_check_bits=seats*8,FF_floor_um2=seats*64*.2916,
            actual_VM_SRAM_payload_protection='External finite VM SRAM SECDED unchanged; no transient ECC/control mirror added'),
        ports=dict(read_bytes_per_virtual_edge=reads*4,write_bytes_per_virtual_edge=writes*4,
            request_bits=337,response_bits=273,command_bits=690,owner_bits=74),
        routing=dict(boundary_tracks=610,channel_um=120,track_capacity=1166),
        replica_cost=dict(quarters=4,capture_seats_per_quarter=seats,read_write_scan_groups=29),
        area=dict(capture_slot_um=[1200,1200],capture_only_fit=seats*64*.2916<=1200*1200*.55,
            full_native_arithmetic_area='unqualified; actual lane/SFU/reducer masters required'),
        latency=dict(additional_cycles=0,disabled_scan_edges_per_virtual_edge=29,
            full_program='actual virtual native edges plus real service ACK/visibility waits; no guessed token rate'),
        implementation='Same exact native arithmetic and finite service calendar, plain64 transient seats instead of SECDED72; no epoch/cohort/lease/release protocol',
        gate='Actual AR N256/M64 finite VM numerical/visibility gate, model-priced component physical intake by Claude')

def generate(source):
    if 'module ot_qwen_r25_su_quarter #(' not in source or 'OWNER_W=73' not in source:raise ValueError('source ABI')
    x=source.replace('module ot_qwen_r25_su_quarter #(','module ot_qwen_r25_su_quarter_mx1 #(')
    x=x.replace('GROUP_SKIP=0,OWNER_W=73','GROUP_SKIP=1,OWNER_W=74')
    x=x.replace(' import ot_gpu_w6_secded_pkg::*;',''' // Transient native pipeline/control seats are plain; actual VM SRAM protection is external.
 function automatic [71:0] plain_seat(input [63:0] x);plain_seat={8'b0,x};endfunction
 function automatic [65:0] plain_data(input [71:0] x);plain_data={2'b0,x[63:0]};endfunction''')
    x=x.replace('encode64(', 'plain_seat(').replace('decode64(', 'plain_data(')
    return x

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',action='store_true');p.add_argument('--source',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    if a.model:print(json.dumps(model(),indent=2));return
    if not a.source or not a.out:p.error('source and out required')
    a.out.write_text(generate(a.source.read_text()))
    print(json.dumps(dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest())))
if __name__=='__main__':main()
