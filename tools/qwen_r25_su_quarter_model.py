#!/usr/bin/env python3
"""Before-build real N256/M64 quarter and finite native-port calendar."""
import json
import math

def model():
    n,m,q=256,64,4
    reads,writes=5*n,2*n+n//8
    capture_bits=(reads*2+writes)*72
    command_bits=11*72+3*72
    return dict(schema='opentallas.qwen_r25_su_quarter.v1', adopted=False,
        models=['Qwen3-8B HBM'], native=dict(N=n,M=m,quarters=q,LV=7,
            MLAT=6,ALAT=6,CTL12=2,OPR=1,CAPR=1,DDIV=21,SIDEX=4,FSQ=1,
            BCAST_STAGES=5,RET_STAGES=6,MACs_per_virtual_edge=n,
            exp_or_divides_per_virtual_edge=m,
            global_reduction='Each quarter can execute the complete chunk8 reduction; no unpriced or reordered cross-quarter partial sum. Compiler prices duplicate work.'),
        storage=dict(read_snapshot_rows=reads,read_reply_rows=reads,
            write_snapshot_rows=writes,protected_row_bits=72,
            capture_bits_per_quarter=capture_bits,command_control_bits=command_bits,
            capture_ff_area_floor_um2=capture_bits*.2916,
            four_quarter_capture_slot_mm2=q*capture_bits*.2916/.55/1e6,
            ROM_ECC=False,mutable_capture_SECDED=True,
            shared_VM_capacity_words=262144,KV_capacity_rows=8224),
        ports=dict(native_read_bytes_per_virtual_edge=reads*4,
            native_write_bytes_per_virtual_edge=writes*4,
            service_bytes_per_accepted_read=32,service_bytes_per_accepted_write=32,
            req_bits=337,rsp_bits=273,one_outstanding_per_quarter=True,
            native_snapshot_bits=reads*27+writes*59,
            physical_boundary='Only registered 337/273 service and protected command/completion cross quarter boundary; native wide buses remain inside quarter'),
        calendar=dict(native_clock='0.9 GHz parent clock, enabled only after actual service replies and visibility receipts',
            virtual_edge='Snapshot PRE-edge read/write ports, advance native one edge, serve captured reads and publish captured writes, then repeat',
            read_scan='finite increasing cursor; disabled seats skipped; response checked by real tag before operand capture',
            publication='write ACK followed by same-sector read reproducing scalar before retirement',
            worst_disabled_scan_master_edges_per_virtual_edge=5*(reads+writes),
            enabled_read_additional_edges='actual request/response latency + protected reply capture',
            enabled_write_additional_edges='actual write ACK + actual visibility read + comparison',
            latency_per_program='sum measured virtual edges and enabled reads/writes/visibility reads; never assign fixed service delay or token rate before real measurement',
            duplicated_full_reduction_quarters=q),
        physical=dict(arithmetic_area='reuse source-matched real c12 lane/reducer masters; no light/XOR envelope credit',
            capture_slot_um=[1200,1200],capture_fit_at_55pct=(capture_bits+command_bits)*.2916<=1200*1200*.55,
            service_routing_tracks=610,proposed_service_corridor_um=120,
            track_pitch_um=.072,track_capacity=math.floor(120/.072*.7),
            command_fanout='registered broadcast stages5; actual256 light/64SFU lanes',
            replica_mux_demux='four service endpoints, actual native scalar/address snapshot seats per lane, finite completion barrier',
            final_SS_FF_closed=False),
        exactness='Real c12 FP32 arithmetic; native690 decoded fields, held fixed-latency virtual sampling, golden chunk8 order. No DPI or host arithmetic qualifies the RTL.')

if __name__=='__main__': print(json.dumps(model(),indent=2))
