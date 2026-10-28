from pathlib import Path
import json,lec
P=Path('/old');O=Path('/work');log=[]
L=lec.Lec(lec.read_aig(P/'gold.aig'),lec.read_map(P/'gold.map'),lec.read_aig(P/'gate.aig'),lec.read_map(P/'gate.map'))
base={(s,k):tuple(v) for s,k,v in json.load(open(P/'hyp.json'))}
for s,k,v in json.load(open(P/'hints.json')):
 if len(v)==4 and v[0]=='eq':base[(s,k)]=tuple(v)
points={'gold':L.gp,'gate':L.tp}
valid=lambda sd,k,h: k in points['gold' if sd=='both' else sd] and (h[0]!='eq' or (h[2] in points[h[1]] and (sd!='both' or h[2] in L.tp)))
before=len(base);base={(sd,k):h for (sd,k),h in base.items() if valid(sd,k,h)}
print('OLD_DIAGNOSTIC_CANDIDATES',before,'compatible',len(base),flush=True)
sel={k for s,k in base if k.startswith('ff:u_dut._8039') or k in ('ff:u_dut._80400_','ff:u_dut._80365_')}
sel={k for k in sel if base.get(('gate',k),('','',''))[2].startswith('ff:u_dut.u_bound.u_dcal.cfg_data[')}
assert len(sel)==8,sel

support=json.load(open(O/'support.json'));new={}
for k in sorted(sel):
 gd=[x[5:] for x in support[k]['gold'] if x.startswith('gold:ff:u_dut.u_bound.u_dcal.u_seq.cfg_data[')]
 td=[x[5:] for x in support[k]['gate'] if x.startswith('gate:ff:u_dut._')]
 assert len(gd)==1 and len(td)==1,(k,gd,td)
 new[td[0]]=('eq','gold',gd[0],0)
assert len(new)==8,new
(O/'derived_candidates.json').write_text(json.dumps(new,indent=1))
lec.noreset_classify(L)
print('PREDECESSOR_BASE',[(k,L.rst_val.get(('gate',k)),L.rst_val.get(('gold',h[2]))) for k,h in new.items()],flush=True)

L.hyp=dict(base);L.hyp.update({('gate',k):tuple(h) for k,h in new.items()})
m,_=L.build(with_compare=True,with_hyp=True)
wanted={x['point'] for x in json.load(open(P/'lec.json'))['unproven_points']}
ids=[i for i,n in enumerate(m.onames) if n in wanted];assert len(ids)==42,len(ids)
m.outs=[m.outs[i] for i in ids];m.onames=[m.onames[i] for i in ids]
res=lec.prove(m,O,1000,log,tag='compare42',single_cap=42)
print('COMPARE42',res,flush=True)
(O/'compare42.json').write_text(json.dumps(dict(scope='DIAGNOSTIC old AIG no KEEP; 42 comparisons with exact8 predecessor candidates; not release',results=res),indent=1))
(O/'compare42.log').write_text('\n'.join(log))
