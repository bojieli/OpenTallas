import json,math,re
from pathlib import Path
p=Path(__file__).parent
raw=json.loads((p/'source_plan.json').read_text());side=json.loads((p/'source_sidecar.json').read_text())
L=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
xy=lambda a,b,f:[round(a[0]+(b[0]-a[0])*f,3),round(a[1]+(b[1]-a[1])*f,3)]
proposal={'types':{}};reports={}
for tn in ['hd_st_k5','hd_st_turn','hd_spn','hd_spn_end']:
 t=raw['partition_types'][tn]; c=t['clock'];info=side['collector']['types'][tn];pins={r['name']:r['xy_um'] for r in c['landing_contract']['pins']}
 centers={r['name']:[(r['band']['rect_um'][0]+r['band']['rect_um'][2])/2,(r['band']['rect_um'][1]+r['band']['rect_um'][3])/2] for r in info['local_sources']}
 # Aggregate stage 1 at source centroid, remaining already-budgeted stages lead to tree-bus output.
 center=[sum(a[k] for a in centers.values())/len(centers) for k in range(2)]
 tree=info['mask']['tree_bus'];end=pins['cland_up_ready_'+tree];depth=info['local_registered_depth']
 anchors={'u_cland_agg_'+str(k):xy(center,end,(k-1)/(depth-1)) for k in range(1,depth)}
 targets={'agg':center,**{r['bus']:pins['cland_up_ready_'+r['bus']] for r in info['up_buses'] if r['carries']=='local'}}
 stages={};site_consumers={};status_records={}
 for tgt,at in targets.items():
  n=max(1,math.ceil(max(L(src,at) for src in centers.values())/225)-1)
  stages[tgt]={};status_records[tgt]=n
  for ring,src in centers.items():
   path=[xy(src,at,(k+1)/(n+1)) for k in range(n)]
   stages[tgt][ring]=[{'xy_um':q} for q in path]
   for k,q in enumerate(path):site_consumers[f'u_cland_sin_{tgt}_{ring}_{k}']=q
 site_consumers.update(anchors)
 for r in info['up_buses']:site_consumers['u_cland_up_'+r['bus']]=pins['cland_up_ready_'+r['bus']]
 origin=c['start_capture_um'];rdepth=max(1,math.ceil(max(L(origin,q) for q in centers.values())/225)-1)
 reader={'depth':rdepth,'origin_rect_um':[origin[0]-8.64,origin[1]-8.64,origin[0]+8.64,origin[1]+8.64], 'branches':{b:{'stages':[{'xy_um':xy(origin,q,(k+1)/(rdepth+1)),'raw_reset':'PICK'} for k in range(rdepth)]} for b,q in centers.items()}}
 outs={b:pins['cland_fstart_out_'+b] for b in info['mask']['outputs']}
 wdepth=max(1,math.ceil(max(L(origin,q) for q in outs.values())/225)-1)
 writer={'depth':wdepth,'branches':{b:{'stages':[{'xy_um':xy(origin,q,(k+1)/(wdepth+1)),'raw_reset':'PICK'} for k in range(wdepth)]} for b,q in outs.items()}}
 rtl=(p/(t['module']+'.sv')).read_text()
 mon=re.search(r'u_cland_agg_1\s*\([^;]*?\.rst_n\((\w+)\)',rtl,re.S).group(1)
 parent=re.search(r'ot_dp_rrelay\s+\w+\s*\([^;]*?\.d\((\w+)\)[^;]*?\.q\('+mon+r'\)',rtl,re.S).group(1)
 raws=[]
 for m in re.finditer(r'ot_dp_rrelay\s+(\w+)\s*\([^;]*?\.q\((rst_rl_\d+)\)\);[^\n]*depth (\d+) @ \(([^,]+), ([^)]+)\)',rtl):
  inst,net,d,x,y=m.groups();raws.append((net,int(d),[float(x),float(y)]))
 need=next(q[1] for q in raws if q[0]==parent)
 copies=[];reset_max=0
 for i,(inst,q) in enumerate(site_consumers.items()):
  pool=[r for r in raws if r[1]==need]
  r=min(pool,key=lambda r:L(r[2],q));copy_xy=xy(r[2],q,.5) if L(r[2],q)>350 else q
  reset_max=max(reset_max,L(r[2],copy_xy),L(copy_xy,q))
  copies.append({'name':f'geo_{i}','raw':r[0],'xy_um':copy_xy,'consumers':[inst]})
 # Origin/fstart reset also uses a local same-cycle copy; raw depth may differ from monitor.
 origin_reset=re.search(r'u_cland_origin\s*\([^;]*?\.rst_raw_n\((\w+)\)',rtl,re.S).group(1)
 origin_parent=re.search(r'ot_dp_rrelay\s+\w+\s*\([^;]*?\.d\((\w+)\)[^;]*?\.q\('+origin_reset+r'\)',rtl,re.S).group(1)
 ond=next(r[1] for r in raws if r[0]==origin_parent)
 r=min([r for r in raws if r[1]==ond],key=lambda r:L(r[2],origin))
 copies.append({'name':'origin_geo','raw':r[0],'xy_um':origin,'consumers':['u_cland_origin']})
 edit={'set':{'clock.landing_reader_start':reader,'clock.landing_writer_start':writer,'clock.landing_status_input_stages':stages,'clock.landing_status_anchors':anchors,'clock.landing_local_resets':copies},'auto_sink_sites':True,'ft_order_explicit':True}
 proposal['types'][tn]=edit
 reports[tn]={'status_input_extra_cycles':status_records,'reader_start_boot_extra_cycles':rdepth,'writer_start_boot_extra_cycles':wdepth,'steady_data_cycles_added':0,'new_status_flops':sum(len(v)*status_records[k]*2 for k,v in stages.items()),'reset_copy_flops':len(copies),'reset_hop_max_est_um':round(reset_max,3),'status_chain_hop_est_um':225,'start_chain_hop_est_um':225,'raw_pick_required':True,'status':'PROPOSAL_ESTIMATE_ONLY_NOT_BUILT'}
(p/'turn_overlay.json').write_text(json.dumps({'types':{'hd_st_turn':proposal['types']['hd_st_turn']}},indent=1)+'\n');(p/'residual_overlay.json').write_text(json.dumps(proposal,indent=1)+'\n');(p/'residual_estimate.json').write_text(json.dumps(reports,indent=1)+'\n');print(json.dumps(reports,indent=1))
