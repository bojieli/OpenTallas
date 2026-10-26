#!/usr/bin/env python3
"""Source-versioned forward D candidate: actual known shapes + explicit unknowns.
Connectivity overlays are required graph edges, not routed nets/timing estimates.
"""
import json,argparse,hashlib
from pathlib import Path
from hbm_system_known_placement import build,W,H
from hbm_system_geometry import lef

def candidate(g):
 c=build('D_local_central_NE',g);b=c['boxes'];mw,mh=51.408,20.79
 for s in range(64):
  sl=s//4;q=b[f'ATT_q{sl}_0'];b[f'Q{128+s}'].update(x=q['x']+310+(s%4)*(mw+5.4),y=q['y']+1190.7,source='actual_query64partition_363c3cfaa',stripe=s,field=sl%4)
 for n in list(b):
  if n.startswith('P')and n[1:].isdigit():del b[n]
 for field in range(4):
  q=b[f'ATT_q{field}_0'];q2=b[f'ATT_q{field+16}_0'];top=q2['y']+(2*562.95+21.6+43.2+70.488+21.6+20.79+43.2)
  for s in range(128):b[f'Pfield{field}_{s}']=dict(x=q['x']+800+(s%16)*(mw+5.4),y=top+43.2+(s//16)*(mh+5.4),w=mw,h=mh,role='P_Q_memory',orientation='R0',source='P4_4408c92e6',physical_shape_status='actual32x128macro_only; fieldcontroller/mux/clockunplaced')
  # PIN-FIRST planning reservation only; actual4759pins not yet hardened.
  tw=2*514.89+21.6+43.2+2*(mw+5.4)
  b[f'gather_plan{field}']=dict(x=q['x']+2*tw+43.2,y=q['y']+1700,w=500,h=450,role='gather_reservation',orientation='R0',physical_body_qualified=False,source='registered_gather_adf0ef9d5',planning_area_mm2=.225,realFF=4757,root_with_PV=11445,added_edges=2)
 conflicts=[];items=list(b.items())
 for i,(n,a)in enumerate(items):
  for m,d in items[i+1:]:
   if min(a['x']+a['w'],d['x']+d['w'])>max(a['x'],d['x'])+1e-6 and min(a['y']+a['h'],d['y']+d['h'])>max(a['y'],d['y'])+1e-6:conflicts.append([n,m])
 c.update(name='forward_D_mode34_Q64_P4_registered',rectangle_conflicts=conflicts,known_and_planning_rectangles=len(b),macro_and_prototype_box_area_mm2=sum(v['w']*v['h']for v in b.values()if v['role']!='gather_reservation')/1e6,unqualified_gather_reservation_mm2=.9)
 c['actual_source_profiles']={'mode34':'9cf430e13','query64':'363c3cfaa','P4':'4408c92e6','registered_gather':'adf0ef9d5','quad_LEF_sha256':'ac510d59eafc85b5b516f40e21227e532fbe63527e23d772e5ebc357cf6b89f4'}
 c['missing_physical_areas']=['P4controller/muxlogic: exactwholeP4logic6235.80768um2,224FF unplaced','mode34guard640FF+mode/control','SC256macros+32768status+1024readflags','589824VtransposeFF','QK32lane/headreductiontrees andPVblockmergeactualhardenedviews','SU/SFUactual128SRAM+10reducerSRAM+alllogic','HC/IDX/host/normalization/sinkfetch','sharedHBMPCcontrollers+command-onlyPHY/readburstsuccessor','FEC/PMAstreamadapter','VMhub/ring/replay and1092trackbridgecorridors','clocktrees/PG/halos,allnativeSID/headmapping/routecuts']
 c["canonical_HEADS1_binding_gap"]={'canonical_programme': 'frozenG25opcode369 logicalH1', 'hardware_profile': 'actual H16/D512 32pairs128quads retained unless explicitly replaced by source-qualified successor', 'activity': 'physical head0 fixed; all H16 arithmetic/buses/clocks retained; actual native writer/wholearith join open', 'H1_owner_report': {'query_fill_slots':128,'query_real_VM_bursts':8,'query_zero_fill_slots':120,'P_T128_fill_slots':32,'P_T128_real_VM_bursts':2,'P_T128_zero_fill_slots':30,'P_T640_fill_slots':160,'P_T640_real_VM_bursts':10,'P_T640_zero_fill_slots':150,'SC_T128_64word_commits':2,'SC_T640_64word_commits':10,'PV_64word_commits':8,'physical_head':0,'physical_quad_cohort':[0,1,4,5],'all512_HG1_execute_schedule':True,'zero_fills_are_real_SRAM_writes':True,'source_artifact_pending':True}, 'native_P_successor': '3ad2f11d8 frozen5c1bb65fd, HEADS1 scaledSC/futureE lease proof in progress', 'H16_results': 'component architecture and workload exploration only; no native canonical headmap claim'}
 return c

def draw(c,path,quad,mem,code):
 vm_path=Path('/home/ubuntu/wt/hbm-vm-static-1014/results/arch/hbm_vm_bank_static_1015/native_pin_pg_diagnostic/native_bank_actual_pin_pg.json');vm=json.loads(vm_path.read_text());vm_pins={}
 for n,_,_,_,sh in vm['bterms']:
  if sh:
   _,a=sh[0];vm_pins[n]=((a[0]+a[2])/2,(a[1]+a[3])/2)
 scale=.017;svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1470">','<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="context-stroke"/></marker><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0,5L5,0" stroke="#b63b55" stroke-width="1"/></pattern></defs>','<rect width="100%" height="100%" fill="white"/>','<text x="16" y="25" font-size="20">HBM H16 component forward-flow study: shared compute, local stores, unfinished boundaries</text>','<text x="16" y="47" font-size="13">All panels same 32.984×25.981 mm die / true aspect ratio. Lines show required connectivity; unplaced intermediates prevent timing/routing claims.</text>','<text x="16" y="68" font-size="13">K → QK(shared orange) → SC → scale/MAX/EXP → rawE + BF16EB → PV(same orange + localV) → PV/DEN → inverseRoPE</text>','<text x="16" y="88" font-size="12">Solid endpoint dots use actual LEF pins where present. Dashed diamonds/lines are unplaced reduction/mux obligations; they are not free wire paths.</text>']
 colors={'PC_prototype':'#7294a5','SM_frame':'#d3d0e1','ATT_quad':'#db9a46','KV_code':'#288750','PV_memory':'#cd5894','P_Q_memory':'#5f9dc9','KV_metadata':'#288750','programme':'#795f9f','VM_bank':'#dfbf42','LG_prototype':'#b0ca8d','HBM_PHY_abstract':'#aaa','SerDes':'#555','endpoint_group':'#9db9b5','gather_reservation':'url(#hatch)'}
 titles=['QK phase: feature reductions cross fields AND central seams','KV/PV phase: same34 mode-local code; localP4 + transpose missing','PV drain: local capture → registered gather → SAME NE eight banks','Algorithm and outside boundaries: local reductions ≠ global COLL']
 notes=[['Representative head0: 2 lanes ×16 featurepartials, 32b/edge each.','H1 uses physicalhead0; full local H16 buses/clocks still present.','Query64: 512b/client;128fill slots =8H1 VM bursts +120zero slots.'],['Green bankt locally feeds QKtile t OR Vtile t after distinct fullreload.','P4: +384SRAM=.410409mm²; global1024b converted write fan4.','Pissue1024b/field; T6402.5MiB quadport traffic remains, now local.'],['Shown4historical full-gather reservations; real nativeclock FAILED.','Current8bank-half leaves2386FF each, same+2edges; not placed here.','Same128commits; nominal11460 sinks/region, no actualCTS grant.'],['NoCOLL inside component QK featuretrees, REDMAX/REDSUM or PVmerge.','Post-o_own Oprojection/COLL is downstream; rank/headmapping OPEN.','Quarterbridge1092tracks/corridor has no actualhubhome/pinroute grant.']]
 def point(b,p):return b['x']+p[0],b['y']+p[1]
 for panel in range(4):
  x0=20+(panel%2)*655;y0=140+(panel//2)*595
  def xy(p):return x0+p[0]*scale,y0+(H-p[1])*scale
  def line(a,b,color,width=1,dashed=True):
   ax,ay=xy(a);bx,by=xy(b);svg.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{color}" stroke-width="{width}" opacity=".72" '+('stroke-dasharray="4 3" 'if dashed else'')+'marker-end="url(#arrow)"/>')
  svg.append(f'<text x="{x0}" y="{y0-15}" font-size="14">{titles[panel]}</text>');svg.append(f'<rect x="{x0}" y="{y0}" width="{W*scale}" height="{H*scale}" fill="#f8f8f8" stroke="black"/>')
  for n,b in c['boxes'].items():
   x,y=xy((b['x'],b['y']+b['h']));svg.append(f'<rect x="{x}" y="{y}" width="{b["w"]*scale}" height="{b["h"]*scale}" fill="{colors[b["role"]]}" stroke="white" stroke-width=".3"><title>{n} {b["w"]}×{b["h"]}µm; {b.get("source","candidate reservation")}</title></rect>')
   if b['role']=='ATT_quad':
    for pin,col in [('ld_w[0]','#146fa6'),('oy[0]','#a52235')]:
     px,py=xy(point(b,quad['pins'][pin]));svg.append(f'<circle cx="{px}" cy="{py}" r=".7" fill="{col}"/>')
  if panel==0:
   for lane in range(2):
    ends=[point(c['boxes'][f'ATT_q{16*lane+s}_0'],quad['pins']['oy[0]'])for s in range(16)]
    for lev in range(4):
     nxt=[]
     for k in range(0,len(ends),2):
      a,b=ends[k:k+2];mid=((a[0]+b[0])/2,(a[1]+b[1])/2+110*(1 if lane==0 else-1));line(a,mid,'#be2948',1.1);line(b,mid,'#be2948',1.1);px,py=xy(mid);svg.append(f'<path d="M{px},{py-3}L{px+3},{py}L{px},{py+3}L{px-3},{py}z" fill="white" stroke="#be2948"/>');nxt.append(mid)
     ends=nxt
   for sl in [0,1,4,5]:
    qb=c['boxes'][f'Q{128+4*sl}'];src=point(qb,mem['pins']['rd_out[0]'])
    for tile in [sl,sl+16]:line(src,point(c['boxes'][f'ATT_q{tile}_0'],quad['pins']['ld_w[0]']),'#1478aa',1.3)
  if panel==1:
   for t in [0,1,4,5,16,17,20,21]:line(point(c['boxes'][f'ATT_code{t}'],code['pins']['rd_out[0]']),point(c['boxes'][f'ATT_q{t}_0'],quad['pins']['ib[0]']),'#237d3b',1.3)
   for g in range(4):
    store=c['boxes'][f'Pfield{g}_0'];src=(store['x']+400,store['y']+80)
    for t in range(g,32,4):line(src,point(c['boxes'][f'ATT_q{t}_0'],quad['pins']['ld_w[0]']),'#217ab0',1.2)
  if panel==2:
   for g in range(4):
    p=c['boxes'][f'gather_plan{g}'];sink=(p['x'],p['y']+p['h']/2)
    for t in range(g,32,4):line(point(c['boxes'][f'ATT_PVbank{64*t}'],mem['pins']['rd_out[0]']),sink,'#a52b79',1)
    for vb in [2*g,2*g+1]:
     v=c['boxes'][f'VM_NE_{vb}'];line((p['x']+p['w'],p['y']+p['h']/2),point(v,vm_pins['wq1[8]']),'#592ca2',1.6)
  if panel==3:
   svg += [f'<rect x="{x0+110}" y="{y0+200}" width="355" height="80" fill="white" fill-opacity=".94" stroke="#ba3c48" stroke-dasharray="5 3"/>',f'<text x="{x0+120}" y="{y0+220}" font-size="12">UNPLACED: SC256 / SU-SFU / MAX-SUM / HC-IDX</text>',f'<text x="{x0+120}" y="{y0+240}" font-size="12">589824 transposeFF / PCcontrollers / sink-DEN-norm</text>',f'<text x="{x0+120}" y="{y0+260}" font-size="12">Actual clocks, PG, halos, COLL hubs and source head map</text>']
  for i,text in enumerate(notes[panel]):svg.append(f'<text x="{x0}" y="{y0+H*scale+20+17*i}" font-size="11">{text}</text>')
  sx,sy=xy((1500,1200));svg.append(f'<line x1="{sx}" y1="{sy}" x2="{sx+5000*scale}" y2="{sy}" stroke="black" stroke-width="2"/><text x="{sx}" y="{sy-5}" font-size="10">5000µm</text>')
 if any(v['role']=='PC_prototype' for v in c['boxes'].values()):
  svg.append('<text x="20" y="1440" font-size="12">Blue shoreline strips:128 PC prototypes244.512×345.6µm, SAME source/inventory; newoutline pin/PG/clock and commandPHY still UNQUALIFIED.</text>')
 svg += ['<text x="20" y="1360" font-size="12">Inventory shown:128 realquad outlines /2048PV /34KV /64Q /512P SRAMs;32SMframes,32VMbanks,96LGprototypes,9SerDes/endpoints,4PHYreservations.</text>','<text x="20" y="1380" font-size="12">Missing realhardware listed above prevents whole-die fit/clock/cut/native-performance closure. White space is unverified. Orange compute is shared by QK/PV phases.</text>',f'<text x="20" y="1400" font-size="11">Sources mode34 9cf430e13; Q64 363c3cfaa; P4 4408c92e6; gather adf0ef9d5; quadLEF {quad["sha256"][:16]}…</text>','<text x="20" y="1420" font-size="11">Canonical logicalH1 fixes physicalhead0; fifteen zero-filled Q/P slots and ALL local buses/clocks retained. Native writer/wholearith join OPEN.</text>','</svg>'];Path(path).write_text('\n'.join(svg))

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=candidate(json.loads(Path(a.graph).read_text()));Path(a.out).write_text(json.dumps(c,indent=2)+'\n');draw(c,Path(a.out).with_suffix('.svg'),lef('physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef'),lef('physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef'),lef('physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef'));print(json.dumps({k:c[k]for k in ['known_and_planning_rectangles','macro_and_prototype_box_area_mm2','unqualified_gather_reservation_mm2','rectangle_conflicts']}))
if __name__=='__main__':main()
