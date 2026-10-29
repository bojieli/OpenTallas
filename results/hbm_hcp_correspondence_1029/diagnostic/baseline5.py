import os,json,pickle,collections
from pathlib import Path
os.environ.setdefault('OT_LEC_RESET_CYCLES','4')
import lec_engine as lec
r=Path(__file__).parent;out=r/'baseline5';out.mkdir(exist_ok=True);log=[]
with (r/'normalized.pkl').open('rb') as f:L=pickle.load(f)
m,kind=L.build(with_compare=True,with_hyp=True)
st=lec.prove(m,out,1000,log,tag='baseline')
print('BASELINE',len(st),collections.Counter(st.values()),flush=True)
old=json.loads((r/'inputs/lec.json').read_text());oldbad={e['point'] for e in old['failing']} | {e['point'] for e in old.get('unproven_points',[])}
newbad={k for k,v in st.items() if v!='proved'}
print('SAME_FAILED',oldbad==newbad,'EXTRA',sorted(newbad-oldbad)[:20],'MISSING',sorted(oldbad-newbad)[:20],flush=True)
(out/'baseline.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log))
k='ff:u_dut.u_fcore.u_core.u_core.nout_r[1]'
for side in ('gold','gate'):
 lit=L.dlit[side,k];print('D_SUPPORT',side,[kind[v] for v in m.cone_inputs(lit)],'X',L.dxlit.get(k),flush=True)
print('BASELINE_DONE',flush=True)
