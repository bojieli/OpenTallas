# PATH-QC-RP1 F58 (2026-10-25): structural control-register replication BEFORE CTS (no post-route ECO).
# f57r4 FF hold -13.91 ps / 12 EP: u_c1 (W0 leaf, early) -> g_cbk[k].u for the W1-leaf consumers (mask 0xABBF).
# Fix: one replica u_c1w of the c1 control flop + its QN->Q decode inverter, SAME D net (pcr_addr[3]) and SAME
# clock (ck), placed at the W1 consumers' centroid, re-driving exactly the 12 W1-mask consumers. Launch and capture
# then sit in the receiving clock region (CTS clusters by location); +0 data cycles (same register stage).
# Kit RTL carries the identical replica (rtl/qfd_dv_s8_crh_rp1.sv u_c1w, kff ID 3401) so LEC is RTL-vs-netlist exact.
# Usage: IN=<3_place.odb> OUT=<odb> VOUT=<v> openroad -exit rp1_ctl_replica.tcl
read_db $::env(IN)
set blk [ord::get_db_block]
proc must {o what} { if {$o eq "NULL" || $o eq ""} { error "RP1_REP missing $what" }; return $o }
set ff0  [must [$blk findInst {u_c1/q$_DFF_P_}] u_c1_ff]
set inv0 [must [$blk findInst {u_c1/_1_}] u_c1_inv]
set mff  [$ff0 getMaster]; set minv [$inv0 getMaster]
set nd   [must [[$ff0 findITerm D] getNet] d_net]
set nck  [must [[$ff0 findITerm CLK] getNet] ck_net]
set nq0  [must [[$inv0 findITerm Y] getNet] c1_bank]
if {[$blk findInst {u_c1w/q$_DFF_P_}] ne "NULL"} { error "RP1_REP replica already present" }
set ff1  [odb::dbInst_create $blk $mff {u_c1w/q$_DFF_P_}]
set inv1 [odb::dbInst_create $blk $minv {u_c1w/_1_}]
set nqn1 [odb::dbNet_create $blk {u_c1w/_0_}]
set nq1  [odb::dbNet_create $blk {c1_bank_w}]
[$ff1 findITerm D] connect $nd
[$ff1 findITerm CLK] connect $nck
[$ff1 findITerm QN] connect $nqn1
[$inv1 findITerm A] connect $nqn1
[$inv1 findITerm Y] connect $nq1
foreach i [list $ff1 $inv1] { foreach p {VDD VSS} { [$i findITerm $p] connect [$blk findNet $p] } }
set mask 0xABBF; set moved 0; set sx 0.0; set sy 0.0
for {set k 0} {$k < 16} {incr k} {
  if {!(($mask >> $k) & 1)} continue
  set c [must [$blk findInst "g_cbk\\\[$k\\\].u/q\$_DFF_P_"] "g_cbk$k"]
  set it [$c findITerm D]
  if {[[$it getNet] getName] ne [$nq0 getName]} { error "RP1_REP g_cbk$k D not on c1_bank" }
  $it disconnect; $it connect $nq1; incr moved
  set sx [expr {$sx + [lindex [$c getLocation] 0]}]; set sy [expr {$sy + [lindex [$c getLocation] 1]}]
}
if {$moved != 12} { error "RP1_REP moved $moved != 12" }
set cx [expr {int($sx / $moved)}]; set cy [expr {int($sy / $moved)}]
$ff1 setLocation $cx $cy; $ff1 setPlacementStatus PLACED
$inv1 setLocation [expr {$cx + 1200}] $cy; $inv1 setPlacementStatus PLACED
puts "RP1_REP moved $moved W1-mask consumers to c1_bank_w; replica seed at ([expr {$cx/1000.0}],[expr {$cy/1000.0}]); c1_bank iterms now [llength [$nq0 getITerms]]"
detailed_placement
check_placement -verbose
foreach i [list $ff0 $inv0 $ff1 $inv1] { puts "RP1_REP_LOC [$i getName] [$i getLocation]" }
puts "RP1_REP nets: d=[$nd getName] ([llength [$nd getITerms]] iterms) ck=[$nck getName] q0=[$nq0 getName] ([llength [$nq0 getITerms]]) q1=c1_bank_w ([llength [$nq1 getITerms]])"
write_db $::env(OUT)
write_verilog $::env(VOUT)
