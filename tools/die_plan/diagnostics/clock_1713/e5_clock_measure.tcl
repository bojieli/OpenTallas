# Clock-only electrical measurement; NEVER a data timing or sign-off gate.
set C $::env(CLOCK_CORNER)
source /scripts/timing_libs.tcl
ot_lib_load $C /out/libraries_measure_${C}.json /work/config.mk
read_db /out/clock.odb
read_sdc /work/checkpoint/4_cts.sdc
read_spef /out/clock.spef
set_propagated_clock [get_clocks clk]
set ::ot_ps_lib_only 1
source /scripts/pair_skew.tcl
set ::ot_ps_method tag
set clk [get_clocks clk]
if {abs([get_property $clk period]-833.0)>1e-6} {error "Unexpected period; no constraint changes permitted"}
set fh [open /out/clock_${C}.tsv w]
puts $fh "kind\tpin\tlate_ps\tearly_ps\trise_slew_ps"
set measured 0
foreach inst [[ord::get_db_block] getInsts] {
  set name [$inst getName]
  set kind ""
  if {[regexp {^ot_dtsh_[0-9]+$} $name]} {set kind TRUNK}
  if {[regexp {^ot_dtap_[0-9]+$} $name]} {set kind TAP}
  foreach it [$inst getITerms] {
    if {![$it isInputSignal]} continue
    set mt [$it getMTerm]
    set ck [expr {[$mt getSigType] eq "CLOCK" || [$mt getName] in {CLK CK CP clk}}]
    if {$kind eq "" && !$ck} continue
    if {$kind ne "" && [$mt getName] ne "A"} continue
    set pin [get_pins -quiet "$name/[$mt getName]"]
    if {$pin eq ""} {error "Missing actual clock pin $name/[$mt getName]"}
    set late [ot_ps_ckarr $pin $clk max]; set early [ot_ps_ckarr $pin $clk min]
    if {$late eq "" || $early eq ""} {error "No unique clock-tag arrival at $name/[$mt getName]"}
    set type $kind
    if {$type eq ""} {set type [expr {[[$inst getMaster] isBlock] ? "MACRO" : "REG"}]}
    puts $fh "$type\t$name/[$mt getName]\t$late\t$early\t[get_property $pin slew_max_rise]"
    incr measured
  }
}
close $fh
if {$::ot_ps_method ne "tag"} {error "Clock-tag API unavailable; property fallback not qualified"}
puts "PARTIAL_CLOCK_MEASURE $C pins=$measured raw_clock_tags=1 data_paths_omitted=1 NO_SIGNOFF"
