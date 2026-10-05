#!/usr/bin/env python3
"""Small cost-only join of committed inputs and frozen owner floorplan artifacts."""
import hashlib,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SOURCE='c1e6ed36e68489d96d7ea818b23d5acd044b440e'
PINS={}
def read(p):
    b=subprocess.check_output(['git','-c','gc.auto=0','show',SOURCE+':'+p],cwd=ROOT)
    PINS[p]=hashlib.sha256(b).hexdigest()
    return json.loads(b)
def local(p):
    b=(OUT/p).read_bytes();PINS[p]=hashlib.sha256(b).hexdigest();return json.loads(b)
d=read('results/rtl/dsrom_recovery_20261004/draft/placement.json')
lever=read('results/rtl/dsrom_recovery_20261004/levers/draft.json')
h=read('results/rtl/dsrom_recovery_20261004/levers/head.json')
old=read('results/arch/energy_silicon_measured/energy_silicon.json')['deepseek_1m']['rom']['silicon']
i=read('results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json')
st=read('results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json')
f=read('results/rtl/dsrom_s81_fulldie_20261004/floorplan.json')
ret=read('results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/model.json')
router=read('results/rtl/dsrom_recovery_20261004/router/screen.json')
phy={x:read('results/physical_abi3/asap7/chip/dsrom_recovery_head_20261004/r4_'+x+'/physical.json') for x in 'AB'}
plans={k:local('inputs/physcost_'+k+'.json') for k in ['head','draft','layer']}
sourcehash=hashlib.sha256((OUT/'inputs/physcost_source.py').read_bytes()).hexdigest();PINS['inputs/physcost_source.py']=sourcehash
assert all(p['recovery_tool_sha256']==sourcehash for p in plans.values())
bf=set(st['BF_site_IDs']);bounds=st['region_bounds'];slots=[]
for r,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
    nb=sum(p in bf for p in range(lo,hi));nq=hi-lo-nb
    slots.append(dict(region=r,pairs=hi-lo,BF_pairs=nb,q_pairs=nq,occupied_slots=nb+(nq+1)//2,reserved_slots=12))
assert sum(v['pairs'] for v in slots)==2417 and sum(v['BF_pairs'] for v in slots)==519
cost=d['dies']['die_mm2'];n=d['dies'];bundle=4*phy['A']['place_and_route']['metrics']['die_area_um2']+phy['B']['place_and_route']['metrics']['die_area_um2']
metrics={k:{x:phy[k]['place_and_route']['metrics'][x] for x in ['standard_cell_area_um2','macro_area_um2','macro_count','core_area_um2','die_area_um2']} for k in 'AB'}
for k in 'AB':metrics[k].update(parameters=phy[k]['design']['parameters'],false_path_io=phy[k]['design']['false_path_io'],block_closed=phy[k]['design']['closed'])
def delta(a,b):return {k:round(a['area_mm2_by_kind'].get(k,0)-b['area_mm2_by_kind'].get(k,0),6) for k in sorted(set(a['area_mm2_by_kind'])|set(b['area_mm2_by_kind'])) if a['area_mm2_by_kind'].get(k,0)!=b['area_mm2_by_kind'].get(k,0)}
r=dict(schema='opentallas.ds-recovery.cost-delta.v1',status='SOURCE_BOUND_COST_MILESTONE_NOT_COMPLETE_SYSTEM_TOTAL',source_revision=SOURCE,
 ownership='Rawls cost-only sidecar; Maxwell gate/full-die physical; Noether energy; no shared ledger/model/scoreboard writes',
 ledger_join=dict(old_explicit_die_counts={'layer':i['layer_dies'],'head':i['head_dies'],'table':i['table_dies'],'sum':i['layer_dies']+i['head_dies']+i['table_dies']},old_ledger_dies=old['logic_dies'],baseline_draft_separately_counted_in_old_ledger=False,
  warning='Old368 explicitly324+8+36; draft+52 is relative to baseline12, not relative to this ledger. Legacy physcost description embeds drafter in a different12-head-die design. Whether old fixed-area reservations already cover any draft functionality is unbound; no subtraction/reuse credit.',
  canonical_plus_separate64_draft_die_count=368+64,canonical_plus_separate64_and_12head_plan_die_count=324+36+64+12,
  counts_qualification='432/436 are nonoverlap itemization scenarios, NOT installed or accepted system inventories. Resolve overlap/old integrated-drafter removal and selected head-die contract before totaling.'),
 draft=dict(groups=d['groups'],matrix_rows_placed=d['matrix_rows_placed'],checkpoint=d['checkpoint'],placement_source_commit=d['source_commit'],capacity=d['capacity'],
  source_declared_dies=n,incremental_vs_baseline12_dies=52,incremental_vs_baseline12_logic_reservation_mm2=52*cost,
  baseline12_logic_reservation_mm2=12*cost,gross64_logic_reservation_mm2=64*cost,
  formula='die counts times839.239mm2 decision-priced reservation; not routed die measurement. These three quantities are alternative baseline views, not additive cost rows.',
  link_inventory=dict(primary_dies=4,replica_groups=15,replica_dies=60,new_star_links_per_primary=15,primary_star_link_endpoints=60,
    note='Actual placement calls for15 links each primary. Existing plan adds15 SerDes/FIFO ports per primary; baseline ports retained. Replica receive endpoints, full endpoint logic, clocks/PDN and link/stack/controller binding not jointly priced.'),
  primary_existing_plan_added_footprints_per_die_mm2=delta(plans['draft'],plans['layer']),
  primary_existing_plan_added_footprint_all4_mm2=4*(plans['draft']['placed_footprint_mm2']-plans['layer']['placed_footprint_mm2']),
  plan_not_implementation='Draft plan is primary variant only; not all64 dies. Plan imports K6 router slab while draft lever keeps K3/128 selector unadopted. Do not replicate this primary slab/15links to60 expert dies.'),
 head=dict(actual_measured_bundle=h['measurement']['vehicle'],measured_rows=h['measurement']['bundle']['rows'],routed_block_metrics=metrics,
  A4_B1_routed_block_die_footprint_sum_mm2=bundle/1e6,A4_B1_routed_standard_cell_area_sum_mm2=(4*metrics['A']['standard_cell_area_um2']+metrics['B']['standard_cell_area_um2'])/1e6,
  canonical_lm_head_physical4096_total=i['dedicated_storage']['global_tensors'][1]['pairs']*4,
  lever_lm_head_ROM4096_per_rank=2525,lever_lm_head_ROM4096_all4=10100,
  storage_payload_change='No checkpoint payload change: row/K permutation and lane skew; zero spare words in lever. Payload-preserving does not establish unchanged compute/placement area.',
  same_verify_draft_head_array=True,new_separate_draft_head_die_credit=0,
  preserved_plan=dict(head_dies=12,bundles_per_die=85,A_per_die=340,B_per_die=85,other_embed_norm_pairs_per_die=211,
    bundles_reserved_all12=1020,bundles_fractional_required_all4ranks=1010,reserved_full_bundle_physical4096_all12=10200,
    excess_reserved_full_bundle_macro_count=100,
    non_head_pairs_reserved_all12=2532,non_head_pairs_required=2526,
    head_frame_slots_per_bundle=3,head_frame_slots_per_die=255,
    A_B_abstract_area_per_die_mm2=plans['head']['area_mm2_by_kind']['hd_a']+plans['head']['area_mm2_by_kind']['hd_b'],
    all_placed_footprint_per_die_mm2=plans['head']['placed_footprint_mm2'],generated_abstracts=plans['head']['head']['element_abstract']),
  source_plan_vs_canonical_die_delta=4,source_plan_vs_canonical_die_reservation_sensitivity_mm2=4*cost,
  actual_adopted_head_die_delta=None,actual_head_area_delta_mm2=None,
  unknown='12-die plan is owner WIP, not adopted8->12 change. 85full bundles x12 adds tail/partition padding beyond fractional1010; full rank/localrow map, tail64 handling, reuse/removal of old head blocks, real abstracts and x/compare/VM/root clock/PDN context unresolved. +4x839.239 is only same-reservation sensitivity, not actual head cost.'),
 field_slots=dict(canonical_pairs=2417,BF_pairs=519,q_pairs=1898,frames=128,reserved_slots=1536,occupied_slots=sum(v['occupied_slots'] for v in slots),empty_slots=1536-sum(v['occupied_slots'] for v in slots),per_region=slots,
  slot_um=f['field']['slot_um'],slot_area_mm2=f['field']['slot_um'][0]*f['field']['slot_um'][1]/1e6,frame_reservation_mm2=f['field']['frames_mm2'],
  placed_q_BF_macro_footprint_mm2=f['area_mm2_by_kind']['q']+f['area_mm2_by_kind']['bf'],
  scope='Existing128-frame geometric slots; q pairs pack2/slot, BF1/slot inside each region. Region-boundary half-slots cannot be pooled. Geometry/abstract reservation, not measured whole-die compute area or fungible spare routing capacity.',
  router=dict(measured_screen_cells_um2=router['cell_area_um2'],density_reservation=0.5,slab_reservation_per_layer_mm2=router['cell_area_um2']/0.5/1e6,
   existing_layer_plan_footprint_delta_per_die_mm2=plans['layer']['placed_footprint_mm2']-f['placed_footprint_mm2'],nominal324_layer_slab_reservation_mm2=324*router['cell_area_um2']/0.5/1e6,
   caveat='K6 selector synthesis/ideal-clock screen, no routed whole-die footprint gain/closure; added slot can fit only in owner plan, not an adopted reticle increase. Do not double-add cells+slab or add slab to die839.239 automatically.'),
  return_delta=dict(old_plan_nodes=f['field']['return_nodes'],actual_retained_nodes=ret['retained_nodes'],unary_stages=ret['retained_unilateral_nodes'],extra_FF50_reservation_per_layer_die_mm2=ret['compact_additional_debit_not_removed_by_dead_pruning_mm2'],nominal324_extra_FF50_reservation_mm2=324*ret['compact_additional_debit_not_removed_by_dead_pruning_mm2'],status=ret['label'],qualification='Storage reservation only; old plan4706 vs actual5090. No removal of384 unary latency/fault stages. Not additive to a future ledger that already includes5090; adder/control/clock/PDN/routing excluded.'),
  candidate_PQ_shadow_context_and_BF519_to520_cost_mm2=None,candidate_qualification='Pending field successor and R93 BF conversion have no full-context delta here; old BF519 slot inventory retained. No helper-only synthesis area scaled as full element.'),
 plan_provenance=dict(preserved_source_commit='57f68e1087a3b6f3f110101b2753454c4f443f48',preserved_source_sha256=sourcehash,
  artifacts='Exact existing owner archive JSON copied into inputs; sourcehash matches all three recorded recovery_tool_sha256. Latest archive WIPsource6f3e66 differs and is not used.',
  python_legality={k:p['legality_python'] for k,p in plans.items()},physical_qualification='Zero overlaps/outside in Python placement only; no GRT/DRC/SSFF/capture/admission acceptance inferred.'),
 unresolved_costs=['Selected8vs12 head inventory and integer tail/rank mapping; old integrated draft removal/overlap','All primary/replica endpoint logic/ports/receive storage plus x/compare transport, CTS, PDN, physical corridors','Draft KV/window SRAM/HBM capacity and stack/base/controller inventory; no inherited452-stack currentfulltotal','Current head/table/layer actual die outline and placement costs;839.239 priced versus858 physical outline','Pending PQ walker/context/tag storage, BF520 conversion and any SU candidate slot costs; no adoption from component screens'],
 complete_current_logic_mm2=None,complete_current_total_silicon_mm2=None,pure_compute_split_mm2=None,input_sha256=PINS)
(OUT/'cost_delta.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(incremental52_mm2=r['draft']['incremental_vs_baseline12_logic_reservation_mm2'],gross64_mm2=r['draft']['gross64_logic_reservation_mm2'],occupied_field_slots=r['field_slots']['occupied_slots'],empty_field_slots=r['field_slots']['empty_slots'],head_bundle_footprint_mm2=bundle/1e6,sourcehash_matches=True)))
