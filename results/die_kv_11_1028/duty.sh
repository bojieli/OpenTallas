#!/bin/bash
# DIE-KV-11 duty risk sweep (COORD/DIE-QC-11 probe form): rerun the kit_rt combo GRT0 tcl, dump rise AND fall arrival per tap
# (root driven by vclk both edges) + report_check_types -min_pulse_width, TT and FF.
R=/srv/opentallas-scratch2/claude/die-kv-11-1028; K=$R/kit_rt
for C in TT FF; do
  O=$R/duty_$C; mkdir -p $O


  true <<'T'
set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
puts "OT_MPW_BEGIN"
if {[catch {report_check_types -min_pulse_width} e]} { puts "OT_MPW_ERR $e" }
if {[catch {report_check_types -min_pulse_width -violators} e]} { puts "OT_MPW_ERR $e" }
puts "OT_MPW_END"
puts OT_DONE
T
  docker run -d --name dkv11-duty-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
done
for C in TT FF; do docker wait dkv11-duty-$C; docker rm dkv11-duty-$C >/dev/null; tail -n 2 $R/duty_$C/combo_$C.log; done
