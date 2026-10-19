#!/usr/bin/env python3
"""Declare exact static-QK head child node-beat outputs intentionally unused.

The pinned static parent removes its V/node-beat face and 32 node-beat relay
children. Its sixteen CLOSED lane8 children retain their nb pins internally.
Only that parent role is admitted; no master-wide lane8 output exemption.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import kv_output_pads as O
P=O.P
ROOT=O.ROOT
SOURCES={
 'rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s.sv':'a095738e457696598f1aaf50d507bc3c50314f760b35765a224433d2ebde628f',
 'tools/qwen_kv_die/head_st_rtl.py':'acfe66bc661401c27cb93443633c5cb4a9012eb2face4f400ff7c8fe1d4b1994',
}
PARENTS={'qkd_rhead':'ot_qkh_head_native_r4_s','qkd_rhead_ft':'ot_qkh_head_native_r4_ft_s'}


def derive(run,die,root=ROOT,existing=None):
    for name,sha in SOURCES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('static head role source changed; re-prove intentionally absent V/node-beat face: '+name)
    frames=json.loads((run/'expand.json').read_text())['frames']
    _,_,_,pre=P.parse_die(str(run/'case_kv/die.v.preexp'))
    params_path=run/'case_kv/die.v.params.json';params=json.loads(params_path.read_text()) if params_path.exists() else {}
    parents={}
    for master,inst,prm,cm in pre:
        if master not in PARENTS:continue
        if inst in parents or prm or params.get(inst):raise ValueError('ambiguous/parameterized static head '+inst)
        if frames.get(master,{}).get('module')!=PARENTS[master]:raise ValueError('head frame is not the pinned static-QK role')
        if any(p in cm for p in ('nb','nb_d','ck_nb1','ck_nb2')):raise ValueError('parent still exposes node-beat face')
        parents[inst]=master
    counts=Counter(parents.values())
    for master,count in counts.items():
        if frames[master]['instances']!=count:raise ValueError('head parent census mismatch')
    nets,top_inputs,top_outputs,ins=P.parse_die(str(die));cells={i:(m,p,c)for m,i,p,c in ins}
    if len(cells)!=len(ins):raise ValueError('duplicate expanded instance identity')
    targets={};target_nets=set()
    for parent in sorted(parents):
        net='n_'+parent+'__nb_t'
        if nets.get(net)!=(1024,0):raise ValueError('static child-only node-beat width changed '+parent)
        target_nets.add(net)
        for lane in range(16):
            inst=f'{parent}__g_t_{lane}__u_l8'
            if inst not in cells:raise ValueError('static lane child missing '+inst)
            master,prm,cm=cells[inst]
            expected=[(net,k)for k in reversed(range(64*lane,64*(lane+1)))]
            if master!='ot_qkh_lane8' or prm or params.get(inst) or P.expr_bits(cm.get('nb',''),nets)!=expected:
                raise ValueError('static child nb identity/role changed '+inst)
            targets[inst]=master
    if target_nets & (top_inputs | top_outputs):raise ValueError('node-beat net is exposed at a top face')
    # Count every other occurrence conservatively, including unfamiliar output ports.
    # A single consumer, duplicate driver, expression or assign blocks the whole affected role.
    for master,inst,prm,cm in ins:
        if master=='__assign__' and any(re.search(r'\b'+re.escape(n)+r'\b',inst) for n in target_nets):
            raise ValueError('node-beat net has an assign/alias consumer')
        for port,expr in cm.items():
            if inst in targets and port=='nb':continue
            bits=P.expr_bits(expr,nets)
            referenced={b[0]for b in bits} if bits is not None else set(re.findall(r'[A-Za-z_][A-Za-z_0-9$]*',expr))
            if referenced & target_nets:raise ValueError('static node-beat output has another driver/consumer: '+inst+'.'+port)
    doc=json.loads(json.dumps(existing or dict(pads={},instances={})))
    current_die_sha=hashlib.sha256(die.read_bytes()).hexdigest()
    previous=doc.get('source_contract',{}).get('die_sha256')
    if previous and previous!=current_die_sha:raise ValueError('existing relay pads derive from a different die')
    # Never leave a master-wide nb permission that could exempt dynamic heads sharing this closed lane8.
    global_ports=doc.setdefault('pads',{}).get('ot_qkh_lane8',{})
    if isinstance(global_ports,dict):global_ports.pop('nb',None)
    for inst,master in targets.items():
        ent=doc.setdefault('instances',{}).setdefault(inst,dict(master=master,ports={}))
        if ent.get('master')!=master:raise ValueError('existing instance declaration names a different master')
        ent.setdefault('ports',{})['nb']=[[0,63]]
        ent['reason']='Pinned static-QK parent intentionally removes V/node-beat output and its relay children; exact child nb slice has no other driver or consumer'
    doc['static_head_unused_contract']=dict(source_sha256=SOURCES,preexpand_sha256=hashlib.sha256((run/'case_kv/die.v.preexp').read_bytes()).hexdigest(),
        expand_sha256=hashlib.sha256((run/'expand.json').read_bytes()).hexdigest(),die_sha256=current_die_sha,
        parents=parents,child_outputs=len(targets),bits=64*len(targets))
    return doc


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--die',type=Path,required=True);ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--existing',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=derive(a.run,a.die,a.root,json.loads(a.existing.read_text()) if a.existing else None);a.out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:v for k,v in doc['static_head_unused_contract'].items() if k!='parents'}))
if __name__=='__main__':main()
