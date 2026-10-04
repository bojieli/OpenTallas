#!/usr/bin/env python3
"""Export captured DS layer entry, never synthesize prior-layer activations.

Consumes existing captured state and an explicit layer/position/lineage record.
No checkpoint reader, compiler, simulator or job launcher is invoked here.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import hdc_replay_v41 as R


def digest(*arrays):
    return hashlib.sha256(b''.join(np.asarray(a,dtype='<f4').tobytes() for a in arrays)).hexdigest()


def entry(arrays, receipt):
    for key in ('layer','position'):
        if type(receipt.get(key)) is not int or receipt[key] < 0:
            raise ValueError('explicit nonnegative '+key+' required')
    layer=receipt['layer']
    if not 0<=layer<len(R.RATIO):raise ValueError('layer outside retained product')
    ratio=R.RATIO[layer]
    source=max((x for x in R.KV_SRC if x<=layer),default=None) if ratio else None
    if (source is not None and type(receipt.get('kv_source_layer')) is not int) or receipt.get('kv_source_layer')!=source:raise ValueError('KV ownership differs from retained layer map')
    values={}
    for key,tail in [('h_in',(4,5120)),('pre_in',(4,)),('win',(512,)),('ckv',(512,)),('ik',(128,))]:
        if key not in arrays:raise ValueError('missing captured '+key)
        a=np.asarray(arrays[key])
        if a.dtype!=np.float32 or not np.isfinite(a).all():raise ValueError(key+' must be captured finite FP32 stored values')
        if key in ('h_in','pre_in'):
            if a.shape!=tail:raise ValueError(key+' full mHC shape mismatch')
        elif a.ndim!=2 or a.shape[1:]!=tail:raise ValueError(key+' row shape mismatch')
        values[key]=a.copy()
    if not np.array_equal(G.to_bf16(values['h_in']),values['h_in']):raise ValueError('residual must match retained BF16-valued contract')
    if len(values['win'])>127:raise ValueError('window capacity exceeded')
    if len(values['ckv'])!=len(values['ik']):raise ValueError('compressed KV/index-key global rows differ')
    pos=receipt['position']
    nrows=pos//ratio if ratio else 0
    if len(values['ckv'])!=nrows:raise ValueError('compressed row count differs from actual group cadence')
    if 'open_group' not in arrays:raise ValueError('missing compressor open group')
    group=np.asarray(arrays['open_group'])
    slots=pos%ratio if ratio else 0
    if group.dtype!=np.float32 or group.shape!=(slots,2,512) or not np.isfinite(group).all():raise ValueError('compressor open kv/score slot shape mismatch')
    values['open_group']=group.copy()
    if receipt.get('open_group_positions')!=list(range(pos-slots,pos)):raise ValueError('open compressor slot lineage mismatch')
    wp=receipt.get('window_positions');ids=receipt.get('compressed_row_ids')
    for key in ('window_positions','compressed_row_ids','open_group_positions'):
        xs=receipt.get(key)
        if type(xs) is not list or any(type(x) is not int or x<0 for x in xs):raise ValueError('typed nonnegative '+key+' required')
    if wp!=list(range(max(0,pos-127),pos)):raise ValueError('entry window must contain all chronological prior rows')
    if len(wp)!=len(values['win']):raise ValueError('window position/data count mismatch')
    if ids!=list(range(len(values['ckv']))):raise ValueError('compressed global IDs must be explicit dense chronological rows')
    if digest(values['h_in'],values['pre_in'])!=receipt.get('input_sha256'):raise ValueError('captured mHC/pre-mix lineage mismatch')
    for key in ('win','ckv','ik','open_group'):
        if digest(values[key])!=receipt.get('state_sha256',{}).get(key):raise ValueError('captured '+key+' source digest mismatch')
    # Same arithmetic tree and VM bases as Rank.__init__/write_rt; not np.sum.
    layout=R.ShapeLayout(R.SHIPPED,tp_exact=True).vm.map
    h=values['h_in'].reshape(-1)
    values['ssx']=np.array([V.csum(G.mul(h,h))],dtype=np.float32)
    words={}
    for key,base in [('h_in',layout['H']),('pre_in',layout['PF']),('ssx',layout['SSX'])]:
        for i,bits in enumerate(values[key].reshape(-1).view(np.uint32)):
            a=base+i
            if not 0<=a<1<<19 or a in words:raise ValueError('native VM overlap or address overflow')
            words[a]=int(bits)
    report={'layer':receipt['layer'],'position':pos,'kv_source_layer':receipt['kv_source_layer'],
            'residual_elements':20480,'pre_mix_elements':4,'native_VM_elements':len(words),
            'window_rows':len(values['win']),'compressed_rows':len(values['ckv']),'index_keys':len(values['ik']),
            'index_score_shape':[len(values['ckv'])], 'compressor_open_slots':slots,
            'state_bytes':{k:v.nbytes for k,v in values.items()},
            'lineage':receipt,'scope':'captured entry exporter only; no layer program/weight/caller/physical or full-token admission'}
    return values,words,report


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with np.load(a.state,allow_pickle=False) as z:values,words,report=entry(z,json.loads(a.receipt.read_text()))
    a.out.mkdir(parents=True,exist_ok=False)
    # Sparse element-addressed VM image, the runtime's existing @address ABI.
    (a.out/'vm_init.hex').write_text(''.join(f'@{addr:x}\n{bits:08x}\n' for addr,bits in sorted(words.items())))
    np.savez(a.out/'service_entry.npz',**values)
    report['inputs']={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [a.state,a.receipt]}
    report['output_sha256']={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in a.out.iterdir()}
    (a.out/'entry.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
