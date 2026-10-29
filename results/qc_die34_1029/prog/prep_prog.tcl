# DIE-QC-34 PROG QC-020 candidate 2 (GEOM-58 PASS-COND 09:37): prepare the ONE route from native_pin_reach.odb (sha 6a2f8b49).
# (1) existing protected-instance PG hook (codex-qc-prog-pg-0830 pg_connect.tcl = tools/die_plan/pg_connect.tcl copy):
#     216 open supply terms on 108 protected ot_ms_* spine buffers -> bound, then hard check 0 open;
# (2) remove ALL old non-special routing (the 354 moved FFs invalidate the archived 5_2 wires; clock nets included, so the
#     moved-sink leaves are re-routed by GRT/DRT); cells, placement, special (PG) nets untouched.
read_db /work/in/native_pin_reach.odb
source /work/pg_connect.tcl
set b [ord::get_db_block]
set before 0; foreach i [$b getInsts] { incr before [ot_pg_open_terms $i] }
puts "PREP_PG open_before=$before"
# 5_2-stage census is larger than the 6_final 216 (ORFS binds post-DRT cells at 5_3 global_connect); the hook binds all, require 0 open after
set rep [ot_pg_connect_all dqc34_prog_native]
if {$rep != 108} { error "PREP_PG unexpected repaired instance count $rep != 108" }
ot_pg_require_bound dqc34_prog_native
set n 0; set nc 0
foreach net [$b getNets] {
  if {[$net isSpecial]} continue
  set w [$net getWire]
  if {$w ne "NULL" && $w ne ""} { if {[$net getSigType] eq "CLOCK"} { incr nc }; odb::dbWire_destroy $w; incr n }
}
puts "PREP_STRIP removed routing of $n nets ($nc CLOCK-typed)"
set ff 0; foreach i [$b getInsts] { if {[string match DFF* [[$i getMaster] getName]]} { incr ff } }
puts "PREP_CENSUS insts [llength [$b getInsts]] dff $ff"
write_db /work/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/4_cts.odb
puts "PREP_DONE"
