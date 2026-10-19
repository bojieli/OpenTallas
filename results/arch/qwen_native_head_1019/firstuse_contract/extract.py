"""Finite source/inventory extraction only; does not simulate or elaborate RTL."""
import csv
import hashlib
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
holding = OUT.parent / 'holding_model'
model = json.loads((holding / 'model.json').read_text())
exact = json.loads((holding / 'exact_chains.json').read_text())
selected = {c['chain'] for c in model['chains']
            if c['partial_ring_eligible_after_lifetime_proof']}
rows = []
for chain in exact['chains']:
    if chain['index'] not in selected:
        continue
    stages = chain['stages']
    assert len(stages) == 4
    assert all(s['type'] == '$_DFF_P_' and s['clock'] == [2]
               and not s.get('reset') for s in stages)
    # Each first stage is the preserved macro-output capture.
    first = stages[0]['Qnames'][0]
    assert first.startswith('u_h.u_lane.e_tag_m[')
    tail = next((n for n in stages[-1]['Qnames'] if '.s3_tail[' in n), None)
    imm = next((n for n in stages[-1]['Qnames'] if '.s3_imm2[' in n), None)
    ad = next((n for n in stages[-1]['Qnames'] if '.s3_ad[' in n), None)
    endpoint = tail or imm or ad
    assert endpoint
    group = 'tail' if tail else 'imm2' if imm else 'ad'
    rows.append({'chain': chain['index'], 'tag_bit': int(re.search(r'\[(\d+)\]', first)[1]),
                 'group': group, 'capture': first, 'stage1': '|'.join(stages[1]['Qnames']),
                 'stage2': '|'.join(stages[2]['Qnames']), 'stage3': endpoint,
                 'consumer_ports': json.dumps(stages[-1]['Qloads']),
                 'source_attributes': json.dumps([s['attributes'] for s in stages])})
assert len(rows) == 97
counts = {g: sum(r['group'] == g for r in rows) for g in ('tail', 'imm2', 'ad')}
assert counts == {'tail': 62, 'imm2': 32, 'ad': 3}
with (OUT / 'paths.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

ledger = json.loads((OUT / 'parent_ledger_input.json').read_text())
sources = dict(ledger['source_sha256'])
sources.update({p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [
    'rtl/test/qwen_dv/tb_head_control_trim_equiv.sv',
    'tools/qwen_native_head_1019/run_control_trim_equiv.sh',
    'tools/qwen_native_head_1019/control_census.sh',
]})
checks = {}
for name, expected in sources.items():
    path = ROOT / name
    if path.exists():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (name, actual, expected)
        checks[name] = {'sha256': actual, 'verified_present': True}
    else:
        checks[name] = {'sha256': expected, 'verified_present': False,
                        'reason': 'Exact hash retained from parent ledger; not re-read here'}
(OUT / 'source_hashes.json').write_text(json.dumps(checks, indent=2) + '\n')
receipt = {'status': 'SOURCE_CONTRACT_MODEL_ONLY_NO_RTL_OR_JOBS',
           'source': '5cd31ebb8', 'terminal': 'cd660e13e',
           'parent_ledger': '0dd6c84a7', 'holding_model': 'f7659f090',
           'paths': counts, 'captures_retained': 97,
           'data_stages_under_discussion': 291,
           'mixed_reset_FPU_chains_preserved': 24,
           'mixed_reset_FPU_FF_preserved': 94,
           'unused_tail_captures_preserved': 7,
           'unsafe_roots_unresolved': 83, 'rt_loads_unresolved': 1603,
           'local_checks': '97 exact four-stage unreset paths, same clock, endpoint consumers, source hashes',
           'RTL_simulation': False, 'all_output_equivalence': None,
           'actual_parent_native_first_use': None,
           'actual_parent_stopped_clock_epoch': None,
           'native_area_cap_depth': None}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, sort_keys=True))
