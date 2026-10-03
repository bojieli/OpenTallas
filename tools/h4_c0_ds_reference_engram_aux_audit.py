"""Compare admitted Engram auxiliary row bytes to independent checkpoint reads.

Audits already-produced reference; never reruns arithmetic or supplies operands.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from h4_c0_ds_whole_reference import sha,load,payload,MANIFEST
from h4_c0_ds_reference_attention_observers import UPSTREAM


def audit(manifest,reference,out):
    if sha(manifest)!=MANIFEST or sha(reference)!=UPSTREAM:raise ValueError('exact admitted and independent reference pins')
    m=load(manifest);r=load(reference);a={};pins={}
    for name in ('selected_row_ids','selected_codes','selected_exp'):
        binding=next(v for k,v in m['view_bindings'].items() if k.startswith('53/') and k.endswith('/'+name))
        p=Path(binding['path'])
        if sha(p)!=binding['sha256']:raise ValueError('admitted source row image pin')
        arr=np.load(p,allow_pickle=False)
        if arr.dtype!=np.dtype('<i8') or list(arr.shape)!=binding['shape']:raise ValueError('actual I64 source auxiliary extent')
        a[name]=arr;pins[str(p)]=sha(p)
    ids=a['selected_row_ids'].reshape(-1)
    if ids.tolist()!=r['engram_ids']:raise ValueError('original independent hash-selected row identities')
    reads={(x['tensor'],x['rows'][0]):x for x in r['checkpoint_reads'] if x.get('rows') is not None}
    checks=[]
    for i,row in enumerate(ids):
        for key,tensor,shift in [('selected_codes','layers.1.engram.embed.weight',0),('selected_exp','layers.1.engram.embed.scale',127)]:
            decoded=a[key][i];raw=decoded+shift
            if np.any(raw<0) or np.any(raw>255):raise ValueError('actual raw byte representability')
            raw=np.ascontiguousarray(raw,dtype='u1');proof=reads[(tensor,int(row))]
            if raw.nbytes!=proof['selected_raw_bytes'] or payload(raw)!=proof['selected_raw_sha256']:
                raise ValueError('released checkpoint selected row bytes differ')
            checks.append(dict(row_id=int(row),tensor=tensor,selected_raw_bytes=raw.nbytes,selected_raw_sha256=payload(raw)))
    receipt=dict(status='PASS_ADMITTED_AUX_ROWS_MATCH_INDEPENDENT_RELEASED_CHECKPOINT',rows=len(ids),row_byte_checks=len(checks),
        source_pins={str(Path(manifest).resolve()):sha(manifest),str(Path(reference).resolve()):sha(reference),str(Path(__file__).resolve()):sha(__file__),**pins},
        checks=checks,reference_reexecuted=False,runtime_operand_source=False,native_execution_qualified=False,hardware_qualified=False)
    out=Path(out)
    with out.open('x') as f:f.write(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('manifest','reference','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(**vars(a)),sort_keys=True))
