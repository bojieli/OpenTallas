"""Close sub-minimum same-net gaps by trimming only a shield's outer edge.

PG and clock conductors are immutable. Narrowing an outer shield edge keeps the
clock-facing edge and its spacing, and avoids joining a shield to PG into a new
wide-spacing class. All coordinates are native integer DBUs.
"""
from collections import defaultdict


def trim_shields(rows, widths, gap=40, min_width=40):
    out=[dict(r,rect=list(r['rect'])) for r in rows]
    eligible=set();bins=defaultdict(list)
    for i,r in enumerate(out):
        if r['net']!='VSS' or not r.get('special',True) or r['layer'] not in ('M8','M9'):continue
        axis=1 if r['layer']=='M8' else 0;q=r['rect']
        if q[axis+2]-q[axis] in widths:eligible.add(i)
        bins[r['layer'],q[axis]//gap].append(i)
    edits=[]
    for i,r in enumerate(out):
        if r['net']!='VSS' or r['layer'] not in ('M8','M9'):continue
        ax=1 if r['layer']=='M8' else 0;along=1-ax;a=r['rect'];edge=a[ax+2]
        for bucket in (edge//gap,edge//gap+1):
            for j in bins.get((r['layer'],bucket),[]):
                if i==j:continue
                b=out[j]['rect'];g=b[ax]-a[ax+2]
                if not 0<g<gap or min(a[along+2],b[along+2])<=max(a[along],b[along]):continue
                target=i if i in eligible else j if j in eligible else None
                if target is None:continue
                before=list(out[target]['rect']);delta=gap-g
                if target==i:a[ax+2]-=delta
                else:b[ax]+=delta
                after=out[target]['rect']
                if after[ax+2]-after[ax]<min_width:raise ValueError('shield notch trim violates minimum width')
                edits.append(dict(index=target,before=before,after=list(after),gap_before=g,gap_after=gap))
    return out,edits


def tcl(shield,width_um,gap_um=.04):
    """Actual OpenDB special-wire post-pass after PG and shields both exist."""
    return [r'''proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set bins {};array set dirty {}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {$sw in $::ot_clock_shield_swires && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  lappend bins($name,[expr {[lindex $box $a]/$gap}]) $i
 }}
 set fixes 0
 for {set i 0} {$i<$count} {incr i} {
  set a $ax($i);set along [expr {1-$a}];set name [$lays($i) getName]
  set edge [lindex $q($i) [expr {$a+2}]];set bin [expr {$edge/$gap}]
  foreach k [list $bin [expr {$bin+1}]] {
   if {![info exists bins($name,$k)]} {continue}
   foreach j $bins($name,$k) {
    if {$i==$j} {continue};set aa $q($i);set bb $q($j)
    set g [expr {[lindex $bb $a]-[lindex $aa [expr {$a+2}]]}]
    if {$g<=0 || $g>=$gap || min([lindex $aa [expr {$along+2}]],[lindex $bb [expr {$along+2}]])<=max([lindex $aa $along],[lindex $bb $along])} {continue}
    set target -1
    if {$eligible($i)} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j)} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    lset q($target) $index $value
    if {[lindex $q($target) [expr {$a+2}]]-[lindex $q($target) $a]<$gap} {error "shield notch trim violates minimum width"}
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  lassign $q($i) x0 y0 x1 y1;odb::dbSBox_destroy $objs($i)
  odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}''',f'ot_trim_shield_notches {shield} [expr {{round({width_um}*[$blk getDbUnitsPerMicron])}}] [expr {{round({gap_um}*[$blk getDbUnitsPerMicron])}}]']
