import datetime
import hashlib
import json
import re
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def words(p):
    return [x.strip().lower() for x in Path(p).read_text().splitlines() if x.strip()]

root = Path('/home/ubuntu/w12')
r = json.loads((root / 'rt64_token.json').read_text())
checks = {}
for name, recorded in r['layer_x_checks'].items():
    layer, die, _ = name.split('_')
    got = root / 'rt64' / (name + '.hex')
    want = root / 'oracle6144' / (f'L{int(layer[1:]):02d}_{die}_x.hex')
    a, b = words(got), words(want)
    mismatch = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
    checks[name] = {'words': len(a), 'mismatches': mismatch,
                    'actual_sha256': sha(got), 'expected_sha256': sha(want)}
    assert checks[name] == recorded, (name, checks[name], recorded)
assert sha(root / 'rt64/qwen_rom_rt') == r['binary_sha256']
assert sha(root / 'rt64/gen/ot_qwen_rom_core.sv') == r['generated_core_sha256']
assert sha(root / 'oracle6144/oracle.json') == r['oracle_sha256']
assert r['status'] == 'pass' and r['source_stable']
assert all(c['mismatches'] == 0 and c['words'] == 4096 for c in checks.values())
assert len(checks) == 72
assert r['stages_run'] == [f'L{i}' for i in range(36)] + ['head']
assert r['rtl_token'] == r['oracle_token'] == 50994
assert r['rtl_logit_bits'] == r['oracle_logit_bits'] == '419c0f7e'
log = (root / 'rt64/token.log').read_text()
assert len(re.findall(r'^STAGE .* done ', log, re.M)) == 37
assert all(sum(int(x) for x in m) == 0 for m in re.findall(r'seq_fault=(\d+) core_fault=(\d+) coll_fault=(\d+)', log))
assert f"cycles={r['total_cycles']} edges={r['total_cycles']}" in log.splitlines()[-1]
partial = {}
live_log = (root / 'rt_tp4d/token.log').read_text()
completed = re.findall(r'^STAGE (L\d+) done .*', live_log, re.M)
for layer in completed:
    for die in range(4):
        got = root / 'rt_tp4d' / f'{layer}_die{die}_x.hex'
        want = root / 'oracle_tp4' / f'L{int(layer[1:]):02d}_die{die}_x.hex'
        a, b = words(got), words(want)
        mismatch = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
        partial[f'{layer}_die{die}'] = {'words': len(a), 'mismatches': mismatch,
                                       'actual_sha256': sha(got), 'expected_sha256': sha(want)}
print(json.dumps({'collected_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'host': 'ot-pve1', 'tp2_terminal_record_sha256': sha(root / 'rt64_token.json'),
    'tp2_token_log_sha256': sha(root / 'rt64/token.log'),
    'tp2_binary_sha256': r['binary_sha256'], 'tp2_generated_core_sha256': r['generated_core_sha256'],
    'tp2_layer_checks': checks, 'tp2_verified': True,
    'tp4_completed_layers': completed, 'tp4_checkpoint_checks': partial,
    'tp4_claim_boundary': 'Partial checkpoint comparison only; token and timing gates remain pending.'}, indent=2, sort_keys=True))
