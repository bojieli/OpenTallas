# DIE-QC-12 step D: insert the planned A0 trunk (ICG + CKINVDCx16 DME) on the cluster-CTS db; legalise; write db
source /w/common.tcl
read_db $::env(ODB)
source $::env(TTCL)
set blk [ord::get_db_block]; set db [ord::get_db]
set ck [$blk findNet ck]
proc gnet {n} { set b [ord::get_db_block]; set x [$b findNet $n]; if {$x eq "NULL"} { set x [odb::dbNet_create $b $n]; $x setSigType CLOCK }; return $x }
proc mk {name cell x y} { set b [ord::get_db_block]; set i [odb::dbInst_create $b [[ord::get_db] findMaster $cell] $name]
  $i setLocation [expr {int($x*1000)}] [expr {int($y*1000)}]; $i setPlacementStatus PLACED; return $i }
# sinks off ck
foreach s $TS { lassign $s kind name net
  if {$kind eq "cluster"} { set it [[$blk findInst ${name}_root] findITerm A] } else { set it [[$blk findInst $name] findITerm clk] }
  $it disconnect; $it connect [gnet $net] }
# ICG (trial: ENA tied 1, SE tied 0)
set g [mk a0t_icg ICGx8DC_ASAP7_75t_R {*}$ICG]
[$g findITerm CLK] connect $ck; [$g findITerm GCLK] connect [gnet a0t_gclk]
set th [mk a0t_tiehi TIEHIx1_ASAP7_75t_R [lindex $ICG 0] [expr {[lindex $ICG 1]+2}]]; set tl [mk a0t_tielo TIELOx1_ASAP7_75t_R [lindex $ICG 0] [expr {[lindex $ICG 1]-2}]]
set nh [odb::dbNet_create $blk a0t_ena]; set nl [odb::dbNet_create $blk a0t_se]
[$th findITerm H] connect $nh; [$g findITerm ENA] connect $nh; [$tl findITerm L] connect $nl; [$g findITerm SE] connect $nl
foreach t $TI { lassign $t name cell x y in out
  set i [mk $name $cell $x $y]; [$i findITerm A] connect [gnet $in]; [$i findITerm Y] connect [gnet $out] }
puts "ck iterms [llength [$ck getITerms]]"
detailed_placement
check_placement
write_db $::env(OUT)
