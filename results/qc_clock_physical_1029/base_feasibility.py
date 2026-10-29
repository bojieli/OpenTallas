"""Diagnostic lower bound: can each fixed real clock base reach PG-clear M8?
No topology/routing, no materialization, no adoption. Excludes other top clock
routes/power towers, so FAIL proves existing local access needs repair.
"""
import argparse,json
from pathlib import Path
import fixed_tree as F

def main():
 a=argparse.ArgumentParser();a.add_argument('--tree',required=True);a.add_argument('--netlist',required=True);a.add_argument('--plan',required=True);a.add_argument('--lef',required=True);a.add_argument('--out',required=True);o=a.parse_args()
 tree=json.loads(Path(o.tree).read_text());cells,nets=F.clock_graph(Path(o.netlist).read_text(),tree)
 access={};lef=Path(o.lef).read_text()
 for master in {c['lib'] for c in cells.values()}:
  size,access[master]=F.lef_access(lef,master)
  for c in cells.values():
   if c['lib']==master:c['w']=size[0]
 P=F.DI.load_plan(o.plan);w,_,host=F.access_windows(P,cells,nets,access,8.64);cols=F.clock_column_windows(w,nets)
 pin_net={}
 for n in nets:
  if not n['drv'].startswith('port:'):pin_net[(n['drv'],'Y')]=n['name']
  pin_net.update({(ld,'A'):n['name'] for ld in n['loads'] if not ld.startswith('port:')})
 nd=dict(width=.08,space=.32,rf=.5,cf=1.15);r=F.C128.TrackRouter(nd,'VSS',F.DCM.DEFAULT_TRACKS,8.64)
 r.reserve(F.C128.pg_shapes(F.DI.pg_rects(P,F.C128.pg_grid(P))));bad=[]
 for (cell,pin),(x,y,lo,hi) in w.items():
  c,mode,e=r.place('M8',y,x-.08,x+.08,pin_net[(cell,pin)],keep=(lo,hi),dry=True)
  if c is None:bad.append(dict(cell=cell,pin=pin,net=pin_net[(cell,pin)],base_xy_um=[x,y],window_um=[lo,hi]))
 out=dict(status='FAIL' if bad else 'PASS_LOWER_BOUND_ONLY',physical_route=False,pins=len(w),no_pg_clear_m8=len(bad),host=host,column_windows=cols,failures=bad)
 Path(o.out).write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k!='failures'})
if __name__=='__main__':main()
