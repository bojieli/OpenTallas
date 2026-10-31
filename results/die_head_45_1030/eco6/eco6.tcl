# DIE-HEAD-45 2026-10-30: LEP ECO6 = LEP ECO5 f (BUFx3 leaves) GRT DB + ONE data-DRV fix, nothing else.
# ECO5 f re-sign at flow-20261030-e-head: TT +10.15, FF hold +3.21, pair skew TT/FF 77.0/67.8, DRC 0, only FAIL = TT slew 1:
# beat_tx[157]/D 328.96 (limit 320) on net gpay[101] = OAI21x1 _93338_ (24.1,247.3) -> face flop (5.7,144.2), 121 um
# unbuffered, 1 load (ASAP7 has no larger OAI21).  ECO5 e also failed gpay[86] (_93255_ -> beat_tx[142], 287 ps in f).
# Fix: one BUFx4f next to each OAI driving the long leg (2 cells, data only; clock nets locked; no other repair).
proc so {k args} { puts "SO $k [join $args { }]" }
proc sv {cmd} { if {[catch {uplevel #0 $cmd} r]} { return "ERR:$r" }; return $r }
source /out/libprocs.tcl
set ltt [ot_lib_resolve TT]
set lff [ot_lib_resolve FF]
define_corners TT FF
foreach f $ltt { read_liberty -corner TT $f }
foreach f $lff { read_liberty -corner FF $f }
read_db /base/5_1_grt.odb
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
read_spef /rbase/6_final.spef
so BASE setup_tt [sv {sta::worst_slack_cmd max}] hold_ff [sv {sta::worst_slack_cmd min}]
so DRV_BASE slew [sv sta::max_slew_violation_count] cap [sv sta::max_capacitance_violation_count]
set block [ord::get_db_block]
source /work/clk_freeze.tcl
set nlock 0
foreach n [ot_clk_dbnets] { foreach it [$n getITerms] { set i [$it getInst]; if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} { $i setPlacementStatus LOCKED; incr nlock } } }
puts "ECO6 prelock $nlock clock-net instances"
global_route -start_incremental
file mkdir /out/eco6/clock_lock
ot_clk_freeze /out/eco6/clock_lock
set bm [[ord::get_db] findMaster BUFx4f_ASAP7_75t_R]
foreach {drv flop tag} {_93338_ {u_lane.u.u_gb.beat_tx\[157\]$_DFF_P_} g101 _93255_ {u_lane.u.u_gb.beat_tx\[142\]$_DFF_P_} g86} {
  set di [$block findInst $drv]; set fi [$block findInst $flop]
  if {$di eq "NULL" || $fi eq "NULL"} { error "ECO6: missing $drv / $flop" }
  set dit [$fi findITerm D]; set on [$dit getNet]
  if {[[$di findITerm Y] getNet] ne $on} { error "ECO6: $drv/Y does not drive $flop/D" }
  if {[llength [$on getITerms]] != 2} { error "ECO6: [$on getName] has [llength [$on getITerms]] iterms, expected 2" }
  set nn [odb::dbNet_create $block eco6_${tag}_d]
  set bi [odb::dbInst_create $block $bm eco6_buf_${tag}]
  $dit disconnect; $dit connect $nn
  [$bi findITerm A] connect $on
  [$bi findITerm Y] connect $nn
  set l [$di getLocation]
  $bi setLocation [lindex $l 0] [expr {[lindex $l 1]}]
  $bi setPlacementStatus PLACED
  puts "ECO6 buffer eco6_buf_$tag on [$on getName] at $l -> [$fi getName]/D (new net eco6_${tag}_d)"
}
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_iterations 50 -resistance_aware
ot_clk_freeze_assert lep_eco6
source /work/pg_connect.tcl
ot_pg_connect_all lep_eco6
ot_pg_require_bound lep_eco6
ot_clk_dump /out/eco6/clock_lock/clk_after_grt.tsv after_grt
estimate_parasitics -global_routing
foreach p {u_lane.u.u_gb.beat_tx[157]$_DFF_P_/D u_lane.u.u_gb.beat_tx[142]$_DFF_P_/D eco6_buf_g101/A eco6_buf_g86/A} {
  so PIN $p slew [get_property [get_pins $p] slew_max_rise] setup_slack [get_property [get_pins $p] slack_max] hold_slack [get_property [get_pins $p] slack_min]
}
so FINAL_GRTRC setup_tt [sv {sta::worst_slack_cmd max}] hold_ff [sv {sta::worst_slack_cmd min}]
so DRV_FINAL_GRTRC slew [sv sta::max_slew_violation_count] cap [sv sta::max_capacitance_violation_count]
write_db /out/eco6/5_1_grt.odb
puts "ECO6 DONE"
exit
