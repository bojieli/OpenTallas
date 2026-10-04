"""Cold artifact/word/source/progress audit only; no producer or checkpoint rerun."""
from pathlib import Path
import json,hashlib,base64,struct,subprocess,gzip
B=Path(__file__).resolve().parent.parent;O=Path(__file__).resolve().parent;REPO=Path('/home/ubuntu/OpenTallas')
def sha(raw):return hashlib.sha256(raw).hexdigest()
v=json.loads((B/'Ampere.owner-terminal-snapshot.json').read_text());metadata=json.loads((B/'Ampere.source-metadata-snapshot.json').read_text());cs=json.loads((B/'Ampere.checkpoint-source-snapshot.json').read_text())
raws={}
for name,x in v['payload_files'].items():
 raw=base64.b64decode(x['base64']);assert len(raw)==x['bytes'] and sha(raw)==x['sha256'];raws[name]=raw;(O/name).write_bytes(raw)
r=json.loads(raws['terminal.json']);capture=json.loads(raws['native_capture.json']);progress=[json.loads(x) for x in raws['producer_progress.jsonl'].splitlines() if x]
assert r['verdict']=='PASS' and r['schema']=='C0_PC40_CHECKPOINT_PAYLOAD_PROOF_R1'
initial=json.loads((B/'Ampere.initial-source-pins.json').read_text());assert initial==v['source_pins']
for p,s in v['source_code'].items():assert sha(s.encode())==v['source_pins'][p]
contracts={}
for name,x in metadata['source_metadata'].items():
 raw=base64.b64decode(x['base64']);assert sha(raw)==x['sha256'];(O/name).write_bytes(raw);contracts[name]=json.loads(raw)
source_proofs=[]
for row in contracts['numeric_input_manifest_r1.json']:
 key='source/'+row['archive'];raw=v['source_code'][key].encode() if key in v['source_code'] else base64.b64decode(cs['base64'])
 actual=sha(raw);original=sha(subprocess.check_output(['git','show',row['source_commit']+':'+row['source_path']],cwd=REPO))
 assert actual==row['sha256']==original and len(raw)==row['bytes']
 source_proofs.append({'source_path':row['source_path'],'source_commit':row['source_commit'],'sha256':actual,'archive_matches_original_commit':True})
assert [x['pc'] for x in progress]==list(range(40))
historical=contracts['historical_prefix_hashes_r1.json'];assert historical['observed_PC_count']==40
for actual,old in zip(progress,historical['records']):
 assert actual['pc']==old['pc'] and actual['opcode']==old['opcode'] and actual['outputs']==old['outputs']
assert capture['producer_PC_hash_matches']==40 and capture['native_PC']==40 and capture['opcode']=='FMAX' and capture['template']=='exp' and capture['step']==0
assert capture['input_token']==9707 and capture['position']==0 and capture['source_commit']=='870c5fe581b768df28dd2998b2d0aecc24510c23'
assert capture['oracle_started'] is False and r['oracle_only_after_capture'] is True and r['oracle_input_injection'] is False
assert metadata['actual_image_manifest']['sha256']==capture['image_manifest_sha256']=='83491cd2487ec026e86b5943e0420a4efcb6830aaf35f761e20190a469fd69e7'
frames={}
for name in ('gate','negative','constant','FMAX'):
 raw=raws[name+'.bin'];assert len(raw)==512
 assert sha(raw)==capture['frames'][name]['sha256']==r['comparisons'][name]['expected_sha256']
 assert r['comparisons'][name]['words']==128 and r['comparisons'][name]['bit_mismatches']==r['comparisons'][name]['actual_nonfinite']==0
 frames[name]=struct.unpack('<128I',raw);assert all((b>>23)&255!=255 for b in frames[name])
assert frames['negative']==tuple(x^0x80000000 for x in frames['gate'])
assert all(x==0xc2ae0000 for x in frames['constant'])
def f(x):return struct.unpack('<f',struct.pack('<I',x))[0]
expected=tuple(a if f(a)>-87 else 0xc2ae0000 for a in frames['negative']);assert frames['FMAX']==expected
owner=capture['actual_gate_owner'];assert owner['source_key']==['RF',0,0,38] and owner['published'] is True and owner['logical_source_retire_PC']==40
assert owner['mirror_word_sha256']==sha(raws['gate.bin']) and owner['version']=='Qwen.39.L0.d0.gu_post.49' and capture['source_gate_lease_released'] is False
assert capture['provider']['read_lease_outstanding'] is False and capture['real_RF_or_HBM_handshake'] is False and capture['whole_token_completed'] is False
journal=[json.loads(x) for x in v['journal_jsonl'].splitlines() if x];rows=[x for x in journal if x.get('_PID')=='918356']
finished=[]
for x in rows:
 try:value=json.loads(x.get('MESSAGE',''))
 except json.JSONDecodeError:continue
 if value.get('event')=='SOURCE_PRODUCER_POSTHASH_MATCH':finished.append(value['PC'])
 if value.get('schema')=='C0_PC40_CHECKPOINT_PAYLOAD_PROOF_R1':assert value==r
assert finished==list(range(40)) and not v['original_PID_exists']
invocations={x['_SYSTEMD_INVOCATION_ID'] for x in rows if '_SYSTEMD_INVOCATION_ID' in x};assert len(invocations)==1
assert v['service_properties']['MainPID']=='0' and v['service_properties']['ActiveState']=='inactive'
wrapper=v['source_code']['source/tools/h4_c0_pc40_payload_r1.py']
assert wrapper.index("(out/'native_capture.json').write_bytes(canonical(frozen))")<wrapper.index('import torch')
# Retained properties have been collected/reset; never synthesize historical exit RC.
exit_preserved=v['service_properties']['ExecMainCode']!='0'
assert not exit_preserved
review={'status':'PASS_INDEPENDENT_SCOPED_RELEASED_PAYLOAD_ARTIFACT_AUDIT_WITH_EXIT_RC_RETENTION_GAP','schema':'SAGAN_PC40_RELEASED_PAYLOAD_COLD_AUDIT_V1','source_commit':capture['source_commit'],'source_numeric_inputs_verified_against_original_commit':source_proofs,'job_wrapper_sha256':v['source_pins']['source/tools/h4_c0_pc40_payload_r1.py'],'all_6_live_snapshot_source_pins_unchanged':True,'producer_PCs_0_39':40,'producer_hash_comparison_fields':sum(len(x['outputs']) for x in progress),'source_PC40_frame_words_checked':512,'byte_frame_mismatches':0,'independent_NEG_XOR_constant_FMAX_bit_checks':True,'independent_checkpoint_oracle_recomputed_by_reviewer':False,'checkpoint_oracle_expected_hashes':'Producer frozen expected SHA compared directly against all saved frame bytes; checkpoint arithmetic itself was executed by producer after capture','image_manifest':metadata['actual_image_manifest'],'checkpoint_provenance':r['checkpoint_provenance'],'actual_RF38_source_owner':owner,'source_gate_lease_released':False,'read_lease_outstanding':False,'original_producer_PID':918356,'original_producer_PID_absent':True,'original_journal_invocation_id':next(iter(invocations)),'journal_final_result_matches_payload_receipt':True,'runtime_process_exit_RC':'NOT_INDEPENDENTLY_RETAINED','current_collected_unit_properties':v['service_properties'],'unit_success_alone_not_numerical_proof':True,'elapsed_s':r['elapsed_s'],'maxrss_bytes':r['maxrss_bytes'],'scope':'Actual released Qwen checkpoint software PCs0..39 followed by selected PC40 NEG/constant/FMAX 128word aperture, after-capture oracle comparison. Comparison-only payload proof, not hardware provider movement.','strict_limits':['Only first128 selected gate rows at PC40; remaining whole program/token is not executed','Logical software RF mirrors and source lease do not establish real RTL RF/HBM handshake','Workspace17/18/19 installation, production caller identity, ACK_ID and calendar/physical joins remain unqualified','Checkpoint shard and tensor read provenance is sealed producer evidence; no additional full shard or checkpoint numerical rerun by reviewer','Historical exact OS exit code no longer retained by collected transient unit; journal final result and artifact proof preserved independently','Popper bareACK fixture and actual software payload are parallel proofs, not an integrated production gate'],'hardware_payload_join':False,'ACK_ID_qualified':False,'fulltoken_qualified':False,'no_producer_or_numerical_prefix_rerun':True}
(O/'review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
(O/'source_archive.json.gz').write_bytes(gzip.compress(json.dumps(v['source_code'],sort_keys=True).encode(),mtime=0))
(O/'journal.jsonl').write_text(v['journal_jsonl'])
(O/'owner_snapshot.json.gz').write_bytes(gzip.compress(json.dumps(v,sort_keys=True).encode(),mtime=0))
(O/'source_metadata_snapshot.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
(O/'checkpoint_source_snapshot.json').write_text(json.dumps(cs,indent=2,sort_keys=True)+'\n')
(O/'artifact_manifest.json').write_text(json.dumps({'artifacts':{p.name:sha(p.read_bytes()) for p in O.iterdir() if p.is_file() and p.name!='artifact_manifest.json'},'numeric_source_pins':source_proofs,'actual_wrapper_source_sha256':v['source_pins']['source/tools/h4_c0_pc40_payload_r1.py'],'job_outputs_unmodified':True},indent=2,sort_keys=True)+'\n')
print(json.dumps({k:review[k] for k in ['status','producer_PCs_0_39','producer_hash_comparison_fields','source_PC40_frame_words_checked','byte_frame_mismatches','runtime_process_exit_RC']},indent=2))
