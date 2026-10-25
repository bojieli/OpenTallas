from pathlib import Path
import shutil,subprocess,json
root=Path('/srv/opentallas-scratch2/claude/codex-s81-legacy')
for short in ['rstg','payload']:
 src=root/'kits'/(short+'_r4_m5')
 for margin in [0,5]:
  dst=root/'eco'/(short+'_h'+str(margin));assert not dst.exists();dst.mkdir(parents=True)
  subprocess.run(['rsync','-a','--exclude','/run','--exclude','/views','--exclude','/signoff/','--exclude','/signoff.log','--exclude','/.ot-run-spill-copy',str(src)+'/',str(dst)+'/'],check=True)
  old=next((src/'run/results').glob('asap7/*/base'));base=dst/'run/results/asap7'/old.parent.name/'base';base.mkdir(parents=True)
  for d in ['objects','reports','logs']:(dst/'run'/d/'asap7'/old.parent.name/'base').mkdir(parents=True)
  shutil.copy2(old/'5_2_route.odb',base/'4_cts.odb')
  for n in ['6_final.spef','1_2_yosys.v','1_synth.v','clock_period.txt','mem.json','ot_face_flops.txt','ot_unreg_pins.txt']:
   if (old/n).exists():shutil.copy2(old/n,base/n)
  obj=src/'run/objects/asap7'/old.parent.name/'base'
  if obj.exists():shutil.copytree(obj,dst/'run/objects/asap7'/old.parent.name/'base',dirs_exist_ok=True)
  (base/'4_cts.sdc').write_text((dst/'constraint.sdc').read_text()+'\nset_propagated_clock [all_clocks]\n')
  (dst/'eco_hold.tcl').write_text('''# Extracted RC hold ECO only; no clock/constraint/RTL change.
read_spef $::env(RESULTS_DIR)/6_final.spef
global_route -start_incremental
repair_timing -hold -hold_margin '''+str(margin)+''' -max_buffer_percent 100
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
''')
  with (dst/'config.mk').open('a') as f:f.write('\nexport POST_GLOBAL_ROUTE_TCL = /work/eco_hold.tcl\noverride export PWR_NETS_VOLTAGES =\noverride export GND_NETS_VOLTAGES =\n')
  print(dst)
