proc ds_native_one {values label} {
  if {[llength $values] != 1} {error "Ambiguous/missing native $label"}
  return [lindex $values 0]
}
proc ds_native_pin {inst pin} {
  set it [$inst findITerm $pin]
  if {$it == "NULL"} {error "Missing native pin $pin"}
  return [$it getNet]
}
proc ds_native_binding {} {
  set block [ord::get_db_block]
  set clock [$block findBTerm clk]
  if {$clock == "NULL"} {error "Missing original clock port"}
  set cn [$clock getNet]; set sources {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] eq "BUFx4_ASAP7_75t_R" && [ds_native_pin $inst A] eq $cn} {lappend sources $inst}
  }
  set source [ds_native_one $sources clock_driver]
  set sy [ds_native_pin $source Y]
  set result [dict create source_buf $source]; set used [list $source]
  for {set i 0} {$i<8} {incr i} {
    set port [$block findBTerm [format {d[%d]} $i]]
    if {$port == "NULL"} {error "Missing original data port $i"}
    set dn [$port getNet];set sinks {}
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] getName] eq "DFFHQNx1_ASAP7_75t_R" && [ds_native_pin $inst D] eq $dn} {lappend sinks $inst}
    }
    set sink [ds_native_one $sinks sink_$i]
    set sn [ds_native_pin $sink CLK]; set relays {}
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] getName] eq "BUFx4_ASAP7_75t_R" && [ds_native_pin $inst A] eq $sy && [ds_native_pin $inst Y] eq $sn} {lappend relays $inst}
    }
    set relay [ds_native_one $relays relay_$i]
    dict set result sink_$i $sink;dict set result relay_$i $relay
    lappend used $sink $relay
  }
  if {[llength [lsort -unique $used]] != 17} {error "Native 17-cell ownership aliases"}
  return $result
}
