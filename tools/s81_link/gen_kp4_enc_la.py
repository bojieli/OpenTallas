#!/usr/bin/env python3
"""DIE-S81-85 TX-ENC-LA 2026-11-09: evaluation-domain (syndrome-basis) form of the S81 KP4 encoder state loop.

The RTL encoder (ot_s81_kp4_enc.sv) advances its 300-bit LFSR remainder one 52-symbol chunk a cycle,
    R_k = A R_(k-1) ^ W ch_k            (A: 300 x 300, rows up to 173 inputs; W = [P0 P1]: 520 -> 300)
and the one-cycle A R loop is the TX tile's TT setup path (-169 ps).  A is the matrix of r(x) -> r(x) x^52 mod g(x)
and g(x) = prod_{j=0..29} (x - alpha^j), so the evaluation map
    Q : r -> ( r(alpha^0), ..., r(alpha^29) )          (300 x 300, invertible: Vandermonde)
diagonalises it over GF(2^10):  Q A = D Q  with  D = diag_j( multiply by alpha^(52 j) )  -- 30 constant GF(2^10)
multipliers, i.e. a BLOCK-DIAGONAL GF(2) matrix of 10 x 10 blocks (rows <= 10 inputs).  In the state S = Q R:
    S_k = D S_(k-1) ^ (Q W) ch_k,        parity R_9 = Q^-1 S_9
The loop keeps the f0 mask (S_(-1) = 0 at chunk 0) and is a <= 10-input XOR + 1 XOR with the registered window
part; the dense 300 x 300 work (Q^-1) moves OUT of the loop, into one registered stage of four 75-column partials
read once per frame by the PMA word-9 select.  The window matrices become Q P0 / Q P1 (same shape, same density
class as P0 / P1).  Everything is derived by evaluating the existing RTL step (gen_kp4_linear.enc_cycle) on basis
vectors; Q A = D Q, the window products and Q^-1 are self-checked, and the full frame parity is checked against
tools/s81_link/rs544.py.

    python3 tools/s81_link/gen_kp4_enc_la.py [OUTDIR]     (default rtl/dsrom_sys/s81_link)
writes OUTDIR/ot_s81_kp4_enc_la_mat.svh (e_ar = D rem_q, e_p0 / e_p1 = Q P, e_pi0..3 = rem_tx order rows of Q^-1 over the kept state copy rem_s)
and OUTDIR/ot_s81_kp4_enc_la_mat_q4.svh (split_kp4_window.py enc of the former).  Bench mutants (gen-time):
    MUTPOW=1 writes ..._la_mat_mut.svh with D built from alpha^(51 j) (wrong matrix power) for the FAIL check.
"""
import os
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rs544 as R  # noqa: E402
import gen_kp4_linear as L  # noqa: E402

NP, N = 30, 300
NG = 4                       # Q^-1 column groups (75 S bits each) = registered partials e_pi0..3


def popc(x):
    return bin(x).count("1")


def mat_from_cols(cols):
    """columns (int over N out bits) -> row masks"""
    return [sum(1 << b for b, c in enumerate(cols) if (c >> o) & 1) for o in range(N)]


def apply_rows(rows, v):
    return sum((popc(m & v) & 1) << o for o, m in enumerate(rows))


def eval_vec(rem_bits, exp_of_sym):
    """S_j = sum_i lr[i] alpha^(j * e(i)); rem_bits packs lr[i] at 10 i"""
    lr = [(rem_bits >> (10 * i)) & 0x3FF for i in range(NP)]
    out = 0
    for j in range(NP):
        s = 0
        for i in range(NP):
            if lr[i]:
                s ^= R.gmul(lr[i], R.gpow(R.EXP[1], (j * exp_of_sym(i)) % 1023))
        out |= s << (10 * j)
    return out


def d_apply(S, pw):
    return sum(R.gmul((S >> (10 * j)) & 0x3FF, R.gpow(R.EXP[1], (pw * j) % 1023)) << (10 * j) for j in range(NP))


def gf2_inv(rows):
    """invert an N x N GF(2) matrix given as row masks"""
    a = [(rows[i], 1 << i) for i in range(N)]
    for c in range(N):
        p = next(r for r in range(c, N) if (a[r][0] >> c) & 1)
        a[c], a[p] = a[p], a[c]
        for r in range(N):
            if r != c and (a[r][0] >> c) & 1:
                a[r] = (a[r][0] ^ a[c][0], a[r][1] ^ a[c][1])
    return [a[i][1] for i in range(N)]


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / "rtl/dsrom_sys/s81_link"
    ce = L.matrix(L.enc_cycle, L.enc_unpack, 820)          # columns over lin_in = {rem (520+), window (0..519)}
    acol, pcol = ce[520:820], ce[0:520]
    # Q: lr[i] is the coefficient of x^(29 - i) (lr[0] = feedback end)
    e = lambda i: NP - 1 - i
    qcol = [eval_vec(1 << b, e) for b in range(N)]
    qrows = mat_from_cols(qcol)
    # Q A = D Q on every basis vector
    for b in range(N):
        assert apply_rows(qrows, acol[b]) == d_apply(qcol[b], 52), "Q A != D Q (basis %d)" % b
    pw = int(os.environ.get("MUTPOW", "0")) and 51 or 52
    dcol = [d_apply(1 << b, pw) for b in range(N)]
    drows = mat_from_cols(dcol)
    qpcol = [apply_rows(qrows, c) for c in pcol]
    qprows = mat_from_cols(qpcol)
    qinv = gf2_inv(qrows)
    for _ in range(16):
        v = random.getrandbits(N)
        assert apply_rows(qinv, apply_rows(qrows, v)) == v, "Q^-1 Q != I"
    # par rows in rem_tx order: rem_tx[299 - 10 g - u] = R[10 g + 9 - u]
    prow = [0] * N
    for g in range(NP):
        for u in range(10):
            prow[299 - 10 * g - u] = qinv[10 * g + 9 - u]
    # frame check vs rs544: S loop with the masked chunk 0, parity = Q^-1 S_9
    rng = random.Random(85)
    for _ in range(12):
        msg = [rng.randrange(1024) for _ in range(R.K)]
        cw = R.encode(msg)
        sy = [0] * 6 + msg
        S = 0
        for c in range(10):
            w = sum(s << (510 - 10 * k) for k, s in enumerate(sy[52 * c: 52 * (c + 1)]))
            S = (0 if c == 0 else apply_rows(drows, S)) ^ apply_rows(qprows, w)
        rem = apply_rows(qinv, S)
        if pw == 52:
            assert [(rem >> (10 * i)) & 0x3FF for i in range(NP)] == cw[R.K:], "LA parity != rs544.encode"
    suffix = "_mut" if pw != 52 else ""
    lines = ["// GENERATED by tools/s81_link/gen_kp4_enc_la.py (DIE-S81-85 11-09) -- do not edit.",
             "// OT_S81_KP4_ENC_LA evaluation-domain encoder: state rem_q = S = Q R (S_j = R(alpha^j), 30 x 10 b);",
             "// e_ar = D rem_q (block diagonal, S_j * alpha^(%d j), rows <= 10 inputs); e_p0 / e_p1 = Q P0 / Q P1 window;" % pw,
             "// e_pi0..3 = rem_tx-ordered rows of Q^-1 over rem_s[75 g +: 75] (rem_s = kept copy of rem_q; parity = e_pi0 ^ .. ^ e_pi3,",
             "// one register).",
             "// Self-checked: Q A = D Q on all 300 basis vectors, Q^-1 Q = I, frame parity == tools/s81_link/rs544.py."]
    for o in range(N):
        lines.append("assign e_ar[%d] = ^(rem_q & 300'h%075x);" % (o, drows[o]))
    for o in range(N):
        lines.append("assign e_p0[%d] = ^(ch_q[259:0] & 260'h%065x);" % (o, qprows[o] & ((1 << 260) - 1)))
    for o in range(N):
        lines.append("assign e_p1[%d] = ^(ch_q[519:260] & 260'h%065x);" % (o, qprows[o] >> 260))
    for g in range(NG):
        for o in range(N):
            m = (prow[o] >> (75 * g)) & ((1 << 75) - 1)
            rhs = "1'b0" if m == 0 else "^(rem_s[%d:%d] & 75'h%019x)" % (75 * g + 74, 75 * g, m)
            lines.append("assign e_pi%d[%d] = %s;" % (g, o, rhs))
    path = out / ("ot_s81_kp4_enc_la_mat%s.svh" % suffix)
    path.write_text("\n".join(lines) + "\n")
    subprocess.run([sys.executable, "-I", str(HERE / "split_kp4_window.py"), "enc", str(path),
                    str(out / ("ot_s81_kp4_enc_la_mat%s_q4.svh" % suffix))], check=True)
    fan = lambda rows: (max(map(popc, rows)), sum(map(popc, rows)))
    old_a, old_p = mat_from_cols(acol), mat_from_cols(pcol)
    pi_g = [[(r >> (75 * g)) & ((1 << 75) - 1) for r in prow] for g in range(NG)]
    print("GEN_KP4_ENC_LA PASS pow=%d QA=DQ(300) QinvQ=I frames=12 | loop: old A max/total=%s new D=%s | "
          "window: old P=%s new QP=%s | out Qinv=%s partial max=%d"
          % (pw, fan(old_a), fan(drows), fan(old_p), fan(qprows), fan(qinv), max(max(map(popc, p)) for p in pi_g)))
    # A^2 density for the comparison with the LA = 2 look-ahead form
    a2 = [apply_rows(old_a, c) for c in acol]
    print("A^2 rows max/total=%s" % (fan(mat_from_cols(a2)),))


if __name__ == "__main__":
    main()
