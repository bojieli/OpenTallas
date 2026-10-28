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
L.hyp=dict(base)
m,_=L.build(with_compare=False,with_hyp=True)
result={}
for k in sorted(sel):
 g=base[('gate',k)][2]
 result[k]={}
 for sd,key in [('gold',g),('gate',k)]:
  result[k][sd]=sorted(m.inames[v-1] for v in m.cone_inputs(L.dlit[(sd,key)]))
print(json.dumps(result,indent=1))
(O/'support.json').write_text(json.dumps(result,indent=1))
