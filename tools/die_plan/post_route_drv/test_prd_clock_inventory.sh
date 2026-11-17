#!/bin/bash
# Inside the pinned OpenROAD image, under ot-run admission:
#   test_prd_clock_inventory.sh TOOL_DIR REAL_ONE_BUF_M7_FIXTURE.odb FRESH_OUT
# The fixture is copied from the native_e minimum mechanism proof, not rebuilt.
set -euo pipefail
T=$1; S=$2; O=$3
test ! -e "$O" || { echo 'fresh output required'; exit 2; }
mkdir -p "$O"
cat > "$O/proof.tcl" <<'TCL'
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_db $::env(INVENTORY_FIXTURE)
set n [[ord::get_db_block] findNet clk]
if {$n eq "NULL" || $n eq ""} { error "fixture must preserve the real clk net" }
proc wire_tokens {net} {
  set w [$net getWire]; set out {}
  for {set i 0} {$i < [$w length]} {incr i} { lappend out [list [$w getOpcode $i] [$w getData $i]] }
  return $out
}
set before [wire_tokens $n]
if {[llength $before] != 93} { error "fixture must retain its 93 real wire opcodes" }
set mode $::env(INVENTORY_CASE)
set old_clock [expr {$mode eq "ordinary" ? "M8" : "M6"}]
set_routing_layers -signal M2-M6 -clock M2-$old_clock
if {$mode eq "data"} { $n setSigType SIGNAL }
set ::env(RESULTS_DIR) $::env(INVENTORY_OUT)
set rc [catch {source $::env(INVENTORY_TOOL)} result opts]
if {[wire_tokens $n] ne $before} { error "inventory changed existing clock wire opcodes/data" }
if {[[ord::get_db_block] getMaxRoutingLayer] != 6} { error "signal ceiling changed" }
if {$mode eq "data"} {
  if {!$rc || ![string match {*data above unchanged signal ceiling 6*} $result]} {
    error "above-ceiling data was not refused: $rc $result"
  }
  if {[[ord::get_db_block] getMaxLayerForClock] != 6} { error "data refusal changed clock resources" }
  puts "CLOCK_INVENTORY_DATA_REFUSAL_PASS: $result"
  exit
}
if {$rc} { return -options $opts $result }
if {$mode eq "ordinary"} {
  if {[[ord::get_db_block] getMaxLayerForClock] != 8} { error "existing clock range was narrowed" }
  puts "CLOCK_INVENTORY_EXISTING_RANGE_UNCHANGED_PASS"
  exit
}
if {[[ord::get_db_block] getMaxLayerForClock] != 7} { error "M7 clock resources not registered" }
puts "CLOCK_INVENTORY_WIRE_UNCHANGED_PASS [llength $before]"
set_wire_rc -signal -layer M3
set_wire_rc -clock -layer M6
create_clock -name ck -period 833 [get_ports clk]
global_route -allow_congestion -congestion_iterations 1
global_route -start_incremental
set it [lindex [$n getITerms] 0]
$it disconnect
$it connect $n
global_route -end_incremental
puts "CLOCK_INVENTORY_END_INCREMENTAL_PASS"
TCL
for mode in positive data ordinary; do
  mkdir "$O/$mode"
  INVENTORY_FIXTURE="$S" INVENTORY_TOOL="$T/prd_clock_inventory.tcl" INVENTORY_CASE="$mode" INVENTORY_OUT="$O/$mode" \
    openroad -exit "$O/proof.tcl" > "$O/$mode/run.log" 2>&1
done
grep -q CLOCK_INVENTORY_END_INCREMENTAL_PASS "$O/positive/run.log"
grep -q CLOCK_INVENTORY_DATA_REFUSAL_PASS "$O/data/run.log"
grep -q CLOCK_INVENTORY_EXISTING_RANGE_UNCHANGED_PASS "$O/ordinary/run.log"
test ! -e "$O/data/prd_clock_inventory.json"
printf '%s\n' 'CLOCK_INVENTORY_ACTUAL_FIXTURE_PASS positive, data refusal, ordinary range preservation'
