#!/usr/bin/env python3
"""Refuse actual canonical/reference receipts; no GEN, image, or simulation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    script = Path(__file__).with_name('compile_rope_pair.py')
    data = Path(__file__).resolve().parents[2] / 'results/rtl/tokfunc2_qw_1021/tt_clock_guard'
    canonical = json.loads((data / 'canonical_input.json').read_text())
    old_bytes = (data / 'historical_local_input.json').read_bytes()
    old_hash = hashlib.sha256(old_bytes).hexdigest()
    assert old_hash == canonical['supersedes_for_actual_availability']['sha256']
    old = json.loads(old_bytes)
    old['receipt_sha256'] = old_hash
    bogus = json.loads(json.dumps(old))
    bogus.update(actual_availability_edges=4,
                 actual_GEN_clock_relation={'unverified': 'not an exporter law'})
    cases = [
        ('canonical_reference_only', canonical,
         'TT common-clock reference is not actual source availability; selected GEN clock law required'),
        ('historical_qualified_four_fallback', old,
         'actual TT availability and selected GEN clock-law binding required; no historical four-edge fallback'),
        ('unrecognized_clock_law', bogus,
         'unrecognized actual TT GEN clock-law schema; genuine selected exporter packet required')]
    results = []
    for label, tt, expected in cases:
        # Synthetic surrounding fields deliberately reach the intended guard.
        # They are never treated as actual selected GEN evidence or generated.
        row = {key: 'TEST_ONLY_NEVER_GENERATED' for key in (
            'compute_source', 'kv_source', 'head_producer', 'held_descriptor',
            'user0_host_match_source', 'tt_to_native_path', 'native_to_sysface_path',
            'die_stages', 'selected_slice_source', 'selected_slice_timing_receipt')}
        row.update(compute_gen_sha256='f' * 64, kv_gen_sha256='e' * 64,
                   tt_to_native_edges=0, native_to_sysface_edges=0,
                   head_prepare_edges=8, host_stages=0, kv_codec=1,
                   emb_window=1627, layer_period_min=0, attn_tx_shift=0,
                   status_delay=0, kv_descriptor_to_header_edges=0,
                   source_intrinsic_edges=dict(ct_lm_sample=4,
                       native_prepare_descriptor=3, face_held_bank=1), tt_source=tt)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            ages = root / 'synthetic_envelope.json'
            ages.write_text(json.dumps(row))
            out = root / 'must_not_exist'
            run = subprocess.run([sys.executable, str(script), '--source-dir', str(root),
                '--ages', str(ages), '--token-path', str(root / 'absent'),
                '--link-handoff', str(root / 'absent'), '--out', str(out)],
                capture_output=True, text=True)
            assert run.returncode != 0 and expected in run.stderr and not out.exists(), run
            results.append(dict(case=label, refused=True, output_created=False,
                                diagnostic=expected))
    assert (data / 'historical_local_input.json').read_bytes() == old_bytes
    print(json.dumps(dict(verdict='PASS', scope='pure input refusal; no GEN/image/simulation',
                         historical_input_sha256=old_hash, cases=results), indent=1))


if __name__ == '__main__':
    main()
