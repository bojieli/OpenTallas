import os,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import lec
lec.abc_bin=lambda: "/home/ubuntu/.local/opentallas-tools/bin/yosys-abc"
p=Path(__file__).parent/'st_a'
os.environ['OT_LEC_SUPERSET_VEC']='1'
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
print('superset extra',len(L.superset_extra),flush=True)
keysets={"gold":set(L.gp),"gate":set(L.tp),"both":set(L.gp)&set(L.tp)}
for sd,k,h in json.load(open(p/'hyp.json')):
 h=tuple(h)
 keys=keysets[sd]
 if k not in keys:continue
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):continue
 L.hyp[sd,k]=h
m,kind=L.build()
names={e['point'] for e in json.load(open(p/'lec.json'))['failing']}
sel=[i for i,n in enumerate(m.onames) if n in names]
m.outs=[m.outs[i] for i in sel];m.onames=[m.onames[i] for i in sel]
log=[];st=lec.prove(m,p,1000,log,tag='superset72')
(p/'probe.log').write_text('\n'.join(log));(p/'probe.json').write_text(json.dumps(st,indent=2))
print({k:sum(x==k for x in st.values()) for k in set(st.values())},flush=True)
