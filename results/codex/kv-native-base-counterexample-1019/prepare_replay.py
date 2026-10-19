import hashlib
import json
import pathlib
import re
import shutil

p = pathlib.Path(__file__).resolve().parent
original = pathlib.Path('/srv/opentallas-scratch/claude/kv-native-joint-proof-1019/ktree')
destination = pathlib.Path('/srv/opentallas-scratch/claude/kv-native-base-counterexample-1019')
destination.mkdir(exist_ok=True)
raw = (p / 'joint_base_cex.json').read_text()
normalized = re.sub(r'"name": "([^"\n]*)"', lambda m: '"name": ' + json.dumps(m[1]), raw)
j = json.loads(normalized)
signals = json.loads((p / 'all_decoded_signals.json').read_text())
initial = {}
for s in j['signal']:
    c = s['wave'][0]
    if c in '01':
        initial[s['name']] = c
    elif c == '=':
        initial[s['name']] = s['data'][0]
    else:
        assert c in '4xz'
constraints = []
for name, value in initial.items():
    if all(c in '01' for c in value):
        constraints += ['-set-init', name, str(len(value)) + "'b" + value]
    else:
        for i, bit in enumerate(value[::-1]):
            if bit in '01':
                constraints += ['-set-init', name + '[%d]' % i, "1'b" + bit]
inputs = ['clk', 'rst_n', 'kp_in', 'kpv_in', 'gf_in']
for name in inputs:
    for i, value in enumerate(signals[name]):
        assert value is not None and set(value) <= set('01')
        constraints += ['-set-at', str(i + 1), name, str(len(value)) + "'b" + value]
before = (original / 'joint_base.ys').read_text()
formula = before.splitlines()[-1]
assert formula.startswith('sat -seq 10 -prove-asserts -prove-skip 6 ')
after = before.replace('equiv_miter -assert miter', 'equiv_miter -assert -cmp -trigger miter')
assert after != before
after = after.replace('-dump_json joint_base_cex.json -verify',
                      '-dump_json replay_cex.json ' + ' '.join(constraints) + ' -verify')
(destination / 'replay.ys').write_text(after)
files = {}
for name in ['cells.v', 'gate.v', 'gold1.il']:
    shutil.copy2(original / name, destination / name)
    files[name] = hashlib.sha256((destination / name).read_bytes()).hexdigest()
manifest = {
    'authorization': 'ROOT diagnostic only: one retained counterexample replay; observability only; no qualification',
    'before_script_sha256': hashlib.sha256(before.encode()).hexdigest(),
    'after_script_sha256': hashlib.sha256(after.encode()).hexdigest(),
    'dut_gold_cell_model_sha256_before_and_after_identical': files,
    'original_sat_formula': formula,
    'formula_delta': 'Only concretization to retained CEX; same seq10, asserts, skip6, six reset-low assumptions. Added cmp/trigger outputs only.',
    'initial_signals_with_specified_bits': len(initial),
    'initial_known_bits_pinned': sum(sum(c in '01' for c in v) for v in initial.values()),
    'inputs': inputs,
    'input_samples_pinned': 50,
    'unspecified_x_or_blank': 'Preserved unspecified, never coerced to zero',
    'source_cex_sha256': hashlib.sha256(raw.encode()).hexdigest(),
    'reservation_GB': 32,
    'reservation_basis': 'Original same base peaked 28440788 KiB; no resource expansion',
}
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copy2(p / 'joint_base_cex.json', destination / 'original_cex.json')
(destination / 'name_only_normalized_cex.json').write_text(normalized)
print(json.dumps(manifest, indent=2))
