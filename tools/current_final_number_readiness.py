#!/usr/bin/env python3
"""Current research G0-G5 audit. Historical reports never supply current closure.

Certificates are source-pinned review receipts, not automatic qualification of raw
logs. --check detects stale inputs; --require-final refuses incomplete claims.
No simulation, physical tool, tensor payload or historical report is executed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/arch/current_final_number_readiness_20261002'
TARGETS = ('qwen_rom', 'qwen_hbm', 'deepseek_rom', 'deepseek_hbm')
IDENTITY_FIELDS = ('checkpoint', 'program', 'images', 'source_sha256', 'parameters',
                   'memory_geometry', 'service_parameters', 'clocks', 'placement')
REQUIREMENTS = {
 'G0': ('complete_program', 'legal_addresses_storage', 'source_owned_producers_consumers',
        'finite_buffers_ports_tags_credits', 'write_visibility_lifetimes', 'whole_token_model'),
 'G1': ('full_token_golden_ISA', 'arithmetic_reduction_order', 'representative_context_input_coverage'),
 'G2': ('connected_full_token', 'numerical_state_comparison', 'finite_actual_memory_service',
        'backpressure_reset_drain_CDC', 'persistent_KV_state', 'qualified_checker_raw_return'),
 'G3': ('complete_element_SM_hub', 'real_macro_abstracts_timing', 'parent_integration',
        'OBS_halos_routes_clock_PG', 'disjoint_source_instance_ledger', 'pin_via_escape_exclusions',
        'actual_routing_layer_capacity', 'storage_ownership_binding',
        'detailed_route_extracted', 'DRC_pass', 'workload_power_IR'),
 'G4': ('same_program_RTL_cycle_reconciliation', 'measured_stalls_service_collectives',
        'physical_crossings_frequency', 'critical_path_discrepancies_resolved'),
 'G5': ('optimized_matched_baseline', 'single_user_primary', 'batching_no_single_user_degradation',
        'ablations_sensitivities', 'immutable_versions_commands_fresh_recipe'),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(root, path, used):
    p = root / path
    if not p.is_file():
        used[path] = 'missing'
        return {}
    used[path] = digest(p)
    return json.loads(p.read_text())

def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def timing_errors(record, target):
    errors = []
    domains = {'streaming': 1.2e9}
    if target.startswith('deepseek'):
        domains['serial_chain'] = .9e9
    if record.get('timing_scope') != 'contextual_parent_extracted':
        errors.append('timing is not contextual parent extracted')
    for domain, hz in domains.items():
        for check, corner, uncertainty in [('setup', 'SS', 60), ('hold', 'FF', 25)]:
            v = record.get('timing', {}).get(domain, {}).get(check, {})
            if v.get('corner') != corner or v.get('uncertainty_ps') != uncertainty:
                errors.append(f'{domain} {check} requires {corner}/{uncertainty}ps')
            period = v.get('period_ps')
            if not number(period) or abs(period - 1e12/hz) > .5:
                errors.append(f'{domain} {check} period must match {hz:g}Hz')
            if not number(v.get('worst_slack_ps')) or v['worst_slack_ps'] < 0:
                errors.append(f'{domain} {check} slack missing/negative')
            if v.get('unconstrained_paths') != 0 or v.get('violations') != 0:
                errors.append(f'{domain} {check} unconstrained/violating paths')
    if record.get('capacity_basis') != 'actual_layer_pitch_OBS_PG_pin_via_exclusions':
        errors.append('routing capacity must subtract actual OBS/PG/pin/via exclusions; percentage reserves are not closure')
    if record.get('layout_basis') != 'disjoint_source_matched_instance_union':
        errors.append('inherited area debit is not a disjoint source instance union')
    if record.get('macro_SS_clk_to_q_bound') is not True:
        errors.append('macro SS clock-to-q not bound')
    outline = record.get('outline_mm', [])
    if (not isinstance(outline, list) or len(outline) != 2 or
        not all(number(x) and x > 0 for x in outline) or
        sorted(outline)[0] > 26 or sorted(outline)[1] > 33):
        errors.append('outline must fit 26x33mm without stitching')
    area = record.get('complete_area_mm2')
    valid_outline = (isinstance(outline, list) and len(outline) == 2 and
                     all(number(x) and x > 0 for x in outline))
    if not number(area) or not valid_outline or area <= 0 or area > math.prod(outline):
        errors.append('complete area missing or exceeds legal outline')
    if target.endswith('hbm') and record.get('source_matched_shoreline_PHY') is not True:
        errors.append('HBM shoreline/PHY boundary not qualified')
    return errors

def evaluate(root, target, gate, binding, cert, used):
    errors = []
    identity = binding.get('identity', {})
    if binding.get('identity_bound') is not True or any(not identity.get(k) for k in IDENTITY_FIELDS):
        errors.append('current complete configuration identity unbound')
    if cert.get('schema') != 'opentallas.current-research-gate-certificate.v1':
        errors.append('review certificate missing/wrong schema')
    if cert.get('target') != target or cert.get('gate') != gate or cert.get('mode') != 'AR':
        errors.append('target/gate/AR scope mismatch')
    if cert.get('identity') != identity:
        errors.append('configuration identity mismatch')
    if cert.get('status') != 'pass' or cert.get('evidence_scope') != 'current_full_goal':
        errors.append('not reviewed current full-goal pass')
    pins = identity.get('source_sha256', {})
    if not isinstance(pins, dict) or not pins:
        errors.append('source manifest missing')
    else:
        for path, expected in pins.items():
            p = root / path
            actual = digest(p) if p.is_file() else 'missing'
            used[path] = actual
            if actual != expected:
                errors.append(f'current source mismatch: {path}')
    evidence = cert.get('evidence_sha256', {})
    if not isinstance(evidence, dict) or not evidence:
        errors.append('supporting evidence receipts missing')
    else:
        for path, expected in evidence.items():
            p = root / path
            actual = digest(p) if p.is_file() else 'missing'
            used[path] = actual
            if actual != expected:
                errors.append(f'evidence receipt mismatch: {path}')
    for field in REQUIREMENTS[gate]:
        if cert.get('checks', {}).get(field) is not True:
            errors.append(f'{field} not qualified')
    if gate == 'G0' and target.endswith('hbm') and cert.get('GPU_organisation') is not True:
        errors.append('HBM GPU organisation not bound')
    if gate == 'G3':
        errors.extend(timing_errors(cert, target))
    if gate in ('G2', 'G4'):
        modes = binding.get('claimed_modes', ['AR'])
        qualified = cert.get('qualified_modes', [])
        if any(mode not in qualified for mode in modes):
            errors.append('claimed mode missing exactness/calibration receipt')
    return {'status': 'blocked' if errors else 'pass', 'blockers': errors,
            'required_checks': list(REQUIREMENTS[gate])}

def captured_qwen(root, used):
    base = 'results/rtl/qwen_rom_TP4_terminal_20261002/'
    t = read(root, base+'terminal_manifest.json', used)
    v = read(root, base+'verification_replay.json', used)
    c = read(root, base+'capture.json', used)
    receipt_ok = bool(t.get('artifact_sha256'))
    for name, expected in t.get('artifact_sha256', {}).items():
        p = root/base/name
        used[base+name] = digest(p) if p.is_file() else 'missing'
        receipt_ok &= used[base+name] == expected
    checks = v.get('checks', {})
    required = {f'L{layer}_die{rank}_x.hex' for layer in range(36) for rank in range(4)}
    vectors_ok = required == set(checks) and all(
        x.get('mismatches') == 0 and x.get('words') == 4096 and
        x.get('actual_sha256') == x.get('expected_sha256') for x in checks.values())
    ok = (receipt_ok and vectors_ok and t.get('status') == v.get('status') == 'pass' and
          t.get('runtime_scope_full_token_exact') is True and
          v.get('full_token_exact_at_runtime_scope') is True and
          set(t.get('completed_stages', [])) == {f'L{i}' for i in range(36)} | {'head'} and
          t.get('head_faults') == {'collective': 0, 'core': 0, 'seq': 0} and
          t.get('binary_sha256') == c.get('binary_sha256') and
          v.get('package_sha256') == used.get(base+'capture.json'))
    return {'status': 'pass' if ok else 'blocked', 'scope': t.get('tested_configuration'),
            'token': t.get('rtl_token'), 'logit_bits': t.get('rtl_logit_bits'),
            'cycles': t.get('total_cycles'), 'exact_rank_vectors': len(checks),
            'current_G2_credit': False, 'physical_or_rate_credit': False,
            'current_source_joined': t.get('current_source_joined'),
            'remaining_gates': t.get('remaining_gates'),
            'qualification': 'Receipt consistency of independently reviewed captured numeric PASS; no payload replay or successor transfer.'}

def current_budget(root, binding, used):
    """Explicit current budget binding; historical reservation never overrides it."""
    ref = binding.get('physical_budget', {})
    errors = []
    if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
        return {'status': 'blocked', 'blockers': ['explicit current physical budget binding missing']}
    row = read(root, ref['path'], used)
    if used[ref['path']] != ref['sha256']:
        errors.append('current physical budget receipt mismatch')
    if row.get('schema') != 'opentallas.current-physical-budget.v1' or row.get('target') != 'deepseek_rom':
        errors.append('current physical budget target/schema mismatch')
    if binding.get('identity_bound') is not True or row.get('identity') != binding.get('identity'):
        errors.append('current physical budget configuration/source identity mismatch')
    if row.get('source_sha256') != binding.get('identity', {}).get('source_sha256'):
        errors.append('current physical budget source manifest mismatch')
    for path,expected in row.get('source_sha256', {}).items():
        p=root/path
        used[path]=digest(p) if p.is_file() else 'missing'
        if used[path]!=expected:
            errors.append('current physical budget source bytes mismatch: '+path)
    if row.get('reviewed_complete_inventory') is not True or row.get('unpriced_claim_determining_terms') != []:
        errors.append('current physical inventory incomplete or determining costs unpriced')
    outline=row.get('outline_mm', [])
    valid=(isinstance(outline,list) and len(outline)==2 and all(number(x) and x>0 for x in outline))
    area=row.get('complete_area_mm2')
    if (not valid or sorted(outline)[0]>26 or sorted(outline)[1]>33 or
        not number(area) or area<=0 or area>math.prod(outline)):
        errors.append('current physical budget does not fit legal26x33 outline')
    return {'status':'blocked' if errors else 'pass','blockers':errors,
            'artifact':ref['path'],'complete_area_mm2':area,'outline_mm':outline,
            'scope':'Budget review only; source-extracted contextual physical adapters and G3 still required.'}

def build(root=ROOT):
    used = {}
    bindings = read(root, BASE+'/target_bindings.json', used)
    for path in ('AGENTS.md', 'docs/INTEGRATED_PHYSICAL_PLAN.md',
                 'tools/final_number_readiness.py', 'results/arch/final_number_readiness.json',
                 'tools/current_final_number_readiness.py'):
        p = root/path
        used[path] = digest(p) if p.is_file() else 'missing'
    targets = {}
    for target in TARGETS:
        binding = bindings.get('targets', {}).get(target, {})
        gates = {}
        for gate in REQUIREMENTS:
            path = binding.get('certificates', {}).get(gate, BASE+f'/certificates/{target}_{gate}.json')
            gates[gate] = evaluate(root, target, gate, binding, read(root, path, used), used)
        targets[target] = {'claimed_modes': binding.get('claimed_modes', ['AR']),
                           'gates': gates, 'ready': all(x['status'] == 'pass' for x in gates.values())}
    q = captured_qwen(root, used)
    software = read(root, 'results/uarch/h3_qwen_complete_native_20261002/parent_review.json', used)
    workspace = read(root, 'results/uarch/qwen_native_workspace_provider_r20_20261002/output/join.json', used)
    current_observations = {
        'qwen_hbm_software_native': {'status': software.get('status'),
            'PCs': software.get('PCs'), 'parent_tests': software.get('tests'),
            'hardware_or_rate_credit': False, 'current_full_token_G1_G2_credit': False},
        'qwen_hbm_workspace': {'status': workspace.get('status'),
            'final_native_calendar_source_match': workspace.get('final_native_calendar_source_match'),
            'hardware_or_rate_or_physical_credit': False},
        'qwen_rom_current_KV_physical': {'status': 'blocked',
            'required': ['Current seven-source/parameter join', 'Persistent finite KV fill/ownership/write visibility',
                         'Macro-local KV connected numerical checks', 'Contextual tile/spine/die SS/FF',
                         'Same-program physical/service latency calibration']}}
    budget = read(root, 'results/uarch/dsrom_full_product_binding_20261002/compiled_whole_budget-r6.json', used)
    ledger = budget.get('exact_once_area_ledger_mm2', {})
    area = ledger.get('conservative_no_containment_credit_die_total')
    margin = ledger.get('conservative_no_containment_credit_reticle_margin')
    ds = {'candidate': budget.get('candidate'), 'status': 'blocked', 'complete_area_mm2': area,
          'legal_envelope_mm2': 858, 'margin_mm2': margin,
          'budget_consistent': number(area) and number(margin) and abs(858-area-margin) < 1e-8,
          'qualification': 'Conservative source-pinned reservation FAIL, not a fundamental minimum or impossibility proof; not legal placement or SS/FF closure.',
          'unpriced_positive_terms': ledger.get('unpriced_nonzero_terms'),
          'physical_credit': False}
    # Historical FAIL remains visible; an explicitly source-bound successor
    # budget can replace its binding without mutating or erasing that record.
    selected_budget=current_budget(root, bindings.get('targets', {}).get('deepseek_rom', {}), used)
    ds_gate=targets['deepseek_rom']['gates']['G3']
    if selected_budget['status'] != 'pass':
        ds_gate['status']='blocked'
        ds_gate['blockers'].extend(selected_budget['blockers'])
    targets['deepseek_rom']['ready']=all(v['status']=='pass' for v in targets['deepseek_rom']['gates'].values())
    return {'schema': 'opentallas.current-final-number-readiness.v1', 'source_sha256': used,
            'historical_report_is_current_authority': False,
            'objective': 'Minimum single-user AR latency; speculative modes conditional on claimed performance.',
            'clock_policy': {'streaming_hz': 1200000000, 'deepseek_serial_hz': 900000000,
                             'setup_corner': 'SS', 'setup_uncertainty_ps': 60,
                             'hold_corner': 'FF', 'hold_uncertainty_ps': 25, 'TT_credit': False},
            'captured_qwen_TP4_numeric': q, 'deepseek_S58_physical_screen': ds,
            'deepseek_current_bound_budget': selected_budget,
            'certificate_validation_scope': 'Review-receipt schema/hash/scope checks; generic certificates are not automatic raw timing, route or functional proof. Add source-extracted artifact adapters as campaigns become available.',
            'current_scoped_observations': current_observations,
            'targets': targets, 'terminal_ready': all(t['ready'] for t in targets.values()),
            'claim_boundary': 'Current G0-G5 all four targets required. Numerical, directed, software, inventory, TT and outline evidence never substitute for contextual physical/token service gates.'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--require-final', action='store_true')
    args = ap.parse_args()
    result = build()
    out = ROOT/BASE/'readiness.json'
    if args.check:
        if not out.is_file() or json.loads(out.read_text()) != result:
            print('stale current readiness report'); return 2
    else:
        out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('captured_QTP4_numeric='+result['captured_qwen_TP4_numeric']['status'])
    for target, row in result['targets'].items():
        print(target+': '+', '.join(k+'='+v['status'] for k,v in row['gates'].items()))
    print('terminal_ready='+str(result['terminal_ready']))
    return 1 if args.require_final and not result['terminal_ready'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
