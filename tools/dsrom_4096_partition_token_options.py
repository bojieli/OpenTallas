#!/usr/bin/env python3
"""Existing-topology pair partitions and retained analytical whole-token pricing.
No instruction rewriting, golden reordering, build, runtime HDL or physical flow.
"""
import argparse,collections,copy,hashlib,json,math,resource,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_4096_comparable_capacity_20261002'
def main():
 resource.setrlimit(resource.RLIMIT_AS,(16*1024**3,16*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
 source=subprocess.check_output(['git','show','e72abea5ae169d3167dddc89543013f0e6bb3a7a:tools/uarch_model.py'],cwd=ROOT);assert (ROOT/'tools/uarch_model.py').read_bytes()==source
 sys.path.insert(0,str(ROOT/'tools'));import uarch_model as u
 cap=json.load(open(OUT/'model.json'));wake=json.loads(subprocess.check_output(['git','show','e72abea5ae169d3167dddc89543013f0e6bb3a7a:results/uarch/w10_baseline_wake/fullgoal_bound.json'],cwd=ROOT))
 qa=math.prod(u.CONS_PITCH[u.PRODUCT_PITCH]['q_um'])/1e6;ba=math.prod(u.CONS_PITCH[u.PRODUCT_PITCH]['bf16_outline_um'])/1e6
 base=next(r for r in cap['capacity_rows'] if r['stages']==41);total_q=41*base['q_pairs'];total_b=41*1024;total_pairs=total_q+total_b
 rows=[]
 for prior in cap['capacity_rows']:
  S=prior['stages'];b=math.ceil(total_b/S);q=math.ceil(total_q/S);np=max(math.ceil(u._cons_busiest_macros(S)/2),b+q);q=np-b
  assert S*b>=total_b and S*q>=total_q and 4*np*4096*274>=prior['required_payload_bits']
  field=prior['integer_mixed_field_need_mm2']+(np-prior['busiest_pairs'])*(qa-2*.0150025)-(1024-b)*(ba-qa)
  repair=cap['RNE_construction']['per_die_increment_mm2']*b/1024
  wake_area=(q*wake['elements']['q']['incremental_placement_um2_at_50pct']+b*wake['elements']['column']['incremental_placement_um2_at_50pct'])/1e6
  # Keep full return reservation fixed until its exact source ledger proves a
  # partitionable component. No proportional storage shrinking by assumption.
  fixed_return=cap['return_FF_construction']['area_mm2'];need=field+repair+wake_area+fixed_return
  rows.append(dict(stages=S,total_dies=4*S+44,pairs_per_die=np,q_pairs_per_die=q,BF16_pairs_per_die=b,total_q_pairs_TP4=4*S*q,total_BF16_pairs_TP4=4*S*b,reference_total_q_pairs_TP4=4*total_q,reference_total_BF16_pairs_TP4=4*total_b,aggregate_q_compute_not_reduced=True,aggregate_BF16_compute_not_reduced=True,actual_ROM_payload_bits_per_die=prior['required_payload_bits'],physical_ROM_storage_bits_per_die=4*np*4096*274,field_need_mm2=field,return_no_unproved_partition_credit_mm2=fixed_return,RNE_increment_mm2=repair,WAKE_increment_mm2=wake_area,full_conservative_field_need_mm2=need,usable_field_mm2=prior['usable_field_mm2'],capacity_screen_fit=need<=prior['usable_field_mm2'],local_return_leaf_count_candidate=np,local_balanced_tree_height_screen=math.ceil(math.log2(np)),golden_tree_latency_credit_cycles=0,compiler_stage_bank_address_ownership_verified=False))
 best=next(r for r in rows if r['capacity_screen_fit']);np1024=next(r for r in rows if r['capacity_screen_fit'] and r['pairs_per_die']<=1024)
 selected=sorted({41,43,best['stages'],66,np1024['stages'],224});outputs=[];saved_preset=copy.deepcopy(u.PRESETS['proposal']);original=u._cons_adjust;graphs=[]
 def capture(g,P,*args,**kw):
  value=original(g,P,*args,**kw)
  if P==1:graphs.append(dict(nodes=len(g.nodes),kinds=dict(collections.Counter(nd['kind'] for nd in g.nodes.values())),hop_nodes=[dict(name=n,issue_s=nd['issue'],depth_s=nd['depth']) for n,nd in g.nodes.items() if nd['kind'] in ['hop','collective']]))
  return value
 u._cons_adjust=capture
 try:
  for S in selected:
   r=next(x for x in rows if x['stages']==S);u.PRESETS['proposal']['bf16_stripe_macros']=2*r['BF16_pairs_per_die']
   graphs.clear()
   p=u.cons_v41_rom(S,8,36,bf16='columns',clock_hz=u.PRODUCT_CLOCK_HZ,field_concurrency=u.FIELD_CONCURRENCY,added_latency=dict(u.SOFTPLUS_FIX,**u.W11_STREAM_SS,**u.PLUS_LAT),dyn_scale=u.PRODUCT_DYN_SCALE,slow_domain=(.9e9,'w18'),elem_stages=8,ss_wire=True,serial=u.PRODUCT_SERIAL,die=u.DIE_SHRUNK_INTERIM,vmh=u.VMC_FUSED,hub_block=u.PRODUCT_HUB)
   token_us=1e6/p['ar_tokens_s_b1']
   die_area=math.prod(cap['reticle_policy_constrained_outline_mm']);layer_dies=4*S;baseline_layer_dies=164;stacks_per_die=u.A.ROM_DIE_HBM_STACKS
   hardware=u.mfg_cost([(layer_dies,die_area)],[(2*S,'cowos_l_2die')],layer_dies*stacks_per_die)
   baseline_cost=u.mfg_cost([(baseline_layer_dies,814.9819)],[(82,'cowos_l_2die')],baseline_layer_dies*stacks_per_die)
   package_cost=dict(layer_packages=2*S,total_two_die_packages_if_all_roles_paired=2*S+22,layer_HBM_stacks=layer_dies*stacks_per_die,HBM_stacks_per_layer_die=stacks_per_die,layer_service_island_replicas=layer_dies,layer_service_gross_mm2=layer_dies*95.53381470719998,layer_hardware_model=hardware,baseline_layer_hardware_model=baseline_cost,layer_hardware_delta_usd=hardware['hardware_usd']-baseline_cost['hardware_usd'],head8_table36_cost_unchanged_and_not_in_layer_subtotal=True,NRE_increment_not_in_hardware_subtotal=True,extra_ROM_coding_mask_NRE_usd_low=(layer_dies-164)*u.MASK['coding_masks_per_die'][0]*u.MASK['single_mask_usd'][0],extra_ROM_coding_mask_NRE_usd_high=(layer_dies-164)*u.MASK['coding_masks_per_die'][1]*u.MASK['single_mask_usd'][1],cost_basis='Pinned repository FAB negative-binomial wafer/yield,CoWoS-L/test and assumed360USD24GBHBM model; not actual vendor quotes or currentmarketprice. No numerical package/foundry outline proof.')
   outputs.append(dict(capacity=r,package_HBM_cost=package_cost,retained_analytical_full_token_us=token_us,retained_analytical_stage_hops=p.get('stage_hops'),retained_analytical_pipeline_hops_us=p.get('pipeline_hops_us'),source_graph_inventory=copy.deepcopy(graphs),source_graph_source='e72abea5ae169d3167dddc89543013f0e6bb3a7a:tools/uarch_model.py cons_v41_rom/_cons_stages/_cons_adjust',candidate_model_BF16_stripe_macros=2*r['BF16_pairs_per_die'],field_MAC_source_model_rounding_vs_integer_slots_reconciled=False,physical_or_finite_service_qualification_transferred=False))
   print(json.dumps(dict(stages=S,NP=r['pairs_per_die'],BF16pairs=r['BF16_pairs_per_die'],dies=r['total_dies'],capacity_screen=r['capacity_screen_fit'],retained_analytical_full_token_us=token_us,qualified=False)),flush=True)
 finally:u.PRESETS['proposal'].clear();u.PRESETS['proposal'].update(saved_preset);u._cons_adjust=original
 feasible=[x for x in outputs if x['capacity']['capacity_screen_fit']];priced_min=min(feasible,key=lambda x:x['retained_analytical_full_token_us'])
 x=dict(schema='opentallas.DSROM4096.same-topology-pair-token-options.v1',die_envelope_mm=[26,33],stitching=False,capacity_model_sha256=hashlib.sha256((OUT/'model.json').read_bytes()).hexdigest(),cost_coefficients=dict(FAB=u.FAB,MASK=u.MASK,COST=u.COST),unified_model_source_sha256=hashlib.sha256(source).hexdigest(),baseline41_pairs_per_die=base['busiest_pairs'],fixed_services=dict(attention_tiles=64,index_MACs_pc=1024,HBM_reader_ports=128,collector_banks=4,selected_seats=512,WINDOW_rows=128,peerTXskids=3,replication_not_reduced=True),return_storage_bits_per_die_preserved=138469120,return_storage_partition_credit_bits=0,all_stage_capacity_rows=rows,priced_options=outputs,lowest_stages_passing_conservative_capacity=best['stages'],first_capacity_passing_NP_at_most1024=np1024,lowest_retained_analytical_token_us_among_priced_options=priced_min['retained_analytical_full_token_us'],lowest_retained_analytical_option_stages=priced_min['capacity']['stages'],whole_token_scope='Executed retained analytical DAG with fewer source-model BF16 stripes, regenerated stage/substage hops and unchanged compute/reduction-order settings. Conditional comparison only; old wire reach and service timing assumptions are explicitly not requalified.',exact_open_proofs=['Golden compiler bank/address/stage and reduction-subtree ownership for candidate NP: analytic stage fractions are not source-executed ISA ownership','Source-named full138469120bit return storage, depth and port ledger; no shrinking or overlap credit until proved','Actual integer field mixed q/BF element boundaries and RNE+WAKE source-copy gate/SSFF abstract/OBS/PG in legal26x33','L20 joint own-visible/WINDOW128/selected512 admission, finite backend/arbitration/reverse-credit/physical-drain contracts; resulting context route cuts priced in real token events','Actual hub/field/collective endpoint layout and SSFF timing replacing historical retained analytical timing assumptions'],certified_optimal_per_user_latency_us=None,product_adopted=False,RTL_or_PnR_started=False,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 out=OUT/'partition_token_options.json';b=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 if out.exists():assert out.read_bytes()==b
 else:out.write_bytes(b)
if __name__=='__main__':main()
