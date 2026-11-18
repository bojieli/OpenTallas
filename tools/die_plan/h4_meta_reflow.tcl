# H4 structural placement form: same RTL/register edges, metadata terminates at SYN alignment control.
if {![info exists ::env(H4_PREVIEW)] || $::env(H4_PREVIEW) ne "1"} {source /work/gp_noconverge_gate.tcl}
set h4_save_mid [expr {[info exists ::env(OT_TXL_MID)] ? $::env(OT_TXL_MID) : "0"}]
set ::env(OT_TXL_MID) 0
source /work/txl_mid.tcl
set ::env(OT_TXL_MID) $h4_save_mid
namespace eval h4_meta {
 proc cone {roots} {
  set cells [dict create];set front $roots
  while {[llength $front]} {
   set next {}
   foreach i $front {
    foreach t [$i getITerms] {
     if {![$t isInputSignal] || [[$t getMTerm] getName] in {CLK CLKN CK CKN RESETN SETN}} continue
     set n [$t getNet];if {$n eq "NULL" || [$n getSigType] in {CLOCK POWER GROUND}} continue
     foreach q [$n getITerms] {
      if {![$q isOutputSignal]} continue
      set j [$q getInst];set name [$j getName];set m [$j getMaster]
      if {[dict exists $cells $name] || [$m isBlock] || [$m isSequential] || [regexp {^(DFF|SDFF)} [$m getName]]} continue
      if {[$j getPlacementStatus] in {FIRM LOCKED COVER}} {error "H4 fixed comb authority in AM cone: $name"}
      dict set cells $name $j;lappend next $j
     }
    }
   }
   set front $next
  }
  return $cells
 }
 proc run {} {
  set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
  set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set macs {};set halo [expr {8.64*$u}];set am {};set anchors {};set lasts {}
  foreach i [$b getInsts] {
   set n [$i getName];set nn [string map {\\ {}} $n];set m [$i getMaster]
   if {[$m isBlock]} {set z [$i getBBox];lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]}
   if {![regexp {DFF} [$m getName]]} continue
   if {[regexp {u_dec[.]u_syn[.]am_ok[$]} $nn]} {lappend am $i}
   if {[regexp {u_dec[.]u_syn[.](wc|miss|cand|lock)([[]|[$])} $nn]} {lappend anchors $i}
   if {[regexp {u_dec[.]u_rck_transport4[.]q[[]([0-9]+)[]]} $nn -> bit] && $bit>=544 && $bit<=553} {dict set lasts $bit $i}
  }
  if {[llength $am]!=1 || [llength $anchors]!=8 || [dict size $lasts]!=10} {error "H4 wrong full shape: am[llength $am] anchors[llength $anchors] metadata[dict size $lasts]"}
  set ax 0.0;set ay 0.0
  foreach i $anchors {lassign [$i getLocation] x y;set ax [expr {$ax+$x/8.0}];set ay [expr {$ay+$y/8.0}]}
  set o [open $::env(RESULTS_DIR)/H4_meta_sites.tsv w]
  set ff [lindex $am 0];set roots [cone [list $ff]];set k 0
  foreach n [lsort [dict keys $roots]] {
   set i [dict get $roots $n];lassign [$i getLocation] ox oy
   set tx [expr {$ax+(($k%10)-4.5)*1.62*$u}];set ty [expr {$ay+(8.64+($k/10)*0.54)*$u}]
   set p [ot_txl_mid::nearest_free $tx $ty $macs $core [expr {1.08*$u}] [expr {50*$u}]]
   if {![llength $p]} {error "H4 no macro-free AM logic site"}
   lassign $p x y;$i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED
   puts $o "comb\t$n\t[expr {$ox/$u}]\t[expr {$oy/$u}]\t[expr {$x/$u}]\t[expr {$y/$u}]";incr k
  }
  lassign [$ff getLocation] ox oy
  set pp [ot_txl_mid::nearest_free [expr {$ax+2.16*$u}] [expr {$ay+5.4*$u}] $macs $core [expr {1.08*$u}] [expr {50*$u}]]
  if {![llength $pp]} {error "H4 no macro-free am_ok FF site"}
  lassign $pp x y;$ff setLocation [expr {int($x)}] [expr {int($y)}];$ff setPlacementStatus PLACED
  puts $o "am_ok\t[$ff getName]\t[expr {$ox/$u}]\t[expr {$oy/$u}]\t[expr {$x/$u}]\t[expr {$y/$u}]"
  set maxhop 0.0;set moved 0;set hcells 0
  dict for {bit q} $lasts {
   set C u_dec.u_rck_transport4;set chain [list $q];set src {}
   for {set cur $q} {[llength $chain]<16} {} {
    set d [ot_txl_mid::iterm_of $cur {D}];if {$d eq ""} break
    set up [ot_txl_mid::up $d];if {![llength $up]} break
    lassign $up di dt
    if {[string first "$C.g_reg.r" [$di getName]]>=0} {set chain [linsert $chain 0 $di];set cur $di} else {set src $dt;break}
   }
   set qo [ot_txl_mid::iterm_of $q {QN Q}];set snk [expr {$qo eq "" ? "" : [ot_txl_mid::down $qo]}]
   if {[llength $chain]!=4 || $src eq "" || $snk eq ""} {error "H4 incomplete metadata bit$bit chain [llength $chain]"}
   lassign [ot_txl_mid::ctr $src] sx sy;lassign [ot_txl_mid::ctr $snk] dx dy
   set pts [ot_txl_mid::targets $sx $sy $dx $dy 4];set places {}
   foreach p $pts {lassign $p tx ty;set z [ot_txl_mid::nearest_free $tx $ty $macs $core [expr {1.08*$u}] [expr {50*$u}]];if {![llength $z]} {error "H4 no metadata relay site"};lappend places $z}
   set hs {};foreach r $chain {lappend hs [ot_txl_mid::up_cells [ot_txl_mid::iterm_of $r {D}]]}
   set px $sx;set py $sy
   foreach r $chain p $places hc $hs {
    if {[$r getPlacementStatus] in {FIRM LOCKED COVER}} {error "H4 metadata relay is fixed: [$r getName]"}
    lassign $p x y;lassign [$r getLocation] ox oy
    incr hcells [ot_txl_mid::place_hop $hc $px $py $x $y $macs $core [expr {1.08*$u}] [expr {50*$u}]]
    $r setLocation [expr {int($x)}] [expr {int($y)}];$r setPlacementStatus PLACED;incr moved
    set h [expr {(abs($x-$px)+abs($y-$py))/$u}];if {$h>$maxhop} {set maxhop $h}
    puts $o "meta\t[$r getName]\t[expr {$ox/$u}]\t[expr {$oy/$u}]\t[expr {$x/$u}]\t[expr {$y/$u}]"
    set px $x;set py $y
   }
   incr hcells [ot_txl_mid::place_hop [ot_txl_mid::up_cells $snk] $px $py $dx $dy $macs $core [expr {1.08*$u}] [expr {50*$u}]]
   set h [expr {(abs($dx-$px)+abs($dy-$py))/$u}];if {$h>$maxhop} {set maxhop $h}
  }
  close $o
  if {$maxhop>405} {error "H4 metadata registered hop exceeds405: $maxhop"}
  puts "H4_META_REFLOW am_ok1 metadataFF$moved comb[dict size $roots] buffer_moves$hcells max_hop_um[format %.3f $maxhop] cycles0 anchor[expr {$ax/$u}],[expr {$ay/$u}]"
 }
}
h4_meta::run
