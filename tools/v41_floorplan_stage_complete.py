#!/usr/bin/env python3
"""Proposed complete stage payload/bank reservation; refuses unapproved physical bindings."""
import argparse,json,math,hashlib,struct
from pathlib import Path
import v41_floorplan_stage_bankmap as B
ROOT=B.ROOT

def build(snapshot):
    x=B.derive(snapshot,17,0); macros=json.loads((ROOT/'physical/asap7_memory_macros/index.json').read_text())['macros']; macro=macros['ot_rom_8192x274_m8']; dense=[]; seen=set(); total=0; nextbank=x['reservation']['macros']
    ts={t['tensor']:t for t in x['unbound_dense_tensors']}
    for name,t in ts.items():
        if name in seen:continue
        shape=t['shape']; rows=shape[0]; sources=[name]; mode='replicated'; axis=None
        if name.endswith('.scale') and name[:-6]+'.weight' in ts:continue
        if t['dtype']=='F8_E4M3':
            sc=name[:-7]+'.scale';sources.append(sc);seen.add(sc)
            cols=shape[1]
            if '.wo_b.' in name:cols//=4;axis=1
            else:rows//=4;axis=0
            if '.wo_a.' in name:
                payload=rows*cols*2; mode='offline_FP8_scale_to_BF16_exact_dequant'; lanes=8; bits=256
                # Conservative eight local banks of 8 BF16 lanes each.
                useful_per_macro=8192*256//8; count=math.ceil(payload/(8*useful_per_macro))*8
            else:
                payload=rows*(cols+cols//32);mode='FP8_264bit_per32codes_scale_replicated_per_output_row';bits=264;lanes=8
                count=math.ceil((math.ceil(rows/8)*(cols//32))/8192)*8
        else:
            payload=t['full_tensor_bytes'];bits=264;lanes=1
            if '.gate.weight' in name or '.attn_sink' in name:rows//=4;payload//=4;axis=0;mode='output_row_quarter'
            count=math.ceil(payload/(8192*264//8))
        dense.append(dict(tensor=name,source_tensors=sources,source_shape=shape,rank_shape=[rows]+([cols] if len(shape)==2 and t['dtype']=='F8_E4M3' else shape[1:]),split_axis=axis,representation=mode,payload_bytes=payload,macro_first=nextbank,macro_count=count,macro_payload_bits=bits,parallel_bank_count=lanes,physical_binding='proposed reservation; raw non-QE banks require adapter and port scheduling',local_group='ROM_MAC.dense_QE' if t['dtype']=='F8_E4M3' and '.wo_a.' not in name else 'ROM_MAC.ME' if '.wo_a.' in name else 'VM.CONSTANT_HE'))
        nextbank+=count;total+=payload;seen.update(sources)
    placement=json.loads((ROOT/'results/arch/v41_die_placement.json').read_text());cap=math.floor(placement['rom_bytes_per_die']);idx=json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map'];tables=[]
    for n in sorted(k for k in idx if k.endswith('engram.embed.weight')):
        def metadata(k):
            with open(snapshot/idx[k],'rb') as f:l=struct.unpack('<Q',f.read(8))[0];raw=f.read(l)
            return json.loads(raw)[k],hashlib.sha256(raw).hexdigest()
        w,h=metadata(n);s,hs=metadata(n[:-7]+'.scale');assert w['shape'][1]==256 and s['shape']==[w['shape'][0],8]
        tables.append(dict(tensor=n,rows=w['shape'][0],row_bytes=264,header_sha256=h,scale_header_sha256=hs))
    table_rows=sum(t['rows'] for t in tables);eg_dies=placement['counts']['engram']; dedicated_rows=eg_dies*(cap//264)
    headroom=placement['head_die_spare_bytes'];head_rows=max(0,math.floor(headroom/264))*4
    residual=table_rows-dedicated_rows-head_rows;q,rem=divmod(residual,112); ordinal=17*4
    start=dedicated_rows+head_rows+ordinal*q+min(ordinal,rem);nrows=q+(ordinal<rem);intervals=[];base=0
    for t in tables:
        lo=max(start,base);hi=min(start+nrows,base+t['rows'])
        if lo<hi:intervals.append(dict(tensor=t['tensor'],row_begin=lo-base,row_end=hi-base))
        base+=t['rows']
    # One 264-byte row is eight264-bit words, i.e.1024 rows/macro.
    spill_count=math.ceil(nrows/1024);spillpayload=nrows*264;known=x['reservation']['payload_bytes']+total+spillpayload
    return dict(schema='opentallas.v41.stage17_complete_reservation.v1',status='proposal_rejected_capacity_and_physical_bindings_pending',
        checkpoint=x['checkpoint_revision'],source_sha256=x['source_sha256'],expert_manifest='results/floorplan/v41_stage17_bankmap.json',
        expert_payload_bytes=x['reservation']['payload_bytes'],expert_macros=x['reservation']['macros'],dense_reservations=dense,dense_payload_bytes=total,
        spill_proposal=dict(status='new integer equal-row split proposal; not prior adopted assignment',tables=tables,dedicated_table_die_rows=dedicated_rows,head_die_rows=head_rows,layer_spill_rows=residual,layer_die_ordinal=ordinal,rows=nrows,intervals=intervals,payload_bytes=spillpayload,macro_first=nextbank,macro_count=spill_count,physical_binding='264-bit words with8reads/row; gatherports and wholefabric table-routing unbound'),
        totals=dict(payload_bytes=known,logical_capacity_bytes=cap,payload_excess_bytes=known-cap,macros=nextbank+spill_count,predictive_macro_area_mm2=(nextbank+spill_count)*macro['area_um2']/1e6,physical_macro_bytes=(nextbank+spill_count)*8192*274//8,capacity_pass=known<=cap),
        root_options=[dict(action='move spill rows off stage17',minimum_rows_to_remove=math.ceil(max(0,known-cap)/264),cost='other dies need explicit capacity and routing map; preserve complete table coverage'),dict(action='move whole routed expert to adjacent stage',payload_freed_per_expert_bytes=3*1566720,minimum_experts=math.ceil(max(0,known-cap)/(3*1566720)),cost='changes expert activation forwarding and ordered sum schedule; reverify numerical order'),dict(action='store wo_a compact and dequantize near ME',payload_saving_upper_bound_bytes=16777216-(2097152*(32+1)//8),cost='new decoder bandwidth/latency/rounding contract; not approved')],
        unresolved=['raw constants/HC banking port contract','selected expert MAC replication vs critical path','Engram mapping globally approved and routed','ECC','whole-stage executable program','full physical placement and power'])

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--snapshot',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();p.output.write_text(json.dumps(build(p.snapshot),indent=2)+'\n')
