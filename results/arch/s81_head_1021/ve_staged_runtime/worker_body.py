import base64,hashlib,json,os,pathlib,socket,time,types
r=pathlib.Path(REQUEST['run']);r.mkdir(parents=True,exist_ok=False)
receipt=r/'input_provenance';receipt.mkdir()
(receipt/'REQUEST.json').write_text(json.dumps(REQUEST,sort_keys=True)+'\n')
(r/'src').mkdir()
print('VE_STAGE_READY '+json.dumps({'run':str(r),'host':socket.gethostname(),'pid':os.getpid(),'mode':'STAGING_ONLY_NO_APPLY_NO_EDA'}),flush=True)
while not (receipt/'COPY_DONE').exists():
    if (receipt/'COPY_FAILED').exists():raise RuntimeError((receipt/'COPY_FAILED').read_text())
    time.sleep(2)
helper=base64.b64decode(REQUEST['helper_b64']);assert hashlib.sha256(helper).hexdigest()==REQUEST['helper_sha256']
module=types.ModuleType('published_infra_eco');exec(compile(helper,'published_infra_eco_continuation.py','exec'),module.__dict__)
parent=REQUEST['parent'];proof=REQUEST['proof'];cp=proof['checkpoint'];src=r/'src'
# Preserve original corner bytes and prove copied original identity before rebasing.
original_corner=(r/cp['corner_sta']).read_bytes()
assert hashlib.sha256(original_corner).hexdigest()==proof['corner_sta_original_sha256']
(receipt/'original_corner_sta.json').write_bytes(original_corner)
for rel,expected in proof['immutable_input_hashes'].items():
    assert module.file_sha(r/rel)==expected, 'original route input differs: '+rel
for entry in REQUEST['frozen_blobs']:
    raw=base64.b64decode(entry['data_b64']);assert hashlib.sha256(raw).hexdigest()==entry['sha256']
    p=src/module.relative(entry['path']);p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(raw);p.chmod(entry['mode'])
    q=r/'cl'/pathlib.Path(entry['path']).name;q.parent.mkdir(exist_ok=True,parents=True);q.write_bytes(raw);q.chmod(entry['mode'])
for rel,transform in proof['transformed_templates'].items():
    p=src/module.relative(rel)
    if transform['before_sha256'] is None:assert not p.exists()
    else:assert module.file_sha(p)==transform['before_sha256']
    p.write_text(transform['utf8'].replace('@@EXACT_SOURCE_ROOT@@',str(src)))
corner=json.loads(original_corner);corner['orfs_dir']=str(r/pathlib.Path(cp['route_base']).parents[3])
(r/cp['corner_sta']).write_text(json.dumps(corner,sort_keys=True,indent=1)+'\n')
(r/'cl/SRC_DIR').write_text(str(src)+'\n')
manifest={'schema':module.SCHEMA,'operation':'lost_hold_eco','infrastructure_cause':'scheduled_retirement',
    'parent':{'name':parent['name'],'state_sha256':module.canonical_sha(parent),'source_commit':parent['commit_full']},
    'physical_disposition':{'kind':'hold_only','source_structural_required':False,'setup_tt_ps':82.85,'hold_ff_ps':-15.07,'drc':0},
    'interrupted_eco_checkpoint':'none','source_completeness':{'known_required_source_bytes_missing':[]},
    'canonical_source_readset':proof,'checkpoint':cp,'post_sdc_files':proof['post_sdc_files'],
    'runtime':dict(proof['approved_runtime'],host='ot-epyc9',run=str(r),ram_gb=64),
    'historical_provenance':{'original_route_loaded_image_libraries':'HISTORICAL_PROVENANCE_UNVERIFIED',
        'new_runtime':'Immutable16470/25RVT; reconstructed source with exact pinned deterministic transforms. New filesystem identity; no historical tar alias.'}}
manifest['file_hashes']=module.expected_source_hashes(parent,manifest)
manifest['file_hashes'].update(module.expected_checkpoint_hashes(manifest))
manifest['file_hashes'].update({'cl/'+pathlib.Path(x['path']).name:x['sha256'] for x in parent['route_overlay_plan']['files']})
child=module.build(parent,manifest,REQUEST['new_name']);assert child['spec']['mem_cap_gb']==64
verified=module.verify_runtime(manifest)
assert not (r/'cl/linked_infra_eco').exists(), 'root owns exclusive apply and guard creation'
(receipt/'parent_state.json').write_text(json.dumps(parent,indent=1)+'\n')
(receipt/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=1)+'\n')
summary=dict(verified,mode='STAGING_ONLY_NO_APPLY_NO_READY_NO_EDA',runtime=str(r),host='ot-epyc9',
    new_name=REQUEST['new_name'],published_commit=REQUEST['published_commit'],published_helper_sha256=REQUEST['helper_sha256'],
    manifest_file_sha256=module.file_sha(receipt/'manifest.json'),parent_state_sha256=module.canonical_sha(parent),
    actual_source_files=len(module.expected_source_hashes(parent,manifest)),runtime_ram_gb=64,runtime_docker_cap_gb=64,
    original_corner_sha256=proof['corner_sta_original_sha256'],historical_provenance=manifest['historical_provenance'])
(receipt/'VERIFIED.json').write_text(json.dumps(summary,indent=1)+'\n')
print('VE_STAGE_VERIFIED '+json.dumps(summary),flush=True)
