from pathlib import Path
import json,re,hashlib,os,shutil
R=Path.cwd();D=R/'capture_gutter_v1';D.mkdir(exist_ok=True);d=json.load(open(R/'native_macro_binding.json'));moves=[]
for row in d['rows']:
 m=re.fullmatch(r'm([01])\.g_bank\\\[(\d+)\\\]\.u_b\.genblk1\.genblk1\.g_m11\.u_m',row['actual_native_name']);assert m,row['actual_native_name'];family,bank=map(int,m.groups());shift=(8.64 if family==1 or bank>=8 else 0)+(8.64 if family==1 and bank>=8 else 0);old=row['planned_xy_um'][:];row['planned_xy_um'][1]=round(old[1]+shift,6)
 if shift:moves.append(dict(instance=row['actual_native_name'],old_xy_um=old,new_xy_um=row['planned_xy_um'],delta_um=[0,shift]))
assert len(moves)==24
original=(R/'native_macro_binding.json').read_bytes();d.update(status='PREP_TWO_HORIZONTAL_CAPTURE_GUTTERS',baseline_binding_sha256=hashlib.sha256(original).hexdigest(),all_xy_orient_preserved=False,only_name_tokens_changed=False,position_variant=dict(gutters_um=8.64,outline_changed=False,source_or_ABI_or_cycle_changed=False,moves=moves));(D/'native_macro_binding.json').write_text(json.dumps(d,indent=2)+'\n')
text='foreach {inst master x y orient} {\n'+''.join('  {'+q['actual_native_name']+'} '+q['master']+' '+str(q['planned_xy_um'][0])+' '+str(q['planned_xy_um'][1])+' '+q['planned_orient']+'\n'for q in d['rows'])+'} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n';(D/'macro_placement_capture_gutters.tcl').write_text(text)
for name in ['freeze.json','clock_roots.json','macro_ownership.json','sram.lef','std.lef']:
 p=D/name
 if not p.exists():p.symlink_to(R/name)
shutil.copyfile(R/'capture_geometry.py',D/'capture_geometry.py');print('PREP',D,'moves',len(moves))
