"""Single S82 scan-die construction: native source rectangles and full RD64 graph.
This emits a routing input, not a hardened-cell or clock-qualified fit verdict.
"""
import argparse, gzip, hashlib, json, math
from pathlib import Path
import dsrom_c_s82_placement as P
ROOT=P.ROOT; BASE=P.BASE
PHY=ROOT/'physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5.json'
def collision_scan(rectangles):
 grid={};hits=[]
 for i,a in enumerate(rectangles):
  b=a['bbox_um'];keys=[(x,y) for x in range(int(b[0]//1000),int((b[2]-1e-7)//1000)+1) for y in range(int(b[1]//1000),int((b[3]-1e-7)//1000)+1)]
  for j in set(j for k in keys for j in grid.get(k,[])):
   if P.overlap(b,rectangles[j]['bbox_um']):hits.append([rectangles[j]['name'],a['name']])
  for k in keys:grid.setdefault(k,[]).append(i)
 return hits
def build():
 old=P.build(); phy=json.loads(PHY.read_text());w=phy['footprint']['width_um'];h=phy['footprint']['height_um'];halo=4.32
 rect=[dict(a) for a in old['rectangles'] if a['kind'] not in ('q','BF','cfg','return_FF50_reservation')]
 for i,(x,y,orient) in enumerate([(4.32,4.32,'R0'),(8513.568,4.32,'R0'),(12000.096,26000-h-4.32,'MX'),(20509.344,26000-h-4.32,'MX')]):
  rect.append(dict(name=f'HBM_PHY{i}',kind='HBM_PHY_assumed_abstract',bbox_um=[x,y,x+w,y+h],orientation=orient,signal_pins=phy['pins']['signal_pins'],area_grade='assumed',clock_min_period_ps=900))
 obstacles=list(rect);shift=P.snap(h+3*halo);bounds=P.read('stage_map')['region_bounds'];fail=[]
 elems={a['site']:a for a in old['rectangles'] if a['kind'] in ('q','BF')}
 pitch=P.snap(157.68+2*halo)
 for region,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
  origin=P.snap(region%2*16500);x=origin+halo;y=shift+region//2*pitch+halo
  for pair in range(lo,hi):
   a=dict(elems[pair]);ow,oh=a['bbox_um'][2]-a['bbox_um'][0],a['bbox_um'][3]-a['bbox_um'][1]
   while True:
    b=[x-halo,y-halo,x+ow+halo,y+oh+halo];hits=[o for o in obstacles if P.overlap(b,o['bbox_um'])]
    if not hits:break
    x=P.snap(max(o['bbox_um'][2] for o in hits)+halo)
   if x+ow+halo>origin+16500:fail.append([region,pair,x+ow+halo])
   a['bbox_um']=[x,y,x+ow,y+oh];rect.append(a);x=P.snap(x+ow+2*halo)
 for a in old['rectangles']:
  if a['kind'] in ('cfg','return_FF50_reservation'):
   a=dict(a);b=a['bbox_um'];a['bbox_um']=[b[0],b[1]+shift,b[2],b[3]+shift];rect.append(a)
 band=next(a['bbox_um'] for a in rect if a['kind']=='return_FF50_reservation')
 # Exactly 63 binary nodes per retained 64-leaf region plus one root; no
 # deletion of inactive pairs. Storage children replace the aggregate slab.
 storage=[];edges=[];leaves={}; node_bits=2*64*65+66;root_bits=128*(65+66);bit_area=.75816
 for region in range(128):
  x0=region*33000/128;rw=33000/128;y=band[1]
  current=[]
  lo,hi=bounds[region],bounds[region+1]
  for slot in range(32):
   pair=lo+slot if lo+slot<hi else None
   for mb in (0,1):
    key=f'leaf{32*region+slot}_{mb}';leaves[key]=dict(field_pair=pair,return_pair=32*region+slot,MB=mb,active=pair is not None,constant_zero=pair is None);current.append(key)
  level=0
  while len(current)>1:
   nxt=[];count=len(current)//2;nh=count*node_bits*bit_area/rw
   for j in range(count):
    name=f'return_r{region}_L{level}_n{j}';b=[x0+j*rw/count,y,x0+(j+1)*rw/count,y+nh]
    storage.append(dict(name=name,kind='return_node_FF50_storage',bbox_um=b,bits=node_bits,region=region,level=level,physical_implementation='unmapped FF50 storage reservation; adder/control excluded'))
    edges.extend(dict(source=current[2*j+k],destination=name,bits=66,class_name='return_binary') for k in (0,1));nxt.append(name)
   current=nxt;y+=nh;level+=1
  name=f'return_root{region}';storage.append(dict(name=name,kind='return_root_FF50_storage',bbox_um=[x0,y,x0+rw,y+root_bits*bit_area/rw],bits=root_bits,region=region))
  edges.append(dict(source=current[0],destination=name,bits=66,class_name='return_to_root'))
  edges.append(dict(source=name,destination='CAPTURE_RAW' if region<64 else 'CAPTURE_RAW_256_PAIRED',bits=69,class_name='no_ready_root_capture'))
 rect=[a for a in rect if a['kind']!='return_FF50_reservation']+storage
 for cfg in [a for a in rect if a['kind']=='cfg']:
  edges.append(dict(source=cfg['name'],destination=f'pair{cfg["pair"]}',bits=72,class_name='cfg_read_to_local_wordmux',slice=cfg['slice'],local_wordmux_unplaced=True))
 collisions=collision_scan(rect);outside=[a['name'] for a in rect if min(a['bbox_um'][:2])<0 or a['bbox_um'][2]>33000+1e-6 or a['bbox_um'][3]>26000+1e-6]
 area=sum((a['bbox_um'][2]-a['bbox_um'][0])*(a['bbox_um'][3]-a['bbox_um'][1])/1e6 for a in rect)
 # Centre distances are a conservative graph input, never claimed pin-route length.
 positions={a['name']:((a['bbox_um'][0]+a['bbox_um'][2])/2,(a['bbox_um'][1]+a['bbox_um'][3])/2) for a in rect}
 for e in edges:
  src=e['source']; dst=e['destination']
  if src in leaves:
   pair=leaves[src]['field_pair'];src=f'pair{pair}' if pair is not None else None
  if src in positions and dst in positions:
   e['centre_L1_um']=sum(abs(x-y) for x,y in zip(positions[src],positions[dst]))
  else:e['centre_L1_um']=None
 crossing={str(x):sum(e['bits'] for e in edges if e['source'] in positions and e['destination'] in positions and min(positions[e['source']][0],positions[e['destination']][0])<x<max(positions[e['source']][0],positions[e['destination']][0])) for x in (8250,16500,24750)}
 readback=BASE/'s82_combined_r1/routed_q';rq=json.loads((readback/'readback_context.json').read_text());cs=json.loads((readback/'census_summary.json').read_text());term=json.loads((readback/'original_terminal.json').read_text())
 return dict(routed_q_readback=dict(context=rq,instance_count=cs['instances'],cell_area_um2=cs['cell_area_um2'],macro_count=cs['master_counts']['ot_rom_4096x274_m8'],actual_failure=term['acceptance']['checks'][0],retained_failed_abstract_not_adopted=True),combined_cut_bits=crossing,cuts_are_static_bus_census_not_cycle_demands=True,candidate=old['candidate'],source_inventory_commit=old['source_inventory_commit'],die_um=[33000,26000],die_mm2=858,rectangles=rect,leaves=leaves,edges=edges,rectangle_count=len(rect),collisions=collisions,out_of_die=outside,region_overflow=fail,named_no_overlap=not(collisions or outside or fail),named_area_mm2=area,unallocated_geometric_mm2=858-area,unallocated_is_not_capacity_credit=True,retained_screen_mm2=old['screen_mm2'],retained_screen_margin_mm2=old['screen_margin_mm2'],complement_credit_mm2=0,return_bits=sum(a['bits'] for a in storage),return_mm2=sum(a['bits'] for a in storage)*bit_area/1e6,return_nodes=8064,return_roots=128,weight_pairs=2388,q=1876,BF=512,weight_macros=9552,cfg_macros=16716,PHY_stacks=4,PHY_body_mm2=4*w*h/1e6,PHY_charged_again_mm2=0,PHY_inherited_containment_proven=False,field_shift_um=shift,PG=dict(die_power_W=204,voltage_V=.7,total_current_A=204/.7,M8_M9_width_um=2,M8_M9_pitch_um=22.56,M8_M9_spacing_um=9.28,per_layer_occupancy_fraction=4/22.56,macro_M7_upfeeds_qualified=False,source='caf733122ebf4f9fab44b1abf623cc882bd211b1 retained native PDN repair; live diagnostic preserved'),routing=dict(return_edge_bits=66,root_edge_bits=69,PHW=10,control_bits=16,PAR2_interdie_bits=0,combined_native_route_measured=False,actual_pin_endpoint_route_lengths=None,clock_buffer_source_union_placed=False,reset_release_qualified=False,PHY_clock_900ps_not_833ps=True),hardware_PnR_admitted=False,hierarchical_route_admitted=False,full_die_fit=False,rate_adopted=False,missing=['native q/BF routed abstracts and SS/FF at selected pipeline','return adder/control/clock/polarity/enable gates beyond storage slab','inherited465.477 debit replacement union incl287.022 complement and47.208 residual','W3 owner/controller/crossing service capacity and pin endpoints','finite full clock/reset/hold/via site assignment and native PG upfeeds','source-owned scalar publication/consumer/calendar deadlines'],source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PHY,ROOT/'tools/dsrom_c_s82_placement.py',*sorted(P.I.glob('*')),*sorted(readback.glob('*'))] if p.is_file()})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode();p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
