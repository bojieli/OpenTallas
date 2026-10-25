set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n [$b findNet VDD]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VDD] }
$n setSigType POWER; $n setSpecial
set n [$b findNet VDDPHY]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VDDPHY] }
$n setSigType POWER; $n setSpecial
set n [$b findNet VSS]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VSS] }
$n setSigType GROUND; $n setSpecial
add_global_connection -net {VDD} -inst_pattern {^mixed$} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {^mixed$} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {^mixed$} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {^mixed$} -pin_pattern {^VSS$} -ground
add_global_connection -net {VDDPHY} -inst_pattern {^mixed$} -pin_pattern {^VDDPHY$} -power
add_global_connection -net {VSS} -inst_pattern {^mixed$} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name Core -power VDD -ground VSS -secondary_power {VDDPHY}
set region [odb::dbRegion_create $b ot_pg_0]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(0*$dbu)}] [expr {round(345.6*$dbu)}] [expr {round(86.4*$dbu)}]
set_voltage_domain -name ot_pg_0 -region ot_pg_0 -power VDD -ground VSS
define_pdn_grid -name ot_pg_0 -voltage_domains {ot_pg_0} -starts_with GROUND
add_pdn_stripe -grid ot_pg_0 -layer M8 -width 0.48 -pitch 8.64 -offset 4.32 -spacing 3.84
add_pdn_stripe -grid ot_pg_0 -layer M9 -width 0.48 -pitch 8.64 -offset 4.32 -spacing 3.84
add_pdn_connect -grid ot_pg_0 -layers {M8 M9}
set region [odb::dbRegion_create $b ot_pg_1]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(86.4*$dbu)}] [expr {round(345.6*$dbu)}] [expr {round(345.6*$dbu)}]
set_voltage_domain -name ot_pg_1 -region ot_pg_1 -power VDDPHY -ground VSS
define_pdn_grid -name ot_pg_1 -voltage_domains {ot_pg_1} -starts_with GROUND
add_pdn_stripe -grid ot_pg_1 -layer M8 -width 1.92 -pitch 8.64 -offset 4.32 -spacing 2.4
add_pdn_stripe -grid ot_pg_1 -layer M9 -width 1.92 -pitch 8.64 -offset 4.32 -spacing 2.4
add_pdn_connect -grid ot_pg_1 -layers {M8 M9}
set ot_pg_pin_rects {
  {VDD 3.9840 0.0000 4.2720 86.3040}
  {VDD 12.6240 0.0000 12.9120 86.3040}
  {VDD 21.2640 0.0000 21.5520 86.3040}
  {VDD 29.9040 0.0000 30.1920 86.3040}
  {VDD 38.5440 0.0000 38.8320 86.3040}
  {VDD 47.1840 0.0000 47.4720 86.3040}
  {VDD 55.8240 0.0000 56.1120 86.3040}
  {VDD 64.4640 0.0000 64.7520 86.3040}
  {VDD 73.1040 0.0000 73.3920 86.3040}
  {VDD 81.7440 0.0000 82.0320 86.3040}
  {VDD 90.3840 0.0000 90.6720 86.3040}
  {VDD 99.0240 0.0000 99.3120 86.3040}
  {VDD 107.6640 0.0000 107.9520 86.3040}
  {VDD 116.3040 0.0000 116.5920 86.3040}
  {VDD 124.9440 0.0000 125.2320 86.3040}
  {VDD 133.5840 0.0000 133.8720 86.3040}
  {VDD 142.2240 0.0000 142.5120 86.3040}
  {VDD 150.8640 0.0000 151.1520 86.3040}
  {VDD 159.5040 0.0000 159.7920 86.3040}
  {VDD 168.1440 0.0000 168.4320 86.3040}
  {VDD 176.7840 0.0000 177.0720 86.3040}
  {VDD 185.4240 0.0000 185.7120 86.3040}
  {VDD 194.0640 0.0000 194.3520 86.3040}
  {VDD 202.7040 0.0000 202.9920 86.3040}
  {VDD 211.3440 0.0000 211.6320 86.3040}
  {VDD 219.9840 0.0000 220.2720 86.3040}
  {VDD 228.6240 0.0000 228.9120 86.3040}
  {VDD 237.2640 0.0000 237.5520 86.3040}
  {VDD 245.9040 0.0000 246.1920 86.3040}
  {VDD 254.5440 0.0000 254.8320 86.3040}
  {VDD 263.1840 0.0000 263.4720 86.3040}
  {VDD 271.8240 0.0000 272.1120 86.3040}
  {VDD 280.4640 0.0000 280.7520 86.3040}
  {VDD 289.1040 0.0000 289.3920 86.3040}
  {VDD 297.7440 0.0000 298.0320 86.3040}
  {VDD 306.3840 0.0000 306.6720 86.3040}
  {VDD 315.0240 0.0000 315.3120 86.3040}
  {VDD 323.6640 0.0000 323.9520 86.3040}
  {VDD 332.3040 0.0000 332.5920 86.3040}
  {VDD 340.9440 0.0000 341.2320 86.3040}
  {VSS 4.3680 0.0000 4.6560 345.6000}
  {VSS 13.0080 0.0000 13.2960 345.6000}
  {VSS 21.6480 0.0000 21.9360 345.6000}
  {VSS 30.2880 0.0000 30.5760 345.6000}
  {VSS 38.9280 0.0000 39.2160 345.6000}
  {VSS 47.5680 0.0000 47.8560 345.6000}
  {VSS 56.2080 0.0000 56.4960 345.6000}
  {VSS 64.8480 0.0000 65.1360 345.6000}
  {VSS 73.4880 0.0000 73.7760 345.6000}
  {VSS 82.1280 0.0000 82.4160 345.6000}
  {VSS 90.7680 0.0000 91.0560 345.6000}
  {VSS 99.4080 0.0000 99.6960 345.6000}
  {VSS 108.0480 0.0000 108.3360 345.6000}
  {VSS 116.6880 0.0000 116.9760 345.6000}
  {VSS 125.3280 0.0000 125.6160 345.6000}
  {VSS 133.9680 0.0000 134.2560 345.6000}
  {VSS 142.6080 0.0000 142.8960 345.6000}
  {VSS 151.2480 0.0000 151.5360 345.6000}
  {VSS 159.8880 0.0000 160.1760 345.6000}
  {VSS 168.5280 0.0000 168.8160 345.6000}
  {VSS 177.1680 0.0000 177.4560 345.6000}
  {VSS 185.8080 0.0000 186.0960 345.6000}
  {VSS 194.4480 0.0000 194.7360 345.6000}
  {VSS 203.0880 0.0000 203.3760 345.6000}
  {VSS 211.7280 0.0000 212.0160 345.6000}
  {VSS 220.3680 0.0000 220.6560 345.6000}
  {VSS 229.0080 0.0000 229.2960 345.6000}
  {VSS 237.6480 0.0000 237.9360 345.6000}
  {VSS 246.2880 0.0000 246.5760 345.6000}
  {VSS 254.9280 0.0000 255.2160 345.6000}
  {VSS 263.5680 0.0000 263.8560 345.6000}
  {VSS 272.2080 0.0000 272.4960 345.6000}
  {VSS 280.8480 0.0000 281.1360 345.6000}
  {VSS 289.4880 0.0000 289.7760 345.6000}
  {VSS 298.1280 0.0000 298.4160 345.6000}
  {VSS 306.7680 0.0000 307.0560 345.6000}
  {VSS 315.4080 0.0000 315.6960 345.6000}
  {VSS 324.0480 0.0000 324.3360 345.6000}
  {VSS 332.6880 0.0000 332.9760 345.6000}
  {VSS 341.3280 0.0000 341.6160 345.6000}
  {VDDPHY 3.9840 86.4000 4.2720 345.6000}
  {VDDPHY 12.6240 86.4000 12.9120 345.6000}
  {VDDPHY 21.2640 86.4000 21.5520 345.6000}
  {VDDPHY 29.9040 86.4000 30.1920 345.6000}
  {VDDPHY 38.5440 86.4000 38.8320 345.6000}
  {VDDPHY 47.1840 86.4000 47.4720 345.6000}
  {VDDPHY 55.8240 86.4000 56.1120 345.6000}
  {VDDPHY 64.4640 86.4000 64.7520 345.6000}
  {VDDPHY 73.1040 86.4000 73.3920 345.6000}
  {VDDPHY 81.7440 86.4000 82.0320 345.6000}
  {VDDPHY 90.3840 86.4000 90.6720 345.6000}
  {VDDPHY 99.0240 86.4000 99.3120 345.6000}
  {VDDPHY 107.6640 86.4000 107.9520 345.6000}
  {VDDPHY 116.3040 86.4000 116.5920 345.6000}
  {VDDPHY 124.9440 86.4000 125.2320 345.6000}
  {VDDPHY 133.5840 86.4000 133.8720 345.6000}
  {VDDPHY 142.2240 86.4000 142.5120 345.6000}
  {VDDPHY 150.8640 86.4000 151.1520 345.6000}
  {VDDPHY 159.5040 86.4000 159.7920 345.6000}
  {VDDPHY 168.1440 86.4000 168.4320 345.6000}
  {VDDPHY 176.7840 86.4000 177.0720 345.6000}
  {VDDPHY 185.4240 86.4000 185.7120 345.6000}
  {VDDPHY 194.0640 86.4000 194.3520 345.6000}
  {VDDPHY 202.7040 86.4000 202.9920 345.6000}
  {VDDPHY 211.3440 86.4000 211.6320 345.6000}
  {VDDPHY 219.9840 86.4000 220.2720 345.6000}
  {VDDPHY 228.6240 86.4000 228.9120 345.6000}
  {VDDPHY 237.2640 86.4000 237.5520 345.6000}
  {VDDPHY 245.9040 86.4000 246.1920 345.6000}
  {VDDPHY 254.5440 86.4000 254.8320 345.6000}
  {VDDPHY 263.1840 86.4000 263.4720 345.6000}
  {VDDPHY 271.8240 86.4000 272.1120 345.6000}
  {VDDPHY 280.4640 86.4000 280.7520 345.6000}
  {VDDPHY 289.1040 86.4000 289.3920 345.6000}
  {VDDPHY 297.7440 86.4000 298.0320 345.6000}
  {VDDPHY 306.3840 86.4000 306.6720 345.6000}
  {VDDPHY 315.0240 86.4000 315.3120 345.6000}
  {VDDPHY 323.6640 86.4000 323.9520 345.6000}
  {VDDPHY 332.3040 86.4000 332.5920 345.6000}
  {VDDPHY 340.9440 86.4000 341.2320 345.6000}
}

# Explicit same-net PG contacts for a containing macro spanning supply regions.
# Native macro grids select one voltage domain per instance and cannot represent
# this mixed macro. Use the technology's fixed VIA78 in a 2x2 array: 80nm pitch
# exceeds V7 cut32nm+spacing46nm and satisfies the wide-strap multi-cut rule.
proc ot_pg_connect_pins {} {
  global ot_pg_pin_rects
  set block [ord::get_db_block]
  set tech [ord::get_db_tech]
  set dbu [$tech getDbUnitsPerMicron]
  set via [$tech findVia VIA78]
  if {$via eq "NULL"} { error "regional PG needs actual technology VIA78" }
  set metal {}; set wires {}; set done {}; set count 0
  foreach q $ot_pg_pin_rects {
    lassign $q netname ux0 uy0 ux1 uy1
    if {![dict exists $metal $netname]} {
      set boxes {};set net [$block findNet $netname]
      foreach w [$net getSWires] {
        foreach s [$w getWires] {
          if {[$s isVia] || [[$s getTechLayer] getName] ne "M8"} continue
          lappend boxes [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
        }
      }
      dict set metal $netname $boxes
      dict set wires $netname [odb::dbSWire_create $net ROUTED]
    }
    set x0 [expr {round($ux0*$dbu)}];set y0 [expr {round($uy0*$dbu)}]
    set x1 [expr {round($ux1*$dbu)}];set y1 [expr {round($uy1*$dbu)}]
    foreach r [dict get $metal $netname] {
      lassign $r a b c d
      set x [expr {round(($x0+$x1)/2.0)}];set y [expr {round(($b+$d)/2.0)}]
      # Entire four-via enclosure must fit real M7 pin and actual same-net M8.
      set vx [expr {round(.056*$dbu)}];set vy [expr {round(.067*$dbu)}]
      set tx [expr {round(.067*$dbu)}];set ty [expr {round(.060*$dbu)}]
      if {$x-$vx<$x0 || $x+$vx>$x1 || $y-$vy<$y0 || $y+$vy>$y1 || $x-$tx<$a || $x+$tx>$c || $y-$ty<$b || $y+$ty>$d} continue
      set key [list $netname $x $y]
      if {[dict exists $done $key]} continue
      dict set done $key 1
      foreach dx {-0.040 0.040} {
        foreach dy {-0.040 0.040} {
          odb::dbSBox_create [dict get $wires $netname] $via [expr {round($x+$dx*$dbu)}] [expr {round($y+$dy*$dbu)}] STRIPE
          incr count
        }
      }
    }
  }
  puts "OT_PG_PIN_VIAS $count"
  if {!$count} {error "regional PG made no actual pin-to-mesh contacts"}
}

