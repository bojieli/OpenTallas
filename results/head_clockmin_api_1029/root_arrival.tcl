# Exact tested iterator selection; invoke after existingSTAarrival warmup. No reroute or clock-policy change.
proc ot_root_arrival {pin edge mm} {
  if {$mm eq "min"} {set best 1e30} else {set best -1e30}
  set seen 0
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} {continue}
    set iter [$vertex path_iterator $edge $mm]
    while {[$iter has_next]} {
      set path [$iter next]
      set start [$path start_path]
      set name [get_full_name [$start pin]]
      if {$name ne "root"} {continue}
      set value [get_property $path arrival]
      incr seen
      if {$mm eq "min"} {set best [expr {min($best,$value)}]} else {set best [expr {max($best,$value)}]}
    }
    $iter finish
  }
  if {!$seen} {error "no actual root-path arrival at [get_full_name $pin] $edge $mm"}
  return $best
}
