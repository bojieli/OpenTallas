"""Render the finite source MODEL with explicit routing refusals, no EDA."""
import json,gzip,pathlib,hashlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=pathlib.Path(__file__).parent
J=json.load(open(P/'first_band_only/model.json'))
B=json.load(gzip.open(P/'first_band_only/MODEL_boxes.json.gz','rt'))
G=json.load(open(P/'pg_output/ledger.json'))
demand=max(r['demand'] for r in J['geometry']['x_cuts'])
regions=['south_belt','band','north_belt']
small=sum(G['summary'][f'{l}:via_landing:{r}']['pg_clear'] for l in ['M2','M4'] for r in regions)
full=sum(G['summary'][f'{l}:via_landing:all']['pg_clear'] for l in ['M2','M4'])
raw=json.load(gzip.open(P/'kit/inputs/raw.json.gz','rt'));m=next(iter(raw['modules'].values()))
a=json.load(open(P/'kit/allowlist.json'));netid={v['name']:int(k) for k,v in m['net_metadata'].items()}
ds={}
for n,c in m['cells'].items():
 for p,bits in c['connections'].items():
  if c['port_directions'][p]=='output':
   for bit in bits:ds.setdefault(bit,[]).append(n)
center=lambda n:((B['cells'][n]['bbox'][0]+B['cells'][n]['bbox'][2])/2,(B['cells'][n]['bbox'][1]+B['cells'][n]['bbox'][3])/2)
spans=[]
for br in a['branches']:
 drivers=ds.get(netid[br['source_net']],[])
 if len(drivers)!=1 or drivers[0] not in B['cells']:continue
 x,y=center(drivers[0]);X,Y=center(br['buffers'][0])
 dbox=B['cells'][drivers[0]]['bbox'];hbox=B['cells'][br['buffers'][0]]['bbox']
 sep=max(0,dbox[0]-hbox[2],hbox[0]-dbox[2])+max(0,dbox[1]-hbox[3],hbox[1]-dbox[3])
 spans.append(dict(source_net=br['source_net'],driver=drivers[0],first_HB=br['buffers'][0],role=br['role'],center_Manhattan_um=abs(X-x)+abs(Y-y),bbox_separation_lower_bound_um=sep))
spans.sort(key=lambda r:r['center_Manhattan_um'],reverse=True)
sourcegroups={}
for br in a['branches']:
 group=sourcegroups.setdefault(br['source_net'],dict(source_net=br['source_net'],branches=[],total_first_HB_inputs=0))
 group['branches'].append(dict(role=br['role'],first_HB=br['buffers'][0],all_HB=br['buffers'],sinks=br['sinks'],inverter=br.get('inverter')))
 group['total_first_HB_inputs']+=1
R=dict(schema='int8.fresh_source_finite_refusal.v1',status='SOURCE_MODEL_REFUSED_FOR_BUILD',
 original_firm_ECO='separate immutable refusal owner; not retried',
 first_band=dict(status='CUT_FAIL',crossing_nets=demand,optimistic_M2_M4_M6_gross=1145),
 exterior_24p84_belts=dict(status='PG_PROJECTED_CAPACITY_REFUSAL',crossing_nets=demand,M2_M4_via_clear=small,
   clock_reserve=None,new_PG_contacts=None,area_um2=2*24.84*216),
 whole_core_exterior=dict(status='UNQUALIFIED_SOURCE_GEOMETRY_ONLY',horizontal_PG_via_clear_rays=full,
   residual_before_clock_and_new_PG=full-demand,used_existing_outline=True,
   band_y_um=[55.62,73.98],south_routing_y_um=[2.16,55.62],north_routing_y_um=[73.98,127.44],
   routing_belt_area_um2=2*53.46*233.28,clock_reserve=None,new_PG_contact_deduction=None,
   signal_signal_via_DRC=None,wire_capacitance=None,min_CQ_load_domain=None,qualified=False),
 actual_source_first_HB_center_spans=spans,
 max_source_first_HB_center_span_um=max(r['center_Manhattan_um'] for r in spans),
 max_source_first_HB_bbox_separation_um=max(r['bbox_separation_lower_bound_um'] for r in spans),
 source_group_inventory=dict(groups=len(sourcegroups),branches=sum(g['total_first_HB_inputs'] for g in sourcegroups.values()),
   max_branches_per_shared_source=max(g['total_first_HB_inputs'] for g in sourcegroups.values()),
   data_branches=594,RESETN_branches=10,reset_split_branches=12,all_groups=list(sourcegroups.values())),
 next_source_ownership=dict(mechanism='Bind every first HB to actual shared source owner; partition source-owned near-pin sites, never sink-owned first-HB placement',
   source_wire_allowance='<=0.5fF TOTAL per shared source, not per branch; native contact/via/wire proof required',
   downstream='Keep HB2/HB3 and genuine RESET split inverter ownership explicit; measure full branch min/max waveform/load/RC before geometry acceptance',
   if_source_near_pin_sites_unavailable='REFUSE geometry; genuinely stronger source or different hold topology needs new native Lib whole-path budget, with real cost',
   output_legs='Price source-to-firstHB, HB-to-HB, final-to604D/RESETN endpoints separately; source affine clustering does not prove sink legs',
   clock='Fresh whole clock independently budgeted, no inherited phases',
   no_new_source_or_engine_permission=True),
 timing=dict(old_conditional_setup_headroom_not_transferred=True,seven_boundary_feedback_conditions='OPEN',
   minimum_wire_cap_292_TT_sources='OPEN, actual extraction required',complete_604_endpoint_min_max='OPEN',
   clock_early_late_waveform_pulse='OPEN',SS_setup='OPEN',FF_hold='OPEN'),
 geometry=dict(outline_um2=237.6*129.6,whole_fill=J['area_um2']/(237.6*129.6),
   local_band_fill=J['band_utilization'],max_local_cohort_row_fill=max(r['max_row_fill'] for r in J['geometry']['cohorts']),
   all_464_rows_retained=True,exception='pin-bound outline whole-fill is5.418%; root explicit review required; no utilisation pass inferred from band'),
 no_source_implementation=True,no_engine=True,no_placement_request=True,
 canonical_projection_method_commit='5b100ce330bd619261dfdf087e5a2df3bc6fff7d')
(P/'finite_refusal.json').write_text(json.dumps(R,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(15,9))
for y,h in [(2.16,53.46),(73.98,53.46)]:ax.add_patch(Rectangle((2.16,y),233.28,h,facecolor='#d5e5eb',alpha=.6,hatch='..',edgecolor='#9db1bf',lw=.3))
for y,h in [(30.78,24.84),(73.98,24.84)]:ax.add_patch(Rectangle((10.8,y),216,h,fill=False,edgecolor='#bb4433',ls='--',lw=1.1))
groups={k:[] for k in ('FF','hold/addition','clock','native signal')}
for n,c in B['cells'].items():
 b=c['bbox'];key='clock' if n.startswith('MODEL_clock') or n in {r['instance'] for r in json.load(open(P/'kit/inputs/clock_cost.json'))['rows']} else 'hold/addition' if n in a['added_cells'] else 'FF' if c['master'].startswith('DFF') else 'native signal'
 groups[key].append(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1]))
colors={'FF':'#3179b4','hold/addition':'#2c9c65','clock':'#a637a1','native signal':'#d89d30'}
for key,rs in groups.items():ax.add_collection(PatchCollection(rs,facecolor=colors[key],edgecolor='none'))
pos=json.load(gzip.open(P/'kit/inputs/positions.json.gz','rt'))
for ps in pos['bterms'].values():
 for q in ps:
  for b in q['boxes']:ax.add_patch(Rectangle((b[1]/1000,b[2]/1000),max(.1,(b[3]-b[1])/1000),max(.1,(b[4]-b[2])/1000),color='#222'))
ax.text(118.8,114,'Whole-outline routing geometry: UNQUALIFIED\n2,436 PG-clear M2/M4 rays; clock/new-PG/via/RC remain OPEN',ha='center',fontsize=10)
ax.text(118.8,17,'Dashed 24.84 um belts: REFUSED\n1,323 PG-clear rays < 1,414 crossing nets before clock/new PG',ha='center',fontsize=10,color='#9d3024')
ax.set(xlim=(0,237.6),ylim=(0,129.6),aspect='equal',xlabel='um',ylabel='um',title='INT8 fresh native-source MODEL — BUILD REFUSED\n12,491 cells / 1,668.41856 um² / 2,782 FF / 604 hold branches; no source implementation or engines')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker='s',linestyle='',color=colors[k],label=f'{k}: {len(v)}') for k,v in groups.items()],loc='center left',bbox_to_anchor=(1,.5),fontsize=9)
fig.text(.07,.035,'Cell band216×18.36 um at42.07%; whole pin-bound outline5.418% fill requires owner review. 464 rows preserved.\nAll clock phase/PG birth/contact/timing domains OPEN; 292 actual lower-wire-cap predicates and seven feedback conditions retained.',fontsize=9)
fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(P/'MODEL.png',dpi=180)
print(json.dumps({k:R[k] for k in ['status','first_band','exterior_24p84_belts','whole_core_exterior','max_source_first_HB_center_span_um','max_source_first_HB_bbox_separation_um']},indent=2))
print('SOURCE_GROUPS',len(sourcegroups),'BRANCHES',sum(g['total_first_HB_inputs'] for g in sourcegroups.values()),'MAX_PER_SOURCE',max(g['total_first_HB_inputs'] for g in sourcegroups.values()))
