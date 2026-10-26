foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] {read_liberty $l}
foreach l [glob /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/*_tt.lib /src/physical/ref_tile/s81dv_idxtxga/views/dsdv_idx_txm_grp/*_tt.lib] {read_liberty $l}
read_db /base/4_cts.odb
read_sdc /base/4_cts.sdc
source /test/clock_spine.tcl

set block [ord::get_db_block]
set chosen ""
foreach i [$block getInsts] {
  if {[string match clkbuf_sp_* [$i getName]] && [string match BUFx* [[$i getMaster] getName]]} {set chosen $i; break}
}
if {$chosen eq ""} {error "No existing native spine buffer"}
set output "[$chosen getName]/Y"
set row [list $output [[$chosen getMaster] getName] A ck]
set result [ot_sp_internal_root test $row]
puts "POSITIVE native root $row $result"
proc reject {label row pattern} {
  if {![catch {ot_sp_internal_root test $row} msg]} {error "Negative accepted: $label"}
  if {![string match $pattern $msg]} {error "Unexpected negative $label: $msg"}
  puts "NEGATIVE $label CAUGHT $msg"
}
reject missing [list absent/Y BUFx24_ASAP7_75t_R A ck] {*missing output*}
reject wrong_master [lreplace $row 1 1 INVx1_ASAP7_75t_R] {*wrong master*}
reject wrong_input [lreplace $row 2 2 B] {*unary noninverting*}
set data_port ""
foreach b [$block getBTerms] {if {[$b getIoType] eq "INPUT" && [$b getName] ne "ck"} {set data_port [$b getName]; break}}
if {$data_port eq ""} {error "No data input for negative"}
reject data_source [lreplace $row 3 3 $data_port] {*source must be one actual clock*}
set inverter ""
foreach i [$block getInsts] {if {[string match INVx* [[$i getMaster] getName]]} {set inverter $i; break}}
if {$inverter eq ""} {error "No native inverter for negative"}
reject inverter [list "[$inverter getName]/Y" [[$inverter getMaster] getName] A ck] {*unary noninverting*}
reject wrong_pin [list "[$chosen getName]/A" [[$chosen getMaster] getName] A ck] {*missing output*}
puts "NATIVE_CLOCK_GUARDS PASS positive1 negative6"
# Construction API fixture only: the immutable saved CTS tree is protected.
# Remove protection only from this in-memory fixture's one existing root net
# and direct sink cohort. No ODB/SDC is written, and no production hook clears it.
set fixture_net [lindex $result 0]
$fixture_net setDoNotTouch 0
foreach it [$fixture_net getITerms] {[$it getInst] setDoNotTouch 0}
puts "NATIVE_FIXTURE instrumented one existing protected root in memory only"
set ::ot_sp_internal_roots [dict create test $row]
set ::env(OT_SPINE_ITERS) 0
set ::env(OT_SPINE_MACRO_LEAF) 1
set ::env(OT_SPINE_MACRO_PIN_LEAF) 1
set_wire_rc -signal -layer M3
set_wire_rc -clock -layer M6
set_propagated_clock [all_clocks]
if {![ot_clock_spine test clkbuf_tx_smoke_]} {error "Internal physical tree did not build"}
puts "NATIVE_INTERNAL_SPINE_BUILD PASS"
exit
