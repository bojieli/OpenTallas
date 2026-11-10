# DIE-HBM-97 KVPIPE rev3 (vE probe, DO_NOT_COUNT): capped TT STA on the guided GLOBAL placement (3_3_place_gp),
# same libs / RC / repair as sta_vd.tcl; per group worst slack with launch and endpoint x/y (um); per copy wire estimate
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach lf {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/$lf }
read_liberty /work/macros/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
set R /work/run/results/asap7/hbc_ot_hbm_sm_kv_line/base
set db [lindex [lsort [glob -nocomplain $R/3_3_place_gp.odb $R/3_place.odb]] 0]
puts "DB $db"
read_db $db
read_sdc $R/2_floorplan.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
puts "BEFORE_REPAIR WNS [format %.1f [expr [sta::worst_slack -max]*1e12]]"
set_max_fanout 64 [current_design]
set_max_transition 300 [current_design]
repair_design -slew_margin 35 -cap_margin 35
estimate_parasitics -placement
puts "AFTER_REPAIR WNS [format %.1f [expr [sta::worst_slack -max]*1e12]] TNS [format %.1f [expr [sta::total_negative_slack -max]*1e12]]"
set blk [ord::get_db_block]
set U [expr double([$blk getDefUnits])]
proc xy {pin} {
  global blk U
  set n [get_full_name $pin]; set k [string last "/" $n]
  if {$k < 0} { return "PORT" }
  set nm [string range $n 0 [expr $k-1]]
  set in [$blk findInst $nm]
  if {$in eq "NULL"} { set in [$blk findInst [string map {"\\" ""} $nm]] }
  if {$in eq "NULL"} { return "?" }
  set l [$in getLocation]
  return "[format %.1f [expr [lindex $l 0]/$U]],[format %.1f [expr [lindex $l 1]/$U]]"
}
# per endpoint group: worst path, launch pin + x,y, endpoint + x,y
foreach g {wleft wr full act fill_r h128_r wf4_r in_v_r bb g_bank sc rf g_fifo fault s_ready} {
  set tc [get_cells -quiet -hier u_fcore.*${g}*]
  if {[llength $tc] == 0} { set tc [get_cells -quiet u_fcore.${g}*] }
  if {[llength $tc] == 0} { puts "GROUP $g none"; continue }
  set pe [lindex [find_timing_paths -to $tc -path_delay max -group_path_count 1] 0]
  if {$pe eq ""} { puts "GROUP $g nopath"; continue }
  set ps [[$pe path] pins]
  set e [lindex $ps 0]; set s [lindex $ps end]
  puts "GROUP $g slack [format %.1f [expr [$pe slack]*1e12]] launch [get_full_name $s] @ [xy $s] end [get_full_name $e] @ [xy $e] pins [llength $ps]"
}
# per copy: launch from the copy flops, worst slack + flop xy + HPWL of their Q nets
foreach r {h128_r wf4_r in_v_r fill_r} {
  foreach c {0 1 2 3} {
    set fc [get_cells -quiet "u_fcore.g_col\\\[$c\\\].${r}*"]
    if {[llength $fc] == 0} { set fc [get_cells -quiet "u_fcore.g_col\[$c\].${r}*"] }
    if {[llength $fc] == 0} { puts "COPY $r $c none"; continue }
    set pe [lindex [find_timing_paths -from $fc -path_delay max -group_path_count 1] 0]
    set hp 0.0; set loc ""
    foreach cl $fc {
      set in [$blk findInst [get_full_name $cl]]
      if {$in eq "NULL"} { set in [$blk findInst [string map {"\\" ""} [get_full_name $cl]]] }
      if {$in eq "NULL"} continue
      set l [$in getLocation]; append loc " [format %.0f [expr [lindex $l 0]/$U]],[format %.0f [expr [lindex $l 1]/$U]]"
      foreach it [$in getITerms] {
        if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {
          set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
          foreach t [[$it getNet] getITerms] {
            set ll [[$t getInst] getLocation]
            set px [lindex $ll 0]; set py [lindex $ll 1]
            if {$px < $x0} {set x0 $px}; if {$px > $x1} {set x1 $px}; if {$py < $y0} {set y0 $py}; if {$py > $y1} {set y1 $py}
          }
          if {$x1 >= $x0} { set hp [expr $hp + ($x1-$x0+$y1-$y0)/$U] }
        }
      }
    }
    set sl [expr {$pe eq "" ? "nopath" : [format %.1f [expr [$pe slack]*1e12]]}]
    set en [expr {$pe eq "" ? "-" : "[get_full_name [lindex [[$pe path] pins] 0]] @ [xy [lindex [[$pe path] pins] 0]]"}]
    puts "COPY $r c$c n [llength $fc] slack $sl qnet_hpwl_um [format %.0f $hp] flops_at$loc worst_end $en"
  }
}
