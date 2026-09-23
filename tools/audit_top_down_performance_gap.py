#!/usr/bin/env python3
"""Reproduce ROM/HBM system bounds without treating assumptions as RTL rates."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.check_chip_architecture import build_report


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT/name).read_text())


def main():
    work = ROOT/'build/top_down_performance'
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, 'tools/run_iso_node_studies.py', '--output',
                    str(work/'iso-node')], cwd=ROOT, check=True, capture_output=True)
    fresh = work/'iso-node/leading_node_market/analytical.json'
    retained = ROOT/'results/iso-node/leading_node_market/analytical.json'
    assert fresh.read_bytes() == retained.read_bytes(), 'Regenerated analytical study changed; review before quoting retained figures'
    market = json.loads(fresh.read_text())
    config_name = 'configs/architecture/chip_design_v2.json'
    config = load(config_name)
    chip = build_report(ROOT, ROOT/config_name)
    model = load(config['qwen']['model'])
    clock = config['clock_hz']
    context = config['qwen']['priced_context_positions']
    weights = model['dense_weight_bytes']
    kv = sum(g['count']*g['entry_bytes']*context for g in model['attention_groups'])
    # Dense BF16: 2 bytes and 2 arithmetic operations per active weight.
    operations = 2*model['active_parameters']
    assert operations == weights
    hbm_bw = config['hbm_bytes_per_cycle']*clock
    tech = load('configs/hardware/technology.json')
    b200 = tech['reference_parts']['b200_sxm']
    gpu_bw = b200['hbm_bandwidth_bytes_s']['value']
    gpu_ops = b200['published_format_roofs_ops_s']['bf16']['value']
    profiles = []
    for p in chip['profiles']:
        concurrent_dies = p['dies'] if p['partition'] == 'tensor' else 1
        peak = p['lanes']*2*clock*concurrent_dies
        profiles.append({k:p[k] for k in ['id','dies','partition','lanes','tiles',
                         'kv_source_bytes_per_cycle','kv_delivered_bytes_per_cycle',
                         'kv_service_lower_bound_us','qualified_tpot_us']} | {
                         'ideal_bf16_ops_s_available_to_one_token': peak,
                         'dense_linear_compute_lower_bound_us': operations/peak*1e6,
                         'kv_only_token_rate_ceiling': 1e6/p['kv_service_lower_bound_us'],
                         'kv_source_to_delivery_ratio': p['kv_source_bytes_per_cycle']/p['kv_delivered_bytes_per_cycle']})
    x5 = next(p for p in profiles if p['id']=='qwen_x5')
    reconciliation = load('results/derived/qwen3_n5_design_target_reconciliation.json')
    old_rom = reconciliation['targets']['rom']['analytical']['step_time_s']
    cost_currency = {k:sha(ROOT/r['cost_table']) == r['cost_table_sha256']
                     for k,r in reconciliation['runs'].items()}
    calibration = load('results/derived/qwen3_n5_design_target_calibration.json')
    drift = [name for name,value in calibration['inputs'].items()
             if not (ROOT/name).is_file() or sha(ROOT/name) != value['sha256']]
    point = next(p for p in market['points'] if p['model']=='DeepSeek-V4-Flash-0731'
                 and p['architecture']=='ROM-wafer-N4-class-HBM3e-central'
                 and p['context_tokens']==200000 and p['batch_size']==1)
    comparisons = [r for r in market['comparisons'] if
                   r['wafer_architecture']=='ROM-wafer-N4-class-HBM3e-central' and
                   r['batch_per_stage']==1 and
                   ((r['model']=='Qwen3-8B' and r['context_tokens']==8192) or
                    (r['model']=='DeepSeek-V4-Pro-0813' and r['context_tokens']==1000000) or
                    (r['context_tokens']==200000 and r['model'] in
                     ['DeepSeek-V4-Flash-0731','DeepSeek-V4.1-Flash']))]
    keys = ['model','context_tokens','wafer_per_user_tokens_s','wafer_stages',
            'fastest_same_batch_gpu','fastest_same_batch_gpu_per_user_tokens_s',
            'same_batch_per_user_speed_ratio']
    gates = subprocess.run([sys.executable,'tools/check_redesign_gates.py',
                            '--out',str(work/'gates.json')],cwd=ROOT,capture_output=True,text=True)
    assert gates.returncode in (0,1), gates.stderr
    gate_record = json.loads((work/'gates.json').read_text())
    required = point['auxiliary_required_rates_per_s_to_fit_baseline_interval']['attention_score_elements']
    # Registered production recurrence: non-early-exit request latency, excluding
    # wrapper launch/retire overhead. This is an optimistic capacity calculation.
    from tools.run_a3_hc_transcendental_rtl_campaign import iterative_cycles
    exp_cycles = iterative_cycles(0, 0xbf800000, 0)
    attention_profile = load('results/rtl/softmax_exp_reuse/attention_profile.json')
    manifest = load('results/rtl/softmax_cache2/attention/sources.json')
    baseline_drift = [n for n,h in manifest['baseline'].items() if sha(ROOT/n)!=h]
    result = {
        'schema':'opentallas.top-down-performance-gap.v1',
        'scope':'Fresh analytical regeneration and current chip-resource derivation; no measured full-system ROM/HBM efficiency exists.',
        'clock_hz_assumed':clock,
        'market_study_byte_reproduced':True,
        'market_comparisons_analytical_only':[{k:r[k] for k in keys} for r in comparisons],
        'qwen_8k_batch1':{
            'active_weight_bytes':weights,'kv_read_bytes':kv,'linear_operations':operations,
            'hbm_design_delivered_bytes_s_assumed':hbm_bw,
            'hbm_shared_memory_lower_bound_us':(weights+kv)/hbm_bw*1e6,
            'hbm_memory_only_token_rate_ceiling':hbm_bw/(weights+kv),
            'b200_published_raw_bandwidth_bytes_s':gpu_bw,
            'b200_raw_memory_lower_bound_us':(weights+kv)/gpu_bw*1e6,
            'b200_raw_memory_only_token_rate_ceiling':gpu_bw/(weights+kv),
            'b200_linear_compute_lower_bound_us':operations/gpu_ops*1e6,
            'hbm_x5_die_lanes':x5['lanes'],
            'lanes_to_match_bf16_weight_stream':hbm_bw/(2*clock),
            'x5_peak_to_bandwidth_ridge_flops_per_byte':x5['lanes']*2*clock/hbm_bw,
            'b200_peak_to_bandwidth_ridge_flops_per_byte':gpu_ops/gpu_bw,
            'profiles':profiles,
            'old_x5_analytical_tpot_us':old_rom*1e6,
            'current_x5_kv_floor_over_old_total_tpot':x5['kv_service_lower_bound_us']/(old_rom*1e6),
            'required_kv_bandwidth_for_100us_token_bytes_s':kv/100e-6,
            'required_linear_compute_for_100us_token_ops_s':operations/100e-6},
        'flash_200k_batch1_auxiliary':{
            'modeled_token_latency_us':point['per_user_token_latency_s']*1e6,
            'counts':point['auxiliary_counts_per_user_token'],
            'required_rates_per_s':point['auxiliary_required_rates_per_s_to_fit_baseline_interval'],
            'pricing_status':point['auxiliary_pricing_status'],
            'production_non_early_exit_exp_service_cycles':exp_cycles,
            'optimistic_exp_per_second_per_engine_at_assumed_clock':clock/exp_cycles,
            'engine_equivalents_no_reuse_no_early_exit':math.ceil(required*exp_cycles/clock),
            'engine_equivalents_for_10pct_serial_budget':math.ceil(required*10*exp_cycles/clock),
            'scope':'Sizing stress case: one nontrivial exponential per score, no reuse, ideal scheduling, no wrapper overhead. Not actual engine demand, speedup, area, or achievable clock.'},
        'historical_reconciliation_not_current':{
            'cost_tables_current':cost_currency,'calibration_drifted_inputs':drift,
            'rom_cycle_over_analytical_latency':reconciliation['targets']['rom']['step_ratio_cycle_over_analytical'],
            'hbm_cycle_over_analytical_latency':reconciliation['targets']['hbm']['step_ratio_cycle_over_analytical'],
            'scope':'Historical assumed cycle models, not current RTL or silicon measurements; absent links and differing charged work prevent a headline hardware ratio.'},
        'attention_fixture_evidence':{
            'baseline_sources_current':not baseline_drift,'drifted_sources':baseline_drift,
            'active_cycles':attention_profile['aggregate_active_cycles'],
            'nested_exponential_wait_fraction':attention_profile['aggregate_softmax_exponential_wait_cycles']/attention_profile['aggregate_active_cycles'],
            'scope':'Nine sparse-attention fixtures only; not a whole-model demand distribution.'},
        'gate_check':{k:gate_record[k] for k in ['gate_count','passing','terminal_passing']},
        'terminal_gates':[{'id':g['id'],'status':g['status'],'why':g['why']}
                          for g in gate_record['gates'] if g['kind']=='terminal'],
        'proposed_exit_criterion':'On each matched workload, reach at least 70% of an implementation-calibrated feasible ceiling with all costs included; validate timing, correctness, area and activity-based energy separately. This is an engineering proposal, not a measured result or a change to existing release gates.'}
    names = [config_name,config['qwen']['model'],'configs/hardware/technology.json',
             'configs/hardware/leading_node_market.json','results/iso-node/leading_node_market/analytical.json',
             'results/derived/qwen3_n5_design_target_reconciliation.json',
             'results/derived/qwen3_n5_design_target_calibration.json',
             'results/rtl/softmax_exp_reuse/attention_profile.json',
             'results/rtl/softmax_cache2/attention/sources.json',
             'tools/audit_top_down_performance_gap.py','tools/check_chip_architecture.py',
             'src/opentallas/chip_architecture.py','tools/run_iso_node_studies.py',
             'src/opentallas/analytical.py','tools/check_redesign_gates.py',
             'tools/run_a3_hc_transcendental_rtl_campaign.py',
             'rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv']
    result['input_sha256'] = {n:sha(ROOT/n) for n in names}
    output = ROOT/'results/architecture/top_down_performance_gap.json'
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(output.relative_to(ROOT))
    print(json.dumps(result['qwen_8k_batch1'],indent=2))
    print(json.dumps(result['flash_200k_batch1_auxiliary'],indent=2))


if __name__ == '__main__':
    main()
