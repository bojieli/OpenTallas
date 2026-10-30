import json,gzip,re,sys,collections
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-kv-sd-1030');d=json.load(open(r/'sd_r52_split_txup_full_xy_inventory.json'));by={z['instance']:z for z in d};proposal=[]
data=set(json.load(open(r/'phy_split_data_ff_rows.json'))['positions'])
for n,z in by.items():
 if 'u_bound.u_core.u_fdi_cdc.' not in n or n in data:continue
 # Actual c_rx_v follows its data bank; no moving/retiming of data or declared stage counts.
 if '.c_rx_v' in n:y=675.0
 elif '.u_crs.' in n:y=285.12
 elif '.u_prs.' in n:y=505.44
 elif '.up_s' in n:y=450.36
 elif '.u_tx.' in n:y=285.12
 elif '.u_rx.' in n:y=650.16 if z['clock_net']=='clk' else 675.0
 elif '.p_' in n:y=285.12
 else:y=505.44
 old=z['xy_um'];z['xy_um']=[1872.72,y];z['basis']='held full current native control peer-group anchor'
 proposal.append({'instance':n,'old':old,'new':z['xy_um'],'clock':z['clock_net']})
pairs=json.load(gzip.open(r/'sd_r52_all_ff_related_pairs.json.gz'));bad=[];cnt=0;mx=0;types=collections.Counter()
for c in pairs['captures']:
 if c['capture'] not in by:continue
 C=by[c['capture']]
 for i in c['source_indices']:
  S=by[pairs['sources'][i]];dst=abs(S['xy_um'][0]-C['xy_um'][0])+abs(S['xy_um'][1]-C['xy_um'][1]);cnt+=1;mx=max(mx,dst)
  if dst>405+1e-6:
   types[S['instance'].split('/')[0]]+=1
   bad.append({'source':S['instance'],'capture':C['instance'],'L1_um':dst,'source_xy':S['xy_um'],'capture_xy':C['xy_um'],'source_basis':S['basis'],'capture_basis':C['basis']})
bad.sort(key=lambda x:-x['L1_um']);sys.path.insert(0,str(r/'src/tools/die_plan'));import taps
p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'));ts=[(x['name'],*x['xy']) for x in p['partition_types']['kv3_sys_SD']['clock']['taps']];ss=[z['xy_um']+[1] for z in d if z['clock_net']=='clk'];lo,fa,asg=taps.assign(ts,ss,2400,400,max_distance_um=400)
report={'qualified':False,'actual_control_FFs_anchored':len(proposal),'moves':proposal,'actual_FFpair_count':cnt,'over405':len(bad),'maxL1_um':mx,'failing_sources':dict(types),'worst':bad[:50],'tap_capacity':[{'root':t[0],'load':n,'maxL1':f} for t,n,f in zip(ts,lo,fa)],'primary_over220':sum(abs(s[0]-ts[j][1])+abs(s[1]-ts[j][2])>220 for s,j in zip(ss,asg)),'scope':'Only named anchor model; control anchors NOT cell-packing/legalization. Actual SYNTH graph is before mandatory local physical reset tap rebinding. All failures retained. No source/control cycles or pins changed.'}
(r/'sd_r52_control_anchors_prep.json').write_text(json.dumps(report,indent=2));(r/'sd_r52_control_full_xy_inventory.json').write_text(json.dumps(d,indent=1));print(json.dumps({k:v for k,v in report.items() if k not in ['moves','worst']},indent=2));print(json.dumps(bad[:8],indent=1))
