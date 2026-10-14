# Retain recipe2 pin hold cells and all registered data pins.
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
# RAW ret root outliers are the two W-face reset synchronizers, ~100ps late.
# Put them beside their actual S-face return consumers, under the SRAM halo.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set moved {}
set j 0
foreach i [$b getInsts] {
    if {![string match {u_leaf.u.rst_ret_s*} [$i getName]]} { continue }
    # Recipe2 hold buffers inherit the flop's base name; move only real DFFs.
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((288.0+1.08*$j)*$dbu)}] [expr {round(20.52*$dbu)}]
    $i setPlacementStatus FIRM
    lappend moved [$i getName]
    puts "BGL_MC_RESET_CLUSTER [$i getName] at [expr {288.0+1.08*$j}] 20.52"
    incr j
}
if {$j != 2} { error "BGL_MC_RESET_CLUSTER expected2actualresetFFs found$j" }
# The standard PRE_DETAIL_PLACE release will legalize these with the pin flops.
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $moved { puts $fh $n }
close $fh

# H0 captures bank hits beside the row/valid ingress. Count actual mapped DFFs,
# including Yosys's hit wire alias; no combinational or hold-buffer aliases.
set hcount 0
set hnames {}
foreach i [$b getInsts] {
    set n [$i getName]
    if {![string match {u_leaf.u.h0*} $n] && ![string match {u_leaf.u.hit*} $n]} { continue }
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((12.0+0.72*$hcount)*$dbu)}] [expr {round(70.2*$dbu)}]
    $i setPlacementStatus FIRM
    lappend hnames $n
    incr hcount
}
if {$hcount != 28} { error "BGL_MC_H0 expected28actualhitFFs found$hcount" }
puts "BGL_MC_H0 placed $hcount input hit flops near N row/valid pins"
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $hnames {puts $fh $n}
close $fh

# Parallel pair-count FFs sit beside H0; both are captured from the SAME input edge.
set pcount 0; set pnames {}
foreach i [$b getInsts] {
    if {![string match {u_leaf.u.hpair_q*} [$i getName]]} { continue }
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((12.0+0.72*$pcount)*$dbu)}] [expr {round(68.04*$dbu)}]
    $i setPlacementStatus FIRM
    lappend pnames [$i getName]; incr pcount
}
if {$pcount != 28} {error "BGL_MC_PAIR expected28pair-countFFs found$pcount"}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $pnames {puts $fh $n}; close $fh
puts "BGL_MC_PAIR placed $pcount pair count flops beside H0"

# Output-only 14-port domains: compact reset conditioners beside their S consumers.
set out_rst_n 0
set out_rst_counts [dict create 0 0 1 0]
foreach i [$b getInsts] {
 if {![string match {u_leaf.g_output_reset*rst_out_b*} [$i getName]]} {continue}
 if {![string match DFF* [[$i getMaster] getName]]} {continue}
 # Exact reset clocks are subsequently validated from the actual mapped root census.
 if {![regexp {g_output_reset\[([01])\]} [$i getName] unused domain]} {error "MC5S missing actual reset domain [$i getName]"}
 set idx [dict get $out_rst_counts $domain];dict incr out_rst_counts $domain
 $i setLocation [expr {round((87.048+129.96*$domain+0.72*$idx)*$dbu)}] [expr {round(18.36*$dbu)}]
 $i setPlacementStatus FIRM
 set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a];puts $fh [$i getName];close $fh
 incr out_rst_n
}
if {$out_rst_n != 4} {error "MC5 expected4actual output reset FFs found$out_rst_n"}
# Actual output hold chains retain the original lead4f and one final24.
set final24 [[ord::get_db] findMaster BUFx12f_ASAP7_75t_R]
set nfinal 0;set nhb2 0;set nhb3 0
foreach i [$b getInsts] {
 if {![string match ot_ohdrv_*_2 [$i getName]]} {continue}
 set net [[$i findITerm Y] getNet]
 if {[llength [$net getBTerms]] != 1} {error "MC5 final not directly on one port"}
 set port [[lindex [$net getBTerms] 0] getName]
 set hnet [[$i findITerm A] getNet];set hi ""
 foreach t [$hnet getITerms] {if {[$t isOutputSignal]} {set hi [$t getInst]}}
 if {$hi eq "" || ![string match HB* [[$hi getMaster] getName]]} {error "MC5 missing real hold stage"}
 set hmaster HB3xp67_ASAP7_75t_R
 if {[string match o_* $port]} {set hmaster HB3xp67_ASAP7_75t_R;incr nhb3} else {incr nhb2}
 $hi setDoNotTouch 0
 if {![$hi swapMaster [[ord::get_db] findMaster $hmaster]]} {error "MC5 hold master swap failed"}
 $hi setDoNotTouch 1
 if {![$i swapMaster $final24]} {error "MC5 final24 swap failed"}
 $net setDoNotTouch 1
 incr nfinal
}
set_dont_touch [get_cells ot_ohdrv_*_2]
if {$nfinal != 5441 || $nhb2 != 4144 || $nhb3 != 1297} {error "MC5 actual hold census final$nfinal f$nhb2 o$nhb3"}
puts "MC5_OUTPUT_DOMAINS final12=$nfinal forwardHB2=$nhb2 returnHB3=$nhb3 resetFF=$out_rst_n"

# Deterministic pure-buffer delays on actual reset paths. No reset epoch/cycle changes.
proc mc5s_delay_reset {net tag x y select bf} {
 set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 set dest [odb::dbNet_create $b ${tag}_out]
 set moved 0
 foreach t [$net getITerms] {
  if {[$t isOutputSignal]} {continue}
  set name [[$t getInst] getName]
  if {$select && ![regexp {(rst_s|rst_req_s|rst_ret_s|rst_hist_b|rst_out_b)\[} $name]} {continue}
  $t disconnect;$t connect $dest;incr moved
 }
 if {!$moved} {error "MC5S no actual reset consumers for$tag"}
 set cur $net;set k 0
 foreach master [list BUFx4f_ASAP7_75t_R HB2xp67_ASAP7_75t_R $bf] {
  set m [[ord::get_db] findMaster $master]
  if {$m eq "NULL"} {error "MC5S missing reset delay master$master"}
  set nm ${tag}_${k}
  set inst [odb::dbInst_create $b $m $nm]
  [$inst findITerm A] connect $cur
  if {$k==2} {set out $dest} else {set out [odb::dbNet_create $b ${tag}_n${k}]}
  [$inst findITerm Y] connect $out
  $inst setOrient R0;$inst setLocation [expr {round(($x+0.72*$k)*$dbu)}] [expr {round($y*$dbu)}];$inst setPlacementStatus FIRM
  set fh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a];puts $fh $nm;close $fh
  if {$k==1} {set_dont_touch [get_cells $nm];$cur setDoNotTouch 1}
  set cur $out;incr k
 }
 puts "MC5S_RESET_DELAY $tag actual_consumer_pins=$moved HB2 protected; upstream ACK epoch remains raw"
 return $moved
}
set raw_net ""
foreach bt [$b getBTerms] {if {[regexp {^rs(\[0\])?$} [$bt getName]]} {set raw_net [$bt getNet]}}
if {$raw_net eq ""} {error "MC5S missing actual raw external reset net"}
set raw_n [mc5s_delay_reset $raw_net ot_mc5s_epoch_delay 2.16 43.2 1 BUFx12f_ASAP7_75t_R]
if {$raw_n!=12} {error "MC5S expected12 actual conditioner reset pins found$raw_n"}
set hist_n 0
foreach inst [$b getInsts] {
 if {![regexp {u_leaf\.u\.g_reset_hist_split\.rst_hist_b\[1\]} [$inst getName]]} {continue}
 set q [$inst findITerm QN]
 if {$q eq "NULL"} {error "MC5S final history conditioner missing actual QN"}
 incr hist_n [mc5s_delay_reset [$q getNet] ot_mc5s_history_delay 110.16 36.72 0 BUFx12f_ASAP7_75t_R]
}
if {$hist_n!=200} {error "MC5S expected200 real H1 history reset consumers found$hist_n"}
