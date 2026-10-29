import json,pickle
from pathlib import Path
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
r=json.loads((w/'lec.json').read_text());points=r['unproven_points']
print('unproven',len(points),flush=True)
ks=['ff:u_dut.u_bound.u_st.cap[0]']
ks=sorted(k for k in L.gp if '.u_st.cap[' in k)[:4]
for k in ks:
 print('GOLD',k,'lit',L.gp[k],'D',L.gc.get(k),'alias',sorted(L.galias.get(k,[]))[:12],flush=True)
for k in sorted(L.tp):
 if any(x in k for x in ('vm_drained','collective_drained','crom_fault')):print('GATE',k,'lit',L.tp[k],'D',L.tc.get(k),flush=True)
for p in points[:3]:print('POINT',p['point'],'unmatched',p['cone_unmatched_keys'][:6],flush=True)
(w/'alias_inventory.json').write_text(json.dumps({'gold_caps':{k:{'lit':L.gp[k],'D':L.gc.get(k),'aliases':sorted(L.galias.get(k,[]))} for k in L.gp if '.u_st.cap[' in k},'gate_named':{k:{'lit':L.tp[k],'D':L.tc.get(k)} for k in L.tp if any(x in k for x in ('vm_drained','collective_drained','crom_fault','result_cause','result_cycles'))}},indent=2))
