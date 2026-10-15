#!/usr/bin/env python3
"""RS(544,514) "KP4" reference (IEEE 802.3 clause 91/119: GF(2^10), p(x) = x^10 + x^3 + 1, g(x) = prod_{j=0}^{29}
(x - alpha^j), t = 15) for the S81 die-link FEC RTL (rtl/dsrom_sys/s81_link/ot_s81_kp4_*.sv; owner rule 2026-10-14:
the link's digital layer -- framing, credits, FEC -- is real RTL; only the analog PMA is a behavioural model).

Codeword symbol order: transmitted first = coefficient of x^543.  The FEC frame of the S81 die link carries 10 lane
beats of 512 b + a 20-bit header (12-b alignment marker AM, 8-b codeword sequence) = 5,140 message bits = 514 symbols;
message bit k (k = 0 first) = header[19 - k] for k < 20, then beat b bit (511 - j) for k = 20 + 512 b + j; symbol s
(s = 0 first, x^(543 - s)) = message bits 10 s .. 10 s + 9 MSB first.  Parity symbols 514..543 follow.
On the PMA the codeword is 10 words of 544 bits, word w = codeword bits 544 w .. 544 w + 543 (bit 0 of the codeword
= the MSB of symbol 0 = PMA word 0 bit 543).

    python3 tools/s81_link/rs544.py vectors OUT.hex [--n 64] [--seed 1]   # bench vectors (message, codeword, errors)
    python3 tools/s81_link/rs544.py selftest
"""
from __future__ import annotations

import argparse
import random
import sys

M, N, K, T = 10, 544, 514, 15
PRIM = 0b10000001001          # x^10 + x^3 + 1
EXP = [0] * (2 * 1024)
LOG = [0] * 1024
_x = 1
for _i in range(1023):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x400:
        _x ^= PRIM
for _i in range(1023, 2048):
    EXP[_i] = EXP[_i - 1023]
AM = 0xA5C                     # 12-bit alignment marker of the S81 FEC frame header


def gmul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def ginv(a):
    return EXP[1023 - LOG[a]]


def gpow(a, e):
    return 0 if a == 0 else EXP[(LOG[a] * e) % 1023]


def gen_poly():
    g = [1]                      # coefficients, g[0] = highest degree
    for j in range(2 * T):
        r = EXP[j]
        ng = g + [0]
        for i in range(len(g)):
            ng[i + 1] ^= gmul(g[i], r)
        g = ng
    return g                     # degree 30, monic


G = gen_poly()


def encode(msg):
    """msg: 514 symbols (msg[0] = x^543 coefficient) -> 544-symbol systematic codeword"""
    assert len(msg) == K
    rem = [0] * (2 * T)
    for s in msg:
        fb = s ^ rem[0]
        rem = rem[1:] + [0]
        if fb:
            for i in range(2 * T):
                rem[i] ^= gmul(fb, G[i + 1])
    return list(msg) + rem


def syndromes(cw):
    S = []
    for j in range(2 * T):
        a = EXP[j]
        s = 0
        for c in cw:
            s = gmul(s, a) ^ c
        S.append(s)
    return S


def decode(rx):
    """-> (corrected codeword, n_errors) ; n_errors = -1 when uncorrectable (data returned unchanged)"""
    S = syndromes(rx)
    if not any(S):
        return list(rx), 0
    # Berlekamp-Massey
    C, B = [1] + [0] * (2 * T), [1] + [0] * (2 * T)
    L, m, b = 0, 1, 1
    for n in range(2 * T):
        d = S[n]
        for i in range(1, L + 1):
            d ^= gmul(C[i], S[n - i])
        if d == 0:
            m += 1
        elif 2 * L <= n:
            Tm = C[:]
            coef = gmul(d, ginv(b))
            for i in range(len(C) - m):
                C[i + m] ^= gmul(coef, B[i])
            L, B, b, m = n + 1 - L, Tm, d, 1
        else:
            coef = gmul(d, ginv(b))
            for i in range(len(C) - m):
                C[i + m] ^= gmul(coef, B[i])
            m += 1
    lam = C[:L + 1]
    if L > T:
        return list(rx), -1
    # Omega = S(x) Lambda(x) mod x^2t, S(x) = sum S_j x^j
    om = [0] * (2 * T)
    for i in range(2 * T):
        v = 0
        for k in range(min(i, L) + 1):
            v ^= gmul(lam[k], S[i - k])
        om[i] = v
    out = list(rx)
    nroot = 0
    for pos in range(N):                 # symbol index pos <-> degree e = N-1-pos, X = alpha^e
        e = N - 1 - pos
        xinv = EXP[(1023 - e) % 1023]
        v = 0
        for k in range(L + 1):
            v ^= gmul(lam[k], gpow(xinv, k))
        if v == 0:
            nroot += 1
            num = 0
            for i in range(2 * T):
                num ^= gmul(om[i], gpow(xinv, i))
            den = 0
            for k in range(1, L + 1, 2):      # formal derivative: odd terms
                den ^= gmul(lam[k], gpow(xinv, k - 1))
            if den == 0:
                return list(rx), -1
            ev = gmul(EXP[e % 1023], gmul(num, ginv(den)))   # b = 0: e = X * Omega(X^-1) / Lambda'(X^-1)
            out[pos] ^= ev
    if nroot != L:
        return list(rx), -1
    if any(syndromes(out)):
        return list(rx), -1
    return out, L


def frame_message(hdr20, beats):
    bits = [(hdr20 >> (19 - k)) & 1 for k in range(20)]
    for bt in beats:
        bits += [(bt >> (511 - j)) & 1 for j in range(512)]
    assert len(bits) == 5140
    return [int(''.join(map(str, bits[10 * s:10 * s + 10])), 2) for s in range(K)]


def cw_to_int(cw):
    v = 0
    for s in cw:
        v = (v << 10) | s
    return v                      # 5440 bits, bit 5439 = MSB of symbol 0


def selftest():
    rnd = random.Random(7)
    for it in range(40):
        msg = [rnd.randrange(1024) for _ in range(K)]
        cw = encode(msg)
        assert not any(syndromes(cw))
        ne = rnd.randrange(0, T + 1)
        rx = list(cw)
        for p in rnd.sample(range(N), ne):
            rx[p] ^= rnd.randrange(1, 1024)
        out, n = decode(rx)
        assert out == cw and n == ne, (it, ne, n)
    bad = 0
    for it in range(20):
        msg = [rnd.randrange(1024) for _ in range(K)]
        cw = encode(msg)
        rx = list(cw)
        for p in rnd.sample(range(N), T + 1 + rnd.randrange(8)):
            rx[p] ^= rnd.randrange(1, 1024)
        out, n = decode(rx)
        bad += (n != -1)
    print('RS544 selftest PASS (40 correctable exact; %d/20 over-t not flagged)' % bad)


def vectors(path, n, seed):
    """one line a codeword: <hdr20 hex 5> <beats 10 x 128 hex> <codeword 1360 hex> <nerr> <err positions/values>"""
    rnd = random.Random(seed)
    with open(path, 'w') as f:
        for i in range(n):
            hdr = (AM << 8) | (i & 0xFF)
            beats = [rnd.getrandbits(512) for _ in range(10)]
            if i % 7 == 3:
                beats = [0] * 10
            cw = encode(frame_message(hdr, beats))
            f.write('%05x %s %0360x\n' % (hdr, ' '.join('%0128x' % b for b in beats), cw_to_int(cw[K:])))
    print(f'wrote {n} vectors to {path}')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['selftest', 'vectors'])
    ap.add_argument('out', nargs='?')
    ap.add_argument('--n', type=int, default=64)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args(argv)
    if a.mode == 'selftest':
        selftest()
    else:
        vectors(a.out, a.n, a.seed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
