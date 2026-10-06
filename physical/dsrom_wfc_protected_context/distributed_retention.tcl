# Next selected distributed provider only. Actual mapped FFs, not RTL declaration counts.
proc ds_wfc_check_distributed_retention {prefix} {
  set seats [dict create]
  foreach inst [[ord::get_db_block] getInsts] {
    set name [string map [list {\[} {[} {\]} {]}] [$inst getName]]
    if {[string first "${prefix}.g_distributed." $name] != 0} {continue}
    if {![regexp {\.g_(cluster|local)\[([0-9]+)\]\.u_cmd\.(q_check|q)\[([0-9]+)\]} $name -> family seat rail bit]} {continue}
    if {![string match {*DFF*} [[$inst getMaster] getName]]} {error "Command rail is not a mapped FF: $name"}
    set key "$family/$seat/$rail/$bit"
    if {[dict exists $seats $key]} {error "Command bit has multiple mapped drivers: $key"}
    dict set seats $key $inst
  }
  foreach {family count width} {cluster 12 18 local 96 13} {
    for {set seat 0} {$seat < $count} {incr seat} {
      for {set bit 0} {$bit < $width} {incr bit} {
        foreach rail {q q_check} {
          set key "$family/$seat/$rail/$bit"
          if {![dict exists $seats $key]} {error "Independent command FF missing: $key"}
        }
        if {[dict get $seats "$family/$seat/q/$bit"] eq [dict get $seats "$family/$seat/q_check/$bit"]} {
          error "Command complementary rail merged: $family/$seat/$bit"
        }
      }
    }
  }
  if {[dict size $seats] != 2928} {error "Distributed command mapped FF inventory mismatch: [dict size $seats]"}
  puts "DS_WFC_DISTRIBUTED_INDEPENDENT_FF 2928 root432 local2496; all q/q_check distinct"
}
