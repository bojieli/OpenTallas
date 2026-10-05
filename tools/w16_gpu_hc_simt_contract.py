#!/usr/bin/env python3
"""Read-only resource companion to corrected W19 r3 GPU HC candidate.

Positive analytical assumptions; unknown transport service is never a zero.
No generator edit, hardware build, complete-token price or rate adoption.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/w16_gpu_hc_simt_contract_20261001'
INPUTS=OUT+'/assumptions_r1.json'
KERNEL='results/rtl/w19_checkpoint_production_20261001/gpu-simd-lowering-candidate-r3.json'
PROOF='results/quality/w19_hc_simd_proof_20261001/proof.json'
TRANSPORT='results/uarch/w19_transport_contract_20261001/contract_r1.json'
MACRO='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json'


def require(ok,message):
    if not ok:raise ValueError(message)


def read(path):return json.loads((ROOT/path).read_text())
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def assumptions():
    return dict(schema='opentallas.w16.HC_resource_assumptions.v1',measured=False,
        integer_instruction_latency=3,shared_instruction_latency=2,
        barrier_cycles=8,warp_issue_cycles=1,shared_banks=32,bank_ports=1,
        word_bytes=4,transpose_coefficient_buffer=2048,transpose_activation_buffer=1024,
        profile='Conservative serial raw-buffer staging and explicit address/scatter instructions. R3 final-refill writes retained as an additional conservative copy, no overlap or free transpose. Candidate latencies and clocks unqualified.')


def validate(p):
    require(p['measured'] is False,'not measured')
    for k in ('integer_instruction_latency','shared_instruction_latency','barrier_cycles','warp_issue_cycles'):
        require(type(p[k]) is int and p[k]>0,'unknown/zero latency: '+k)
    require((p['shared_banks'],p['bank_ports'],p['word_bytes'])==(32,1,4),'unsupported bank geometry')
    require(p['transpose_coefficient_buffer']==2048 and p['transpose_activation_buffer']==1024,'unpriced buffer geometry')


def scatter_conflict(packed=False):
    # Term-major destination k*C+chunk, C=1024 or512 => bank=chunk%32.
    # 32 consecutive F32 words span4chunks; packed BF16 words span8chunks.
    counts=Counter((lane//(4 if packed else 8))%32 for lane in range(32))
    return max(counts.values())


def transpose(chunks,p,activation=False):
    validate(p);require(chunks in (1024,512),'unsupported bounded wave')
    loops=4 if activation else 8
    tiles=chunks//32
    conflict=scatter_conflict(activation)
    # One raw warp load, six address/control instructions per scalar value,
    # one scatter per coefficient or two per packed activation word.
    values=1  # BF16 pairs stay packed; widening occurs in the pinned chunk program
    phase=(p['warp_issue_cycles']+p['shared_instruction_latency']+
        values*(6*(p['warp_issue_cycles']+p['integer_instruction_latency'])+
                conflict*p['warp_issue_cycles']+p['shared_instruction_latency']))
    # Initial raw write charges bytes/128, final writes are charged here AND
    # retained by r3 refill: deliberately conservative serial additional copy.
    raw_write=chunks*8*(2 if activation else 4)//128
    return dict(chunks=chunks,tiles=tiles,bank_conflict=conflict,
        warp_loads=tiles*loops,warp_scatter_stores=tiles*loops*values,
        integer_address_instructions=tiles*loops*values*6,
        additional_cycles=raw_write+tiles*loops*phase+p['barrier_cycles'],
        raw_read_bytes=chunks*8*(2 if activation else 4),
        scatter_write_bytes=chunks*8*(2 if activation else 4),
        assumption='Serialized ordinary shared/RF/INT instructions; not measured DMA swizzle. No buffer fill/port/turnaround credit.')


def shared_layout():
    regions=[];cursor=0
    for name,size in [('coefficient_tile',32768),('activation_tile',16384),('partials_control',4096)]:
        regions.append(dict(name=name,base=cursor,bytes=size));cursor+=size
    require(cursor==53248 and cursor<=65536,'scratch overflow')
    return dict(regions=regions,live_bytes=cursor,unused_bytes=65536-cursor,
        external_coefficient_transpose_bytes=2048,external_activation_transpose_bytes=1024,
        external_buffers_charged_separately=True,
        reuse='Single buffer. Refill next wave only after chunk/warp partial store retirement and barrier; retain80 F32 warp partials until padded128 final tree completes. Scalar phase follows all25 producers and grid barrier.')


def build(inputs=INPUTS):
    import uarch_model as U
    import w19_gpu_simd_contract as W
    import w19_composed_schedule as S
    from decode_critical_path import Graph
    p=read(inputs);validate(p)
    k=read(KERNEL);hc=k['hc'];proof=read(PROOF);transport=read(TRANSPORT)
    require(U.SM_ELEM['v41']['simt_lanes']==128 and U.SM_ELEM['v41']['scratch_kb']==64,'model budget drift')
    require(hc==W.build()['hc'],'r3 compute candidate no longer reproduces')
    require(k['organisation']['sm_count']==32 and hc['output_rows']==24 and hc['K']==20480,'geometry drift')
    require(hc['local_compute_cycles_candidate']==6854,'corrected compute schedule drift')
    for path,digest in proof['source_pins'].items():require(sha(path)==digest,'software proof source drift: '+path)
    require(len(proof['fixtures'])==7,'proof fixture scope drift')
    require(transport['address']['sector_bits']==27 and not transport['ready_to_build'],'transport qualification changed')
    program=read(S.PROGRAM)
    token_graph=S.graph(program,{})
    hc_ops=[(i,o) for i,o in enumerate(token_graph['operations']) if o.get('fn')=='hc_mixes']
    require(len(hc_ops)==80,'source HC graph drift')
    tiles=[dict(coefficient=transpose(w['chunks'],p),activation=transpose(w['chunks'],p,True)) for w in hc['waves']]
    extra=sum(t['coefficient']['additional_cycles']+t['activation']['additional_cycles'] for t in tiles)
    # Row SMs and norm SM run concurrently: slowest row owner bound. Serialize
    # coefficient and activation transpose on every row owner (same SM ports).
    conditional_cycles=hc['local_compute_cycles_candidate']+extra
    graph=Graph();prior=None;bindings=[]
    for ordinal,(index,op) in enumerate(hc_ops):
        name=f'HC{ordinal}.candidate_compute_and_transpose'
        graph.add(name,[] if prior is None else [prior],layer=op['layer'],issue=conditional_cycles/900000000,stream=False)
        prior=name
        nodes=[n for n in token_graph['nodes'] if n['source_operation_index']==index]
        bindings.append(dict(source_operation_index=index,layer=op['layer'],op=op['id'],
            compute_node=next(n['id'] for n in nodes if n['phase']=='gpu_simt_kernel'),
            additional_transpose_cycles=extra,conditional_local_cycles=conditional_cycles,
            service_nodes_unpriced=[n['id'] for n in nodes if n['phase']!='gpu_simt_kernel']))
    graph.solve(False)
    rf=k['register_file'];macro=read(MACRO)
    # 2 read replicas *2 depth banks *16 groups =64 existing analytical macros/SM.
    require(rf['macro_count_sm']==64 and rf['macro_count_die']==2048,'RF macro geometry drift')
    sources=[inputs,KERNEL,PROOF,TRANSPORT,MACRO,'tools/w19_gpu_simd_contract.py',
        'tools/w19_composed_schedule.py',S.PROGRAM,'tools/uarch_model.py','tools/decode_critical_path.py',
        'tools/w19_transport_contract.py','tools/hdc_golden.py','tools/hdc_golden_v41.py',
        'tools/w19_hc_simd_proof.py','tools/w16_gpu_hc_simt_contract.py','tests/test_w16_gpu_hc_simt_contract.py']
    counts=Counter()
    for w in hc['waves']:
        counts.update({key:value*24 for key,value in w['projection']['instructions'].items()})
        counts.update(w['norm']['instructions'])
    return dict(schema='opentallas.w16.corrected_GPU_HC_resource_composition.v1',inputs=inputs,
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        candidate=KERNEL,profile_measured=False,SM_count=32,lanes_SM=128,clock_hz=900000000,
        source_instruction_counts_chunk_and_warp_trees_per_operator=dict(counts),
        scalar_recipes=k['scalar_recipes'],scalar_dependency_cycles=hc['scalar_dependency_cycles_candidate'],
        latency_contract=k['ALU'],warp_waves=hc['waves'],transpose_waves=tiles,
        shared=shared_layout(),RF=dict(logical_bytes_SM=rf['capacity_bytes_sm'],
            physical_bytes_SM=rf['physical_capacity_bytes_sm'],physical_bytes_die=rf['physical_capacity_bytes_die'],
            candidate_macro_count_die=2048,analytical_macro_outline_area_mm2=2048*macro['area']['macro_area_um2']/1e6,
            macro_claim_boundary=macro['claim_boundary'],qualified_macro_area=False,
            read_bits_cycle_SM=rf['read_bits_cycle_sm'],write_bits_cycle_SM=rf['write_bits_cycle_sm'],
            live_projection_registers=32,coefficient=8,packed_activation=4,expanded_activation=8,products=8,
            accumulator_and_shuffle=2,control_reserve=2,
            scalar_phase_register_allocation=None,
            live_scope='32 resident warps x32 threads x32 registers. Packed source registers may be released after widening; conservative28 value registers +2 accumulator/shuffle +2 control =32. Compiler spills/address64/branch temporaries unqualified; software proof compiled RF cannot be credited to this different kernel.'),
        ports_tracks=dict(shared_word_banks=32,shared_read_bytes_cycle=128,shared_write_bytes_cycle=128,
            coefficient_naive_stride8_conflict=8,activation_packed_stride4_conflict=4,
            term_major_operand_conflict=1,RF_read_data_signals_SM=8192,RF_write_data_signals_SM=4096,
            shared_data_signals_SM=2048,RF_depth_select_mux_bits_SM=8192,
            RF_write_replica_fanout=2,RF_groups=16,RF_depth_mux_inputs=2,
            logical_data_track_demand_SM=8192+4096+2048,
            actual_route_tracks=None,channel_capacity=None,RF_mux_demux_area_mm2=None,
            SIMD_ALU_incremental_area_mm2=None,shared_external_buffer_area_mm2=None,slot_fit=None,
            policy='Logical data conductor demand excludes control/shuffle/clock. No physical layer/pitch/channel fit claim. Existing model SIMT lane area is not separate ADD/MUL/divider/RF closure.'),
        communication=dict(coefficient_HBM_bytes_operator=hc['coefficient_hbm_bytes_operator'],
            activation_endpoint_bytes_operator=hc['activation_broadcast_bytes_operator'],
            producer_scalar_payload_bytes=100,wire_bytes=None,grid_barrier_cycles=None,
            DMA_CDC_fence_latency=None,transport_queue_storage_bytes_rank=transport['geometry']['total_storage_bytes_per_rank'],
            transport_storage_area_mm2=None,transport_service_cycles=None,
            ownership='24 row owners SM0..23, norm SM24; all32 retire grid barrier; scalar consumer SM0. Full32SM RF/shared budget retained, no inactive-lane area credit.'),
        composition=dict(bindings=bindings,HC_operators=80,source_program_operations=len(token_graph['operations']),
            original_local_cycles=6854,additional_transpose_cycles=extra,
            conditional_compute_staging_cycles_operator=conditional_cycles,
            HC80_conditional_compute_staging_us=graph.fin[prior]*1e6,
            full_token_cycles=None,complete_schedule_admitted=False,
            excludes='All controller credit/loaded waits, DMA/CDC, physical collector links, grid/fence/reuse service and non-HC operators remain unpriced. Transpose addition includes conservative duplicate final-refill writes; not a complete-kernel measurement.'),
        numerical_scope=dict(software_fixtures=7,reduction_boundaries=91,target_connected_GPU_kernel_proof=False,
            reference='Existing13-stage per-fixture semantic proof only; no new campaign. Scalar mapping and exact primitive wrappers remain pending.',QC_NAM_adopt=False),
        coordination=dict(Euler_input_consumed=TRANSPORT,QC_input_consumed=PROOF,acknowledgement=False,
            request='Euler reconcile ordinary shared/INT transpose assumptions and external buffers with r3 service; QC bind scalar recipes and compiler RF liveness to target lowering. No dedicated HCP or approximate SFU.'),
        default_enabled=False,ready_to_build=False,hardware_adopted=False,headline_rate=None,
        model_generator_changed=False,pins={path:sha(path) for path in sources})


def check(r):
    for path,digest in r['pins'].items():require(sha(path)==digest,'pin drift: '+path)
    fresh=build(r['inputs']);fresh['base_commit']=r['base_commit']
    require(fresh==r,'resource composition does not reproduce')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group(required=True)
    modes.add_argument('--out',type=Path);modes.add_argument('--check',type=Path)
    ap.add_argument('--inputs',default=INPUTS);a=ap.parse_args()
    if a.check:check(json.loads(a.check.read_text()))
    else:
        with a.out.open('x') as f:json.dump(build(a.inputs),f,indent=2,sort_keys=True);f.write('\n')
    print('PASS: corrected r3 GPU HC conditional resource composition; transport/physical/full-token gates pending')


if __name__=='__main__':main()
