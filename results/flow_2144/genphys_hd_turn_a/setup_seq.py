from pathlib import Path
import shutil
p=Path('/srv/opentallas-scratch2/claude/codex-genphys-ab-2144')
k=p/'seq_tt';shutil.copytree(p/'candidate',k)
for sub in ['results','logs','reports']:
 for f in list((k/'run'/sub).glob('asap7/*/base/5*')):
  d=k/'mcmm_failed_artifacts'/sub;d.mkdir(parents=True,exist_ok=True);f.rename(d/f.name)
shutil.copy2(k/'grt_pre.tcl',k/'grt_pre_original.tcl')
(k/'grt_pre.tcl').write_text('source /work/grt_pre_original.tcl\nproc repair_timing_helper {} {\n  if {$::env(AB_PHASE) eq "tt"} {\n    puts "AB_SEQ TT-only setup repair; vclk TT native"\n    repair_timing -setup -setup_margin 0 -repair_tns 100 -skip_last_gasp -verbose\n  } else {\n    puts "AB_SEQ FF-only hold repair; vclk FF native"\n    repair_timing -hold -hold_margin 5 -setup_margin 0 -verbose\n  }\n}\n')
