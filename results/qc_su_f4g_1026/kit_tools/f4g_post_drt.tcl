# QC-SU-F4G POST_DETAIL_ROUTE_TCL: drop the temporary M6 obstructions (DRT-only aid) and the DRT lock flag of the clock nets.
set blk [ord::get_db_block]; set n 0; set u 0
foreach ob [$blk getObstructions] { if {[[[$ob getBBox] getTechLayer] getName] eq "M6"} { odb::dbObstruction_destroy $ob; incr n } }
foreach nt [$blk getNets] {
  set nm [$nt getName]
  if {!([$nt getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm])} continue
  if {$::env(OT_F4G_LOCK) eq "fixed" && [$nt getWireType] eq "FIXED"} { $nt setWireType ROUTED; incr u }
  if {$::env(OT_F4G_LOCK) eq "dnt" && [$nt isDoNotTouch]} { $nt setDoNotTouch 0; incr u }
}
puts "F4G_SIG_POST m6_obstructions_removed $n clock_nets_unlocked $u"
