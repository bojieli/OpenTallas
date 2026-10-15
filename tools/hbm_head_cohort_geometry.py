#!/usr/bin/env python3
"""Head-cohort alternative; source/control changes explicit, never adopted."""
import argparse,json,math
from pathlib import Path
from hbm_forward_geometry_views import candidate
from hbm_system_known_placement import W,H
from hbm_system_geometry import lef
HEADS=[[0,1,4,5],[2,3,6,7],[8,9,12,13],[10,11,14,15]]

def build(g):
 c=candidate(g);b=c['boxes']
 for n in list(b):
  if b[n]['role']in ['ATT_quad','KV_code','KV_metadata','PV_memory','P_Q_memory','gather_reservation']:del b[n]
 mw,mh=51.408,20.79;qw,qh=514.89,562.95;cw,ch=174.744,70.488;pitchx=cw+21.6+qw+21.6+mw+21.6;pitchy=qh+43.2
 for a in range(4):
  ox=9000+3500*a;oy=9700
  for t in range(32):
   x=ox+(t%4)*pitchx;y=oy+(t//4)*pitchy
   b[f'ATT_q{t}_{a}']=dict(x=x+cw+21.6,y=y,w=qw,h=qh,role='ATT_quad',orientation='R0',source='same_actual128quad_inventory; head-cohort placement only',actual_head_set=HEADS[a])
   b[f'KVcohort{a}_code{t}']=dict(x=x,y=y+260,w=cw,h=ch,role='KV_code',orientation='R0',source='NEW fouractualmode34copies; separateRTL/writefanout/proofrequired')
   for d in range(16):b[f'H{a}_D{t}_{d}']=dict(x=x+cw+21.6+qw+21.6,y=y+50+d*(mh+5.4),w=mw,h=mh,role='PV_memory',orientation='R0',source='NEW quadcohort bankword permutation, notcurrentDsource')
  top=oy+8*pitchy+43.2
  for k in range(32):b[f'Pcohort{a}_{k}']=dict(x=ox+100+(k%8)*(mw+5.4),y=top+(k//8)*(mh+5.4),w=mw,h=mh,role='P_Q_memory',orientation='R0',source='NEW partitionof128Pstoresbyactualheadset; noP4copies')
  for k in range(16):b[f'Qcohort{a}_{k}']=dict(x=ox+700+(k%4)*(mw+5.4),y=top+(k//4)*(mh+5.4),w=mw,h=mh,role='P_Q_memory',orientation='R0',source='NEW queryheadrebanks16/cohort; schedule16edgescandidateunproved')
  for l in range(2):b[f'KVcohort{a}_meta{l}']=dict(x=ox+1100+l*(cw+21.6),y=top,w=cw,h=ch,role='KV_metadata',orientation='R0',source='NEW fourrealmode34copies, total136SRAM')
  for k in range(4):b[f'H{a}_gather{k}']=dict(x=ox+550+(k%2)*543.2,y=15000+(k//2)*493.2,w=500,h=450,role='gather_reservation',orientation='R0',source='actual4757FFleaf, NEW16instances,500x450unqualifiedplanningbody')
 # Preserve all32logical VM banks but stop pretending pairscatter localizes a
 # head. Eachhead writesall8NEbanks, so keep them inoneoutsidecentralcolumn.
 for q in ['SW','NW','SE','NE']:
  for bank in range(8):
   n=f'VM_{q}_{bank}';v=b[n];v['x']=23500 if q=='NE'else(7500 if q.endswith('W')else 25500);v['y']=(11000 if q=='NE'else(9200 if q.startswith('S')else 13300))+bank*(v['h']+43.2)
   for s in range(3):
    z=b[f'LG_{q}_{bank}_{s}'];z.update(x=v['x']-43.2-(s+1)*150.336-s*43.2,y=v['y'])
 conflicts=[];items=list(b.items())
 for i,(n,a)in enumerate(items):
  for m,d in items[i+1:]:
   if min(a['x']+a['w'],d['x']+d['w'])>max(a['x'],d['x'])+1e-6 and min(a['y']+a['h'],d['y']+d['h'])>max(a['y'],d['y'])+1e-6:conflicts.append([n,m])
 c.update(name='HEAD_cohort_shared_quad_alternative',rectangle_conflicts=conflicts,known_and_planning_rectangles=len(b),macro_and_prototype_box_area_mm2=sum(v['w']*v['h']for v in b.values()if v['role']!='gather_reservation')/1e6,unqualified_gather_reservation_mm2=3.6)
 c['actual_source_profiles']={'arithmetic':'same128quads, source/view/headmappingnotnewqualified','D':'NEW cohort/word permutation; notclosedD655source','K_V':'fourmode34copies136macros+2560guardFF, writefanoutfour/unpricedstations','P':'128banks total partition32/cohort; actualquadloadporttie/maskproofneeded','Q':'64banks total rebank16/cohort; changedperquadloadenable/headtag scheduleunproved'}
 c['new_architecture_obligations']={'cohort_heads':HEADS,'head_to_cohort':'{h[3],h[1]}','head_to_wordlane':'{h[2],h[0]}','inverse':'{cohort[1],lane[1],cohort[0],lane[0]}','quad_count':128,'additional_quad_count':0,'D_macros':2048,'KV_macros':136,'extra_KV_macros_vs34':102,'extra_KV_macro_area_mm2':102*cw*ch/1e6,'query_macros':64,'P_macros':128,'P_saved_vs4copies':384,'P_saved_macro_area_mm2':384*mw*mh/1e6,'registered_gather_leaves':16,'extra_gather_leaves_vsD':12,'gather_FF_total':16*4757,'QK_tree_spatial_scope':'eachhead16featuretilepartials/lane nowinsideonequadcohort; existingFP32orderunchanged','PV_output':'oneactiveheadcohortstillwritesall8NEbanks; needrealcohort-outputselector/registeredstations','naive_single_cohort_clock_root_sinks':6720+4*4757,'root_failure':'25748>15000; mustsplitactualclockroots. Atleast2roots/cohort bysinkcountalone; actualreach/fanoutmayneedmore, notadmitted.','additional_output_selector':'4×(2048data+64flags)→2112b; actualsource/area/registeredfaces/calendar notimplemented','query_schedule_candidate':'16edges=4localheads×4feature-subgroups, parallelcohorts; requiresnewactualperquadloadenable/headtagprogramme','whole_native_qualified':False}
 return c

def draw(c,path,quad):
 scale=.025;x0=20;y0=90;svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="980">','<rect width="100%" height="100%" fill="white"/>','<text x="20" y="25" font-size="19">H16 head-cohort component alternative: new bank/control profile (unqualified)</text>','<text x="20" y="48" font-size="12">Actual macro shapes / true32.984×25.981mm aspect. Four headsets,32feature quads each; shared QK/PV compute.</text>']
 colors={'SM_frame':'#ddd9e8','ATT_quad':'#d99035','KV_code':'#3c9b5e','KV_metadata':'#3c9b5e','PV_memory':'#c5508a','P_Q_memory':'#4e93bf','VM_bank':'#dfbf42','LG_prototype':'#adc592','HBM_PHY_abstract':'#aaa','SerDes':'#666','endpoint_group':'#9db9b5','programme':'#795f9f','gather_reservation':'#f1b0b5'}
 for i,(label,role) in enumerate([('32 full SM frames','SM_frame'),('shared QK/PV quads','ATT_quad'),('K/V banks','KV_code'),('local PV stores','PV_memory'),('Q/P stores','P_Q_memory'),('VM banks','VM_bank'),('LG taps','LG_prototype'),('gather reservations','gather_reservation')]):
  xx=20+(i%4)*215;yy=64+(i//4)*17
  svg.append(f'<rect x="{xx}" y="{yy-8}" width="10" height="10" fill="{colors[role]}"/><text x="{xx+14}" y="{yy}" font-size="11">{label}</text>')
 def xy(p):return x0+p[0]*scale,y0+(H-p[1])*scale
 svg.append(f'<rect x="{x0}" y="{y0}" width="{W*scale}" height="{H*scale}" fill="#fafafa" stroke="black"/>')
 for n,b in c['boxes'].items():
  x,y=xy((b['x'],b['y']+b['h']));svg.append(f'<rect x="{x}" y="{y}" width="{b["w"]*scale}" height="{b["h"]*scale}" fill="{colors[b["role"]]}" stroke="white" stroke-width=".3"><title>{n}: {b.get("source", "candidate")}</title></rect>')
 for a in range(4):
  x,y=xy((9000+3500*a,16300));svg.append(f'<text x="{x}" y="{y}" font-size="10">H{HEADS[a]}</text>')
 # Representativehead0/lane0 actualQK leaves are now allwithinheadcohort0.
 pts=[]
 for t in range(16):
  b=c['boxes'][f'ATT_q{t}_0'];pts.append((b['x']+quad['pins']['oy[0]'][0],b['y']+quad['pins']['oy[0]'][1]))
 for level in range(4):
  nxt=[]
  for k in range(0,len(pts),2):
   p,q=pts[k:k+2];mid=((p[0]+q[0])/2,(p[1]+q[1])/2+80)
   for e in [p,q]:
    x,y=xy(e);u,v=xy(mid);svg.append(f'<line x1="{x}" y1="{y}" x2="{u}" y2="{v}" stroke="#b42543" stroke-dasharray="3 2" stroke-width="1"/>')
   nxt.append(mid)
  pts=nxt
 notes=['Frozen G25 opcode369 is logical H1; this H16 component alternative is NOT canonical workload mapping.','Only head0/lane0 QK connectivity shown; real reduction nodes, clocks and stations remain unplaced.','K/V136macros (+102 /1.256370mm²); Q64 rebanks (schedule unproved); P128 (−384/.410409mm² vsP4).','D2048 banks use actual quad headsets; a new selector/control profile needs RTL and mutation proofs.','16registered gathers total76112FF (+57084vsD); modeled25748 sinks/cohort EXCEEDS15k: split clock roots.','3.6mm² gather reservations are UNQUALIFIED. Cohort→VM2048b selector and registered faces are UNPLACED.','Canonical head-major output still reaches ALL8NE banks. SU/SFU/SC/normalization/HC/IDX/PC/PG remain unplaced.']
 for i,n in enumerate(notes):svg.append(f'<text x="20" y="{780+23*i}" font-size="12">{n}</text>')
 sx,sy=xy((2000,1200));svg.append(f'<line x1="{sx}" y1="{sy}" x2="{sx+5000*scale}" y2="{sy}" stroke="black" stroke-width="2"/><text x="{sx}" y="{sy-5}" font-size="11">5000µm</text>')
 svg.append('</svg>');Path(path).write_text('\n'.join(svg))

def source_spans(c,quad):
 out=[]
 for cohort in range(4):
  for lane in range(2):
   pts=[(c['boxes'][f'ATT_q{16*lane+s}_{cohort}']['x']+quad['pins']['oy[0]'][0],c['boxes'][f'ATT_q{16*lane+s}_{cohort}']['y']+quad['pins']['oy[0]'][1])for s in range(16)]
   d=max(abs(x-u)+abs(y-v)for x,y in pts for u,v in pts)
   out.append(dict(cohort=cohort,lane=lane,source_pin_diameter_um=d,minimum_any_root_max_reach_um_lower_bound=d/2,minimum_500um_hops_lower_bound=math.ceil(d/1000)))
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=build(json.loads(Path(a.graph).read_text()));quad=lef('physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef');c['actual_quad_LEF_sha256']=quad['sha256'];Path(a.out).write_text(json.dumps(c,indent=2)+'\n');draw(c,Path(a.out).with_suffix('.svg'),quad);ref=Path(a.out).parent/'forward_D_geometry.json';spans={'head_cohort':source_spans(c,quad),'feature_D':source_spans(json.loads(ref.read_text()),quad),'quad_LEF_sha256':quad['sha256'],'scope':'Source-pin-only diameter, actualreductionnodesunplaced. Conditional500umhoplowerbound excludescelldelay,legalroutes,clock/PG andexistingpipelinebinding.'};(Path(a.out).parent/'QK_source_span_comparison.json').write_text(json.dumps(spans,indent=2)+'\n');print(json.dumps({k:c[k]for k in ['known_and_planning_rectangles','macro_and_prototype_box_area_mm2','unqualified_gather_reservation_mm2','rectangle_conflicts']}))
if __name__=='__main__':main()
