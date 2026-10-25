# S81-CORES/LEGACY post-CTS clock probe (read-only): per register CK arrival (TT, placement parasitics), location,
# clock buffers; macro clock pins.   env ODB SDC OUT (csv) KIT
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain $::env(KIT)/macros/*_tt.lib] { read_liberty $f }
foreach f [glob -nocomplain $::env(KIT)/macros/*.lef] { }
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fh [open $::env(OUT) w]
puts $fh "kind,inst,master,x,y,ck_ps"
foreach p [all_registers -clock_pins] {
  set a ""
  catch {set a [get_property $p arrival_max_rise]}
  set c [get_cells -of_objects $p]
  set n [get_full_name $c]
  set dbi [sta::sta_to_db_inst $c]
  if {$dbi eq "NULL"} continue
  lassign [$dbi getLocation] x y
  set m [[$dbi getMaster] getName]
  set k [expr {[[$dbi getMaster] isBlock] ? "macro" : "ff"}]
  if {$a eq ""} { set a -1 } else { set a [expr {$a * 1.0}] }
  puts $fh "$k,$n,$m,[expr {$x/double($dbu)}],[expr {$y/double($dbu)}],$a"
}
foreach i [[ord::get_db_block] getInsts] {
  set m [[$i getMaster] getName]
  if {[regexp {^(CKBUF|BUF|INV|HB).*} $m]} {
    set isck 0
    foreach it [$i getITerms] { set nn [$it getNet]; if {$nn ne "NULL" && [$nn getSigType] eq "CLOCK"} { set isck 1 } }
    if {$isck} { lassign [$i getLocation] x y; puts $fh "ckbuf,[$i getName],$m,[expr {$x/double($dbu)}],[expr {$y/double($dbu)}],0" }
  }
}
foreach port [get_ports *] {
  set pn [get_full_name $port]
  if {[regexp {^(clk|ck|rst_n|rst|rs)(\[0\])?$} $pn]} continue
  set bt [[ord::get_db_block] findBTerm $pn]
  if {$bt eq "NULL"} continue
  set bb [$bt getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]
  set best 1e9
  set front [list [$bt getNet]]
  set seen {}
  for {set dep 0} {$dep < 40 && [llength $front]} {incr dep} {
    set nxt {}
    foreach net $front {
      if {$net eq "NULL" || [dict exists $seen [$net getName]]} continue
      dict set seen [$net getName] 1
      foreach it [$net getITerms] {
        set i [$it getInst]; set m [[$i getMaster] getName]
        if {[string match *DFF* $m] || [[$i getMaster] isBlock]} {
          set b2 [$i getBBox]
          set d [expr {abs(([$b2 xMin]+[$b2 xMax])/2.0/$dbu - $px) + abs(([$b2 yMin]+[$b2 yMax])/2.0/$dbu - $py)}]
          if {$d < $best} { set best $d }
        } elseif {[regexp {^(BUF|INV|HB)} $m]} {
          foreach it2 [$i getITerms] { set n2 [$it2 getNet]; if {$n2 ne "NULL" && [$n2 getSigType] eq "SIGNAL"} { lappend nxt $n2 } }
        }
      }
    }
    if {$best < 1e9} break
    set front $nxt
  }
  puts $fh "pinreg,$pn,,$px,$py,$best"
}
close $fh
puts "CK_PROBE_DONE"
