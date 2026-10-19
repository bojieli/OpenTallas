import pathlib,json,hashlib,sys
p=pathlib.Path(sys.argv[1]).resolve();grantpath=pathlib.Path(sys.argv[2]);base=pathlib.Path(sys.argv[3]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.load(open(p/'manifest.json'));g=json.load(open(grantpath))
assert g['approved'] is True and g['owner']=='ROOT','NEW_EXACT_ROOT_GRANT_REQUIRED'
assert g['allowed_stage']=='INT8_CLONE_ECO_FEB988_V1'
assert g['manifest_sha256']==sha(p/'manifest.json')
assert g['placement_model_png_sha256']==sha(p/'placement_MODEL.png') and g['personally_reviewed_png'] is True
assert g['image']==m['native_image']
assert g['checkpoint_sha256']==m['frozen_checkpoint_sha256']
for n,h in m['files'].items():assert sha(p/n)==h,'KIT_INPUT_HASH '+n
assert sha(base/'output/cts_checkpoint.odb')==m['frozen_checkpoint_sha256'],'BASELINE_CHANGED'
assert not (p/'output').exists(),'OUTPUT_ALREADY_EXISTS_NO_RETRY'
print('EXACT_ROOT_GRANT_AND_INPUTS_PASS')
