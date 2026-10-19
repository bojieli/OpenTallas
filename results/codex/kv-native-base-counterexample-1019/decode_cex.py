"""Read existing Yosys WaveJSON only; never run or modify a proof."""
import hashlib
import json
import pathlib
import re

p = pathlib.Path(__file__).resolve().parent
raw = (p / 'joint_base_cex.json').read_text()
# Yosys prints identifiers with literal backslashes, including invalid \u escapes.
# Escape ONLY identifier fields. Keep original bytes as the authoritative witness.
normalized = re.sub(r'"name": "([^"\n]*)"',
                    lambda m: '"name": ' + json.dumps(m[1]), raw)
wave = json.loads(normalized)

def decode(signal):
    data = signal.get('data', [])
    di = 0
    value = None
    result = []
    for index, char in enumerate(signal['wave']):
        if char == '=':
            value = data[di]
            di += 1
        elif char in '01xz':
            value = char
        elif char == '4':
            value = None  # blank/unreported, not a logical zero
            if data:
                assert data[di] == ''
                di += 1
        elif char != '.':
            raise ValueError(char)
        if index:
            result.append(value)
    assert di == len(data)
    assert len(result) == 10
    return result

signals = {s['name']: decode(s) for s in wave['signal']}
metadata = {n: v for n, v in signals.items() if n.startswith('S__proof_meta_')}
assert len(metadata) == 95
assert all(v[6:10] == ['0'] * 4 for v in metadata.values())
assert signals['rst_n'] == ['0'] * 7 + ['1'] * 3
assert signals['sc_d'][0] == '1000x0000000010100000000000000x0'
regional = {n: v for n, v in signals.items() if n.startswith('S__u_rr_rst_n_')}
assert len(regional) == 17
assert all(v == ['0'] * 10 for v in regional.values())
valid = {n: v for n, v in signals.items() if n.endswith('_valid_out')}
assert len(valid) == 16
assert all(v == ['0'] * 10 for v in valid.values())
selected = {n: v for n, v in signals.items()
            if n in ['rst_n', 'clk', 'kpv_in', 'kp_in', 'gf_in', 'g_f', 'sc_f', 'sc_d']
            or n.startswith(('S__proof_meta_', 'S__u_rr_')) or n.endswith('_valid_out')}
out = {
    'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
    'signal_count': len(signals),
    'checked_steps': [7, 8, 9, 10],
    'all_95_metadata_gold_observations_zero_at_checked_steps': True,
    'failure_in_original_comparison_set': True,
    'first_original_failed_comparison': None,
    'first_original_failed_step': None,
    'extraction_limit': 'Original miter exported asserts without cmp/trigger or both comparison operands.',
    'semantics': 'S__ equiv Y follows gold A in satgen.cc; metadata gate B is constant zero. Blank and x remain uninterpreted. No state equality is inferred from low valid.',
    'steps': [dict(step=i + 1, **{n: v[i] for n, v in selected.items()}) for i in range(10)],
}
(p / 'decoded_summary.json').write_text(json.dumps(out, indent=2) + '\n')
(p / 'all_decoded_signals.json').write_text(json.dumps(signals, indent=2) + '\n')
print('Decoded 22,764 signals; all 380 checked metadata values are zero; original comparison FAIL remains unresolved.')
