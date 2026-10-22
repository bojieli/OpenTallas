#!/usr/bin/env python3
"""MU-TOK-KV 10-19: run cases of drive_qwk_slice_attn_mu.svh from the 4-user calendar of record (mu_calendar).

The KV-die attention service is one resource ('kvs'); mu_calendar places one kvs window per user-layer (kv_service
cycles, disjoint across users).  The first NSTEP windows of the compiled calendar (layer granularity, SOURCED inputs)
give each step's user, layer and run-edge offset (window start - first window start).  Operands: user u, layer l ->
the real TP4 vector set L<l%2>_d<u>_g<l//2> (distinct real q / K,V history / gold per step).
Cases (each also with +KVA_HCKC, suffix h = diagnostic HBM-clock-on-core):
  u1      single user (user 0, layer 0)
  u4cal   the calendar's first 8 kvs windows (users 0..3 interleaved)
  u4pack  users 0..3 layer 0 back to back at the priced attention window (LAYER_WINDOWS attention = 1,816) = occupancy stress
  m5/m6/m7  u4cal with KVA_MUT 5 (user-row swap) / 6 (user 2 RESULT slot late) / 7 (user 3 epoch user tag wrong at the seam)

    kv_attn_mu_cases.py --vec VECDIR --out cases.txt [--json cal.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import mu_calendar as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vec', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json')
    ap.add_argument('--nstep', type=int, default=8)
    a = ap.parse_args()
    cal = M.compile_calendar(dict(M.SOURCED), tokens=1, granularity='layer')
    win = []
    for u, seq in cal['schedule'].items():
        for name, t0, b in seq:
            for x, y in b['windows'].get('kvs', []):
                win.append((t0 + x, t0 + y, int(u), name))
    win.sort()
    steps = []
    for s, e, u, name in win[:a.nstep]:
        l = int(name.lstrip('L'))
        steps.append(dict(user=u, layer=l, rel=s - win[0][0], window=[s, e], vec=f'L{l % 2}_d{u}_g{l // 2}'))
    attn = dict((op, n) for op, unit, n, busy in M.LAYER_WINDOWS)['attention']

    def args(st):
        return ' '.join([f'+NSTEP={len(st)}'] + [f'+VEC{k}={a.vec}/{x["vec"]} +U{k}={x["user"]} +L{k}={x["layer"]} +REL{k}={x["rel"]}'
                                                  for k, x in enumerate(st)])
    pack = [dict(user=u, layer=0, rel=attn * u, vec=f'L0_d{u}_g0') for u in range(4)]
    cases = dict(u1=args(steps[:1]), u4cal=args(steps), u4pack=args(pack),
                 m5=args(steps) + ' +KVA_MUT=5', m6=args(steps) + ' +KVA_MUT=6', m7=args(steps) + ' +KVA_MUT=7')
    lines = [f'# kv_attn_mu_cases.py: mu_calendar SOURCED kv_service {cal["inputs"]["kv_service"]}, attention window {attn}']
    for n, pa in cases.items():
        lines.append(f'{n} {pa}')
        lines.append(f'{n}h {pa} +KVA_HCKC')
    Path(a.out).write_text('\n'.join(lines) + '\n')
    rec = dict(schema='opentallas.mu_tok_kv.cases.v1', kv_service=cal['inputs']['kv_service'], attention_window=attn,
               calendar_steps=steps, pack_steps=pack)
    if a.json:
        Path(a.json).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['calendar_steps']))


if __name__ == '__main__':
    main()
