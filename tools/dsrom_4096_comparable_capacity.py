#!/usr/bin/env python3
"""Comparable source-pinned 4096-row mixed-element capacity sensitivities.
No compiler ownership substitution, RTL, payload, flow or product adoption.
"""
import ast,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_4096_comparable_capacity_20261002'
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a';PINS={}
def read(path,rev=BASE):
 b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);PINS[rev+':'+path]=hashlib.sha256(b).hexdigest();return b
def js(path,rev=BASE):return json.loads(read(path,rev))
def main():
 parent=js('results/uarch/dsrom_l20_reticle_prerequisite_20261002/model.json','54d46eff8');alt=parent['constrained_alternative']
 owned=js('results/uarch/dsrom_l20_hierarchical_reservation_20261002/model.json','4b6708348f3938e0830c3549fbbecadbce18e798')
 current=js('results/uarch/consolidation.json')['v41_rom'];cfg=js('configs/models/candidates/deepseek-v4.1-flash.json');mm=js('results/floorplan/v41_die_macromap_expanded_woa.json');code=read('tools/uarch_model.py').decode()
 wake=js('results/uarch/w10_baseline_wake/fullgoal_bound.json');palette=js('results/uarch/w10_q_elaboration_inventory_r1/construction.json')['palette']
 read('rtl/v41rom/ot_v41_rom_elem_wake_w10.sv');read('rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv','d8c2d19c2f9d732e8bf4985277abc4cdf13d7af0')
 totals={}
 for die in mm['layer_dies']:
  for group,v in die['macros_by_group'].items():totals[group]=totals.get(group,0)+sum(v.values())
 ns={'_V41_CFG':cfg,'_cons_nonexpert_macros':lambda:totals};fn=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='cons_stage_plan');exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_cons_stage_plan','exec'),ns);plan=ns['cons_stage_plan']
 anchor=sum([13296,464,128,82]);anchor_macros=plan(28)['busiest_macros'];qa=math.prod(current['pitches']['w10b_q']['q_um'])/1e6;ba=math.prod(current['pitches']['w10b_q']['bf16_outline_um'])/1e6
 density=owned['current_product_capacity_sensitivity']['exact_pinned_density_mm2_per_B'];dr=149.6/142.4;cap=alt['usable_field_mm2']
 assert alt['outline_mm'][0]<=33 and alt['outline_mm'][1]<=26.000001
 # Source-decomposed NAND construction bound for the shared combinational
 # repair. Comparator slice: XOR4+lessAND/invert4+MUX4=12 NAND2 equivalents.
 # This is an explicit conservative synthesis construction, not measured area.
 gates={'shift_full_11bit_subtract':11*12,'range_two11bit_and_24fivebit_sticky_comparators':(22+24*5)*12,'safe_shift_5bit_mux':5*4,'retained_barrel_24bit_fivelevels':24*5*4,'guard_bit_24to1_mux':23*4,'guard_index_5bit_decrement':5*6,'retained_range_24bit_mux':24*4,'sticky_enable_24AND':24*2,'sticky_OR_tree':23*3,'increment_24bit':24*6,'rounded_zero_OR_tree':23*3,'helper_32bit_output_mux':32*4,'caller_32bit_select_reservation':32*4,'range_sign_control_reservation':64}
 nand_area=float(palette['nand']['area_um2']);rne_per_leaf=sum(gates.values())*nand_area/.5
 rne=1024*32*rne_per_leaf/1e6
 storage_bits=138469120;ff_area=float(palette['storage']['area_um2']);return_area=storage_bits*ff_area/.5/1e6
 rows=[];partitions={}
 for S in range(28,257):
  pp=plan(S);raw_pairs=anchor*pp['busiest_macros']/anchor_macros/2;pairs=max(1024,math.ceil(raw_pairs));nq=pairs-1024
  # Retained fractional product equation reproduced separately. Never charge
  # every quantized pair the BF16 outline in the mixed product comparison.
  raw_need=pp['payload_per_die_B']*density*dr+raw_pairs*(qa-2*.0150025)+1024*(ba-qa)
  need=pp['payload_per_die_B']*density*dr+nq*(qa-2*.0150025)+1024*(ba-2*.0150025)
  wake_area=(nq*wake['elements']['q']['incremental_placement_um2_at_50pct']+1024*wake['elements']['column']['incremental_placement_um2_at_50pct'])/1e6
  total=need+return_area+wake_area+rne
  # Current PP4096 logical pair has4physical macros. This is a gross storage
  # capacity obligation; actual instruction->bank/address ownership remains
  # a separate source compiler proof. No dropped bits or resized NP allowed.
  physical_macros=4*pairs;stored_bits=physical_macros*4096*274
  assert stored_bits>=math.ceil(pp['payload_per_die_B']*8)
  rows.append(dict(stages=S,total_dies=4*S+44,busiest_pairs=pairs,BF16_pairs=1024,q_pairs=nq,current4096_PP_macros=physical_macros,physical_ROM_storage_bits=stored_bits,required_payload_bits=math.ceil(pp['payload_per_die_B']*8),fractional_product_need_mm2=raw_need,integer_mixed_field_need_mm2=need,fullBF_proxy_need_mm2=pp['payload_per_die_B']*density*dr+pairs*(ba-2*.0150025),return_FF_no_credit_mm2=return_area,WAKE_increment_mm2=wake_area,RNE_construction_increment_mm2=rne,full_conservative_need_mm2=total,usable_field_mm2=cap,retained_sensitivity_fit=raw_need<=cap,integer_mixed_fit=need<=cap,full_no_credit_sensitivity_fit=total<=cap))
 bare=next(r for r in rows if r['retained_sensitivity_fit']);full=next(r for r in rows if r['full_no_credit_sensitivity_fit']);assert bare['stages']==43 and bare['total_dies']==216
 for S in sorted({41,43,full['stages']}):
  pp=plan(S);assert all(abs(sum(fr for _,fr in parts)-1)<1e-10 for parts in pp['frac'].values());partitions[str(S)]={'source_model_stage_fractions':pp['frac'],'source_model_stage_start':pp['start'],'macros_per_die':pp['macros_per_die'],'compiler_stage_ownership_verified':False}
 hop=owned['current_product_capacity_sensitivity']['source_hop_only_price'];hops=full['stages']-41
 latency=dict(additional_source_stage_events=hops,source_stage_dependency_hop_us=hop['depth_s_per_stage_or_substage']*1e6,conditional_added_dependency_us=hops*hop['depth_s_per_stage_or_substage']*1e6,conditional_serialization_us_cap=hops*hop['serialize_s_source_max']*1e6,actual_recompiled_substage_events_bound=False,finite_service_bound=False,optimal_certified_per_user_latency_us=None,reason='Capacity does not establish actual compiler ownership, service arbitration, physical wire/CDC timing or overlap. No certified full-composed fit or optimal rate is derivable from present inputs.')
 model=dict(schema='opentallas.DSROM4096.comparable-capacity.v1',pins=PINS,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reticle_policy_constrained_outline_mm=alt['outline_mm'],usable_field_mm2=cap,baseline_product_stages=41,baseline_product_dies=208,retained43_216_is_incomplete=True,current4096_macro_rows=4096,macros_per_PP_pair=4,BF16_pairs_preserved=1024,NP_resized=False,full_return_required_bits=storage_bits,full_return_requirement_provenance='Explicit user requirement; full retained per-row return provider/port/depth ledger not yet source bound',return_FF_construction=dict(cell=palette['storage']['cell'],cell_area_um2=ff_area,placement_utilization=.5,area_mm2=return_area,embedded_original_slot_credit_mm2=0,why_no_credit='No named provider/instance ledger reconciles the full138469120bit requirement to state already included in historical slot area. This gross additional charge is conservative, not proof that every bit is missing, not an SRAM implementation and not physical minimum.'),RNE_construction=dict(NAND2_cell=palette['nand']['cell'],NAND2_area_um2=nand_area,gates_by_network=gates,per_multiplier_placement_um2=rne_per_leaf,multiplier_replicas=1024*32,per_die_increment_mm2=rne,stage4_comb_SSFF_unqualified=True,additional_state_bits=0,cycles_added=0,q_BF16_disabled_no_extra_repair_replicas=True),WAKE_source=wake['source_commit'],capacity_rows=rows,comparable_retained_sensitivity=bare,comparable_full_no_credit_sensitivity=full,partitions=partitions,latency=latency,reported_r4=dict(stages=224,dies=940,baseline_stages=28,source='User observation; r4 file not present in this clean worktree; no intake or reproduction claimed',comparison='Different baseline/basis. Mixed q/BF1024 inventory must be separated from fullBF outline proxy and source-return/control reservations before comparison.'),exact_missing_bindings=['Per-bank/per-unit full138469120bit return provider ledger, include preexisting state exactly once, finite ports and visible completion','Actual repaired RNE+WAKE4096 element hard abstract/OBS/PG/clock/hold at unchanged SSFF policy; construction area is sizing only','Golden compiler stage/bank/address ownership for integer current4096 inventory and legal placement for every co-resident; fractional analytical partitions are not compiled ownership','Recompiled actual token events with finite backend/transport service and CDC timing; no optimal latency certification until bound'],all_capacity_preserved_in_gross_sensitivity=True,foundry_seal_ring_and_package_envelope_bound=False,physical_layout_admission=False,product_adopted=False,RTL_or_PnR_started=False,four_target_applicability=dict(DS_ROM=True,Qwen_ROM=False,DS_HBM=False,Qwen_HBM=False))
 OUT.mkdir(exist_ok=True);p=OUT/'model.json';b=(json.dumps(model,indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
 print(json.dumps(dict(bare_stages=bare['stages'],full_no_credit_stages=full['stages'],full_no_credit_dies=full['total_dies'],return_FF_mm2=return_area,RNE_mm2=rne,WAKE_mm2=full['WAKE_increment_mm2'],added_hop_us=latency['conditional_added_dependency_us'],adopted=False)))
if __name__=='__main__':main()
