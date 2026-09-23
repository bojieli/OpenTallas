#!/usr/bin/env python3
"""DeepSeek V4.1 static architecture screen, not an implementation forecast."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    names=['configs/models/candidates/deepseek-v4.1-flash.json','configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json','compiler/models/deepseek-v4.1-flash/inference_config.json','results/iso-node/leading_node_market/analytical.json','configs/architecture/rom_hbm_review_v3.json']
    m,h,official,market,c=[json.loads((ROOT/n).read_text()) for n in names]
    op=m['metadata']['operator_config'];layers=m['num_layers'];experts=m['num_experts'];selected=m['experts_per_token']
    assert (layers,experts,selected,op['hidden_size'],op['moe_intermediate_size'])==(official['n_layers'],official['n_routed_experts'],official['n_activated_experts'],official['dim'],official['moe_inter_dim'])
    engram=m['checkpoint_bytes']-h['checkpoint_bytes']
    assert engram==sum(m['metadata']['engram']['num_embeddings'])*m['metadata']['engram']['row_bytes_packed']
    expert_bytes=m['routed_weight_bytes']//layers//experts
    active_expert_bytes=expert_bytes*selected*layers
    expert_ops=6*op['hidden_size']*op['moe_intermediate_size']*selected*layers
    assert math.isclose(expert_ops,16986931200)
    rates=[]
    for context in [8192,200000,1000000]:
        p=next(p for p in market['points'] if p['model']==m['name'] and p['context_tokens']==context and p['batch_size']==1 and p['architecture']=='ROM-wafer-N4-class-HBM3e-central')
        rates.append({'context':context,'weight_bytes':p['deployed_weight_bytes_per_step'],
                      'kv_read_bytes':p['kv_read_bytes_per_user_token'],
                      'tensor_operations':p['tensor_operations_per_user_token'],
                      'auxiliary_items':p['auxiliary_counts_per_user_token'],
                      'required_auxiliary_rates_for_100us':{k:v/100e-6 for k,v in p['auxiliary_counts_per_user_token'].items() if k not in ['sinkhorn_iterations','sinkhorn_matrix_elements_per_iteration']},
                      'sinkhorn_element_iterations_per_token':p['auxiliary_counts_per_user_token']['sinkhorn_iterations']*p['auxiliary_counts_per_user_token']['sinkhorn_matrix_elements_per_iteration']})
    capacity=[]
    for placement,bytes_ in [('all_rom',m['checkpoint_bytes']),('engram_in_hbm',h['checkpoint_bytes'])]:
        for rom_mm2 in [300,400,500]:
            payload=rom_mm2*c['rom_bytes_per_mm2_assumed']*(1-c['rom_reserved_fraction'])
            capacity.append({'placement':placement,'rom_area_per_die_mm2':rom_mm2,
                             'checkpoint_bytes':bytes_,'minimum_dies_capacity_only':math.ceil(bytes_/payload),
                             'scope':'Excludes per-die image reserves, alignment, replication, repair beyond 2%, compute/PHY/other area and bank mapping.'})
    # Optimistic expert-only recurrence: two dependent projections; six experts
    # and gate/up run concurrently, shared expert and all other operators omitted.
    recurrence={str(g):layers*(math.ceil(op['hidden_size']/g)+math.ceil(op['moe_intermediate_size']/g))/1e9*1e6 for g in [1,2,4]}
    weight=rates[1]['weight_bytes']
    hbm=[{'dies':n,'assumed_total_hbm_TB_s':n*4.5,
          'weight_floor_us_no_cache':weight/(n*4.5e12)*1e6,
          'rom_us_for_3x_weight_floor_no_cache':weight/(n*4.5e12)*1e6/3,
          'scope':'Optimistic HBM lower bound, not achieved latency; assumes all dies service this token concurrently, no weight cache, independent capacity/compute/network proof required.'} for n in [8,16,32,80,96]]
    out={'schema':'opentallas.v41-first-principles.v1','model':m['name'],'source_revision':m['source_revision'],
         'status':'feasibility_incomplete_no_implementation_selected',
         'engram_bytes':engram,'engram_lookup_bytes_per_token':m['metadata']['engram']['lookup_bytes_per_token'],
         'engram_fraction_of_checkpoint':engram/m['checkpoint_bytes'],
         'experts':experts,'selected_experts_per_layer':selected,'selected_expert_fraction':selected/experts,
         'packed_expert_bytes':expert_bytes,'active_routed_bytes_per_layer':expert_bytes*selected,
         'active_routed_bytes_per_token':active_expert_bytes,'routed_expert_operations_per_token':expert_ops,
         'expert_only_recurrence_us_at_1ghz_by_products_per_update':recurrence,
         'recurrence_scope':'Conditional native g-product sequential recurrence, one dependent group update per clock, all six experts parallel; g2/g4 are not universally bit-equivalent to scalar arithmetic.',
         'expert_40us_budget':{'per_layer_us':1,'active_bytes_s_per_active_layer_group':expert_bytes*selected/1e-6,
                              'ops_s_per_active_layer_group':expert_ops/layers/1e-6,
                              'physical_group4_lanes_at_65pct_1ghz':math.ceil(expert_ops/layers/1e-6/(8*1e9*.65)),
                              'bytes_s_per_selected_expert':expert_bytes/1e-6},
         'capacity_screens':capacity,'contexts':rates,'hbm_screens':hbm,
         'kv_owners':op['kv_source_layer_ids'],'index_owners':op['index_source_layer_ids'],
         'kv_capacity_shared_main_and_index_bytes_per_context_position':m['metadata']['global_kv_bytes_per_token'],
         'kv_capacity_200k_shared_main_index_bytes':200000*m['metadata']['global_kv_bytes_per_token'],
         'scope_limits':['Market work inventory is analytical and not an operator-complete service ledger.','Capacity does not establish active-bank throughput.','No 3x speedup, numerical qualification, area closure or power claim.','Decode calculation excludes speculative and vision work; prefill requires its CED-specific dependency graph.']}
    out['input_sha256']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names+[str(Path(__file__).resolve().relative_to(ROOT))]}
    (ROOT/'results/architecture/v41_architecture_feasibility.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['contexts','input_sha256']},indent=2))
if __name__=='__main__':main()
