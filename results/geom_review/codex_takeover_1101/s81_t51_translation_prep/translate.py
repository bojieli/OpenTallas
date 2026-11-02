from pathlib import Path
import sys,json,re
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;S=Path('/home/ubuntu/coord/tmp/codex-s81-wavefail-2035/t51_current');D=g.Design(str(S/'geom.tsv'));original=dict(D.cells);land=json.load(open(S/'land_slots.json'));guard=json.load(open(S/'face_guard.json'));lr=g.land_ring_captures(D,land,guard);assert not lr['errors'];out=[]
for label,dy,dx in [('ft2_ring_data_up198p72',198.72,0),('ft2_ring_data_up198p72_stage0_up69p12_ft6_stage2_left11p934',198.72,-11.934)]:
 D.cells=dict(original);moved=[];counts={}
 for i,c in list(D.cells.items()):
  if c[0]!='S':continue
  n=c[6].replace(chr(92),'');sx,sy=0,0
  if n.startswith('u_bound.u_cland_ft2_i/') and 17.28<=g.ctr(c)[0]<=128.22 and 935.82<=g.ctr(c)[1]<=961.74:sy=dy;family='ft2_ring_band_FFs'
  elif dx and n.startswith('u_bound.u_ft_ft2_o_0/'):sy=69.12;family='ft2_stage0'
  elif dx and n.startswith('u_bound.u_ft_ft6_o_2/'):sx=dx;family='ft6_stage2'
  else:continue
  cc=list(c);cc[2]+=sx;cc[4]+=sx;cc[3]+=sy;cc[5]+=sy;D.cells[i]=tuple(cc);moved.append(dict(name=c[6],master=c[1],old=list(g.ctr(c)),new=list(g.ctr(cc)),family=family));counts[family]=counts.get(family,0)+1
 bad=[];r=g.r2r_metrics(D,capture_pairs=bad);ck=g.clock_metrics(D);pm=g.pin_reg_metrics(D,re.compile(g.STRAP_RE_DEFAULT),frozenset(ck['tap_sinks'])|frozenset(lr['clock_exports']),lr['caps']);ce=g.clock_entry_metrics(D,ck)
 # Exact all-slot pin distance, retaining sourceguard ring-membership, not nearest-register semantics.
 ring=[]
 for p in D.pins:
  if not p['name'].startswith('ft2_i['):continue
  ids=lr['caps'].get(p['name']);assert ids
  ds=[abs(g.ctr(D.cells[i])[0]-p['x'])+abs(g.ctr(D.cells[i])[1]-p['y'])for i in ids];ring.append(dict(pin=p['name'],slots=len(ids),max_um=max(ds),min_um=min(ds)))
 out.append(dict(variant=label,scope='STATIC FF-centre translation only; source/publicpins/clocks/counts/cycles unchanged; no legalrows/TAP/occupancy/PG/phase/native qualification',moved_counts=counts,r2r=r,remaining_bad=bad,pin_metrics=pm,ft2_farthest_slot_max_um=max(x['max_um']for x in ring),ft2_pins=len(ring),ft2_any_slot_over150=sum(x['max_um']>150for x in ring),clock_entry=ce,clock_grid_load_max=ck.get('grid_tap_sinks_max'),clock_grid_empty=ck.get('grid_taps_empty'),clock_rooted_errors=ck.get('unrooted_sinks'),moved=moved))
 print(label,counts,r,pm,'ft2max',out[-1]['ft2_farthest_slot_max_um'],ce)
(P/'whole_graph_translation_refined.json').write_text(json.dumps(out,indent=1)+'\n')
