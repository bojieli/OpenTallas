# stage_paths.tcl (VIS-REOWN 11-25, COORD: Fable reviewers saw "paths.png 0 DRAWN" on SMELL renders): worst-N setup AND hold paths of the
# DB being rendered, at any stage, for render_review.py to draw.  Sourced by render_review.sh after `read_db` + layout_dump.tcl, inside the
# pinned ORFS image, kit mounted read-only at /kit.  Never writes the DB.  Everything is caught: a failed STA leaves a note, the PNGs still render.
# env: SP_ODB  the ODB path as read (/kit/...)        SP_OUT  output dir (default /rev)        SP_NPATH paths per check (default 50)
#      SP_SDC  sdc override                           SP_LIBS extra liberty globs (space list)
# Writes: paths_stage_setup.txt, paths_stage_hold.txt (report_checks -format full), stage_paths.txt (mode, sdc, libs, wns lines) or
#         stage_paths_error.txt.
# Clocks: ideal before CTS (3_* DBs; set_propagated_clock is removed), propagated from 4_cts on.  Parasitics: -global_routing on GRT/route DBs
# when the DB carries guides, else -placement.  Libraries: the kit's own objects/.../lib/*.lib, the platform RVT TT NLDM libs and the kit
# config.mk ADDITIONAL_LIBS (/work/ mapped to the kit), as post_place_review.tcl does; hold uses the same TT libraries (labelled).
proc sp_note {m} { puts "SP $m"; flush stdout }
proc sp_stage_paths {} {
  set out [expr {[info exists ::env(SP_OUT)] ? $::env(SP_OUT) : "/rev"}]
  set n [expr {[info exists ::env(SP_NPATH)] ? $::env(SP_NPATH) : 50}]
  set odb $::env(SP_ODB)
  set base [file dirname $odb]
  set run [file normalize $base/../../../..]
  set gen [file normalize $run/..]
  set plat /OpenROAD-flow-scripts/flow/platforms/asap7
  set libs 0
  foreach f [concat [glob -nocomplain $run/objects/asap7/*/base/lib/*.lib] [glob -nocomplain $plat/lib/NLDM/*RVT_TT*]] { if {![catch {read_liberty $f}]} { incr libs } }
  if {[info exists ::env(SP_LIBS)]} { foreach p $::env(SP_LIBS) { foreach f [glob -nocomplain $p] { if {![catch {read_liberty $f}]} { incr libs } } } }
  if {[file exists $gen/config.mk]} {
    foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LIBS' $gen/config.mk || true"] "\n"] {
      foreach w [lrange [split $l " ="] 1 end] {
        set w [string map [list /work/ $gen/] $w]
        if {[string match *.lib $w] && [file exists $w] && ![catch {read_liberty $w}]} { incr libs }
      }
    }
  }
  set tail [file tail $odb]
  set post_cts [regexp {^[4-6]_} $tail]
  set sdc ""
  if {[info exists ::env(SP_SDC)] && $::env(SP_SDC) ne ""} { set sdc $::env(SP_SDC) } else {
    set nm [file rootname $tail]
    # never a later stage's sdc on an earlier DB (a pre-CTS DB must not read 4_cts.sdc)
    set later [expr {$post_cts ? [list $base/4_cts.sdc] : {}}]
    foreach c [concat [list $base/$nm.sdc] $later [list $base/3_place.sdc $base/2_floorplan.sdc $base/1_synth.sdc $gen/constraint.sdc]] { if {[file exists $c]} { set sdc $c; break } }
  }
  if {$sdc eq ""} { error "no sdc found next to $odb" }
  read_sdc $sdc
  if {$post_cts} { catch {set_propagated_clock [all_clocks]}; set clk propagated } else { catch {unset_propagated_clock [all_clocks]}; set clk ideal }
  source $plat/setRC.tcl
  set par placement
  if {[regexp {^[56]_} $tail]} { if {![catch {estimate_parasitics -global_routing}]} { set par global_routing } }
  if {$par eq "placement"} { estimate_parasitics -placement }
  report_checks -path_delay max -group_path_count $n -sort_by_slack -format full -digits 3 > $out/paths_stage_setup.txt
  report_checks -path_delay min -group_path_count $n -sort_by_slack -format full -digits 3 > $out/paths_stage_hold.txt
  set f [open $out/stage_paths.txt w]
  puts $f "odb $odb\nsdc $sdc\nlibs $libs\nclock $clk\nparasitics $par\nnpath $n\nhold_libs TT (same as setup)"
  close $f
  catch {report_wns -digits 3 >> $out/stage_paths.txt}
  catch {report_worst_slack -min -digits 3 >> $out/stage_paths.txt}
  sp_note "OK $clk $par libs $libs sdc $sdc"
}
if {[catch {sp_stage_paths} sp_err]} {
  sp_note "FAILED $sp_err"
  catch {set f [open [expr {[info exists ::env(SP_OUT)] ? $::env(SP_OUT) : "/rev"}]/stage_paths_error.txt w]; puts $f $sp_err; close $f}
}
