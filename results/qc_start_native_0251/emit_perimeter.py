"""Emit real START source with explicit perimeter stage rows and unchanged clock cells."""
import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251');O=R/'perimeter1';Q=Path('/srv/opentallas-scratch2/claude/codex-qc-1029')
sys.path.insert(0,str(R/'src407/tools/die_plan'))
import start_stage_emit as E,schema as S,die_trial as D
bind=json.load(open(O/'bind.json'));meta=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-start-provider-1029/actual26/proof/tap_arrivals_TT.json'))
site=D.SiteMap(S.Plan(S.load(Q/'physical_event/plan_start_native_h800.json')))
over=json.load(open(O/'stage_placement_overrides.json'));st=E.stages_of(bind)
order=iter(sorted(st,key=lambda q:(len(st[q]),st[q])));original=E.place_stage
placed={}
def placer(xy,nf,rows,site=None,W=None,H=None):
 region=next(order)
 if region not in over:return original(xy,nf,rows,site,W,H)
 q=over[region]['anchor_xy_um'];w=nf*E.FLOP_W_UM
 for dy in [0,.27,-.27,.54,-.54,.81,-.81,1.08,-1.08]:
  rect=[q[0],round(q[1]+dy,6),round(q[0]+w,6),round(q[1]+dy+.27,6)]
  if rows.free(rect[0],rect[2],rect[1]) and all(site.legal(v) for v in [(rect[0],rect[1]),(rect[2],rect[3])]):
   placed[region]=rect;return rect
 raise ValueError('explicit perimeter stage actual row conflict '+region)
E.place_stage=placer
cd=Q/'baseline26/trial26/clock'
doc,sv,verilog,tcl=E.emit(bind,meta,(cd/'ctree.v').read_text(),(cd/'ctree.tcl').read_text(),site,(site.W,site.H),path_encoding='base36')
doc.update(scope='native RTL clocks; new explicit perimeter stage sites; all mapped cells/load/extraction still required',placement_override_count=len(placed))
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
print(json.dumps(dict(counts=doc['counts'],explicit_perimeter=len(placed),max_actual_clock_stub_um=max(s.get('clock_stub_manhattan_um',0) for s in doc['stages']),clock_cells_byteidentical=True)),flush=True)
