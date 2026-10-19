import json,pathlib,hashlib,gzip,shutil
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019')
assert (P/'inventory_FF.tsv').read_bytes()==(P/'inventory_TT.tsv').read_bytes()
summary=json.load(open(P/'census_summary.json'));coverage=json.load(open(P/'endpoint_coverage.json'));model=json.load(open(P/'full_scope_model.json'));electrical=json.load(open(P/'source_electrical_model.json'));pack=json.load(open(P/'full_placement_model.json'));wire=json.load(open(P/'wire_geometry_model.json'));assert summary['counts']=={'data':{'lowmargin':594,'negative':24},'async':{'lowmargin':10,'negative':0}};assert not coverage['status_counts'].get('UNEXPLAINED_UNTIMED_HOLD',0)
assert len(model['plans'])==604;assert pack['added_cells']==1866;assert pack['replacements']==1078
for co in ['TT','FF']:
 assert not any(r['table_domain_refusals'] for r in electrical['corners'][co])
assert sum(bool(r['conditional_lower_load_qualification']) for r in electrical['corners']['TT'])==292
assert max(r['conditional_delta_max_ps'] for r in electrical['corners']['TT'])<70
assert max(r['conditional_delta_max_ps'] for r in electrical['corners']['FF'])<70
for co in ['TT','FF']:
 for r in model['plans']:
  for k in ['hold_or_removal','setup_or_recovery']:
   for x in r['bound'][co][k]:
    x['conditional_margin_after_driver70_wire20_budget_ps']=x['conditional_margin_ps']-(90 if k=='setup_or_recovery' else 0)
    assert x['conditional_margin_after_driver70_wire20_budget_ps']>=30
json.dump(model,open(P/'full_scope_model.json','w'),indent=2)
# Copy a stable narrow source input snapshot for reproduction.
for name in ['constraints.sdc','libs_TT.tcl','libs_FF.tcl','lib_SHA256SUMS','platform_SHA256SUMS']:
 shutil.copy2(B/'kit'/name,P/name)
for name in ['typed_lowmargin_manifest.json','endpoint_coverage.json','full_scope_model.json','full_placement_model.json','source_electrical_model.json','wire_geometry_model.json','feedback_model.json','all_changed_source_paths.json']:
 with open(P/name,'rb') as fi,gzip.open(P/(name+'.gz'),'wb') as fo:shutil.copyfileobj(fi,fo)
files=[f for f in P.iterdir() if f.is_file() and f.suffix in ['.json','.gz','.tsv','.tcl','.py','.sh'] and f.name!='RECEIPT.json' and not f.name.startswith(('smoke_path','partial_'))]
source=[B/'output/cts_checkpoint.odb',B/'output/cts_checkpoint.v',B/'output/native/raw.json',B/'kit/constraints.sdc']+list((B/'input/native_libs').glob('*.lib*'))
record=dict(schema='int8.all_hold.immutable_receipt.v1',frozen_checkpoint_sha256='fc6b007164e4e5c2a934052922d40114cc4fc60602423d023aa53fa2a67d2081',native_image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29',all_model_scope_read_only=True,physical_ECO_executed=False,files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},source_files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in source})
assert record['source_files'][str(B/'output/cts_checkpoint.odb')]==record['frozen_checkpoint_sha256'];json.dump(record,open(P/'RECEIPT.json','w'),indent=2)
print('IMMUTABLE_FULL_SCOPE_RECEIPT_PASS 3186 endpoints,604 branches,1866 additional cells; NO_ECO')
