#!/bin/bash
# L2H-P3 10-19: two S8 diagnostic variants of the f4c_t9p3 relayed GEN (same placement/netlist; only the S8 run.tcl differs)
set -e
B=/srv/opentallas-scratch/claude/hnx/die_p4; S=$B/hnx_case_f4c_t9p3_land
for v in rs150 norep; do
  D=${S}_$v; rm -rf $D; mkdir -p $D/out
  for f in $(ls $S); do [ "$f" = out ] && continue; cp -al $S/$f $D/$f; done
  rm -f $D/run.tcl $D/die_repeaters.tcl
done
cp $B/l2h_die_repeaters.tcl ${S}_rs150/die_repeaters.tcl; cp $S/die_repeaters.tcl ${S}_norep/die_repeaters.tcl.orig
sed 's/repair_args {-buffer_gain 4.0}/repair_args {-buffer_gain 4.0} skip_short_um 150/' $S/run.tcl > ${S}_rs150/run.tcl
grep -c 'skip_short_um 150' ${S}_rs150/run.tcl
# norep: GRT of the placed die without the die-repeater step (localises the S8 SIGSEGV; congestion of the unrepeated die)
awk '/^source \/work\/die_repeaters.tcl$/ {print "# L2H-P3 norep: die repeater step removed"; next}
     /^set ot_die_rep_v \[ot_die_repeaters/ {next}
     /^if \{\$ot_die_rep_v != 0\}/ {next}
     /ot_die_rep_post_grt_audit/ {next} {print}' $S/run.tcl > ${S}_norep/run.tcl
grep -c ot_die_rep ${S}_norep/run.tcl || true
du -sh ${S}_rs150 ${S}_norep | cat
