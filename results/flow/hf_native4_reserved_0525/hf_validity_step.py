from pathlib import Path
import json,hashlib,importlib.util,copy
w=Path('/out');prior=Path('/prefix');raw=json.load(open(prior/'RESULT.json'))
assert raw['native_reset']['used']==4 and raw['native_reset']['contract'] is None
assert all(v=='proved' for v in raw['cases'][0]['statuses'].values())
assert any(v=='differs' for v in raw['cases'][1]['statuses'].values())
for n,h in raw['input_hashes'].items():assert hashlib.sha256((prior/'subject'/n).read_bytes()).hexdigest()==h
s=importlib.util.spec_from_file_location('F',prior/'lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F);F.PROVE_JOBS=2
logs=[];keys=list(raw['targets']);result=dict(scope='EXISTING_OFFICIAL_RTL_X_VALIDITY_STEP_ONLY',raw_BASE_receipt=str(prior/'RESULT.json'),native4=True,no_added_masks=True,no_added_constraints=True,no_reset_override=True,source_credit=False,abi_prune_required=True,raw_universal_STEP_still_failed=True,cases=[])
def save():
 (w/'RESULT.json').write_text(json.dumps(result,indent=1)+'\n');(w/'LEMMA.log').write_text('\n'.join(logs))
for value,tag in [(0,'official_validity_STEP'),(1,'wrong_constant_STEP_negative')]:
 D=F.read_aig(prior/'subject/gold.aig');mp=F.read_map(prior/'subject/gold.map');L=F.Lec(D,mp,D,mp);L.kit_reset_ports=raw['reset_ports'];F.noreset_classify(L)
 xvars={v>>1 for v in L.gx};assert {18,19,47,48}<=xvars
 hyp={('gold',k):('const',value)for k in keys};L.hyp=copy.deepcopy(hyp);L.cons=[]
 M,_=L.build(with_compare=False,with_hyp=True);assert L.hyp==hyp and L.cons==[]
 names={'hyp:gold:'+k for k in keys};selected=[(n,o)for n,o in zip(M.onames,M.outs)if n in names];assert {n for n,o in selected}==names and len(selected)==2
 M.onames=[n for n,o in selected];M.outs=[o for n,o in selected]
 stats=F.prove(M,w,1000,logs,tag=tag,single_cap=1000);assert set(stats)==names
 result['cases'].append(dict(tag=tag,statuses=stats,passed=all(v=='proved'for v in stats.values()),anonymous_RTL_X_variables=sorted({18,19,47,48}),native_ternary_BASE={k:L.rst_val.get(('gold',k))for k in keys}));save()
 if value==0 and not all(v=='proved'for v in stats.values()):result['status']='VALIDITY_STEP_NOT_PROVED';save();raise SystemExit(2)
 if value==1 and not any(v=='differs'for v in stats.values()):result['status']='NEGATIVE_HAS_NO_COUNTEREXAMPLE';save();raise SystemExit(2)
result['status']='NATIVE4_BASE_AND_OFFICIAL_VALIDITY_STEP_PROVED_NO_ABI_CREDIT';save();print(result['status'],flush=True)
