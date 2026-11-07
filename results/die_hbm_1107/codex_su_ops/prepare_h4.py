from pathlib import Path
import json,shutil
r=Path('/srv/opentallas-scratch3/claude/codex-hbm-su-1107')
s=r/'kits/opsa_rest_vH2';d=r/'kits/opsa_rest_vH4';assert not d.exists()
d.mkdir();(d/'.keep').touch()
for p in s.iterdir():
 if p.name in ['run','lec','lec_async.runs','face_shell_work','__pycache__','signoff'] or p.name.startswith('FAIL') or p.suffix=='.log':continue
 if p.name.startswith('lec_async.') and p.suffix not in ['.sh','.py']:continue
 if p.is_dir():shutil.copytree(p,d/p.name,symlinks=True)
 elif p.is_file():shutil.copy2(p,d/p.name)
g=json.loads((r/'hop_midpoint_guides.json').read_text())
spec=' '.join('{'+b['prefixes'][0]+' '+' '.join(map(str,b['box_um']))+'}' for b in g['boxes'])
body=(r/'hop_firm.tcl').read_text()
(d/'hop_firm.tcl').write_text('set ::hm_expected 74\nset ::hm_macro_halo_um 10.8\nset ::hm_targets {'+spec+'}\n'+body)
p=d/'face_flops.tcl';p.write_text(p.read_text()+'\nsource /work/hop_firm.tcl\n')
(d/'hop_midpoint_guides.json').write_text(json.dumps(g,indent=2)+'\n')
m=json.loads((d/'CODEX_FORM.json').read_text());m.update(form='opsa_rest_vH4',source=str(s),replaces_failed_form='H3 GPL-0304 NaN in tiny one-FF regions; retained',geometry_change={'class':'long-hop relay placement via existing FIRM grid','targets':74,'no_inclusive_regions':True,'unchanged_checked_boxes':str(r/'hop_midpoint_guides.json'),'reach_rule_um':405,'planned_worst_extent_um':g['planned_worst_leg_including_extent_um'],'release':'existing face_flops_release.tcl before DPL; actual placement re-audit required'})
(d/'CODEX_FORM.json').write_text(json.dumps(m,indent=2)+'\n')
print(d)
