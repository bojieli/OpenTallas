#!/usr/bin/env python3
"""Materialize one MU hub candidate from the same exact probe snapshot.
Only analytical placement/station generation; not P&R. Gate both axes of every segment.
Usage: materialize_mu.py ROOT HEIGHT HUB FIRST_K OUT [--route-stations]
"""
import sys,pathlib,json,copy,hashlib
root=pathlib.Path(sys.argv[1]);H=float(sys.argv[2]);tn=sys.argv[3];first=int(sys.argv[4]);out=pathlib.Path(sys.argv[5]);route='--route-stations' in sys.argv
if out.exists():raise SystemExit('output exists; preserve immutable candidate')
out.mkdir(parents=True)
# Configure precisely the R13 resolver and replica geometry used in the diagnostic.
wrapper=(root/'mu_r13_probe.py').read_text()
setup=wrapper[:wrapper.index("src=(root/")]
oldargv=list(sys.argv)
ns={'__name__':'mu_setup'};exec(compile(setup,'probe_setup','exec'),ns)
R11=ns['R11'];P=ns['P']
claude=(root/'mu_probe_claude.py').read_text()
bound=float(oldargv[oldargv.index('--bound-um')+1]) if '--bound-um' in oldargv else (3957.12 if tn=='q_hub_nw' else 3002.4)
sys.argv=['claude_probe',str(root/'tools'),str(root/'plan'),'all',str(H),str(bound)]
cn={'__name__':'mu_patch'};exec(compile(claude[:claude.index('_orig = R11.prepare')],'claude_unit_patch','exec'),cn)
part='NW_hub' if tn=='q_hub_nw' else 'NE_hub'
t,W,H0,t1,lrep=R11.prepare(P,part,tn,6,3)
t1=copy.deepcopy(t1);t1['_mu_hub_type']=tn;add=cn['patch'](t1)
rows=[];selected=None
for k in range(first,9):
 r=R11.eval_hub(t1,H0,W,H,bound,k,6,3,2,1000,route=False)
 vals=[r['cut'][a]['max_use'] for a in ('x','y')]+[s['cut_'+a] for s in r['segs'] for a in ('x','y')]
 row=dict(k=k,whole=r['cut'],segments=r['segs'],ok=max(v or 0 for v in vals)<=.6+1e-9)
 rows.append(row);print(json.dumps(dict(stage='cut',hub=tn,H=H,**row)),flush=True)
 if row['ok']:selected=k;break
if selected is None:
 (out/'FAIL.json').write_text(json.dumps(dict(hub=tn,H=H,rows=rows),indent=1)+'\n');raise SystemExit(1)
if route:r=R11.eval_hub(t1,H0,W,H,bound,selected,6,3,2,1000,route=True)
ct=copy.deepcopy(t);ct['outline_um']=[W,H];ct['hard_cores']=r['cores'];ct['internal_stations']=r['stations']
# Existing physical templates intentionally remain unqualified for MU source shapes.
ct['note']=ct.get('note','')+' | MU diagnostic model: source RTL/pin tables/rebuild and clock/PG/reset remain required'
(out/'candidate_type.json').write_text(json.dumps(ct,indent=1)+'\n')
report=dict(hub=tn,H=H,bound=bound,k=selected,add=add,cut=r['cut'],segments=r['segs'],stats=r['stats'],we_chain=r['we_chain'],cc=r['cc'],lane_model=lrep,route_stations=route)
(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(dict(stage='done',hub=tn,H=H,k=selected,route_stations=route)),flush=True)
