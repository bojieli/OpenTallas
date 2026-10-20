"""Necessary per-FF convex geometry feasibility, not packing or clock approval."""
import json,gzip,collections,sys,hashlib,math
from pathlib import Path
p=Path(sys.argv[1]);d=json.load(gzip.open(p,'rt'));model_path=sys.argv[2] if len(sys.argv)>2 else 'pin_model_slotswap.json';m=json.load(open(model_path));inv=json.load(open('protected_fence_inventory.json'));reset=json.load(gzip.open('reset_graph_profile.json.gz','rt'));cs={x['instance'].replace('.','/'):x for x in reset['conditioners']};actual={x['instance']for x in d['sequential_instances'] if x['kind']=='liberty_sequential'}
fixed=dict(m['FF_nominal_targets']);outer=[n for n,x in cs.items() if x['stage']=='outer_S2' and n in actual];assert len(outer)==59
for resetname in ('host_rst_n','por_n'):
 names=sorted(n for n in outer if resetname in cs[n]['original']);assert names
 for j,n in enumerate(names):
  a=(-10.8+(j+.5)*21.6/len(names));fixed[n]=[237.612+a,20] if resetname=='host_rst_n' else [455.2,259.404+a]
eligible=actual-set(fixed);assert len(eligible)==14423
macro=[x['instance']for x in d['sequential_instances'] if x['kind']=='synchronous_sram'];assert len(macro)==3
trans=dict(m['macro_nominal_translations']);upper=[n for n in macro if n not in trans];assert len(upper) in (0,1)
if upper:trans[upper[0]]=[0,43.2]
assert set(trans)==set(macro)
rect=[108,209.25,367.2,339.93];R=397;limits={n:[-float('inf'),float('inf'),-float('inf'),float('inf')] for n in eligible};neighbors=collections.defaultdict(list);fixed_bad=[];counts=collections.Counter()
def xy(z):
 n=z.get('instance')
 if n in fixed:return fixed[n]
 if n in trans:return [a+b for a,b in zip(z['xy_um'],trans[n])]
 if z['kind'] in ('port_bit','input_port','output_port'):
  port=m['ports'][z['pin']];a=port['along_um'];f=port['face'];return [0,a]if f=='W'else[475.2,a]if f=='E'else[a,0]if f=='S'else[a,518.4]
 raise ValueError('unclassified fixed endpoint '+str(z))
def constraint(n,z,kind):
 x,y=xy(z);u=x+y;v=x-y;l=limits[n];l[0]=max(l[0],u-R);l[1]=min(l[1],u+R);l[2]=max(l[2],v-R);l[3]=min(l[3],v+R)
 neighbors[n].append({'fixed':z,'nominal_fixed_xy': [x,y],'kind':kind})
def pair(a,b,kind):
 na,nb=a.get('instance'),b.get('instance');ea,eb=na in eligible,nb in eligible;counts[kind+':pairs']+=1
 if ea and eb:counts['core_to_core_diameter_guaranteed_pairs']+=1;return
 if ea:constraint(na,b,kind)
 elif eb:constraint(nb,a,kind)
 else:
  x,y=xy(a),xy(b);dist=sum(abs(a-b)for a,b in zip(x,y));counts['fixed_to_fixed_pairs']+=1
  if dist>405+1e-8:fixed_bad.append({'root':a,'endpoint':b,'nominal_root_xy':x,'nominal_endpoint_xy':y,'L1_um':dist,'category':kind})
for e in d['data_stage_edges']:pair(e['root'],e['endpoint'],'data')
for s in d['sequential_instances']:
 for z in s['input_pins']:
  if z['kind']not in ('data_next_state','memory_data_control'):
   for a in z['roots']:pair(a,z,'nondata_control')
byport={x['pin']:x for x in d['port_bits']}
for z in d['output_port_sources']:
 for a in z['roots']:pair(a,byport[z['port']],'output_port')
def clip(poly,aa,bb,cc):
 out=[]
 for j,q in enumerate(poly):
  t=poly[j-1];vq=aa*q[0]+bb*q[1]-cc;vt=aa*t[0]+bb*t[1]-cc
  if (vq<=1e-8)!=(vt<=1e-8):
   f=vt/(vt-vq);out.append([t[0]+f*(q[0]-t[0]),t[1]+f*(q[1]-t[1])])
  if vq<=1e-8:out.append(q)
 return out
regions={};empty=[]
for n,l in limits.items():
 poly=[[rect[0],rect[1]],[rect[2],rect[1]],[rect[2],rect[3]],[rect[0],rect[3]]]
 for aa,bb,cc in ((1,1,l[1]),(-1,-1,-l[0]),(1,-1,l[3]),(-1,1,-l[2])):
  if math.isfinite(cc):poly=clip(poly,aa,bb,cc)
 if not poly:empty.append({'instance':n,'uv_bounds':l,'fixed_neighbors':neighbors[n]})
 else:regions[n]={'polygon_xy_um':poly,'fixed_neighbor_count':len(neighbors[n])}
r={'schema':'peer.expanded_region_necessary_feasibility.v1','status':'REFUSED_EMPTY_FF_REGION_OR_FIXED_PAIR' if empty or fixed_bad else 'PASS_NECESSARY_REGIONS_ONLY','scope':'Necessary geometry only, not cell packing, global capacity, routing, phase/clock/reset proof or admission. Source dead-FF correspondence independently preserved. All data/control/output pairs checked. Interior combinational gates unplaced.','source_odb_sha256':d['odb_sha256'],'pin_model_sha256':hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),'core_rectangle_um':rect,'core_endpoint_L1_diameter_um':rect[2]-rect[0]+rect[3]-rect[1],'core_area_um2':(rect[2]-rect[0])*(rect[3]-rect[1]),'active_remaining_area_um2':inv['active_remaining_stdcell_area_um2'],'active_remaining_util':inv['active_remaining_stdcell_area_um2']/((rect[2]-rect[0])*(rect[3]-rect[1])),'fixed_neighbor_radius_um':R,'nominal_margin_to405_um':405-R,'eligible_FF':len(eligible),'outer_S2_fixed':len(outer),'macro_translations':trans,'counts':dict(counts),'fixed_pair_over405':fixed_bad,'empty_regions':empty,'feasible_regions':regions}
p.with_name('expanded_region_feasibility_'+Path(model_path).stem+'.json.gz').write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode()));print({k:v for k,v in r.items()if k not in ('fixed_pair_over405','empty_regions','feasible_regions')});print('empty',len(empty),'fixedbad',len(fixed_bad));p.with_name('expanded_region_refusals_'+Path(model_path).stem+'.json').write_text(json.dumps({k:v for k,v in r.items()if k!='feasible_regions'},indent=2)+'\n')
