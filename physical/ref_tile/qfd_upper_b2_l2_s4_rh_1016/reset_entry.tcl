# Source-specific reset boundary for the existing RPIN1 FF. No new logical stage.
# Standard input hold/pin-flop hooks intentionally skip async-reset loads. The
# actual predecessor CTS repeatedly missed its 30ps finishing margin at this
# single raw reset input while adding unrelated internal hold cells.
set b2rb [ord::get_db_block]
set b2rr [$b2rb findBTerm rst_n]
if {$b2rr eq "NULL" || $b2rr eq ""} {error "B2_RESET_ENTRY missing actual rst_n"}
set b2rff {}
foreach inst [$b2rb getInsts] {
  if {[string match {*g_rpin*rs_q*} [$inst getName]] && [string match {DFF*} [[$inst getMaster] getName]]} {lappend b2rff $inst}
}
if {[llength $b2rff]!=1} {error "B2_RESET_ENTRY expected exactly one source RPIN1 FF, got [llength $b2rff]"}
set b2rff [lindex $b2rff 0]
set b2rp [$b2rff findITerm RESETN]
if {$b2rp eq "NULL" || $b2rp eq ""} {error "B2_RESET_ENTRY actual RPIN FF lacks RESETN"}
set b2rn [$b2rp getNet]
if {$b2rn eq "NULL" || $b2rn eq ""} {error "B2_RESET_ENTRY unconnected RESETN"}
set b2rm [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
if {$b2rm eq "NULL" || $b2rm eq ""} {error "B2_RESET_ENTRY actual HB4 delay master missing"}
if {[$b2rb findInst b2_reset_entry_hold] ne "NULL" && [$b2rb findInst b2_reset_entry_hold] ne ""} {error "B2_RESET_ENTRY refuses duplicate application"}
set b2rc [odb::dbInst_create $b2rb $b2rm b2_reset_entry_hold]
set b2rnew [odb::dbNet_create $b2rb b2_reset_entry_hold_n]
$b2rp disconnect
[$b2rc findITerm A] connect $b2rn
[$b2rc findITerm Y] connect $b2rnew
$b2rp connect $b2rnew
set b2rbox {}
foreach bp [$b2rr getBPins] {foreach bx [$bp getBoxes] {set b2rbox $bx;break};if {$b2rbox ne ""} break}
if {$b2rbox eq ""} {error "B2_RESET_ENTRY reset pin must already have assigned geometry"}
set b2rcore [$b2rb getCoreArea]
# Choose the actual top-most row that holds the FF two sites below the core top, and use THAT row's
# orientation and origin (ASAP7 rows alternate R0/MX; an R0 cell on an MX row is illegal).
set b2rffh [[$b2rff getMaster] getHeight]
set b2rrow ""
set b2ry -1
foreach row [$b2rb getRows] {
  set oy [lindex [$row getOrigin] 1]
  set rh [[$row getSite] getHeight]
  if {$oy + $b2rffh <= [$b2rcore yMax] - 2*$rh && $oy > $b2ry} {set b2ry $oy; set b2rrow $row}
}
if {$b2rrow eq ""} {error "B2_RESET_ENTRY no legal row below the assigned N face"}
set b2rsx [[$b2rrow getSite] getWidth]
set b2rox [lindex [$b2rrow getOrigin] 0]
set b2rori [$b2rrow getOrient]
set b2rx [expr {int(([$b2rbox xMin]+[$b2rbox xMax])/2)}]
set b2rx [expr {$b2rox+int(($b2rx-$b2rox)/$b2rsx)*$b2rsx}]
set b2rhx [expr {$b2rx-int(([$b2rm getWidth]+$b2rsx-1)/$b2rsx)*$b2rsx-$b2rsx}]
if {$b2rhx<[$b2rcore xMin] || $b2rx+[[$b2rff getMaster] getWidth]>[$b2rcore xMax]} {error "B2_RESET_ENTRY assigned N-face station does not fit"}
foreach {inst x} [list $b2rff $b2rx $b2rc $b2rhx] {
  $inst setOrient $b2rori
  $inst setLocation $x $b2ry
  $inst setPlacementStatus FIRM
}
set_dont_touch [get_cells b2_reset_entry_hold]
$b2rnew setDoNotTouch 1
puts "B2_RESET_ENTRY source [$b2rff getName] N-face existing FF + HB4 hold cell; normal pipeline unchanged"
