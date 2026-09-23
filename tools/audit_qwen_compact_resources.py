#!/usr/bin/env python3
"""Qwen3-8B compact screen: equal-area ROM and HBM arrays, no deadline.

Each candidate fixes its dies, area allocation and assumed rates first; latency
floors follow from those resources. Floors are maxima of independent resource
bounds, so they are optimistic ceilings on tokens/s, not constructive schedules.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['configs/models/qwen3-8b.json', 'configs/architecture/rom_hbm_review_v3.json',
          'results/architecture/redesign_recurrence_feasibility.json',
          'configs/architecture/rom_density_evidence.json',
          'tools/audit_qwen_compact_resources.py']
DIE_MM2 = 815
CONTEXT = 8192
# Sensitivities, not qualified ROM rates. 'sram_matched' gives stored ROM bytes the
# same delivered rate per byte as the HBM twin's SRAM cache (parity, not evidence).
ROM_AGGREGATE_TB_S = (4.5, 18, 72, 'sram_matched')
HBM_TB_S_PER_DIE = 4.5                      # config assumption, about five HBM3e stacks
HBM_STACK_BYTES = 36e9                      # technology_inputs: B300 288 GB / 8 stacks
HBM_STACKS_PER_DIE = 5
# Fabricated SRAM anchor: GC200 delivers 47.5 TB/s from 900 MB (technology_inputs).
# Using its bandwidth per stored byte for the HBM die's weight cache is conservative
# relative to WSE-3 (21 PB/s from 44 GB) and is an organization, not a new macro.
SRAM_BYTES_S_PER_BYTE = 47.5e12 / 900e6


def model_work(m):
    heads = m['metadata']['num_attention_heads']
    head_dim = m['metadata']['head_dim']
    layers = m['num_layers']
    kv = CONTEXT * sum(g['count'] * g['entry_bytes'] for g in m['attention_groups'])
    linear_ops = m['operations_per_active_parameter'] * m['active_parameters']
    attention_ops = 2 * 2 * layers * heads * head_dim * CONTEXT   # QK and AV MACs
    return {'weight_bytes': m['dense_weight_bytes'], 'kv_bytes': kv,
            'linear_ops': linear_ops, 'attention_ops': attention_ops,
            'ops': linear_ops + attention_ops}


def die_budget(c, dies, rom_mm2, kv_bytes):
    fixed = sum(c['extra_area_caps_mm2_per_die'].values())
    kv_mm2 = kv_bytes / dies / c['sram_bytes_per_mm2_assumed']
    compute_mm2 = DIE_MM2 - rom_mm2 - kv_mm2 - fixed
    lane_mm2 = c['tile_area_mm2_assumed'] / c['lanes_per_tile']
    lanes = max(0, math.floor(compute_mm2 / lane_mm2))
    return {'fixed_mm2': fixed, 'kv_sram_mm2': kv_mm2, 'compute_mm2': compute_mm2,
            'lanes': lanes, 'fits': compute_mm2 > 0}


def floors(parts):
    """Largest independent bound, and the name of the resource that sets it."""
    name = max(parts, key=parts.get)
    return {'terms_us': parts, 'floor_us': parts[name], 'binding': name,
            'tokens_s_ceiling': 1e6 / parts[name]}


def hbm_terms(m, c, dies, lanes, cache_mm2):
    """Weight service and arithmetic for an HBM die with SRAM weight cache."""
    w = model_work(m)
    f, util = c['clock_hz'], c['mac_utilization_target']
    consumable = dies * lanes * 2 * f * util
    cached = min(w['weight_bytes'], dies * cache_mm2 * c['sram_bytes_per_mm2_assumed'])
    hbm_rate = min(dies * HBM_TB_S_PER_DIE * 1e12, consumable) if lanes else 0
    uncached = w['weight_bytes'] - cached
    terms = {'hbm_uncached_weights': uncached / hbm_rate * 1e6 if uncached else 0.0,
             'sram_cached_weights': 1e6 / SRAM_BYTES_S_PER_BYTE if cached else 0.0,
             'arithmetic': w['ops'] / consumable * 1e6 if lanes else math.inf}
    return {'terms': terms, 'cached': cached, 'hbm_rate': hbm_rate}


def candidate(m, c, recurrence, dies, rom_mm2, rom_tb_s, rom_density=None):
    w = model_work(m)
    f, util = c['clock_hz'], c['mac_utilization_target']
    density = (rom_density or c['rom_bytes_per_mm2_assumed']) * (1 - c['rom_reserved_fraction'])
    budget = die_budget(c, dies, rom_mm2, w['kv_bytes'])
    rom_capacity = dies * rom_mm2 * density
    base = {'dies': dies, 'total_die_mm2': dies * DIE_MM2, 'rom_mm2_per_die': rom_mm2,
            'rom_aggregate_TB_s_assumed': rom_tb_s, 'rom_bytes_per_mm2': density / (1 - c['rom_reserved_fraction']),
            'die_budget': budget,
            'rom_capacity_bytes': rom_capacity, 'holds_full_checkpoint': rom_capacity >= m['checkpoint_bytes']}
    if not budget['lanes']:
        return {**base, 'infeasible': 'no area remains for compute after ROM, KV SRAM and fixed caps'}
    ops_s = dies * budget['lanes'] * 2 * f * util
    kv_s = dies * c['kv_local_bytes_per_cluster_cycle'] * c['clusters_per_die'] * f * c['kv_delivery_utilization_target']
    # Each lane consumes one BF16 weight per cycle at the utilization target.
    consumable = dies * budget['lanes'] * 2 * f * util
    offered = m['checkpoint_bytes'] * SRAM_BYTES_S_PER_BYTE if rom_tb_s == 'sram_matched' else rom_tb_s * 1e12
    rom_rate = min(offered, consumable)
    common = {'kv_service': w['kv_bytes'] / kv_s * 1e6, 'arithmetic': w['ops'] / ops_s * 1e6}
    # HBM twin: identical compute and KV SRAM; ROM area becomes PHY plus weight cache.
    cache_mm2 = rom_mm2 - c['hbm_phy_area_mm2_per_die_assumed']
    twin = hbm_terms(m, c, dies, budget['lanes'], cache_mm2)
    # Optimized HBM: same flexible area, split between lanes and cache to minimize its floor.
    flexible = budget['compute_mm2'] + cache_mm2
    lane_mm2 = c['tile_area_mm2_assumed'] / c['lanes_per_tile']
    best = min((max({**hbm_terms(m, c, dies, math.floor(x / lane_mm2), flexible - x)['terms'], 'kv_service': common['kv_service']}.values()), x)
               for x in [flexible * i / 400 for i in range(1, 400)])
    opt_compute = best[1]
    opt = hbm_terms(m, c, dies, math.floor(opt_compute / lane_mm2), flexible - opt_compute)
    contracts = {'sequential_rne_recurrence_1': recurrence['1'], 'sequential_rne_recurrence_3': recurrence['3'],
                 'unqualified_relaxed_association': 0.0}
    rows = {}
    for label, rec in contracts.items():
        rom = floors({**common, 'rom_weights': w['weight_bytes'] / rom_rate * 1e6, 'recurrence': rec})
        hbm = floors({'kv_service': common['kv_service'], **twin['terms'], 'recurrence': rec})
        hbm_opt = floors({'kv_service': common['kv_service'], **opt['terms'], 'recurrence': rec})
        rows[label] = {'rom': rom, 'hbm_equal_area': hbm, 'hbm_equal_area_optimized_split': hbm_opt,
                       'rom_over_hbm_single_sequence': hbm['floor_us'] / rom['floor_us'],
                       'rom_over_optimized_hbm_single_sequence': hbm_opt['floor_us'] / rom['floor_us']}
    hbm_kv_capacity = dies * HBM_STACKS_PER_DIE * HBM_STACK_BYTES - (w['weight_bytes'] - twin['cached'])
    return {**base, 'lane_consumable_weight_TB_s': consumable / 1e12,
            'rom_rate_used_TB_s': rom_rate / 1e12,
            'hbm_twin': {'weight_cache_mm2_per_die': cache_mm2, 'cached_weight_bytes': twin['cached'],
                         'hbm_rate_used_TB_s': twin['hbm_rate'] / 1e12,
                         'optimized_compute_mm2_per_die': opt_compute,
                         'optimized_cache_mm2_per_die': flexible - opt_compute,
                         'optimized_cached_weight_bytes': opt['cached'],
                         'concurrent_8k_sequences_by_kv_capacity': math.floor(hbm_kv_capacity / w['kv_bytes'])},
            'rom_concurrent_8k_sequences_by_kv_capacity': 1,
            'aggregate_compute_bound_tokens_s': ops_s / w['ops'],
            'contracts': rows}


def dies_to_hold(m, c, rom_mm2, rom_density):
    return math.ceil(m['checkpoint_bytes'] / (rom_mm2 * rom_density * (1 - c['rom_reserved_fraction'])))


def break_even_rom_tb_s(m, c, dies, rom_mm2, rom_density=None):
    """Aggregate ROM rate at which ROM matches the HBM twin under relaxed association."""
    base = candidate(m, c, {'1': 0, '3': 0}, dies, rom_mm2, 1e6, rom_density)['contracts']['unqualified_relaxed_association']
    hbm = base['hbm_equal_area']['floor_us']
    return model_work(m)['weight_bytes'] / (hbm * 1e-6) / 1e12


def main():
    m, c, r, ev = [json.loads((ROOT / n).read_text()) for n in INPUTS[:4]]
    rec = r['linear_dependency_floor_us_by_recurrence_cycles']
    w = model_work(m)
    # The HC1 class is 4-bit compute-in-ROM cells; it does not store a BF16 checkpoint for digital readout.
    classes = {k: v for k, v in ev['density_classes_for_sweeps'].items() if not k.startswith('hc1')}
    shapes = [(cls, a, dies_to_hold(m, c, a, d), d) for cls, d in classes.items() for a in (300, 400)]
    rows = [{'density_class': cls, **candidate(m, c, rec, n, a, b, d)} for cls, a, n, d in shapes for b in ROM_AGGREGATE_TB_S]
    rows += [{'density_class': 'beyond_compiler_planning', **candidate(m, c, rec, 4, 500, b)} for b in ROM_AGGREGATE_TB_S]
    out = {
        'schema': 'opentallas.qwen-compact-resources.v2',
        'status': 'equal_area_resource_ceilings_not_physical_performance',
        'full_bf16_checkpoint_bytes': m['checkpoint_bytes'], 'context': CONTEXT, 'work': w,
        'minimum_ROM_area_mm2_full_checkpoint': {cls: m['checkpoint_bytes'] / (d * (1 - c['rom_reserved_fraction']))
                                                 for cls, d in classes.items()},
        'single_die_density_multiplier_required_if_all_815mm2_ROM': m['checkpoint_bytes'] / (
            DIE_MM2 * classes['beyond_compiler_planning'] * (1 - c['rom_reserved_fraction'])),
        'hbm_single_die_weight_floor_us': w['weight_bytes'] / (HBM_TB_S_PER_DIE * 1e12) * 1e6,
        'candidates': rows,
        'break_even_rom_aggregate_TB_s_relaxed_association': {
            f'{cls}:{n}x{a}': break_even_rom_tb_s(m, c, n, a, d) for cls, a, n, d in shapes},
        'assumptions': [
            'Die 815 mm2; fixed per-die caps (exact functions, reduction, fabric, control, clock/power reserve) from rom_hbm_review_v3.',
            'KV: 8K BF16 single sequence in SRAM at the config density, split evenly across dies; served at the config per-cluster KV rate.',
            'Compute: every remaining mm2 becomes lanes at the unqualified legacy tile area; one BF16 weight per lane-cycle at 65% utilization caps consumable stream.',
            'HBM twin: same dies, compute and KV SRAM; ROM area becomes a 50 mm2 PHY and SRAM weight cache; 4.5 TB/s/die HBM; cache bandwidth per byte from fabricated GC200.',
            'ROM aggregate rates are sensitivities with no qualified macro. ROM density is swept over rom_density_evidence classes; dies are the minimum holding the full BF16 checkpoint at that density.',
            'Relaxed association is not admitted: the committed BF16 witness shows blocked sums differ from sequential RNE. It is shown only to expose the memory term.'],
        'limits': [
            'Floors take a maximum of independent bounds; a finite schedule may add them. Tokens/s values are ceilings.',
            'Recurrence floors are whole-K sequential RNE at 1 GHz with fully parallel outputs; attention, nonlinear, control and inter-die service omitted.',
            'Energy, bank conflicts, inter-die links inside the package and prefill are not priced here.',
            '4 x 500 mm2 ROM leaves negative compute area after fixed caps and KV; its rows are shown as infeasible, not as a design.'],
        'input_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in INPUTS},
    }
    (ROOT / 'results/architecture/qwen_compact_resources.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    for row in rows:
        if 'infeasible' in row:
            print(row['density_class'], row['dies'], row['rom_mm2_per_die'], row['infeasible'], round(row['die_budget']['compute_mm2'], 1))
            continue
        s = row['contracts']
        print(row['density_class'][:14], row['dies'], row['rom_mm2_per_die'], row['rom_aggregate_TB_s_assumed'], row['die_budget']['fits'],
              round(row['die_budget']['compute_mm2'], 1), row['die_budget']['lanes'],
              {k: (round(v['rom']['floor_us'], 1), v['rom']['binding'], round(v['hbm_equal_area']['floor_us'], 1),
                   v['hbm_equal_area']['binding'], round(v['rom_over_hbm_single_sequence'], 2)) for k, v in s.items()})
    print(out['break_even_rom_aggregate_TB_s_relaxed_association'], out['hbm_single_die_weight_floor_us'])


if __name__ == '__main__':
    main()
