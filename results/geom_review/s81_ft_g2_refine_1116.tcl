read_db /work/run/results/asap7/dp_serdes__t1__clb45db5be/base/3_place.odb
set gb [ord::get_db_block]
set gd [expr {double([$gb getDbUnitsPerMicron])}]
set gsaved {};set ganchors {};set moved 0;set allft 0
foreach i [$gb getInsts] {
 set nm [$i getName]
 if {[string match *DFF* [[$i getMaster] getName]] && [regexp {u_ft_ft0_o_([0-7])[/\.]} $nm -> st]} {
  incr allft
  foreach it [$i getITerms] {if {[$it getNet] ne "NULL"} {dict set gsaved "$nm/[[$it getMTerm] getName]" [[$it getNet] getName]}}
  lassign [$i getLocation] x y
  if {$st<5} {set x [expr {$x-int(round((5-$st)*4.05*$gd))}];incr moved}
  $i setPlacementStatus PLACED
  $i setLocation $x $y
  $i setPlacementStatus FIRM
 } elseif {[$i getPlacementStatus] in {FIRM LOCKED}} {dict set ganchors $nm [$i getLocation]}
}
if {$allft != 4104 || $moved != 2565} {error "wrong fullshape FT refinement $allft $moved"}
# Resolve fixed tap/endcap obstacles before authorising new FT FIRM sites.
set gfset {};set gfmap {};set gfrows {};set gobstacles {};set grh 270
foreach ii [$gb getInsts] {
 set nn [$ii getName]
 if {[string match *DFF* [[$ii getMaster] getName]] && [regexp {u_ft_ft0_o_([0-7])[/\.]} $nn -> ss]} {
  if {[string match */eq* $nn]} {set bb eq} elseif {![regexp {q\\?\[([0-9]+)} $nn -> bb]} {error "unclassified FT DFF $nn"}
  dict set gfset $nn $ii;dict set gfmap "$ss,$bb" $ii
  set zz [$ii getBBox]
  for {set rr [expr {int(floor(double([$zz yMin])/$grh))}]} {$rr<=int(floor(double([$zz yMax]-1)/$grh))} {incr rr} {dict lappend gfrows $rr $ii}
 } elseif {[$ii getPlacementStatus] in {FIRM LOCKED}} {
  set zz [$ii getBBox];set pad [expr {[[$ii getMaster] isBlock] ? int(8.64*$gd) : 216}]
  set xa [expr {[$zz xMin]-$pad}];set xb [expr {[$zz xMax]+$pad}]
  set ya [expr {[$zz yMin]-([[$ii getMaster] isBlock] ? $pad : 0)}];set yb [expr {[$zz yMax]+([[$ii getMaster] isBlock] ? $pad : 0)}]
  for {set rr [expr {int(floor(double($ya)/$grh))}]} {$rr<=int(floor(double($yb-1)/$grh))} {incr rr} {dict lappend gobstacles $rr [list $xa $ya $xb $yb]}
 }
}
proc gf_blocked {ii xx yy} {
 global gfrows gobstacles grh
 set z [$ii getBBox];lassign [$ii getLocation] ox oy
 set x0 [expr {[$z xMin]+$xx-$ox}];set x1 [expr {[$z xMax]+$xx-$ox}];set y0 [expr {[$z yMin]+$yy-$oy}];set y1 [expr {[$z yMax]+$yy-$oy}]
 for {set r [expr {int(floor(double($y0)/$grh))}]} {$r<=int(floor(double($y1-1)/$grh))} {incr r} {
  if {[dict exists $gobstacles $r]} {foreach q [dict get $gobstacles $r] {lassign $q a b c d;if {$x0<$c && $a<$x1 && $y0<$d && $b<$y1} {return 1}}}
  if {[dict exists $gfrows $r]} {foreach jj [dict get $gfrows $r] {if {$jj eq $ii} continue;set zz [$jj getBBox];if {$x0<[$zz xMax] && [$zz xMin]<$x1 && $y0<[$zz yMax] && [$zz yMin]<$y1} {return 1}}}
 }
 return 0
}
proc gf_hops_ok {ss bb xx yy} {
 global gfmap gd
 foreach ns [list [expr {$ss-1}] [expr {$ss+1}]] {
  if {$ns<0 || $ns>7} continue
  lassign [[dict get $gfmap "$ns,$bb"] getLocation] nx ny
  if {abs($xx-$nx)+abs($yy-$ny)>405*$gd} {return 0}
 }
 return 1
}
set avoided 0
foreach key [dict keys $gfmap] {
 set ii [dict get $gfmap $key];lassign [split $key ,] ss bb;lassign [$ii getLocation] xx yy
 if {![gf_blocked $ii $xx $yy]} continue
 set found 0
 for {set n 1} {$n<=100 && !$found} {incr n} {
  foreach sign {-1 1} {
   set nx [expr {$xx+$sign*$n*54}]
   if {![gf_blocked $ii $nx $yy] && [gf_hops_ok $ss $bb $nx $yy]} {
    $ii setPlacementStatus PLACED;$ii setLocation $nx $yy;$ii setPlacementStatus FIRM
    puts "G2_FT_TAP_AVOID [$ii getName] delta_um=[expr {($nx-$xx)/$gd}]"
    incr avoided;set found 1;break
   }
  }
 }
 if {!$found} {error "No legal same-row FT site within hop405: [$ii getName]"}
}
puts "G2_FT_OBSTACLES avoided=$avoided"
detailed_placement
check_placement -verbose
set changes 0
foreach i [$gb getInsts] {set nm [$i getName];foreach it [$i getITerms] {set key "$nm/[[$it getMTerm] getName]";if {[dict exists $gsaved $key] && ([$it getNet] eq "NULL" || [dict get $gsaved $key] ne [[$it getNet] getName])} {incr changes}}}
if {$changes} {error "FT net identity changed $changes"}
dict for {nm xy} $ganchors {set ii [$gb findInst $nm];if {$ii eq "NULL" || [$ii getLocation] ne $xy} {error "FIRM anchor moved $nm"}}
set pos {};set fp [open /out/g2_refined_positions_legal.tsv w]
foreach i [$gb getInsts] {set nm [$i getName];if {[regexp {u_ft_ft0_o_([0-7])/q\\?\[([0-9]+)} $nm -> st bit]} {lassign [$i getLocation] x y;dict set pos "$st,$bit" [list $x $y];puts $fp "$nm $x $y"}}
close $fp
set maxhop 0;set nbad 0
for {set st 0} {$st<7} {incr st} {for {set bit 0} {$bit<512} {incr bit} {lassign [dict get $pos "$st,$bit"] x y;lassign [dict get $pos "[expr {$st+1}],$bit"] xx yy;set h [expr {(abs($x-$xx)+abs($y-$yy))/$gd}];set maxhop [expr {max($h,$maxhop)}];if {$h>405} {incr nbad}}}
if {$nbad} {error "FT hop >405 afterrefine: $nbad max$maxhop"}
write_db /work/run/results/asap7/dp_serdes__t1__clb45db5be/base/3_place.g2_refined_legal.odb
puts "G2_REFINED_PASS shifted=$moved ft=$allft netpins=[dict size $gsaved] anchors=[dict size $ganchors] maxhop=$maxhop over405=$nbad"
exit
