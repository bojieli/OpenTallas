"""Fit the one reset-overreach START body without changing its clock/source/RTL/cycles."""
import json,shutil,sys
from pathlib import Path
run=Path(sys.argv[1]);src=run/'hk5_leaf2/stages';base=run/'hk5_source/reset_prep';dst=run/'hk5_source/stages_resetfit';out=run/'hk5_source/reset_fit'
shutil.copytree(src,dst);out.mkdir()
st=json.load(open(dst/'start_stages.json'));exports=json.load(open(base/'exports.json'));fixed=json.load(open(base/'fixedpoint.json'))
assert fixed['raw_Q_or_coordinate_mismatches']==0
s=next(s for s in st['stages'] if s['id']=='r91_3');old=s['rect_um'][:]
rect=[8478.486,3869.91,8482.806,3870.18]
assert abs(rect[0]/.054-round(rect[0]/.054))<1e-6 and abs(rect[1]/.27-round(rect[1]/.27))<1e-6
for other in st['stages']:
 if other['id']==s['id']:continue
 b=other['rect_um'];assert min(rect[2],b[2])-max(rect[0],b[0])<=1e-6 or min(rect[3],b[3])-max(rect[1],b[1])<=1e-6,other['id']
s['rect_um']=rect;s['clock_pin_xy_um']=rect[:2]
for row in exports['stages']:
 if row['stage']==s['id']:row['stage_xy_um']=rect[:2]
 row['hop_um']=round(sum(abs(a-b) for a,b in zip(row['stage_xy_um'],row['source']['xy_um'])),4)
exports['summary']['max_hop_um']=max(r['hop_um'] for r in exports['stages'])
exports['summary']['over_hop']=[r['stage'] for r in exports['stages'] if r['hop_um']>405]
assert not exports['summary']['over_hop']
(dst/'start_stages.json').write_text(json.dumps(st,indent=1)+'\n')
(out/'exports.json').write_text(json.dumps(exports,indent=1)+'\n')
report=dict(verdict='PASS',reset_max_hop_um=exports['summary']['max_hop_um'],reset_over405=0,
 selected_type_sources=fixed['selected_type_raw_sources'],raw_Q_coordinate_mismatches=fixed['raw_Q_or_coordinate_mismatches'],
 original_failure=str(base/'fixedpoint.json'),stage='r91_3',old_rect_um=old,new_rect_um=rect,
 delta_um=[round(a-b,3) for a,b in zip(rect[:2],old[:2])],source_topology_change=False,clock_source_change=False,added_cycles=0,
 geometry='native .054 site/.27 row, no other START body overlap; four corners SiteMap legal; actual packed bodies/phase remain NOT RUN')
(out/'repair.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
