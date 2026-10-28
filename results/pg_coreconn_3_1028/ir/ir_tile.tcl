# PG-CORECONN-3: generic tile IR with every hard core's power SPREAD over its own PG pin landings
# (PG-CORECONN-2 ir_dist.tcl method, generalised): per macro PG layer L in {M4,M5,M6} a macro grid connect L->L+1,
# one load per L->L+1 via inside the macro's own pin shapes; macro ITerms disconnected (no lumped PSM node).
# Macros with M7 PG pins carry their own PDN to M7 (signed view; tile adds only M7) -> excluded, listed OT_SKIP.
# Macro power basis: OT_DENS W/mm2 x macro area (conservative); std cells = STA at register activity OT_ACT.
set dens $::env(OT_DENS); set act $::env(OT_ACT); set odb $::env(OT_ODB); set sdc $::env(OT_SDC); set tag $::env(OT_TAG)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_db $odb
read_lef -library /o/pgload.lef
read_sdc $sdc
set block [ord::get_db_block]; set db [ord::get_db]; set dbu [$block getDbUnitsPerMicron]
# classify macros
array set LAY {}; set land {}; set skip {}
foreach inst [$block getInsts] {
  set m [$inst getMaster]; if {![$m isBlock]} continue
  set mt [$m findMTerm VDD]; set ms [$m findMTerm VSS]
  if {$mt eq "NULL" || $ms eq "NULL"} { lappend skip [list [$inst getName] [$m getName] nopg]; continue }
  set ls {}
  foreach mp [$mt getMPins] { foreach g [$mp getGeometry] { set ln [[$g getTechLayer] getName]; if {$ln in {M4 M5 M6} && $ln ni $ls} { lappend ls $ln } } }
  set has7 0; foreach mp [$mt getMPins] { foreach g [$mp getGeometry] { if {[[$g getTechLayer] getName] eq "M7"} { set has7 1 } } }
  if {$has7} { lappend skip [list [$inst getName] [$m getName] own_pdn_to_M7]; continue }
  if {[llength $ls] == 0} { lappend skip [list [$inst getName] [$m getName] nolandable]; continue }
  set L [lindex [lsort $ls] 0]; set LAY([$inst getName]) $L; lappend land [$inst getName]
}
puts "OT_MACROS landable=[llength $land] skipped=[llength $skip]"
foreach s $skip { puts "OT_SKIP $s" }
pdngen -ripup
source /k/pdn.tcl
set up {M4 M5 M5 M6 M6 M7}
foreach L {M4 M5 M6} {
  set pats {}
  foreach i $land { if {$LAY($i) eq $L} { lappend pats "^[string map {. \\. [ \\[ ] \\]} $i]\$" } }
  if {[llength $pats] == 0} continue
  define_pdn_grid -macro -name core_pg_$L -instances $pats -voltage_domains {CORE} -halo {0}
  add_pdn_connect -grid core_pg_$L -layers [list $L [dict get $up $L]]
}
pdngen
set ar 0.0
foreach netn {VDD VSS} {
  set net [$block findNet $netn]; 
  # via index by bottom layer
  array unset VI; array set VI {}
  foreach sw [$net getSWires] { foreach b [$sw getWires] {
    if {![$b isVia]} continue
    set v [$b getBlockVia]; if {$v eq "NULL" || $v eq ""} { set v [$b getTechVia] }
    lappend VI([[$v getBottomLayer] getName]) [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] } }
  foreach iname $land {
    set inst [$block findInst $iname]; set L $LAY($iname)
    set bb [$inst getBBox]; set x0 [$bb xMin]; set y0 [$bb yMin]; set x1 [$bb xMax]; set y1 [$bb yMax]
    set area [expr {double($x1-$x0)*($y1-$y0)/$dbu/$dbu*1e-6}]
    set P [expr {$dens*$area}]
    set rects {}
    set mt [[$inst getMaster] findMTerm $netn]
    set o [$inst getOrient]; set mw [[$inst getMaster] getWidth]; set mh [[$inst getMaster] getHeight]
    if {$o ni {R0 MX MY R180}} { puts "OT_DIST_FAIL orient $o"; exit 1 }
    foreach mp [$mt getMPins] { foreach g [$mp getGeometry] {
      if {[[$g getTechLayer] getName] ne $L} continue
      set ax [$g xMin]; set bx [$g xMax]; set ay [$g yMin]; set by [$g yMax]
      if {$o in {MY R180}} { set t [expr {$mw-$bx}]; set bx [expr {$mw-$ax}]; set ax $t }
      if {$o in {MX R180}} { set t [expr {$mh-$by}]; set by [expr {$mh-$ay}]; set ay $t }
      lappend rects [list [expr {$x0+$ax}] [expr {$y0+$ay}] [expr {$x0+$bx}] [expr {$y0+$by}]] } }
    set pts {}
    if {[info exists VI($L)]} { foreach p $VI($L) { lassign $p cx cy
      if {$cx < $x0 || $cx > $x1 || $cy < $y0 || $cy > $y1} continue
      foreach r $rects { lassign $r a b2 c d; if {$cx >= $a && $cx <= $c && $cy >= $b2 && $cy <= $d} { lappend pts $p; break } } } }
    set n [llength $pts]
    puts "OT_DIST $netn $iname [[$inst getMaster] getName] $L $o rects=[llength $rects] vias=$n area_mm2=[format %.5f $area] P=[format %.6f $P]"
    if {$n == 0} { puts "OT_DIST_FAIL no landings $netn $iname"; exit 1 }
    if {$netn eq "VDD"} { set ar [expr {$ar+$area}] }
    set master [$db findMaster OT_PGL_${netn}_$L]; set k 0; set ll {}
    foreach p $pts { lassign $p cx cy
      set li [odb::dbInst_create $block $master "pgl_${netn}_[regsub -all {[^A-Za-z0-9]} $iname _]_$k"]
      $li setLocation [expr {$cx - 27}] [expr {$cy - 27}]; $li setPlacementStatus FIRM
      [$li findITerm $netn] connect $net; lappend ll $li; incr k }
    set LD($iname,$netn) $ll; set PW($iname,$netn) [expr {$P/$n}]
    [$inst findITerm $netn] disconnect
  }
}
foreach s $skip { set inst [$block findInst [lindex $s 0]]; foreach netn {VDD VSS} { set it [$inst findITerm $netn]; if {$it ne "NULL"} { $it disconnect } } }
puts "OT_MACRO_AREA_MM2 $ar OT_MACRO_W [expr {$ar*$dens}]"
if {[file exists /k/setRC_rcx.tcl]} { source /k/setRC_rcx.tcl } else { source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl }
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set nr 0
foreach r [all_registers] { foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $act -duty 0.5 }; incr nr }
foreach p [all_inputs -no_clocks] { set_power_activity -input_ports $p -activity $act -duty 0.5 }
puts "OT_ACT regs=$nr rate=$act"
report_power -digits 6 > /o/power_${tag}.rpt
foreach k [array names LD] { foreach li $LD($k) { set_pdnsim_inst_power -inst [$li getName] -power $PW($k) } }
set_pdnsim_net_voltage -net VDD -voltage 0.70
set_pdnsim_net_voltage -net VSS -voltage 0.0
foreach net {VDD VSS} {
  puts "OT_IR_BEGIN $tag $net"
  analyze_power_grid -net $net -error_file /o/err_${tag}_$net.rpt -voltage_file /o/volt_${tag}_$net.rpt
  puts "OT_IR_END $tag $net"
}
exit
