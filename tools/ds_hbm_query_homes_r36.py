"""Charge every emitted compound query field after actual r33 state occupancy."""
import math
from ds_hbm_finite_state_homes_r30 import output_spec

def compile_homes(native,initial):
    cursor={r:33554432+initial['per_rank_total_reserved_bytes'][str(r)] for r in range(96)};out=[]
    for op in native['instructions']:
        if op['family']!='index_q':continue
        for rb in op['rank_bindings']:
            if rb.get('empty_owned_extent'):continue
            rank=rb['rank'];t=native['templates'][rb['template']]
            for w in op['writes']:
                if w['native_result_binding']['result']!='iqf':continue
                for field in op['compound_output_fields']['iqf']:
                    spec=output_spec(t,field);length=(spec['bytes']+511)//512*512;base=cursor[rank]
                    if base+length>67108864:raise BufferError('source compound fields exceed actual state capacity')
                    out.append(dict(PC=op['pc'],version=w['version'],rank=rank,field=field,generation=1,base=base,reservation_bytes=length,**spec));cursor[rank]+=length
    return dict(source_native_sha256=native['source_native_sha256'],original_reserved_bytes_per_rank=initial['per_rank_total_reserved_bytes'],rows=out,per_rank_added_bytes={str(r):cursor[r]-33554432-initial['per_rank_total_reserved_bytes'][str(r)] for r in cursor},state_capacity_per_rank=33554432,final_reserved_bytes_per_rank={str(r):cursor[r]-33554432 for r in cursor},hardware_admitted=False)
