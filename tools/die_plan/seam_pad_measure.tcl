# SEAM-PAD-R3 (S81-INT-R3-SEAM, class C-PARENT-SEAM-HOLD): read-only per-input-port seam table of a routed hard core,
# optionally after an IN-MEMORY per-port HB4 pad (nothing is written back to the ODB).
#   env: OT_CORNER TT|FF  ODB (6_final.odb)  SPEF (6_final.spef)  OUT (tsv)  [PAD_SPEC (tsv: port<TAB>n_hb4)]  [OT_SPM_REPORT_ONLY_NEG]
# Kit mounted at /work (constraint.sdc, config.mk, libraries by the kit's own ORFS selector, taken from postcts_gate.tcl).
# Row: port  endpoint  endpoint_pin_kind  hold_slack_ps  setup_slack_ps  n_hb4_inserted
set C $::env(OT_CORNER)
set fh [open /work/config.mk]
foreach ln [split [read $fh] "\n"] {
  if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} { set ::env($k) $v }
}
close $fh
# exact library selector, byte-copied from the kit's postcts_gate.tcl (BEGIN/END embedded exact library selector)
set fh [open /work/postcts_gate.tcl]; set src [read $fh]; close $fh
set b [string first "# BEGIN embedded exact library selector" $src]
set e [string first "# END embedded exact library selector" $src]
if {$b < 0 || $e < 0} {error "SEAM: kit postcts_gate.tcl has no embedded library selector"}
eval [string range $src $b $e]
ot_lib_load $C /tmp/seam_libs_[string tolower $C].json
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set vc [expr {$C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set virt {}; set real {}
foreach k [all_clocks] { if {![llength [get_property $k sources]]} {lappend virt $k} else {lappend real $k} }
if {[llength $virt] != 1} {error "SEAM: expected one virtual IO clock"}
set_clock_latency -source $vc $virt
set_propagated_clock $real
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} {
  read_spef $::env(SPEF)
} else {
  # GRT-stage ODB (no SPEF): the kit's RCX-calibrated global-route RC basis, as postcts_gate.tcl does
  source $::env(LAYER_PARASITICS_FILE)
  estimate_parasitics -global_routing
  puts "SEAM_RC global_routing estimate (no SPEF)"
}
proc ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.3f $t]   ;# get_property slack is already in the library time unit (ps) }
proc seam_paths {pp mode} {
  # async reset ports (rst*) crash STA when queried with a plain -from (OpenROAD 11-27 image); the group form is the one
  # the gunit witness (child_required.tcl) uses
  if {[regexp {^rst} [get_full_name $pp]]} {
    return [find_timing_paths -path_delay $mode -rise_from $pp -path_group asynchronous -group_path_count 1 -endpoint_path_count 1]
  }
  return [find_timing_paths -from $pp -path_delay $mode -group_path_count 1 -endpoint_path_count 1]
}
proc ports_in {} {
  set r {}
  foreach p [all_inputs -no_clocks] {
    set n [get_full_name $p]
    lappend r $n
  }
  return $r
}
set clkports [list]
foreach k $real { foreach s [get_property $k sources] { lappend clkports [get_full_name $s] } }
set blk [ord::get_db_block]
# ---- optional in-memory pads: the SAME hook file the kit installs (seam_pad_port.tcl), sized by PAD_SPEC (port<TAB>n) -------------
set npad 0
if {[info exists ::env(PAD_SPEC)] && $::env(PAD_SPEC) ne ""} {
  set fp [open $::env(PAD_SPEC)]; set spec [read $fp]; close $fp
  set nf [open /tmp/seam_pad_port_n.tcl w]
  puts $nf "set ::ot_sp_per \[dict create \\"
  foreach line [split $spec "\n"] {
    if {$line eq "" || [string index $line 0] eq "#"} continue
    lassign [split $line "\t"] port n
    puts $nf " {$port} $n \\"
    incr npad $n
  }
  puts $nf "\]"
  close $nf
  set ::env(OT_SP_N_FILE) /tmp/seam_pad_port_n.tcl
  source /sp/seam_pad_port.tcl
  puts "SEAM_PAD inserted $npad HB4 cells in memory (hook seam_pad_port.tcl)"
  # the pad nets carry no SPEF/estimate: zero wire RC on them (disclosed), cell delay only
}
# ---- per input port seam table ------------------------------------------------------------------------------------
set out [open $::env(OUT) w]
foreach port [ports_in] {
  if {$port in $clkports} continue
  set pp [get_ports $port]
  set hold nan; set setup nan; set ep ""
  set ph [seam_paths $pp min]
  if {[llength $ph]} { set hold [ps [get_property [lindex $ph 0] slack]]; set ep [get_full_name [get_property [lindex $ph 0] endpoint]] }
  set pm [seam_paths $pp max]
  if {[llength $pm]} { set setup [ps [get_property [lindex $pm 0] slack]] }
  set k 0
  puts $out "$port\t$ep\t$hold\t$setup\t$k"
}
close $out
# whole-core context: worst setup / hold over everything (internal damage check).  A find_timing_paths result is freed
# by the next find call: read each one before the next query.
proc seam_worst {mode} {
  set best nan
  foreach pe [find_timing_paths -path_delay $mode -group_path_count 1] {
    set v [get_property $pe slack]
    if {$best eq "nan" || $v < $best} {set best $v}
  }
  return [ps $best]
}
puts "SEAM_WNS corner=$C setup=[seam_worst max] hold=[seam_worst min]"
set ri [find_timing_paths -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
if {[llength $ri]} { puts "SEAM_INTERNAL_HOLD corner=$C [ps [get_property [lindex $ri 0] slack]]" }
puts "SEAM_DONE corner=$C pads=$npad"
exit
