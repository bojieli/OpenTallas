"""Source-bound zero-added-edge pin-map proposal, never a placement or approval."""
from pathlib import Path
import json,collections,math,sys
p=Path(sys.argv[1]);d=json.loads(p.read_text());ports={x['name'][5:]:x for x in d['port_bits']};pairs=d['all_boundary_macro_pairs'];width,height=475.2,518.4
model={};reserved={'ck_core','por_n','host_rst_n','u_rank__u_control__por_n','pll_locked'}
tx={x for x in ports if x.startswith('u_rank__tx_d[')}|{'u_rank__tx_v','u_rank__tx_cr'};assert len(tx)==530
# Keep the existing reset/clock port faces and positions. PLL face relocation is a ROOT-only parent clock-status proposal.
for n in reserved:
 v=ports[n];face=v['actual_nearest_face'];along=v['xy_um'][1 if face in 'WE' else 0]
 if n=='pll_locked':face,along='S',238.2
 model[n]={'face':face,'along_um':along,'reason':'preserve reset/clock anchor' if n!='pll_locked' else 'PROPOSE PLL status S beside existing derived reset; ROOT parent-binding approval required'}
byport=collections.defaultdict(list)
for q in pairs:
 for n in q['root_ports']['input']:byport[n].append(q['endpoint']['xy_um'][1])
txorder=sorted(tx,key=lambda n:(sum(byport[n])/len(byport[n]) if byport[n] else 150,n))
for i,n in enumerate(txorder):model[n]={'face':'W','along_um':88+(i+.5)*90/530,'reason':'TX data/valid/credit whole bundle beside lower-left macro'}
intervals={'W':[(65.2,88),(178,254),(264.8,453.3)],'E':[(65.2,254),(264.8,453.3)],'S':[(59.4,232.2),(243,415.8)],'N':[(59.4,415.8)]}
for face,ivs in intervals.items():
 rem=[n for n,v in ports.items() if n not in model and v['actual_nearest_face']==face];rem.sort(key=lambda n:(ports[n]['xy_um'][1 if face in 'WE' else 0],n));length=sum(hi-lo for lo,hi in ivs)
 for i,n in enumerate(rem):
  offset=(i+.5)*length/len(rem)
  for lo,hi in ivs:
   if offset<hi-lo:along=lo+offset;break
   offset-=hi-lo
  model[n]={'face':face,'along_um':along,'reason':'uniform remaining face slots around protected clock/reset and TX region'}
assert set(model)==set(ports)
def xy(n):
 m=model[n];a=m['along_um'];return [8,a] if m['face']=='W' else [width-8,a] if m['face']=='E' else [a,8] if m['face']=='S' else [a,height-8]
ffmap={};face_ff=collections.defaultdict(dict);face_pins=collections.defaultdict(list)
for n,m in model.items():
 face_pins[m['face']].append(m['along_um']);v=ports[n]
 for pin in v['data_input_flops']+v['data_output_flops']:
  inst=pin.rsplit('/',1)[0];point=xy(n)
  if inst in ffmap and ffmap[inst]!=point:raise ValueError('multiport FF conflicting target '+inst)
  ffmap[inst]=point;face_ff[m['face']][inst]=m['along_um']
checks=[]
for q in pairs:
 names=q['root_ports']['input'];assert len(names)==1;n=names[0];a=xy(n);b=q['endpoint']['xy_um'];dist=sum(abs(x-y)for x,y in zip(a,b));checks.append({'port':n,'root':q['root']['name'],'macro_endpoint':q['endpoint'],'proposed_capture_xy_um':a,'L1_um':dist,'pass405':dist<=405,'margin405_um':405-dist})
summary={}
for face,slots in face_pins.items():
 a=sorted(face_ff[face].values());peak=0;j=0
 for i,x in enumerate(a):
  while x-a[j]>=10:j+=1
  peak=max(peak,i-j+1)
 span=(min(slots),max(slots));summary[face]={'port_bits':len(slots),'unique_boundary_FFs':len(a),'span_um':span,'global_FF_per_um':len(a)/(span[1]-span[0]),'ten_um_projection_max_FF_per_um':peak/10,'global_le6':len(a)/(span[1]-span[0])<=6,'local10um_le6':peak<=60,'minimum_corner_keepout_um':min(span[0],(height if face in 'WE' else width)-span[1])}
fixed=[]
for q in d['fixed_boundary_pairs_over405']:
 a=ffmap[q['root']['instance']];b=ffmap[q['endpoint']['instance']];dist=sum(abs(x-y) for x,y in zip(a,b));fixed.append({'root_ports':q['root_ports'],'endpoint_ports':q['endpoint_ports'],'proposed_root_xy':a,'proposed_endpoint_xy':b,'L1_um':dist,'pass405':dist<=405})
r={'schema':'peer.proposed_pin_map.geometry_only.v1','status':'MODEL_ONLY_NOT_ADOPTED','outline_um':[width,height],'macro_origins_orientations':'unchanged exact p32a actual R0 macros; actual per-bit WD split respected','added_data_edges':0,'source_sha256':'1277bb49de6e8e577c431282c5d8a057211f6e0ff06e6674b78b37393fce4336','input_odb_sha256':d['odb_sha256'],'nominal_capture_face_inset_um':8,'physical_scope':'Nominal projection model only: row legalization, actual pin access, per-FF cell extent, clock/reset landing routing, interior stage repack, timing and all-stage overlay still OPEN. No kit/source changes. Native/current gate failures retained.','parent_contract_change':'TX data[527:0]/valid/credit E->W; PLL status E->S proposed. Raw por_n E, host_rst_n S, ck_core W and derived reset S stay exact current port coordinates. ROOT must approve coherent parent model before implementation.','all_boundary_macro_pairs':len(checks),'boundary_macro_over405':sum(not x['pass405']for x in checks),'boundary_macro_max_L1_um':max(x['L1_um']for x in checks),'face_density':summary,'fixed_pair_checks':fixed,'ports':model,'FF_nominal_targets':ffmap,'bit_pin_checks':checks}
p.with_name('pin_model.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ('ports','FF_nominal_targets','bit_pin_checks')})
