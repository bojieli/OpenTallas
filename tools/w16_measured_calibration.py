#!/usr/bin/env python3
"""Source-bound W16 measurement ledger; never updates the analytical model.

Create a NEW receipt with --out. --check verifies pins before re-evaluating
supported component parameters. Unknown full-config mappings refuse pricing.
The source/evidence handoff is the JSON receipt, not a product-rate claim.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
TP2 = 'results/rtl/qwen_rom_w12_runtime/terminal_20261001/rt64_token.json'
ERRATA = 'results/rtl/qwen_rom_w12_runtime/terminal_20261001/rt64_token_errata.json'
VERIFY = 'results/rtl/qwen_rom_w12_runtime/terminal_20261001/verification.json'
TP4 = 'results/rtl/qwen_rom_w12_runtime/tp4_progress_20261001.json'
FIELD = 'results/rtl/w17_companion_field_32d35c69c/result.json'
LAUNCH = 'results/rtl/w17_companion_field_32d35c69c/launch.json'
BASELINE = 'results/uarch/w10_baseline_main_prequalification_bb01.json'
REDUCED = 'results/quality/qcnam_w16_recovery_20261001/w11_u2517.json'
ATTR = 'results/quality/qcnam_w16_recovery_20261001/w11_unfused_wired_handoff.json'
QC = 'results/quality/qcnam_completed_core_audit_v2_20261001.json'
CAPACITY = 'results/uarch/w16_measured_calibration_20261001/w19_capacity_preflight.json'
CAPACITY_PIN = 'results/uarch/w16_measured_calibration_20261001/w19_capacity_provenance.json'
W19_PROGRAM = 'results/rtl/w19_hbm_tp96_program_oreduce.json'
W19_FLOORPLAN = 'results/floorplan/hbm_gpu/v41_hbm_die.json'
CONFIG = dict(tp=2, groups_per_die=6144, tiles_per_die=1536, su_width=64,
              tree_cut=6, smin=6, smax=11, collective_lat_cycles=11,
              su_reducer_time_levels=7, count_width=18, kv_fp8=True,
              pruned=True, scale_local=False)
SOURCES = ('tools/w16_measured_calibration.py', 'tools/uarch_model.py',
           'tools/arch_budget_qwen3.py', 'tools/hdc_timing.py',
           'rtl/v41rom/ot_v41_rom_elem_w10.sv',
           'rtl/v41rom/ot_v41_rom_elem_q_w10.sv',
           'rtl/v41rom/ot_v41_rom_elem.sv',
           'rtl/w17_runtime/v41die/ot_v41_pair.sv')
RECORDS = (TP2, ERRATA, VERIFY, TP4, FIELD, LAUNCH, BASELINE, REDUCED, ATTR, QC)


class Refusal(ValueError):
    """Measurement cannot justify the requested configuration or claim."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def sha(path, root=ROOT):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def read(path, root=ROOT):
    return json.loads((root / path).read_text())


def match_config(actual, requested):
    require(actual == requested, 'configuration mismatch: ' + ', '.join(
        k for k in sorted(set(actual) | set(requested))
        if actual.get(k) != requested.get(k)))


def refuse_product_transfer(scope, requested_scope, unsupported=()):
    require(scope == requested_scope, 'measurement scope cannot transfer to ' + requested_scope)
    require(not unsupported, 'unsupported mappings: ' + ', '.join(unsupported))


def exact_checks(checks, expected):
    require(set(checks) == set(expected), 'incomplete checkpoint coverage')
    for key, c in checks.items():
        require(c['mismatches'] == 0 and c['words'] == 4096 and
                c['actual_sha256'] == c['expected_sha256'], 'checkpoint mismatch: ' + key)


def validate_tp2(r, errata, verification, record_sha):
    match_config(r['design_point'], CONFIG)
    match_config(errata['authoritative_design_point'], CONFIG)
    require(errata['original_record_sha256'] == record_sha ==
            verification['tp2_terminal_record_sha256'], 'TP2 receipt binding mismatch')
    require(r['status'] == 'pass' and r['source_stable'] and verification['tp2_verified'],
            'TP2 exact receipt not passing/stable')
    require(r['binary_sha256'] == verification['tp2_binary_sha256'] and
            r['generated_core_sha256'] == verification['tp2_generated_core_sha256'],
            'TP2 executable identity mismatch')
    stages = [f'L{i}' for i in range(36)] + ['head']
    require(r['stages_run'] == stages and set(r['stages']) == set(stages), 'incomplete TP2 token')
    exact_checks(r['layer_x_checks'], [f'L{i}_die{d}_x' for i in range(36) for d in range(2)])
    require(r['layer_x_checks'] == verification['tp2_layer_checks'], 'TP2 verification checks differ')
    require(r['rtl_token'] == r['oracle_token'] == 50994 and
            r['rtl_logit_bits'] == r['oracle_logit_bits'], 'TP2 token/logit mismatch')
    stage_cycles = sum(v['cycles'] for v in r['stages'].values())
    require(r['total_cycles'] == 151557, 'TP2 measured total changed')
    # Host reset/stage handoff edges are outside stage spans. Do not invent
    # a per-stage overhead or mistake the difference for collective service.
    require(stage_cycles <= r['total_cycles'], 'stage spans exceed token total')
    return dict(config=r['design_point'], status='EXACT_HISTORICAL_TOKEN',
                position=0, token=50994, total_cycles=r['total_cycles'],
                stage_span_cycles=stage_cycles,
                outside_stage_span_cycles=r['total_cycles'] - stage_cycles,
                layer_span_cycles=sum(r['stages'][f'L{i}']['cycles'] for i in range(36)),
                head_span_cycles=r['stages']['head']['cycles'],
                binary_sha256=r['binary_sha256'], generated_core_sha256=r['generated_core_sha256'],
                measured_body_cycles=None, measured_collective_service_cycles=None,
                measured_memory_service_cycles=None,
                pending='Stage spans include overlapping work; collective LAT11 is a link parameter, not measured all-reduce service. Embedding preloaded; host supplies stage sequencing and zero KV window.')


def source_binding(record, root=ROOT):
    """Keep original run pins; report drift without silently rebinding history."""
    pins = record.get('source_sha256', record.get('input_sha256', {}))
    return {p: dict(recorded_sha256=h,
                    current_sha256=sha(p, root) if (root / p).is_file() else None,
                    matches_current=(root / p).is_file() and sha(p, root) == h)
            for p, h in sorted(pins.items())}


def supported_qwen_components(config):
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    # The interfaces are checked as well as the results: no defaults silently
    # substitute SU1024 or the ctx-derived LV for this measured configuration.
    require('lv' in inspect.signature(Q.as_built).parameters and
            'su_width' in inspect.signature(Q.as_built).parameters,
            'Qwen replay no longer exposes measured SU/LV')
    require(config['su_width'] >= 8 and config['su_width'] & (config['su_width'] - 1) == 0,
            'unsupported reducer width')
    require(config['su_reducer_time_levels'] >= 0, 'invalid reducer levels')
    tail = T.red_tail(dict(T.K, red_lv=config['su_reducer_time_levels']), config['su_width'])
    return dict(matched=dict(su_width=config['su_width'], red_lv=config['su_reducer_time_levels']),
                reducer_tail_cycles=tail, kind='ANALYTICAL_COMPONENT_ONLY',
                measured_cycles=None, domain='serial_target_0.9GHz; simulation cycles are not physical closure',
                mapping=dict(tp='Q.as_built shape argument; die_shape is TP2',
                             groups_per_die='Q.as_built groups', su_width='Q.as_built su_width',
                             su_reducer_time_levels='Q.as_built lv -> T.red_tail red_lv',
                             smax='Q.as_built max_split caps S, so maximum S=2**smax; no minimum split interface'),
                unsupported=['smin (minimum split absent)', 'tree_cut (cut placement absent)',
                             'collective_lat_cycles (link parameter is not total service)',
                             'runtime images/program and host stage sequencing',
                             'pruned/scale_local/kv_fp8/count_width implementation correspondence',
                             'wire_stages exact spine/return correspondence'],
                full_token_model_cycles=None, matched_full_config=False,
                pricing='REFUSED full-token pricing; supported reducer component only')


def validate_reduced(r, attr):
    s = r['single_step']
    require(r['status'] == 'fail' and s['pass'], 'historical W11 overall FAIL must remain visible')
    require(s['cycles'] == 398676 and s['timing_model']['cycles'] == 344131,
            'historical reduced timing changed')
    require(attr['comparison']['unfused_cycles'] == s['cycles'] and
            attr['comparison']['unfused_cycles'] - attr['comparison']['fused_cycles'] ==
            attr['comparison']['saved_cycles'], 'reduced comparison inconsistent')
    require(sum(attr['su_issue_attributed_intervals_by_region'].values()) ==
            attr['su_issue_attributed_intervals_total'], 'issue attribution inconsistent')
    return dict(engine_parameters=r['engine_parameters'], overall_verdict=r['status'],
                functional_single_step_pass=s['pass'], measured_cycles=s['cycles'],
                historical_model_cycles=s['timing_model']['cycles'],
                cycle_difference=s['cycles'] - s['timing_model']['cycles'],
                comparison=attr['comparison'],
                issue_attributed_intervals=attr['su_issue_attributed_intervals_total'],
                interval_definition=attr['definition'],
                product_price=None, eligible_gain=False, adopt=False,
                assumptions=['Reduced single-step vehicle; HHW8/MG8/SUN16/SUM8, as-built attention/index/selection/Engram.',
                             'Issue intervals include waits; they are not per-region busy counters.',
                             'No full-shape or product-overlap mapping; no raw ratio correction.',
                             'Physical timing and hub routing-layer acceptance are not established.'])


def qc_eligibility(qc):
    require(qc['definitive_core_failure'] and not qc['hardware_adopted'],
            'expected immutable mandatory QC-NAM core stability FAIL')
    failed = [k for k, v in qc['criteria'].items() if v.get('pass') is False]
    require(failed, 'QC-NAM FAIL has no failed mandatory criterion')
    return dict(variant='DeepSeek QC-NAM norm-after-matvec', stability='FAIL',
                failed_criteria=failed, eligible_gain=False, adopt=False,
                full_gate_complete=qc['full_gate_complete'], full_verdict=qc['full_verdict'],
                reason=qc['irreversibility'], scope=qc['scope'])


def resident_records(program, floorplan):
    """Count actual SM issue records per stack; do not scale rounded byte sums.

    Mirrors b22e48b29 gpu_checkpoint_sm_layout issue geometry, with a9b898250
    templates' resident multiplicity (all 384 routed experts; dense once).
    Compact rounding is per SM/family segment, padded baseline is 256 B per
    issue record. Equality to the owner compact manifest is checked separately.
    """
    homes = {sm:int(stack) for stack,sms in floorplan['quadrants'].items() for sm in sms}
    require(set(homes) == set(range(32)), 'W19 SM stack mapping incomplete')
    records, compact = [[0]*4 for _ in range(96)], [[0]*4 for _ in range(96)]
    for layer in program['layers']:
        for op in layer['ops']:
            if op['kind'] != 'mv':
                continue
            multiplicity = 1
            if isinstance(op['w'], list) and isinstance(op['w'][0], int):
                if op['w'][0] == 0:
                    multiplicity = 384
                elif op['w'][0] != 6:
                    continue  # Same non-SM boundary as the owner producer.
            k, fmt = op['k'], op['fmt']
            require(fmt in ('fp4','fp8','bf16') and k > 0 and
                    (fmt == 'bf16' or k % 32 == 0), 'unsupported W19 matrix geometry')
            lanes = {'fp4':8,'fp8':4,'bf16':64}[fmt]
            chunks = ((k if fmt == 'bf16' else k//32) + 7)//8
            groups = (chunks + lanes - 1)//lanes
            require(groups*8 <= 128 and len(op['rows']) == 96, 'W19 issue/rank geometry overflow')
            for rank, (lo,hi) in enumerate(op['rows']):
                n = hi-lo
                require(n >= 0, 'negative W19 row slice')
                per_sm = (n+31)//32
                for sm in range(32):
                    begin, end = min(sm*per_sm,n), min((sm+1)*per_sm,n)
                    count = (end-begin)*groups*8
                    records[rank][homes[sm]] += count*multiplicity
                    compact[rank][homes[sm]] += ((count*136+127)//128)*128*multiplicity
    return records, compact


def w19_capacity(c, provenance, program, floorplan):
    require(c['ranks'] == 96 and c['sm_per_rank'] == 32, 'W19 organisation mismatch')
    stacks = c['rank_stack_bytes']
    require(len(stacks) == 96 and all(len(s) == 4 for s in stacks), 'W19 rank coverage incomplete')
    require(sum(map(sum, stacks)) == c['all_rank_weight_image_bytes'] == 418265202688,
            'W19 image sum mismatch')
    peak = max(map(max, stacks))
    bits = ((peak + 31)//32 - 1).bit_length()
    aperture = (1 << c['existing_sector_address_bits']) * 32
    require(peak == c['max_resident_stack_bytes'] == 1395830400 and
            bits == c['required_sector_address_bits'] == 26 and
            c['existing_sector_address_bits'] == 24 and aperture == 536870912 and
            not c['static_resident_address_fit'], 'W19 aperture failure incorrectly mapped')
    schedule = c['schedule_budget']
    require(schedule['descriptors_per_sm_layer'] == 18 and
            schedule['loaded_latency_ns_assumed'] == 500 and
            schedule['incremental_ns_token_vs_one_fetch_per_layer'] == 40*17*500,
            'W19 static config drain assumption changed')
    require(not schedule['enabled_default'], 'unmeasured W19 schedule cannot be enabled')
    records, compact = resident_records(program, floorplan)
    require(compact == stacks, 'W19 compact record-count reconstruction disagrees with owner manifest')
    padded = [[n*256 for n in row] for row in records]
    padded_peak = max(map(max,padded))
    padded_bits = ((padded_peak+31)//32-1).bit_length()
    return dict(source_commit=provenance['source_commit'], layout_scope='REJECTED_COMPACT_136B_CANDIDATE',
                all_rank_sm_image_bytes=c['all_rank_weight_image_bytes'],
                ranks=96, max_resident_stack_bytes=peak, existing_aperture_bytes=aperture,
                required_sector_address_bits=bits, existing_sector_address_bits=24,
                address_fit=False, modulo_credit=False, reload_credit=False,
                compact_candidate=dict(record_bytes=136, padded_segment_alignment_bytes=128,
                                       eligible_gain=False, adopt=False, rejected=True),
                padded_baseline=dict(record_bytes=256, rank_stack_records=records,
                                     all_rank_records=sum(map(sum,records)),
                                     all_rank_sm_image_bytes=sum(map(sum,padded)),
                                     max_resident_stack_bytes=padded_peak,
                                     required_sector_address_bits=padded_bits,
                                     address_fit=padded_peak <= aperture,
                                     derivation='Actual op/rank/SM issue record counts times 256; no rounded compact-byte ratio.',
                                     capacity_kind='ANALYTICAL_STATIC_IMAGE_ONLY',
                                     measured_service_ns=None, full_token_price=None,
                                     eligible_gain=False, adopt=False),
                non_sm_capacity={k:'UNQUALIFIED: separate resident images/address allocation and controller service required'
                                 for k in ('norm_and_HC_constants', 'embedding', 'Engram', 'KV', 'index')},
                schedule=dict(op_order=schedule['schedule'], config_change=schedule['fetch_cfg_change'],
                              incremental_ns_token_assumed=340000, formula='40 * (18 - 1) * 500 ns',
                              measured_ns_token=None, adopted=False, priced_in_headline=False,
                              free_multi_family_whole_expert_stream_credit=False),
                full_token_price=None, eligible_gain=False, adopt=False,
                pending='Address capacity FAIL; non-SM images/capacity, connected golden runtime, controller contention, static config/drain measurements and contextual SS/FF remain open.',
                Euler_handoff=provenance['Euler_handoff'])


def build(root=ROOT):
    require(root.resolve() == ROOT.resolve(), 'model imports must use this tool worktree')
    r, e, v, tp4, f, launch, b, reduced, attr, qc = [read(p, root) for p in RECORDS]
    token = validate_tp2(r, e, v, sha(TP2, root))
    components = supported_qwen_components(token['config'])
    require(tp4['design_point']['tp'] == 4 and tp4['design_point']['su_width'] == 64,
            'TP4 partial receipt configuration changed')
    exact_checks(tp4['checks'], [f'{l}_die{d}' for l in tp4['completed_layers'] for d in range(4)])
    require('head' not in tp4['completed_layers'], 'TP4 receipt no longer partial')
    require(f['status'] == 'pass' and f['source_stable'] and f['golden_mismatch'] == 0 and
            f['negative_control_rejected'], 'W17 field gate not exact with negative control')
    pair_pin = f['source_sha256']['rtl/w17_runtime/v41die/ot_v41_pair.sv']
    require(pair_pin == sha('rtl/w17_runtime/v41die/ot_v41_pair.sv', root),
            'cannot interpret W17 element namespace after pair source drift')
    pair = (root / 'rtl/w17_runtime/v41die/ot_v41_pair.sv').read_text()
    require(re.search(r'\bot_v41_rom_elem\s*#', pair) is not None and
            'ot_v41_rom_elem_w10 #' not in pair, 'W17 field namespace is not legacy element')
    field = dict(source_commit=launch['source_commit'], params=f['params'],
                 measured_cases=[{k:c[k] for k in ('name','positions','rows','K','cycles_rtl',
                                                  'stream_beats','t_phase_model','t_read')} for c in f['cases']],
                 component_gate='PASS', element='ot_v41_rom_elem (legacy)',
                 matched_w10_lat8=False, product_price=None,
                 pending='Small field checkpoint slices; measured completion includes config/load/return. Issue/read figures alone cannot price complete phases or full token. No LAT8/4096-row PP bridge measurement.')
    import uarch_model as U
    baseline = U.w10_baseline_model()
    require(baseline['qualification'] == b['qualification'], 'W10 baseline qualifier drift')
    require(baseline['composition'] == b['composition'], 'W10 historical composition no longer matches current model')
    baseline_audit = dict(qualification=baseline['qualification'],
                          composition=baseline['composition'], kind='ANALYTICAL_LATENCY_AUDIT',
                          matched_parameter='elem_stages=7 vs CUT-derived LAT8; not a measured field calibration',
                          product_adoption=False, measured_field_cycles=None,
                          unsupported=['whole-field elem_fill=78 inherited',
                                       'W17 companion uses legacy element, not FAST1/PP1 baseline'])
    capacity, capacity_pin = read(CAPACITY), read(CAPACITY_PIN)
    require(sha(CAPACITY) == capacity_pin['origin_sha256'], 'W19 imported capacity pin mismatch')
    paths = set(SOURCES + RECORDS + (CAPACITY, CAPACITY_PIN, W19_PROGRAM, W19_FLOORPLAN)) | set(U.CONS_SOURCES)
    # Freeze imported model helpers, as well as the explicitly listed model
    # records. This does not refresh any current model or historical pin.
    paths.update(str(Path(m.__file__).resolve().relative_to(root))
                 for m in tuple(sys.modules.values()) if getattr(m, '__file__', None)
                 and Path(m.__file__).resolve().is_relative_to(root / 'tools')
                 and Path(m.__file__).suffix == '.py')
    # Also freeze the current sources behind historical pins, retaining those
    # historical pins and exposing every mismatch in the receipt below.
    for rec in (r, f, b, reduced, qc):
        paths.update(p for p in rec.get('source_sha256', rec.get('input_sha256', {}))
                     if (root / p).is_file())
    return dict(schema='opentallas.w16.measured_input_calibration.v1',
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip(),
                objective='minimum single-user decode latency; batching secondary',
                policy=dict(streaming_target_hz=1200000000, serial_target_hz=900000000,
                            setup_corner='SS', hold_corner='FF', setup_uncertainty_ps=60,
                            hold_uncertainty_ps=25, physical_signoff=False,
                            product_headline_promotion=False, model_source_changed=False),
                designs=dict(qwen_rom='matched component / unmatched token pending',
                             v41_rom='field scope + separate LAT7/LAT8 model audit; token pending',
                             qwen_hbm='no matching connected full-token service measurement in these inputs; unpriced',
                             v41_hbm='no matching connected full-token service measurement in these inputs; unpriced'),
                qwen_tp2=token, qwen_supported_components=components,
                qwen_tp4_partial=dict(config=tp4['design_point'], completed_layers=tp4['completed_layers'],
                                      logged_stage_spans=tp4['log_tail'], full_token=False, product_price=None,
                                      pending='G/LV/wire/source/binary identity absent from this progress receipt; parent W12 identity collector owns completion.'),
                qwen_tp4_historical_l0=dict(rtl=U.QWEN_L0_RTL, attribution=U.QWEN_L0_ATTR,
                                           kind='HISTORICAL_ATTRIBUTION_ONLY', product_price=None,
                                           pending='Historical L0/itrace paths are not present here. LAT339 is not all-reduce service. Segmentation/SMIN7/treecut7 differ from TP2. No fresh exact full-config model check.'),
                w17_field=field, w10_baseline_audit=baseline_audit,
                w11_reduced=validate_reduced(reduced, attr), qc_nam=qc_eligibility(qc),
                w19_capacity=w19_capacity(capacity, capacity_pin, read(W19_PROGRAM), read(W19_FLOORPLAN)),
                historical_source_bindings={p:source_binding(read(p), root) for p in (TP2,FIELD,BASELINE,REDUCED,QC)},
                pins={p:sha(p, root) for p in sorted(paths)},
                handoff='Parent owns main/TASKS/push and W12 identity integration. No engine RTL or W10/W19 model edits. Any later model change requires parent coordination, numerical validation, and refresh of all matching current records.')


def check(receipt, root=ROOT):
    for p, h in receipt['pins'].items():
        require((root / p).is_file() and sha(p, root) == h, 'source/evidence pin drift: ' + p)
    fresh = build(root)
    # Commit changes after creation are expected; every computational input is
    # pinned separately. The receipt keeps its original base commit unchanged.
    fresh['base_commit'] = receipt['base_commit']
    require(fresh == receipt, 'calibration receipt no longer reproduces')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--check', type=Path)
    args = ap.parse_args()
    try:
        if args.check:
            check(json.loads(args.check.read_text()))
            print('PASS: source pins, matched component checks, refusal boundaries and preserved FAILs')
        else:
            # Exclusive creation: failed/historical receipts are never replaced.
            require(not args.out.exists(), 'receipt already exists; retain historical evidence')
            result = build()
            with args.out.open('x') as out:
                json.dump(result, out, indent=2, sort_keys=True, allow_nan=False)
                out.write('\n')
            print('Created calibration-only receipt: ' + str(args.out))
    except (Refusal, FileExistsError) as exc:
        print('REFUSED: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
