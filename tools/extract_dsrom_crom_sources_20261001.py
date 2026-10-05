import hashlib,json,os,subprocess
from pathlib import Path
PIN='84eabdef1338455ecd0b0ee76f47745cc724b206'
CAT='25631b8754f4ec295d5d6415ca85e75f38564664'
CP='results/quality/w16_w17_nonexpert_header_census_20261001/census.json'
RP='results/quality/w16_dsrom_maintext_binding_recipes_20261001/contract.json'
def git(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
craw=git('db83b444c5c8f905e5f3903a605ea52190cc0f5e',CP);cat=json.loads(craw);rraw=git(PIN,RP);recipes=json.loads(rraw)['recipes']
base='results/quality/w16_w17_checkpoint_header_catalogue_20261001/'
hcat=json.loads(git(CAT,base+'catalogue.json'));snap=Path(hcat['snapshot'])
for key in ('config','index'):
 p=hcat[key+'_path'];assert sha((snap/p).read_bytes())==hcat[key+'_sha256']
selected={k:r for k,r in recipes.items() if r.get('recipe')=='pack_constant_from_manifest'}
assert len(selected)==409 and sum(r['stored_bytes'] for r in selected.values())==1058240
out=Path('/home/ubuntu/dsrom-crom-source-20261001');assert not out.exists();out.mkdir();(out/'raw').mkdir()
result={};count=0
for k,recipe in sorted(selected.items()):
 r=cat['tensors'][k];sh=r['shard'];b=hcat['shards'][sh];source=snap/sh
 before=source.stat();assert before.st_size==b['file_bytes']
 fd=os.open(source,os.O_RDONLY)
 try:
  hb=os.pread(fd,b['header_bytes'],8);assert sha(hb)==b['raw_header_sha256']
  raw=os.pread(fd,r['stored_bytes'],r['absolute_file_offsets'][0]);assert len(raw)==r['stored_bytes'];count+=len(raw)
 finally:os.close(fd)
 after=source.stat();assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
 dest=out/'raw'/(k+'.bin');dest.write_bytes(raw);dest.chmod(0o444)
 result[k]=dict(path=str(dest),dtype=r['dtype'],shape=r['stored_shape'],sha256=sha(raw),bytes=len(raw),shard=sh,data_offsets=r['data_offsets'],absolute_file_offsets=r['absolute_file_offsets'],raw_header_sha256=b['raw_header_sha256'],header_bytes=b['header_bytes'],source_blob_id_not_full_rehashed=b['blob_id_from_cache_path_not_rehashed'])
old=Path('/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L00_r0/w.attn_norm.bin');oldsha=sha(old.read_bytes());assert oldsha==result['layers.0.attn_norm.weight']['sha256']=='1e862a4492423ffe1663b101267ac4710ba72ec0cea51b1396ea5c9c0a1fa682'
m=dict(schema='opentallas.dsrom.actual-CROM-raw-source-subset.v1',checkpoint=dict(revision=hcat['checkpoint_revision'],snapshot=str(snap),config_sha256=hcat['config_sha256'],index_sha256=hcat['index_sha256'],catalogue_commit=CAT,census_commit='db83b444c5c8f905e5f3903a605ea52190cc0f5e',census_sha256=sha(craw),recipe_commit=PIN,recipe_sha256=sha(rraw)),tensors=result,verification=dict(tensor_count=409,checkpoint_payload_bytes_read=count,header_hashes_verified=True,source_stats_unchanged=True,all40_layers_and_finalnorm=True,L0_retained_raw_binary_matches=True,L0_existing_path=str(old),L0_existing_sha256=oldsha),authorization_scope='Fermat delegated user-authorized actualall40+headCROM writer input extraction only;1MB rawsubset;no numericdecode/engine/PnR/download',extractor_sha256=sha(Path(__file__).read_bytes()))
manifest=out/'manifest.json';manifest.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');manifest.chmod(0o444)
(out/'SHA256SUMS').write_text(''.join(r['sha256']+'  raw/'+k+'.bin\n' for k,r in sorted(result.items()))+sha(manifest.read_bytes())+'  manifest.json\n');(out/'SHA256SUMS').chmod(0o444)
print(json.dumps(dict(manifest=str(manifest),sha256=sha(manifest.read_bytes()),tensor_count=409,payload_bytes=count)))
