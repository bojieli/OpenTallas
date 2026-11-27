# KW-FIX-25/AUTORENDER 11-06: read one stage ODB (read only, no write_db), dump what layout_smells.py needs, compute smells.json,
# and save PNGs marked with the worst offenders.  Run by layout_render_hook.sh: openroad -gui (offscreen Qt), timeout-bounded.
# env: OT_LR_ODB, OT_LR_OUT, OT_LR_LABEL (place|grt|route), OT_LR_TOOLS, OT_LR_MAX_INST (default 400000: above it sampled connectivity
# (OT_LR_SAMPLE_ROOTS plain nets, default 100000; repeater trees, ports, macros, clocks complete), low resolution), OT_LR_KEEP_DUMP=1 keeps dump.tsv.
# CTS and custom labels get placement views. OT_LR_RUDY=1 requests the diagnostic fallback on a routed checkpoint.
# Everything inside one catch: under -gui an uncaught Tcl error would leave OpenROAD in its event loop until the timeout.
set lr_top_rc [catch {
proc lr_env {n d} { return [expr {[info exists ::env($n)] ? $::env($n) : $d}] }
proc lr_note {m} { puts "OT_LR $m" }
set lr_out $::env(OT_LR_OUT); set lr_label $::env(OT_LR_LABEL)
read_db $::env(OT_LR_ODB)
set lr_b [ord::get_db_block]
set lr_dbu [expr {double([$lr_b getDbUnitsPerMicron])}]
proc lr_um {v} { return [format %.3f [expr {$v / $::lr_dbu}]] }
proc lr_box {b} { return "[lr_um [$b xMin]]\t[lr_um [$b yMin]]\t[lr_um [$b xMax]]\t[lr_um [$b yMax]]" }
set lr_ninst [llength [$lr_b getInsts]]
set lr_max [lr_env OT_LR_MAX_INST 400000]
set lr_big [expr {$lr_ninst > $lr_max}]

proc lr_dump {path} {
  global lr_b lr_label lr_ninst lr_big
  set f [open $path w]
  fconfigure $f -buffering full -buffersize 1048576
  puts $f "H\t$lr_label\t$lr_ninst\t$lr_big\t[$lr_b getName]"
  puts $f "D\t[lr_box [$lr_b getDieArea]]"
  puts $f "C\t[lr_box [$lr_b getCoreArea]]"
  set tech [[ord::get_db] getTech]
  foreach l [$tech getLayers] {
    if {[$l getType] ne "ROUTING"} { continue }
    puts $f "L\t[$l getName]\t[$l getRoutingLevel]\t[$l getDirection]\t[lr_um [$l getPitch]]"
  }
  foreach bk [$lr_b getBlockages] {
    catch { if {![$bk isSoft]} { puts $f "B\t[lr_box [$bk getBBox]]" } }
  }
  foreach i [$lr_b getInsts] {
    set m [$i getMaster]; set mn [$m getName]
    if {![info exists ::lr_mtop($m)]} {
      set t 0
      if {[$m isBlock]} {
        foreach o [$m getObstructions] { set ly [$o getTechLayer]; if {$ly ne "NULL" && [$ly getType] eq "ROUTING" && [$ly getRoutingLevel] > $t} { set t [$ly getRoutingLevel] } }
      }
      set ::lr_mtop($m) [list [$m isBlock] $t]
    }
    lassign $::lr_mtop($m) isb top
    # I id name master isblock obstruction_top_level x0 y0 x1 y1
    puts $f "I\t[$i getId]\t[$i getName]\t$mn\t$isb\t$top\t[lr_box [$i getBBox]]"
  }
  foreach bt [$lr_b getBTerms] {
    set n [$bt getNet]
    set st [$bt getSigType]
    if {$st eq "POWER" || $st eq "GROUND"} { continue }
    set ly ""
    foreach bp [$bt getBPins] { foreach box [$bp getBoxes] { set l0 [$box getTechLayer]; if {$l0 ne "NULL"} { set ly [$l0 getName] }; break }; if {$ly ne ""} { break } }
    puts $f "P\t[$bt getName]\t[$n getName]\t$st\t[$bt getIoType]\t$ly\t[lr_box [$bt getBBox]]"
  }
  # big DB (COORD 11-25: smells were 'not computable' on most KV/QC types): sampled connectivity instead of none.  Kept complete:
  # nets with a port, a macro pin or a clock pin, and every net driven by or feeding a repeater (buf/inv/hold buffer), so each kept
  # root's buffer tree is whole; other nets (non-repeater driver and loads) are kept 1 in k, k = ceil(those / OT_LR_SAMPLE_ROOTS).
  # Header S line: S <k> <kept> <total> (layout_smells marks every connectivity check 'sampled').
  set lr_k 1
  if {$lr_big} {
    set lr_rootn 0
    foreach n [$lr_b getNets] { if {![lr_keep_full $n]} { incr lr_rootn } }
    set lr_k [expr {max(1, int(ceil(double($lr_rootn) / [lr_env OT_LR_SAMPLE_ROOTS 100000])))}]
    lr_note "big DB ($lr_ninst insts): sampled connectivity, 1 in $lr_k of $lr_rootn plain nets, repeater trees/ports/macros/clocks complete"
  }
  set lr_seen 0; set lr_kept 0; set lr_total 0
  foreach n [$lr_b getNets] {
    set st [$n getSigType]
    if {$st eq "POWER" || $st eq "GROUND"} { continue }
    incr lr_total
    if {$lr_k > 1 && ![lr_keep_full $n]} { incr lr_seen; if {$lr_seen % $lr_k} { continue } }
    incr lr_kept
    set ts {}
    foreach it [$n getITerms] {
      set mt [$it getMTerm]
      if {![info exists ::lr_mt($mt)]} { set ::lr_mt($mt) [list [$mt getName] [$mt getIoType] [$mt getSigType]] }
      lassign $::lr_mt($mt) mn io sg
      set inst [$it getInst]
      set xy ""
      if {[[$inst getMaster] isBlock]} { set bb [$it getBBox]; set xy "[lr_um [$bb xCenter]],[lr_um [$bb yCenter]]" }
      lappend ts "[$inst getId]:$mn:$io:$sg:$xy"
    }
    # N name sigtype terms (id:mterm:io:sig:xy, macro pins with their own xy)
    puts $f "N\t[$n getName]\t$st\t[join $ts { }]"
    foreach g [$n getGuides] {
      set ly [$g getLayer]
      puts $f "G\t[$n getName]\t[$ly getRoutingLevel]\t[lr_box [$g getBox]]"
    }
  }
  if {$lr_big} { puts $f "S\t$lr_k\t$lr_kept\t$lr_total" }
  close $f
}

# a net kept whole when connectivity is sampled: power excluded by the caller; ports, macro pins, clock pins, repeaters
proc lr_keep_full {n} {
  set st [$n getSigType]
  if {$st eq "POWER" || $st eq "GROUND"} { return 1 }
  if {$st eq "CLOCK" || [llength [$n getBTerms]]} { return 1 }
  foreach it [$n getITerms] {
    set inst [$it getInst]; set m [$inst getMaster]
    if {![info exists ::lr_rep($m)]} { set ::lr_rep($m) [list [$m isBlock] [regexp -nocase {^(BUF|INV|HB[0-9]|CKINV|CKBUF|DLY)} [$m getName]]] }
    lassign $::lr_rep($m) isb rep
    if {$isb || $rep} { return 1 }
    if {[regexp {^(CLK|CK|GCLK|clk)$} [[$it getMTerm] getName]]} { return 1 }
  }
  return 0
}

# Heatmap CSVs are also the base of the GRT congestion summary in smells.json
set lr_dump_path $lr_out/dump.tsv
set lr_cong $lr_out/congestion.csv
if {[catch {lr_dump $lr_dump_path} e]} { lr_note "dump failed: $e" }
# Routing reads the retained GCell grid. RUDY can initialize the router, so
# reserve it for an explicit diagnostic on a recognized routed checkpoint.
set lr_cong_src none; set lr_cong_ctl ""
proc lr_csv_rows {p} { if {[catch {set f [open $p]}]} { return 0 }; set n 0; while {$n < 3 && [gets $f l] >= 0} { incr n }; close $f; return $n }
set lr_odb_name [file tail $::env(OT_LR_ODB)]
set lr_routed_view [expr {
  ($lr_label eq "grt" && $lr_odb_name in {5_1_grt.odb 5_1_grt-failed.odb})
  || ($lr_label eq "route" && $lr_odb_name eq "5_2_route.odb")
}]
if {$lr_routed_view} {
  set lr_has_grid 0
  catch {
    set lr_grid [$lr_b getGCellGrid]
    set lr_has_grid [expr {$lr_grid ne "NULL" && [$lr_grid getNumGridPatternsX] > 0 && [$lr_grid getNumGridPatternsY] > 0}]
  }
  catch {file delete $lr_cong}
  if {$lr_has_grid} {
    if {[catch {gui::dump_heatmap Routing $lr_cong} e]} { lr_note "Routing heat map dump: $e" }
    if {[lr_csv_rows $lr_cong] >= 2} {
      set lr_cong_src routing; set lr_cong_ctl "Heat Maps/Routing Congestion"
      catch {gui::set_heatmap Routing ShowLegend 1}
    }
  }
  if {$lr_cong_src eq "none" && [lr_env OT_LR_RUDY 0] eq "1"} {
    if {[catch {gui::dump_heatmap RUDY $lr_cong} e]} { lr_note "RUDY heat map dump: $e" }
    if {[lr_csv_rows $lr_cong] >= 2} {
      set lr_cong_src rudy; set lr_cong_ctl "Heat Maps/Estimated Congestion (RUDY)"
      catch {gui::set_heatmap RUDY ShowLegend 1}
    }
  }
}
set lr_smell_rc [catch {
  exec timeout -k 5 [lr_env OT_LR_SMELL_TIMEOUT 150] python3 -I $::env(OT_LR_TOOLS)/layout_smells.py $lr_dump_path --congestion $lr_cong --congestion-source $lr_cong_src --odb $::env(OT_LR_ODB) --out $lr_out/smells.json --marks $lr_out/marks.tsv --one $lr_out/smells.one 2>@1
} e]
lr_note "smells rc $lr_smell_rc: $e"
if {![lr_env OT_LR_KEEP_DUMP 0]} { catch {file delete $lr_dump_path} }
catch {file delete $lr_cong}

# ---- PNGs
proc lr_marks {} {
  # offender marks: name x y text color (written by layout_smells.py, at most a few dozen)
  if {[catch {set f [open $::lr_out/marks.tsv]}]} { return }
  while {[gets $f ln] >= 0} {
    lassign [split $ln "\t"] x y txt col
    catch {gui::add_label $x $y $txt center $col 12}
  }
  close $f
}
proc lr_pins {} {
  set c 0
  foreach bt [$::lr_b getBTerms] {
    set st [$bt getSigType]
    if {$st eq "POWER" || $st eq "GROUND"} { continue }
    set bb [$bt getBBox]
    set col [expr {$st eq "CLOCK" ? "red" : "yellow"}]
    catch {gui::add_label [expr {[$bb xCenter] / $::lr_dbu}] [expr {[$bb yCenter] / $::lr_dbu}] . center $col 12}
    if {[incr c] > 20000} { break }
  }
}
set lr_die [$lr_b getDieArea]
set lr_wum [expr {[$lr_die dx] / $lr_dbu}]; set lr_hum [expr {[$lr_die dy] / $lr_dbu}]
set lr_mx [expr {0.03 * max($lr_wum, $lr_hum)}]
set lr_x0 [expr {[$lr_die xMin] / $lr_dbu - $lr_mx}]; set lr_y0 [expr {[$lr_die yMin] / $lr_dbu - $lr_mx}]
set lr_x1 [expr {[$lr_die xMax] / $lr_dbu + $lr_mx}]; set lr_y1 [expr {[$lr_die yMax] / $lr_dbu + $lr_mx}]
set lr_px [expr {$lr_big ? 800 : 1600}]
set lr_res [expr {max($lr_x1 - $lr_x0, $lr_y1 - $lr_y0) / $lr_px}]
proc lr_save {name args} {
  # one display set per image; a failed image only logs
  gui::set_display_controls "Heat Maps/*" visible false
  foreach {k v} $args { gui::set_display_controls $k visible $v }
  if {[catch {save_image -area [list $::lr_x0 $::lr_y0 $::lr_x1 $::lr_y1] -resolution $::lr_res $::lr_out/$name} e]} { lr_note "$name: $e" }
}
catch {gui::set_heatmap Placement ShowLegend 1}
catch {gui::set_display_controls "Misc/Scale bar" visible true}
catch {lr_pins}
catch {lr_marks}
set lr_rc [catch {
  switch -- $lr_label {
    grt {
      if {$lr_cong_ctl ne ""} { lr_save congestion.png "Nets/*" false "Instances/StdCells/*" false "Shape Types/Routing/*" false $lr_cong_ctl true }
      lr_save density.png "Nets/*" false "Instances/StdCells/*" true "Heat Maps/Placement Density" true
    }
    route {
      if {$lr_cong_ctl ne ""} { lr_save congestion.png "Nets/*" false "Instances/StdCells/*" false "Shape Types/Routing/*" false $lr_cong_ctl true }
      lr_save wires.png "Nets/*" true "Nets/Power" false "Nets/Ground" false "Instances/StdCells/*" false "Shape Types/Routing/*" true
    }
    default {
      lr_save density.png "Nets/*" false "Shape Types/Routing/*" false "Heat Maps/Placement Density" true
      lr_save layout.png "Nets/*" false "Instances/*" true
    }
  }
} e]
lr_note "render rc $lr_rc: $e"
} lr_top_e]
if {$lr_top_rc} { puts "OT_LR script stopped: $lr_top_e" }
exit 0
