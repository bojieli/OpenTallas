#!/usr/bin/env python3
"""TOK-FUNC3-QW stage chain collector: KVROOT/chain/{in,vec,runs} -> KVROOT/chain/result.json.

usage: stage_chain.collect.py CHAIN_DIR [--grade G]
Verdict PASS only when: all 36 layer vectors built with the TP4 attention reproduction exact (od input == attention of the
RTL q/k/v), every hand-off edge bit-exact, every L<n>_u1 and G<i>_u4 run KVATTN_REL PASS with exact results, and the
control CTL_L35_goldflip FAILs.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('chain', type=Path)
ap.add_argument('--grade', default='RTL-functional (source assembly)')
a = ap.parse_args()
C = a.chain.resolve()
FX, P = C / 'in/fx', C / 'in/p8191'
bad, edges = [], {}


def bits(x):
    return np.asarray(x, dtype=np.float32).view(np.uint32)


def read_hex(p):
    return np.array([int(w, 16) for w in p.read_text().split()], dtype=np.uint32)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def edge(name, x, y):
    x, y = np.asarray(x).reshape(-1), np.asarray(y).reshape(-1)
    ok = x.shape == y.shape and bool(np.array_equal(x, y))
    edges[name] = dict(ok=ok, words=int(x.size), mismatched=None if x.shape != y.shape else int((x != y).sum()))
    if not ok:
        bad.append(f'hand-off {name} not bit-exact')


# ---- compute-die hand-off chain (stg fixtures = values the RTL produced / consumed bit-exact in stage stg)
for L in range(36):
    f = {k: np.load(FX / f'L{L}_{k}.npz') for k in ('resid1', 'resid2', 'qk', 'silu', 'mat_qkv', 'mat_gu', 'mat_od')}
    fj = json.loads((FX / f'L{L}_fixture.json').read_text())
    xin_name, xin_sha = fj['inputs']['die0']['x_in'].split()
    want = 'x_preload.hex' if L == 0 else f'L{L - 1:02d}_die0_x.hex'
    xin = P / xin_name
    ok = xin_name == want and xin.exists() and sha(xin) == xin_sha
    edges[f'L{L}.x_in<-{want}'] = dict(ok=ok, file=xin_name)
    if not ok:
        bad.append(f'L{L} x_in is not {want}')
    edge(f'L{L}.resid1.out==resid2.in', bits(f['resid1']['gold_x']), bits(f['resid2']['x']))
    edge(f'L{L}.resid1.out==gu.x', bits(f['resid1']['gold_x']), bits(f['mat_gu']['x']))
    qkv_rows = bits(f['mat_qkv']['gold_y'])
    edge(f'L{L}.qkv.out==qk.in', qkv_rows, bits(f['qk']['qkv']))
    edge(f'L{L}.gu.out==silu.in', bits(f['mat_gu']['gold_y']), bits(f['silu']['gu']))
    edge(f'L{L}.silu.out==down.x', bits(f['silu']['gold_act']), bits(f['mat_od']['down_x']))
    edge(f'L{L}.resid2.out==layer_X', bits(f['resid2']['gold_x']), read_hex(P / f'L{L:02d}_die0_x.hex'))
# ---- attention leg: vectors built from the qk RTL outputs; TP4 reproduction == od input
vec = {}
for L in range(36):
    m = C / 'vec' / f'L{L}' / 'meta.json'
    if not m.exists():
        bad.append(f'L{L} vectors missing'); continue
    rt = json.loads(m.read_text())['real_token']
    vec[L] = rt
    edges[f'L{L}.qk.out->KV(q,k,v)->TP4 attention==od.o_x'] = dict(ok=rt['tp4_repro_word_mismatch'] == 0 and
                                                                   rt['kv_pre_p_row_zero'] and rt['kv_fp8_representable'],
                                                                   mismatched=rt['tp4_repro_word_mismatch'])
    if not edges[f'L{L}.qk.out->KV(q,k,v)->TP4 attention==od.o_x']['ok']:
        bad.append(f'L{L} attention hand-off not exact')
# ---- KV RTL runs
runs = {}
for d in sorted((C / 'runs').iterdir()) if (C / 'runs').exists() else []:
    log = (d / 'sim.log').read_text(errors='replace') if (d / 'sim.log').exists() else ''
    v = next((l for l in log.splitlines() if l.startswith('KVATTN_REL')), None)
    users = [json.loads(l) for l in log.splitlines() if l.startswith('{"user"')]
    runs[d.name] = dict(verdict=v, users=users, exit=(d / 'exit').read_text().strip() if (d / 'exit').exists() else None,
                        time=(d / 'time').read_text().strip() if (d / 'time').exists() else None,
                        mismatch_sample=[l for l in log.splitlines() if l.startswith('MISMATCH')][:3])
want = [l.split()[0] for l in (C / 'runlist.txt').read_text().splitlines()] if (C / 'runlist.txt').exists() else []
for n in want:
    r = runs.get(n)
    v = (r or {}).get('verdict') or ''
    if n.startswith('CTL_'):
        if 'FAIL' not in v:
            bad.append(f'{n} control did not FAIL: {v or "NOT RUN"}')
    elif not v.startswith('KVATTN_REL PASS') or not r['users'] or not all(u['exact'] for u in r['users']):
        bad.append(f'{n} {v or "NOT RUN"}')
u1 = {L: runs.get(f'L{L}_u1', {}).get('users', [{}])[0] if runs.get(f'L{L}_u1', {}).get('users') else {} for L in range(36)}
keys = ('start_to_retire', 'start_to_status', 'work_span', 'cyc_k_last', 'cyc_v_last', 'cyc_final_out')
per_layer = {L: {k: u.get(k) for k in keys} for L, u in u1.items()}
def stat(k):
    vals = [v[k] for v in per_layer.values() if v.get(k) is not None]
    return dict(min=min(vals), max=max(vals), sum=sum(vals), n=len(vals)) if vals else None
u4 = {}
for i in range(9):
    r = runs.get(f'G{i}_u4')
    if r and r['users']:
        us = r['users']
        u4[f'G{i}'] = dict(layers=[4 * i + j for j in range(4)], cmd_period=(us[-1]['cyc_cmd'] - us[0]['cyc_cmd']) / 3,
                           first_cmd_to_last_status=us[-1]['cyc_status'] - us[0]['cyc_cmd'],
                           start_to_status=[u['start_to_status'] for u in us])
cycles = dict(
    kv_attention_u1_ctx8192={k: stat(k) for k in keys},
    kv_attention_u1_per_layer=per_layer,
    kv_attention_token_36_layers_start_to_status=(stat('start_to_status') or {}).get('sum'),
    kv_attention_u4=u4,
    kv_attention_u4_cmd_period=sorted({v['cmd_period'] for v in u4.values()}) or None)
res = dict(
    stage='chain', grade=a.grade, verdict='PASS' if not bad else 'FAIL',
    golden=('real token (TP4 ISA golden prompt, position 8191, ctx 8192): per layer the KV attention RTL result bit-exact '
            'vs TP8-native attention (S128/PV256) of the q/k/v the compute-die RTL produced in stage stg; the TP4 '
            'attention (S128/PV512) of the same inputs == the od stage input bit-exact (hand-off)'),
    binary_sha256=(C / 'binary.sha256').read_text().split()[0] if (C / 'binary.sha256').exists() else None,
    hand_off=dict(edges=len(edges), exact=sum(1 for e in edges.values() if e['ok'])),
    tp8_vs_tp4_attention={L: v['tp8_vs_tp4_attn'] for L, v in vec.items()},
    cycles=cycles, runs={k: dict(verdict=v['verdict'], exit=v['exit'], time=v['time'], mismatch_sample=v['mismatch_sample'])
                         for k, v in runs.items()},
    failures=bad[:60],
    stand_ins=['KV vehicle tb_kvattn_rel drives the tile face (D2D landing / TX slot) at its compiled edges; the D2D link itself is stage xdie / ovl4u',
               'KV window K/V rows < P from the TP4 golden prefill (kv_pre head 0), not written by the KV RTL in this run'],
    gaps=['golden family split: the KV RTL computes TP8-native attention (PV256) while the 36-layer token golden is TP4 '
          '(PV512); the od/resid stages were fed the TP4 ATTN (word diffs in tp8_vs_tp4_attention). A 36-layer TP8 token '
          'golden (tools/qwen_layerbench/qwen_tp8_layer_gold.py, only L0..L1 at P8191 exist) closes it'],
    edges=edges,
    logs=['runlist.txt', 'timing.txt', 'binary.sha256', 'vectors.sha256', 'fd.txt', 'GRADE', 'runs/<name>/sim.log',
          'runs/<name>/time', 'runs/<name>/exit', 'vec/<name>/meta.json', 'vec/<name>.log'])
(C / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
print('CHAIN', res['verdict'], json.dumps(res['hand_off']), 'failures', len(bad))
