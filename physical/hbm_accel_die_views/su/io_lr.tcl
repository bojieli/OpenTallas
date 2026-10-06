# CLAUDE HBM-ABSTRACTS (hub): lane pins split between the LEFT and RIGHT edges (M4, platform 2-track spacing): a light
# lane's 2,251 pins need 2,251 slots, one 162 um edge gives 1,672 at 2 tracks and 1-track spacing leaves M4 short /
# eolKeepOut violations at the edge (l3light).  A column with this lane faces a channel on each side.
# (set_io_pin_constraint takes one region: the pins alternate left / right in block order, so every bus splits evenly)
set ot_l {}
set ot_r {}
set i 0
foreach bterm [[ord::get_db_block] getBTerms] {
  set n [$bterm getName]
  if {$n == "VDD" || $n == "VSS"} { continue }
  if {$i % 2 == 0} { lappend ot_l $n } else { lappend ot_r $n }
  incr i
}
set_io_pin_constraint -region left:* -pin_names $ot_l
set_io_pin_constraint -region right:* -pin_names $ot_r
