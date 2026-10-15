#!/usr/bin/env python3
"""Repack actual four-slice VM and entire HC towers in the canonical die.

Whole-system arrangement candidates, preserving exact field/root identities,
all 164 VM core nodes and granted native HC tower dimensions. This is a
rectangle/capacity experiment; global endpoint pins and physical schedules
remain mandatory before adoption. Inputs are source-pinned in the report.
"""
import argparse,copy,gzip,hashlib,json
from pathlib import Path


def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def box(name,xy,wh,kind):return dict(name=name,xy_um=xy,outline_um=wh,kind=kind,orientation='R0')
def overlap(a,b):
 x,y=a['xy_um'];w,h=a['outline_um'];xx,yy=b['xy_um'];ww,hh=b['outline_um']
 return x<xx+ww-1e-6 and x+w>xx+1e-6 and y<yy+hh-1e-6 and y+h>yy+1e-6


def options(cap,vm,contract):
 slots={s['name']:s for s in contract['slots']}
 sw,sh=vm['core_slice_outline_um'];gap=21.6
 b_hc=max(0,13446+2*sw+2*gap-17312.4);c_hc=max(0,15584.4+sw+2*gap-17312.4)
 specs=[('A_vertical_expansion',[[14036.112,12804.48+sh*s] for s in range(4)],[14079.312,12804.48+4*sh],0,0,0),
        ('B_compact_2x2',[[13446+(sw+gap)*(s%2),12804.48+(sh+gap)*(s//2)] for s in range(4)],[13489.2,12804.48+2*sh+2*gap],b_hc,0,0),
        ('C_two_client_regions',[[15584.4,6000.48+(sh+gap)*s] if s<2 else [15584.4,14001.12+(sh+gap)*(s-2)] for s in range(4)],[13770,12804.48],c_hc,-108,-216)]
 out=[]
 for label,origins,edge,hc_dx,su_dx,svc_dx in specs:
  fixed=[]
  for name,x,y,w,h in cap['hard_fixed_boxes']:
   if name=='sp_vm':continue
   if name in ('sp_hc_s','sp_hc_t'):
    native_h=slots[name]['outline']['h'];y=y+h-native_h;h=native_h;x+=hc_dx
   elif name=='sp_su_s':x+=su_dx
   elif name in ('sp_capture','sp_gather','sp_pq','sp_wfc','sp_sseq','sp_collective','sp_host'):x+=svc_dx
   fixed.append(box(name,[x,y],[w,h],'hard_cluster'))
  fixed += [box(h['name'],h['at_um'],[h['outline']['w'],h['outline']['h']],'unbound_HCP_reservation') for h in cap['hcp_homes']]
  nodes=[]
  for n in vm['nodes']:
   s=n['slice'];xy=[origins[s][0]+n['xy_um'][0],origins[s][1]+n['xy_um'][1]-sh*s]
   q=box(n['name'],xy,n['outline_um'],'VM_core');q['master']=n['master'];q['slice']=s;nodes.append(q)
  edgebox=box('VM_global_edge_UNPROVEN',edge,[1987.2,561.6],'unproven_edge_reservation')
  out.append(dict(name=label,slice_origins_um=origins,vm_nodes=nodes,fixed=fixed,edge=edgebox,
                  changes=dict(hc_tower_translation_x_um=hc_dx,su_translation_x_um=su_dx,service_stack_translation_x_um=svc_dx),
                  architectural_tradeoff=('Existing vertical grouping with actual larger VM; exposes overlap rather than claiming old slot fit' if label.startswith('A') else 'Whole native32bank slices in2x2; shorter physical span, new global fanout/calendar must be built' if label.startswith('B') else 'Two slices near lowerSU/HC and two near upperHC; global all-slice service equalization may add substantial cycles')))
 return out


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for key in ['capacity','vm','contract','field','out']:ap.add_argument('--'+key,type=Path,required=True)
 a=ap.parse_args();cap,vm,contract,field=[load(p) for p in [a.capacity,a.vm,a.contract,a.field]]
 counts={kind:sum(r[7]==kind for r in field['insts']) for kind in ['seq','cfg','bf','bfcol','q','cfifo']}
 assert counts==dict(seq=2417,cfg=16919,bf=519,bfcol=1038,q=1898,cfifo=128),counts
 assert cap['pair_count']==2417 and cap['bf_pairs']==519 and cap['root_count']==128
 assert len({n['name'] for n in vm['nodes']})==len(vm['nodes'])
 assert sum(n['master']=='dsfd_vm_static_bank128' for n in vm['nodes'])==128
 fields=[box(r[0],[r[2],r[3]],[r[4],r[5]],r[7]) for r in field['insts'] if r[8].startswith('frame_')]
 opts=options(cap,vm,contract)
 for q in opts:
  moving=q['vm_nodes']+[q['edge']];fixed=q['fixed'];collisions=[]
  # Each candidate is compared against every unchanged real field child.
  for n in moving:
   for other in fields+fixed:
    if overlap(n,other):collisions.append([n['name'],other['name']])
  for i,n in enumerate(moving):
   for other in moving[i+1:]:
    if overlap(n,other):collisions.append([n['name'],other['name']])
  for i,n in enumerate(fixed):
   for other in fixed[i+1:]:
    if overlap(n,other):collisions.append([n['name'],other['name']])
   for other in fields:
    if overlap(n,other):collisions.append([n['name'],other['name']])
  outside=[n['name'] for n in moving+fixed if min(n['xy_um'])<0 or any(n['xy_um'][i]+n['outline_um'][i]>cap['die_outline_um'][i]+1e-6 for i in range(2))]
  q['rectangle_collisions']=collisions;q['outside']=outside
  q['scope']='GEOMETRY_ONLY_UNADOPTED_SYSTEM_ALTERNATIVE'
  q['hardware_counts']=dict(field_pairs=2417,BF_fronts=519,CFG_ROM=16919,root_regions=128,VM_core_nodes=len(q['vm_nodes']),VM_banks=sum(n['master']=='dsfd_vm_static_bank128' for n in q['vm_nodes']))
  q['unproven']=['Global53writer/cap16/CDC16 packing in edge reservation','Actual global readissue/return/write pin faces and clock/phase delivery','All boundary wire length, actual relay allocation/cuts<=0.60 and priced extra static cycles','All native HC children and expandedHCP source pin contracts','Full revised canonical FIELD return/broadcast topology regenerates; old transport not kept']
 report=dict(schema='opentallas.s81.system_geometry_options.v1',scope='CANONICAL_FULL_FIELD_AND_ACTUAL_VM_CORE_RECTANGLES_ONLY',
   input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.capacity,a.vm,a.contract,a.field,Path(__file__)]},die_um=cap['die_outline_um'],canonical_actual_counts=counts,unchanged_field_children=len(fields),baseline_snapshot_instances=len(field['insts']),source_VM_template_nodes=len(vm['nodes']),source_VM_template_status=('SUPERSEDED_EXACT_PIN_AUDIT_FAIL_MAX1097.9UM:164node template is rectangle diagnostic only; successor188nodes pending' if len(vm['nodes'])==164 else 'Actualsource option; native pin/route qualification must still be checked'),options=opts,
   recommendation='B is the first candidate to evaluate if it clears rectangle checks. It compacts the actual4slice VM while keeping SU and service vertical locations. C compares physical client grouping but may worsen shared all-slice service latency. No routed/performance ranking is proven.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n')
 print(json.dumps([dict(name=q['name'],collisions=len(q['rectangle_collisions']),outside=len(q['outside']),first_collisions=q['rectangle_collisions'][:5]) for q in opts]))
if __name__=='__main__':main()
