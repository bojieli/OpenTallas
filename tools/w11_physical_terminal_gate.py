#!/usr/bin/env python3
"""Bind preserved W11 terminal failures to the composed graph, without timing credit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CKV = 'results/physical_abi3/asap7/chip/w11_ckv_merge_finish_20261001'
CTL = 'results/physical_abi3/asap7/chip/w11_attn_eng_ctl/endpoint_e3e9e9b8_terminal'
SERVICE = 'results/quality/w16_w19_composed_schedule_20261001_r2/service_readiness.json'
FEASIBILITY = 'results/quality/w16_w11_ckv_feasibility_20261001/feasibility.json'
OUT = ROOT / 'results/uarch/w11_physical_terminal_gate_20261001.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(root=ROOT):
    pins = {}

    def read(path):
        raw = (root / path).read_bytes()
        pins[path] = sha(raw)
        return raw

    measurement = json.loads(read(CKV + '/measurement.json'))
    for item in measurement['archives'].values():
        raw = read(CKV + '/' + item['artifact'])
        if 'gzip_sha256' in item:
            assert sha(raw) == item['gzip_sha256'], 'CKV compressed archive drift'
            assert sha(gzip.decompress(raw)) == item['raw_sha256'], 'CKV raw archive drift'
        else:
            assert sha(raw) == item['sha256'], 'CKV configuration drift'
    finish = json.loads(gzip.decompress(read(CKV + '/6_report.json.gz')))
    fields = {'setup_worst_slack_ps': 'finish__timing__setup__ws',
              'hold_worst_slack_ps': 'finish__timing__hold__ws',
              'setup_violations': 'finish__timing__drv__setup_violation_count',
              'hold_violations': 'finish__timing__drv__hold_violation_count',
              'slew_violations': 'finish__timing__drv__max_slew',
              'area_um2': 'finish__design__instance__area'}
    for name, key in fields.items():
        assert measurement['metrics'][name] == finish[key], 'CKV finish metric drift: ' + name
    route = json.loads(gzip.decompress(read(CKV + '/5_2_route.json.gz')))
    assert measurement['metrics']['route_drc'] == route['detailedroute__route__drc_errors'], 'CKV DRC drift'
    assert measurement['verdict'] == 'MEASURED_FINISH_NOT_CLOSED'
    assert measurement['metrics']['setup_worst_slack_ps'] < 0
    assert measurement['metrics']['hold_worst_slack_ps'] < 0
    assert measurement['adopt'] is False
    feasibility = json.loads(read(FEASIBILITY))
    assert feasibility['physical_admission'] is False
    assert feasibility['engine_RTL_build_ready'] is False and feasibility['adopt'] is False
    assert feasibility['preserved_failure']['metrics'] == measurement['metrics']
    current_source_matches = {
        path: sha(read(path)) == expected
        for path, expected in measurement['source_binding'][0]['source_sha256'].items()
    }

    collection = json.loads(read(CTL + '/collection.json'))
    for item in collection['inventory']:
        raw = read(CTL + '/' + item['archived'])
        assert sha(raw) == item['archived_sha256'], 'controller archive drift'
        if item['archived'].endswith('.gz'):
            assert sha(gzip.decompress(raw)) == item['raw_sha256'], 'controller raw archive drift'
    physical = json.loads(read(CTL + '/physical.json'))
    exit_record = json.loads(read(CTL + '/exit.json'))
    assert physical['status'] == 'error' and physical['flow_completed'] is False
    assert exit_record['returncode'] == 1
    log = gzip.decompress(read(CTL + '/logs/5_1_grt.log.gz')).decode()
    assert '[ERROR DRT-0305] Net one_ of signal type POWER' in log
    assert 'read_liberty -corner WC' in log and '_SS_' in log
    assert 'read_liberty -corner BC' in log and '_FF_' in log
    service = json.loads(read(SERVICE))
    pins['tools/w11_physical_terminal_gate.py'] = sha(Path(__file__).read_bytes())
    return dict(schema='opentallas.w11.composed-physical-terminal-gate.v1',
                graph_sha256=service['graph_sha256'], source_sha256=pins,
                applies_to=['DeepSeek-V4.1 ROM', 'DeepSeek-V4.1 HBM'],
                status='BLOCKED_W11_PHYSICAL_TERMINALS',
                CKV=dict(status=measurement['verdict'], metrics=measurement['metrics'],
                         measured_configuration=measurement['measured_configuration'],
                         original_source_binding=measurement['source_binding'],
                         original_source_Git_replay='NOT_ESTABLISHED_BY_THIS_ARCHIVE',
                         current_RTL_matches_failed_source=current_source_matches,
                         conditional_ROM_staging_baseline=feasibility['required_baseline_candidate'],
                         HBM_transfer_qualified=False,
                         independent_FF_hold_PASS=False, required_hub_layers=['M2', 'M5'],
                         physical_admission=False, connected_rate_credit=False),
                controller=dict(status='TERMINAL_FLOW_ERROR_DRT0305', returncode=1,
                                completed_at=physical['completed_at'],
                                original_source_commit=collection['source_commit'],
                                actual_constraints=collection['constraints'],
                                wrapper_corner_label=physical['corner']['name'],
                                route_corner_verdict=None, flow_completed=False,
                                physical_admission=False, connected_rate_credit=False),
                full_token_cycles=None, full_token_rate=None,
                maximum_qualified_clock_hz=None, physical_admission=False,
                hardware_adopted=False, tuning=False, restart=False,
                old_composed_service_changed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.check:
        assert json.loads(OUT.read_text()) == result, 'stale W11 physical terminal gate'
    else:
        with OUT.open('x') as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write('\n')
    print('BLOCKED CKV timing/hub scope and controller pin-access error; no physical credit')
