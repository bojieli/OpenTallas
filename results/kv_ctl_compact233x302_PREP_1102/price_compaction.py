"""Source-identical parent/CTL geometry PREP, never activated or routed here."""
import json,csv,re,collections,hashlib,math
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector');S=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/capsule')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
net=S/'1_synth_odb.v';counts=collections.Counter(m for m,n in re.findall(r'(?m)^\s*(\S+)\s+(\\?\S+)\s*\(',net.read_text()) if m.endswith('_ASAP7_75t_R') or m.startswith('ctl_sram_'))
cells=list(csv.DictReader(open(C/'placed.csv')));dims={}
for c in cells:
 if c['kind']=='pin':continue
 wh=(float(c['w']),float(c['h']))
 assert c['master'] not in dims or dims[c['master']]==wh
 dims[c['master']]=wh
assert sum(counts.values())==54686 and counts['ctl_sram_1r1w_64x128_p192']==6 and all(k in dims for k in counts)
logic=sum(n*dims[k][0]*dims[k][1] for k,n in counts.items() if not k.startswith('ctl_sram_'));macro=sum(n*dims[k][0]*dims[k][1] for k,n in counts.items() if k.startswith('ctl_sram_'))
oldpins=json.load(open(C/'pins.json'));assert len(oldpins)==6849;newpins=json.loads(json.dumps(oldpins));groups=collections.defaultdict(list);W=233.28;H=302.4;shift=(371.52-W)/2;shifty=(371.52-H)/2
assert abs(shift-69.12)<1e-6 and abs(shifty-34.56)<1e-6
for p in newpins:
 if p['face']=='interior':p['x']=round(p['x']-shift,3);p['y']=round(p['y']-shifty,3)
 else:groups[(p['face'],p['layer'])].append(p)
peaks={};mins={}
for (face,layer),pins in groups.items():
 axis='x' if face in ['N','S'] else 'y';pins.sort(key=lambda p:(p[axis],p['bus'],str(p['bit'])));vals=[]
 for i,p in enumerate(pins):
  span=W if face in ['N','S'] else H;raw=4.344+(span-8.688)*i/max(1,len(pins)-1);a=round((raw-.024)/.048)*.048+.024;p[axis]=round(a,3)
  p['y' if face in ['N','S'] else 'x']=(H if face=='N' else W) if face in ['N','E'] else 0.0
  vals.append(p[axis])
 assert len(set(vals))==len(vals)
 mins[face+'/'+layer]=round(min((b-a for a,b in zip(vals,vals[1:])),default=0),3)
 j=0;best=0
 for i,v in enumerate(vals):
  while v-vals[j]>10.0000001:j+=1
  best=max(best,i-j+1)
 peaks[face+'/'+layer]=best/10
ident=lambda p:p['bus']+(f"[{p['bit']}]" if p['bit'] is not None else '')
assert sorted(map(ident,oldpins))==sorted(map(ident,newpins)) and len(set(map(ident,newpins)))==6849
(O/'candidate_pins_PREP.json').write_text(json.dumps(newpins,indent=1)+'\n')
parent_pins=[]
for p in newpins:
 x,y=p['x'],p['y']
 if p['face']=='W':x=.096
 elif p['face']=='E':x=W-.096
 elif p['face']=='S':y=.096
 elif p['face']=='N':y=H-.096
 parent_pins.append(dict(name=ident(p),layer=p['layer'],x=round(x,3),y=round(y,3)))
(O/'candidate_parent_pins_PREP.json').write_text(json.dumps(dict(schema='opentallas.die_plan.core_pins.v1',core='qkd_kvs_ctl',frame='PREP current6849 native profile,233.28x302.4 R0',source='GEOMETRY MODEL ONLY; parent namespace from actual production profile; expected native .096edge inset must be measured after normalFP before adoption',pins=parent_pins),indent=1)+'\n')
basis=json.load(open(O/'actual_production_parent_basis.json'));core=basis['core'];assert core['inst']=='kvs_ctl' and core['outline_um']==[371.52,371.52]
origin=[round(v+ds,3) for v,ds in zip(core['origin_um'],[shift,shifty])];assert origin==[967.68,172.8]
clocks=[]
for old,new in zip(oldpins,newpins):
 if old['face']=='interior':
  a=[round(core['origin_um'][i]+old[k],3) for i,k in enumerate(['x','y'])];b=[round(origin[i]+new[k],3) for i,k in enumerate(['x','y'])];assert a==b;clocks.append(dict(name=ident(old),old_local=[old['x'],old['y']],new_local=[new['x'],new['y']],global_unchanged=a))
macros=sorted((c for c in cells if c['kind']=='macro'),key=lambda c:(float(c['y']),float(c['x'])));sites=[]
for i,c in enumerate(macros):
 x=[25.92,155.52][i%2];y=[43.2,129.6,216.0][i//2];sites.append(dict(name=c['name'],master=c['master'],x=x,y=y,orient='R0',width=float(c['w']),height=float(c['h']),model_halo_um=4.32))
 assert x-4.32>=4.32 and y-4.32>=4.32 and x+float(c['w'])+4.32<=W-4.32 and y+float(c['h'])+4.32<=H-4.32
 for a,b in zip([core['origin_um'][0]+float(c['x']),core['origin_um'][1]+float(c['y'])],[origin[0]+x,origin[1]+y]):assert abs((b-a)/8.64-round((b-a)/8.64))<1e-6
(O/'candidate_macro_sites_PREP.json').write_text(json.dumps(sites,indent=2)+'\n')
delta=dict(status='PREP_NOT_APPLIED',basis=basis,parent_type='kv3_hub_C',child_instance='kvs_ctl',old=core,new=dict(core,origin_um=origin,outline_um=[W,H],pins_file='pins/kvs_ctl_compact233x302_1102_PREP.json'),clock_reset_global_coordinates_unchanged=clocks,boundary_pin_bits=6847,public_pin_positions_changed=True,logical_ABI_changes=0,RTL_changes=0,cycles_added=0,R8_added=0,selected_views_changed=False)
(O/'parent_delta_PREP.json').write_text(json.dumps(delta,indent=2)+'\n')
prices=[]
for w,h in [(371.52,371.52),(293.76,293.76),(276.48,276.48),(267.84,267.84),(250.56,285.12),(233.28,302.4),(233.28,371.52)]:prices.append(dict(outline_um=[w,h],native_SYNTH_logic_area_um2=logic,native_fixed_macro_area_um2=macro,logic_only_fill=logic/(w*h-macro)))
report=dict(status='PREP_NOT_PHYSICAL_QUALIFICATION',parent_basis=basis,source_module='qkd_kvs_ctl',source_native_synth_odb_sha256=sha(S/'run/results/asap7/hc_qkd_kvs_ctl__371_52x371_52/base/1_synth.odb'),source_native_synth_export_sha256=sha(net),source_standard_instances=54680,source_FFs=18768,master_types_joined=len(counts),source_logic_area_um2=logic,fixed_macro_area_um2=macro,outline_prices=prices,chosen_outline_um=[W,H],parent_old_origin_um=core['origin_um'],parent_new_origin_um=origin,parent_8p64_grid=True,parent_clock_reset_global_unchanged=clocks,macro_inventory=sites,pin_inventory=len(newpins),face_counts=dict(collections.Counter(p['face'] for p in newpins)),candidate_peak_pins_per_um_10um=peaks,minimum_same_face_layer_center_spacing_um=mins,pin_budget_per_um_unchanged=6.0,signal_ceiling_unchanged='M5',candidate_pin_file_sha256=sha(O/'candidate_pins_PREP.json'),PG_phase='parent and all six SRAM global moves are integer8.64um; current4.32/8.64 PG phases preserved geometrically, not actual PG qualification',OPEN=['native floorplan rows/taps/PG and pinaccess qualification','deliberate18768FF site assignment including unchanged54 physical master choices','actual fullgraph405/public150 and p90<=30; no more than10percent publicpins beyond30','actual empty-bin<=.5 using existing functional cells only','local M2-M5 channel capacity and actual>=50iteration GRT0 if proxy>.6','parent new publicpin correspondence/routes/clock model and current-source native views','no CTS/PLACE permission from this PREP; root picture review required'])
(O/'pricing_PREP.json').write_text(json.dumps(report,indent=2)+'\n');(O/'source_master_area_join.json').write_text(json.dumps({m:dict(count=n,width_um=dims[m][0],height_um=dims[m][1],total_area_um2=n*dims[m][0]*dims[m][1]) for m,n in sorted(counts.items())},indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ['source_logic_area_um2','fixed_macro_area_um2','chosen_outline_um','parent_new_origin_um','candidate_peak_pins_per_um_10um','minimum_same_face_layer_center_spacing_um']},indent=2))
