from pathlib import Path
import shutil,json
s=Path('/srv/opentallas-scratch2/claude/hbm-cons-2-suk/kits/ot_hbm_su_pg_lane_full_x_core_5f8f465b7af8_vK/ot_hbm_su_pg_lane_full_x_core_5f8f465b7af8-_vK')
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-su-1107')
d=r/'kits/fullx_vL_lockup';assert not d.exists()
d.mkdir(parents=True);(d/'.keep').touch()
for p in s.iterdir():
 if p.name in ['run','lec','lec_async.runs','face_shell_work','__pycache__','signoff','vk_views','views'] or p.name.startswith('FAIL') or p.suffix=='.log':continue
 if p.name.startswith('lec_async.') and p.suffix not in ['.sh','.py']:continue
 if p.is_dir():shutil.copytree(p,d/p.name,symlinks=True)
 elif p.is_file():shutil.copy2(p,d/p.name)
for f in ['fullx_lockups.tcl','fullx_lockup_targets.tsv']:shutil.copy2(r/'fullx_vk_census'/f,d/f)
p=d/'post_synth_actual.tcl';t=p.read_text();assert t.count('write_verilog')==1
p.write_text(t.replace('write_verilog','source /work/fullx_lockups.tcl\nwrite_verilog'))
(d/'added_rx_clk_PIN_cycles.json').write_text(json.dumps({'baseline':'private part55 full_x vK','delta':0,'mechanism':'supported transparent-low DLLx1 on direct rising-FF chains'},indent=2)+'\n')
assert (d/'lec_async.sh').is_file(),'missing async tool source; never filter .sh as a receipt'
print(d)
