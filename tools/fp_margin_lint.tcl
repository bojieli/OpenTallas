# Floorplan margin lint (fp-lint 2026-10-08): dump the floorplan geometry tools/fp_margin_lint.py judges.
#
# Runs inside OpenROAD on a loaded floorplan (ORFS 3_2_place_iop.odb, before global placement) or offline:
#   openroad -exit -no_init <(echo 'read_db X.odb; source tools/fp_margin_lint.tcl; ot_fp_lint_dump out.json')
# In the flow (closure loop, OT_FP_LINT=1) tools/orfs_hold_mm.py patches ORFS util.tcl so that the PRE GLOBAL_PLACE step
# hook calls ot_fp_lint_flow after the block's own PRE_GLOBAL_PLACE hook: dump, judge with fp_margin_lint.py, and on a
# FAIL stop the flow with "FLOORPLAN_MARGIN: <reasons>" (the loop turns that into verdict FLOORPLAN_MARGIN).

set ::ot_fpl_dir [file dirname [file normalize [info script]]]

proc ot_fpl_q {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

proc ot_fpl_rect {r dbu} {
  return [format {[%.4f,%.4f,%.4f,%.4f]} [expr {double([$r xMin]) / $dbu}] [expr {double([$r yMin]) / $dbu}] \
            [expr {double([$r xMax]) / $dbu}] [expr {double([$r yMax]) / $dbu}]]
}

proc ot_fp_lint_dump {out {edge_band_um 3.0}} {
  set block [ord::get_db_block]
  set tech [ord::get_db_tech]
  set dbu [expr {double([$tech getDbUnitsPerMicron])}]
  set die [$block getDieArea]
  set core [$block getCoreArea]
  set band [expr {int($edge_band_um * $dbu)}]
  set dx0 [expr {[$die xMin] + $band}]; set dx1 [expr {[$die xMax] - $band}]
  set dy0 [expr {[$die yMin] + $band}]; set dy1 [expr {[$die yMax] - $band}]
  set f [open $out w]
  puts $f "\{\"dbu\": $dbu, \"die\": [ot_fpl_rect $die $dbu], \"core\": [ot_fpl_rect $core $dbu], \"edge_band_um\": $edge_band_um,"
  foreach v {MIN_ROUTING_LAYER MAX_ROUTING_LAYER TECH_LEF PLACE_DENSITY} {
    if {[info exists ::env($v)]} { puts $f "[ot_fpl_q env_$v]: [ot_fpl_q $::env($v)]," }
  }
  # routing layers
  set ls {}
  foreach l [$tech getLayers] {
    if {[$l getType] ne "ROUTING"} { continue }
    lappend ls "\{\"name\": [ot_fpl_q [$l getName]], \"level\": [$l getRoutingLevel], \"dir\": [ot_fpl_q [$l getDirection]],\
 \"pitch\": [expr {[$l getPitch] / $dbu}], \"width\": [expr {[$l getWidth] / $dbu}]\}"
  }
  puts $f "\"layers\": \[[join $ls ,]\],"
  # instances: per-master counts, macros (BLOCK masters) with their geometry
  set mcount [dict create]
  set macros {}
  set mrefs {}
  foreach inst [$block getInsts] {
    set m [$inst getMaster]
    set mn [$m getName]
    dict incr mcount $mn
    if {[$m isBlock]} { lappend mrefs $inst }
  }
  set ms {}
  dict for {mn n} $mcount {
    set mm [[ord::get_db] findMaster $mn]
    set obs_top 0
    if {[$mm isBlock]} {
      foreach o [$mm getObstructions] {
        set tl [$o getTechLayer]
        if {$tl ne "NULL" && [$tl getType] eq "ROUTING"} { set obs_top [expr {max($obs_top, [$tl getRoutingLevel])}] }
      }
      foreach mt [$mm getMTerms] {
        foreach mp [$mt getMPins] {
          foreach g [$mp getGeometry] {
            set tl [$g getTechLayer]
            if {$tl ne "NULL" && [$tl getType] eq "ROUTING"} { set obs_top [expr {max($obs_top, [$tl getRoutingLevel])}] }
          }
        }
      }
    }
    lappend ms "[ot_fpl_q $mn]: \{\"n\": $n, \"w\": [expr {[$mm getWidth] / $dbu}], \"h\": [expr {[$mm getHeight] / $dbu}],\
 \"type\": [ot_fpl_q [$mm getType]], \"block\": [expr {[$mm isBlock] ? "true" : "false"}], \"top_layer\": $obs_top\}"
  }
  puts $f "\"masters\": \{[join $ms ,\n]\},"
  set nets_seen [dict create]
  foreach inst $mrefs {
    set h [$inst getHalo]
    set halo "null"
    if {$h ne "NULL"} { set halo [ot_fpl_rect $h $dbu] }
    set pins {}
    foreach it [$inst getITerms] {
      set n [$it getNet]
      if {$n eq "NULL"} { continue }
      set st [$n getSigType]
      if {$st ne "SIGNAL" && $st ne "CLOCK"} { continue }
      set xy [$it getAvgXY]
      if {[llength $xy] == 3 && [lindex $xy 0]} {
        set px [expr {[lindex $xy 1] / $dbu}]; set py [expr {[lindex $xy 2] / $dbu}]
      } else {
        set bb [$inst getBBox]
        set px [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]
      }
      set nn [$n getName]
      set io [$it getIoType]
      set cap "null"
      if {$io eq "OUTPUT"} {
        # macro output capture: the sole std-cell sink (a pin flop) and where it sits now
        set sinks {}
        foreach s [$n getITerms] {
          if {$s ne $it && [$s getIoType] eq "INPUT"} { lappend sinks $s }
        }
        if {[llength $sinks] == 1} {
          set si [[lindex $sinks 0] getInst]
          set sm [$si getMaster]
          if {![$sm isBlock]} {
            set ps [$si getPlacementStatus]
            set loc [$si getLocation]
            set cap "\[[ot_fpl_q [$sm getName]],[ot_fpl_q $ps],[expr {[lindex $loc 0] / $dbu}],[expr {[lindex $loc 1] / $dbu}]\]"
          }
        }
      }
      lappend pins [format {[%s,%.3f,%.3f,%s,%s]} [ot_fpl_q $nn] $px $py [ot_fpl_q $io] $cap]
    }
    lappend macros "\{\"name\": [ot_fpl_q [$inst getName]], \"master\": [ot_fpl_q [[$inst getMaster] getName]],\
 \"bbox\": [ot_fpl_rect [$inst getBBox] $dbu], \"status\": [ot_fpl_q [$inst getPlacementStatus]], \"halo\": $halo, \"pins\": \[[join $pins ,]\]\}"
  }
  puts $f "\"macros\": \[[join $macros ,\n]\],"
  # block terminals (pins)
  set bs {}
  foreach bt [$block getBTerms] {
    set n [$bt getNet]
    set st [$bt getSigType]
    set nn [expr {$n eq "NULL" ? "" : [$n getName]}]
    set boxes {}
    foreach bp [$bt getBPins] {
      foreach b [$bp getBoxes] {
        set tl [$b getTechLayer]
        lappend boxes "\[[ot_fpl_q [expr {$tl eq "NULL" ? "" : [$tl getName]}]],[ot_fpl_rect $b $dbu]\]"
      }
    }
    lappend bs "\[[ot_fpl_q [$bt getName]],[ot_fpl_q $nn],[ot_fpl_q $st],[ot_fpl_q [$bt getIoType]],\[[join $boxes ,]\]\]"
  }
  puts $f "\"bterms\": \[[join $bs ,\n]\],"
  # PDN shapes inside the edge band (pin clearance) -- wires and vias of POWER/GROUND special nets
  set ss {}
  foreach n [$block getNets] {
    if {![$n isSpecial]} { continue }
    set st [$n getSigType]
    if {$st ne "POWER" && $st ne "GROUND"} { continue }
    foreach sw [$n getSWires] {
      foreach b [$sw getWires] {
        if {[$b xMin] > $dx0 && [$b xMax] < $dx1 && [$b yMin] > $dy0 && [$b yMax] < $dy1} { continue }
        if {[$b isVia]} {
          set v [$b getTechVia]
          if {$v eq "NULL"} { set v [$b getBlockVia] }
          if {$v eq "NULL"} { continue }
          set lo [[$v getBottomLayer] getName]; set hi [[$v getTopLayer] getName]
          lappend ss "\[\"via\",[ot_fpl_q $lo],[ot_fpl_q $hi],[ot_fpl_rect $b $dbu]\]"
        } else {
          set tl [$b getTechLayer]
          if {$tl eq "NULL"} { continue }
          lappend ss "\[\"wire\",[ot_fpl_q [$tl getName]],\"\",[ot_fpl_rect $b $dbu]\]"
        }
      }
    }
  }
  puts $f "\"pdn_edge\": \[[join $ss ,\n]\],"
  set bl {}
  foreach b [$block getBlockages] {
    lappend bl "\{\"bbox\": [ot_fpl_rect [$b getBBox] $dbu], \"soft\": [expr {[$b isSoft] ? "true" : "false"}], \"max_density\": [$b getMaxDensity]\}"
  }
  puts $f "\"blockages\": \[[join $bl ,]\],"
  set rs {}
  foreach r [$block getRows] { lappend rs [ot_fpl_rect [$r getBBox] $dbu] }
  puts $f "\"rows\": \[[join $rs ,]\]\}"
  close $f
}

# flow entry: dump -> judge -> stop the flow on FAIL (inert unless OT_FP_LINT is set and non-zero)
proc ot_fp_lint_flow {} {
  if {![info exists ::env(OT_FP_LINT)] || $::env(OT_FP_LINT) in {"" 0 false}} { return }
  if {[info exists ::env(OT_FP_LINT_PY)]} { set py $::env(OT_FP_LINT_PY) } else { set py $::ot_fpl_dir/fp_margin_lint.py }
  set outdir $::env(REPORTS_DIR)
  set dump $outdir/fp_margin_lint_dump.json
  set rep $outdir/fp_margin_lint.json
  set t0 [clock seconds]
  if {[catch {ot_fp_lint_dump $dump} msg]} {
    puts "OT_FP_LINT: dump failed ($msg): lint skipped"
    return
  }
  set args [list python3 $py check $dump --out $rep]
  if {[info exists ::env(OT_FP_LINT_ARGS)]} { lappend args {*}$::env(OT_FP_LINT_ARGS) }
  set rc [catch {exec {*}$args 2>@1} res]
  puts $res
  puts "OT_FP_LINT: [expr {[clock seconds] - $t0}] s"
  # the loop's verdict file (docker shim mounts {CL}/fplint at /ot_fplint)
  if {[file isdirectory /ot_fplint]} { catch {file copy -force $rep /ot_fplint/fp_margin_lint.json} }
  if {$rc && [regexp {FLOORPLAN_MARGIN} $res]} {
    if {[file isdirectory /ot_fplint]} {
      set fh [open /ot_fplint/FAIL w]; puts $fh $res; close $fh
    }
    error "FLOORPLAN_MARGIN: floorplan margin lint failed before global placement (see $rep)"
  } elseif {$rc} {
    puts "OT_FP_LINT: checker error (not a verdict), flow continues: $res"
  }
}
