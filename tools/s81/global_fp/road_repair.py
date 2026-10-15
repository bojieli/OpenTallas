#!/usr/bin/env python3
"""Road-preserving S81 screen; source-pinned geometry, never route qualification."""
import argparse, gzip, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import candidates as C
import placer as P
import score as S

REGION=[13942.8,1807.9,19040.4,23632.0]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--plan',required=True);a=ap.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 gp=Path('results/arch/s81_globalfp_1015/graph.json');g=json.loads(gp.read_text());base=C.base_rects(g)
 base['sp_hc_s'][3]+=194.4;base['sp_hc_t'][3]+=233.28;base['sp_gather'][3]=1045.416
 # Current VM bodies are PARTIAL lower bounds, never complete hard macros.
 vm={'2x2':[3952.8,4903.2],'1x4v':[1965.6,9828.]}
 plan=json.load(gzip.open(a.plan));segments=[]
 for chain in plan['chain_paths']:
  for p,q in zip(chain['path'],chain['path'][1:]):
   if abs(p[0]-q[0])<1e-5 and 15670.8<=p[0]<=17312.4 and p[1]!=q[1]:
    lo,hi=sorted([p[1],q[1]]);segments.append(dict(lo=lo,hi=hi,bits=sum(chain['lanes'])+len(chain['lanes']),chain=chain['chain']))
 def peak(ss):
  ev=[]
  for s in ss:ev.extend([(s['lo'],s['bits']),(s['hi'],-s['bits'])])
  cur=0;best=(0,0)
  for y,d in sorted(ev):
   cur+=d
   if cur>best[0]:best=(cur,y)
  active=[s for s in ss if s['lo']<=best[1]<s['hi']]
  return dict(bits=best[0],y=best[1],minimum_width_at_060=best[0]/S.CAP_PER_UM/.6,active_chains=active)
 tree=[s for s in segments if s['chain'].startswith(('cx','cr'))]
 cuts=dict(all_chains=peak(segments),broadcast_return_only=peak(tree),source_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),source=a.plan)
 rows=[]
 for w in (432.,648.,864.,1080.,1641.6):
  rows.append(dict(width=w,all_chain_share=cuts['all_chains']['bits']/S.CAP_PER_UM/w,tree_only_share=cuts['broadcast_return_only']['bits']/S.CAP_PER_UM/w))
 h=REGION[3]-REGION[1];w=REGION[2]-REGION[0]
 towers=['sp_su_s','sp_hc_s','sp_hc_t']
 mains=['sp_su_s','sp_hc_s','sp_hc_t','sp_capture','sp_gather','sp_pq','sp_wfc','sp_sseq','sp_collective','sp_host']
 # PQ+ROM needs1728 width; using the smaller graph PQ1672.248 also proves the same bound.
 th=sorted(base[n][3] for n in towers)
 need2=sum(th[:2])+vm['2x2'][1]
 sum1=sum(base[n][3] for n in mains)+vm['1x4v'][1]
 widths=sorted([base[n][2] for n in mains]+[vm['1x4v'][0]])
 assert vm['2x2'][0]+min(base[n][2] for n in towers)>w
 assert sum(base[n][2] for n in towers)>w
 assert sum(widths[:3])>w and sum1>2*h and need2>h
 bounds=dict(hub_width=w,hub_height=h,current_vm_lower_bounds=vm,
  two_by_two=dict(minimum_tower_span=sum(th[:2]),minimum_total_height=need2,height_deficit=need2-h,reason='VM cannot overlap any tower in y; three towers cannot overlap each other simultaneously; interval-graph coloring gives tower span >= sum of two shortest heights.'),
  one_by_four=dict(three_smallest_main_widths=widths[:3],three_width_sum=sum(widths[:3]),total_main_height=sum1,capacity_at_two_rectangles=2*h,height_sum_deficit=sum1-2*h,minimum_height_increase=(sum1-2*h)/2,reason='At most two main rectangles fit at any y. Integrate occupied rectangle count over height. This excludes MIX4, HCX, halos, crossing corridor and missing VM leaves.'),
  literal1641road=dict(remaining_width=w-1641.6,two_smallest_tower_width=sum(sorted(base[n][2] for n in towers)[:2]),tower_height_sum=sum(base[n][3] for n in towers)))
 # Constructive LOWER-BOUND witness after an explicit enlarged hub; it is deliberately not adoptable.
 dims={n:base[n][2:] for n in C.MOVABLE};dims['sp_vm']=vm['1x4v'];dims['sp_pq'][0]=1728.;dims['mix4']=[1613.5,1542.2]
 columns=[['sp_su_s','sp_hc_s'],['sp_hc_t','sp_collective','mix4','sp_host','hcx_ctl','hcx_gatherpack','embed_expand','engram_dispatch'],['sp_vm','sp_wfc','sp_sseq','sp_pq','sp_capture','sp_gather']]
 rects={};xx=REGION[0];topy=REGION[1]
 for col in columns:
  cw=max(dims[n][0] for n in col);yy=REGION[1]
  for n in col:
   bw,bh=dims[n];rects[n]=[xx,yy,bw,bh];yy+=bh+21.6
  topy=max(topy,yy);xx+=cw+21.6
 roadx=xx-21.6;rw=864.;right=roadx+rw
 corridor=[REGION[0],topy,right-REGION[0],1512.]
 assert topy+1512<=REGION[3]
 witness=dict(schema='opentallas.s81.hub_layout.v1',scope='REJECTED_ENLARGED_HUB_LOWER_BOUND_WITNESS_NOT_GENERATOR_INPUT',source='eb9cfa044 current_system_geometry partial VM body; no complete current VM macro',blocks={n:r for n,r in rects.items() if n.startswith('sp_')},mix4=rects['mix4'],corridor=corridor,vertical_road=[roadx,REGION[1],rw,h],required_hub_x=[REGION[0],right],extra_width=right-REGION[2],e_stack=dict(order=['sp_wfc','sp_sseq','sp_pq','sp_capture','sp_gather']),fatal=['Crosses current S14E and eastern field homes; requires connected system repartition, no naive field translation fits edge.','VM is partial lower bound and omits cap/CDC/router/global/current missing leaves.','Tree-only source cut fits864 but all-chain source cut fails; no rerouted incident graph or relay station allocation.'])
 (out/'enlarged_1x4v_hub_layout_REJECTED.json').write_text(json.dumps(witness,indent=1))
 audit=dict(schema='opentallas.s81.road_repair.audit.v1',scope='SCREEN_ONLY_HARD_INFEASIBILITY_NO_GRT',source_commit='eb9cfa044920f23a9565d6c5fda43d2d5f217d06',graph_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),vm_geometry_status='OPEN: partial source body only; current complete parent footprint unavailable',vm_source='tools/s81/current_system_geometry.py and results/arch/s81_system_current_1015/report.json @ fdca7e391; VM owner confirms current inventory changed to352memory leaves / partial502memory+write leaves550roots',new_norm_status='Parent NORM correction adds further194.4/233.28 beyond v23; actualNT810 metadata and64source rows pending. Existing tower bounds remain conservative lower bounds.',hc_source='tools/s81/contract_v23_hc_budget.py (+194.4/+233.28); v24 changes pins, no outline growth',bounds=bounds,cuts=cuts,road_width_comparison=rows,new_BF_x2=dict(extra_E_lane=538,coincident_peak_tree_bits=cuts['broadcast_return_only']['bits']+538,minimum_width_at060=(cuts['broadcast_return_only']['bits']+538)/S.CAP_PER_UM/.6,road_width_shares=[dict(width=r['width'],share=(cuts['broadcast_return_only']['bits']+538)/S.CAP_PER_UM/r['width']) for r in rows],scope='Sensitivity from main S-BIND bf-x2-pair538lane; exact new source path/coincidence needs GEN'),witness=dict(file='enlarged_1x4v_hub_layout_REJECTED.json',extra_width=witness['extra_width']),limitations=['Cuts are exact vertical logical lane counts from GEN18c chain_paths, with one fclk per lane; not current routed tracks or CTS/PG capacity.','21.09375 bits/um from score.py is a historical effective two-layer estimate, not a new road-specific layer grant.','5324 tree-only load excludes hub/service chains; cannot qualify a narrowed road without explicit rerouting and all incident graph coverage.','No source current VM complete outline, no GRT/STA or native qualification.'])
 (out/'audit.json').write_text(json.dumps(audit,indent=1))
 print(json.dumps(dict(bounds=bounds,road_width_comparison=rows,witness_extra_width=witness['extra_width']),indent=1))
if __name__=='__main__':main()
