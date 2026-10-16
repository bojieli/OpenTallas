#!/usr/bin/env python3
"""Finite actual-source endpoint component gate; golden values are compare-only.

Run this under ot-run. A positive 512-word exact/timeline result is required
before any injected-fault or independently shifted-calendar control counts.
This does not establish full die/layer/token or physical qualification.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from compile_native_endpoint import compile_programme


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    ap.add_argument('vectors', type=Path)
    ap.add_argument('out', type=Path)
    a = ap.parse_args()
    binary, vec, out = a.binary.resolve(), a.vectors.resolve(), a.out.resolve()
    meta = json.loads((vec/'meta.json').read_text())
    if [meta.get(k) for k in ('q_heads', 'kv_heads', 'hd', 'groups')] != [4, 1, 128, 3072]:
        raise ValueError('requires actual TP8 four-head/one-KV-head, 3072-group vectors')
    if meta.get('attn_splits') != [128, 256]:
        raise ValueError('wrong arithmetic split for actual TP8 P.V hardware')
    for name, expected in meta['hashes'].items():
        if sha(vec/name) != expected:
            raise ValueError(f'vector hash mismatch: {name}')
    programme = compile_programme(17, 19, meta['ctx']-1, 6, 4)
    out.mkdir(parents=True, exist_ok=True)
    (out/'programme.json').write_text(json.dumps(programme, indent=2)+'\n')
    records = []
    for mode in ('steady', 'q_drop', 'k_drop', 'k_late', 'v_late', 'v_swap', 'tx_first_late'):
        first = programme['compiled_tx_first'] + (mode == 'tx_first_late')
        cmd = [str(binary), f'+VEC={vec}', f'+CTX={meta["ctx"]}',
               f'+CAL={programme["calendar_hex"]}', f'+TX_FIRST={first}',
               '+MODE='+('steady' if mode == 'tx_first_late' else mode)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        log = r.stdout+r.stderr
        (out/(mode+'.log')).write_text(log)
        terminal = [line for line in log.splitlines() if line.startswith('ENDPOINT ')]
        passed = bool(terminal) and (r.returncode != 0 if mode == 'tx_first_late' else r.returncode == 0)
        records.append(dict(mode=mode, command=cmd, exit_code=r.returncode, passed=passed,
                            terminal=terminal, log_sha256=sha(out/(mode+'.log'))))
        if not passed:
            break  # fault controls cannot qualify a nonfunctional positive
    receipt = dict(scope='ACTUAL_SOURCE_ENDPOINT_COMPONENT_ONLY', binary_sha256=sha(binary),
                   vector_meta=meta, programme=programme, records=records,
                   passed=len(records)==7 and all(r['passed'] for r in records),
                   native_full_layer=False, native_full_token=False, physical_qualified=False)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(passed=receipt['passed'], records=records)))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
