# RXB vE: locality for new RQ capture and existing writer data slots, no new cycles.
proc rxb_locality_place {} {
 source /work/dmem_read_pins.tcl
 set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
 set core [$b getCoreArea];set rows [$b getRows];set site [[lindex $rows 0] getSite]
 set sx [$site getWidth];set rh [$site getHeight];set ys {};set ori {}
 foreach row $rows {set y [lindex [$row getOrigin] 1];lappend ys $y;dict set ori $y [$row getOrient]}
 set ys [lsort -unique -integer $ys]
 set mac {};set rq {};set banks {};set maxw 0;set area 0
 foreach i [$b getInsts] {
  set n [string map [list "\\" ""] [$i getName]];set m [$i getMaster];set mn [$m getName]
  if {$mn eq "ot_sram_1r1w2c_64x546_m1"} {lappend mac $i}
  if {![string match *DFF* $mn]} {continue}
  if {[string match *u_lpl_5_w*data* $n]} {dict set banks $n $i}
 }
 if {[llength $mac]!=1 || [dict size $banks]!=2176} {
  error "RXB_LOCAL: native macro/bank count [llength $mac]/[dict size $banks], expected1/2176"
 }
 set mac [lindex $mac 0];if {[$mac getOrient] ne "R0"} {error "RXB_LOCAL: native pin table requires R0"}
 # Cell names follow canonical output aliases in Yosys. Discover topology from native pins.
 set used {}
 for {set bit 0} {$bit<544} {incr bit} {
  set it [$mac findITerm [format {rd_out[%d]} $bit]]
  if {$it eq "NULL" || $it eq ""} {error "RXB_LOCAL: missing native rd_out bit$bit"}
  set q [list [$it getNet]];set seen {};set hit {}
  while {[llength $q]} {
   set net [lindex $q end];set q [lrange $q 0 end-1]
   if {$net eq "NULL" || [dict exists $seen [$net getName]]} {continue}
   dict set seen [$net getName] 1
   foreach t [$net getITerms] {
    if {[$t getIoType] ne "INPUT"} {continue}
    set ci [$t getInst];set cm [[$ci getMaster] getName];set pn [[$t getMTerm] getName]
    if {[string match *DFF* $cm] && $pn eq "D"} {dict set hit [$ci getName] $ci;continue}
    if {[regexp {^(BUF|INV)} $cm]} {
     foreach o [$ci getITerms] {if {[$o getIoType] eq "OUTPUT"} {lappend q [$o getNet]}}
    } else {error "RXB_LOCAL: native bit$bit non-capture sink [$ci getName]/$pn"}
   }
  }
  if {[dict size $hit]!=1} {error "RXB_LOCAL: native bit$bit capture count[dict size $hit]"}
  set i [lindex [dict values $hit] 0];set name [$i getName]
  if {[dict exists $used $name]} {error "RXB_LOCAL: FF $name shared by native bits"}
  dict set used $name 1;dict set rq $bit $i;set m [$i getMaster]
  set maxw [expr {max($maxw,[$m getWidth])}]
  set area [expr {$area+[$m getWidth]*double([$m getHeight])/$u/$u}]
 }
 lassign [$mac getLocation] mx my
 # Entire west bay outside5.4um halo, 6columns separated by at least0.432um.
 set right [expr {$mx-round(5.4*$u)}];set left [$core xMin]
 set pitch [expr {ceil(($maxw+.432*$u)/double($sx))*$sx}];set cols 6
 if {$right-$cols*$pitch<$left} {error "RXB_LOCAL: six capture columns exceed available west bay"}
 set bayh 56.0;set fill [expr {$area/(($right-$left)/$u*$bayh)}]
 if {$fill>.40} {error "RXB_LOCAL: capture bay fill $fill exceeds0.40"}
 set occ {};set anchors {};set maxreach 0
 for {set bit 0} {$bit<544} {incr bit} {
  set i [dict get $rq $bit];set m [$i getMaster];lassign [dict get $rxb_rd_pin_xy $bit] px py
  set py [expr {$my+$py*$u}];set px [expr {$mx+$px*$u}]
  set target [expr {$py-$rh/2.0}];set best {};set bd 1e30
  foreach y $ys {set d [expr {abs($y-$target)}];if {$d<$bd} {set bd $d;set best $y}}
  set col [expr {$bit%$cols}];set x [expr {$right-($col+1)*$pitch}]
  set x [expr {int([$core xMin]+floor(($x-[$core xMin])/double($sx))*$sx)}]
  if {[dict exists $occ "$x,$best"]} {error "RXB_LOCAL: capture occupancy collision bit$bit"}
  dict set occ "$x,$best" 1
  if {[$i getPlacementStatus] eq "FIRM"} {error "RXB_LOCAL: capture already FIRM $bit"}
  $i setOrient [dict get $ori $best];$i setLocation $x $best;$i setPlacementStatus FIRM
  set reach [expr {(abs($px-$x)+abs($py-$best))/$u}];set maxreach [expr {max($maxreach,$reach)}]
  lappend anchors [list $bit [$i getName] [expr {$x/$u}] [expr {$best/$u}] $reach]
 }
 if {$maxreach>20} {error "RXB_LOCAL: capture reach $maxreach exceeds20um"}
 # Writer data banks sit southwest, below native macro+halo, never across dchn.
 set box {4.32 4.32 82.08 37.8};lassign $box x0 y0 x1 y1;set ba 0
 dict for {n i} $banks {set m [$i getMaster];set ba [expr {$ba+[$m getWidth]*double([$m getHeight])/$u/$u}];if {[$i getGroup] ne "NULL" && [$i getGroup] ne ""} {error "RXB_LOCAL: existing bank group $n"}}
 set bf [expr {$ba/(($x1-$x0)*($y1-$y0))}]
 if {$bf>.40} {error "RXB_LOCAL: southwest bank fill $bf exceeds0.40"}
 set r [odb::dbRegion_create $b rxb_dmem_writer];$r setRegionType EXCLUSIVE
 odb::dbBox_create $r [expr {round($x0*$u)}] [expr {round($y0*$u)}] [expr {round($x1*$u)}] [expr {round($y1*$u)}]
 set g [odb::dbGroup_create $r rxb_dmem_writer];$g setType VOLTAGE_DOMAIN
 dict for {n i} $banks {$g addInst $i}
 set f [open /work/rxb_capture_anchors.list w];foreach a $anchors {puts $f $a};close $f
 puts "RXB_LOCAL: capture544 area$area fill$fill columns$cols max_pin_origin_reach$maxreach bank2176 area$ba fill$bf region$box"
}
proc rxb_locality_release {} {
 set b [ord::get_db_block];set n 0
 set f [open /work/rxb_capture_anchors.list];set data [read $f];close $f
 foreach row [split $data "\n"] {
  if {$row eq ""} {continue}
  set i [$b findInst [lindex $row 1]]
  if {$i eq "NULL" || [$i getPlacementStatus] ne "FIRM"} {error "RXB_LOCAL: capture release lost [lindex $row 1]"}
  $i setPlacementStatus PLACED;incr n
 }
 if {$n!=544} {error "RXB_LOCAL: release capture$n expected544"}
 foreach g [$b getGroups] {if {[$g getName] eq "rxb_dmem_writer"} {set r [$g getRegion];odb::dbGroup_destroy $g;odb::dbRegion_destroy $r}}
 puts "RXB_LOCAL: released capture$n and southwest bank region before detailed legalization"
}
