# mg.sh <tag> <signoff_dir>: est (current table) slew-violation counts at slew limit x (1-margin), margins 0/20/30/40/50 %
W=/srv/opentallas-scratch2/claude/flow-rc-1027; T=$W/tools; O=$W/$1/mg; SO=$2/tt; mkdir -p $O; cp $T/setRC_rcx_asap7.tcl $O/
S=$SO/session.tcl; n=$(grep -n "^read_db" $S | head -1 | cut -d: -f1)
{ head -n $((n-1)) $S; cat <<'TCL'
read_db /base/5_1_grt.odb
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
source /out/setRC_rcx_asap7.tcl
estimate_parasitics -global_routing
puts "FRCMG base slew [sta::max_slew_violation_count]"
foreach m {0.2 0.3 0.4 0.5} {
  set_max_transition [expr {320.0*(1.0-$m)}] [current_design]
  puts "FRCMG margin $m slew_viol_at_[expr {320.0*(1.0-$m)}] [sta::max_slew_violation_count]"
}
TCL
} > $O/mg.tcl
mounts=$(grep -o -- "-v [^ ]*" $SO/cmd.sh | grep -v ":/out$" | tr "\n" " ")
docker run --rm --memory 24g $mounts -v $O:/out openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/mg.tcl > $O/mg.log 2>&1
grep ^FRCMG $O/mg.log > $O/mg.txt; echo MGDONE >> $O/mg.txt
