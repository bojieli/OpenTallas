# East W v2: output-only -5.81ps plus p_w[1086] valid-capture -1.20ps.
# Boundary delay hardware, no timing exceptions: shared output and input stages,
# plus one additional local HB4 on each of the four write-valid inputs.
set ::env(OT_IOHOLD_IN) 1
source /src/physical/dsrom_window_source/leaf_iohold.tcl
set b [ord::get_db_block]
set m [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
if {$m eq "NULL"} {error "EAST_W_HOLD: HB4 master missing"}
set firm {}
foreach bit {0 543 1086 1629} {
 set bt [$b findBTerm [format {p_w[%d]} $bit]]
 if {$bt eq "NULL"} {error "EAST_W_HOLD: input bit $bit missing"}
 set old [$bt getNet];set loads [$old getITerms]
 if {[llength $loads]!=1} {error "EAST_W_HOLD: bit $bit has nonsingle local hold load"}
 set dst [lindex $loads 0]
 set n [odb::dbNet_create $b [format "ot_wv_extra_n%d" $bit]]
 set i [odb::dbInst_create $b $m [format "ot_wv_extra_%d" $bit]]
 # Temporarily release only the original local hold input while splicing;
 # restore both protections before any placement/repair step.
 set di [$dst getInst];set idt [$di isDoNotTouch];set ndt [$old isDoNotTouch]
 $di setDoNotTouch 0;$old setDoNotTouch 0
 $dst disconnect;[$i findITerm A] connect $old;[$i findITerm Y] connect $n;$dst connect $n
 $di setDoNotTouch $idt;$old setDoNotTouch $ndt
 set x 0;set y 0
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {set x [expr {([$box xMin]+[$box xMax])/2}];set y [expr {([$box yMin]+[$box yMax])/2}];break};break}
 set ca [$b getCoreArea]
 set x [expr {max([$ca xMin],min($x,[$ca xMax]-[$m getWidth]))}]
 set y [expr {max([$ca yMin],min($y,[$ca yMax]-[$m getHeight]))}]
 $i setOrient R0;$i setLocation $x $y;$i setPlacementStatus FIRM
 set_dont_touch [get_cells [$i getName]];$n setDoNotTouch 1
 lappend firm [$i getName]
}
set fh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a];puts $fh [join $firm "\n"];close $fh
puts "EAST_W_HOLD: 4 additional valid-input HB4 stages; shared input/output stages retained"
