# list-driven insertion (in-flow form): /work/hpad_list.txt = odb instance names of the flops to pad (written by the
# dry run of hold_pad_struct.tcl on the same synthesized netlist, TT single scene, ideal clocks).  Fail closed when any
# listed flop or its D net is missing, so a changed netlist cannot pass silently.
proc ot_hpad_insert_list {fn} {
  set blk [ord::get_db_block]
  set m [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
  if {$m eq "NULL" || $m eq ""} { error "OT_HPAD no HB4xp67_ASAP7_75t_R master" }
  set fh [open $fn]; set names [split [string trim [read $fh]] "\n"]; close $fh
  set n 0; set miss 0
  foreach nm $names {
    set ii [$blk findInst $nm]
    if {$ii eq "NULL" || $ii eq ""} { incr miss; if {$miss <= 5} { puts "OT_HPAD_MISSING $nm" }; continue }
    set it [$ii findITerm D]; set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} { incr miss; continue }
    set b [odb::dbInst_create $blk $m "ot_hpad_$n"]
    set nn [odb::dbNet_create $blk "ot_hpad_n_$n"]
    $it disconnect; $it connect $nn
    [$b findITerm A] connect $net; [$b findITerm Y] connect $nn
    # pad OUTPUT net dont-touch only: an instance dont-touch blocks resizer buffering of the pad's INPUT net (vM2 try 1:
    # GPL timing-driven repair_design RSZ-3006 on e_rd__fc[251], load ot_hpad_5824/A dont_touch)
    $nn setDoNotTouch 1
    incr n
  }
  puts "OT_HPAD list [llength $names] padded $n missing $miss"
  if {$miss} { error "OT_HPAD $miss listed flops not found: netlist differs from the list" }
}
