"""Actual residual soft cells and direct net cuts, for physical placement decisions.
Usage: scorer_residual_census.py ASBUILT OUTPUT
No source changes or invented hard cores; count actual flattened cells only.
"""
from pathlib import Path
import collections,json,re,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E
a,out=map(Path,sys.argv[1:]);d=json.loads(a.read_text());F=E.flatten(d,'hbm_current_native_top')
packet=json.loads(Path(__file__).with_name('scorer_exact_packet.json').read_text())
prefix={x['source_path']:'HARD:'+x['partition']+'/'+x['plan_inst'] for x in packet['exact_children']}
kb=json.loads(Path(__file__).with_name('keybuf_active_map.json').read_text())
prefix.update({x['source_path']:'HARD:'+x['partition']+'/'+x['plan_inst'] for x in kb['active']})
anchors={x['prefix']:x['candidate_partition'] for x in packet['residual_proposals']}
ordered=sorted(prefix,key=len,reverse=True);soft=sorted(anchors,key=len,reverse=True)
groups={};drivers=collections.defaultdict(set);loads=collections.defaultdict(set);records={}
for ci,c in enumerate(F.cells):
    if not c.path.startswith('hb_idx__s_'):g='OUTSIDE'
    else:
        g=next((prefix[p] for p in ordered if c.path==p or c.path.startswith(p+'.')),None)
        if g is None:g=next(p for p in soft if c.path==p or c.path.startswith(p+'.'))
    groups[ci]=g
    if g in anchors:
        r=records.setdefault(g,dict(candidate_partition=anchors[g],cells=0,modules=collections.Counter(),register_bits=0,named_cells=[]))
        r['cells']+=1;r['modules'][c.module]+=1
        if c.module in ('$dff','$adff','$sdff','$dffe','$adffe','$dlatch','$adlatch'):r['register_bits']+=len(c.ports.get('Q',[]))
        if not c.module.startswith('$'):r['named_cells'].append(dict(path=c.path,module=c.module,params=c.params,port_widths={p:len(v) for p,v in c.ports.items()}))
    for p,bits in c.ports.items():
        for n in bits:
            if not isinstance(n,int):continue
            (drivers if c.dirs[p]=='output' else loads)[n].add(g)
for g,r in records.items():
    r['input_cut_bits']=sum(g in ls and any(x!=g for x in drivers[n]) for n,ls in loads.items())
    r['output_cut_bits']=sum(g in ds and any(x!=g for x in loads[n]) for n,ds in drivers.items())
    r['modules']=dict(r['modules']);r['status']='SOFT_PLACEMENT_REQUIRED'
rec=dict(schema='opentallas.hbm.scorer_residual_census.v1',groups=records,soft_cells=sum(r['cells'] for r in records.values()),register_bits=sum(r['register_bits'] for r in records.values()),note='Direct net cut bits, not geometric reach or pin-fit qualification. Hard child paths override residual prefixes; no hard core duplication.')
out.write_text(json.dumps(rec,indent=2)+'\n');print('softgroups',len(records),'cells',rec['soft_cells'],'registerbits',rec['register_bits'])
