#!/usr/bin/env python3
"""Pure refusal checks. Synthetic inputs never reach image generation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    script = Path(__file__).with_name('compile_rope_pair.py')
    fixture = {key: 'TEST_ONLY_NEVER_GENERATED' for key in (
        'compute_source', 'kv_source', 'compute_gen_sha256', 'kv_gen_sha256',
        'head_producer', 'held_descriptor', 'user0_host_match_source',
        'tt_to_native_path', 'native_to_sysface_path', 'die_stages',
        'selected_slice_source', 'selected_slice_timing_receipt')}
    fixture.update({key: 0 for key in (
        'tt_to_native_edges', 'native_to_sysface_edges', 'head_prepare_edges',
        'host_stages', 'kv_codec', 'emb_window', 'layer_period_min',
        'attn_tx_shift', 'status_delay', 'kv_descriptor_to_header_edges')})
    fixture['source_intrinsic_edges'] = dict(
        ct_lm_sample=4, native_prepare_descriptor=3, face_held_bank=1)
    fixture['tt_source'] = dict(producer_instance='u_gi')
    cases = []
    for status in (None, 'SOURCE_ONLY_NOT_SELECTED', 'UNKNOWN'):
        row = json.loads(json.dumps(fixture))
        if status is not None:
            row['tt_source']['status'] = status
        cases.append((f'status_{status}', row,
                      'selected TT source-local edges are missing or unqualified'))
    local = json.loads(json.dumps(fixture))
    local['tt_source'].update(status='QUALIFIED_SOURCE_LOCAL_EDGES',
        selection_status='NOT_SELECTED_NO_ACTUAL_GEN', master='TEST_ONLY_MASTER',
        calendar_sample_edges=1, output_offset_edges=6, producer_offset_edges=3,
        source_to_output_edges=3, receipt_sha256='f' * 64,
        rtl_sha256='f' * 64, lp_record_sha256='f' * 64)
    local['head_prepare_edges'] = 8
    for key in ('compute_gen_sha256', 'kv_gen_sha256', 'tt_to_native_edges',
                'native_to_sysface_edges', 'kv_descriptor_to_header_edges'):
        row = json.loads(json.dumps(local))
        row[key] = None
        prefix = 'unknown required source/GEN fact:' if key.endswith('sha256') else 'unknown required actual age/programme input:'
        cases.append((f'qualified_local_missing_{key}', row, f'{prefix} {key}'))
    row = json.loads(json.dumps(local))
    row['tt_source']['master'] = None
    cases.append(('qualified_local_missing_selected_master', row,
                  'unknown actual selected TT source identity: master'))
    results = []
    for label, row, expected in cases:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            ages = root / 'synthetic.json'
            ages.write_text(json.dumps(row))
            out = root / 'must_not_exist'
            run = subprocess.run([
                sys.executable, str(script), '--source-dir', str(root),
                '--ages', str(ages), '--token-path', str(root / 'absent_token'),
                '--link-handoff', str(root / 'absent_handoff'), '--out', str(out)
            ], capture_output=True, text=True)
            assert run.returncode != 0 and not out.exists(), run
            assert expected in run.stderr, run
            results.append(dict(case=label, refused=True, output_created=False,
                                diagnostic=expected))
    print(json.dumps(dict(verdict='PASS', scope='pure malformed-input refusals; no GEN/image/simulation', cases=results), indent=1))


if __name__ == '__main__':
    main()
