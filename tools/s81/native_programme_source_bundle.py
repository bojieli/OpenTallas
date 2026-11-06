#!/usr/bin/env python3
"""Assemble a new source-only programme bundle; never activate a die or clear holds."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--selector',required=True)
ap.add_argument('--original-manifest',type=Path,required=True);ap.add_argument('--idle-programme',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();repo=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(repo/'tools/s81_dv'));from layer_prog.slice_source import resolve
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
if a.out.exists():raise SystemExit('Select a new output directory; prior bundles are immutable')
legacy=json.loads(a.original_manifest.read_text());entries=list(legacy['programmes']);assert len(entries)==15
entries.append(dict(path=str(a.idle_programme),sha256=sha(a.idle_programme)))
selector=json.loads((a.source_root/a.selector).read_text())
# The raw RTL is checked against every retained programme before any output.
for ent in entries:
 p=Path(ent['path']);assert sha(p)==ent['sha256'],('programme changed',p)
 old=json.loads(p.read_text())['selected_slice_source']
 for rel,digest in old['source_sha256'].items():
  if rel.endswith('.sv'):assert sha(a.source_root/rel)==digest,('selected RTL changed',rel)
a.out.mkdir(parents=True);S=a.out/'source';S.mkdir()
for rel in selector['files']+[a.selector]:
 p=S/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.source_root/rel,p)
os.environ.update(OT_S81_SELECTED_SOURCE_ROOT=str(S),OT_S81_SELECTED_ASBUILT_MANIFEST=a.selector,OT_S81_SELECTED_DEFINES=','.join(selector['defines']))
keys=['die_master','wrapper_chain','xg','ring','streamer','capture','xr','selected_hb']
rows=[];linked=0;linked_bytes=0;seen=set()
def material(src,dst):
 global linked,linked_bytes
 if str(src).endswith('.viamap.hex'):
  src=Path(src).resolve();os.link(src,dst);linked+=1;linked_bytes+=src.stat().st_size
 else:shutil.copy2(src,dst)
 return dst
for ent in entries:
 p=Path(ent['path']);data=json.loads(p.read_text());sl=data['slice'];assert sl not in seen;seen.add(sl);old=data['selected_slice_source']
 class Selected:
  inst={sl:dict(master=old['die_master'],params='' if old['selected_hb'] is None else '.HB('+str(old['selected_hb'])+')')}
 now=resolve(Selected(),sl)
 assert all(now[k]==old[k] for k in keys),('selected graph changed',sl,{k:(old[k],now[k]) for k in keys if old[k]!=now[k]})
 dest=a.out/'programmes'/sl;shutil.copytree(p.parent,dest,copy_function=material)
 data['selected_slice_source']=now
 data['source_bundle_origin']=dict(programme_path=str(p),programme_sha256=ent['sha256'],original_source_selector=old.get('selected_asbuilt_manifest'),original_source_selector_restored=False)
 (dest/'programme.json').write_text(json.dumps(data,indent=2)+'\n')
 rows.append(dict(slice=sl,programme=str((dest/'programme.json').relative_to(a.out)),sha256=sha(dest/'programme.json'),source_identity_unchanged=True,idle_actual_slice=data.get('idle_actual_slice',False),lifetime_qualified=data['lifetime_qualified'],sealed_programme_held=data['sealed_programme_held']))
assert seen=={f'u_s_{c}{t}' for c in range(8) for t in 'NS'}
assert all(not x['lifetime_qualified'] and x['sealed_programme_held'] for x in rows)
manifest=dict(schema='opentallas.s81.native_programme_source_bundle.v1',status='PARTIAL',source_programmes=16,programmes=rows,source_selector=a.selector,source_selector_sha256=sha(S/a.selector),physical_binding_qualified=False,production_enabled=False,current_wc1_adopted=False,lifetime_qualified=False,pin_cycles_added=0,legacy_bundle_manifest=str(a.original_manifest),legacy_bundle_manifest_sha256=sha(a.original_manifest),legacy_missing_bound_images=legacy['missing_bound_images'],legacy_missing_bound_image_count=len(legacy['missing_bound_images']),rom_coverage_recomputed=False,legacy_missing_slice_programmes=legacy['missing_slice_programmes'],payload_materialization='hardlinks to immutable retained ROM images; metadata copied before editing',hardlinked_image_files=linked,hardlinked_image_logical_bytes=linked_bytes,qualification='coherent explicit source selector and unchanged programme payloads only; aggregate gather/retirement, full ROM coverage and current-die integration remain open')
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k not in ['programmes','legacy_missing_bound_images']}),flush=True)
