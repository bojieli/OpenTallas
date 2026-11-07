from pathlib import Path
import json,shutil
r=Path('/srv/opentallas-scratch3/claude/codex-hbm-su-1107')
s=r/'kits/opsa_rest_vH2';d=r/'kits/opsa_rest_vH3';assert not d.exists()
d.mkdir();(d/'.keep').touch()
for p in s.iterdir():
 if p.name in ['run','lec','lec_async.runs','face_shell_work','__pycache__','signoff'] or p.name.startswith(('FAIL','lec_async.')):continue
 if p.is_dir():shutil.copytree(p,d/p.name,symlinks=True)
 elif p.is_file():shutil.copy2(p,d/p.name)
g=json.loads((r/'hop_midpoint_guides.json').read_text())
spec=' '.join('{'+b['name']+' {'+' '.join('{'+p+'}' for p in b['prefixes'])+'} '+' '.join(map(str,b['box_um']))+'}' for b in g['boxes'])
body=(r/'repo/physical/die_plan/hbm_arch_cores/macro_reg_guide.tcl').read_text()
(d/'hop_mid_guide.tcl').write_text('# CODEX H3: actual face/native-capture midpoint guides, 405um reach rule.\nset ::ot_mrg_spec [concat '+spec+']\n'+body)
shutil.copy2(r/'repo/physical/die_plan/hbm_arch_cores/macro_reg_guide_release.tcl',d/'hop_mid_release.tcl')
for fn,src in [('face_flops.tcl','hop_mid_guide.tcl'),('face_flops_release.tcl','hop_mid_release.tcl')]:
 p=d/fn;p.write_text(p.read_text()+'\nsource /work/'+src+'\n')
(d/'hop_midpoint_guides.json').write_text(json.dumps(g,indent=2)+'\n')
manifest=json.loads((d/'CODEX_FORM.json').read_text());manifest.update(form='opsa_rest_vH3',source=str(s),geometry_change={'class':'SPARSE+reach','H2_verdict':'GEOMETRY FAIL at PLACE; no route','face_to_hop_over405':9,'hop_to_consumer_over405':65,'guides':len(g['boxes']),'planned_worst_leg_with_extent_um':g['planned_worst_leg_including_extent_um'],'guide_size_um':[16,14],'native_capture_coordinates':'H2 actual3_place.odb all combinational reachable capture FFs; unchanged RTL'},pin_cycles=manifest['pin_cycles'])
(d/'CODEX_FORM.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(d,'guides',len(g['boxes']),'worst',g['planned_worst_leg_including_extent_um'])
