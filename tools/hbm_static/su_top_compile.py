#!/usr/bin/env python3
"""Whole static SU (ot_hbm_su_static_top) full-shape programme + independent golden (H-ELEM-B 2026-10-15).

One fixed-edge command image drives the real top (4 quarters x 4 port-group slices + cores, 512 lanes, 512 pinned store
banks / 3,072 SRAM models, 4 reducers, 4 RF replicas, RF relay routes). Nothing in the DUT is computed by the bench:
  FILL   1,024 edges: every store word (512 rows x 512 banks, su_arith_compile's seed) enters through the VM SU-station
         ports (32 sector reads / edge; port p fills store groups p and p+8 only);
  OPS    the 31 su_arith_compile baseline classes (its exact control image + NumPy hdc_golden expected words) + BYP_KV
         (KV destination: BF16 write) + AB_RF (B operand = RF scalar broadcast, source code 1), 176 edges each;
  DRAIN  after every op: 64 rows x 64 groups = 4,096 sectors back through the VM ports (expected LG write edge, sector,
         mask, data);
  REDUCE op AB: per quarter an 8-chain + tree FP32 sum of one lane's 64 outputs; op AA: same shape MAX; then reducer 0
         sums the four quarter sums read from its RF replica (class 4) -> RF word 2 (relay to all replicas) -> AB_RF;
         RF sector drains (class 5 + slice-0 port 0) from EVERY quarter of every quarter's results (replica coherence).
Expected values: hdc_golden add/mul/to_bf16 (independent NumPy FP32 RNE, canonical +0) in the compiled order.
Edge rule (see RTL headers): command line E is sampled at edge E; LG samples fill requests at E (data back E+10), drain
writes at E+4; reducer command E -> issue E+2 -> scalar held from E+10 (checked at E+11, reducer r1 LAT 8); RF word
readable by a read sampled at >= export_edge + 12 + RF_RELAY; lane store read n consumed n+3; RF broadcast class command issued n-1 (held for the op).
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import su_arith_compile as SAC  # noqa: E402
from hdc_golden import add, mul, to_bf16  # noqa: E402

QW = 1742 + 240 + 312 + 54 + 74          # bits per quarter per line
LINE = 4 * QW


def f32(u): return np.uint32(u).view(np.float32)
def u32(x): return int(np.float32(x).view(np.uint32))


def fmax(a, b):
    """ot_hbm_su_reduce_static MAX: finite ordered compare, canonical +0 for zeros."""
    fa, fb = f32(a), f32(b)
    r = a if (fa > fb or (fa == fb and not (a >> 31))) else b
    return 0 if (r & 0x7fffffff) == 0 else r


class Prog:
    def __init__(s, n):
        s.n = n
        s.ctl = [[0] * 4 for _ in range(n)]
        s.vmr = [[0] * 4 for _ in range(n)]
        s.vmw = [[0] * 4 for _ in range(n)]
        s.rf = [[0] * 4 for _ in range(n)]
        s.red = [[0] * 4 for _ in range(n)]
        s.expw, s.exps = [], []
        s.lw = np.zeros((n, 4), dtype=np.int64)

    def put(s, arr, e, q, sh, w, val):
        assert 0 <= val < 1 << w
        cur = (arr[e][q] >> sh) & ((1 << w) - 1)
        assert cur == 0, ('slot busy', e, q, sh)
        arr[e][q] |= val << sh

    def vmr_cmd(s, e, q, p, sector, grp, row):
        s.put(s.vmr, e, q, p * 30, 30, (1 << 29) | (sector << 13) | (grp << 9) | row)

    def vmw_cmd(s, e, q, p, src, grp, row, sector, mask):
        s.put(s.vmw, e, q, p * 39, 39, (1 << 38) | (src << 37) | (grp << 33) | (row << 24) | (sector << 8) | mask)

    def rf_cmd(s, e, q, c, addr):
        s.put(s.rf, e, q, c * 9, 9, (1 << 8) | addr)

    def red_cmd(s, e, q, op, a=0, b=0, d=0, tag=0, osel=0, lane=0):
        s.put(s.red, e, q, 0, 74, (1 << 73) | (op << 70) | (a << 60) | (b << 50) | (d << 40) | (tag << 8) | (osel << 7) | lane)

    def write(s, out):
        with open(out / 'prog.mem', 'w') as f:
            for e in range(s.n):
                v = 0
                for q in range(4):
                    qv = ((((s.ctl[e][q] << 240 | s.vmr[e][q]) << 312 | s.vmw[e][q]) << 54 | s.rf[e][q]) << 74) | s.red[e][q]
                    v |= qv << (q * QW)
                f.write(f'{v:0{LINE // 4}x}\n')
        s.expw.sort(key=lambda x: (x[0], x[1], x[2]))
        with open(out / 'expw.mem', 'w') as f:
            for e, q, p, sec, mask, words in s.expw:
                data = 0
                for k, w in enumerate(words): data |= (w & 0xffffffff) << (32 * k)
                f.write(f'{e:08x}{q:01x}{p:01x}{sec:04x}{mask:02x}{data:064x}\n')
        s.exps.sort()
        with open(out / 'exps.mem', 'w') as f:
            for e, q, tag, val in s.exps: f.write(f'{e:08x}{q:08x}{tag:08x}{val:08x}\n')
        with open(out / 'explw.mem', 'w') as f:
            for e in range(s.n): f.write(''.join(f'{int(s.lw[e][q]):02x}' for q in (3, 2, 1, 0)) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--rf-relay', type=int, default=8)
    ap.add_argument('--mlat', type=int, default=3); ap.add_argument('--alat', type=int, default=3); ap.add_argument('--leaf', type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    arith = out / 'arith'
    subprocess.run([sys.executable, str(HERE / 'su_arith_compile.py'), str(arith)], check=True)
    seed = np.array([int(x, 16) for x in (arith / 'seed.mem').read_text().split()], dtype=np.uint32)
    gold = np.array([int(x, 16) for x in (arith / 'gold.mem').read_text().split()], dtype=np.uint32)
    ctl_lines = (arith / 'control.mem').read_text().split()
    nbase = len(SAC.OPS); assert len(ctl_lines) == nbase * 176 and len(gold) == nbase * 32768
    data = seed.view(np.float32).reshape(512, 512)          # [row][global lane]
    R, FO = a.rf_relay, 8 + 23 + 4 * (a.mlat - 3) + (a.alat - 3) + a.leaf
    S0, PER = 1040, 176
    names = [n for n, _ in SAC.OPS] + ['BYP_KV', 'AB_RF']
    NOPS = len(names)
    NE = S0 + PER * NOPS + FO + 64 + 128 + 40
    P = Prog(NE)
    # ---------------- FILL: port p, edge e: row e>>1, store group p + 8*(e&1)
    for e in range(1024):
        row, hi = e >> 1, e & 1
        for q in range(4):
            for p in range(8):
                P.vmr_cmd(e, q, p, (q << 13) | (row << 4) | (hi << 3) | p, p + 8 * hi, row)
    # ---------------- op control images
    terms_all = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) for k in range(7))
    terms_noB = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) if s != 1 for k in range(7))
    G_ADDR = 2
    golds = [gold[t * 32768:(t + 1) * 32768] for t in range(nbase)]
    A = data[0:64]

    def extra_images(mods, terms, vb_override):
        base = dict(no=1, ni=8192, ls=7, lvw=7, dst=1, co_dst=1, cp_imm1=0x3fa00000, cm_imm1=0x3fa00000, ce_imm1=0x3fa00000,
                    ca_imm2=0x3ec00000, cs_imm2=0x3ec00000, cx_imm3=0x3f400000)
        base.update(mods)
        imgs = []
        for cycle in range(176):
            vector = max(0, min(63, cycle - 8)); row = []
            for q in range(4):
                vb = [SAC.physical_word(q, (s * 64 if s < 4 else 256) + vector) for s in range(5)]
                for s, v in vb_override.items(): vb[s] = v
                f = dict(base, ld=int(cycle == 0), ld_c=terms, emit=int(8 <= cycle < 72), i_v=vector * 128,
                         vb=sum(v << (s * 24) for s, v in enumerate(vb)))
                row.append(SAC.pack(f))
            imgs.append(row)
        return imgs

    S = [S0 + PER * t for t in range(NOPS)]
    for t in range(nbase):
        for c in range(176):
            v = int(ctl_lines[t * 176 + c], 16)
            for q in range(4): P.ctl[S[t] + c][q] = (v >> (q * 1742)) & ((1 << 1742) - 1)
    for t, (mods, terms, vbo) in ((nbase, (dict(dst=2, co_dst=2), terms_all, {})),
                                  (nbase + 1, (dict(cp_m1=1, cm_m1=1, srcs=1 << 2), terms_noB, {1: G_ADDR}))):
        for c, row in enumerate(extra_images(mods, terms, vbo)):
            for q in range(4): P.ctl[S[t] + c][q] = row[q]
    # lane write counts: every op writes 128 lanes per quarter at S+FO .. S+FO+63
    for t in range(NOPS):
        for c in range(64): P.lw[S[t] + FO + c][:] = 128
    # ---------------- reducers (op AB sum, op AA max) + global sum + RF drains
    t_ab, t_aa = names.index('AB'), names.index('AA')
    rf_val = {}
    lane_sum = [7 * q + 3 for q in range(4)]; lane_max = [11 * q + 5 for q in range(4)]
    X = {}
    RLAT = 8                     # reducer command edge E -> issue E+2 -> commit / scalar issue+8 (r1 operand stage)
    DEP = RLAT + 1               # same-address dependent command distance
    NCH = DEP                    # interleaved accumulation chains so one lane output per edge never waits
    for kind, t, lanes, base_addr, rfo in (('sum', t_ab, lane_sum, 0, 0), ('max', t_aa, lane_max, 32, 1)):
        for q in range(4):
            l = lanes[q]; vals = [int(golds[t][c * 512 + 128 * q + l]) for c in range(64)]
            acc = [None] * NCH; ready = {}
            for c in range(64):
                e = S[t] + FO + c; k = c % NCH
                if c < NCH:
                    P.red_cmd(e, q, 0, d=base_addr + k, lane=l); acc[k] = vals[c]
                else:
                    op = 1 if kind == 'sum' else 3
                    assert e >= ready[base_addr + k]
                    P.red_cmd(e, q, op, a=base_addr + k, d=base_addr + k, lane=l)
                    acc[k] = u32(add(f32(acc[k]), f32(vals[c]))) if kind == 'sum' else fmax(acc[k], vals[c])
                ready[base_addr + k] = e + DEP
            comb = (lambda x, y: u32(add(f32(x), f32(y)))) if kind == 'sum' else fmax
            top = 2 if kind == 'sum' else 5
            # pairwise tree over the chains (left-to-right pairs per level), each op at the first edge its operands are
            # committed and the reducer's command slot is free
            vv = {base_addr + i: acc[i] for i in range(NCH)}
            level = [base_addr + i for i in range(NCH)]; nxt_addr = base_addr + NCH; last = S[t] + FO + 63
            while len(level) > 1:
                nl = []
                for i in range(0, len(level) - 1, 2):
                    x, y = level[i], level[i + 1]
                    e = max(ready[x], ready[y], last + 1); last = e
                    d = nxt_addr; nxt_addr += 1
                    P.red_cmd(e, q, top, a=x, b=y, d=d); vv[d] = comb(vv[x], vv[y]); ready[d] = e + DEP; nl.append(d)
                if len(level) % 2: nl.append(level[-1])
                level = nl
            root = level[0]
            ex = max(ready[root], last + 1); tag = 0x100 | (8 * q + rfo)
            assert nxt_addr < base_addr + 32
            P.red_cmd(ex, q, 4, a=root, tag=tag)
            P.exps.append((ex + RLAT + 3, q, tag, vv[root]))
            rf_val[8 * q + rfo] = vv[root]; X[(kind, q)] = ex
    xl = max(X.values())
    m = xl + RLAT + 4 + 2 + R    # class-4 read (m-2) after the RF commit of the last export (+RLAT+4+R)
    gsum = None
    for i in range(4):
        e = m + DEP * i
        P.rf_cmd(e - 2, 0, 4, 8 * i)
        P.red_cmd(e, 0, 0 if i == 0 else 1, a=80, d=80, osel=1)
        gsum = rf_val[8 * i] if i == 0 else u32(add(f32(gsum), f32(rf_val[8 * i])))
    ex3 = m + 4 * DEP; tag = 0x100 | G_ADDR
    P.red_cmd(ex3, 0, 4, a=80, tag=tag); P.exps.append((ex3 + RLAT + 3, 0, tag, gsum)); rf_val[G_ADDR] = gsum
    g_ready = ex3 + RLAT + 4 + R
    # AB_RF: B = RF word G broadcast (class 1 held one edge ahead through the op)
    t_rf = nbase + 1
    assert S[t_rf] - 1 >= g_ready
    for e in range(S[t_rf] - 1, S[t_rf] + 176):
        for q in range(4): P.rf_cmd(e, q, 1, G_ADDR)
    gw = f32(gsum)
    golds.append(to_bf16(A).view(np.uint32).ravel())                  # BYP_KV: KV write = bf16(out)
    golds.append(mul(A, gw).astype(np.float32).view(np.uint32).ravel())  # AB_RF
    # RF drains in the gap after op 3's drain: every quarter drains RF groups 0..3 (row 0) via slice 0 port 0
    Z = S[3] + FO + 64 + 128 + 2
    assert Z > g_ready and Z + 8 < S[4] + FO + 64
    for q in range(4):
        for g in range(4):
            e = Z + 2 * g
            P.rf_cmd(e, q, 5, 8 * g)
            sec = (q << 13) | ((508 + g) << 4) | (1 << 3)
            mask = 0x07 if g == 0 else 0x03
            P.vmw_cmd(e + 1, q, 0, 1, 0, 0, sec, mask)
            words = [rf_val.get(8 * g + k, 0) if (mask >> k) & 1 else 0 for k in range(8)]
            P.expw.append((e + 1 + 4, q, 0, sec, mask, words))
    # ---------------- drains after every op
    for t in range(NOPS):
        D = S[t] + FO + 64
        g = golds[t]
        for e in range(128):
            row, hi = 256 + (e >> 1), e & 1
            for q in range(4):
                for p in range(8):
                    j = p + 8 * hi
                    sec = (q << 13) | (row << 4) | (hi << 3) | p
                    P.vmw_cmd(D + e, q, p, 0, j, row, sec, 0xff)
                    c = row - 256
                    words = [int(g[c * 512 + 128 * q + 8 * j + k]) for k in range(8)]
                    P.expw.append((D + e + 4, q, p, sec, 0xff, words))
    P.write(out)
    man = dict(schema='opentallas.hbm.su_static_top_programme.v1', qualified=False, edges=NE, ops=names, op_start=S,
               first_output=FO, rf_relay=R, fill_edges=1024, expected_vm_writes=len(P.expw), expected_scalars=len(P.exps),
               sum_lanes=lane_sum, max_lanes=lane_max, rf_words={str(k): f'{v:08x}' for k, v in sorted(rf_val.items())},
               global_sum_export=ex3, g_ready=g_ready, rf_drain_edge=Z,
               golden='hdc_golden add/mul/to_bf16 NumPy FP32 RNE (independent of the DUT); su_arith_compile seed/gold/control reused',
               line_bits=LINE, quarter_layout='[q*2422 +: 2422] = {control1742, vmr240, vmw312, rf54, red74}')
    (out / 'programme.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'NE={NE} NW={len(P.expw)} NS={len(P.exps)}')


if __name__ == '__main__':
    main()
