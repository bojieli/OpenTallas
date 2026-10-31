# DIE-QC-50/gen47ndr DRT probe: keep only clock nets whose pins all lie in a window (full die kept), optional sparse M1-M7 tracks
read_db /srv/opentallas-scratch2/claude/die-qc-50/gen47ndr/grt_TT/clk_grt.odb
set b [ord::get_db_block]
lassign $::env(WIN) x0 y0 x1 y1
set keep 0; set del 0
foreach n [$b getNets] {
  set ok 1
  foreach it [$n getITerms] { set bb [[$it getInst] getBBox]; if {[$bb xMin] < $x0 || [$bb xMax] > $x1 || [$bb yMin] < $y0 || [$bb yMax] > $y1} { set ok 0; break } }
  if {$ok} { foreach bt [$n getBTerms] { set bb [$bt getBBox]; if {[$bb xMin] < $x0 || [$bb xMax] > $x1 || [$bb yMin] < $y0 || [$bb yMax] > $y1} { set ok 0; break } } }
  if {$ok && [llength [$n getITerms]] > 0} { incr keep } else { odb::dbNet_destroy $n; incr del }
}
puts "WIN keep $keep del $del"
if {$::env(SPARSE) eq "1"} {
  set tech [ord::get_db_tech]
  foreach tg [$b getTrackGrids] { set l [[$tg getTechLayer] getName]; if {$l in {M1 M2 M3 M4 M5 M6}} { odb::dbTrackGrid_destroy $tg } }
  make_tracks M1 -x_offset 0.009 -x_pitch 0.72 -y_offset 0.009 -y_pitch 0.72
  make_tracks M2 -x_offset 0.009 -x_pitch 0.72 -y_offset 0.045 -y_pitch 0.27
  make_tracks M3 -x_offset 0.009 -x_pitch 0.72 -y_offset 0.009 -y_pitch 0.72
  make_tracks M4 -x_offset 0.009 -x_pitch 0.72 -y_offset 0.012 -y_pitch 0.72
  make_tracks M5 -x_offset 0.012 -x_pitch 0.72 -y_offset 0.012 -y_pitch 0.72
  make_tracks M6 -x_offset 0.012 -x_pitch 0.72 -y_offset 0.016 -y_pitch 0.768
}
set_routing_layers -signal M1-M9 -clock M1-M9
detailed_route -output_drc $::env(OUT)/drc.rpt -droute_end_iter 10 -verbose 1
puts DRT_DONE
set wl 0; foreach n [$b getNets] { set w [$n getWire]; if {$w ne "NULL"} { incr wl [$w getLength] } }
puts "WIN_WL_DBU $wl"
write_db $::env(OUT)/win.odb
