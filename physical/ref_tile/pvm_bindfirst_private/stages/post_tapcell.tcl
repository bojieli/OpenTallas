set pvm_bf_stage post_tapcell
# Canonical PG binding step (HBM-SMATT6 10-20). tapcell births TAPCELL/endcap
# instances after the pre_synth global_connect, and floorplan repair_tie_fanout
# births ordinary TIEHI/TIELO clones; their VDD/VSS terminals stay empty until a
# global_connect runs. Replay the same five persisted kit rules (no new rule, no
# signal net touched: pin patterns are ^VDD$/^VDDPE$/^VDDCE$/^VSS$/^VSSE$ only),
# then the unchanged graph/protection/scoped-TIE guard must see ALL native PG
# bound (pending ties are no longer tolerated from this stage on).
set block [ord::get_db_block]
set rules {}
foreach g [$block getGlobalConnects] {lappend rules [list [$g getInstPattern] [$g getPinPattern] [[$g getNet] getName]]}
set expect {{.* ^VDD$ VDD} {.* ^VDDPE$ VDD} {.* ^VDDCE$ VDD} {.* ^VSS$ VSS} {.* ^VSSE$ VSS}}
set canon {}; foreach e $expect {lappend canon [list {*}$e]}
if {[lsort $rules] ne [lsort $canon]} {error "PVM_BF_PG_RULES_DRIFT $rules"}
global_connect
puts "PVM_BF_POST_TAPCELL_GLOBAL_CONNECT rules=[llength $rules]"
source [file join [file dirname [info script]] .. stage_guard.tcl]
if {$pending} {error "PVM_BF_POST_TAPCELL_PG_PENDING $pending"}
