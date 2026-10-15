# Source-preserving VQ receiver stations: buffer beside the face before long fanout wires.
# No new register, clock, reset qualifier, FIFO or data edge. Standard BUFx4f identity cells.
set qc_blk [ord::get_db_block]
set qc_master [[ord::get_db] findMaster BUFx4f_ASAP7_75t_R]
if {$qc_master eq "NULL"} {error "COPY_VQ_STATION: BUFx4f missing"}
set qc_ca [$qc_blk getCoreArea]
set qc_n 0;set qc_firm {};set qc_maxseed 0
set qc_ports {}
foreach bt [$qc_blk getBTerms] {
 if {[$bt getIoType] eq "INPUT" && [regexp {^vq[0-3]\[[0-9]+\]$} [$bt getName]]} {lappend qc_ports [list [$bt getName] $bt]}
}
foreach pair [lsort -index 0 $qc_ports] {
 set bt [lindex $pair 1];set net [$bt getNet];set loads {}
 foreach it [$net getITerms] {if {[$it isInputSignal]} {lappend loads $it} else {error "COPY_VQ_STATION: input net has internal driver"}}
 if {![llength $loads]} {error "COPY_VQ_STATION: source VQ bit has no sink"}
 set cell [odb::dbInst_create $qc_blk $qc_master [format "ot_qcopy_vq_%04d" $qc_n]]
 set n2 [odb::dbNet_create $qc_blk [format "ot_qcopy_vq_n%04d" $qc_n]]
 foreach it $loads {$it disconnect; $it connect $n2}
 [$cell findITerm A] connect $net;[$cell findITerm Y] connect $n2
 set found 0
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {set px [expr {([$box xMin]+[$box xMax])/2}];set py [expr {([$box yMin]+[$box yMax])/2}];set found 1;break};if {$found} break}
 if {!$found} {error "COPY_VQ_STATION: no actual placed BPin"}
 # Eight rows stagger finite-width cells behind dense N/S face contacts.
 set depth [expr {($qc_n%8)*[$qc_master getHeight]}]
 set x [expr {max([$qc_ca xMin],min($px-[$qc_master getWidth]/2,[$qc_ca xMax]-[$qc_master getWidth]))}]
 if {abs($py-[$qc_ca yMin]) < abs($py-[$qc_ca yMax])} {
  set y [expr {[$qc_ca yMin]+$depth}]
 } else {set y [expr {[$qc_ca yMax]-[$qc_master getHeight]-$depth}]}
 $cell setOrient R0;$cell setLocation $x $y;$cell setPlacementStatus FIRM
 lappend qc_firm [$cell getName]
 $net setDoNotTouch 1
 incr qc_n
}
if {$qc_n!=2048} {error "COPY_VQ_STATION: expected2048 actual source VQ bits, saw$qc_n"}
set_dont_touch [get_cells ot_qcopy_vq_*]
# Reference recipe's PRE_DETAIL_PLACE release reads this exact name list.
if {[info exists ::env(RESULTS_DIR)]} {
 set f [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a];puts $f [join $qc_firm "\n"];close $f
}
puts "COPY_VQ_STATION: $qc_n actual BUFx4f cells seeded beside placed VQ BPin contacts; zero added data edges"
