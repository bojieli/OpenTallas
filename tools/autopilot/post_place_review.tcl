# post_place_review.tcl (STAGE-PLATEAU): post-placement review of a kit's 3_3_place_gp / 3_5_place_dp ODB.
# Run inside the pinned ORFS image after `read_db <odb>` (tools/autopilot/post_place_review.py writes the wrapper).
# env: PPR_OUT   output dir (writes layout.json, pins.tsv, nets.tsv, macros.tsv, macro_pins.tsv, paths_ideal_raw.txt, ppr_tcl.log)
#      PPR_NPATH top-N setup paths (default 50)       PPR_SDC  sdc to read (default: first of base/3_place.sdc, 2_floorplan.sdc, gen/constraint.sdc)
#      PPR_LIBS  extra liberty globs (space list)     OT_LAYOUT_BINS density bins (default 64)
# Method: ideal clock (propagated clocks removed), estimate_parasitics -placement, report_checks max; geometry for the python
# renderer is dumped from the DB (the python side draws; no headless GUI is used).
set ppr_out $::env(PPR_OUT)
set ppr_n [expr {[info exists ::env(PPR_NPATH)] ? $::env(PPR_NPATH) : 50}]
set ppr_block [ord::get_db_block]
set ppr_dbu [expr {double([$ppr_block getDbUnitsPerMicron])}]
proc ppr_um {v} { return [format %.3f [expr {$v / $::ppr_dbu}]] }
set ppr_t0 [clock seconds]
set ppr_tmax 900 ;# safety: stop macro-pin enumeration after this many seconds in the script
proc ppr_log {m} { puts "PPR t=[expr {[clock seconds] - $::ppr_t0}]s $m"; flush stdout }

# ---------------------------------------------------------------- 1. layout geometry (blocks, pins, PG straps, density)
set ::env(OT_LAYOUT_OUT) $ppr_out/layout.json
if {![info exists ::env(OT_LAYOUT_BINS)]} { set ::env(OT_LAYOUT_BINS) 64 }
if {[catch {source [file join [file dirname [file normalize [info script]]] layout_dump.tcl]} err]} { ppr_log "LAYOUT_DUMP_FAILED $err" }

# ---------------------------------------------------------------- 2. net bounding boxes (RUDY input) + pin table
proc ppr_iterm_xy {it} {
  if {![catch {$it getAvgXY x y} ok] && $ok} { return [list $x $y] }
  set bb [[$it getInst] getBBox]
  return [list [expr {([$bb xMin] + [$bb xMax]) / 2}] [expr {([$bb yMin] + [$bb yMax]) / 2}]]
}
proc ppr_net_bbox {net} {
  set xs {}; set ys {}; set n 0
  foreach it [$net getITerms] {
    lassign [ppr_iterm_xy $it] x y; lappend xs $x; lappend ys $y; incr n
  }
  foreach bt [$net getBTerms] {
    set bb [$bt getBBox]
    if {$bb ne "NULL"} { lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2}]; lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2}]; incr n }
  }
  if {$n < 2} { return {} }
  return [list [tcl::mathfunc::min {*}$xs] [tcl::mathfunc::min {*}$ys] [tcl::mathfunc::max {*}$xs] [tcl::mathfunc::max {*}$ys] $n]
}
ppr_log "NETS_START"
set f [open $ppr_out/nets.tsv w]
puts $f "x0\ty0\tx1\ty1\tpins"
set ppr_nn 0
foreach net [$ppr_block getNets] {
  if {[$net getSigType] eq "POWER" || [$net getSigType] eq "GROUND"} { continue }
  set b [ppr_net_bbox $net]
  if {$b eq ""} { continue }
  lassign $b x0 y0 x1 y1 n
  puts $f "[ppr_um $x0]\t[ppr_um $y0]\t[ppr_um $x1]\t[ppr_um $y1]\t$n"
  incr ppr_nn
}
close $f
ppr_log "NETS $ppr_nn"

# ---------------------------------------------------------------- 3. macros: halo + pin faces
ppr_log "MACROS_START"
set f [open $ppr_out/macros.tsv w]
set g [open $ppr_out/macro_pins.tsv w]
puts $f "name\tmaster\tx0\ty0\tx1\ty1\thalo_l\thalo_b\thalo_r\thalo_t"
puts $g "macro\tpin\tlayer\tx0\ty0\tx1\ty1"
set ppr_np 0
foreach inst [$ppr_block getInsts] {
  if {![[$inst getMaster] isBlock]} { continue }
  set bb [$inst getBBox]
  set h {0 0 0 0}
  if {![catch {$inst getHalo} hb] && $hb ne "NULL" && $hb ne ""} { catch { set h [list [$hb xMin] [$hb yMin] [$hb xMax] [$hb yMax]] } }
  puts $f "[$inst getName]\t[[$inst getMaster] getName]\t[ppr_um [$bb xMin]]\t[ppr_um [$bb yMin]]\t[ppr_um [$bb xMax]]\t[ppr_um [$bb yMax]]\t[ppr_um [lindex $h 0]]\t[ppr_um [lindex $h 1]]\t[ppr_um [lindex $h 2]]\t[ppr_um [lindex $h 3]]"
  foreach it [$inst getITerms] {
    if {[$it getSigType] eq "POWER" || [$it getSigType] eq "GROUND"} { continue }
    if {[catch {$it getGeometries} geoms]} { continue }
    # getGeometries -> list of {dbTechLayer Rect} pairs (already in die coordinates)
    set mtn [[$it getMTerm] getName]
    foreach pr $geoms {
      lassign $pr lay r
      puts $g "[$inst getName]\t$mtn\t[$lay getName]\t[ppr_um [$r xMin]]\t[ppr_um [$r yMin]]\t[ppr_um [$r xMax]]\t[ppr_um [$r yMax]]"
      incr ppr_np
    }
    if {[clock seconds] - $ppr_t0 > $ppr_tmax} { break }
  }
}
close $f; close $g
ppr_log "MACRO_PIN_RECTS $ppr_np"

# ---------------------------------------------------------------- 4. STA, ideal clock, placement parasitics
set ppr_plat /OpenROAD-flow-scripts/flow/platforms/asap7
proc ppr_sta {} {
  global ppr_out ppr_n ppr_plat
  set odb $::env(PPR_ODB)
  set base [file dirname $odb]
  set run [file normalize $base/../../../..]
  set gen [file normalize $run/..]
  foreach f [concat [glob -nocomplain $run/objects/asap7/*/base/lib/*.lib] [glob -nocomplain $ppr_plat/lib/NLDM/*RVT_TT*]] { catch {read_liberty $f} }
  if {[info exists ::env(PPR_LIBS)]} { foreach p $::env(PPR_LIBS) { foreach f [glob -nocomplain $p] { catch {read_liberty $f} } } }
  if {[file exists $gen/config.mk]} {
    foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LIBS' $gen/config.mk || true"] "\n"] {
      foreach w [lrange [split $l " ="] 1 end] { set w [string map [list /work/ $gen/] $w]; if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} } }      ;# the kit is mounted at /kit here, config.mk names /work/macros/*.lib
    }
  }
  set sdc ""
  if {[info exists ::env(PPR_SDC)] && $::env(PPR_SDC) ne ""} { set sdc $::env(PPR_SDC) } else {
    foreach c [list $base/3_place.sdc $base/2_floorplan.sdc $base/1_synth.sdc $gen/constraint.sdc] { if {[file exists $c]} { set sdc $c; break } }
  }
  if {$sdc eq ""} { error "no sdc found" }
  read_sdc $sdc
  ppr_log "SDC $sdc"
  catch {unset_propagated_clock [all_clocks]}
  source $ppr_plat/setRC.tcl
  estimate_parasitics -placement
  report_checks -path_delay max -group_path_count $ppr_n -sort_by_slack -format full -digits 3 > $ppr_out/paths_ideal_raw.txt
  # quick setup STA summary (COORD 08:xx): clock period, WNS, TNS and every endpoint below -150 ps (the SDC's time unit is ps), read by post_place_review.py finish()
  catch {report_wns -digits 3 > $ppr_out/sta_wns.txt}
  catch {report_tns -digits 3 > $ppr_out/sta_tns.txt}
  catch {report_checks -path_delay max -group_path_count 200000 -slack_max -150 -format end -digits 3 > $ppr_out/sta_below150.txt}
  catch {set pf [open $ppr_out/sta_clocks.txt w]; foreach c [all_clocks] { puts $pf "[get_name $c] [get_property $c period]" }; close $pf}
  # pin table for every pin that appears in the report
  set txt [read [set fh [open $ppr_out/paths_ideal_raw.txt]]]; close $fh
  array set seen {}
  set o [open $ppr_out/pins.tsv w]
  puts $o "pin\tx\ty\tnet\tnet_hpwl_um\tfanout"
  foreach {all pin} [regexp -all -inline -line {^\s+(?:[-\d.]+\s+)+[\^v]\s+(\S+)\s+\(} $txt] {
    if {[info exists seen($pin)]} { continue }
    set seen($pin) 1
    set un [string map {"\\" ""} $pin]
    set it ""
    foreach nm [list $pin $un] { if {![catch {$::ppr_block findITerm $nm} r] && $r ne "NULL" && $r ne ""} { set it $r; break } }
    if {$it ne ""} {
      lassign [ppr_iterm_xy $it] x y
      set net [$it getNet]
      set nn "-"; set hp 0.0; set fo 0
      if {$net ne "NULL" && $net ne ""} {
        set nn [$net getName]
        set b [ppr_net_bbox $net]
        if {$b ne ""} { set hp [expr {([lindex $b 2] - [lindex $b 0] + [lindex $b 3] - [lindex $b 1]) / $::ppr_dbu}]; set fo [lindex $b 4] }
      }
      puts $o "$pin\t[ppr_um $x]\t[ppr_um $y]\t$nn\t[format %.3f $hp]\t$fo"
      continue
    }
    foreach nm [list $pin $un] {
      if {![catch {$::ppr_block findBTerm $nm} bt] && $bt ne "NULL" && $bt ne ""} {
        set bb [$bt getBBox]; set net [$bt getNet]; set hp 0.0; set fo 0; set nn "-"
        if {$net ne "NULL" && $net ne ""} { set nn [$net getName]; set b [ppr_net_bbox $net]; if {$b ne ""} { set hp [expr {([lindex $b 2] - [lindex $b 0] + [lindex $b 3] - [lindex $b 1]) / $::ppr_dbu}]; set fo [lindex $b 4] } }
        puts $o "$pin\t[ppr_um [expr {([$bb xMin] + [$bb xMax]) / 2}]]\t[ppr_um [expr {([$bb yMin] + [$bb yMax]) / 2}]]\t$nn\t[format %.3f $hp]\t$fo"
        break
      }
    }
  }
  close $o
}
if {[catch {ppr_sta} err]} {
  ppr_log "STA_SKIPPED $err"
  set fh [open $ppr_out/sta_error.txt w]; puts $fh $err; close $fh
} else { ppr_log "STA_OK paths_ideal_raw.txt" }
ppr_log "DONE"
