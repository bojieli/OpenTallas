#!/usr/bin/env python3
"""Current source-count B/C system packing, explicitly incomplete native VM.
Only real leaf rectangles are placed. Missing read/CDC/control-tree geometry
is listed rather than hidden in an inherited parent reservation.
"""
import argparse,copy,gzip,hashlib,json,math
from pathlib import Path

def box(n,xy,wh,k,**extra):return dict(name=n,xy_um=xy,outline_um=wh,kind=k,orientation='R0',**extra)
def overlap(a,b):
 x,y=a['xy_um'];w,h=a['outline_um'];X,Y=b['xy_um'];W,H=b['outline_um'];return x<X+W-1e-6 and x+w>X+1e-6 and y<Y+H-1e-6 and y+h>Y+1e-6

def main():
 ap=argparse.ArgumentParser()
 for n in ['capacity','local','field','edge','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();cap=json.loads(a.capacity.read_text());local=json.loads(a.local.read_text());field=json.loads(gzip.decompress(a.field.read_bytes()));edge=json.loads(a.edge.read_text());assert cap['pair_count']==2417 and cap['bf_pairs']==519
 rows=[r for r in field['insts'] if len(r)>8 and r[8].startswith('frame_') and r[7] not in ['rly','rstg']];assert len(rows)==32942
 fields=[box(r[0],[r[2],r[3]],[r[4],r[5]],'field') for r in rows]
 grid={}
 def cells(b):
  x,y=b['xy_um'];w,h=b['outline_um'];return [(i,j) for i in range(int(x//1000),int((x+w)//1000)+1) for j in range(int(y//1000),int((y+h)//1000)+1)]
 for i,b in enumerate(fields):
  for c in cells(b):grid.setdefault(c,[]).append(i)
 sw,sh=1965.6,2440.8;gap=21.6;opts=[]
 for name,origins,hcdx,sudx,svc in [('B_compact_2x2',[[13592.88+(sw+gap)*(s%2),12804.48+(sh+gap)*(s//2)] for s in range(4)],254.88,0,True),('C_two_client_regions',[[15584.4,6000.48+(sh+gap)*s] if s<2 else [15584.4,14001.12+(sh+gap)*(s-2)] for s in range(4)],259.2,-108,False)]:
  nodes=[];unplaced=[]
  for n in local['nodes']:
   s=n['slice'];master=n['master'];ox,oy=origins[s]
   if n['name'].endswith('_wscatter'):continue
   if 'bank' in n:nq=n['bank']//8
   elif 'quarter' in n['name']:nq=int(n['name'].split('quarter')[-1])//2
   elif 'bridge' in n['name']:nq=int(n['name'].split('bridge')[-1])
   else:unplaced.append(dict(name=n['name'],master=master,reason='Actual global read/control and scalar-return structural repair; inherited rectangle not qualified'));continue
   x,y=n['xy_um'];x+=1015.2*(nq%2)-1123.2*(nq%2);y+=1166.4*(nq//2)-777.6*(nq//2)-1468.8*s
   nodes.append(box(n['name'],[ox+x,oy+y],n['outline_um'],'bank_local_memory',master=master,slice=s,q8=nq))
  for s,(ox,oy) in enumerate(origins):
   for q in range(4):
    qx,qy=ox+1015.2*(q%2),oy+1166.4*(q//2)
    for b in range(8):
     cx=540+64.8*b if b<4 else 237.6-64.8*(b-4)
     nodes.append(box(f'vm_s{s}_q{q}_capture{b}',[qx+cx,qy+756],[43.2,43.2],'write_capture',master='dsfd_vm_static_write_capture128',slice=s,q8=q))
     dx,dy=edge['group']['stage_xy_um'][b];nodes.append(box(f'vm_s{s}_q{q}_storage{b}',[qx+dx,qy+820.8+dy],[86.4,86.4],'write_storage',master='dsfd_vm_static_wstage128',slice=s,q8=q))
    nodes.append(box(f'vm_s{s}_q{q}_scatterout',[qx+302.4,qy+648],[172.8,86.4],'write_output',master='dsfd_vm_static_scatter_b8_out',slice=s,q8=q))
    nodes.append(box(f'vm_s{s}_q{q}_dispatch',[qx+108,qy+820.8],[734.4,345.6],'write_dispatch',master='dsfd_vm_static_wdispatch128',slice=s,q8=q))
   nodes.append(box(f'vm_payload{s}',[ox+432,oy+2354.4],[1166.4,86.4],'write_payload',master='dsfd_vm_static_w0_payload',slice=s))
  header=[13592.88,17729.28] if svc else [13834.8,12900.48]
  nodes.extend([box('vm_w0_header',header,[216,86.4],'write_header'),box('vm_w0_control',[header[0]+237.6,header[1]],[216,86.4],'write_control')])
  fixed=[];service_y=17837.28
  for n,x,y,w,h in cap['hard_fixed_boxes']:
   if n=='sp_vm':continue
   if n=='sp_su_s':x+=sudx
   elif n in ['sp_hc_s','sp_hc_t']:
    nh=8806.32 if n=='sp_hc_s' else 9227.52;y=y+h-nh;h=nh;x+=hcdx
   elif n in ['sp_capture','sp_gather','sp_pq','sp_wfc','sp_sseq','sp_collective','sp_host']:
    if svc:y=service_y;service_y+=h+21.6
    else:x-=108
   fixed.append(box(n,[x,y],[w,h],'fixed_cluster'))
  fixed.extend(box(h['name'],h['at_um'],[h['outline']['w'],h['outline']['h']],'unbound_HCP') for h in cap['hcp_homes'])
  collisions=[]
  for b in nodes+fixed:
   for i in set(i for c in cells(b) for i in grid.get(c,[])):
    if overlap(b,fields[i]):collisions.append([b['name'],fields[i]['name']])
  allboxes=nodes+fixed
  for i,b in enumerate(allboxes):
   for other in allboxes[i+1:]:
    if overlap(b,other):collisions.append([b['name'],other['name']])
  assert len(nodes)==470,len(nodes);assert len(unplaced)==8,len(unplaced)
  outside=[b['name'] for b in allboxes if any(b['xy_um'][i]<0 or b['xy_um'][i]+b['outline_um'][i]>cap['die_outline_um'][i] for i in [0,1])]
  opts.append(dict(name=name,slice_origins_um=origins,slice_known_outline_um=[sw,sh],nodes=nodes,fixed=fixed,unplaced_actual_core=unplaced,collisions=collisions,outside=outside,geometry_screen=dict(q8_intergroup_horizontal_channel_um=64.8,E_HC_to_first_field_column_gap_um=19558.8-(17312.4+hcdx+1816.536),service_v1026_station_width_um=54.84,unproven='E corridor fulltraffic/clock/PG and actual futureGEN routes'),source_inventory=dict(core_leaves=328,core_clock_roots=376,write_edge_leaves=150,write_edge_clock_roots=150,known_total_leaves=478,known_total_clock_roots=526,placed_real_leaf_rectangles=470,unplaced_real_read_control_leaves=8),costs=dict(local_write_extra_cycles=0,read_repair_extra_cycles='Pending actual scope/implementation; proposal +1 per local return',global_write_distribution_cycles='UNPRICED: payload to four dispatches/slice exceeds single-hop distance',cap16_CDC16_x34_area='MISSING_NATIVE_DIMENSIONS; upstream capture remains separate',cuts='LOCAL_PIN_DISTANCE_ONLY; no fullboundary/activity/clock/PG cut pass'),changes=dict(hc_dx_um=hcdx,su_dx_um=sudx,service_stack='Tightly reordered preserving real macro heights' if svc else 'West108um, preserving source y')))
 report=dict(scope='PARTIAL_CURRENT_SYSTEM_PACKING_NOT_NATIVE_ADOPTED',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.capacity,a.local,a.field,a.edge,Path(__file__)]},die_um=cap['die_outline_um'],field_regions=cap['placements'],service_corridors=cap['service_access_corridors'],options=opts,known_missing=['VM FSR/read-return native geometry (eight known blocks) and proposed egress replacement','Cap16/CDC16/x34 native footprints/clock roots','Actual W0 shared fanout and header/control distribution trees','All81stage actual activity/programme/physicalSUhome map','Actual production whole-die pin/clock/PG/fullcuts/extra fixedage proof','Actual routed localbank/q4/b8 timing audit rejects27344of83712bits; geometry is not timing proof'],recommendation='B remains development direction. C compares client proximity but has a larger all-slice service span. No performance/cut-qualified selection.')
 report['source_inventory_binding']='328 memory leaves/376 roots from S_VM dfe28f6f8 + proof94c4514c2; local bank vectors from actual188 predecessor; direct capture/out pins30421c7c5 and q8reach eaca93a88; no scalar returnrepair substitution'
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps([dict(name=o['name'],collisions=len(o['collisions']),first=o['collisions'][:8],outside=o['outside'],placed=len(o['nodes'])) for o in opts],indent=1))
if __name__=='__main__':main()
