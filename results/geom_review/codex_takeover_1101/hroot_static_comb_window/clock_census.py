from pathlib import Path
from collections import Counter
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import os
P=Path(__file__).parent;candidate=os.environ.get('CLOCK_PREP')=='1';D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');taps=[p for p in D.pins if g.GRID_TAP_RE.match(p['name']) and p['io']=='INPUT'];bad=[];distances=[];load=Counter();special=Counter()
if candidate:
 for p in taps:
  if p['name']=='clk_t19':p['y']-=51.84
# Closest-grid geometry is the planned preCTS assignment, not an actual built clock tree.
for cid,c in D.cells.items():
 if c[0]!='S':continue
 nets=[n for n,ck in D.cell_in.get(cid,[])if ck]
 if not nets:continue
 n=nets[0];dr=D.nets[n][1]
 if dr and dr[0]=='p':root=D.pin_by_k[dr[1]]['name']
 else:root='not_direct_root'
 if not g.GRID_TAP_RE.match(root):special[root]+=1;continue
 x,y=g.ctr(c);tap=min(taps,key=lambda p:abs(x-p['x'])+abs(y-p['y']));d=abs(x-tap['x'])+abs(y-tap['y']);load[tap['name']]+=1;distances.append(d)
 if d>220:bad.append(dict(name=c[6],xy=[x,y],nearest_tap=tap['name'],tap_xy=[tap['x'],tap['y']],distance_um=round(d,4)))
res=dict(scope='STATIC current actual preCTS clock classification; no CTS/tree/timing or source/parent qualification',actual_clock_cells=g.clock_metrics(D)['clock_cells'],candidate_clkt19_dy_um=-51.84 if candidate else 0,grid_taps=len(taps),grid_assigned_sinks=sum(load.values()),special_direct_roots=dict(special),grid_loads=dict(load),grid_max_load=max(load.values()),nearest_grid_max_um=round(max(distances),4),nearest_grid_over220=len(bad),nearest_grid_worst=sorted(bad,key=lambda z:-z['distance_um'])[:12])
(P/('clock_candidate_PREP.json' if candidate else 'clock_census.json')).write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in ['grid_loads','nearest_grid_worst']});print(res['nearest_grid_worst'][:2])
