#!/usr/bin/env python3
"""Pre-recorded stimulus trace for the IRG fastpad chunk bench (original vs fastpad dsdv_idx_rg2_chunk).

One line per cycle, 1120-bit hex word:
  [0] rst_n  [1] ql_v  [9:2] head offset (ql_head = hb + off; off >= 8 never matches)  [521:10] ql_codes
  [553:522] ql_sc  [569:554] ql_w  [1113:570] k_key  [1114] kvalid (record is valid metadata)
Phases: cold prime of all 8 heads, then random traffic: key bubbles, random query reloads interleaved with keys,
full-field values (normal, zero, refused scale, BF16 weight overflow, NaN/Inf weight), and warm resets after which
kvalid stays 0 until all 8 heads are re-primed and the column is flushed.
"""
import random, sys

def bf16_w(r, mode):
    s = r.getrandbits(1)
    if mode == 'big':
        e = r.choice([254, 255, 250, 252])
    elif mode == 'any':
        e = r.getrandbits(8)
    elif mode == 'tiny':
        e = r.randint(0, 5)
    else:
        e = r.randint(112, 140)
    return (s << 15) | (e << 7) | r.getrandbits(7)

def scales(r, mode):
    out = 0
    for b in range(4):
        if mode == 'refuse' and r.random() < 0.5:
            u = r.randint(253, 255)
        elif mode == 'any':
            u = r.getrandbits(8)
        elif mode == 'big':
            u = r.randint(180, 252)
        elif mode == 'tiny':
            u = r.randint(0, 40)
        else:
            u = r.randint(108, 146)
        out |= u << (8 * b)
    return out

def codes(r, zero_p):
    if r.random() < zero_p:
        return 0
    return r.getrandbits(512)

def main():
    seed = int(sys.argv[1]); n = int(sys.argv[2]); out = sys.argv[3]
    r = random.Random(seed)
    rows = []
    state = {'blocked': 0}
    def row(rst=1, qv=0, off=0, qc=0, qs=0, qw=0, key=0, kv=0):
        w = (rst & 1) | ((qv & 1) << 1) | ((off & 0xff) << 2) | (qc << 10) | (qs << 522) | (qw << 554) | (key << 570) | ((kv & 1) << 1114)
        rows.append(w)
    def rand_key():
        m = r.random()
        kmode = 'norm' if m < 0.90 else ('refuse' if m < 0.93 else ('big' if m < 0.96 else ('tiny' if m < 0.98 else 'any')))
        kc = codes(r, 0.03)
        return kc | (scales(r, kmode) << 512)
    def rand_q(off):
        m = r.random()
        qmode = 'norm' if m < 0.96 else ('refuse' if m < 0.97 else ('big' if m < 0.985 else 'any'))
        wm = r.random()
        wmode = 'norm' if wm < 0.95 else ('big' if wm < 0.97 else ('tiny' if wm < 0.99 else 'any'))
        return dict(qv=1, off=off, qc=codes(r, 0.03), qs=scales(r, qmode), qw=bf16_w(r, wmode))
    def prime():
        for h in r.sample(range(8), 8):
            row(key=rand_key(), **rand_q(h))
            for _ in range(r.randint(0, 2)):
                row(key=rand_key())
        for _ in range(90):          # flush: every head holds a primed query before the first valid key
            row(key=rand_key())
    # time 0: reset held, then cold prime
    for _ in range(12):
        row(rst=0, key=rand_key())
    for _ in range(8):
        row(key=rand_key())
    prime()
    next_reset = r.randint(3000, 6000)
    while len(rows) < n:
        if len(rows) >= next_reset:
            # warm reset: in-flight records aborted (bench ring clears on rst_n low), then re-prime
            # sometimes a query beat is in flight exactly when reset hits
            for _ in range(r.randint(0, 3)):
                row(key=rand_key(), kv=1, **rand_q(r.randint(0, 7)))
            for _ in range(r.randint(2, 25)):
                row(rst=0, key=rand_key(), **(rand_q(r.randint(0, 15)) if r.random() < 0.3 else {}))
            # release window: chunk relay (3) + slice relay (3) + rn_p (1) edges; a query beat inside it is accepted at
            # some slices and dropped at others in BOTH forms, at different slices (beats travel 2 vs 9 edges a hop),
            # so the reader re-primes only after the release
            for _ in range(r.randint(12, 20)):
                row(key=rand_key())
            prime()
            next_reset = len(rows) + r.randint(3000, 6000)
            continue
        kv = 1 if r.random() < 0.75 else 0          # bubbles
        key = rand_key() if (kv or r.random() < 0.7) else 0
        if r.random() < 0.04:
            row(key=key, kv=kv, **rand_q(r.randint(0, 15)))
        else:
            row(key=key, kv=kv)
    # tail: drain with bubbles
    for _ in range(200):
        row(key=rand_key())
    with open(out, 'w') as f:
        for w in rows:
            f.write('%0280x\n' % w)
    print('rows', len(rows))

main()
