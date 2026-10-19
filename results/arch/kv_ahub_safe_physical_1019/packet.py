"""Package the measured OpenDB floorplan and its rejected boundary partition."""
import json, collections, hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

base=Path(__file__).resolve().parent
x=json.loads((base/'floorplan.json').read_text())
source=collections.defaultdict(list)
for p in x['ports']:
 for e in p['endpoints']:
  if e['is_ff']:
   source[e['inst']].append({'port':p['port'],'face':p['face'],'port_xy_um':p['xy'],'port_rect_um':p['pin_rect_um'],'pin':e['pin'],'master':e['master']})
partition=[]
for n,uses in sorted(source.items()):
 partition.append({'source':n,'uses':uses,'required_partition':[[v['port']] for v in uses] if len(uses)>1 else [[uses[0]['port']]],'copies_required':max(0,len(uses)-1)})
assert len(source)==540
assert sum(len(v) for v in source.values())==645
assert len(x['cross_face_sources'])==35
assert {p['port'] for p in x['ports'] if not p['endpoints'] and p['port'] not in ('ck','rst_n')}==set()
assert sum(v['copies_required'] for v in partition)==105
assert max(x['face_density_per_um'].values())<=6
part={'schema':'opentallas.ahub.face_partition.v1','source_commit':'483ac4ba8','native_sha256':x['source_native_sha256'],'historical_unique_face_ff':623,'current_unique_face_ff':540,'public_ff_ports':623,'ff_endpoint_occurrences':645,'all_endpoint_occurrences':649,'same_edge_hs_start_sinks':23,'additional_dedicated_output_ff_required':105,'constant_ports':['am0[1]','am1[1]','am2[1]','am3[1]'],'partition':partition,'shared_output_witnesses':x['cross_face_sources'],'repair_rule':'For each AM group, keep one existing FF and clone its complete master/D/CLK/SETN/RESETN tuple for each of the other three output ports. Same source capture edge; no output edge/extra relay. Repartition every upstream driver and reset recursively, including added copies, then rerun source equivalence and occupied-reset/native miter.','pin_assignment_scope':'The lower bound rejects the explicit full-face coordinates in floorplan.json. A different assignment could reduce the bound but cannot establish historical dedicated face identity.'}
(base/'boundary_partition.json').write_text(json.dumps(part,indent=2)+'\n')
band=[21.6,226.8,712.8,231.66]
capacity=(band[2]-band[0])*(band[3]-band[1])
model={'schema':'opentallas.ahub.safe_geometry_rejection.v1','qualified':False,'status':'BLOCKED_BEFORE_PLACEMENT','outline_um':[734.4,540],'aspect_ratio':734.4/540,'macro_area_um2':sum((m['box_um'][2]-m['box_um'][0])*(m['box_um'][3]-m['box_um'][1]) for m in x['macros']),'mapped_source_std_area_um2':1575.67518,'physical_tie_import_std_area_um2':x['std_area_um2'],'tie_area_increment_um2':x['std_area_um2']-1575.67518,'boundary_ff_area_um2':x['boundary_ff_area_um2'],'historical_band_all_std_fill_percent':100*x['std_area_um2']/7464.96,'candidate_core_band_um':band,'candidate_band_nominal_site_area_um2':capacity,'candidate_all_std_charged_fill_percent':100*x['std_area_um2']/capacity,'candidate_status':'CAPACITY_ESTIMATE_ONLY: all std charged to core band; native face strip/copy placement, legal rows, PG blockages and clock loads not admitted. Reprice after source repair.','macro_halo_um':5.4,'pg_reservations':'Original child LEFs immutable; parent M5/M6/M7 stripes and child PG connection/access unmeasured. No PDN generated.','clock_ownership':'Prospective source-owned W/E/N face groups and central core/5 child contacts. N entry at x367.212,y540; central core root near367.2,229 requires approximately311um trunk; regional buffer routes/loaded TT+FF arrivals unknown. No assumed compensation or clock latency change.','native_limits_ps':{'launch':220,'capture':190,'pin_flop_spread_TT_FF':80},'constraints':'No delay/uncertainty/hold relaxation; all native TT/FF timing, physical PG escape and <=405um stage reach remain unqualified.','max_endpoint_diameter_um':x['cross_face_sources'][0]['diameter_um'],'minimum_any_location_max_leg_um':x['cross_face_sources'][0]['minimum_possible_max_leg_um'],'reach_limit_um':405,'allowed_next_step':'Source face-copy repair, then regenerate exact area/row/native access and region ownership model before placement/CTS approval.'}
(base/'model.json').write_text(json.dumps(model,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(13,9))
ax.add_patch(Rectangle((0,0),734.4,540,fill=False,lw=2))
for m in x['macros']:
 a,b,c,d=m['box_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#d9e8ef',edgecolor='#355968'))
 ax.text((a+c)/2,(b+d)/2,m['inst']+'\n'+m['master']+'\nR0',ha='center',va='center',fontsize=8)
 # Exact immutable native contact rectangles, transformed by R0.
 fn='zh.lef' if m['master']=='ot_nhb_zh' else 'recip.lef'
 import sys
 sys.path.insert(0,str(base));import check_macro_track_alignment as cm
 lm=cm.parse_lef((base/fn).read_text())[0]
 for pin in lm['pins']:
  if pin['name'] not in ('clk','rst_n'):continue
  for layer,r in pin['rects']:
   xx=a+(r[0]+r[2])/2000;yy=b+(r[1]+r[3])/2000
   ax.plot(xx,yy,'o',color='#d16d00',ms=4)
a,b,c,d=band
ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#5eaa6d',alpha=.8))
ax.text(367.2,216,'Candidate core band 691.2 × 4.86 µm; capacity only',ha='center',fontsize=8)
for p in x['ports']:
 ax.plot(*p['xy'],'.',color={'W':'#286bc1','E':'#8056a5','N':'#138c80'}[p['face']],ms=2)
worst=x['cross_face_sources'][0]
byport={p['port']:p for p in x['ports']}
points=[byport[n]['xy'] for n in worst['witness_pair']]
ax.plot([p[0] for p in points],[p[1] for p in points],color='#c32d2d',lw=1.8,ls='--')
ax.text(367.2,120,'BLOCKED: shared AM[9] source\npin-rectangle L1 separation ≥914.784 µm\nany register location requires one leg ≥457.392 µm',ha='center',color='#a51f1f',fontsize=10,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'})
clock=byport['ck']['xy'];ax.plot(*clock,'*',ms=12,color='#d16d00');ax.annotate('Proposed clock entry',clock,(500,555),arrowprops={'arrowstyle':'->'},fontsize=8)
ax.set(xlim=(-25,760),ylim=(-20,585),xlabel='µm',ylabel='µm',aspect='equal')
ax.set_title('Exact 483ac4ba8 AHUB native floorplan preflight — BLOCKED before placement\nAll five unchanged children R0 on 43.2 µm grid; no CTS, route, PG or timing claim',fontsize=12)
fig.tight_layout();fig.savefig(base/'preflight.png',dpi=150);fig.savefig(base/'preflight.svg');plt.close(fig)
