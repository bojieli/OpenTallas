from pathlib import Path
import json
b=Path('/srv/opentallas-scratch2/claude/codex-collft-0336');a=json.loads((b/'anchors_nf40low.json').read_text())
lines=['# LOCAL coll_ft PLACE-only physical candidate; no RTL/cycle change. Unchanged 0.4 reserved footprint.','set nf_anchors {}','set nf_protected {}']
def esc(n):return '{'+n.replace('\\','')+'}'
for q in a['anchors']:
 x,y=q['origin_um'];lines.append(f"dict set nf_anchors {esc(q['name'])} [list {x} {y} {q['reserved_width_um']}]")
for q in a['protected']:
 x,y=q['origin_um'];lines.append(f"dict set nf_protected {esc(q['name'])} [list {x} {y}]")
lines.append(r'''
proc nf_name {i} { return [string map {\\ {}} [$i getName]] }
proc nf_put {i xy reserve} {
 global ff_dbu ff_sw ff_rh ff_x0 ff_y0 ff_orient cland_done cland_n cland_fh
 lassign $xy ax ay
 set x [expr {int(round($ax*$ff_dbu))}];set y [expr {int(round($ay*$ff_dbu))}]
 set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
 if {$h != $ff_rh || ($x-$ff_x0)%$ff_sw || ($y-$ff_y0)%$ff_rh || ![dict exists $ff_orient $y]} { error "NF invalid row/site [$i getName]" }
 set rw [expr {$reserve > 0 ? int(round($reserve*$ff_dbu)) : $w}]
 if {$reserve > 0 && $w > $rw*0.4+1} { error "NF actual cell exceeds unchanged .4 reserved footprint [$i getName]" }
 $i setOrient [dict get $ff_orient $y]
 $i setLocation $x $y
 $i setPlacementStatus FIRM
 cland_occupy $x $y $rw $h
 dict set cland_done [$i getName] 1;incr cland_n
 puts $cland_fh "[$i getName]\tcland:nf40low\t$ax\t$ay\t-"
}
set nf_seen {};set nf_pseen {}
foreach i [$ff_blk getInsts] {
 set k [nf_name $i]
 if {[dict exists $nf_anchors $k]} { set v [dict get $nf_anchors $k];nf_put $i $v [lindex $v 2];dict set nf_seen $k 1 }
 if {[dict exists $nf_protected $k]} { nf_put $i [dict get $nf_protected $k] 0;dict set nf_pseen $k 1 }
}
if {[dict size $nf_seen] != [dict size $nf_anchors] || [dict size $nf_pseen] != [dict size $nf_protected]} { error "NF missing expected anchor/protected names: [dict size $nf_seen]/[dict size $nf_anchors] [dict size $nf_pseen]/[dict size $nf_protected]" }
rename cland_put nf_original_put
proc cland_put {i rect tag {sp {}} {cur 0}} {
 if {[dict exists $::nf_protected [nf_name $i]]} { return }
 nf_original_put $i $rect $tag $sp $cur
}
rename cland_place_ff nf_original_place_ff
proc cland_place_ff {prefix rect tag} {
 set hit 0
 foreach i [$::ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
  if {[dict exists $::cland_done $nm]} { incr hit;continue }
  if {[regexp {DFF|DHL|DLL|SDF|LQN} [[$i getMaster] getName]]} { error "NF unplanned mapped FF $nm" }
 }
 puts "OT_CLAND local bit-correlated FF anchors $prefix: $hit FIRM; combinational logic movable"
 return $hit
}
puts "OT_CLAND NF40LOW anchored [dict size $nf_seen] FFs and preserved [dict size $nf_pseen] protected cells; reserve 0.4 unchanged"
''')
(b/'nf40low_anchors.tcl').write_text('\n'.join(lines)+'\n')
k=b/'gen_nf40low_ff/coll_ft__cla4a25d77/coll_ft__cla4a25d77';t=k/'landing_placement.tcl'
s=t.read_text();marker='foreach spec $cland_groups {';assert s.count(marker)==2
s=(k/'landing_placement.generated.tcl').read_text() if (k/'landing_placement.generated.tcl').exists() else s
(k/'landing_placement.generated.tcl').write_text(s)
(k/'nf40low_anchors.tcl').write_text((b/'nf40low_anchors.tcl').read_text())
before,after=s.rsplit(marker,1);s=before+'source /work/nf40low_anchors.tcl\n'+marker+after;t.write_text(s)
print(k)
