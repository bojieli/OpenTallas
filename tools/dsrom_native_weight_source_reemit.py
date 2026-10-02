#!/usr/bin/env python3
"""Independent retained emitter re-emission, with only exact weight-key patches.

Run in a fresh Python process: source imports precede owner compiler imports.
This compiles software instruction words; no RTL elaboration or payload reads.
"""
import json,gzip,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'
sys.path.insert(0,str(D/'inputs/source/tools'))
import w11_dsrom_full_tp_program as F
sys.path.insert(1,str(ROOT/'tools'))
import dsrom_native_weight_address_join as J
import dsrom_full_owner_compiler as C
import dsrom_owner_cfg_interface_export as E


def check():
    dem=json.load(gzip.open(D/'inputs/demand-r5.json.gz','rt'))
    join=J.Join(dem,C.readrows(J.PHASES));total=0;patched=0
    qm={'wq_a':'wq_a','wkv':'wkv','wq_b':'wq_b','wo_b':'wo_b','iwq_b':'indexer.wq_b','ewkv':'engram.wkv'}
    mm={'gate':'gate','wo_a':'wo_a.group0','cwkv':'compressor.wkv','cwgate':'compressor.wgate','iwk':'indexer.wk','iwp':'indexer.weights_proj'}
    for L in range(40):
        nodes=[n for n in dem['nodes'] if n['scope']==L and n['kind']=='instruction']
        original=F.jsonable(F.FullLayerBuilder(L).build_layer())
        if original!=[n['instruction'] for n in nodes]:raise ValueError('original source reemit '+str(L))
        b=F.FullLayerBuilder(L)
        for key,m in b.lay.qmat.items():
            if not isinstance(key,tuple) or key[0]!=L or not isinstance(m,dict):continue
            if len(key)==2 and key[1] in qm:alias=qm[key[1]]
            elif len(key)==3 and key[1]=='shared' and key[2] in ('w1','w3','w2'):alias='shared.'+key[2]
            elif len(key)==4 and key[1:3]==('exp',0) and key[3] in ('w1','w3','w2'):alias='exp0.'+key[3]
            else:continue
            m['base']=join.phases[(L,alias)]['source_key_word']&((1<<30)-1)
        for part in ('w1','w3','w2'):b.lay.qmat[(L,'exp_stride',part)]=4096
        for key,m in b.lay.mat.items():
            if isinstance(key,tuple) and key[0]==L and len(key)==2 and key[1] in mm:
                m['base']=join.phases[(L,mm[key[1]])]['source_key_word']&((1<<30)-1)
        emitted=F.jsonable(b.build_layer())
        if len(emitted)!=len(nodes):raise ValueError('changed instruction count')
        for n,actual in zip(nodes,emitted):
            expected=dict(n['instruction']);binding=join.binding(n['id'])
            if binding.get('address_bound'):
                for key,p in binding['address_patches'].items():expected[key]=p['new']
                patched+=1
            if actual!=expected:raise ValueError('patch source reemit mismatch '+n['id'])
            total+=1
    head=[n['instruction'] for n in dem['nodes'] if n['scope']=='head' and n['kind']=='instruction']
    if F.head_descriptors()!=head:raise ValueError('head source reemit')
    total+=len(head)
    result={'verdict':'PASS_SOURCE_REEMIT_EXACT','instructions':total,'patched_weight_instructions':patched,
        'no_nonaddress_mode_shape_predicate_or_rounding_change':True,'RTL_or_payload_reads':False}
    if (total,patched)!=(4778,1149):raise ValueError('coverage')
    print(json.dumps(result,sort_keys=True));return result

if __name__=='__main__':check()
