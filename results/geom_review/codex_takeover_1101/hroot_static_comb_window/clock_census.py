from pathlib import Path
from collections import Counter
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import os
P=Path(__file__).parent;candidate=os.environ.get('CLOCK_PREP')=='1';D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');taps=[p for p in D.pins if g.GRID_TAP_RE.match(p['name']) and p['io']=='INPUT'];
if os.environ.get('ENDPOINT_PREP')=='1':
 rows=json.load(open(P/'current_graph_lp_margin391.json'))[0];byname={c[6]:k for k,c in D.cells.items()}
 for cid,c in list(D.cells.items()):
  cc=list(c)
  if 'u_cland_i_seq__g_fan_N__u_fan_kc/' in c[6]:cc[3]-=146.88;cc[5]-=146.88
  elif 'u_cland_i_fch_pc_Q_N_q/' in c[6] or 'u_cland_i_kvpc_Q_N_pc__fo/' in c[6]:cc[2]+=172.8;cc[4]+=172.8
  D.cells[cid]=tuple(cc)
 for z in rows['targets']:
  cid=byname[z['name']];c=list(D.cells[cid]);x,y=g.ctr(c);dx,dy=z['new'][0]-x,z['new'][1]-y;c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[cid]=tuple(c)
bad=[];distances=[];load=Counter();special=Counter()
if candidate:
 for p in taps:
  if p['name']=='clk_t19':p['y']-=51.84
  if os.environ.get('CLOCK20_PREP')=='1' and p['name']=='clk_t20':p['y']+=51.84
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
(P/('clock_endpoint391_PREP.json' if os.environ.get('ENDPOINT_PREP')=='1' else 'clock_candidate_PREP.json' if candidate else 'clock_census.json')).write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in ['grid_loads','nearest_grid_worst']});print(res['nearest_grid_worst'][:2])
