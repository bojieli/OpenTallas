#!/usr/bin/env python3
"""Replay the native profile; every hypothesis and compare point is re-proved.
Run inside the pinned ORFS image with tools/die_plan on PYTHONPATH:
  python3 replay.py ACTUAL_AIG_INPUT_DIR OUTPUT_DIR
"""
import collections
import hashlib
import json
from pathlib import Path
import sys
import lec

src, out = map(Path, sys.argv[1:3]); out.mkdir(parents=True, exist_ok=True)
packet = Path(__file__).parent
expected = json.loads((packet / 'summary.json').read_text())['actual_inputs']
for name, digest in expected.items():
    if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError('actual input mismatch: ' + name)
L = lec.Lec(lec.read_aig(src/'gold.aig'), lec.read_map(src/'gold.map'),
            lec.read_aig(src/'gate.aig'), lec.read_map(src/'gate.map'))
log = []
lec.normalize_gold_elements(L, lec.slang_elements(src/'gold.aliases.json'), log)
for fn in (lec.json_alias_keys, lec.slang_element_keys, lec.alias_arrays):
    fn(L, log, work=src)
for fn in (lec.relayout, lec.renamed, lec.replica_proposals, lec.merged_proposals,
           lec.register_alias_proposals, lec.fsm_proposals):
    fn(L, log)
L.hyp.clear()
for sd, key, hint in json.loads((packet/'native_profile.json').read_text()):
    L.hyp[sd, key] = tuple(hint)
for (sd, key), hint in L.hyp.items():
    if hint[0] == 'loaded' and lec.loaded_base(L, hint[2]) is not None:
        raise RuntimeError('loaded guard not reset-false: ' + key)
for tag, compare in [('joint', False), ('compare', True)]:
    m, _ = L.build(with_compare=compare, with_hyp=True)
    status = lec.prove(m, out, 1000, log, tag=tag, single_cap=200)
    (out/(tag+'.json')).write_text(json.dumps(status))
    (out/'proof.log').write_text('\n'.join(log))
    print(tag, collections.Counter(status.values()), flush=True)
    if any(value != 'proved' for value in status.values()):
        raise RuntimeError(tag + ' FAIL')
_, missing, constants = lec.kept_registers(L, src/'gold.keep')
if missing or constants:
    raise RuntimeError('kept register failure')
print('EQUIVALENT', flush=True)
