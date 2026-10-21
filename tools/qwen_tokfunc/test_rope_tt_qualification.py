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
    results = []
    for status in (None, 'SOURCE_ONLY_NOT_SELECTED', 'UNKNOWN'):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            row = json.loads(json.dumps(fixture))
            if status is not None:
                row['tt_source']['status'] = status
            ages = root / 'synthetic.json'
            ages.write_text(json.dumps(row))
            out = root / 'must_not_exist'
            run = subprocess.run([
                sys.executable, str(script), '--source-dir', str(root),
                '--ages', str(ages), '--token-path', str(root / 'absent_token'),
                '--link-handoff', str(root / 'absent_handoff'), '--out', str(out)
            ], capture_output=True, text=True)
            assert run.returncode != 0 and not out.exists(), run
            assert 'selected TT source-local edges are missing or unqualified' in run.stderr
            results.append(dict(status=status, refused=True, output_created=False))
    print(json.dumps(dict(verdict='PASS', scope='pure malformed-input refusals; no GEN/image/simulation', cases=results), indent=1))


if __name__ == '__main__':
    main()
