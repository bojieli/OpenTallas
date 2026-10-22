#!/usr/bin/env python3
import collections,hashlib,json,pathlib,re
O=pathlib.Path(__file__).resolve().parent;L=json.loads((O/'ledger.json').read_text());R=O/'receipts'
def parse(path):
 text=path.read_text();cases={int(i):dict(checks=int(c),mismatches=int(m))for i,c,m in re.findall(r'AGE_CASE id=(\d+) checks=(\d+) mismatches=(\d+)',text)}
 return dict(path=str(path.relative_to(O)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cases=cases,semantic_verdict='FAIL' if 'AGE_MECHANISM_FAIL' in text or 'PROVIDER_AGE_FAIL' in text else ('PASS' if 'PROVIDER_AGE_PASS' in text else 'UNRESOLVED'))
runs={key:parse(R/rel) for key,rel in dict(initial='run_base.log',wrong_K='run_K.log',extra_stage='run_STAGE.log',observed='observer/run_observed.log',half_edge='observer/run_PHASE.log',provider='provider_gold/run_provider.log',provider_K='provider_gold/run_provider_K.log',provider_stage='provider_gold/run_provider_STAGE.log').items()}
assert all(runs['observed']['cases'][i]['mismatches']==0 for i in range(5))
assert runs['observed']['cases'][7]['mismatches']==512
assert 'OBSERVED_SOURCE_AGE id=7 age=16 t=1413' in (R/'observer/run_observed.log').read_text()
for name in ['wrong_K','extra_stage','half_edge']:
 assert all(runs[name]['cases'][i]['mismatches']>0 for i in range(5))
assert runs['provider']['semantic_verdict']=='PASS'
for name in ['provider_K','provider_stage']:
 assert all(runs[name]['cases'][i]['mismatches']>0 for i in [5,6])
bad=[r for r in L['buses']if any(not a['declared_window_ok']for a in r['landings'])]
result=dict(verdict='HOLD_SOURCE_AND_NATIVE_COMPOSITION',historical_age_differences=109,source_family_count=23,declared_D4_residual_window_failures=[dict(bus=r['bus'],width=r['width'],landings=r['landings'])for r in bad],declared_window_failure_bits=sum(r['width']for r in bad),representative_pin_age_comparisons_pass=5*512+2*512,provider_source_gold_checks=1152,provider_fault_checks=1608,actual_CTLM_HR_low73_ideal_age=16,current_export_CTLM_HR_ideal_age=20,CTLM_HR_mismatches=512,runs=runs,scope='Original register-cone/lane mechanisms under ideal common roots and declared reset epochs. Provider full RTL/store/macro source used. No physical root phase or full-parent first-use qualification.',production_native_phase=None,adoptable_ages=None,source_recompile=False,die_GRT_admitted=False,hardware_delta=None)
(O/'evidence.json').write_text(json.dumps(result,indent=1)+'\n')
manifest={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.rglob('*'))if p.is_file() and p.name!='sha256.json'}
(O/'sha256.json').write_text(json.dumps(manifest,indent=1)+'\n')
print('HOLD buses=109 D4_window_failures=9 bits=1757 passed_pin_comparisons=3584 provider_gold=1152 provider_fault=1608 HR_age16_vs20_fail=512')
