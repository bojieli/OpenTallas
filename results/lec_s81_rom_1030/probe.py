import json,pickle,collections
from pathlib import Path
import rom_lec as lec
r=Path(__file__).parent/'rom';out=r/'alias_chain_probe';out.mkdir(exist_ok=True);log=[]
j=json.loads((r/'lec.json').read_text());contract=lec.reset_contract_gate('/srv/opentallas-scratch2/claude/s81-kits-e/kits/rom_gb2r2_bt5',j['top']);print('EXACT_CONTRACT',contract,flush=True)
lec.abc_bin=lambda:'/home/ubuntu/.local/opentallas-tools/bin/yosys-abc'
with (r/'normalized.pkl').open('rb') as f:L=pickle.load(f)
candidates=[]
for k in sorted({k for p in j['unproven_points']for k in p['cone_unmatched_keys']}):
 assert k in L.tonly and k.replace('#t','') in L.gp,k
 candidates.append(['gate',k,['eq','gold',k.replace('#t',''),0]])
 if '.u_c2.q#t[' in k:
  up=k.replace('.u_c2.q#t[','.u_c2x.q#t[');assert up in L.tonly and up.replace('#t','') in L.gp
  candidates.append(['gate',up,['eq','gold',up.replace('#t',''),0]])
a=lec.apply_hints(L,candidates,out,1000,log,propose_only=True);print('ADDED',len(candidates),a['applied'],a['skipped'],flush=True)
assert a['applied']==len(candidates) and not a['skipped']
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='all_compare_alias',single_cap=100)
(out/'all_compare_alias.json').write_text(json.dumps(st));(out/'untrusted_alias_hints.json').write_text(json.dumps(candidates,indent=1))
print('JOINT_ALL',len(st),collections.Counter(st.values()),flush=True)
(out/'proof.log').write_text('\n'.join(log))
if any(v!='proved' for v in st.values()):print('FAIL',[k for k,v in st.items()if v!='proved'][:25],flush=True)
assert all(v=='proved' for v in st.values())
k=candidates[0][1];h=L.hyp['gate',k];L.hyp['gate',k]=h[:-1]+(1,)
mm,_=L.build(with_compare=False,with_hyp=True);i=mm.onames.index('hyp:gate:'+k);mm.outs=[mm.outs[i]];mm.onames=[mm.onames[i]]
wrong=lec.prove(mm,out,1000,log,tag='wrong_polarity',single_cap=100);print('WRONG',wrong,flush=True)
(out/'wrong_polarity.json').write_text(json.dumps(wrong));assert list(wrong.values())==['differs']
(out/'receipt.json').write_text(json.dumps(dict(status='ALL_PROVED',retained_only=True,ordinary_native_gate=False,reset_contract=contract,baseline=dict(collections.Counter(json.loads((r/'alias_probe/baseline23.json').read_text()).values())),all_compare=dict(collections.Counter(st.values())),new_aliases=len(candidates),wrong=wrong),indent=1)+'\n')
print('ROM_ALIAS_DONE',flush=True)
