#!/usr/bin/env python3
"""Finite ordinary GPU QK/PV dot calendars for TP96 attention.

No numeric evaluator, no golden operands, no RTL. Covers dot instructions and
resident scratch only. Softmax/EXP, division, RoPE and transport remain explicit
unpriced phases; these records cannot admit a full attention kernel by themselves.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from w19_gpu_simd_contract import chunk_program, schedule_warps

ROOT=Path(__file__).resolve().parents[1]


def dot_program(leaves):
    if leaves not in [16,32]:raise ValueError('power-of-two warp subtree only')
    p=copy.deepcopy(chunk_program())
    if leaves==16:
        p=[i for i in p if not (i['op']=='SHFL_PAIR' and i['attributes']['offset']==16)
           and not (i['op']=='FADD' and i['attributes'].get('predicate')=='lane % 32 == 0')]
    p[-1]['attributes']['predicate']=f'lane % {leaves} == 0'
    return p


def dot_calendar(leaves,warps):
    p=dot_program(leaves);c=schedule_warps(p,warps)
    live=set();peak=0
    for ins in reversed(p):
        peak=max(peak,len(live|({ins['dst']} if ins['dst'] else set())))
        live.discard(ins['dst']);live.update(s for s in ins['src'] if not s.startswith('@'))
        peak=max(peak,len(live))
    if peak+8>32:raise ValueError('fullshape per-thread RF capacity exceeded')
    c.update(peak_live_value_registers=peak,reserved_address_loop_registers=8,
             RF_read_ports=2,RF_write_ports=1)
    return c


def profile(rows):
    if rows not in [128,640]:raise ValueError('actual full-window profile128 or128+512')
    local_rows=rows//32
    remaining=local_rows*2;qk_waves=[]
    while remaining:
        warps=min(32,remaining)
        qk_waves.append(dict(rows=warps//2,warps=warps,calendar=dot_calendar(32,warps)))
        remaining-=warps
    # QK64chunks/key: two warp32 subtrees then one FP32 ADD. Collectors
    # use ordinary LDS32, FADD, STS:2*2+9+3=16 candidate cycles/wave.
    qk=sum(w['calendar']['cycles']+16 for w in qk_waves)
    if rows==128:
        pv_waves=[dict(chunk_start=0,chunks_per_output=16,warp_subtree=16,
                       calendar=dot_calendar(16,8))]
        pv=pv_waves[0]['calendar']['cycles']
    else:
        pv_waves=[dict(chunk_start=0,chunks_per_output=64,warp_subtree=32,
                       calendar=dot_calendar(32,32)),
                  dict(chunk_start=64,chunks_per_output=16,warp_subtree=16,
                       calendar=dot_calendar(16,8))]
        # First64chunks: two32 trees->ADD. Last16:ADD(+0) to32, then
        # ADD(+0) to64, then ADD(first64,last64). Keep paddedtree ops.
        pv=sum(w['calendar']['cycles'] for w in pv_waves)+16+(2+2*9+3)+(2*2+9+3)
    qk_keys=local_rows*512*2;pv_keys=rows*16*2
    # Keep source rows until routed transpose ACK and destination rows until
    # PV consumers finish. This explicitly counts both layouts, not aliasing.
    live=qk_keys+pv_keys+512*4+rows*4+max(local_rows*64*4,16*128*4)+4096
    if live>65536:raise ValueError('fullshape shared capacity exceeded')
    return dict(rows=rows,head_width=512,active_head_owners=64,SMs_per_rank=32,
       QK=dict(assignment='SMs0..31 contiguous local_rows; two contiguous chunk32 warp subtrees/key',
               chunks_per_key=64,waves=qk_waves,compute_cycles_candidate=qk,
               products_per_rank=rows*512,final_two_partial_collector_cycles_per_wave_candidate=16),
       PV=dict(assignment='SMs0..31 each16 consecutive output dims; contiguous key order/window then selection',
               outputs_per_SM=16,chunks_per_output=rows//8,waves=pv_waves,
               padded_chunk_count=1<<((rows//8-1).bit_length()),
               compute_cycles_candidate=pv,products_per_rank=rows*512,
               padded_tail='for640rows, last16chunks growto32+0 thento64+0, then combine first64 onleft'),
       staging=dict(source_QK_key_bytes_SM=qk_keys,destination_PV_key_bytes_SM=pv_keys,
                    rounded_Q_as_F32_bytes_SM=2048,rounded_EXP_as_F32_bytes_SM=rows*4,
                    partial_scratch_bytes_SM=max(local_rows*64*4,16*128*4),
                    control_bytes_SM=4096,total_live_bytes_SM=live,
                    key_transpose_bytes_rank=rows*512*2,Q_broadcast_bytes_rank=32*512*4,
                    EXP_broadcast_bytes_rank=32*rows*4,
                    byte_format='keys BF16 from actual decoded window/selected rows; Q and EXP explicitly goldenBF16 rounded then widened before dot; coefficients stagedF32 views'),
       barriers=['actual KV commit/publication epoch validated before row reads',
                 'Q BF16 rounding+staging beforeQK','allQK scores retired beforemax/EXP',
                 'max+EXP+denominator completed beforePV/outputDIV','keytranspose writes consumed/ACK before source reuse',
                 'PV+DIV+BF16+inverseRoPE retire beforeWoa activation publish'],
       unpriced=['Q and EXP BF16round/widen instruction calendars','max/EXP/denominator,DIV512,outputBF16,inverseRoPE',
                 'KV decode/fetch,transpose bank arbitration/NoC,DMA,CDC,collector broadcast/fences',
                 'shared byteenable/ports/area/routes +RF/register allocation +fullshape physical admission'],
       full_attention_cycles=None,connected_exactness=False)


def build():
    paths=['tools/w19_gpu_attention_dots.py','tools/w19_gpu_simd_contract.py','tools/w19_hbm_tp96_isa.py',
           'tools/hdc_golden_v41.py','tools/hdc_golden.py','results/rtl/w19_hbm_tp96_program_oreduce.json']
    prog=json.loads((ROOT/paths[-1]).read_text())
    bindings=[dict(layer=l['layer'],op=o['id'],profile_rows=640 if o['yarn'] else 128,
                   owners=o['ranks']) for l in prog['layers'] for o in l['ops']
              if o['kind']=='local' and o['fn']=='attend']
    return dict(schema='opentallas.w19.gpu-attention-dot-calendars.v1',status='PARTIAL_KERNEL_MODEL_NOT_ADMITTED',
                source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                source_graph_binding=bindings,profiles=[profile(128),profile(640)],
                clock_GHz=.9,full_token_cycles=None,adopted=False,physical_qualified=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():ap.error('refuse overwrite')
    a.out.write_text(json.dumps(build(),indent=2)+'\n')
