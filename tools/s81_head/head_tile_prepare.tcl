# Clear only this corridor layout's own existing/data-copy FFs before reapplying
# its deterministic banks. This makes repeated PRE_GPL invocations independent of
# a previous invocation's FIRM status; other fixed cells/macros stay occupied.
set htp_targets [dict create]
set htp_file [open $::env(HEAD_TILE_RELAY_TARGETS) r]
while {[gets $htp_file ln]>=0} {
  if {$ln eq "" || [string index $ln 0] eq "#"} continue
  dict set htp_targets [lindex [split $ln "\t"] 0] 1
}
close $htp_file
set htp_released 0
foreach inst [[ord::get_db_block] getInsts] {
  set name [$inst getName]
  set nm [string map {\\ {}} $name]
  set own [expr {[dict exists $htp_targets $name] ||
                 [regexp {^u_core[.]x_q|^u_core[.]xo_q} $nm] ||
                 $nm eq {u_core.u_b.u_x.genblk1.g_line.line[255]$_DFF_P_}}]
  if {$own && [string match DFF* [[$inst getMaster] getName]] &&
      [$inst getPlacementStatus] eq "FIRM"} {
    $inst setPlacementStatus PLACED
    incr htp_released
  }
}
puts "HEAD_TILE_PREP cleared_owned_firm=$htp_released other_fixed_unchanged=1"
