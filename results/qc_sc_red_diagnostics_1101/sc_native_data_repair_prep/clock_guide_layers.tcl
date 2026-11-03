# Observe native local pin/via access separately from configured CLOCK routing layers.
set f [open /work/clock_guide_layers.tsv w]
puts $f "net\tlayer\tvia_layer\tnative_connected_to_terminal\trole_hint\tbbox_dbu"
set layers {};set lower_term 0;set lower_other 0;set upper 0
foreach n [[ord::get_db_block] getNets] {
 if {[$n getSigType] ne "CLOCK"} continue
 foreach g [$n getGuides] {
  set ln [[$g getLayer] getName];set vl [$g getViaLayer];set vn NULL
  if {$vl ne "NULL" && $vl ne ""} {set vn [$vl getName]}
  set term [$g isConnectedToTerm];dict incr layers $ln
  set hint configured_clock_layer
  if {$ln in {M1 M2 M3}} {
   if {$term} {incr lower_term;set hint native_terminal_access_below_clock_min} else {incr lower_other;set hint below_clock_min_native_guide_unclassified}
  } elseif {$ln ni {M4 M5}} {incr upper;set hint above_configured_ceiling}
  # Bounding-box metadata is observational; the native layer policy is authoritative.
  set bbox NA
  catch {set q [$g getBox];set bbox [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]}
  puts $f "[$n getName]\t$ln\t$vn\t$term\t$hint\t$bbox"
 }
};close $f
puts "SC_CLOCK_GUIDE_LAYER_CENSUS layers=$layers lower_terminal_access=$lower_term lower_unclassified=$lower_other above_ceiling=$upper"
if {$upper} {error SC_CLOCK_GUIDES_ABOVE_CONFIGURED_M5_CEILING}
# No rejection of native lower-layer pin/via access and no new geometric threshold.
