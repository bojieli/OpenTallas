from pathlib import Path
from collections import defaultdict,Counter
import json,math,copy
b=Path('/srv/opentallas-scratch2/claude/codex-sc974-alias-1030');o=b/'candidate';E=json.load((o/'endpoint_map.json').open())['endpoints'];old=json.load((b/'input/pins572.json').open());pins=copy.deepcopy(old['pins']);byname={p['name']:p for p in pins};masters=json.load((o/'frontier_native_masters.json').open())['masters'];caps=json.load((o/'lib_caps.json').open())['by_corner'];W,H=253.2,505.44;origin=[345.6,656.64]
PG={'M5':(4.32,2.16,.264),'M6':(4.32,2.16,.48),'M7':(8.64,4.32,.48)};tracks={'M4':(.048,.024),'M5':(.048,.024),'M6':(.064,.032),'M7':(.064,.032)}
def pg(layer,c):
 if layer not in PG:return False
 per,cen,half=PG[layer];d=(c-cen)%per;return min(d,per-d)<half-1e-9
used=defaultdict(list)
for p in pins:used[p['face'],p['layer']].append(p['x'] if p['face'] in 'NS' else p['y'])
windows={'N':(24.,80.),'E':(.192,39.),'W':(210.,276.),'S':(20.,140.)};layers={'N':['M5','M7'],'S':['M5','M7'],'E':['M4','M6'],'W':['M4','M6']}
aliasface=Counter();endpointpins=[]
for row in E:
 key=row['leaf_port'] if row['leaf_port'] in byname else row['source_bit'];base=byname[key]
 if row['new_alias']:
  face=base['face'];target=base['x'] if face in 'NS' else base['y'];lo,hi=windows[face];options=[]
  for layer in layers[face]:
   pitch,off=tracks[layer]
   for k in range(math.ceil((lo-off)/pitch),math.floor((hi-off)/pitch)+1):
    c=round(off+k*pitch,6)
    if pg(layer,c) or any(abs(c-v)<.192-1e-6 for v in used[face,layer]):continue
    options.append((abs(c-target)+(.03 if layer!=base['layer'] else 0),layer,c))
  assert options,(row,face);_,layer,c=min(options);used[face,layer].append(c)
  p=copy.deepcopy(base);p.update(name=row['private_port'],bus=row['private_port'],bit=None,layer=layer,role='one existing retained FF D endpoint per private input pin',source_bit=row['source_bit'],capture_instance=row['instance'],parent_signal=row['actual_parent_net'])
  if face in 'NS':p['x']=c
  else:p['y']=c
  pins.append(p);aliasface[face]+=1
 else:p=base
 endpointpins.append(dict(row,pin_name=p['name'],face=p['face'],layer=p['layer'],child_local_xy_um=[p['x'],p['y']],child_global_xy_um=[p['x']+origin[0],p['y']+origin[1]],native_master=masters[row['instance']],D_cap_fF={c:caps[c]['cells'][masters[row['instance']]]['D_capacitance_fF'] for c in ['tt','ff']}))
assert len(pins)==974 and len({p['name'] for p in pins})==974 and aliasface==dict(N=9,E=132,W=132,S=129),aliasface
# All original outputs are byte-identical positions/layers/names. No input FF or parent public endpoint migrates.
assert [p for p in pins if p['dir']=='out']==[p for p in old['pins'] if p['dir']=='out']
errors=[]
for p in pins:
 c=p['x'] if p['face'] in 'NS' else p['y'];pitch,off=tracks[p['layer']]
 if abs((c-off)/pitch-round((c-off)/pitch))>1e-5:errors.append([p['name'],'track'])
 if pg(p['layer'],c):errors.append([p['name'],'PG'])
 if not(0<=p['x']<=W and 0<=p['y']<=H):errors.append([p['name'],'outline'])
# New pins obey a .192um separation from every same-face/same-layer original/new pin.
for r in endpointpins:
 if not r['new_alias']:continue
 p=next(p for p in pins if p['name']==r['pin_name']);c=p['x'] if p['face'] in 'NS' else p['y']
 others=[q for q in pins if q['name']!=p['name'] and (q['face'],q['layer'])==(p['face'],p['layer'])]
 assert min(abs(c-(q['x'] if p['face'] in 'NS' else q['y'])) for q in others)>=.192-1e-6
assert not errors,errors
# Model existing parent driver neighborhoods, not FIRM placement or timing clearance.
groups=defaultdict(list)
for r in endpointpins:groups[r['actual_parent_net']].append(r)
parent_homes=[]
for net,rows in groups.items():
 face=rows[0]['face'];basekey=rows[0]['leaf_port'] if rows[0]['leaf_port'] in byname else rows[0]['source_bit'];basepin=byname[basekey];pub=basepin['parent_public']
 if face=='E' and pub['bus'] in ['x_fe_i','flt_fe_i']:
  x=608.58;delta=100. if pub['bus']=='flt_fe_i' else 24.;y=pub['y']+delta;kind='existing direct public bin capture, proposed parent-only home';publicreach=abs(x-pub['x'])+abs(y-pub['y'])
 elif face=='E':x=608.58;y=sum(r['child_global_xy_um'][1] for r in rows)/len(rows);kind='existing pd8 final parent stage, outside child east halo';publicreach=None
 elif face=='W':x=4.86;y=pub['y'];kind='existing CA-fed parent bin, proposed home';publicreach=abs(x-pub['x'])+abs(y-pub['y'])
 elif face=='N':x=sum(r['child_global_xy_um'][0] for r in rows)/len(rows);y=1167.48;kind='existing CA read/bin neighborhood above child halo; upstream chain remains unresolved';publicreach=None
 else:x=sum(r['child_global_xy_um'][0] for r in rows)/len(rows);y=651.24;kind='existing final R8/pad registered bank plus selector neighborhood below child halo; no new stage';publicreach=None
 hops=[abs(x-r['child_global_xy_um'][0])+abs(y-r['child_global_xy_um'][1]) for r in rows]
 # Existing core margin4.32; native DFFHQNx1 is1.08x.27. Homes are not certified free sites.
 row=dict(parent_signal=net,source_bits=sorted({r['source_bit'] for r in rows}),face=face,existing_driver_model=kind,parent_home_um=[x,y],pin_to_child_max_L1_um=max(hops),endpoint_count=len(rows),public_capture_reach_model_um=publicreach,source_gate_cap_unchanged_fF={c:sum(r['D_cap_fF'][c] for r in rows) for c in ['tt','ff']},status='MODEL ONLY; parent existing FF/FT/reset/clock/fixed-site census and all per-hop timing still required')
 parent_homes.append(row)
for r in endpointpins:
 home=next(g for g in parent_homes if g['parent_signal']==r['actual_parent_net'])['parent_home_um'];r['parent_to_private_pin_L1_um']=sum(abs(a-z) for a,z in zip(home,r['child_global_xy_um']))
 width=1.404 if 'DFFASR' in r['native_master'] else 1.08
 x,y=r['child_local_xy_um'];face=r['face']
 if face=='E':x=math.floor((W-4.32-width)/.054)*.054+width/2
 elif face=='W':x=4.32+width/2
 else:x=min(max(round((x-width/2)/.054)*.054+width/2,4.32+width/2),W-4.32-width/2)
 y=min(max(round((y-.135)/.27)*.27+.135,4.455),H-4.455)
 r['individual_first_FF_grid_witness_local_um']=[round(x,6),round(y,6)]
 r['individual_pin_to_FF_reach_um']=sum(abs(a-z) for a,z in zip([x,y],r['child_local_xy_um']))
 r['individual_parent_to_child_FF_L1_um']=abs(home[0]-x-origin[0])+abs(home[1]-y-origin[1])
 assert r['individual_pin_to_FF_reach_um']<=30 and r['individual_parent_to_child_FF_L1_um']<=405,(r['source_bit'],r)
 r['witness_scope']='individual row/site witness ONLY; multiple witnesses may overlap, global packing/TAP/fixed occupancy remainsOPEN'
facebudget={}
for face in 'NESW':
 rs=[r for r in endpointpins if r['face']==face];allp=[p for p in pins if p['face']==face];facebudget[face]=dict(total_private_pins=len(allp),data_input_endpoints=len(rs),extra_aliases=aliasface[face],max_parent_driver_to_pin_proxy_um=max(r['parent_to_private_pin_L1_um'] for r in rs),max_individual_parent_to_child_FF_L1_um=max(r['individual_parent_to_child_FF_L1_um'] for r in rs),max_individual_pin_FF_reach_um=max(r['individual_pin_to_FF_reach_um'] for r in rs),gate_cap_fF={c:sum(r['D_cap_fF'][c] for r in rs) for c in ['tt','ff']},same_layer_new_pin_minsep_um=.192)
report=dict(scope='PRIVATE974 source/pin MODEL only, not physical ready or parent activation',child_outline_um=[W,H],parent_body_um=[345.6,656.64,598.8,1162.08],private_bits=974,inputs=759,outputs=215,source_ff=43058,new_ff=0,new_cycles=0,original_output_positions_frozen=215,track_PG_outline_errors=errors,per_face=facebudget,source_parent_max_gate_fanout=max(g['endpoint_count'] for g in parent_homes),parent_gate_cap_conservation='757 identical original D sinks regrouped into974privateports; aggregate gate capacitance per original parent net unchanged. New pin/wire parasitics remain unmeasured and must be charged.',public_capture_outliers=[g for g in parent_homes if (g['public_capture_reach_model_um'] or 0)>30],physical_holds=['Parent direct E/public bins and all public bouts stay parent; no migration across >150um face reach. One flt capture proposed at104.86um consumes one type p90 outlier budget, overall p90 census remains OPEN.','Child first757 DFF and215outputFF need actual retained FIRM homes, p90<=30/max150 and <=405 every actual register hop. Pin proxies leave no hidden waiver.','Child source clock tree/RC/insertion/pair-skew qualification NOT RUN; no new clock loads/domains, no old parent clock identity inheritance.','Child MAXM7/OBSmaxM7 explicit; parent17FTchains and4reset overlap reroute/source budgets remain OPEN. No route over actual OBS is assumed.','Standalone legacy QC generator RECT currently lacks M6/M7 pin shapes; review explicit layer6/7 shape extension before GEN/P&R.','Parent-hop homes are analytic neighborhoods outside child halo, not FIRM coordinates or a timing guarantee; upstream CA/R8/pad transport retained and still requires all hops.'])
(o/'pins974.json').write_text(json.dumps(dict(schema='opentallas.core_pins.v1',module='qfd_dv_s5_sc2_leaf_alias974',outline_um=[W,H],pins=pins),indent=2)+'\n');(o/'alias_pin_budget.json').write_text(json.dumps(report,indent=2)+'\n');(o/'endpoint_pin_map.json').write_text(json.dumps(endpointpins,indent=2)+'\n');(o/'parent_hop_budget.json').write_text(json.dumps(parent_homes,indent=2)+'\n');print(json.dumps(report,indent=2))
