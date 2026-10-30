from pathlib import Path
import json,shutil,hashlib
b=Path('/srv/opentallas-scratch2/claude/codex-collft-0336');t='coll_ft__cla4a25d77'
p=json.loads((b/'plan_collft_nf40lowtap.json').read_text());bands=p['partition_types'][t]['clock']['landing_contract']['bands'];a=json.loads((b/'anchors_nf40lowtap.json').read_text())
for n in a['stats']:bands[n]['ring_place']='ff'
(b/'plan/plan_collft_nf40lowtap_ff3.json').write_text(json.dumps(p,indent=2)+'\n')
src=b/'gen_nf40low_ff2'/t;dst=b/'gen_nf40low_ff3'/t;shutil.copytree(src,dst);k=dst/t
old=(k/'nf40low_anchors.tcl').read_text();functions='proc nf_name'+old.split('proc nf_name',1)[1]
functions=functions.replace('cland_n cland_fh\n','cland_n cland_fh cland_occ\n',1)
marker=' if {[$i getPlacementStatus] eq "FIRM"}'
check=''' if {$reserve > 0} {
  set row [expr {int(($y-$ff_y0)/$ff_rh)}]
  if {[dict exists $cland_occ $row]} {
   foreach iv [dict get $cland_occ $row] {
    lassign $iv lo hi
    if {$x < $hi && $x+$rw > $lo} { error "NF occupied reserved footprint before GPL [$i getName]: x=$x y=$y rw=$rw occupied=$iv" }
   }
  }
 }
'''
assert functions.count(marker)==1;functions=functions.replace(marker,check+marker,1)
lines=['# FF3 same .4-reserve global-bit anchors repacked around ACTUAL physical TAP/edge cells.','set nf_anchors {}','set nf_protected {}']
def name(n):return '{'+n.replace('\\','')+'}'
for q in a['anchors']:
 x,y=q['origin_um'];lines.append(f"dict set nf_anchors {name(q['name'])} [list {x} {y} {q['reserved_width_um']}]")
for q in a['protected']:
 x,y=q['origin_um'];lines.append(f"dict set nf_protected {name(q['name'])} [list {x} {y}]")
(k/'nf40low_anchors.tcl').write_text('\n'.join(lines)+'\n'+functions)
(k/'PLAN_SHA').write_text(hashlib.sha256((b/'plan/plan_collft_nf40lowtap_ff3.json').read_bytes()).hexdigest()+'\n')
shutil.copy2(k/'nf40low_anchors.tcl',b/'nf40lowtap_anchors_ff3.tcl')
print(k)
