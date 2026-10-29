"""Retained HCP AIG correspondence; no RTL, timing or physical change."""
import os,json,pickle,collections,hashlib
from pathlib import Path
os.environ.setdefault('OT_LEC_RESET_CYCLES','4')
import lec_engine as lec
r=Path(__file__).parent;out=r/'proof';out.mkdir(exist_ok=True);log=[]
with (r/'normalized.pkl').open('rb') as f:L=pickle.load(f)
p='ff:u_dut.u_fcore.u_core.u_core.'
old=p+'nout_r[1]';new=p+'nout_r#t[1]';partner=p+'nout_r[3]'
assert old in L.matched and new not in L.tp and partner in L.gp
assert not L.cons
# Remove the incorrect name coupling; this is only a candidate correspondence.
L.tp[new]=L.tp.pop(old);L.tc[new]=L.tc.pop(old)
L.matched=sorted(set(L.gp)&set(L.tp));L.gonly=sorted(set(L.gp)-set(L.tp));L.tonly=sorted(set(L.tp)-set(L.gp))
if ('gate',old) in L.rst_val:L.rst_val['gate',new]=L.rst_val.pop(('gate',old))
for attr in ('_qkey','_latch_cone'):
 L.__dict__.pop(attr,None)
assert L.rst_val['gate',new][0]==L.rst_val['gold',partner][0]==0
L.hyp['gate',new]=('eq','gold',partner,0)
keys=[old]+[p+'d0[%d]'%k for k in range(6,14)]
for k in keys:
 assert k in L.gonly and L.rst_val['gold',k][0]==0,k
 L.hyp['gold',k]=('const',0)
held=lec.noreset_sound(L);base={k:held.get(('gold',k)) for k in keys}
assert all(v is not None for v in base.values()),base
print('REKEY_CANDIDATE',old,'->',new,'EQ',partner,'BASE',base,flush=True)
(out/'base.json').write_text(json.dumps(base,indent=1)+'\n')
m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag='joint',single_cap=200)
print('JOINT',len(st),collections.Counter(st.values()),flush=True)
(out/'joint.json').write_text(json.dumps(st));assert all(v=='proved' for v in st.values()),'joint failed'
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200)
print('COMPARE',len(st),collections.Counter(st.values()),flush=True)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log))
if any(v!='proved' for v in st.values()):print('FAILED',[k for k,v in st.items()if v!='proved'][:30],flush=True)
assert all(v=='proved' for v in st.values()),'full compare failed'
# The same engine must refute an inverted, wrong correspondence.
L.hyp['gate',new]=('eq','gold',partner,1)
mm,_=L.build(with_compare=False,with_hyp=True);idx=mm.onames.index('hyp:gate:'+new)
mm.outs=[mm.outs[idx]];mm.onames=[mm.onames[idx]]
wrong=lec.prove(mm,out,1000,log,tag='wrong_inverse',single_cap=200)
print('WRONG_CONTROL',wrong,flush=True);(out/'wrong.json').write_text(json.dumps(wrong))
assert list(wrong.values())==['differs'],wrong
(out/'receipt.json').write_text(json.dumps(dict(status='ALL_PROVED',counts=dict(collections.Counter(st.values())),rekey=dict(old=old,new=new,partner=partner),reset_base=base,eq_reset_base=0,wrong=wrong,normalized_sha256=hashlib.sha256((r/'normalized.pkl').read_bytes()).hexdigest()),indent=1)+'\n')
print('HCP_REKEY_DONE',flush=True)
