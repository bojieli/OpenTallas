#!/usr/bin/env python3
"""Finite serial HEAD INT8 component images; full row coverage, explicit VM->STREAM gap.

No source-bound HN frontend, shared calendar, or STREAM publisher is implied.
One existing SM component service is reused in row order; no parallel speedup.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]

def plan(rows=18992,columns=4096,partitions=16,chunk_rows=512):
    if min(rows,columns,partitions,chunk_rows)<1: raise ValueError('positive dimensions and capacities required')
    groups=(columns+511)//512
    limit=(256*16)//groups
    if chunk_rows>limit: raise ValueError(f'chunk exceeds DD256: at most {limit} rows for K={columns}')
    part_rows=(rows+partitions-1)//partitions
    chunks=[]
    for part in range(partitions):
        lo,hi=part*part_rows,min((part+1)*part_rows,rows)
        for offset in range(0,max(0,hi-lo),chunk_rows):
            count=min(chunk_rows,hi-lo-offset)
            chunks.append(dict(index=len(chunks),logical_partition=part,partition_offset=offset,rows=count,
                global_row_begin=lo+offset,global_row_end=lo+offset+count,
                descriptors=(count*groups+15)//16,
                packed_hbm_bytes=((count*groups+15)//16)*64*136,physical_component_service=0,
                output=dict(space='STREAM',format='FP32',words=count,order='ascending global row',
                    source='existing SM writer reduced-and-packed VM results; never raw SM rdata column partials',
                    vm_sector_count=(count+7)//8,vm_word_order='bits[32*lane+:32], lane0 first',
                    drain_cycles=None,drain_status='MISSING_SELECTED_VM_READ_TO_STREAM_CONTRACT')))
    if [c['global_row_begin'] for c in chunks] != [0]+[c['global_row_end'] for c in chunks[:-1]] or chunks[-1]['global_row_end']!=rows:
        raise AssertionError('HEAD row coverage has a gap or overlap')
    return dict(schema='opentallas.qwen.head_chunks.v1',rows=rows,columns=columns,logical_partitions=partitions,
        chunk_rows=chunk_rows,chunks=chunks,serialized_executions=len(chunks),physical_services_used=1,
        total_output_words=rows,total_output_bytes=4*rows,weight_code_bytes=rows*columns,
        packed_hbm_bytes=sum(c['packed_hbm_bytes'] for c in chunks),serial_fp32_publication_edges_if_one_word_per_edge=rows,
        required_events=['selected source logical-partition to physical-service map',
            'finite descriptor/programme publication per chunk',
            'existing SM writer retirement before VM read',
            'qualified VM read and FP32 STREAM publication/drain before next chunk overwrites VM',
            'selected frontend/HN backend command adapter and exact INT8 numerical qualification'],
        installable=False,performance_qualified=False)

def verify_packed_weights(comp):
    """Decode actual 136B packets back to captured INT8 rows, including idle/tail lanes."""
    from hbm_svc_packed136_image import sector_address
    checked=0; packets=0
    for rec in comp['kinds'][0]['recs']:
        W=rec['W']; K=rec['K']; groups=rec['Gn']
        items=[(r,g) for r in range(rec['R']) for g in range(groups)]
        for bi,block in enumerate(rec['blocks']):
            own=items[16*bi:16*(bi+1)]
            slots=[(own[wave+slot][0],own[wave+slot][1],t) if wave+slot<len(own) else None
                   for wave in (0,8) for t in range(8) for slot in range(8)]
            for p,word in enumerate(block['lines']):
                if word>>1024: raise ValueError('nonzero padding above packed INT8 payload')
                for half in range(2):
                    it=slots[2*p+half]
                    for lane in range(64):
                        index=(it[1]*64+lane)*8+it[2] if it is not None else K
                        expected=int(W[it[0],index])&255 if it is not None and index<K else 0
                        if (word>>(half*512+lane*8))&255 != expected:
                            raise ValueError(f'HEAD packed weight order mismatch block={bi} packet={p} half={half} lane={lane}')
                        checked+=1
                packets+=1
            raw=b''.join(int(w).to_bytes(136,'little') for w in block['lines'])
            sectors=(len(raw)+127)//128*4
            alloc=dict(pcs=[0,1,2,3],row_base=block['dram_row']>>3,stack_bytes=1<<35)
            actual=b''.join(int(comp['mem'][sector_address(o+512*(block['dram_row']&7),alloc)]).to_bytes(32,'little') for o in range(sectors))
            if actual[:len(raw)]!=raw or any(actual[len(raw):]): raise ValueError('HEAD HBM sector publication mismatch')
    return dict(packet_lines=packets,code_bytes_including_padding=checked,bit_exact=True)

def compile_chunks(kv,layer,rank,out,*,partitions=16,chunk_rows=512,rows=18992,columns=4096):
    import numpy as np
    import sm_slice_lower as S
    result=plan(rows,columns,partitions,chunk_rows)
    out.mkdir(parents=True,exist_ok=True)
    for chunk in result['chunks']:
        comp=S.compile_qwen_sm(kv,layer,chunk['logical_partition'],rank=rank,tags=('head',),
            partitions=partitions,row_chunk=(chunk['partition_offset'],chunk['rows']))
        rec=comp['kinds'][0]['recs'][0]
        if rec['m']!=rows or rec['K']!=columns or rec['row0']!=chunk['global_row_begin']:
            raise ValueError('captured HEAD shape/row identity differs from explicit plan')
        weight_order=verify_packed_weights(comp)
        budget=comp['budget']
        if budget['descriptors']>256 or budget['store_top']>2048: raise ValueError('finite producer capacity exceeded')
        d=out/f"chunk{chunk['index']:03d}";d.mkdir(exist_ok=True)
        # These are the actual existing service compiler words, not a synthetic high-level record.
        (d/'ingress.mem').write_text(''.join(f'{t} {word:x}\n' for t,word in comp['ing']))
        (d/'activation.mem').write_text(''.join(f'{t} {word:x}\n' for t,word in comp['xw']))
        (d/'hbm.mem').write_text(''.join(f'{addr:x} {word:064x}\n' for addr,word in sorted(comp['mem'].items())))
        (d/'expected_fp32.mem').write_text(''.join(f'{int(word):08x}\n' for word in np.asarray(rec['o'],np.uint32)))
        chunk['component']=dict(weight_order=weight_order,budget=budget,ingress_words=len(comp['ing']),activation_beats=len(comp['xw']),
            hbm_sectors=len(comp['mem']),weight_image_installation='fixture file only; selected production allocation/publication cost UNKNOWN',last_ingress_edge=max(t for t,_ in comp['ing']),
            last_command_edge=comp['ops'][-1]['last_cmd_abs'],
            compiler_drain_edges=S.SB.DRAIN,component_end_edge=comp['n_end'],
            writer_retirement_bound_edges=S.RES_LAT,
            earliest_vm_read_edge=comp['ops'][-1]['last_cmd_abs']+S.RES_LAT,
            next_chunk_component_reuse_not_before=comp['n_end'],
            next_chunk_start=None,next_chunk_status='hold until explicit output drain completes')
        (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--partitions',type=int,default=16);p.add_argument('--chunk-rows',type=int,default=512)
    p.add_argument('--rows',type=int,default=18992);p.add_argument('--columns',type=int,default=4096)
    p.add_argument('--kv',type=Path);p.add_argument('--layer',type=int,default=0);p.add_argument('--rank',type=int,default=0)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.kv: result=compile_chunks(a.kv,a.layer,a.rank,a.out,partitions=a.partitions,chunk_rows=a.chunk_rows,rows=a.rows,columns=a.columns)
    else:
        result=plan(a.rows,a.columns,a.partitions,a.chunk_rows);a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('rows','columns','logical_partitions','serialized_executions','installable')}))
