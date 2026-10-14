# Isolated candidate only. Invoked by explicit OT_OFLOP_DFFE_PAIRS=1.
# Prove exact Liberty functions and scalar topology before choosing q placement.
# No logic or timing constraints are edited. Missing inputs fail closed.
if {![info exists ::env(LIB_FILES)] || $::env(LIB_FILES) eq ""} {
  error "OT_DFFE_PAIR: actual Liberty LIB_FILES required"
}
if {![info exists ::env(OT_OFLOP_DFFE_EXPECTED_PAIRS)] || ![string is integer -strict $::env(OT_OFLOP_DFFE_EXPECTED_PAIRS)] || $::env(OT_OFLOP_DFFE_EXPECTED_PAIRS) < 1} {
  error "OT_DFFE_PAIR: explicit positive OT_OFLOP_DFFE_EXPECTED_PAIRS required"
}
set ot_dffe_net $::env(RESULTS_DIR)/ot_dffe_pin_pairs.graph.tsv
set ot_dffe_json $::env(RESULTS_DIR)/ot_dffe_pin_pairs.json
set fh [open $ot_dffe_net w]
proc ot_dffe_row {fh args} {
  foreach field $args {if {[regexp {[\t\r\n]} $field]} {error "OT_DFFE_PAIR: unsafe native graph name"}}
  puts $fh [join $args "\t"]
}
foreach bt [$ot_blk getBTerms] {
  set n [$bt getNet];if {$n eq "NULL"} {error "OT_DFFE_PAIR: disconnected port"}
  ot_dffe_row $fh PORT [string tolower [$bt getIoType]] [$bt getName] "@[$n getId]"
}
foreach i [$ot_blk getInsts] {
  ot_dffe_row $fh CELL [$i getName] [[$i getMaster] getName]
  foreach it [$i getITerms] {
    if {![$it isInputSignal] && ![$it isOutputSignal]} continue
    set n [$it getNet]
    if {$n eq "NULL"} {
      # Keep a unique disconnected vertex; it cannot prove any input/clock root.
      set key "@disconnected:[$i getId]:[[$it getMTerm] getName]"
      puts "OT_DFFE_PAIR uncovered disconnected [$i getName]/[[$it getMTerm] getName]"
    } else {set key "@[$n getId]"}
    ot_dffe_row $fh PIN [$i getName] [[$it getMTerm] getName] $key
  }
}
close $fh
set ot_dffe_cmd [list python3 /src/tools/ref_tile/recognize_dffe_pin_pairs.py \
  --graph $ot_dffe_net --top [$ot_blk getName] --out $ot_dffe_json --libs]
foreach f $::env(LIB_FILES) { lappend ot_dffe_cmd $f }
if {[catch {set ot_dffe_text [exec {*}$ot_dffe_cmd]} why]} {
  error "OT_DFFE_PAIR: strict recognizer failed: $why"
}
set ot_dffe_inst [dict create]
foreach i [$ot_blk getInsts] {
  set key [$i getName]
  if {[dict exists $ot_dffe_inst $key]} {error "OT_DFFE_PAIR: ambiguous canonical instance $key"}
  dict set ot_dffe_inst $key $i
}
set ot_dffe_q [dict create]; set ot_dffe_d [dict create]
foreach row [split [string trim $ot_dffe_text] "\n"] {
  if {$row eq ""} continue
  set fields [split $row "\t"]
  if {[llength $fields] != 3} {error "OT_DFFE_PAIR: invalid recognizer row"}
  lassign $fields qp fn dp
  if {![dict exists $ot_dffe_inst $fn]} {error "OT_DFFE_PAIR: missing actual instance $fn"}
  if {[dict exists $ot_dffe_q $qp] || [dict exists $ot_dffe_d $dp]} {error "OT_DFFE_PAIR: repeated pair"}
  dict set ot_dffe_q $qp [dict get $ot_dffe_inst $fn]
  dict set ot_dffe_d $dp $qp
  puts "OT_DFFE_PAIR proven q=$qp d=$dp ff=$fn placement=q-face"
}
if {[dict size $ot_dffe_q] != $::env(OT_OFLOP_DFFE_EXPECTED_PAIRS)} {error "OT_DFFE_PAIR: expected $::env(OT_OFLOP_DFFE_EXPECTED_PAIRS) pairs, proved [dict size $ot_dffe_q]"}
# Paired q register takes explicit precedence over its d input. Ordinary ports
# still use the existing recognizer, with its behavior unchanged when flag off.
set ot_bterms {}
foreach bt [$ot_blk getBTerms] {if {[$bt getIoType] eq "OUTPUT"} {lappend ot_bterms $bt}}
foreach bt [$ot_blk getBTerms] {if {[$bt getIoType] ne "OUTPUT"} {lappend ot_bterms $bt}}
