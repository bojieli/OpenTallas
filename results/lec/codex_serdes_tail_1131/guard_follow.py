"""Collect the existing owned canary. Never launches a proof or changes inputs."""
import json
import time
from pathlib import Path

root = Path('/srv/opentallas-scratch2/claude/codex-serdes-loaded-1131')
while True:
    log_path = root / 'otrun_crit.log'
    log = log_path.read_text(errors='replace') if log_path.exists() else ''
    if 'RAN on' not in log and 'NOT RUN' not in log:
        time.sleep(30)
        continue
    path = root / 'events.json'
    event = json.loads(path.read_text()) if path.exists() else {}
    controls = event.get('controls', {})
    base = event.get('encoder_cons_reset_base', {})
    checks = {
        'run_exit_zero': 'exit 0' in log and 'RAN on' in log,
        'native_diagnostic_completed': event.get('verdict') == 'NATIVE_GUARD_DIAGNOSTIC_COMPLETE_ONLY',
        'original_baseline_points': event.get('baseline_points') == 59356,
        'expected_final_obligations': event.get('final_points') == 59367,
        'all_baseline_names_present': event.get('missing_baseline_points') == [],
        'original_tail_pairs': len(event.get('baseline_tail_retained', [])) == 3,
        'all_loaded_candidates': len(event.get('loaded_retained', [])) == 10,
        'joint_profile_no_drops': event.get('joint', {}).get('dropped') == [],
        'joint_statuses_all_proved': bool(event.get('joint', {}).get('status')) and all(
            value == 'proved' for value in event.get('joint', {}).get('status', {}).values()),
        'cons_native_reset_base': base.get('outside_allowed') == [] and
            len(base.get('native_values', {})) == 5 and
            all(value == 0 for value in base.get('native_values', {}).values()),
        'full_comparison_off': event.get('full_equivalence') == 'NOT_RUN',
    }
    for family in ('bm_tail_high', 'encoder_header'):
        control = controls.get(family, {})
        refusal = control.get('reset_true_guard', {})
        checks[family + '_reset_live_refused'] = (
            refusal.get('applied') == 0 and len(refusal.get('loaded_refused', [])) == 1)
        wrong = control.get('wrong_constant_status', {})
        checks[family + '_wrong_value_differs'] = (
            len(wrong) == 1 and next(iter(wrong.values())) == 'differs')
    receipt = {
        'verdict': 'PASS_GUARD_ONLY' if all(checks.values()) else 'HELD',
        'checks': checks,
        'native_error': event.get('error'),
        'run_tail': log[-1200:],
        'full_equivalence': 'NOT_RUN',
        'scope': 'Native guard canary only. No source adoption, canonical comparison, route or signoff credit.',
    }
    (root / 'guard_receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps(receipt), flush=True)
    break
