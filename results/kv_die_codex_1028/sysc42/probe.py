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
res={}
for mode in ('old_equality','inverted','wrong_bit'):
 L.hyp=dict(base)
 for k in sel:
  h=list(L.hyp[('gate',k)])
  if mode=='inverted':h[3]^=1
  if mode=='wrong_bit':h[2]=h[2].rsplit('[',1)[0]+'['+str((int(h[2].rsplit('[',1)[1][:-1])+1)%8)+']'
  L.hyp[('gate',k)]=tuple(h)
 m,_=L.build(with_compare=False,with_hyp=True)
 ids=[i for i,n in enumerate(m.onames) if n in {'hyp:gate:'+k for k in sel}]
 assert len(ids)==8
 m.outs=[m.outs[i] for i in ids];m.onames=[m.onames[i] for i in ids]
 res[mode]=lec.prove(m,O,1000,log,tag=mode,single_cap=8)
 print(mode,res[mode],flush=True)
 (O/'results.json').write_text(json.dumps(dict(scope='DIAGNOSTIC old AIG no KEEP, only D relations under prior untrusted candidate hypotheses; not release',results=res),indent=1))
 (O/'probe.log').write_text('\n'.join(log))
