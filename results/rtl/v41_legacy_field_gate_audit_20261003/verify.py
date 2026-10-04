#!/usr/bin/env python3
"""Offline verification of preserved legacy frontend FAIL; never launches tools."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def classify(receipt, trace, scope):
    if receipt['returncode'] != 1 or not receipt['source_unmodified_before'] or not receipt['source_unmodified_after']:
        raise ValueError('not a stable failed source-gate invocation')
    if '%Error-MODMISSING:' not in trace or "module: 'ot_hdc_cg'" not in trace:
        raise ValueError('missing exact frontend failure')
    if receipt['functional_comparison_reached'] or scope['functional_comparison_reached']:
        raise ValueError('frontend FAIL cannot claim functional comparison')
    if scope['selected_runtime_regression_established'] or scope['current_PHW10_connected_validation']:
        raise ValueError('legacy failure cannot establish selected runtime/current PHW10 result')
    if scope['runtime_rerun_performed']:
        raise ValueError('runtime was not independently rerun in this audit')
    return 'FAIL_LEGACY_FRONTEND_SOURCE_CLOSURE'

def verify():
    manifest = json.loads((BASE/'manifest.json').read_text())
    for name, expected in manifest.items():
        if sha(BASE/name) != expected:
            raise ValueError('artifact hash mismatch: '+name)
    receipt=json.loads((BASE/'receipt.json').read_text())
    scope=json.loads((BASE/'classification.json').read_text())
    trace=(BASE/'verilate_flat.log').read_text()
    assert classify(receipt,trace,scope)==scope['status']
    sources=json.loads((BASE/'source_manifest.json').read_text())
    for name, expected in sources.items():
        assert sha(BASE/'source'/name)==expected
    historical=json.loads((BASE/'historical_comparison.json').read_text())
    assert historical['all_match_e9bd212f9'] and len(historical['current_mismatches'])==6
    assert sha(BASE/'historical_PASS.json')==historical['historical_record_sha256']
    archived=json.loads((BASE/'historical_PASS.json').read_text())
    assert archived['params']['nbf']==8 and receipt['parameters']['nbf']==4
    assert '"ot_hdc_cg"' not in (BASE/'source/tools/v41_field_rt_gate.py').read_text().split('COMMON =',1)[1].split('VIA_ROM =',1)[0]
    assert '"ot_hdc_cg"' in (BASE/'source/tools/w17_runtime_v41_field_rt_gate.py').read_text().split('COMMON =',1)[1].split('VIA_ROM =',1)[0]
    rejected=0
    mutations=[({'returncode':0}, {},trace),({'source_unmodified_after':False},{},trace),({'functional_comparison_reached':True},{},trace),({}, {'selected_runtime_regression_established':True},trace),({}, {'current_PHW10_connected_validation':True},trace),({}, {'runtime_rerun_performed':True},trace),({}, {},trace.replace('ot_hdc_cg','wrong_module'))]
    for rm,sm,tm in mutations:
        try: classify(receipt|rm,tm,scope|sm)
        except ValueError: rejected+=1
        else: raise AssertionError('invalid evidence accepted')
    return {'status':'ARCHIVE_VERIFIED','artifacts':len(manifest),'sources':len(sources),'negative_controls_rejected':rejected,'gate_verdict':scope['status'],'selected_runtime_regression_established':False}

if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
