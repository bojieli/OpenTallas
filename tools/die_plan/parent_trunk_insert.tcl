# parent_trunk_insert.tcl -- insert a parent_trunk_dme.py plan (ICG + inverter DME trunk) on a placed parent db,
# legalise, write the db.  OPT-IN shared step (DIE-QC-15 upstream of DIE-QC-14 ins_trunk.tcl); nothing calls it by default.
# env: ODB (in), OUT (out db), TTCL (parent_trunk_dme.py tcl output: ICG / TI / TS lists), optional
#      CLK_NET (ck)  ROOT_SUFFIX (_root) ROOT_PIN (A)  CHILD_PIN (clk)  PREFIX (a0t)  ICG_CELL (ICGx8DC_ASAP7_75t_R)
#      ICG_INST (opt-in, QC-A0-KITS-9): reuse the RTL ICG instance of that name (moved to the planned site; its CLK on
#      the planned net, its GCLK net becomes the gated trunk root net, ENA/SE keep the RTL enable) instead of creating
#      a new ICG with tie cells.  OT_PT_NO_IO (opt-in): skip read_db/write_db (the caller holds the db, e.g. a kit hook).
# Libraries/LEF must already be loaded by the caller (read_db carries tech + masters).
# Without ICG_INST the ICG enable is tied ENA=1 / SE=0 here (trial structure); the RTL enable step + gated bench + LEC
# are separate.  A plan made with --ungated-split (TTCL sets ROOT_NET / ICG_IN) has its ICG inside the tree: the root
# leg starts on CLK_NET itself and the ICG CLK sits on the planned net ICG_IN.
proc ptenv {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) } ; return $d }
set CLK_NET [ptenv CLK_NET ck]; set RS [ptenv ROOT_SUFFIX _root]; set RP [ptenv ROOT_PIN A]
set CP [ptenv CHILD_PIN clk]; set PRE [ptenv PREFIX a0t]; set ICGC [ptenv ICG_CELL ICGx8DC_ASAP7_75t_R]
set ICGI [ptenv ICG_INST ""]
if {[ptenv OT_PT_NO_IO 0] ne "1"} { read_db $::env(ODB) }
source $::env(TTCL)
set blk [ord::get_db_block]; set db [ord::get_db]
set ck [$blk findNet $CLK_NET]
if {$ck eq "NULL"} { error "parent_trunk_insert: clock net $CLK_NET not found" }
array unset ::pt_netmap
if {[info exists ROOT_NET]} { set ::pt_netmap($ROOT_NET) $ck }
set gi "NULL"
if {$ICGI ne ""} {
  set gi [$blk findInst $ICGI]
  if {$gi eq "NULL"} { error "parent_trunk_insert: ICG_INST $ICGI not found" }
  if {[[$gi getMaster] getName] ne $ICGC} { error "parent_trunk_insert: ICG_INST $ICGI is [[$gi getMaster] getName], not $ICGC" }
  set gn [[$gi findITerm GCLK] getNet]
  if {$gn eq "NULL"} { error "parent_trunk_insert: ICG_INST $ICGI GCLK unconnected" }
  set ::pt_netmap(${PRE}_gclk) $gn
}
proc gnet {n} { if {[info exists ::pt_netmap($n)]} { return $::pt_netmap($n) }
  set b [ord::get_db_block]; set x [$b findNet $n]; if {$x eq "NULL"} { set x [odb::dbNet_create $b $n]; $x setSigType CLOCK }; return $x }
proc mk {name cell x y} { set b [ord::get_db_block]; set m [[ord::get_db] findMaster $cell]
  if {$m eq "NULL"} { error "parent_trunk_insert: master $cell not found" }
  set i [odb::dbInst_create $b $m $name]
  $i setLocation [expr {int($x*1000)}] [expr {int($y*1000)}]; $i setPlacementStatus PLACED; return $i }
foreach s $TS { lassign $s kind name net
  if {$kind eq "cluster"} { set inst [$blk findInst ${name}${RS}]; set pn $RP } else { set inst [$blk findInst $name]; set pn $CP }
  if {$inst eq "NULL"} { error "parent_trunk_insert: sink $kind $name not found" }
  set it [$inst findITerm $pn]
  if {$it eq "NULL"} { error "parent_trunk_insert: sink $name has no pin $pn" }
  $it disconnect; $it connect [gnet $net] }
set icgin [expr {[info exists ICG_IN] ? [gnet $ICG_IN] : $ck}]
if {$gi ne "NULL"} {
  $gi setLocation [expr {int([lindex $ICG 0]*1000)}] [expr {int([lindex $ICG 1]*1000)}]; $gi setPlacementStatus PLACED
  set it [$gi findITerm CLK]; $it disconnect; $it connect $icgin
} else {
  set g [mk ${PRE}_icg $ICGC {*}$ICG]
  [$g findITerm CLK] connect $icgin; [$g findITerm GCLK] connect [gnet ${PRE}_gclk]
  set th [mk ${PRE}_tiehi TIEHIx1_ASAP7_75t_R [lindex $ICG 0] [expr {[lindex $ICG 1]+2}]]
  set tl [mk ${PRE}_tielo TIELOx1_ASAP7_75t_R [lindex $ICG 0] [expr {[lindex $ICG 1]-2}]]
  set nh [odb::dbNet_create $blk ${PRE}_ena]; set nl [odb::dbNet_create $blk ${PRE}_se]
  [$th findITerm H] connect $nh; [$g findITerm ENA] connect $nh; [$tl findITerm L] connect $nl; [$g findITerm SE] connect $nl
}
foreach t $TI { lassign $t name cell x y in out
  set i [mk $name $cell $x $y]; [$i findITerm A] connect [gnet $in]; [$i findITerm Y] connect [gnet $out] }
puts "parent_trunk_insert: [llength $TI] trunk cells, [llength $TS] sinks; $CLK_NET iterms [llength [$ck getITerms]]"
detailed_placement
check_placement
if {[ptenv OT_PT_NO_IO 0] ne "1"} { write_db $::env(OUT) }
