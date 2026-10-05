"""HA0/HA10: frozen study replay and explicit, unvalidated fairness bounds.

No inference, RTL admission, measured composition or adopted accelerator rate.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path

STUDY = 'results/uarch/hbm_accelerator_study_20261003/'
STUDY_PINS = {
    STUDY + 'ladder_model.py': '5266d81b537fe18edd427f853bdb25c6b6533c3c65e7dafc2ac3bedb0378125f',
    STUDY + 'ladder.json': '0f21684483496bd811b2ac08e4f4a4f8e29cbd91bb8ad5f696162dbd80b62e2c',
}
GATES = ['exact', 'latency', 'area', 'route', 'timing', 'gain']
COMPOSITION = 'results/rtl/hbm_accel_composition_20261004/measured_composition.json'
Q27 = 'results/uarch/hbm_accelerator_integration_20261004/qwen3.8-27b_hbm_inputs.json'  # header facts; agree with configs/models/candidates/qwen3.8-27b.json (cf63b0c0f)

# Sourced DRAM silicon per stack (HA0). Micron's HBM3E product brief gives an 11 mm x 11 mm cube
# footprint; a stacked core die cannot exceed it, so 121 mm2 bounds each core die and the base die.
# 8-high 24 GB = 8 core + 1 base; 12-high 36 GB = 12 core + 1 base.  These are UPPER bounds
# (conservative against the side with more stacks); the study's 900/1000/1450 stay as the ASSUMED
# die-area sensitivities.
HBM3E_FOOTPRINT_MM2 = 11.0 * 11.0
DRAM_MM2_PER_STACK_SOURCED = dict(
    bound_8hi=9 * HBM3E_FOOTPRINT_MM2, bound_12hi=13 * HBM3E_FOOTPRINT_MM2,
    source='Micron HBM3E product brief: 11 mm x 11 mm x 0.72 mm cube (assets.micron.com hbm3e-product-brief.pdf)',
    rule='core and base dies each <= cube footprint; bound, not a measured die area')


def _numeric_leaves(x, path=''):
    if isinstance(x, bool):
        return
    if isinstance(x, (int, float)):
        yield path, float(x)
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _numeric_leaves(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _numeric_leaves(v, f'{path}/{i}')


def ladder_reproduction(replayed, recorded):
    """Max relative deviation of every numeric leaf; HA0 acceptance is <= 0.1%."""
    a, b = dict(_numeric_leaves(replayed)), dict(_numeric_leaves(recorded))
    if a.keys() != b.keys():
        raise ValueError('ladder structure differs from ladder.json')
    worst = max((abs(a[k] - b[k]) / max(abs(b[k]), 1e-12), k) for k in a)
    return dict(leaves=len(a), max_rel_dev=worst[0], at=worst[1], tolerance=1e-3, pass_=worst[0] <= 1e-3)


def gpu_faithful_r0(m, ds):
    """GPU-faithful R0: every W19 boundary pays a cooperative-grid sync (1.43 us) instead of the
    ablation's custom 62-cycle barrier (which no GPU has; labelled)."""
    lad = ds['1M']['firm']['ladder']
    r0, r1 = lad[0], lad[1]
    per_boundary_us = m.GPU_GRID_SYNC_NS * 1e-3
    hw_us = m.W19_BOUNDARY_CYC / m.F_FAST * 1e6
    boundaries = m.W19_AR['barrier'] / hw_us
    return dict(row='R0 GPU-faithful grid sync', grid_sync_us_per_boundary=per_boundary_us,
                ablation_barrier_us_per_boundary=hw_us, ablation_barrier_cycles=m.W19_BOUNDARY_CYC,
                boundaries=boundaries, ar_us=r0['ar_us'], ar_tok_s=r0['ar_tok_s'],
                w19_ablation_ar_tok_s=r1['ar_tok_s'],
                label='ablation barrier (62 cycles) is NOT GPU-real; R0 is the GPU-faithful row',
                source='V100 cooperative-groups grid sync 1.43 us (IPDPS 2020), study GPU_GRID_SYNC_NS')


def qwen27_sourced(root, m):
    """Qwen3.8-27B from the pinned config + safetensors headers (no weights downloaded): a hybrid,
    48 Gated-DeltaNet layers with an FP32 recurrent state + 16 full-attention layers (4 KV heads x 256),
    not the study's ASSUMED dense 64x8x128 GQA."""
    c = json.loads((root / Q27).read_text())
    w = c['streamed_weight_bytes_8bit']
    kv = c['kv_bytes_8k_fp8'] + c['recurrent_state_read_write_bytes_per_token']
    lm = c['lm_head_bytes_8bit']
    sram_iso = (m.Q_ROM['dies'] * m.Q_ROM['die_mm2'] - 4 * m.Q_DIE_RIGHT_MM2) / m.SRAM_MM2_PER_MB
    pts = {f'hbm_accel_{n}_stacks': m.qwen_point(n, m.Q_STACK_TBPS_MEASURED, sram_iso, weights=w, kv=kv, lmhead=lm)
           for n in (16, 24)}
    gpu = m.GPU_FIXED_S_QWEN * c['num_layers'] / 36 + m.B200_S_PER_B * (w + kv)
    study = m.build_qwen27()
    return dict(config=Q27, source_revision=c['source_revision'], streamed_weight_bytes=w,
                kv_and_state_bytes_per_token_8k=kv, lm_head_bytes=lm, **pts,
                b200_fp8_tier2_tok_s=round(1 / gpu, 1),
                study_assumed=study, evidence='MODEL; DFlash tau is the Qwen3-8B b16 tau (not measured on 27B)',
                delta_vs_study_ar_pct={k: round(100 * (pts[k]['ar_tok_s'] / study[k]['ar_tok_s'] - 1), 1) for k in pts})


def silicon(logic_mm2, stacks, dram_mm2_per_stack):
    """All DRAM core dies plus base die; no logic-only iso-area substitution."""
    if (isinstance(stacks, bool) or not isinstance(stacks, int) or stacks < 0
            or not math.isfinite(logic_mm2) or logic_mm2 <= 0
            or not math.isfinite(dram_mm2_per_stack) or dram_mm2_per_stack <= 0):
        raise ValueError('positive logic, explicit nonnegative integer stack count and positive DRAM area required')
    dram = stacks * dram_mm2_per_stack
    return dict(logic_mm2=logic_mm2, stacks=stacks, dram_core_and_base_mm2=dram,
                total_silicon_mm2=logic_mm2 + dram)


def iso_power(rate, static_w, dynamic_J_per_token, budget_w):
    """Necessary average-power bound with retained static draw; not a timing proof.

Do not claim clock scaling, more TP ranks, overlap or instantaneous PDN closure.
"""
    if any(not math.isfinite(x) or x <= 0 for x in (rate, static_w, dynamic_J_per_token, budget_w)):
        raise ValueError('finite positive source power and rate inputs required')
    headroom = budget_w - static_w
    bound = min(rate, max(0.0, headroom) / dynamic_J_per_token)
    return dict(budget_w=budget_w, static_w=static_w, dynamic_J_per_token=dynamic_J_per_token,
                average_rate_upper_bound_tok_s=bound,
                source_unrestricted_rate_hypothesis_tok_s=rate,
                minimum_mean_intertoken_us=None if bound == 0 else 1e6 / bound,
                static_floor_exceeds_budget=headroom <= 0,
                instantaneous_power_and_throttling_schedule_qualified=False,
                scope='necessary average-power envelope only; no measured iso-power rate')


def _load_study(root):
    for name, expected in STUDY_PINS.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'frozen study changed: {name}')
    path = root / (STUDY + 'ladder_model.py')
    spec = importlib.util.spec_from_file_location('_ha_frozen_ladder', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rec = json.loads((root / (STUDY + 'ladder.json')).read_text())
    ds, qwen = mod.build_ds(), mod.build_qwen()
    if ds != rec['ds'] or qwen != rec['qwen']:
        raise ValueError('study numerical replay differs; no fitting or expectation replacement')
    return mod, rec, ds, qwen


def build(u):
    root = u.ROOT
    m, historical, ds, qwen = _load_study(root)
    # Separate authorities: the legacy DAG has 329 boundaries. W19 uses the
    # composed barrier count (~343); R0c replaces its postponed first access.
    services = []
    for profile in ('off', 'low', 'central', 'high'):
        time, parts, boundaries = u.v41_hbm_chain(True, service=profile)
        services.append(dict(profile=profile, authority='legacy architecture DAG, not W19',
                             token_us=time, parts_us=parts, boundaries=boundaries,
                             evidence='UNVALIDATED_SERVICE_MODEL'))
    gpu = u.gpu_tier2()
    gpu_ds = next(x for x in gpu if 'V4.1' in x['design'])
    comparisons = m.build_compare(ds, qwen)['ds']
    area_cases = m.DRAM_MM2_PER_STACK
    rows = []
    for i, row in enumerate(comparisons):
        rows.append(dict(id=f'ds_{i}', model='DeepSeek-V4.1', study_point=row,
                         area_sensitivities={k: silicon(row['logic_mm2'], row['stacks'], area_cases[k])
                                             for k in ('low', 'central', 'high')},
                         evidence='UNVALIDATED_MODEL_HYPOTHESIS', adopted=False))
    # Qwen option-C and HBM candidate have identical logic footprint and stack
    # count at the study's iso-total point. Macro fit and power are not inferred.
    q_areas = {}
    for key, dies, stacks, logic in [('same_silicon_as_ablation', 2, 8, 2 * m.Q_DIE_FULL_MM2),
                                    ('iso_total_silicon_with_rom', 4, 16, 4 * m.Q_ROM['die_mm2'])]:
        point = qwen[key]
        q_areas[key] = dict(dies=dies, area_sensitivities={
            k: silicon(logic, stacks, area_cases[k]) for k in ('low', 'central', 'high')},
            ar_power_model=point['power_ar'], dflash_power_model=point['power_dflash'],
            sram_mib=point['sram_mib'], sram_macro_fit_and_routes_qualified=False)
    power_rows = []
    # These budgets are different evidence classes, never conflated.
    budgets = {'eight_B200_measured_decode_draw': 8 * 689.0,
               'eight_B200_1200W_TDP_sensitivity': 8 * 1200.0}
    for stacks in (384, 192):
        static = m.DS_HBM_STATIC_GATED_W - (384 - stacks) * m.HBM_IDLE_W_STACK
        for label, budget in budgets.items():
            power_rows.append(dict(model='DeepSeek-V4.1', stacks=stacks, mode='AR',
                                   power_basis=label, **iso_power(ds['1M']['firm']['best_ar_tok_s'],
                                   static, m.DS_HBM_DYN_J, budget),
                                   source='study transferred dynamic energy and gated-static constants',
                                   actual_routing_and_capacity_qualified=False))
    for key in q_areas:
        for mode, power_key, rate_key in [('AR', 'power_ar', 'ar_tok_s'),
                                        ('DFlash_lab_tau', 'power_dflash', 'dflash_tok_s')]:
            pt = qwen[key].get('point', qwen[key].get('ar'))
            power = qwen[key][power_key]
            rate = pt[rate_key]
            dynamic = power['J_per_token'] - power['static_w'] / rate
            for basis, budget in [('one_B200_measured_decode_draw', 689.0),
                                  ('one_B200_1200W_TDP_sensitivity', 1200.0)]:
                power_rows.append(dict(model='Qwen3-8B', geometry=key, mode=mode,
                                       power_basis=basis, **iso_power(rate, power['static_w'], dynamic, budget)))
    historical_energy = {}
    economics = json.loads((root / 'results/uarch/economics.json').read_text())
    for design, modes in [('qwen_hbm', ('ar', 'dflash')), ('v41_hbm', ('ar', 'mtp'))]:
        historical_energy[design] = {}
        for mode in modes:
            r = economics[design][mode]
            historical_energy[design][mode] = dict(
                evidence='historical legacy-DAG ablation, not W19 or accelerator',
                batch1=r['rows'][0], saturated=next(x for x in r['rows'] if x['batch'] == r['sat_batch']),
                source=f'results/uarch/economics.json#{design}.{mode}')
    # Reuse finite die-count/stack choices already priced by consolidation. The
    # 96-rank accelerator delta is NOT transferred to another TP geometry.
    sweep = json.loads((root / 'results/uarch/consolidation.json').read_text())['hbm']['v41_sweep']
    matched = []
    for area_case in ('low', 'central', 'high'):
        per_stack = area_cases[area_case]
        target = silicon(16 * 800.0, 64, per_stack)['total_silicon_mm2']
        for r in sweep:
            area = silicon(r['silicon_mm2'], r['dies'] * r['stacks_per_die'], per_stack)
            if r['feasible'] and area['total_silicon_mm2'] <= target:
                matched.append(dict(area_case=area_case, budget_total_silicon_mm2=target,
                                    dies=r['dies'], stacks_per_die=r['stacks_per_die'], area=area,
                                    unused_silicon_budget_mm2=target - area['total_silicon_mm2'],
                                    historical_ablation=r['ar'], accelerator_rate=None,
                                    reason='96-rank ladder not qualified at this TP; no linear rate scaling'))
    gates = {rid: dict(status='UNVALIDATED', ordered_gates={g: 'NOT_PASSED' for g in GATES},
                       adopted=False, modeled_input=meta) for rid, meta in m.RUNG_META.items()}
    clock = dict(source_commit='2078c269c4a14dd566b96a73b52a272582faa13f',
                 evidence='placed control-loop screens; not final routed SS/FF',
                 reported_MHz={'SM_issue': [750, 815], 'bulk_copy': [590, 680],
                               'W6_SECDED_fence': 429, 'KV_lifecycle': 458},
                 admission=False, throughput_halving_allowed=False,
                 placed_miss_under_150ps='route before concluding',
                 required_fix='lookahead or registered flags with preserved issue throughput')
    source_paths = list(STUDY_PINS) + ['tools/uarch_model.py', 'tools/hbm_accelerator_model.py',
        'results/uarch/consolidation.json', 'results/uarch/economics.json',
        'results/uarch/dsrom_gpu_index_scan_correction_20261003/model.json',
        'results/uarch/dsrom_hub_edge_wires_20261003/model.json',
        'results/uarch/hbm_accelerator_integration_20261003/defaults_before.json',
        'results/uarch/v41_hbm_service_term_20261003/uarch_model_service_term.patch',
        'results/uarch/hbm_accelerator_integration_20261003/VALIDATION_ADDENDUM.md',
        'results/uarch/hbm_accelerator_integration_20261003/C1_C5hc_REPLAY.md', Q27]
    return dict(schema='opentallas.uarch.hbm_accelerator_integration.v2',
                status='UNVALIDATED_MODEL_HYPOTHESES', default_enabled=False, adopted=False,
                study_source_commit='a3ed9c36d50312f33fa99bf2b49d31c0423ec3f9',
                published_accelerator_rates=[], measured_composition=None,
                hypotheses=dict(ds=ds, qwen=qwen, qwen27=qwen27_sourced(root, m)),
                ladder_reproduction=dict(ds=ladder_reproduction(ds, historical['ds']),
                                         qwen=ladder_reproduction(qwen, historical['qwen'])),
                measured_composition_record=COMPOSITION,
                labeled_baselines=dict(gpu_faithful_R0=gpu_faithful_r0(m, ds), legacy_service_rows=services,
                    w19_recorded='custom 62-cycle hardware barrier; not GPU-faithful grid sync',
                    gpu_grid='1.43 us historical cooperative-grid synchronization assumption; not measured B200',
                    corrected_B200=gpu_ds,
                    full_score_AR_tok_s=1 / u.gpu_tier2_v41_ctx(1048576, candidate_gather=False),
                    B200_MTP='existing 1.94x sensitivity; not DSpark workload-matched tau',
                    H100=next(x for x in qwen['gpus'] if 'H100' in x['gpu'])),
                fairness=dict(DRAM_core_and_base_mm2_per_stack=area_cases,
                    DRAM_mm2_per_stack_sourced=DRAM_MM2_PER_STACK_SOURCED,
                    ds_sourced_bound_8hi={r['id']: silicon(r['study_point']['logic_mm2'], r['study_point']['stacks'], DRAM_MM2_PER_STACK_SOURCED['bound_8hi']) for r in rows},
                    ds_system_counts=rows, qwen_area=q_areas, qwen_ROM_option_C_area={
                        k: silicon(4 * m.Q_ROM['die_mm2'], 16, area_cases[k])
                        for k in ('low', 'central', 'high')}, iso_power_average_bounds=power_rows,
                    iso_total_silicon_budget_ablation=matched,
                    comparable_workload_precision_context_and_acceptance_qualified=False,
                    historical_ablation_energy=historical_energy, saturated_accelerator_J_per_token=None,
                    saturation_gap='no composed batch/union/credit calendar; never infer from batch1'),
                wire_accounting=dict(source_commit='4ec2eef0e',
                    transfer_scope='four-die collective fit; 96-rank topology remains unvalidated',
                    C1_gather_fixed_ns=m.C1_GATHER_NS, C1_reduce_fixed_ns=m.C1_REDUCE_NS,
                    C5hc_increment_ns=m.INPKG_STEP_NS, endpoint_stages_per_side=34,
                    wire_only_two_endpoint_ns=2 * 34 / 1.2,
                    rule='C1/C5hc transferred fits already include endpoint wires; do not add them twice or replace them by 10ns'),
                gates=gates, clock_blocker=clock, priority=['HA2', 'clock_loops', 'HA8', 'HA1'],
                measured_gate_requirements='exact -> system latency incl wire/CDC/credits/refresh -> area -> routed corridor -> SS60/FF25 -> composed gain >=1%; reject failures, no tuning away',
                resource_price_limits='study costs are estimates; mux/fanout/ports/routes/replicas and clock/power grid require composition before build',
                input_sha256={p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths})
