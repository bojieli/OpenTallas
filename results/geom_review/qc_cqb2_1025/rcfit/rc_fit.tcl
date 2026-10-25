# QC-CQB F2: RC correlation fit. MODE=rcx: arrivals/hold slacks on the routed RCX view (6_final + spef).
# MODE=est: same on 5_1_grt + route.guide with estimate_parasitics -global_routing, for every (kR kC) scale of the
# setRC.tcl layer RC (M1-M9, vias by kR).  Output one TSV per setting: CK pin arrival / D pin hold slack.
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
set B $::env(OT_BASE)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_$c.lib
set mode $::env(MODE)
if {$mode eq "rcx"} { read_db $B/6_final.odb } else { read_db $B/5_1_grt.odb }
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
set ckp [all_registers -clock_pins]
set dp {}; foreach p [all_registers -data_pins] { lappend dp $p }
proc dump {tag} {
  global ckp dp c
  set f [open /work/rcfit/${tag}_$c.tsv w]
  foreach p $ckp { set a ""; catch {set a [get_property $p arrival_max_rise]}; puts $f "CK\t[get_full_name $p]\t$a" }
  foreach p $dp { set s ""; catch {set s [get_property $p slack_min]}; if {$s ne "" && $s < 150} { puts $f "HS\t[get_full_name $p]\t$s" } }
  puts $f "WNS\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]"
  close $f
}
if {$mode eq "rcx"} {
  read_spef $B/6_final.spef
  dump rcx
} else {
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
  set_routing_layers -signal M2-M5 -clock M2-M5
  read_guides $B/route.guide
  set base {M1 7.04175E-02 1e-10 M2 2.97127E-02 1.74942E-01 M3 3.12870E-02 1.55554E-01 M4 1.80365E-02 1.78475E-01 M5 1.89935E-02 1.64264E-01 M6 1.18796E-02 1.87426E-01 M7 1.25096E-02 1.62979E-01}
  foreach kk $::env(KLIST) {
    lassign [split $kk ,] kRh kCh kRv kCv
    if {$kRv eq ""} { set kRv $kRh; set kCv $kCh }
    foreach {l r cap} $base {
      if {$l in {M2 M4 M6}} { set kr $kRh; set kc $kCh } else { set kr $kRv; set kc $kCv }
      set_layer_rc -layer $l -resistance [expr {$r*$kr}] -capacitance [expr {$cap*$kc}]
    }
    foreach v {V1 V2 V3} { set_layer_rc -via $v -resistance [expr {1.72E-02*$kRh}] }
    foreach v {V4 V5} { set_layer_rc -via $v -resistance [expr {1.18E-02*$kRh}] }
    estimate_parasitics -global_routing
    dump est_[string map {, _} $kk]
    puts "FIT $kk done"
  }
}
puts FIT_DONE
