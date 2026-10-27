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
        if q[axis+2]-q[axis] in widths and r.get('outer_edge') in (axis,axis+2):eligible.add(i)
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
                target=i if i in eligible and r['outer_edge']==ax+2 else j if j in eligible and out[j]['outer_edge']==ax else None
                if target is None:continue
                before=list(out[target]['rect']);delta=gap-g
                if target==i:a[ax+2]-=delta
                else:b[ax]+=delta
                after=out[target]['rect']
                nominal=rows[target]['rect'][ax+2]-rows[target]['rect'][ax]
                if after[ax+2]-after[ax]<max(min_width,nominal*31/32):
                    out[target]['rect'][:]=before
                    continue
                edits.append(dict(index=target,before=before,after=list(after),gap_before=g,gap_after=gap,nominal_width=nominal,actual_width=after[ax+2]-after[ax],density_multiplier=nominal/(after[ax+2]-after[ax])))
    return out,edits


def provenance_tcl():
    return [r'''proc ot_shield_box {sw ly x0 y0 x1 y1 outer nominal} {
 set b [odb::dbSBox_create $sw $ly $x0 $y0 $x1 $y1 STRIPE]
 set ::ot_clock_shield_outer($b) $outer;set ::ot_clock_shield_nominal($b) $nominal
 return $b
}''']


def tcl(shield,width_um,gap_um=.04):
    """Actual OpenDB special-wire post-pass after PG and shields both exist."""
    return [r'''proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set faces {};array set nominal {};array set bins {};array set dirty {}
 array set provenance {};foreach sw $::ot_clock_shield_swires {set provenance($sw) 1}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {[info exists provenance($sw)] && [info exists ::ot_clock_shield_outer($b)] && [info exists ::ot_clock_shield_nominal($b)] && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  if {$eligible($i)} {set faces($i) $::ot_clock_shield_outer($b);set nominal($i) $::ot_clock_shield_nominal($b)}
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
    if {$eligible($i) && $faces($i)==$a+2} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j) && $faces($j)==$a} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    set proposed $q($target);lset proposed $index $value
    set actual [expr {[lindex $proposed [expr {$a+2}]]-[lindex $proposed $a]}]
    if {$actual<$gap || $actual*32<$nominal($target)*31} {continue}
    set q($target) $proposed
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  set axis $ax($i);set actual [expr {[lindex $q($i) [expr {$axis+2}]]-[lindex $q($i) $axis]}]
  puts "OT_SHIELD_WIDTH layer [$lays($i) getName] nominal $nominal($i) actual $actual outer $faces($i) density_multiplier [expr {double($nominal($i))/$actual}]"
  lassign $q($i) x0 y0 x1 y1
  unset -nocomplain ::ot_clock_shield_outer($objs($i)) ::ot_clock_shield_nominal($objs($i))
  odb::dbSBox_destroy $objs($i)
  set b [odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE]
  set ::ot_clock_shield_outer($b) $faces($i);set ::ot_clock_shield_nominal($b) $nominal($i)
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}''',f'ot_trim_shield_notches {shield} [expr {{round({width_um}*[$blk getDbUnitsPerMicron])}}] [expr {{round({gap_um}*[$blk getDbUnitsPerMicron])}}]']
