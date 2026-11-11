# DIE-HBM-97 KVPIPE rev3 (vE probe, DO_NOT_COUNT): capped TT STA on the guided detail placement (3_place),
# same libs / RC / repair as sta_vd.tcl; per group worst slack with launch and endpoint x/y (um); per copy wire estimate
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach lf {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/$lf }
read_liberty /work/macros/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
set R /work/run/results/asap7/hbc_ot_hbm_sm_kv_line/base
set db $R/3_place.odb
puts "DB $db"
read_db $db
read_sdc $R/2_floorplan.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
proc fin {x} { if {![string is double -strict $x]} { return "NA($x)" }; if {abs($x) < 1e-6} { return [format %.1f [expr $x*1e12]] }; return [format %.1f $x] }
# sta::worst_slack / total_negative_slack return ps (user units); path slack returns seconds
puts "BEFORE_REPAIR WNS [fin [sta::worst_slack -max]]"
set_max_fanout 64 [current_design]
set_max_transition 300 [current_design]
repair_design -slew_margin 35 -cap_margin 35
estimate_parasitics -placement
puts "AFTER_REPAIR WNS [fin [sta::worst_slack -max]] TNS [fin [sta::total_negative_slack -max]]"
report_checks -path_delay max -group_path_count 1 -format full -digits 1 > /work/sta_ve_worst.txt
set blk [ord::get_db_block]
set U [expr double([$blk getDefUnits])]
# instance name -> location/sequential, names normalised (no backslashes) on both sides
array set LOC {}; array set SEQ {}
foreach in [$blk getInsts] {
  set nm [string map {"\\" ""} [$in getName]]
  set l [$in getLocation]
  set LOC($nm) "[format %.1f [expr [lindex $l 0]/$U]],[format %.1f [expr [lindex $l 1]/$U]]"
  set SEQ($nm) [[$in getMaster] isSequential]
  set DBI($nm) $in
}
set nc 0; set ncs 0
foreach nm [array names LOC] { lassign [split $LOC($nm) ,] px py; if {$px < 12.0 && $py < 12.0} { incr nc; if {$SEQ($nm)} { incr ncs } } }
puts "CORNER cells within 12 um of the core origin: $nc (sequential $ncs)"
proc iname {pin} { set n [string map {"\\" ""} [get_full_name $pin]]; set k [string last "/" $n]; if {$k < 0} { return "" }; return [string range $n 0 [expr $k-1]] }
proc xy {pin} { global LOC; set i [iname $pin]; if {$i eq ""} { return "PORT" }; if {[info exists LOC($i)]} { return $LOC($i) }; return "?" }
# launch = first pin from the path start that sits on an instance (skips the clock source port)
proc launch {ps} { for {set k [expr [llength $ps]-1]} {$k >= 0} {incr k -1} { set p [lindex $ps $k]; if {[iname $p] ne ""} { return $p } }; return [lindex $ps end] }
# per endpoint group: worst DATA path (endpoints = D / data pins of the group's cells; async reset recovery excluded)
foreach g {wleft wr full act fill_r h128_r wf4_r in_v_r bb g_bank sc rf g_fifo fault s_ready} {
  set tp {}
  foreach c [get_cells -quiet -hier u_fcore.*${g}*] { foreach pn [get_pins -quiet -of_objects $c -filter "direction==input"] { set b [get_property $pn lib_pin_name]; if {$b ne "CLK" && $b ne "RESETN" && $b ne "SETN"} { lappend tp $pn } } }
  if {[llength $tp] == 0} { puts "GROUP $g none"; continue }
  set pe [lindex [find_timing_paths -to $tp -path_delay max -group_path_count 1] 0]
  if {$pe eq ""} { puts "GROUP $g nopath"; continue }
  set ps [[$pe path] pins]; set e [lindex $ps 0]; set s [launch $ps]
  puts "GROUP $g slack [fin [$pe slack]] launch [get_full_name $s] @ [xy $s] end [get_full_name $e] @ [xy $e] pins [llength $ps]"
}
# per copy: sequential cells only; worst data path launched by them; flop xy; HPWL of their Q nets
foreach r {h128_r wf4_r in_v_r fill_r} {
  foreach c {0 1 2 3} {
    set fl {}
    set pfx "u_fcore.g_col\[$c\].$r"
    foreach nm [array names SEQ] { if {$SEQ($nm) && [string first $pfx $nm] == 0} { lappend fl $nm } }
    if {[llength $fl] == 0} { puts "COPY $r c$c none"; continue }
    set hp 0.0; set loc ""; set qp {}
    foreach nm $fl {
      set in $DBI($nm); append loc " $LOC($nm)"
      foreach it [$in getITerms] {
        if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {
          set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
          foreach t [[$it getNet] getITerms] { set ll [[$t getInst] getLocation]; set px [lindex $ll 0]; set py [lindex $ll 1]
            if {$px < $x0} {set x0 $px}; if {$px > $x1} {set x1 $px}; if {$py < $y0} {set y0 $py}; if {$py > $y1} {set y1 $py} }
          if {$x1 >= $x0} { set hp [expr $hp + ($x1-$x0+$y1-$y0)/$U] }
        }
      }
      foreach q [get_pins -quiet "[string map {[ \\[ ] \\]} $nm]/Q*"] { lappend qp $q }
    }
    set sl "nopath"; set en "-"
    if {[llength $qp]} { set pe [lindex [find_timing_paths -from $qp -path_delay max -group_path_count 1] 0]
      if {$pe ne ""} { set sl [fin [$pe slack]]; set e [lindex [[$pe path] pins] 0]; set en "[get_full_name $e] @ [xy $e]" } }
    puts "COPY $r c$c n [llength $fl] qpins [llength $qp] slack $sl qnet_hpwl_um [format %.0f $hp] flops_at$loc worst_end $en"
  }
}
