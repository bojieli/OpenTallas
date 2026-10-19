#!/usr/bin/env python3
"""Build four independent ISA token golds from a verified real common prefix.

Run on the fleet after the canonical 36-layer P8191 golden finishes. This is
oracle fixture generation, not an RTL or general multi-user qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'results/rtl/qwen_hbmacc_p8191_20261004/gold_tp4/oracle.json'
OFFSETS = [0, 16, 32, 168]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def run(cmd, env=None):
    subprocess.run([str(x) for x in cmd], check=True, env=env)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fx', type=Path, required=True)
    ap.add_argument('--canonical-gold', type=Path, required=True)
    ap.add_argument('--oracle-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--threads', type=int, default=32)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    import numpy as np
    # A failed verification is evidence too. Never overwrite its output when a
    # later caller retries; give every attempt a new directory.
    a.out.mkdir(parents=True, exist_ok=False)
    target = a.out / 'MANIFEST.json'
    ref = json.loads(REF.read_text())
    # Fail before generating another user if the original full gold is absent
    # or changed. Verification includes all layer/head/history digests.
    run([a.python, ROOT / 'tools/exactness/fixtures.py', 'verify', '--gold',
         a.canonical_gold, '--ref', REF, '--out', a.out / 'canonical_verify.json'])
    oracle = a.oracle_root / 'tools/qwen_hbmacc_position_oracle_gpu.py'
    for rel, expected in ref['oracle_source_sha256'].items():
        if sha(a.oracle_root / rel) != expected:
            raise SystemExit(f'oracle source mismatch: {rel}')
    tokens_path = a.fx / 'inputs/prompt_tokens_8192.txt'
    embedding = a.fx / 'inputs/prompt_embedding.npz'
    prep = a.fx / 'prep/tp4'
    for path, expected in ((tokens_path, ref['tokens_sha256']),
                           (embedding, ref['embedding_npz_sha256']),
                           (prep / 'prep.json', ref['prep_sha256'])):
        if sha(path) != expected:
            raise SystemExit(f'canonical input mismatch: {path}')
    tokens = [int(t) for t in tokens_path.read_text().split()]
    if len(tokens) != 8192:
        raise SystemExit('expected exactly 8192 canonical prompt tokens')
    available = set(int(t) for t in np.load(embedding)['tokens'])
    selected = [tokens[-1]]
    for token in reversed(tokens[:-1]):
        if token in available and token not in selected:
            selected.append(token)
        if len(selected) == 4:
            break
    if len(selected) != 4:
        raise SystemExit('need four distinct already-pinned embedding tokens')
    history = a.out / 'canonical_kv_pre'
    run([a.python, ROOT / 'tools/exactness/fixtures.py', 'history', '--gold',
         a.canonical_gold / 'P8191', '--out', history])
    history_record = json.loads((history / 'MANIFEST.json').read_text())
    history_hashes = {key: value['bin_sha256']
                      for key, value in history_record['files'].items()}
    users = []
    for user, token in enumerate(selected):
        out = a.canonical_gold if user == 0 else a.out / f'user{user}/gold'
        inp = tokens_path if user == 0 else a.out / f'user{user}/tokens.txt'
        if user:
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text('\n'.join(map(str, tokens[:-1] + [token])) + '\n')
        users.append(dict(user=user, final_token=token, position=8191,
                          admission_offset=OFFSETS[user], tokens=str(inp),
                          tokens_sha256=sha(inp), gold=str(out),
                          state='CANONICAL_VERIFIED' if user == 0 else 'NOT_RUN'))
    manifest = dict(schema='opentallas.qwen.shared-prefix-gold4.v1',
                    claim='diagnostic shared-real-prefix independent-request ISA golds; no RTL verdict',
                    reference_sha256=sha(REF), generator_sha256=sha(__file__),
                    common_prefix_tokens=8191,
                    common_prefix_sha256=hashlib.sha256(
                        ('\n'.join(map(str, tokens[:-1])) + '\n').encode()).hexdigest(),
                    checkpoint_prep_sha256=ref['prep_sha256'],
                    embedding_sha256=ref['embedding_npz_sha256'],
                    arithmetic='released checkpoint TP4, original ISA rounding/reduction order',
                    ownership='each new oracle process owns all layer K/V stores; only immutable pre-divergence history shared',
                    admission_scope='isolated F16 witness receipt 26b514ed1; production phase/retirement still open',
                    retirement='real per-user ME/XPF final-read join required; numerical fixture is not retirement proof',
                    users=users, verdict='PREPARED_NOT_NUMERICAL_PASS')
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    if not a.run:
        return
    env = dict(os.environ, QWEN_O4_TP='4', QWEN_O4_GROUPS='6144',
               HDC_SU_WIDTH='1024', HDC_KV_FMT='fp8', OMP_NUM_THREADS=str(a.threads))
    for user in users[1:]:
        out = Path(user['gold'])
        out.mkdir(parents=True, exist_ok=True)
        cmd = [a.python, oracle, '--run', '--device', 'cpu', '--prep-dir', prep,
               '--layers', '36', '--head', '--tokens', user['tokens'],
               '--positions', '8191', '--embedding-npz', embedding,
               '--kv-history', history, '--out', out]
        user['command'] = list(map(str, cmd))
        user['state'] = 'RUNNING'
        target.write_text(json.dumps(manifest, indent=2) + '\n')
        run(cmd, env)
        rec = json.loads((out / 'oracle.json').read_text())
        if (rec['layers'], rec['tp'], rec['groups'], rec['positions']) != (36, 4, 6144, [8191]):
            raise SystemExit('oracle shape mismatch')
        if rec['tokens_sha256'] != user['tokens_sha256']:
            raise SystemExit('oracle user token identity mismatch')
        if rec['oracle_source_sha256'] != ref['oracle_source_sha256']:
            raise SystemExit('oracle arithmetic provenance mismatch')
        if rec['kv_history_sha256'] != history_hashes:
            raise SystemExit('oracle history identity mismatch')
        if not rec['primitive_selftest'] or not all(rec['primitive_selftest'].values()):
            raise SystemExit('oracle primitive arithmetic self-test failed')
        position = rec['per_position']['8191']
        if position['token'] != user['final_token']:
            raise SystemExit('oracle final token mismatch')
        for key in ('layer_x_sha256', 'kv_pre_sha256', 'kv_at_P_sha256'):
            if len(position[key]) != 144:
                raise SystemExit(f'incomplete 36-layer TP4 fixture: {key}')
        if position['kv_pre_sha256'] != ref['per_position']['8191']['kv_pre_sha256']:
            raise SystemExit('pre-divergence history differs from canonical prefix')
        if 'head' not in position:
            raise SystemExit('missing head fixture')
        user.update(state='ISA_GOLD_GENERATED', oracle_sha256=sha(out / 'oracle.json'))
        target.write_text(json.dumps(manifest, indent=2) + '\n')
    manifest['verdict'] = 'FOUR_SHARED_PREFIX_ISA_GOLDS_GENERATED_NOT_RTL'
    target.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
