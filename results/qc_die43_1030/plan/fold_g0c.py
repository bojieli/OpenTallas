# DIE-QC-43: fold Codex macro delta (c5547024f) onto the ring-START plan (plan_straps + 35 landing_relay_start_copy)
# and run full G0C on base / ring / composite with main tools/die_plan/check.py.
import json,sys,collections,hashlib
from pathlib import Path
W=Path(sys.argv[1]);O=Path(sys.argv[2]);sys.path.insert(0,str(W/'tools/die_plan'))
import check as C
ring=json.loads((O/'plan_ring_codex.json').read_text());delta=json.loads((O/'delta_committed.json').read_text())
comp=json.loads(json.dumps(ring))
for tn,d in delta.items():
    t=comp['partition_types'][tn]
    assert not t.get('hard_cores'), tn
    t['hard_cores']=list(d['hard_cores']);t['core_pg_connect']=d['core_pg_connect']
both=sorted(set(delta)&{k for k,v in comp['partition_types'].items() if v.get('landing_relay_start_copy')})
(O/'plan_qc43.json').write_text(json.dumps(comp,indent=2)+'\n')
res={'types_macro':len(delta),'macros':sum(len(d['hard_cores']) for d in delta.values()),'types_ring':sum(1 for v in comp['partition_types'].values() if v.get('landing_relay_start_copy')),'types_both':both,
     'plan_qc43_sha256':hashlib.sha256((O/'plan_qc43.json').read_bytes()).hexdigest()}
errs={}
for name in sys.argv[3:]:
    raw=json.loads((O/(name+'.json')).read_text())
    r,summary=C.run(raw,plan_dir=O,completeness=True)
    errs[name]=r.errors();(O/(name+'_g0c.json')).write_text(json.dumps({'errors':r.errors(),'summary':summary},indent=1,default=list))
    print(name,len(r.errors()),flush=True)
key=lambda i:json.dumps(i,sort_keys=True)
base=errs.get('plan_straps',[]);bk={key(i) for i in base}
for n,e in errs.items():
    new=[i for i in e if key(i) not in bk];gone=len(bk-{key(i) for i in e})
    res[n]={'errors':len(e),'new_vs_base':len(new),'gone_vs_base':gone,'new_by_check':dict(collections.Counter(i.get('check') for i in new)),'new_sample':new[:5]}
(O/'fold_g0c.json').write_text(json.dumps(res,indent=1,default=list));print(json.dumps(res,indent=1,default=list)[:3000])
