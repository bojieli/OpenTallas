# DIE-QC-12 step B: glue-register leaf clusters -> each cluster net driven by a CKINVDCx16 root at the planned site, TritonCTS local trees
source /w/common.tcl
read_db $::env(ODB)
read_sdc /p/constraint.sdc
source /p/setRC_rcx.tcl
source $::env(CLTCL)
set blk [ord::get_db_block]; set db [ord::get_db]
set inv [$db findMaster CKINVDCx16_ASAP7_75t_R]
set ck [$blk findNet ck]
set nets {}
foreach cdef $CL {
  lassign $cdef name x y regs
  set n [odb::dbNet_create $blk $name]; $n setSigType CLOCK
  set i [odb::dbInst_create $blk $inv ${name}_root]
  $i setLocation [expr {int($x*1000)}] [expr {int($y*1000)}]; $i setPlacementStatus PLACED
  [$i findITerm A] connect $ck; [$i findITerm Y] connect $n
  foreach r $regs { set ri [$blk findInst $r]; set it [$ri findITerm CLK]; $it disconnect; $it connect $n }
  lappend nets $name
}
detailed_placement
set_dont_use {*x1_ASAP7* *xp33* *xp67* }
clock_tree_synthesis -clk_nets $nets -sink_clustering_enable -repair_clock_nets
estimate_parasitics -placement
detailed_placement
check_placement
write_db $::env(OUT)
