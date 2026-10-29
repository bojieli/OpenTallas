import sys,json,pickle,hashlib,importlib.util,copy
from pathlib import Path
from collections import Counter
base=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sp=importlib.util.spec_from_file_location('lec',base/'lec_conditional.py');m=importlib.util.module_from_spec(sp);sys.modules['lec']=m;sp.loader.exec_module(m)
with (base/'q0_loaded_coupon5/normalized_state.pkl').open('rb') as f:L=pickle.load(f)
a,_=L.build(with_compare=True,with_hyp=True);a.write(out/'original_reconstructed.aig');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(out/'original_reconstructed.aig')=='f0315f084196f130a51a3f93d3ed9610084465f36570ec31f8f8e02e3e484217'
h=json.load(open(base/'q0_loaded_coupon5/hints.json'));new=[]
for k in sorted(L.gonly):
 if k.endswith(('.rq_g','.rq_v')):
  guard=k.rsplit('.',1)[0]+'.rq_valid';assert guard in L.gp
  new.append(['gold',k,['load_once',0,[[[guard,1]]]]])
assert len(new)==2,new
h+=new;log=[];r=m.apply_hints(L,h,out,1000,log);print('PROPOSED',new,flush=True);print('HINTS',r['applied'],'DROP',r['dropped'],'LOAD_ONCE',r['load_once'],flush=True)
a,kind=L.build(with_compare=True,with_hyp=True);s=m.prove(a,out,1000,log,tag='miter_load_once');counts=dict(Counter(s.values()));print('COUNTS',counts,flush=True)
kit=Path('/srv/opentallas-scratch2/claude/codex-kv-1028/ectl/fp/kits/qkd_ectlk_q0__216x172.8');decl,missing,const=m.kept_registers(L,kit/'lec/gold.keep');rec={'original_miter_sha256':sha(out/'original_reconstructed.aig'),'new_tool_sha256':sha(base/'lec_conditional.py'),'hint_report':r,'counts':counts,'kept':{'declared':len(decl),'missing':missing,'constant_proved':len(const)},'point_failures':[k for k,v in s.items() if v!='proved']};(out/'result.json').write_text(json.dumps(rec,indent=1)+'\n');(out/'hints.json').write_text(json.dumps(h,indent=1)+'\n');(out/'proof.log').write_text('\n'.join(log))
assert not rec['point_failures'],rec['point_failures'][:5]
assert not missing,missing[:5]
with (out/'proved_state.pkl').open('wb') as f:pickle.dump(L,f)
for label,change in [('wrong_constant',lambda e:e[2].__setitem__(1,1)),('wrong_enable',lambda e:e[2][2][0][0].__setitem__(1,0))]:
 trial=copy.deepcopy(L);bad=copy.deepcopy(new[0]);change(bad);dd=out/label;dd.mkdir();lg=[];rr=m.apply_hints(trial,[bad],dd,1000,lg);caught=bad[1] in rr['dropped'] or bool(rr['skipped']) or bool(rr['load_once_refused']);(dd/'result.json').write_text(json.dumps({'caught':caught,'report':rr},indent=1)+'\n');(dd/'proof.log').write_text('\n'.join(lg));print('CONTROL',label,caught,flush=True);assert caught,label
print('Q0_FROZEN_LOAD_ONCE_PASS',counts,'keptmissing',len(missing),flush=True)
