#!/bin/bash
# rcprobe.sh <signoff_corner_dir> <out_dir> <mem_gb> <mode rcx|est|wd> <layers e.g. M2-M7> [rc files (host paths, est mode)]
# Diagnostic (FLOW-RC-1): re-uses the sign-off session's exact library loading (session.tcl head before read_db) and mounts.
SO=$1; OUT=$2; MEM=$3; MODE=$4; L=$5; shift 5; RCS="$@"
mkdir -p $OUT/rc; T=$(cd $(dirname $0); pwd)
cmd=$(cat $SO/cmd.sh)
mounts=$(echo "$cmd" | grep -o -- '-v [^ ]*' | grep -v ':/out$' | tr '\n' ' ')
base=$(echo "$cmd" | grep -oP -- '-v \K[^ ]*(?=:/base)')
img=openroad/orfs:asap7lock
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
rcl=""; for r in $RCS; do cp $r $OUT/rc/; rcl="$rcl /out/rc/$(basename $r)"; done
if [ $MODE = wd ]; then
  cp $T/rc_calib_wire_dump.py $OUT/
  docker run --rm --name frc_wd_$$ --memory ${MEM}g -v $base:/base:ro -v $OUT:/out $img $OR -python -exit /out/rc_calib_wire_dump.py /base/6_final.odb /out/wire.tsv > $OUT/wd.log 2>&1
  tail -1 $OUT/wd.log; exit
fi
n=$(grep -n '^read_db' $SO/session.tcl | head -1 | cut -d: -f1)
head -n $((n-1)) $SO/session.tcl > $OUT/probe_$MODE.tcl
cat >> $OUT/probe_$MODE.tcl <<TCL
proc frc_cnt {tag} {
  set s [sta::max_slew_violation_count]; set c [sta::max_capacitance_violation_count]
  puts "FRC \$tag slew \$s cap \$c setup [format %.2f [sta::time_sta_ui [sta::worst_slack_cmd max]]] hold [format %.2f [sta::time_sta_ui [sta::worst_slack_cmd min]]]"
  set f [open /out/viol_\$tag.txt w]
  with_output_to_variable v { report_check_types -max_slew -violators -max_count 100000 }
  puts \$f \$v; close \$f
}
if {"$MODE" eq "rcx"} {
  read_db /base/6_final.odb
  read_spef /base/6_final.spef
  read_sdc /sdc/golden.sdc
  set_propagated_clock [all_clocks]
  frc_cnt rcx
} else {
  read_db /base/5_1_grt.odb
  read_sdc /sdc/golden.sdc
  set_propagated_clock [all_clocks]
  set_routing_layers -signal $L -clock $L
  foreach rc {$rcl} {
    source \$rc
    if {[catch {estimate_parasitics -global_routing -spef_file /out/est_[file rootname [file tail \$rc]].spef} e]} { puts "FRC_NOROUTES \$e"; exit 1 }
    frc_cnt est_[file rootname [file tail \$rc]]
  }
}
puts FRC_DONE
TCL
docker run --rm --name frc_${MODE}_$$ --memory ${MEM}g $mounts -v $OUT:/out $img $OR -no_init -exit /out/probe_$MODE.tcl > $OUT/$MODE.log 2>&1
grep '^FRC' $OUT/$MODE.log
