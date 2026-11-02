"""Price added macro-free streets from actual native row PG phase, not new-PG closure."""
import csv,json,re,hashlib,collections
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');tracks={q['layer']:q for q in json.load(open(C/'tracks.json'))['tracks']};pg=list(csv.DictReader(open(C/'pg_boxes.csv')));Y0,Y1=4320,12960;ts={l:np.array([y for y in tracks[l]['Y'] if Y0<=y<Y1]) for l in ['M2','M4']};offset={};start=0
for l,t in ts.items():offset[l]=start;start+=len(t)
events=collections.defaultdict(list);rects=0
for q in pg:
 if q['kind']=='metal':ls=[q['layer']]
 else:
  pairs=re.findall(r'VIA([1-9])([1-9])',q['via']) or re.findall(r'via([1-9])_([1-9])_',q['via']);assert len(pairs)==1,q['via'];ls=['M'+s for s in pairs[0]]
 for l in ls:
  if l not in ts:continue
  margin=27 if l=='M2' else 36;x0,y0,x1,y1=[int(q[k]) for k in ['x0_dbu','y0_dbu','x1_dbu','y1_dbu']];x0-=margin;x1+=margin;y0-=margin;y1+=margin;a=int(np.searchsorted(ts[l],y0,'left'));b=int(np.searchsorted(ts[l],y1,'right'))
  if a==b:continue
  a+=offset[l];b+=offset[l];events[x0].append((a,b,1));events[x1+1].append((a,b,-1));rects+=1
counts=np.zeros(start,dtype=int);segments=[];last=None
for x,updates in sorted(events.items()):
 if last is not None and x>4320 and last<246240:segments.append([max(last,4320),min(x,246240),int(np.sum(counts==0))*.75])
 for a,b,v in updates:counts[a:b]+=v
 last=x
segments=[q for q in segments if q[0]<q[1]]
def cap_at(x):return next(q[2] for q in segments if q[0]<=x<q[1])
old=json.load(open(O.parent/'kv_ctl_compact250x285_native_FP_1102/channel_model_minmove_PREP.json'));cuts=[]
for q in old['capacity_cuts']:
 if q['direction']!='H':continue
 x=q['cut_um']*1000
 if not 4320<x<246240:continue
 add=2*cap_at(x);cuts.append(dict(original_local_cut_um=q['cut_um'],new_same_global_cut_um=round(q['cut_um']-8.64,3),original_native_derated_tracks=q['remaining_derated_tracks'],predicted_added_17p28um_tracks=add,predicted_total_derated_tracks=q['remaining_derated_tracks']+add,original_model_net_boxes=q['net_box_crossings'],same_netbox_capacity_ratio=q['net_box_crossings']/(q['remaining_derated_tracks']+add)))
r=dict(status='PHASE_DERIVED_PG_EDGE_PRICE_NOT_NEW_NATIVE_PG_OR_ROUTE',actual_sample_um=[4.32,12.96],new_added_macro_free_street_height_um=17.28,native_sample_raw_tracks={k:len(v) for k,v in ts.items()},native_obstacle_rectangles=rects,actual_same_phase_added_tracks_range=[2*min(q[2] for q in segments),2*max(q[2] for q in segments)],worst_same_netbox_whole_cut_ratio=max(q['same_netbox_capacity_ratio'] for q in cuts),cuts=cuts,PG_readset_sha256=hashlib.sha256((C/'pg_boxes.csv').read_bytes()).hexdigest(),track_readset_sha256=hashlib.sha256((C/'tracks.json').read_bytes()).hexdigest(),limits=['Uses actual macro-free PG strip at exact 8.64um phase; expected repeated row PG in enlarged inter-SRAM streets, not new native PG','Keeps original net boxes to isolate capacity; new pin/cone placement can change demand','New macro PG connections, rows/TAP inventory and signal/clock via coupling require normal native FP and actual placement','No floorplan/placement/signoff permission or source/parent adoption'])
(O/'edge_capacity_PREP.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['cuts','limits']},indent=2))
