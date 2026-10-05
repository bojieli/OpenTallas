from pathlib import Path
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl')
s=p.read_text();assert s.count('  repair_timing_helper\n')==1
s=s.replace('  repair_timing_helper\n', '  source /diag/capture.tcl\n  ot_capture before_repair\n  set ot_rc [catch {repair_timing_helper} ot_msg ot_options]\n  ot_capture after_repair\n  if {$ot_rc} {return -options $ot_options $ot_msg}\n')
p.write_text(s)
