import json,gzip,hashlib,sqlite3,zlib,collections
from pathlib import Path
root=Path.cwd();run=Path('/tmp/kepler-ds-r45-PC0-9-execution-20261002')
r=json.load(open(run/'receipt.json'));t=json.load(open(str(run)+'.terminal.json'))
assert r['status']=='PASS_SOURCE_NATIVE_PREFIX_BYTE_EXACT' and t['exit_code']==0 and t['tracked_source_unchanged']
assert r['PCs_retired']==list(range(10)) and r['last_PC']==9
refpath=root/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json';raw=refpath.read_bytes();rh=hashlib.sha256(raw).hexdigest();assert rh==r['comparison']['reference_sha256'];ref=json.loads(raw)
pc0path=root/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/parent_PC0_independent_golden.json';pc0=json.load(open(pc0path))
native=json.loads(gzip.decompress((run/'bound_native.json.gz').read_bytes()));homes=json.loads(gzip.decompress((run/'bound_homes.json.gz').read_bytes()))
original=json.loads(gzip.decompress((root/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz').read_bytes()))
expected={(d['PC'],d['version'],d['rank'],d['generation'],d['field']):d for d in ref['expectations']}
for w in original['instructions'][0]['writes']:
 v=pc0['results'][w['native_result_binding']['result']]
 for rank in range(96):
  expected[(0,w['version'],rank,1,'data')]=dict(shape=v['shape'],dtype='<f4',payload_sha256=v['golden_sha256'],home_indices=[i for i in w['home_indices'] if rank in homes[i]['rank_group']])
assert len(expected)==1568
path=Path(r['journal']['path']);db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
seen=set();counts=collections.Counter();digest=hashlib.sha256()
for blob, in db.execute('select value from event where journal=1 order by seq'):
 canonical=zlib.decompress(blob);digest.update(len(canonical).to_bytes(8,'little')+canonical);d=json.loads(canonical);a=d['identity'];key=(a['PC'],a['version'],a['rank'],a['generation'],d['field']);assert key in expected and key not in seen
 e=expected[key];assert all(d[x]==e[x] for x in ('shape','dtype','payload_sha256')) and d['byte_exact'] and d['reference_sha256']==rh
 assert d['original_reference_home_indices']==e['home_indices']
 assert d['allocated_home_records']==[homes[i] for i in a['home_indices']]
 w=next(w for w in native['instructions'][a['PC']]['writes'] if w['version']==a['version']);assert a['home_indices']==[i for i in w['home_indices'] if a['rank'] in homes[i]['rank_group']]
 seen.add(key);counts[a['PC']]+=1
assert seen==set(expected) and digest.hexdigest()==r['comparison']['journal']['framed_event_SHA256']
call_counts=collections.Counter();retired=[]
for blob, in db.execute('select value from event where journal=? order by seq',(r['journal']['journal_id'],)):
 d=json.loads(zlib.decompress(blob))['record']
 if 'template' not in d:retired.append(d);continue
 p=native['templates'][d['template']];assert d['source_native_stages']==len(p['code']) and d['native_opcode_counts']==dict(collections.Counter(i['op'] for i in p['code']))
 call_counts[(d['PC'],d['rank'],d['template'])]+=1
want=collections.Counter()
for op in native['instructions'][:10]:
 for owned in op['rank_bindings']:
  if owned.get('empty_owned_extent'):continue
  for b in owned.get('buffer_programs') or [dict(template=owned['template'])]:want[(op['pc'],owned['rank'],b['template'])]+=1
assert call_counts==want and sum(call_counts.values())==928
assert [(d['PC'],d['version']) for d in retired]==[(1,'DeepSeek.1.attn_x.55'),(5,'DeepSeek.5.win_new.61'),(8,'DeepSeek.8.o.65')]
assert all(d['producer_all_rank_reverse_retirement_complete'] and d['source_or_manifest_consumer_references']==0 for d in retired)
retained={d['version'] for d in r['retained_versions']};assert not retained.intersection(d['version'] for d in retired)
h=hashlib.sha256()
with path.open('rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
result=dict(status='PASS_PARENT_R45_COMPLETE_PC0_9_WITNESS_AND_SOURCE_CALL_REVIEW',source_commit=t['source_commit'],actual_outputs=1568,outputs_by_PC=dict(counts),actual_native_calls=928,retirement_control_records=3,source_reference_sha256=rh,PC0_reference_sha256=hashlib.sha256(pc0path.read_bytes()).hexdigest(),journal_bytes=path.stat().st_size,journal_sha256=h.hexdigest(),output_framed_sha256=digest.hexdigest(),terminal_receipt_sha256=hashlib.sha256((run/'receipt.json').read_bytes()).hexdigest(),source_unchanged=True,actual_payload_recomputed_by_parent=False,retirement_checks_scope='Matches actual control records, retained versions and source guards; not independent physical completion proof.',failed_R43_preserved=True,full_token_qualified=False,hardware_qualified=False,physical_cycles_qualified=False)
script=Path(__file__).read_bytes();dest=root/'results/uarch/native_software_parent_intake_20261002';(dest/'DS_R45_actual_PC0_9_parent_review.py').write_bytes(script);result['verification_script_sha256']=hashlib.sha256(script).hexdigest();(dest/'DS_R45_actual_PC0_9_parent_review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
