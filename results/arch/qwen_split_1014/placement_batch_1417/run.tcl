read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/relay.lef
read_verilog /work/top.v
link_design test
initialize_floorplan -die_area {0 0 3000 3000} -core_area {0 0 3000 3000} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /work/snap.tcl
set b [ord::get_db_block]
set requests {}
for {set n 0} {$n<1000} {incr n} {
 lappend requests [list [$b findInst u$n] [expr {20.0+($n%40)*50}] [expr {20.0+($n/40)*50}] R0]
}
set t [clock milliseconds]
set baseline {}
foreach row $requests {lappend baseline [ot_mts::place {*}$row]}
set slow_ms [expr {[clock milliseconds]-$t}]
foreach i [$b getInsts] {$i setPlacementStatus NONE}
set t [clock milliseconds]
set fast [ot_mts::place_many $requests]
set fast_ms [expr {[clock milliseconds]-$t}]
if {$baseline ne $fast} {error "placement changed"}
ot_mts::assert_on_track -label cached_same_geometry
# An orientation with no legal site intersection must reject in both paths.
set first [lindex [lindex $requests 0] 0]
set a [catch {ot_mts::place $first 20 20 MX} ea]
set z [catch {ot_mts::place_many [list [list $first 20 20 MX]]} ez]
if {!$a || !$z || $ea ne $ez} {error "illegal orientation diverged"}
# Replacing an existing placed macro must exclude its own prior footprint.
set repeat [lindex $requests 0]
ot_mts::place_many [list $repeat $repeat]
# Error clears cache; ordinary calls remain valid afterward.
if {![catch {ot_mts::place_many [list {bad arity}]}]} {error "malformed request accepted"}
if {$ot_mts::bulk_active || $ot_mts::bulk_boxes ne {}} {error "cache survived failure"}
ot_mts::place {*}$repeat
puts "OT_BULK_PLACEMENT_PASS count=1000 exact=1 slow_ms=$slow_ms fast_ms=$fast_ms"
