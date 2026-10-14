#!/usr/bin/env python3
"""Generate an unassigned lo-only alignment request from accepted pin authority."""
import copy,gzip,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'physical/s81_die_pins/v18/gather_leaves'
OUT=SRC/'requests/ssa2_lo_input_alignment';OUT.mkdir(parents=True,exist_ok=True)
PROOF=ROOT/'results/rtl/s81_ph_20261006/gather/pins_v18'
def write(name,data):
 raw=(json.dumps(data,indent=1)+'\n').encode();(OUT/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parent_path=SRC/'requests/lo_input_alignment/parent_assignment.json'
parent=json.loads(parent_path.read_text())
baseline_parent=json.loads((PROOF/'parent_assignment.json').read_text())
for name,port in baseline_parent['ports'].items():
 assert parent['ports'][name]==port,(name,'existing parent assignment changed')
masters={};changes=[];fail=[];counts={}
for side in ['rw','re']:
 p=SRC/f'dsfd_gth_{side}.json';original=subprocess.check_output(['git','show',f'0ef156eff:physical/s81_die_pins/v18/gather_leaves/dsfd_gth_{side}.json'],cwd=ROOT);d=json.loads(original);pins=copy.deepcopy(d['pins']);old=copy.deepcopy(pins)
 for b in range(828):
  out=pins[f'lo[{b}]'];desired=pins[f'li[{276+b}]']['point'][2];delta=round(desired-out['point'][2],6)
  out['point'][2]=desired;out['rect'][1]=round(out['rect'][1]+delta,6);out['rect'][3]=round(out['rect'][3]+delta,6)
  changes.append({'master':f'dsfd_gth_{side}','port':f'lo[{b}]','matched_input':f'li[{276+b}]','old':old[f'lo[{b}]']['point'],'proposed':out['point'],'ordinate_delta_um':delta,'new_ideal_midpoint':[(out['point'][1]+pins[f'li[{276+b}]']['point'][1])/2,desired],'ideal_half_manhattan_um':94.998})
 assert set(old)==set(pins) and len(pins)==3423
 for name,x in pins.items():
  if x['face']!=old[name]['face'] or x['direction']!=old[name]['direction'] or x['point'][0]!=old[name]['point'][0]:fail.append([side,name,'face/layer/direction changed'])
  r=x['rect'];layer,xx,yy=x['point'];coord=yy if x['face'] in ['W','E'] else xx
  if abs((coord-.012)/.048-round((coord-.012)/.048))>1e-6:fail.append([side,name,'native track'])
  if not (0<=r[0]<r[2]<=190.08 and 0<=r[1]<r[3]<=164.16):fail.append([side,name,'face bounds'])
 buckets={}
 for name,x in pins.items():buckets.setdefault((x['face'],x['point'][0]),[]).append((name,x['rect']))
 overlaps=[]
 for (face,layer),bucket in buckets.items():
  axis=1 if face in ['W','E'] else 0;bucket.sort(key=lambda x:x[1][axis])
  for i,(name,r) in enumerate(bucket):
   for name2,z in bucket[i+1:]:
    if z[axis]>=r[axis+2]:break
    if max(r[0],z[0])<min(r[2],z[2]) and max(r[1],z[1])<min(r[3],z[3]):overlaps.append([name,name2,layer])
 dump=json.loads((PROOF/f'dsfd_gth_{side}.gate_dump.json').read_text());pg_overlaps=[]
 for name,x in pins.items():
  layer=x['point'][0];r=x['rect']
  for item in dump['pdn_edge']:
   if item[1]!=layer:continue
   z=item[3]
   if max(r[0],z[0])<min(r[2],z[2]) and max(r[1],z[1])<min(r[3],z[3]):pg_overlaps.append([name,item])
 fail.extend([side,'signal overlap',z] for z in overlaps);fail.extend([side,'PG overlap',z] for z in pg_overlaps)
 d.update(status='REQUEST_NOT_ASSIGNED',pins=pins,authority='Pending explicit die owner assignment; accepted0ef156eff remains authoritative',baseline_manifest_sha256=hashlib.sha256(original).hexdigest(),requested_change='Only lo[827:0] ordinate aligned with corresponding source li[1103:276]; all co own/forward points preserved')
 masters[side]=pins;write(f'dsfd_gth_{side}.json',d)
 lines=['# PIN REPAIR REQUEST ONLY: NOT DIE ASSIGNED; do not submit this plan']
 for name,x in sorted(pins.items()):
  layer,xx,yy=x['point'];lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{xx} {yy}}} -force_to_die_boundary')
 (OUT/f'dsfd_gth_{side}.tcl').write_text('\n'.join(lines)+'\n')
 counts[side]={'ports':len(pins),'changed':sum(x!=old[n] for n,x in pins.items()),'same_layer_signal_overlaps':len(overlaps),'same_layer_PG_overlaps':len(pg_overlaps),'unchanged_co_bits':848,'co_own_bits_preserved':212,'unchanged_clock_reset_status':all(pins[n]==old[n] for n in ['ck','rs','rso','fi[0]','fi[1]','fo[0]','fo[1]'])}
instances=json.loads((PROOF/'leaf_instances.json').read_text());imap={x['clock_pin']['instance']:x for x in instances}
def updated(ep):
 ep=copy.deepcopy(ep)
 if ep['instance']=='PARENT':
  name,bit=ep['port'].rsplit('[',1);bit=int(bit[:-1]);face,layer,t,_=parent['ports'][name]['per_bit'][bit];w,h=parent['outline_um'];pt=[layer,0 if face=='W' else w if face=='E' else t,0 if face=='S' else h if face=='N' else t]
  assert ep['point']==pt,(ep,pt,'parent projection changed')
  ep['point']=pt
 else:
  inst=imap[ep['instance']];side=inst['master'].rsplit('_',1)[1];layer,x,y=masters[side][ep['port']]['point'];ox,oy=inst['origin_um'];ep['point']=[layer,round(x+ox,6),round(y+oy,6)]
 return ep
links=json.load(gzip.open(PROOF/'bit_links.json.gz'));summary={}
for link in links:
 old=link['manhattan_um'];link['a']=updated(link['a']);link['b']=updated(link['b']);a=link['a']['point'];b=link['b']['point'];link['baseline_manhattan_um']=old;link['manhattan_um']=round(abs(a[1]-b[1])+abs(a[2]-b[2]),6)
 s=summary.setdefault(link['kind'],{'count':0,'baseline_max_manhattan_um':0,'requested_max_manhattan_um':0,'requested_max_euclidean_um':0});s['count']+=1;s['baseline_max_manhattan_um']=max(s['baseline_max_manhattan_um'],old);s['requested_max_manhattan_um']=max(s['requested_max_manhattan_um'],link['manhattan_um']);s['requested_max_euclidean_um']=max(s['requested_max_euclidean_um'],round(math.hypot(a[1]-b[1],a[2]-b[2]),6))
bindings=json.load(gzip.open(PROOF/'whole_leaf_port_bindings.json.gz'));bindings=[updated(x) for x in bindings]
assert len(bindings)==109536
write('bit_links.json.gz',links);write('whole_leaf_port_bindings.json.gz',bindings);write('master_port_changes.json',changes)
write('proof.json',{'status':'REQUEST_NOT_ASSIGNED','source_generator_sha256':sha(Path(__file__)),'parent_assignment_sha256':sha(parent_path),'parent_assignment_source':'die owner c1c8cc079; prior data/leaf/control coordinates verified unchanged;133ck_r added','baseline_parent_assignment_sha256':sha(PROOF/'parent_assignment.json'),'RTL_mapping_sha256':sha(ROOT/'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv'),'baseline_accepted_commit':'0ef156eff','master_audit':counts,'instances':32,'whole_signal_bits':len(bindings),'links':summary,'failures':fail,'projection':'All existing logical per-bit links and parent coordinates preserved. Every leaf endpoint regenerated from its requested master point and accepted native origin. No source or consumed bit order change.','seam_effect':'EW seam channel horizontal26.004um plus ordinate26.496um =52.500um Manhattan, compared with39.156/39.348um baseline. Faces/layers unchanged; real route cut/PG/slew/reach/hold still owed.','owed':['Explicit die owner acceptance before any use','Actual pin-stage IOP/PG/LEF and native lattice validation','Placement legalizes staggered real FF D/Q positions; ideal94.998um midpoint is not physical reach proof','SS60/25/833.333 normalized per-bit setup/output max and hold/min pair budgets','Existing SS internal EV failure and macro214.4ps slew remain unresolved','No routed/adopted/qualified claim']})
print('REQUEST',counts,'links',summary,'failures',len(fail))
