#!/usr/bin/env python3
"""Necessary-condition checks for the review proposal; never predicts achieved TPOT."""
import argparse
from copy import deepcopy
import hashlib
import json
from math import ceil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from opentallas.chip_architecture import qwen_units, align_up


def evaluate(c, m):
    dies, hz = c['dies'], c['clock_hz']
    assert dies > 0 and m['metadata']['num_key_value_heads'] % dies == 0
    for k in ['mac_utilization_target','weight_delivery_utilization_target',
              'kv_delivery_utilization_target','fast_exact_utilization_target',
              'fallback_utilization_limit']:
        assert 0 < c[k] <= 1, k
    units = qwen_units(m)
    raw = ceil((sum(align_up(ceil((u['bytes']-u['replicated_bytes'])/dies)+u['replicated_bytes'],
                           c['rom_alignment_bytes']) for u in units)+c['rom_misc_bytes_per_die']) /
               (1-c['rom_reserved_fraction']))
    tiles = c['clusters_per_die']*c['tiles_per_cluster']
    lanes = tiles*c['lanes_per_tile']
    area = {'rom':raw/c['rom_bytes_per_mm2_assumed'],
            'kv_sram':c['kv_capacity_bytes_per_die']/c['sram_bytes_per_mm2_assumed'],
            'tensor_tiles':tiles*c['tile_area_mm2_assumed'],
            'attention_scratch':c['attention_scratch_bytes_per_die']/c['sram_bytes_per_mm2_assumed'],
            'stream_scratch':c['stream_scratch_bytes_per_die']/c['sram_bytes_per_mm2_assumed'],
            **c['extra_area_caps_mm2_per_die']}
    area_used = sum(area.values())
    hbm_area = area_used-area['rom']+c['hbm_phy_area_mm2_per_die_assumed']+c['hbm_twin_extra_sram_bytes_per_die']/c['sram_bytes_per_mm2_assumed']
    w = m['dense_weight_bytes']
    kv_per_position = sum(g['count']*g['entry_bytes'] for g in m['attention_groups'])
    kv = kv_per_position*c['context_positions']
    scores = m['num_layers']*m['metadata']['num_attention_heads']*c['context_positions']
    att_ops = scores*m['metadata']['head_dim']*4
    linear_ops = m['active_parameters']*2
    compute = dies*lanes*2*hz*c['mac_utilization_target']
    rom_bw = dies*tiles*c['weight_port_bytes_per_tile_cycle']*hz*c['weight_delivery_utilization_target']
    kv_bw = dies*c['clusters_per_die']*c['kv_local_bytes_per_cluster_cycle']*hz*c['kv_delivery_utilization_target']
    fast = dies*c['fast_exact_lanes_per_die']*hz*c['fast_exact_utilization_target']/c['fast_exact_initiation_interval_cycles']
    fallback = dies*c['fallback_engines_per_die']*hz*c['fallback_utilization_limit']/c['fallback_service_cycles_budget']
    budgets = c['serial_latency_budgets_us']
    target = sum(budgets.values())
    # Give the twin ideal persistent weight use of ALL extra SRAM, excluding it
    # from both HBM weight traffic and compute; compute is unchanged in reality.
    resident_cache = dies*c['hbm_twin_extra_sram_bytes_per_die']
    hbm_stream = max(0,w-resident_cache)
    hbm_bw = dies*c['hbm_delivered_bytes_s_per_die_assumed']
    hbm_weights_floor = hbm_stream/hbm_bw*1e6
    hbm_shared_floor = (hbm_stream+kv)/hbm_bw*1e6
    collective = c['collectives_per_layer']*m['num_layers']*c['collective_latency_budget_ns']/1000
    conditions = {
        'rom_area_within_cap':area_used<=c['die_area_mm2'],
        'hbm_twin_area_within_cap':hbm_area<=c['die_area_mm2'],
        'kv_capacity':kv_per_position*c['capacity_positions']/dies<=c['kv_capacity_bytes_per_die'],
        'score_and_exp_scratch':scores*8/dies<=c['attention_scratch_bytes_per_die'],
        'weight_service_budget':w/rom_bw*1e6<=budgets['linear_weight_and_compute'],
        'linear_compute_budget':linear_ops/compute*1e6<=budgets['linear_weight_and_compute'],
        'kv_service_budget':kv/kv_bw*1e6<=budgets['attention_kv_qk_av'],
        'attention_compute_budget':att_ops/compute*1e6<=budgets['attention_kv_qk_av'],
        'exp_service_budget':scores/fast*1e6<=budgets['exact_functions_norm_and_selection'],
        'fallback_average_capacity':scores*c['fallback_fraction_target']/fallback*1e6<=budgets['exact_functions_norm_and_selection'],
        'collective_budget':collective<=budgets['collectives'],
        'threefold_vs_hbm_weight_floor_with_extra_cache':hbm_weights_floor/target>=c['required_rom_over_hbm_speedup']}
    return {'scope':'Necessary capacity/service inequalities only. No placement, schedule, numerical proof or achieved speedup.',
        'area_mm2_per_die':area,'rom_area_total_mm2_per_die':area_used,
        'hbm_twin_area_total_mm2_per_die':hbm_area,'unallocated_rom_area_mm2_per_die':c['die_area_mm2']-area_used,
        'raw_rom_bytes_per_die':raw,'lanes_per_die':lanes,'tiles_per_die':tiles,
        'system_effective_bf16_ops_s_target':compute,'system_weight_bytes_s_target':rom_bw,
        'system_kv_bytes_s_target':kv_bw,'linear_weight_floor_us':w/rom_bw*1e6,
        'linear_compute_floor_us':linear_ops/compute*1e6,'kv_floor_us':kv/kv_bw*1e6,
        'qk_av_operations':att_ops,'qk_av_floor_us':att_ops/compute*1e6,
        'attention_scores':scores,'attention_exp_floor_us':scores/fast*1e6,
        'fallback_fraction_capacity_in_20us_budget':fallback*budgets['exact_functions_norm_and_selection']*1e-6/scores,
        'collective_budget_total_us':collective,'collective_payload_serialization_cycles':ceil(c['collective_payload_bytes']/c['collective_endpoint_bytes_per_cycle']),
        'hbm_min_outstanding_bytes_per_die':c['hbm_delivered_bytes_s_per_die_assumed']/hz*c['hbm_read_latency_cycles_assumed'],
        'hbm_min_outstanding_transactions_per_die':ceil(c['hbm_delivered_bytes_s_per_die_assumed']/hz*c['hbm_read_latency_cycles_assumed']/c['hbm_transaction_bytes']),
        'rom_token_latency_target_us_not_prediction':target,
        'hbm_twin_persistent_weight_cache_bytes':resident_cache,
        'hbm_twin_weight_only_lower_bound_us':hbm_weights_floor,
        'hbm_twin_shared_weight_kv_lower_bound_us':hbm_shared_floor,
        'conditional_speedup_floor_if_rom_target_met_weights_only':hbm_weights_floor/target,
        'conditions':conditions,'all_necessary_conditions_pass':all(conditions.values()),
        'hbm_full_spare_cache_weight_floor_us':max(0,w-resident_cache-max(0,c['die_area_mm2']-hbm_area)*c['sram_bytes_per_mm2_assumed']*dies)/hbm_bw*1e6,
        'required_rom_us_for_3x_vs_full_spare_cache':max(0,w-resident_cache-max(0,c['die_area_mm2']-hbm_area)*c['sram_bytes_per_mm2_assumed']*dies)/hbm_bw*1e6/c['required_rom_over_hbm_speedup'],
        'qualified_token_latency_us':None,'qualified_speedup':None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='results/architecture/rom_hbm_review_v3.json')
    args=parser.parse_args()
    config=ROOT/'configs/architecture/rom_hbm_review_v3.json'
    c=json.loads(config.read_text());m=json.loads((ROOT/c['model']).read_text())
    report={'proposal':evaluate(c,m),'sensitivities':{}}
    stretch=deepcopy(c)
    stretch.update(c['rom_performance_variant'])
    report['performance_variant']=evaluate(stretch,m)
    report['performance_variant_scope']='Primary performance proposal, stronger than the 150us bring-up architecture; all rates and area caps require implementation proof.'
    for label,changes in {
        'rom_density_half':{'rom_bytes_per_mm2_assumed':c['rom_bytes_per_mm2_assumed']/2},
        'weight_delivery_25pct':{'weight_delivery_utilization_target':0.25},
        'clock_750mhz':{'clock_hz':750000000},
        'collective_1us':{'collective_latency_budget_ns':1000},
        'fallback_0p1pct':{'fallback_fraction_target':0.001},
        'context_32k_without_capacity_upgrade':{'context_positions':32768,'capacity_positions':33024},
        'hbm_twice_bandwidth':{'hbm_delivered_bytes_s_per_die_assumed':9e12},
    }.items():
        v=deepcopy(c);v.update(changes);r=evaluate(v,m)
        report['sensitivities'][label]={'failed_conditions':[k for k,v in r['conditions'].items() if not v],
                                       'area_mm2':r['rom_area_total_mm2_per_die'],
                                       'weight_floor_us':r['linear_weight_floor_us'],
                                       'kv_floor_us':r['kv_floor_us'],
                                       'conditional_speedup_floor':r['conditional_speedup_floor_if_rom_target_met_weights_only']}
    report['performance_sensitivities'] = {}
    for label, changes in {
        'rom_density_half': {'rom_bytes_per_mm2_assumed':stretch['rom_bytes_per_mm2_assumed']/2},
        'weight_delivery_half': {'weight_delivery_utilization_target':stretch['weight_delivery_utilization_target']/2},
        'clock_750mhz': {'clock_hz':750000000},
        'collective_1us': {'collective_latency_budget_ns':1000},
        'fallback_0p1pct': {'fallback_fraction_target':0.001},
        'hbm_twice_bandwidth': {'hbm_delivered_bytes_s_per_die_assumed':9e12},
    }.items():
        v=deepcopy(stretch);v.update(changes);r=evaluate(v,m)
        report['performance_sensitivities'][label] = {
            'failed_conditions':[k for k,v in r['conditions'].items() if not v],
            'required_rom_us_for_3x_vs_full_spare_cache':r['required_rom_us_for_3x_vs_full_spare_cache']}
    report['independent_hbm_all_sram_capacity_screen'] = {
        'active_weight_sram_mm2_per_die':m['dense_weight_bytes']/c['dies']/c['sram_bytes_per_mm2_assumed'],
        'checkpoint_sram_mm2_per_die':m['checkpoint_bytes']/c['dies']/c['sram_bytes_per_mm2_assumed'],
        'scope':'Capacity-only ideal lower bound, no alignment/ECC/metadata/spares. An independently optimized HBM/SRAM design can trade compute for weight residency; the streamed-HBM bound is not a universal comparator.'}
    report['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           [config,ROOT/c['model'],Path(__file__).resolve(),ROOT/'src/opentallas/chip_architecture.py']}
    out=ROOT/args.output;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
