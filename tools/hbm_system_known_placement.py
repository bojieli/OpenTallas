#!/usr/bin/env python3
"""Whole-die structural precursors with every KNOWN footprint retained.

Unknown physical state remains unplaced and prevents adoption. These layouts
are not a complete floorplan or a synthetic substitute for missing hard views.
"""
import json,math,argparse
from pathlib import Path
W,H=32984.288,25980.528

def build(kind,graph):
 boxes={};gaps=[]
 def put(n,x,y,w,h,role,**kw):boxes[n]=dict(x=x,y=y,w=w,h=h,role=role,orientation='R0',**kw)
 # Fixed actual HBM PHY+controller abstract shoreline remains a reservation;
 # command-only physical PHY matching native controllers is still missing.
 for n,v in graph['nodes'].items():
  if n.startswith('phy_'):
   a=v['geometry'];put(n,*a['xy_um'],*a['outline_um'],'HBM_PHY_abstract',orientation_source=a['orientation'],native_command_view_missing=True)
 # Complete35 frames, not the old9.412mm2 model. Current16tile physical views
 # and static front binding remain missing inside every known outer frame.
 sw,sh=graph['nodes']['SM0']['geometry']['outline_um'];qs=['SW','SE','NW','NE']
 for i in range(32):
  q=qs[i//8];j=i%8;x=(200 if q.endswith('W') else 19500)+(j%2)*(sw+86.4);y=(2000 if q.startswith('S') else 16700)+(j//2)*(sh+86.4)
  put(f'SM{i}',x,y,sw,sh,'SM_frame',native_qualified=False)
 # Compare full central32pair field with four8pair fields. All actual quads,
 # code memories, PVmemories and narrow metadata remain explicit.
 qw,qh=514.89,562.95;mw,mh=51.408,20.79;localD=kind.startswith('D_local_');central=kind=='D_local_central_NE';cw,ch=174.744,70.488
 tw=2*qw+21.6+43.2+(2*(mw+5.4) if localD else 0);th=2*qh+21.6+43.2+ch+21.6+mh+43.2
 for t in range(32):
  if kind=='central_ATT':ox=14000+(t%8)*tw;oy=10000+(t//8)*th
  else:
   q=qs[t%4] if kind in ('bank_affinity_scattered_NE','D_local_scattered_NE','D_local_central_NE') else qs[t//8];j=([u for u in range(32) if u%4==t%4].index(t) if kind in ('bank_affinity_scattered_NE','D_local_scattered_NE','D_local_central_NE') else t%8);ox=(8500 if q.endswith('W') else 19500)+(j%4)*tw;oy=(9700 if q.startswith('S') else 13500)+(j//4)*th
  if central and j%4>=2:ox+=1100
  for a in range(4):put(f'ATT_q{t}_{a}',ox+(a%2)*(qw+21.6),oy+(a//2)*(qh+21.6),qw,qh,'ATT_quad',logical_tile=t,source_mapping_proposed=True)
  put(f'ATT_code{t}',ox+100,oy+2*qh+21.6+43.2,cw,ch,'KV_code',source='actual_same34_grouped_staging_successor')
  if localD:
   for cc in range(16):
    for hg in range(4):put(f'ATT_PVbank{(t*16+cc)*4+hg}',ox+2*qw+21.6+10.8+(hg%2)*(mw+5.4),oy+(hg//2)*(qh+21.6)+cc*(mh+5.4),mw,mh,'PV_memory',source='literal_opt_in_D2048',bank=(t*16+cc)*4+hg)
  else:
   for a in range(4):put(f'ATT_PVbank{t*4+a}',ox+a*(mw+5.4),oy+th-43.2-mh,mw,mh,'PV_memory',source='canonical128bankXOR_mapping',bank=t*4+a)
 # One P/Q/programme inventory, canonical NE VM allocation. P128 is newly
 # source proved; controller/transpose/status physical shapes stay unplaced.
 for b in range(192):put(('P' if b<128 else 'Q')+str(b),23500+(b%16)*(mw+5.4),16320+(b//16)*(mh+5.4),mw,mh,'P_Q_memory')
 for l in range(2):put(f'KV_metadata{l}',23200,16400+l*(ch+21.6),cw,ch,'KV_metadata')
 put('ATT_programme',24500,16500,cw,ch,'programme')
 # Northactualbody / southseparatelyprovisionalbody; no false alias.
 for q in qs:
  bw,bh=graph['nodes'][f'vm_{q}_bank0']['provisional_body_um'];x=(15000 if q.endswith('W') else (26100 if localD else 25900)) if kind in ('bank_affinity_scattered_NE','D_local_scattered_NE','D_local_central_NE') else (13500 if q.endswith('W') else 24900);y=9200 if q.startswith('S') else 13300
  for b in range(8):
   by=y+b*(bh+43.2);put(f'VM_{q}_{b}',x,by,bw,bh,'VM_bank',source_body_qualified=False)
   for s in range(3):put(f'LG_{q}_{b}_{s}',x-43.2-(s+1)*150.336-s*43.2,by,150.336,151.2,'LG_prototype',outline_measured=False,roots=1,read_return=10+4*s,write_return=7+4*s)
 if kind in ('bank_affinity_scattered_NE','D_local_scattered_NE','D_local_central_NE'):
  # Same logicalNE8banks/oneWG1; physical pairs follow bankaffinitygroups.
  # NoextraVMport or payloadmemory is added. AllotherNEclients now require
  # physicallydistributed read/control/ring joins and explicitcycle proof.
  for g,q in enumerate(qs):
   ox=8500 if q.endswith('W') else 19500;oy=9700 if q.startswith('S') else 13500;edge_x=ox+4*tw
   bs=[b for b in range(128) if (b//4)%4==g]
   for j,b in enumerate([] if localD else bs):put(f'ATT_PVbank{b}',edge_x+396+(j%4)*(mw+5.4),oy+1350+(j//4)*(mh+5.4),mw,mh,'PV_memory',bank=b,source='canonical128bankXOR_mapping')
   for half in range(2):
    b=2*g+half;bx=(ox+2*tw+666 if central else edge_x+666);by=oy+1000+half*(339.12+43.2)
    put(f'VM_NE_{b}',bx,by,393.12,339.12,'VM_bank',source_body_qualified=False,logical_NE_bank_unchanged=True)
    for stage in range(3):put(f'LG_NE_{b}_{stage}',bx-43.2-(stage+1)*150.336-stage*43.2,by-151.2-43.2,150.336,151.2,'LG_prototype',outline_measured=False,roots=1,read_return=10+4*stage,write_return=7+4*stage)
 # Same9SerDes, sameS5/N4/order/Y. E-adjacent endpoint envelope cannot fit
 # old250.632um gaps, so this explicit new shoreline-coordinate alternative
 # widens pitch. Pad/rank/clock contract and intervening FEC/PMA footprints
 # remain required; no existing cavity grant or direct612→PHY shortcut.
 pitch=771.216
 for side,count in [('S',5),('N',4)]:
  start=W/2-count*pitch/2
  for j in range(count):
   old=graph['nodes'][f'lk_{side}{j}']['geometry'];x=start+j*pitch;y=old['xy_um'][1]
   put(f'lk_{side}{j}',x,y,250.056,2250.216,'SerDes',requires_new_shoreline_contract=True)
   put(f'endpoint_{side}{j}',x+250.056+43.2,y+400,434.72,515.2,'endpoint_group',actual_FEC_PMA_adapter_not_placed=True,physical_qualified=False)
 # ExacthostPHYoutline, originalposition, where present in source legacy.
 # It is intentionally excluded here until current hostPHYsourcehash matches.
 conflicts=[]
 items=list(boxes.items())
 for i,(n,a) in enumerate(items):
  if min(a['x'],a['y'])<0 or a['x']+a['w']>W or a['y']+a['h']>H:gaps.append({'outside':n})
  for m,b in items[i+1:]:
   ox=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);oy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
   if ox>1e-6 and oy>1e-6:conflicts.append([n,m,ox,oy])
 drain_graph=None
 if localD:
  drain_graph={'source_sha256':'1acef905baf503c6488107b4465c393a519245a809718c4b9039cf37ec789918','mapped_actual_logic_um2':31942.5201,'clock_endpoints':{'clk':53,'bank_clk':[6688]*4},'groups':[],'physical_leaf_outlines_known':False,'extra_pipeline_stages_authorized':False}
  for g in range(4):
   ts=list(range(g,32,4));dests=[2*g,2*g+1]
   # Algebraic bank affinity is exact. This is not cycle or native proof.
   for t in ts:
    for cc in range(16):assert ((16*t+cc)//8)%8==2*g+cc//8
   drain_graph['groups'].append({'group':g,'tiles':ts,'source_macro_hierarchies':[f'g_tile[{t}].u_store.g_bank[b].u_data b=0..63' for t in ts],'local_selectors':'four headgroups then four head lanes;16 dimensions/tile','regional_mux':{'inputs':8,'payload_bits_per_input':512,'flags_per_input':16,'physical_outline_um':None,'proposed_region':'adjacent to destination bank pair; exact actual leaf required'},'destination_logical_NE_banks':dests,'source_tile_to_VM_ports_verified':False,'actual_commit_edges_per_record_engine_total':128,'same_phase_root':f'bank_clk[{g}]','outside_dependencies':['query/P gathers','QK lane reductions + score store','HC read/write','LG chains + hub/ring/control','clock buffers/PG/cut']})
 unresolved=[n for n,v in graph['nodes'].items() if v.get('geometry') is None and 'parent' not in v]
 return dict(actual_D_drain_hierarchy=drain_graph,name=kind,die_outline_um=[W,H],boxes=boxes,rectangle_conflicts=conflicts,outside=gaps,known_rectangle_count=len(boxes),placed_rectangle_area_mm2=sum(a['w']*a['h'] for a in boxes.values())/1e6,missing_physical_containers=unresolved,adoption_allowed=False,all_global_wires_or_cuts_scored=False,limits=['All coordinates are proposed; no source bound die placement grant.','SMframecontains16unqualifiedtileparents; no inheritednativephysicalclosure.','P/Qcontrollers, 589824transposeFFs,16384PVflagFFs and physicaldecode/relayhardware notplaced.','SharednativePCcontrollers,burst/sectoradapter,actualFEC/PMAgearboxandphysicalcommandPHYunplaced.','SU/SFU/HC/IDX/host/VMhub/ring/replay/clocktrees notplaced; empty regions are not proven capacity.','SerDespositions intentionally change withinS5/N4shorelines; realpad/rank/clocksourcecontract mustapprovebeforeadoption.','ExistingPHY+controllerabstractshoreline is retained only as conservative capacityreservation.','43.2/86.4umstreetsaregeometryspacing, notPG/cut<=0.60 proof.','Alltransferpaths mustuseactualpins,productionactivity,realreachandexplicitfixedcalendarstationsbeforeanywinner.'])

def pv_write_affinity(c,vm_path,sram_path):
 from hbm_system_geometry import lef
 raw=json.loads(Path(vm_path).read_text());pins={}
 for n,_,_,_,sh in raw['bterms']:
  if sh:
   _,a=sh[0];pins[n]=((a[0]+a[2])/2,(a[1]+a[3])/2)
 mem=lef(sram_path);total=0.;worst=0.;pairs=0;per_bank=[0.]*8
 # Canonical FP32[head][dim], eight consecutive256bVMsectors per edge.
 # This architectural relation bypasses still-unplaced selection/adapterFFs;
 # it is a geometric source-to-destination affinity, not one legal timing hop.
 for h in range(16):
  for dim in range(512):
   tile,cc=divmod(dim,16);bank=(tile*16+cc)*4+h//4 if c['name'].startswith('D_local_') else (tile*4+h//4)^((cc&3)|((cc&12)<<2));vb=(dim//8)%8
   src=c['boxes'][f'ATT_PVbank{bank}'];dst=c['boxes'][f'VM_NE_{vb}']
   for k in range(32):
    sx,sy=mem['pins'][f'rd_out[{(h%4)*32+k}]'];dx,dy=pins[f'wq1[{8+(dim%8)*32+k}]']
    d=abs(src['x']+sx-dst['x']-dx)+abs(src['y']+sy-dst['y']-dy)
    total+=d;per_bank[vb]+=d;worst=max(worst,d);pairs+=1
 return dict(boundary='canonical PV storage -> NE VM WG1',bit_pairs_per_record=pairs,bit_um_per_record=total,max_actual_pin_affinity_um=worst,per_VM_bank_bit_um=per_bank,optimistic_max_additional_500um_stations=max(0,math.ceil(worst/500)-1),scope='Actual source SRAM rd_out and actual destination VMwq1 payloadpin centres at proposed positions; missing output adapter/capture/clock/relay hardware means affinity only, not direct net timing or full outside objective.',source_LEF_sha256=mem['sha256'])

def pv_capture_affinity(c,quad_path,sram_path):
 from hbm_system_geometry import lef
 q=lef(quad_path);m=lef(sram_path);lookup={base+4*(l//2)+l%2:(a,l) for a,base in enumerate([0,2,8,10]) for l in range(4)};total=0.;worst=0.
 for t in range(32):
  for h in range(16):
   a,l=lookup[h];src=c['boxes'][f'ATT_q{t}_{a}']
   for cc in range(16):
    bank=(t*16+cc)*4+h//4 if c['name'].startswith('D_local_') else (t*4+h//4)^((cc&3)|((cc&12)<<2));dst=c['boxes'][f'ATT_PVbank{bank}']
    for k in range(32):
     sx,sy=q['pins'][f'oy[{l*32+k}]'];dx,dy=m['pins'][f'wd_in[{(h%4)*32+k}]'];d=abs(src['x']+sx-dst['x']-dx)+abs(src['y']+sy-dst['y']-dy);total+=d;worst=max(worst,d)
 return dict(bit_pairs_per_record=262144,bit_um_per_record=total,max_actual_pin_affinity_um=worst,scope='Quad oy -> selected-profile PVstorage wd input realpins at proposed positions; unplaced selection/capture/status/relay hardware, not direct timing hop.')

def draw(cases,path):
 labels={'central_ATT':'A: central attention reference','four_ATT_groups':'B: four attention groups','bank_affinity_scattered_NE':'C: bank affinity / lower-area fallback','D_local_scattered_NE':'D1: local PV / bank pairs at field edge','D_local_central_NE':'D2: local PV / central bank-pair corridor'}
 scale=.0175;svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="1280">','<rect width="100%" height="100%" fill="white"/>','<text x="15" y="26" font-size="20">HBM whole-die structural precursors: all known macro footprints, missing state explicit</text>','<text x="15" y="48" font-size="13">32.984 × 25.981 mm, same scale / real dimensions; incomplete layouts. No physical, pad or routing adoption. Gray gaps are not proven free capacity.</text>']
 colors={'SM_frame':'#aaa5c8','ATT_quad':'#d99035','KV_code':'#55a46d','PV_memory':'#cf4a91','P_Q_memory':'#4e8fbd','KV_metadata':'#178c45','programme':'#795f9f','VM_bank':'#e4c85c','LG_prototype':'#a6c66b','HBM_PHY_abstract':'#888','SerDes':'#444','endpoint_group':'#75aaa9'}
 for i,c in enumerate(cases):
  x0=20+(i%2)*625;y0=100+(i//2)*570;svg += [f'<text x="{x0}" y="{y0-20}" font-size="17">{labels[c["name"]]}</text>',f'<rect x="{x0}" y="{y0}" width="{W*scale}" height="{H*scale}" fill="#f7f7f7" stroke="black"/>']
  for n,b in c['boxes'].items():
   x=x0+b['x']*scale;y=y0+(H-b['y']-b['h'])*scale;w=b['w']*scale;h=b['h']*scale
   svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{colors[b["role"]]}" stroke="white" stroke-width=".35"><title>{n} {b["role"]}, {b["w"]}×{b["h"]} µm; all proposed, unqualified</title></rect>')
   if b['role']=='SM_frame':svg.append(f'<text x="{x+4}" y="{y+h/2}" font-size="10">{n}</text>')
  svg.append(f'<text x="{x0}" y="{y0+H*scale+20}" font-size="12">PV affinity capture {c["PV_capture_pin_affinity"]["bit_um_per_record"]/1e6:.1f} / drain {c["PV_external_pin_affinity"]["bit_um_per_record"]/1e6:.1f} Mbit·µm; no mux/clock closure.</text>')
  svg.append(f'<text x="{x0}" y="{y0+H*scale+38}" font-size="12">{c["known_rectangle_count"]} boxes; {c["placed_rectangle_area_mm2"]:.3f} mm²; overlaps {len(c["rectangle_conflicts"])}; NE banks '+('four local pairs' if ('scattered' in c['name'] or c['name']=='D_local_central_NE') else 'one east column')+'</text>')
 svg += ['<text x="20" y="1230" font-size="13">Purple:32 complete SM frames (unqualified); orange:128 quads; green:34 KV; pink:128/2048 PV; blue:192 P/Q; yellow:32 VM.</text>','<text x="20" y="1250" font-size="13">96 LG prototypes, nine SerDes/endpoint groups and four historical PHY reservations retained. All other source state stays unplaced.</text>','</svg>'];Path(path).write_text('\n'.join(svg))

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--out',required=True);p.add_argument('--vm-pin-json',default='/home/ubuntu/wt/hbm-vm-static-1014/results/arch/hbm_vm_bank_static_1015/native_pin_pg_diagnostic/native_bank_actual_pin_pg.json');p.add_argument('--quad-lef',default='physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef');p.add_argument('--sram-lef',default='physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef');a=p.parse_args();g=json.loads(Path(a.graph).read_text());r=dict(schema='opentallas.hbm.system_geometry.known_placement.v1',candidates=[build(k,g) for k in ['central_ATT','four_ATT_groups','bank_affinity_scattered_NE','D_local_scattered_NE']]);
 for c in r['candidates']:
  c['PV_external_pin_affinity']=pv_write_affinity(c,a.vm_pin_json,a.sram_lef);c['PV_capture_pin_affinity']=pv_capture_affinity(c,a.quad_lef,a.sram_lef);c['PV_capture_plus_drain_bit_um']=c['PV_external_pin_affinity']['bit_um_per_record']+c['PV_capture_pin_affinity']['bit_um_per_record']
 Path(a.out).write_text(json.dumps(r,indent=2)+'\n');draw(r['candidates'],Path(a.out).with_suffix('.svg'));print(json.dumps([{k:v for k,v in c.items() if k in ['name','known_rectangle_count','placed_rectangle_area_mm2','rectangle_conflicts','outside']} for c in r['candidates']]))
if __name__=='__main__':main()
