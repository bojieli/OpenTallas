from pathlib import Path
import json,gzip,hashlib,subprocess
p=Path('results/arch/kv_ledger_current_main_native_validation_1019')
def load(q): return json.loads(q.read_text())
def digest(q): return hashlib.sha256(q.read_bytes()).hexdigest()
before=load(p/'identity_before_completion.json'); after=load(p/'identity_after_completion.json'); assert before==after
old=json.load(gzip.open('/home/ubuntu/artifacts/kv-gen8-ledger-fix-1019/packet/input_manifest_v3.json.gz','rt'))['files']
cohorts={};baseline_class=[]
for shape in ['baseline','candidate']:
 cohorts[shape]={}
 for family,rel in [('alias',f'evidence_v2/{shape}/alias'),('parameters',f'evidence/{shape}/parameters'),('unsigned_policy',f'evidence/{shape}/unsigned_parameters'),('unsigned_actual_flow',f'evidence_unsigned_flow/{shape}')]:
  r=load(p/rel/'result.json');cohorts[shape][family]=dict(tests=r['tests'],passed=len(r['passed']),failures=len(r['failures']),errors=len(r['errors']),exit_code=int((p/rel/'exit_code').read_text()))
  if shape=='candidate': assert r['successful'] and not r['skipped']
  if shape=='baseline' and family=='alias':
   for kind in ['failures','errors']:
    for name,trace in r[kind]:
     end=trace.splitlines()[-1]
     classification='expected exception not raised' if end=='AssertionError: ValueError not raised' else 'refused for a different earlier reason' if 'does not match' in end else 'KeyError before intended check'
     baseline_class.append(dict(test=name,classification=classification,last_trace_line=end))
source_sets=[]
for shape in ['baseline','candidate']:
 for q in sorted((p/f'evidence_v2/{shape}/alias/outputs').glob('*/inventory.json')):
  r=load(q); assert all(old.get(k)==v for k,v in r['sources'].items()),q
  source_sets.append(r['sources'])
assert len(source_sets)==26 and all(x==source_sets[0] for x in source_sets)
main=json.load(gzip.open(p/'current_main_archive_manifest.json.gz','rt'))['files']
allowed={'tools/qwen_kv_die/kv_expand.py','tools/qwen_kv_die/kv_expand_parameters.py','tools/qwen_kv_die/test_kv_expand_parameters.py','tools/qwen_kv_die/test_kv_expand_alias.py','tools/qwen_kv_die/test_kv_expand_unsigned_flow.py'}
loaded_checks=[]
for q in p.rglob('result.json'):
 r=load(q);shape='candidate' if '/candidate/' in str(q) else 'baseline'
 for path,sha in r['loaded_modules'].items():
  rel=path.split('/'+shape+'/',1)[1]
  if rel not in allowed: assert main[rel]==sha,(q,rel)
 loaded_checks.append(str(q.relative_to(p)))
source={name:digest(Path(name)) for name in sorted(allowed) if Path(name).exists()}
expected={'tools/qwen_kv_die/kv_expand.py':'8cf4e4bf33354de4e0801e97d7446d5c785937a4ab7b6631246d80a24cc41054','tools/qwen_kv_die/kv_expand_parameters.py':'b6e99a5a24e7d5001c58aba2e7acebbf213c3466c48d4bac8a877186cba276ed'}
assert all(source[k]==v for k,v in expected.items())
for q in (p/'evidence_v2/candidate/alias/result.json',p/'evidence_v2/baseline/alias/result.json'):
 r=load(q);shape='candidate' if '/candidate/' in str(q) else 'baseline'
 for path,sha in r['loaded_modules'].items():
  rel=path.split('/'+shape+'/',1)[1]
  if rel in expected and shape=='candidate': assert expected[rel]==sha
param='tools/qwen_kv_die/kv_expand_parameters.py';base=subprocess.check_output(['git','show','efae17de:'+param]);cand=Path(param).read_bytes(); marker=b'def artifact_identity';assert base[base.index(marker):]==cand[cand.index(marker):]
report=dict(schema='opentallas.kv_current_main_helper_validation.v1',main_base='efae17de2128f3813aff8cf76226e8be8d60ea97',main_results_only_successor='a15e7c6db',source_candidate='716f993f9',source_code_changed_after_review=False,cohorts=cohorts,baseline_alias_classification=baseline_class,original_fixture_setup_errors=dict(baseline=13,candidate=13,classification='predecessor-only face_land_rtl API; not causal refusal evidence'),fixture_adaptation='replace predecessor-only face_land_rtl assertion with current-main FACE_LAND_TILES master+_fl plus actualfile existence; real require_closed selector/Yosys/producer/binder unchanged',source_sha256=source,loaded_dependency_current_main_match=True,loaded_dependency_reports=loaded_checks,all26_actual_alias_input_inventories_match_frozen_predecessor_manifest=True,actual_alias_input_file_count=len(source_sets[0]),frozen_source_view_generator_and_live_v4_input_hashes_unchanged=True,artifact_identity_preserve_verify_bound_suffix_byte_identical=True,source_adoption='ROOT review required; no activation',qualification='DIAGNOSTIC_COMPONENT_ONLY',holds=['native receipt absent: strict REFUSE','reset296 fanout/current whole-element PG/contact safety unqualified','original live v4 unchanged','offline912-row proposal not installed','no bulk ledger continuation/gates/reroutes/production publication/runtime activation'])
(p/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
manifest={str(q.relative_to(p)):digest(q) for q in sorted(p.rglob('*')) if q.is_file() and q.name!='sha256.json'}
(p/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(cohorts=cohorts,files=len(manifest),identity_checks='PASS'),indent=2))
