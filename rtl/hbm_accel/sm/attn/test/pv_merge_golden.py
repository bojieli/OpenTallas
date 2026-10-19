#!/usr/bin/env python3
"""HH-2 2026-10-19: golden of tb_pv_merge (ot_hbm_sm_pv_merge, LV 4, PUBLISH 1).
  gen   STIM.hex [seed]      64 chunks x 16 FP32 lanes (entry e chunk j at line e*8+j)
  check STIM.hex RUN.log [tight]   binary-counter merge in RNE FP32 (numpy), fold 0 <- 0 + 1, publication words; prints
                             'PVM PASS checked=N' or 'PVM FAIL mismatches=M'
Merge order (the RTL's): chunk c merges stack[k] + v while bit k of c is set (carry chain), then rests in stack[k];
the flush adds the set levels of n from level 0 up: acc = stack[k] + acc (k = 0: + 0).  Values are normal and nonzero,
so x + 0 = x and the FP32 adds are commutative."""
import sys
import numpy as np

F = np.float32
LV = 4


def lanes(word: int):
    return np.array([(word >> (32 * l)) & 0xFFFFFFFF for l in range(16)], dtype=np.uint32).view(F)


def word(v):
    b = np.asarray(v, dtype=F).view(np.uint32)
    return sum(int(b[l]) << (32 * l) for l in range(16))


def gen(path, seed=19):
    rng = np.random.default_rng(seed)
    with open(path, "w") as f:
        for _ in range(64):
            v = (rng.standard_normal(16) * np.exp2(rng.integers(-6, 7, 16))).astype(F)
            v[v == 0] = F(1.0)
            f.write(f"{word(v):0128x}\n")


def merge(ch):
    st = [None] * (LV + 1)
    for c, x in enumerate(ch):
        v, k = x, 0
        while (c >> k) & 1:
            v = (st[k] + v).astype(F)
            k += 1
        st[k] = v
    n, acc = len(ch), np.zeros(16, F)
    for k in range(LV):
        acc = (st[k] + acc).astype(F) if (n >> k) & 1 else (acc + F(0)).astype(F)
    return acc


def check(stim, log, tight=False):
    ch = [lanes(int(l, 16)) for l in open(stim).read().split()]
    node, tag = {}, {}
    for e in range(8):
        node[e] = merge([ch[e * 8 + j] for j in range(e + 1)])
        tag[e] = (1 << 15) | ((1 if e == 0 else 0) << 14) | (1 << 13) | ((e * 8 + e) << 3) | e
    exp_pv = {(tag[e], word(node[e])) for e in range(8)}
    fold = (node[0] + node[1]).astype(F)
    pubn = {0: fold, **{e: node[e] for e in range(2, 8)}}
    if tight:   # (0<-0+1) (2<-2+3) (4<-4+5) (2<-2+4); publish 2, 0, 6, 7
        n23, n45 = (node[2] + node[3]).astype(F), (node[4] + node[5]).astype(F)
        pubn = {0: fold, 2: (n23 + n45).astype(F), 6: node[6], 7: node[7]}
    exp_pub = {(e, w, tag[e], int(pubn[e].view(np.uint32)[w])) for e in pubn for w in range(16)}
    got_pv, got_pub, done = set(), set(), None
    for ln in open(log):
        p = ln.split()
        if not p:
            continue
        if p[0] == "PV":
            got_pv.add((int(p[1], 16), int(p[2], 16)))
        elif p[0] == "PUB":
            got_pub.add((int(p[1]), int(p[2]), int(p[3], 16), int(p[4], 16)))
        elif p[0] == "PVM" and p[1] == "DONE":
            done = dict(x.split("=") for x in p[2:])
    mism = len(exp_pv ^ got_pv) + len(exp_pub ^ got_pub)
    if done is None:
        mism += 1
    elif done["fault"] != "0" or done["pv"] != "8" or done["pub"] != str(16 * len(pubn)):
        mism += 1
    n = len(exp_pv) * 16 + len(exp_pub)
    if mism:
        print(f"PVM FAIL mismatches={mism} (pv {len(exp_pv ^ got_pv)}, pub {len(exp_pub ^ got_pub)}, done {done})")
        return 1
    print(f"PVM PASS checked={n} (8 runs of 1..8 chunks, {'tight fold calendar' if tight else 'fold 0<-0+1'}, {len(pubn)} publications; {done})")
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 19)
    else:
        sys.exit(check(sys.argv[2], sys.argv[3], len(sys.argv) > 4 and sys.argv[4] == "tight"))
