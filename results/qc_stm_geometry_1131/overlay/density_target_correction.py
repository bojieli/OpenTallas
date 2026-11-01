from pathlib import Path
import json,gzip,math,re,collections
b=Path('/srv/opentallas-scratch/claude/wt/codex-qc-tload-protocol-1131/results/qc_stm_geometry_1131');o=b/'overlay';q=json.load(gzip.open(b/'private_proposal_v2.json.gz'));groups=q['clock_assignments'];manifest=json.load(gzip.open(o/'native_export_launch_manifest.json.gz'));pub=next(x for x in manifest['exports'] if x['data_port']=='b_tw_data_ctl_o');names=[x['last_native_launch_FF'] for x in sorted(pub['bits'],key=lambda x:x['bit'])];assert len(names)==2104
r=q['N_publication_box'];nx=math.ceil(math.sqrt(len(names)*(r[2]-r[0])/(r[3]-r[1])));ny=math.ceil(len(names)/nx);loc={}
for i,n in enumerate(names):
 x=r[0]+.54+(r[2]-r[0]-1.08)*(i%nx)/(nx-1);y=r[1]+.135+(r[3]-r[1]-.27)*(i//nx)/(ny-1);loc[n]=[x,y]
rows=[[x,y,1] for x,y in loc.values()];delta=[]
for name,z in groups.items():
 keep=[n for n in z['actual_named_local_FFs'] if n not in loc];moved=[n for n in z['actual_named_local_FFs'] if n in loc]
 if keep:
  box=z['estimated_consumer_bbox_um'];rows.append([(box[0]+box[2])/2,(box[1]+box[3])/2,len(keep)])
 if moved:delta.append({'advisory_group':name,'before_bbox':z['estimated_consumer_bbox_um'],'moved_named_FFs':moved,'after_existing_semantic_window':r,'remaining_unchanged_count':len(keep)})
assert sum(x[2] for x in rows)==52609
old=json.load(open(o/'native_sink_estimate.json'));(o/'native_sink_estimate_degenerate_FAIL.json').write_text(json.dumps(old,indent=1)+'\n');old['bins']=rows;old['note']='Only2104 exact native b_tw publication launch FFs uniformly distributed by actual bit order inside ALREADY DECLARED whole-cell N_publication window. All other semantic geometry unchanged. Native identity/clock not reassigned; estimated planning ONLY.';(o/'native_sink_estimate.json').write_text(json.dumps(old,indent=1)+'\n')
with gzip.open(o/'density_membership_delta.json.gz','wt') as f:json.dump({'scope':'explicit target-window planning correction ONLY','count':2104,'native_total':52609,'no_duplicate_FF':True,'native_clock_connections_changed':False,'clock_endpoints_changed':False,'physical_cell_bbox':[1.08,.27],'existing_window':r,'grid':[nx,ny],'membership_delta':delta,'per_named_FF_estimated_centers':loc},f,indent=1)
print('CORRECTED',len(names),'actualFF; total',sum(x[2] for x in rows),'bins',len(rows),'grid',nx,ny)
