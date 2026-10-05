#!/usr/bin/env python3
"""Explicit opt-in A8 metadata for the existing native SM descriptor ABI.

Default delegates the already released matrix-per-SM descriptor compiler.
A8 changes only source row views, compact HBM placement and fetch schedule;
no owner, value, arithmetic or result sum is created here.
"""
from dshbm_expert_workgroup_descriptor import compile_descriptors,read_expert_ids
from dshbm_expert_workgroup_interleave import chunks


def compile_descriptors_a8(ids, *, layer, die, input_job, interleave8=False):
    base=compile_descriptors(ids,layer=layer,die=die,input_job=input_job)
    if not interleave8:return base
    records=[]
    for k,e in enumerate(ids):
        for q in range(4):
            start=die*24+q*6
            records.append(dict(sm=4*k+q,slot=k,stack=q,expert=int(e),
                d_base=0,d_lines=288,op_rows=12,op_c=8,op_g=3,op_fmt=2,op_gs=1,
                load=1,xaddrs=24,compact_hbm_lines=255,pad_lines=1,
                source_views=[dict(tensor=f'layers.{layer}.ffn.experts.{int(e)}.{w}.weight',
                    scale=f'layers.{layer}.ffn.experts.{int(e)}.{w}.scale',
                    row_start=start,row_stop=start+6,native_rows=list(range(parity,12,2)))
                    for parity,w in enumerate(('w1','w3'))]))
    return dict(**{k:v for k,v in base.items() if k not in ('descriptors','weight_stream')},
        interleave8=True,descriptors=records,layout='A8 alternating w1/w3 rows; explicitly different from legacy B',
        per_stack_schedule=[c.__dict__ for c in chunks(ids)],
        weight_stream=dict(source_bytes_per_expert_stack=32640,source_line_bits=1024,
            sector_bits=256,pc_sector_j0s=[0,8,16,24,32],pc_gu_sector_count=8,
            gearbox_native_bits=1088,gearbox_native_lines=288,
            bank_set='expert%7',bank_row='ROW_BASE+expert//7',
            SM='4*router_slot+stack',padding='one zero 128B line per expert/stack'),
        w2_contract='cfg_lines is W2-only; cfg_lut maps the 136 j>=32 source lines. Caller must preserve its W2 byte/SM ordering; not qualified by GU numeric fixture',
        source_scope='AR six real IDs; no MTP-union/physical-provider/full-token qualification')

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ids-u32',required=True)
    p.add_argument('--layer',type=int,required=True);p.add_argument('--die',type=int,required=True)
    p.add_argument('--input-job',required=True);p.add_argument('--interleave8',action='store_true')
    p.add_argument('--out',required=True);a=p.parse_args()
    x=compile_descriptors_a8(read_expert_ids(a.ids_u32),layer=a.layer,die=a.die,input_job=a.input_job,interleave8=a.interleave8)
    Path(a.out).write_text(json.dumps(x,indent=2)+'\n')
