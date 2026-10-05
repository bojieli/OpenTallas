#!/usr/bin/env python3
"""Native DBU cut capacities from existing read-only ODB text exports.
No flow, netlist, RTL or database mutation. Unknown via layer blocks every plane.
"""
import argparse,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_l20_hierarchical_reservation_20261002'
def merge(xs):
 result=[]
 for lo,hi in sorted(xs):
  if result and lo<=result[-1][1]:result[-1][1]=max(hi,result[-1][1])
  else:result.append([lo,hi])
 return result
def free(tracks,intervals):
 j=0;n=0
 for t in tracks:
  while j<len(intervals) and intervals[j][1]<t:j+=1
  if j==len(intervals) or t<intervals[j][0]:n+=1
 return n
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--geometry-dir',type=Path,required=True);a=ap.parse_args();result={}
 for name in ['DS','Qwen']:
  p=a.geometry_dir/(name+'_geometry.json.gz');b=p.read_bytes();g=json.loads(gzip.decompress(b));grid=json.loads((OUT/'grid_inputs'/(name+'_grid.json')).read_bytes());dbu=g['dbu_per_um'];assert dbu==1000
  layers={r['name']:r for r in grid['layers']};planes={r['layer']:r for r in grid['grids']}
  obs={l:[] for l in layers};halo_policy=4*dbu
  macros=[]
  for m in g['macro_instances']:
   assert m['orientation']=='R0';ox,oy=m['origin'];master=grid['macro_master_OBS'][m['master']]
   for o in master['OBS']:
    if o['layer'] not in obs:continue
    x0,y0,x1,y1=o['bbox'];obs[o['layer']].append([ox+x0-halo_policy,oy+y0-halo_policy,ox+x1+halo_policy,oy+y1+halo_policy])
   macros.append({k:m[k] for k in ['name','master','origin','bbox','orientation']})
  pdn={l:[] for l in layers};unknown=0
  for net in g['power_special_shapes']:
   for r in net['shapes']:
    target=[r['layer']] if r['layer'] in layers else list(layers)
    if r['layer'] not in layers:unknown+=1
    # Margin covers half maximum routing/via metal width. Via bbox with
    # missing layer identity conservatively obstructs every routing plane.
    x0,y0,x1,y1=r['bbox'];bbox=[x0-50,y0-50,x1+50,y1+50]
    for l in target:pdn[l].append(bbox)
  cuts=[]
  for l,info in layers.items():
   if not l.startswith('M') or l=='M1':continue
   horiz=info['direction']=='HORIZONTAL';axis='Y' if horiz else 'X';idx=0 if horiz else 1
   tracks=sorted({start+i*step for start,count,step in planes[l][axis] for i in range(count)})
   # Actual macro center and edge cuts plus die center; topology is explicit,
   # never nominal height/pitch multiplied without blockages.
   coords=sorted({g['die'][idx+2]//2}|{m['bbox'][idx] for m in macros}|{m['bbox'][idx+2] for m in macros}|{(m['bbox'][idx]+m['bbox'][idx+2])//2 for m in macros})
   vals=[]
   for c in coords:
    def intervals(rs):return merge([[r[1 if horiz else 0],r[3 if horiz else 2]] for r in rs if r[idx]<=c<=r[idx+2]])
    mo=intervals(obs[l]);allblocked=intervals(obs[l]+pdn[l]);n=free(tracks,allblocked)
    vals.append({'cut_DBU':c,'macro_OBS_halo_blocked_tracks':len(tracks)-free(tracks,mo),'all_OBS_halo_PDN_via_blocked_tracks':len(tracks)-n,'free_tracks':n,'policy50pct_signal_tracks':n//2})
   cuts.append({'layer':l,'direction':info['direction'],'unique_track_count':len(tracks),'grid_array_duplicates_removed':True,'minimum_sampled_cut_free_tracks':min(r['free_tracks'] for r in vals),'cut_records':vals})
  rows=sum(r['count']*math.prod(r['site_size']) for r in g['rows'])/dbu**2
  result[name]={'ODB_sha256':g['ODB_sha256'],'export_sha256':hashlib.sha256(b).hexdigest(),'grid_sha256':hashlib.sha256((OUT/'grid_inputs'/(name+'_grid.json')).read_bytes()).hexdigest(),'dbu_per_um':dbu,'die_bbox_DBU':g['die'],'macro_count':len(macros),'translated_macro_origins_and_boxes_DBU':macros,'macro_OBS_counts_by_master':{k:len(v['OBS']) for k,v in grid['macro_master_OBS'].items()},'macro_halo_policy_DBU':halo_policy,'stored_database_halos':[r['halo'] for r in grid['macro_halos'] if r['halo'] is not None],'remaining_ROW_site_area_um2':rows,'unknown_layer_PDN_via_count_conservatively_blocked_all_planes':unknown,'native_cut_capacity':cuts,'claim':'Guaranteed sampled-cut counts after conservative exclusions, not a routing sufficiency proof. Original mapped parent FFs are unplaced; repairedTC not qualified. Dedicated new serviceband must reserve PDN/vias before physical admission.'}
  del g,pdn,obs,b
 out={'schema':'opentallas.actual-grid-OBS-cut-capacity.v1','models':result,'historical_macro_timing_qualification_transfer':False,'engine_build_admitted':False,'no_OpenROAD_invocation':True,'no_live_job_polled':True}
 p=OUT/'actual_grid_usable_capacity.json';b=(json.dumps(out,indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
 print(json.dumps({n:{'macro_count':v['macro_count'],'ROW_um2':v['remaining_ROW_site_area_um2'],'min_free_tracks':{l['layer']:l['minimum_sampled_cut_free_tracks'] for l in v['native_cut_capacity']}} for n,v in result.items()}))
if __name__=='__main__':main()
