from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path('/home/ubuntu/coord/tmp/qc0815');d=defaultdict(list)
for l in (p/'r9_mux_grid.txt').read_text().splitlines():
 g,n,*r=l.split();d[g].append((n,list(map(float,r))))
f,a=plt.subplots(figsize=(10,8));rows=[]
occupied=[]
for g,L in sorted(d.items(),key=lambda z:(z[1][0][1][3]-z[1][0][1][1],z[0])):
 for k,(n,(x,y,X,Y)) in enumerate(L):
  w=.486 if '_A_' in g else .54
  candidates=[]
  for ri in range(round((y-4.32)/.27),round((Y-4.32)/.27)):
   yy0=round(4.32+ri*.27,3)
   for ci in range(6):
    xx0=round(4.32+round((x+.27+ci*1.08-4.32)/.054)*.054,3)
    if xx0<x or xx0+w>X or yy0<y or yy0+.27>Y+.001:continue
    if any(xx0+w+.216>a and xx0-.216<A and yy0+.269>b and yy0<B-.001 for a,b,A,B in occupied):continue
    candidates.append((abs(yy0-(y+Y)/2)+.1*abs(xx0-(x+X)/2),xx0,yy0))
  assert candidates,('No legal site',g,n)
  _,xx0,yy=min(candidates);occupied.append((xx0,yy,xx0+w,yy+.27));xx=xx0+w/2
  rows.append(f' {{{n} {xx:.3f} {yy:.3f} {x:.3f} {y:.3f} {X:.3f} {Y:.3f}}}');a.plot(xx,yy,'b.' if '_A_' in g else 'g.',ms=4)
a.set(xlim=(245,345),ylim=(0,270),aspect='equal',title='BTAB R9b deterministic bounded mux placement: A blue -> B green\n2D globally packed sites in unchanged bounds, exact footprints and >=0.216um padding')
f.savefig(p/'btab_r9b_mux_plan.png',dpi=120)
s='''# R9b deterministic mux datapath placement in the approved R7 bounded grids.
set rb [ord::get_db_block]; set ru [$rb getDbUnitsPerMicron]; set ro {}
foreach row [$rb getRows] {dict set ro [lindex [$row getOrigin] 1] [$row getOrient]}
set rn 0
foreach rec {\n'''+ '\n'.join(rows)+'''
} {
 lassign $rec n xc y x0 y0 x1 y1
 set i [$rb findInst $n];if {$i eq "NULL"} {error "R9_MUX missing $n"}
 set w [expr {[[$i getMaster] getWidth]/double($ru)}]
 set x [expr {4.32+round(($xc-$w/2.0-4.32)/0.054)*0.054}]
 set yy [expr {round($y*$ru)}]
 if {![dict exists $ro $yy]} {error "R9_MUX no row at $y"}
 if {$x<$x0 || $x+$w>$x1 || $y<$y0 || $y+0.27>$y1+0.001} {error "R9_MUX outside grid $n"}
 $i setOrient [dict get $ro $yy]
 $i setLocation [expr {round($x*$ru)}] $yy
 $i setPlacementStatus FIRM
 incr rn
}
foreach g [$rb getGroups] {if {[string match r7_mux_* [$g getName]]} {foreach i [$g getInsts] {$g removeInst $i};odb::dbGroup_destroy $g}}
foreach r [$rb getRegions] {if {[string match r7_mux_* [$r getName]]} {odb::dbRegion_destroy $r}}
puts "R9_MUX_FIXED $rn deterministic grid cells, no sparse GPL groups"
'''
(p/'r9_mux_fixed.tcl').write_text(s)
print('mux sites',len(rows))
