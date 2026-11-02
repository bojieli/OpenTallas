import json,re,gzip,hashlib,csv
from pathlib import Path
O=Path(__file__).resolve().parent;poses=json.loads((O/'repack_legal_poses.json').read_text());cert=json.loads((O/'legalize_repack.json').read_text());assert cert['failed']==0 and cert['R2R']['r2r_captures_gt405']==0
source=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/capsule/1_synth_odb.v').read_text();mapped={n.replace('\\',''):c for c,n in re.findall(r'(?m)^\s*(DFF\S+)\s+(\\?\S+)\s*\(',source)};assert len(mapped)==len(poses)==18768
resize=[]
for p in poses:
 old=mapped[p['name'].replace('\\','')]
 if old!=p['master']:
  assert old=='DFFHQNx1_ASAP7_75t_R' and p['master']=='DFFHQNx2_ASAP7_75t_R'
  resize.append(dict(name=p['name'],source_master=old,planned_master=p['master']))
assert len(resize)==54
head=r'''# PREP ONLY: exact state-site geometry from qualified CTL source, no cycle/RTL change.
# Standard cell resizing below reuses the54 x1->x2 choices of the completed PLACE.
# Ordinary combinational sizing/buffering remains enabled. The planned FF footprints stay fixed.
uplevel #0 {
set b [ord::get_db_block]
set db [ord::get_db]
set dbu [$b getDbUnitsPerMicron]
proc ctl_ff_literal {name} {return [string map [list {\[} {[} {\]} {]}] $name]}
set actual {}
foreach i [$b getInsts] {
 if {[[$i getMaster] isSequential] && ![[$i getMaster] isBlock]} {
  set name [ctl_ff_literal [$i getName]]
  if {[dict exists $actual $name]} {error "CTL_FF_PLAN duplicate literal identity $name"}
  dict set actual $name $i
 }
}
set rows {}
foreach row [$b getRows] {dict set rows [lindex [$row getOrigin] 1] [$row getOrient]}
set expected {}
set resized 0
foreach {name wanted x y width height} {
'''
lines=[head]
for p in poses:
 assert not any(c in p['name'] for c in '{}\n\r;')
 x,y=p['ll_xy'];w,h=p['outline_um'];lines.append('{'+p['name']+'} '+p['master']+f' {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n')
lines.append(r'''} {
 set name [ctl_ff_literal $name]
 dict set expected $name 1
 if {![dict exists $actual $name]} {error "CTL_FF_PLAN missing exact source FF $name"}
 set i [dict get $actual $name]
 if {[[$i getMaster] getName] ne $wanted} {
  if {[[$i getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R" || $wanted ne "DFFHQNx2_ASAP7_75t_R"} {error "CTL_FF_PLAN unpriced master change $name"}
  $i setDoNotTouch 0
  if {![$i swapMaster [$db findMaster $wanted]]} {error "CTL_FF_PLAN ordinary x1->x2 resize failed $name"}
  incr resized
 }
 set xx [expr {round($x*$dbu)}];set yy [expr {round($y*$dbu)}]
 if {![dict exists $rows $yy]} {error "CTL_FF_PLAN no native row at $y"}
 $i setOrient [dict get $rows $yy]
 $i setLocation 0 0
 set bb [$i getBBox]
 if {([$bb xMax]-[$bb xMin]) != round($width*$dbu) || ([$bb yMax]-[$bb yMin]) != round($height*$dbu)} {error "CTL_FF_PLAN footprint mismatch $name"}
 $i setLocation [expr {$xx-[$bb xMin]}] [expr {$yy-[$bb yMin]}]
 set bb [$i getBBox]
 if {[$bb xMin] != $xx || [$bb yMin] != $yy} {error "CTL_FF_PLAN location mismatch $name"}
 $i setPlacementStatus FIRM
 # Preserve unobservable state; live DATA cells stay touchable for ordinary
 # combinational buffering. Process-local family exclusions preserve masters.
 set live 0
 foreach it [$i getITerms] {
  set mt [$it getMTerm];set n [$it getNet]
  if {$n ne "NULL" && ([$mt getSigType] eq "CLOCK" || [$mt getName] in {CLK CK clk ck})} {$n setDoNotTouch 1}
  if {[$mt getIoType] eq "OUTPUT" && $n ne "NULL" && ([llength [$n getBTerms]] || [llength [$n getITerms]]>1)} {set live 1}
 }
 $i setDoNotTouch [expr {!$live}]
}
if {[lsort [dict keys $expected]] ne [lsort [dict keys $actual]]} {error "CTL_FF_PLAN complete source FF inventory mismatch"}
puts "CTL_FF_PLAN PASS [dict size $expected] exact source FF sites, $resized ordinary x1->x2 resizes, clock/reset connectivity untouched"
}
''')
(O/'ctl_ff_repack.tcl').write_text(''.join(lines));(O/'FF_master_resize.json').write_text(json.dumps(resize,indent=1)+'\n')
with gzip.GzipFile(str(O/'repack_legal_poses.json.gz'),'wb',mtime=0) as f:f.write((O/'repack_legal_poses.json').read_bytes())
# Show only the state geometry. Ordinary logic is to reflow at the next PLACE.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
review=json.load(open(O.parent/'geom_review/ctl_production_1101/review.json'));pins=json.load(open(O.parent/'geom_review/ctl_production_1101/input/pins.json'));fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,new,title in zip(axs,[False,True],['Actual completed PLACE','PREP FF repack; ordinary logic to reflow']):
 ax.add_patch(Rectangle((0,0),371.52,371.52,fill=False,color='black'))
 for b in review['blocks']:ax.add_patch(Rectangle((b['x'],b['y']),52.296,39.96,facecolor='#c4d4e7',edgecolor='#4b7199'))
 for q in pins:ax.plot(q['x'],q['y'],'.',ms=.3,color='#d16d6d')
 xy=[p['center_xy'] if new else p['old_xy'] for p in poses];ax.scatter([p[0] for p in xy],[p[1] for p in xy],s=.25,c='#3e9b57',alpha=.45)
 ax.add_patch(Rectangle((181.4,181.4),9.04,9.04,facecolor='white',edgecolor='#cc9e00',lw=1.2))
 ax.set(xlim=(-5,376),ylim=(-5,376),aspect='equal',xlabel='x (um)',ylabel='y (um)',title=title)
fig.suptitle('CTL0ABI geometry PREP: 1794 FF sites relocated; all18768 row/site legal;54 existing physical x1→x2 sizes retained\nR2R619.11→391.61um, 1550→0 far captures; public pin p90=15.62/max149.32um; macros/taps/clock/reset unchanged\nSource/RTL/latency unchanged. Low fill and channel pricing remain open; no new P&R executed.',fontsize=10)
fig.tight_layout();fig.savefig(O/'repack_plan.png',dpi=140)
print('PREP_READY',len(poses),'FFs',len(resize),'resizes',cert['R2R']['r2r_max'])
