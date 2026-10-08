#!/bin/bash
# S81-DIE dietop_resume_drt.sh <dir holding ckpt_grt.odb + route.guide from dietop_round.sh> [threads] [mem_gb]
# Resumes a die-top round whose detail route failed on DRT-0509 (deprecated -bottom_routing_layer): reloads the
# global-routed checkpoint and its guides, sets the M4-M9 range through set_routing_layers (the only supported way),
# then DRT -> checkpoint -> antenna -> RCX -> SPEF -> die netlist.  Same step/OT_TIME/OTMEM conventions.
set -u
D=$(readlink -f $1); T=${2:-64}; M=${3:-600}
cat > $D/resume_drt.tcl <<T
proc mem {tag} { set f [open /proc/self/status]; set s [read \$f]; close \$f
  regexp {VmRSS:\\s+(\\d+)} \$s -> r; regexp {VmHWM:\\s+(\\d+)} \$s -> h
  puts "OTMEM \$tag rss_mb=[expr {\$r/1024}] hwm_mb=[expr {\$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 \$body} err]} { puts "OT_STEP_FAIL \$name \$err"; flush stdout; return 0 }
  puts "OT_TIME step=\$name s=[format %.1f [expr {([clock milliseconds]-\$t0)/1000.0}]]"; mem \$name; flush stdout; return 1 }
set_thread_count $T
step load { read_db /work/ckpt_grt.odb }
step guides { read_guides /work/route.guide }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_*.lib*] { read_liberty \$l }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set ok_drt [step drt { detailed_route -output_drc /work/drt_drc.rpt -droute_end_iter 20 -verbose 1 }]
step ckpt_drt { write_db /work/ckpt_drt.odb }
step antenna { puts "OT_ANTENNA [check_antennas -report_file /work/antenna.rpt]" }
if {\$ok_drt} { step rcx { define_process_corner -ext_model_index 0 X; extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules; write_spef /work/die.spef } }
step netlist { write_verilog /work/die_routed.v }
step wl { report_wire_length -net * -detailed_route -file /work/wirelength_drt.csv }
T
N=s81_dietop_drt_$(basename $D)
date -u +%FT%TZ > $D/resume.start
docker run --rm --name $N --cpus=$T --memory=${M}g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/resume_drt.tcl > /work/resume_drt.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/resume.exit; date -u +%FT%TZ > $D/resume.end
