"""Emit real START source with explicit perimeter stage rows and unchanged clock cells."""
import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251');O=R/'reset_wave3';O.mkdir(exist_ok=True);Q=Path('/srv/opentallas-scratch2/claude/codex-qc-1029')
sys.path.insert(0,str(R/'srcf4/tools/die_plan'))
import start_stage_emit as E,schema as S,die_trial as D
bind=json.load(open(R/'perimeter1/bind.json'));meta=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-start-provider-1029/actual26/proof/tap_arrivals_TT.json'))
site=D.SiteMap(S.Plan(S.load(Q/'physical_event/plan_start_native_h800.json')))
over=json.load(open(R/'perimeter1/stage_placement_overrides.json'));st=E.stages_of(bind)
order=iter(sorted(st,key=lambda q:(len(st[q]),st[q])));original=E.place_stage
placed={}
def placer(xy,nf,rows,site=None,W=None,H=None):
 region=next(order);r=bind['regions'][region]
 oldnf=E.stage_flops(r,bind.get('root_settle_cycles',64) if r.get('parent') is None else None)
 cols=min(oldnf,4);nr=(nf+cols-1)//cols;w=cols*E.FLOP_W_UM
 points=([over[region]['anchor_xy_um']] if region in over else
         [[xy[0]+E.CLK_CELL_W_UM+E.GAP_UM,xy[1]],[xy[0]-E.GAP_UM-w,xy[1]]])
 for k in range(40):
  for dy in ([0] if k==0 else [k*.27,-k*.27]):
   for q in points:
    x,y=q[0],round(q[1]+dy,6);rect=[x,y,round(x+w,6),round(y+nr*.27,6)]
    if min(x,y)<0 or rect[2]>W or rect[3]>H:continue
    if not all(rows.free(rect[0],rect[2],round(y+i*.27,6)) for i in range(nr)):continue
    if not all(site.legal(v) for v in [(rect[0],rect[1]),(rect[0],rect[3]),(rect[2],rect[1]),(rect[2],rect[3])]):continue
    for i in range(1,nr):rows.add(rect[0],rect[2],round(y+i*.27,6))
    placed[region]=rect;return rect
 raise ValueError('actual multirow reset stage cannot fit '+region)
E.place_stage=placer
cd=Q/'baseline26/trial26/clock'
doc,sv,verilog,tcl=E.emit(bind,meta,(cd/'ctree.v').read_text(),(cd/'ctree.tcl').read_text(),site,(site.W,site.H),path_encoding='base36',reset_wave=True)
doc.update(scope='native RTL clocks; new explicit perimeter stage sites; all mapped cells/load/extraction still required',placement_override_count=len(over),all_stage_multirow_count=len(placed),max_ff_columns=4)
cells,cxy=E.ctree_cells(verilog,tcl);driver={v[2]:k for k,v in cells.items()}
for s in doc['stages']:
 s['actual_clock_driver']=driver.get(s['clock_net'])
 if s['actual_clock_driver'] is not None:
  xy=cxy[s['actual_clock_driver']];s['clock_stub_manhattan_um']=sum(abs(a-b) for a,b in zip(s['clock_pin_xy_um'],xy))
 s['placement_scope']='explicit perimeter row' if s['region'] in over else 'original node-adjacent row'
# Preserve every actual tree driver's original location, cell and net tuple.
oldcells,oldxy=E.ctree_cells((cd/'ctree.v').read_text(),(cd/'ctree.tcl').read_text());assert cells==oldcells and cxy==oldxy
out=O/'emitted';out.mkdir(exist_ok=True)
for name,obj in [('start_stages.json',json.dumps(doc,indent=1)),('start_stages.sv',sv),('ctree.v',verilog),('ctree.tcl',tcl)]: (out/name).write_text(obj)
print(json.dumps(dict(counts=doc['counts'],explicit_perimeter=len(over),all_stage_multirow_count=len(placed),max_actual_clock_stub_um=max(s.get('clock_stub_manhattan_um',0) for s in doc['stages']),clock_cells_byteidentical=True)),flush=True)
