#!/usr/bin/env python3
"""ELEM-CENSUS S81-LINK 2026-10-16: GF(2)-linear (lookahead) forms of the two per-cycle chains of the S81 KP4 FEC RTL.

The KP4 encoder advances its 30-symbol LFSR by 52 message symbols a cycle and the decoder advances each of its 30
syndromes by 55 received symbols a cycle (Horner).  Written as 52 / 55 chained steps (H-DIE 7a8b12424) each cycle is a
~200-XOR-level chain -- not closable at 833 ps.  Every step is GF(2)-linear (XOR plus multiplication by a CONSTANT
GF(2^10) element), so the whole cycle is one GF(2) matrix: each next-state bit = the XOR of a fixed subset of
{state bits, window bits}.  This script derives those subsets by evaluating EXACTLY the RTL step (same symbol order,
same constants) on every basis vector, self-checks the matrices against tools/s81_link/rs544.py (encode parity,
syndromes) on random codewords, and writes one balanced XOR reduction per output bit:

    rtl/dsrom_sys/s81_link/ot_s81_kp4_enc_mat.svh  e_ar / e_p0 / e_p1: next rem = A rem ^ P0 win[259:0] ^ P1 win[519:260]
    rtl/dsrom_sys/s81_link/ot_s81_kp4_syn_mat.svh  s_ar / s_p0 / s_p1: next S = A S ^ P0 win[274:0] ^ P1 win[549:275]
(S81-KP4 2026-10-17: the state part is the loop; the window parts are computed a cycle ahead and registered.)

    python3 tools/s81_link/gen_kp4_linear.py [OUTDIR [LA2DIR]]   (default rtl/dsrom_sys/s81_link,
                                                                  rtl/hbm_accel/cores_split/reform_1104b)
    rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la2_mat.svh  l2_r* / l2_w*: the LA = 2 encoder (HBM-GAPS-3 11-05)
    rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_ffa_mat.svh  fb / fa / fo: LA = 2 + FF FOLD (A in the FF slices)
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rs544 as R  # noqa: E402

NP, SPC_E, SPC_D = 30, 52, 55


# ------------------------------------------------------------------ encoder: the RTL g_lfsr step chain
def enc_cycle(rem, w):
    """rem[i] = LFSR symbol i (rem[0] = feedback end), w[k] = window symbol k (k = 0 first); 52 RTL steps"""
    lr = list(rem)
    for k in range(SPC_E):
        fb = w[k] ^ lr[0]
        lr = [(lr[i + 1] if i < NP - 1 else 0) ^ R.gmul(fb, R.G[i + 1]) for i in range(NP)]
    return lr


def enc_unpack(v):
    """lin_in bit vector (int, 820 b) -> (rem, w).  rem_f[10 i + b] = lin_in[520 + 10 i + b];
    window symbol k = wsl[519 - 10 k -: 10] = lin_in[519 - 10 k -: 10]"""
    rem = [(v >> (520 + 10 * i)) & 0x3FF for i in range(NP)]
    w = [(v >> (510 - 10 * k)) & 0x3FF for k in range(SPC_E)]
    return rem, w


def enc_pack_out(rem):
    return sum(r << (10 * i) for i, r in enumerate(rem))


# ------------------------------------------------------------------ decoder: the RTL g_syn Horner chain
def syn_cycle(S, w):
    out = []
    for j in range(NP):
        t, a = S[j], R.EXP[j]
        for k in range(SPC_D):
            t = R.gmul(t, a) ^ w[k]
        out.append(t)
    return out


def syn_unpack(v):
    """syn_in (850 b): S_f[10 j + b] = syn_in[550 + 10 j + b]; window symbol k = swin[5499 - 10 k -: 10]
    = syn_in[549 - 10 k -: 10]"""
    S = [(v >> (550 + 10 * j)) & 0x3FF for j in range(NP)]
    w = [(v >> (540 - 10 * k)) & 0x3FF for k in range(SPC_D)]
    return S, w


def matrix(fn, unpack, nin):
    """columns: output bit vector for every basis input bit"""
    return [enc_pack_out(fn(*unpack(1 << b))) for b in range(nin)]


def apply(cols, v):
    o = 0
    b = 0
    while v:
        if v & 1:
            o ^= cols[b]
        v >>= 1
        b += 1
    return o


def masks(cols, nout):
    return [sum(1 << b for b, c in enumerate(cols) if (c >> o) & 1) for o in range(nout)]


def selfcheck(ce, cs, n=24, seed=7):
    rng = random.Random(seed)
    for _ in range(n):
        msg = [rng.randrange(1024) for _ in range(R.K)]
        cw = R.encode(msg)
        # encoder: 6 leading zero symbols, then 52 symbols a cycle for 10 cycles (520 = 6 + 514)
        sy = [0] * 6 + msg
        rem = [0] * NP
        for c in range(10):
            w = sy[SPC_E * c: SPC_E * (c + 1)]
            v = enc_pack_out(rem) << 520 | sum(s << (510 - 10 * k) for k, s in enumerate(w))
            r2 = apply(ce, v)
            assert r2 == enc_pack_out(enc_cycle(rem, w)), "encoder matrix != step chain"
            rem = [(r2 >> (10 * i)) & 0x3FF for i in range(NP)]
        assert rem == cw[R.K:], "encoder matrix parity != rs544.encode"
        # decoder syndromes: corrupt a few symbols, 6 leading zeros, 55 symbols a cycle for 10 cycles
        rx = list(cw)
        for p in rng.sample(range(R.N), rng.randrange(0, 20)):
            rx[p] ^= rng.randrange(1, 1024)
        sy = [0] * 6 + rx
        S = [0] * NP
        for c in range(10):
            w = sy[SPC_D * c: SPC_D * (c + 1)]
            v = enc_pack_out(S) << 550 | sum(s << (540 - 10 * k) for k, s in enumerate(w))
            r2 = apply(cs, v)
            assert r2 == enc_pack_out(syn_cycle(S, w)), "syndrome matrix != Horner chain"
            S = [(r2 >> (10 * j)) & 0x3FF for j in range(NP)]
        assert S == R.syndromes(rx), "syndrome matrix != rs544.syndromes"


def emit_split(path, what, groups):
    """groups: [(out_name, in_expr, nin, masks)] -> one balanced XOR reduction per output bit of every group"""
    lines = [f"// GENERATED by tools/s81_link/gen_kp4_linear.py -- {what}.",
             "// <out>[o] = XOR of the <in> bits set in mask o (GF(2)-linear lookahead of the per-cycle chain, split into the",
             "// loop-carried STATE part and the pipelined WINDOW parts; derived from the exact RTL step on every basis vector,",
             "// self-checked against tools/s81_link/rs544.py).  Include inside the module body after the vector declarations."]
    for name, expr, nin, ms in groups:
        hexw = (nin + 3) // 4
        for o, m in enumerate(ms):
            lines.append(f"assign {name}[{o}] = ^({expr} & {nin}'h{m:0{hexw}x});")
    Path(path).write_text("\n".join(lines) + "\n")


def split(ms, nwin, cuts):
    """full masks over {state, window[nwin-1:0]} -> state masks + one mask list per window slice [lo, hi)"""
    st = [m >> nwin for m in ms]
    parts = [[(m >> lo) & ((1 << (hi - lo)) - 1) for m in ms] for lo, hi in cuts]
    return st, parts


def selfcheck_split(me, ms, n=24, seed=11):
    """the RTL form: next = A.state ^ P0.win[lo0:hi0] ^ P1.win[lo1:hi1] (bit-for-bit the full matrix)"""
    def ap(masks, v):
        return sum((bin(m & v).count("1") & 1) << o for o, m in enumerate(masks))
    rng = random.Random(seed)
    for mfull, nwin in ((me, 520), (ms, 550)):
        st, parts = split(mfull, nwin, CUTS[nwin])
        for _ in range(n):
            s, w = rng.getrandbits(300), rng.getrandbits(nwin)
            ref = ap(mfull, (s << nwin) | w)
            got = ap(st, s)
            for (lo, hi), pm in zip(CUTS[nwin], parts):
                got ^= ap(pm, (w >> lo) & ((1 << (hi - lo)) - 1))
            assert got == ref, "split matrix != full matrix"


# window slices of the pipelined partial sums (S81-KP4 2026-10-17): two halves, each registered before the loop
CUTS = {520: [(0, 260), (260, 520)], 550: [(0, 275), (275, 550)]}

# ------------------------------------------------------------------ encoder LA = 2 (HBM-GAPS-3 2026-11-05, opt-in)
# The LA = 1 loop rem' = A rem ^ w has one cycle for a <= 173-input XOR plus its 300 x 300 wiring (the S81 enc tile
# closed TT +0.7 ps in a 216 x 216 square; HBM serdes_tx routed TT -180.76 on the same path).  Two steps at once:
#     R_j = A^2 R_(j-1) ^ (A w_2j ^ w_(2j+1)),   R_(-1) = 0 at chunk 0,   parity = R_4
# so the state loop gets two cycles: G registered partial sums of A^2 R (rem bits split in G index groups), then one
# XOR of the G partials and v.  v = A w_k ^ w_(k+1) is feed-forward (G registered partials of A w_k, then ^ w_(k+1)).
LA2_G = 4


def matmul_masks(ma, mb):
    """row masks of A.B over GF(2) (A, B 300 x 300 as row masks over the input bit index)"""
    out = []
    for m in ma:
        r = 0
        b = 0
        while m:
            if m & 1:
                r ^= mb[b]
            m >>= 1
            b += 1
        out.append(r)
    return out


def group_masks(ms, n, g):
    w = n // g
    return [[(m >> (w * i)) & ((1 << w) - 1) for m in ms] for i in range(g)]


def selfcheck_la2(me, n=24, seed=13):
    """LA = 2 pair recurrence on the split masks == the LA = 1 chain == rs544.encode parity"""
    def ap(masks, v):
        return sum((bin(m & v).count("1") & 1) << o for o, m in enumerate(masks))
    ea, (e0, e1) = split(me, 520, CUTS[520])
    a2 = matmul_masks(ea, ea)
    ga2, gaw = group_masks(a2, 300, LA2_G), group_masks(ea, 300, LA2_G)
    w75 = 300 // LA2_G
    rng = random.Random(seed)
    for _ in range(n):
        msg = [rng.randrange(1024) for _ in range(R.K)]
        sy = [0] * 6 + msg
        ws = []
        for c in range(10):
            win = sum(s << (510 - 10 * k) for k, s in enumerate(sy[SPC_E * c: SPC_E * (c + 1)]))
            ws.append(ap(e0, win & ((1 << 260) - 1)) ^ ap(e1, win >> 260))
        rem = 0
        for c in range(10):
            rem = ap(ea, rem) ^ ws[c]
        Rj = 0
        for j in range(5):
            st = 0
            for i in range(LA2_G):
                st ^= ap(ga2[i], (Rj >> (w75 * i)) & ((1 << w75) - 1))
            v = ws[2 * j + 1]
            for i in range(LA2_G):
                v ^= ap(gaw[i], (ws[2 * j] >> (w75 * i)) & ((1 << w75) - 1))
            Rj = (0 if j == 0 else st) ^ v
        assert Rj == rem, "LA2 pair recurrence != LA1 chain"
        assert [(Rj >> (10 * i)) & 0x3FF for i in range(NP)] == R.encode(msg)[R.K:], "LA2 parity != rs544.encode"
    return ga2, gaw


def emit_la2(path, ga2, gaw):
    w = 300 // LA2_G
    hexw = (w + 3) // 4
    lines = ["// GENERATED by tools/s81_link/gen_kp4_linear.py -- KP4 encoder LA = 2 (opt-in, ot_s81_kp4_enc #(.LA(2))):",
             "// R_j = A^2 R_(j-1) ^ (A w_2j ^ w_(2j+1)).  l2_r<i>[o] = XOR of rem_q[%d i +: %d] under row o of A^2 (state loop," % (w, w),
             "// stage 1, registered); l2_w<i>[o] = XOR of wb[%d i +: %d] under row o of A (feed-forward, registered).  Derived" % (w, w),
             "// from the LA = 1 matrices above, self-checked against the LA = 1 chain and tools/s81_link/rs544.py.",
             "// Include inside the LA = 2 generate block after the vector declarations."]
    for nm, src, gs in (("l2_r", "rem_q", ga2), ("l2_w", "wb", gaw)):
        for i, ms in enumerate(gs):
            for o, m in enumerate(ms):
                lines.append(f"assign {nm}{i}[{o}] = ^({src}[{w * i + w - 1}:{w * i}] & {w}'h{m:0{hexw}x});")
    Path(path).write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------ encoder LA = 2 FOLD (DIE-HEAD-85/TXF 2026-11-07, opt-in)
# HEAD TX vE failed GRT on the LA2 strip: the feed-forward A w_k cone (l2_w, a dense 300 x 300 matrix on wb) and the
# state cone (l2_r) converged on one 40-um strip.  FOLD moves A into the FF matrix, which already reads the chunk window
# in 8 registered 65-bit input slices (fp): on an even chunk the slice computes (A P) ch, on an odd chunk P ch, so wb
# carries A w_2j then w_(2j+1) and v = wb(T-1) ^ wb(T) = A w_2j ^ w_(2j+1).  Per slice s, output o, three disjoint
# masks: B = AP & P (both chunks), EA = AP & ~P (even only), EP = P & ~AP (odd only):
#     fp[s][o] = ^(cq & B) ^ (ev ? ^(cq & EA) : ^(cq & EP))
# The l2_w cone and its 1200 wp flops are gone; the stream and its latency are unchanged.
FF_SL = 65


def fold_masks(me):
    """-> (B, EA, EP): per slice s (8 x 65 window bits), 300 row masks each"""
    ea, (e0, e1) = split(me, 520, CUTS[520])
    pf = [e0[j] | (e1[j] << 260) for j in range(300)]
    apf = matmul_masks(ea, pf)
    sl = lambda m, s: (m >> (FF_SL * s)) & ((1 << FF_SL) - 1)
    B = [[sl(apf[o] & pf[o], s) for o in range(300)] for s in range(8)]
    EA = [[sl(apf[o] & ~pf[o], s) for o in range(300)] for s in range(8)]
    EP = [[sl(pf[o] & ~apf[o], s) for o in range(300)] for s in range(8)]
    return B, EA, EP


def selfcheck_fold(me, ga2, fm, n=24, seed=17):
    """the FOLD recurrence (slice partials as the RTL computes them) == rs544.encode parity"""
    def ap(masks, v):
        return sum((bin(m & v).count("1") & 1) << o for o, m in enumerate(masks))
    B, EA, EP = fm
    w75 = 300 // LA2_G
    rng = random.Random(seed)
    for _ in range(n):
        msg = [rng.randrange(1024) for _ in range(R.K)]
        sy = [0] * 6 + msg
        wsel = []
        for c in range(10):
            win = sum(s << (510 - 10 * k) for k, s in enumerate(sy[SPC_E * c: SPC_E * (c + 1)]))
            acc = 0
            for s in range(8):
                x = (win >> (FF_SL * s)) & ((1 << FF_SL) - 1)
                acc ^= ap(B[s], x) ^ ap(EA[s] if c % 2 == 0 else EP[s], x)
            wsel.append(acc)
        Rj = 0
        for j in range(5):
            st = 0
            for i in range(LA2_G):
                st ^= ap(ga2[i], (Rj >> (w75 * i)) & ((1 << w75) - 1))
            Rj = (0 if j == 0 else st) ^ wsel[2 * j] ^ wsel[2 * j + 1]
        assert [(Rj >> (10 * i)) & 0x3FF for i in range(NP)] == R.encode(msg)[R.K:], "LA2 FOLD parity != rs544.encode"


def emit_fold(path, fm):
    B, EA, EP = fm
    hexw = (FF_SL + 3) // 4
    lines = ["// GENERATED by tools/s81_link/gen_kp4_linear.py -- KP4 encoder LA = 2 + FF FOLD (opt-in, ot_s81_kp4_enc_la",
             "// #(.LA(2), .FF(1), .FOLD(1))).  Per 65-bit window slice s of cq[o / 75] and parity bit o:",
             "//   fb = XOR under AP & P, fa = XOR under AP & ~P (even chunk), fo = XOR under P & ~AP (odd chunk);",
             "//   fp[s][o] = fb ^ (ev ? fa : fo), so wb = A w_k on even chunks and w_k on odd chunks.",
             "// Self-checked against the LA = 2 recurrence and tools/s81_link/rs544.py.  Include inside g_ff after the declarations."]
    for nm, ms in (("fb", B), ("fa", EA), ("fo", EP)):
        for s in range(8):
            for o in range(300):
                lines.append(f"assign {nm}[{s}][{o}] = ^(cq[{o // 75}][{FF_SL * s} +: {FF_SL}] & {FF_SL}'h{ms[s][o]:0{hexw}x});")
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / "rtl/dsrom_sys/s81_link"
    ce = matrix(enc_cycle, enc_unpack, 820)
    cs = matrix(syn_cycle, syn_unpack, 850)
    selfcheck(ce, cs)
    me, ms = masks(ce, 300), masks(cs, 300)
    selfcheck_split(me, ms)
    ea, (e0, e1) = split(me, 520, CUTS[520])
    sa, (s0, s1) = split(ms, 550, CUTS[550])
    emit_split(out / "ot_s81_kp4_enc_mat.svh",
               "KP4 encoder: 52-symbol LFSR advance = e_ar (rem_q[299:0]) ^ e_p0 (ch_q[259:0]) ^ e_p1 (ch_q[519:260])",
               [("e_ar", "rem_q", 300, ea), ("e_p0", "ch_q[259:0]", 260, e0), ("e_p1", "ch_q[519:260]", 260, e1)])
    emit_split(out / "ot_s81_kp4_syn_mat.svh",
               "KP4 decoder: 55-symbol syndrome advance = s_ar (S_q[299:0]) ^ s_p0 (sc_q[274:0]) ^ s_p1 (sc_q[549:275])",
               [("s_ar", "S_q", 300, sa), ("s_p0", "sc_q[274:0]", 275, s0), ("s_p1", "sc_q[549:275]", 275, s1)])
    fan = lambda L: max(bin(m).count("1") for m in L)
    print(f"GEN_KP4_LINEAR PASS selfcheck=24 split_check=48 max_fanin enc A={fan(ea)} P={fan(e0)},{fan(e1)} "
          f"syn A={fan(sa)} P={fan(s0)},{fan(s1)}")
    ga2, gaw = selfcheck_la2(me)
    # the LA = 2 table belongs to the HBM-only ot_s81_kp4_enc_la (the S81/HEAD files above stay as they are)
    la2_out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent.parent / "rtl/hbm_accel/cores_split/reform_1104b"
    emit_la2(la2_out / "ot_s81_kp4_enc_la2_mat.svh", ga2, gaw)
    print(f"GEN_KP4_LINEAR LA2 PASS selfcheck=24 groups={LA2_G} max_fanin A2 part={max(fan(g) for g in ga2)} "
          f"A part={max(fan(g) for g in gaw)} rows A2 total={sum(bin(m).count('1') for g in ga2 for m in g)} "
          f"A total={sum(bin(m).count('1') for g in gaw for m in g)}")
    fm = fold_masks(me)
    selfcheck_fold(me, ga2, fm)
    emit_fold(la2_out / "ot_s81_kp4_enc_ffa_mat.svh", fm)
    tot = lambda L: sum(bin(m).count("1") for g in L for m in g)
    print(f"GEN_KP4_LINEAR FOLD PASS selfcheck=24 terms B={tot(fm[0])} EA={tot(fm[1])} EP={tot(fm[2])} "
          f"(FF P alone={sum(bin(m).count('1') for m in me) - sum(bin(m >> 520).count('1') for m in me)})")


if __name__ == "__main__":
    main()
