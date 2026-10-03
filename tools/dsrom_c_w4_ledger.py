"""Scenario C W4: source-bound attribution, without physical complement credit."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_c_w4_20261003'

def union_area(rects):
 xs=sorted({v for r in rects for v in (r[0],r[2])});area=0
 for a,b in zip(xs,xs[1:]):
  ys=sorted((r[1],r[3]) for r in rects if r[0]<b and r[2]>a);end=None;length=0
  for lo,hi in ys:
   start=lo if end is None else max(lo,end)
   length+=max(0,hi-start);end=hi if end is None else max(end,hi)
  area+=(b-a)*length
 return area/1e12

def build():
 d={p.stem:json.loads(p.read_text()) for p in (BASE/'inputs').glob('*.json')}
 f=d['fixed'];s=d['shard']['area'];n=d['noecc'];m=d['map']['area'];w=d['wake']['area'];p=d['pg']['area']
 def term(name,value,scaling,kind,origin):return dict(name=name,mm2=value,scaling=scaling,kind=kind,source=origin)
 terms=[term('field macro clearance',s['added_field_macro_clearance_mm2'],'per-element geometry','halo policy','shard.area'),term('cfg halo grid',s['added_cfg_halo_grid_mm2'],'per-element geometry','halo policy','shard.area'),term('reservation rounding',s['additional_reservation_rounding_mm2'],'per-die accounting','rounding policy','shard.area'),term('retained main request and mux proxy',n['area']['new_conservative_per_shard_screen_mm2']-s['revised_conservative_screen_mm2'],'provider instance counts','proposal cell reservation','noecc.area'),term('selector state replacement',n['full_topk_slot']['additional_state_only_debit_once_mm2'],'per-die service','state floor','noecc.full_topk_slot'),term('BF frame growth',m['BF_complete_frame_growth_charged_once_mm2'],'per BF element','frame reservation','map.area'),term('field row whitespace',m['extra_row_whitespace_noncontainment_policy_mm2'],'packing-dependent','noncontainment policy','map.area'),term('selector complete replacement',w['complete_selector_extra_charged_once_mm2'],'per-die service','slot reservation','wake.area'),term('q frame growth',w['mapped_q_growth_charged_once_mm2'],'per q element','frame reservation','wake.area'),term('root clock buffer',w['retained_full_root_clock_buffer_increment_at50pct_mm2'],'per element clock','cell floor','wake.area'),term('selector escape corridor',p['escape_corridor_increment_mm2'],'per-die service','route reservation','pg.area')]
 start=f['single_parallel_successor']['conservative_priced_per_shard_mm2'];end=p['screen_with_corridor_mm2'];delta=sum(t['mm2'] for t in terms)
 assert abs(start+delta-end)<1e-8
 rects=f['source_service_rectangles'];union=union_area([r['bbox_DBU'] for r in rects]);assert abs(union-f['rectangle_union']['union_mm2'])<1e-8
 return dict(schema='opentallas.dsrom.scenario-c.W4-attribution.v1',scope='historical PAR2 attribution consumed by W2 successor; not S73 placement',historical_start_mm2=start,historical_end_mm2=end,increment_mm2=delta,terms=terms,service_rectangles=rects,service_rectangle_union_mm2=union,inherited_fixed_mm2=f['single_parallel_successor']['full_inherited_fixed_debit_retained_per_shard_mm2'],unmapped_complement_mm2=f['containment']['unmapped_inherited_complement_after_rectangle_union_mm2'],complement_credit_mm2=0,native_residual_47_mm2=f['containment']['native_47p208_residual_mm2'],replacement_requirements={k:dict(owner=owner,rectangles=None,credit_mm2=0) for k,owner in [('HBM_PHY_and_shoreline','Chandra W3'),('SerDes_and_stage_IO','W2/W3'),('halos_and_unfillable_regions','Maxwell W4'),('clock_PG_decap','Maxwell W4/W7'),('DFT','provider needed')]},scan_nonscan_floorplans_ready=False,actual_PDN_route_pass=False,physical_admitted=False,rate_adopted=False,W7_requires=['W2 complete active-site inventory and exact stage/rank map','W1 measured finite return depth and nonpower tree','W3 scan/non-scan PHY and controller rectangles','disjoint IO/halo/clock/PG/decap/DFT containment plus legal route'],source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((BASE/'inputs').glob('*.json'))})
if __name__=='__main__':print(json.dumps(build(),indent=2,sort_keys=True))
