from pathlib import Path
import json,re,collections
R=Path('/srv/opentallas-scratch2/claude/die-s81-47/bind_ev2/out')
FIELDS=Path('/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/down_cap_safe_fields_1131')
OUT=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200')
OUT.mkdir(exist_ok=True)
names=json.loads((R/'bind_names.json').read_text())
top=(R/'rtl/s81_bound_top.sv').read_text()
parts={inst:mod for mod,inst in re.findall(r'(?m)^    (\w+)(?: #\([^\n]*\))? (\w+) \(',top)}
defs={}
for p in (R/'rtl').glob('*.sv'):
 text=p.read_text();match=re.search(r'(?m)^module (\w+)',text)
 if not match:continue
 module=match[1]
 for master,args,local in re.findall(r'(?m)^    (dsfd_bf_(?:col|front_roots)) #\(([^\n]+)\) (\w+) \(',text):
  defs[module,local]=dict(master=master,parameters=args,definition=p.name)
wrappers=[];images=[];fields={};missing=[]
for emitted,original in names.items():
 part,local=emitted.split('.',1)
 record=defs.get((parts.get(part),local))
 if record is None:continue
 m=re.fullmatch(r'(u_f_\d[LR]\d+)\.u_r(\d+)\.u_e(\d+)([ew]?)',original)
 if not m:raise ValueError(('unexpected original identity',original))
 frame,row,pair,side=m.groups();pair=int(pair)
 if frame not in fields:
  f=json.loads((FIELDS/frame/'field.json').read_text())
  assert f['frame']==frame
  phases=[dict(phase=p['phase'],op=p['op'],rows=p['rows'],seg=p['seg'],nseg=p['nseg'],bf_pairs=p['bf_pairs'],calendar=p['calendar'],descriptor_count=len(p.get('desc',{}))) for p in f['phases'] if p.get('fmt')=='bf16']
  fields[frame]=dict(master=f['master'],bf_pairs=f['bf_pairs'],phases=phases)
 assert pair in fields[frame]['bf_pairs']
 wrappers.append(dict(emitted=emitted,original=original,**record))
 if record['master']=='dsfd_bf_front_roots':
  assert not side
  continue
 assert side in ('e','w') and '.MB(0)' in record['parameters']
 for bank in (0,1):
  source=FIELDS/frame/'images'/f'{frame}_e{pair}{side}_{bank}.viamap.hex'
  if not source.is_file():missing.append(str(source));continue
  images.append(dict(original_column=original,candidate_selector=original+f'_{bank}',source=str(source),bytes=source.stat().st_size,
                     frame=frame,row=int(row),pair=pair,side=side,bank=bank,macro='ot_rom_4096x274_m8'))
assert not missing,missing[:3]
counts=collections.Counter(x['master'] for x in wrappers)
assert counts==dict(dsfd_bf_col=456,dsfd_bf_front_roots=228),counts
assert len(images)==len({x['candidate_selector'] for x in images})==912
assert len(fields)==72
result=dict(status='PASS_NATIVE_BF_IDENTITY_AND_EXISTING_IMAGE_JOIN',native_source=str(R),source_images=str(FIELDS),emitted_definition_counts=dict(collections.Counter(x['master'] for x in defs.values())),
            actual_wrapper_counts=dict(counts),frames=len(fields),images=len(images),missing_images=missing,
            frame_BF_count_histogram=dict(collections.Counter(len(f['bf_pairs']) for f in fields.values())),wrappers=wrappers,images_join=images,field_classes=fields,
            production_enabled=False,reset_or_mission_qualified=False,canonical_manifest_changed=False)
(OUT/'native_image_join.json').write_text(json.dumps(result,indent=1)+'\n')
print(result['status'],counts,len(images),len(fields),flush=True)
