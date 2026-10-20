from pathlib import Path
import sys,json,copy,hashlib
sys.path.insert(0,'/audit/cand/tools/ref_tile')
import native_census as N
import pre_route_gate as P
r=json.loads(Path('/audit/candidate_new.json').read_text());before=copy.deepcopy(r)
g=P.Gate();assert P.check_native_census(g,'GATE_NATIVE_CENSUS_RESULT '+json.dumps(r))
assert r==before and r['status']=='FAIL' and r['max_dynamic_loads']==34 and len(r['violations'])==15
assert any(i['severity']=='WARN' for i in g.items)
checks=['actual_gate_warn_raw_fail_preserved']
for change in ['missing_node','extra_node','wrong_driver','wrong_net','loads','max','missing_lib','other_top','role_error']:
 bad=copy.deepcopy(r)
 if change=='missing_node':bad['violations'].pop()
 elif change=='extra_node':bad['violations'].append(bad['violations'][0])
 elif change=='wrong_driver':bad['violations'][0]['driver']+='x'
 elif change=='wrong_net':bad['violations'][0]['net']+='x'
 elif change=='loads':bad['violations'][0]['loads']=33
 elif change=='max':bad['max_dynamic_loads']=35
 elif change=='missing_lib':bad['liberty'].pop()
 elif change=='other_top':bad['top']+='x'
 elif change=='role_error':bad['role_errors']=['injected unknown Liberty pin']
 assert not N.ktree_scoped_admission(bad),change
 assert not P.check_native_census(P.Gate(),'GATE_NATIVE_CENSUS_RESULT '+json.dumps(bad)),change
 checks.append(change+'_refused')
manifest={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in Path('/audit').glob('*.json')}
Path('/audit/actual_gate_checks.json').write_text(json.dumps({'checks':checks,'gate_items':g.items,'raw_reports':manifest},indent=2)+'\n')
print('ACTUAL_GATE_WARN_AND_9_SIGNATURE_NEGATIVES_PASS')
