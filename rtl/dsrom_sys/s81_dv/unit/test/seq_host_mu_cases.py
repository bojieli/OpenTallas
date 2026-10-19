#!/usr/bin/env python3
"""MU-S81-2/SEQ (10-19): job-start (+mu) and boot-config (+cfg) files for tb_dsdv_seq_host_mu.sv.

Calendars of record: results/arch/mu_s81_1018/calendar_{ar,mtp}.json (dv_mu_calendar --phase-q 4).  Boot config
lines "IDX WORD" (hex): host CSR 0x15 = f_mc (dsdv_mu_hslot + dsdv_mu_hwin), 0x16 = f_mw (dsdv_mu_hwin windows), as
dsdv_seq_host_mux decodes them from f_host:
  gap table  one sel-0 word per calendar slot: g[k] = shift[k+1] - shift[k], g[n-1] = P - shift[n-1]
  RL         sel 1, d[23] = 0: start-capture -> t_kd edges of the compiled programme (KIT age + 7 = 64 for L0)
  windows    NEV 8 events: e0..e3 TX window (kind 0) on end slice ep 0..3 at D = DB + 2 ep, e4..e7 landing replay
             (kind 1) at D = DB + 1 + 2 ep; per-slot attributes {land, ab} = {s % 3 != 2, s % 2} for every event
mu file: "shift user pos tok slot" a line, shift in edges after the launch edge, two passes of the period
(pos = 3 + 100 user + pass stride, tok = 1000 + 7 user + pass: bench data).
  seq_host_mu_cases.py --root R --out DIR       writes every case (see CASES) into DIR
"""
import argparse
import json
from pathlib import Path

RL = 64            # L0 programme: KIT row age 57 + 7 (seq_host: f_ks capture -> issuer +3, command +4 + age, KIT -> t_kd +3 - 7 + 7)
DB = 50            # window D base: D in [nw + 2, RL - 2] for nw <= 46


def attr(s):
    return (1 if s % 3 != 2 else 0, s % 2)


def w_gap(g):
    assert 0 < g < 1 << 24
    return 0x15, (1 << 25) | g


def w_rl(r):
    return 0x15, (1 << 25) | (1 << 24) | r


def w_win(sub, d):
    return 0x16, (1 << 25) | (sub << 21) | d


def cfg_words(gaps, nw, rl=RL, windows=True):
    w = [w_gap(g) for g in gaps] + [w_rl(rl)]
    if windows:
        for e in range(8):
            kind, ep = (0, e) if e < 4 else (1, e - 4)
            D = DB + 2 * ep + kind
            w += [w_win(0, e | kind << 8 | ep << 9), w_win(1, D)]
            for s in range(nw):
                land, ab = attr(s)
                w.append(w_win(2, s | ab << 10 | land << 11))
    return w


def calendar(root, mode):
    c = json.loads((root / f'results/arch/mu_s81_1018/calendar_{mode}.json').read_text())
    sh = [s['shift'] for s in c['slots']]
    us = [s['user'] for s in c['slots']]
    P = c['period']
    gaps = [b - a for a, b in zip(sh, sh[1:] + [P])]
    stride = c['pos']['stride']
    return P, sh, us, gaps, stride


def starts(P, sh, us, stride, passes=2):
    out = []
    for p in range(passes):
        for k, (s, u) in enumerate(zip(sh, us)):
            out.append((p * P + s, u, 3 + 100 * u + p * stride, 1000 + 7 * u + p, k))
    return out


def write(d, name, mu, cfg):
    (d / f'{name}.mu').write_text(''.join(f'{a} {b} {c} {e} {f}\n' for a, b, c, e, f in mu))
    (d / f'{name}.cfg').write_text(''.join(f'{i:02x} {x:07x}\n' for i, x in cfg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    root, d = Path(a.root), Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    info = {}
    for mode in ('ar', 'mtp'):
        P, sh, us, gaps, stride = calendar(root, mode)
        n = len(sh)
        st = starts(P, sh, us, stride)
        cfg = cfg_words(gaps, n)
        write(d, f'{mode}', st, cfg)                     # all users, two periods
        write(d, f'{mode}_single', st[:1], cfg)          # user 0 alone (same config, same boot)
        info[mode] = dict(period=P, slots=n, users=sorted(set(us)), gaps=sorted(set(gaps)), starts=len(st))
    P, sh, us, gaps, stride = calendar(root, 'ar')
    one = starts(P, sh, us, stride, passes=1)
    # the former uniform-period config (one gap word = S 21,312) on the record calendar: user 3 is 4 edges off -> t_mf[1]
    write(d, 'f_uniform', one, cfg_words([gaps[0]], 47))
    # one user 4 edges off its slot boundary (issuer-legal: 4-edge phase) -> t_mf[1]
    off = [(s + (4 if k == 3 else 0), u, p, t, k) for (s, u, p, t, k) in one[:6]]
    write(d, 'f_offcal', off, cfg_words(gaps, len(gaps)))
    # RL one edge long: every return mismatches its announced edge -> t_mf[2]
    write(d, 'f_rl', one[:3], cfg_words(gaps, len(gaps), rl=RL + 1))
    # a 2-slot calendar {8, 40}: slot 0 reused at +48 while its start (RL 64) is outstanding -> collision t_mf[0]
    two = cfg_words([8, 40], 2)
    write(d, 'f_collide', [(0, 0, 100, 1000, 0), (48, 1, 101, 1007, 0)], two)
    # the same user in slots 0 and 1 (+8) while its first start is outstanding -> dup t_mf[1]
    write(d, 'f_dup', [(0, 5, 100, 1000, 0), (8, 5, 101, 1001, 1)], two)
    (d / 'cases.json').write_text(json.dumps(info, indent=1) + '\n')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
