#!/usr/bin/env python3
"""HBM-NEXT-UNITS-SUDMA 2026-10-19: N-row SU.VOP record on the WHOLE static SU (ot_hbm_su_static_top, d4g RTL unchanged)
behind the row-relative command stage ot_hnx_su_rowx (rtl/hbm_next/su/).

    su_rows_compile.py OUT --n N [--nv 14] [--op AB|ABC] [--absolute] [--lat 1]

One SU.VOP record of N rows (verify positions), n = 512 x nv FP32 elements a row (nv = 14: DS h = 7,168):
  AB   O_r = A_r * B           (B broadcast: rs_B = 0, e.g. a norm gain; A, O per row)
  ABC  O_r = bf16(A_r * B + C_r)  (A, C, O per row; B broadcast) = su_arith_compile AB_AD_C_BF16
Schedule (static, compiler-fixed, every edge known; collision = assert here, FAULT in the RTL):
  c1 head: B fill (2 nv edges), prologue fill of row 0, the op's ld edge; period p = 0 .. N-1 (length II): the fills of
  row p + 1 (2 nv edges per per-row operand: 32 VM read ports = 64 sectors = one 512-word vector every 2 edges), then
  row p's nv vector emits timed so their store result writes (emit + 23) follow the fill writes (cmd + 11) with GUARD
  edges; drains (vmw reads, 2 edges a vector) at EM(r, 0) + 23 + MARGIN + 2 j.
  II = (2 k + 1) nv + 2 GUARD, k = per-row VM operands: each store bank has ONE write port shared by fill and lane
  result (both on one edge = FAULT st_conflict in ot_hbm_su_static_pgslice), so the store write port bounds the row.
Row-relative image (default): every command is row 0's; the per-edge row code (rowc.mem) names the row of the vmr, vmw and
control classes and ot_hnx_su_rowx adds row x stride (VM sector, store row, control vb) per operand. --absolute: the
unrolled d4g image (absolute addresses, row codes 0) -> must give the SAME expected files (the d4g SU runs it unchanged).
--wsplit 1 (HBM-NEXT-UNITS-SUDMA2, needs ot_hnx_su_top with wsplit = 1): split store write phase. The fill writes the
HI = 0 store groups on even bank-write edges and HI = 1 on odd ones (fill command e -> bank write e + FW, FW = 12, from
the ab_n4_g0 witness); a vector's lane write W = emit + 23 is put on a fill-HI0 edge, HI = 1 banks commit at W, HI = 0
banks (deferred one edge by ot_hnx_su_wsplit) at W + 1, on a fill-HI1 edge. Vectors emit every 2nd edge, the row fill
streams with no gap: II = 2 k nv (+ 2 --sguard). --fw 11 = the schedule-parity witness (must FAULT st_conflict).
Golden: hdc_golden mul / add / bf16 RNE in NumPy, independent of the DUT (su_arith_compile seed rows = VM rows).
Outputs: prog.mem (4 x 2422 b a line), rowc.mem (4 x 20 b), strides.mem, expw/exps/explw.mem, arith/seed.mem,
programme.json (cycles(N), II, dictionary sizes per 256-b column for the row-relative and the absolute image).
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_static')); sys.path.insert(0, str(ROOT / 'tools'))
import su_arith_compile as SAC  # noqa: E402
from hdc_golden import add, mul  # noqa: E402

QW = 1742 + 240 + 312 + 54 + 74
FO_EM = 23                  # emit -> store write (FO - 8, su_top_compile defaults MLAT 3 ALAT 3 LEAF 0 PIN_REG 0)
MARGIN = 16                 # store write -> drain read (compiler margin, not a measured minimum)
VM_A, VM_C, VM_B, VM_O, VM_RS = 0, 120, 230, 300, 16     # VM rows of row 0 / broadcast, VM row stride per row
ST_A, ST_C, ST_O, ST_B, ST_D = 0, 128, 256, 384, 448      # store rows (row r at + r nv: stays in its 128-row frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--n', type=int, required=True); ap.add_argument('--nv', type=int, default=14)
    ap.add_argument('--op', choices=('AB', 'ABC'), default='AB'); ap.add_argument('--absolute', action='store_true')
    ap.add_argument('--lat', type=int, default=1, help='edges of the rowx stage (REG 1)')
    ap.add_argument('--guard', type=int, default=1, help='edges between fill and lane-result store writes')
    ap.add_argument('--wsplit', type=int, default=0, help='1: split store write phase (ot_hnx_su_top wsplit = 1)')
    ap.add_argument('--fw', type=int, default=12, help='fill command -> bank write edge offset (11 = parity witness)')
    ap.add_argument('--sguard', type=int, default=0, help='wsplit: extra edge pairs a period')
    a = ap.parse_args()
    N, nv, L = a.n, a.nv, a.lat
    assert 1 <= N <= 16 and N * nv <= 128 - 0 and VM_O + VM_RS * (N - 1) + nv <= 512 and VM_A + VM_RS * (N - 1) + nv <= VM_C
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/hbm_static/su_arith_compile.py'), str(out / 'arith')], check=True,
                   stdout=subprocess.DEVNULL)
    seed = np.array([int(x, 16) for x in (out / 'arith/seed.mem').read_text().split()], dtype=np.uint32)
    data = seed.view(np.float32).reshape(512, 512)
    rowops = ['A'] + (['C'] if a.op == 'ABC' else [])
    k, g = len(rowops), a.guard
    # store write port (ONE per bank: fill > lane result, both on one edge = FAULT st_conflict): fill cmd e writes at
    # e + 11, emit m writes its result at m + 23 -> period p: fills of row p + 1 then the results of row p, disjoint
    II = (2 * k + 1) * nv + 2 * g if not a.wsplit else 2 * k * nv + 2 * a.sguard
    T = lambda p: 2 * nv + (p + 1) * II           # period p = -1 .. N - 1 (p = -1: prologue fill of row 0)
    FR = [T(r - 1) for r in range(N)]
    if a.wsplit:
        # lane write W = emit + 23 on a fill-HI0 bank-write edge: W = T + FW (mod 2); first emit >= last fill cmd + 25
        def em0(r):
            b = T(r) + 24
            return b + ((b + 23 - T(r) - a.fw) % 2)
        EM = [[em0(r) + 2 * j for j in range(nv)] for r in range(N)]
        for r in range(1, N):
            assert EM[r][0] > EM[r - 1][-1], 'emit slots overlap'
    else:
        EM = [[T(r) + 2 * k * nv + g - 12 + j for j in range(nv)] for r in range(N)]
    for r in range(N):
        assert EM[r][0] >= FR[r] + 2 * k * nv - 1 + 25, 'row data not in the store before its first emit'
    S = EM[0][0] - 8
    DR = [[EM[r][0] + FO_EM + MARGIN + 2 * j for j in range(nv)] for r in range(N)]
    NE = DR[-1][-1] + 2 + 8
    ctl = [[0] * 4 for _ in range(NE)]; vmr = [[0] * 4 for _ in range(NE)]; vmw = [[0] * 4 for _ in range(NE)]
    rc = [[0] * 4 for _ in range(NE)]
    expw, lw = [], np.zeros((NE + L + 1, 4), dtype=np.int64)
    rel = not a.absolute

    def put(arr, e, q, sh, w, val):
        assert 0 <= val < 1 << w
        assert (arr[e][q] >> sh) & ((1 << w) - 1) == 0, ('slot busy', e, q, sh)
        arr[e][q] |= val << sh

    def setrc(e, q, sh, w, val):
        cur = (rc[e][q] >> sh) & ((1 << w) - 1)
        assert cur in (0, val), ('row code clash', e, q, sh, cur, val)
        rc[e][q] |= val << sh

    # read operand classes: sel 0 A, 1 B, 2 C (ROWX order A B C D I); strides in sectors / store rows
    def fill(e, vm_row, st_row, sel, r):
        for hi in range(2):
            for q in range(4):
                for p in range(8):
                    vr, sr = (vm_row - VM_RS * r, st_row - nv * r) if rel else (vm_row, st_row)
                    put(vmr, e + hi, q, p * 30, 30, (1 << 29) | ((q << 13) | (vr << 4) | (hi << 3) | p) << 13
                        | (p + 8 * hi) << 9 | sr)
                if rel:
                    setrc(e + hi, q, 0, 4, r); setrc(e + hi, q, 4, 3, sel)
    for j in range(nv):
        fill(2 * j, VM_B + j, ST_B + j, 1, 0)
    for r in range(N):
        for k, op in enumerate(rowops):
            for j in range(nv):
                if op == 'A':
                    fill(FR[r] + 2 * nv * k + 2 * j, VM_A + VM_RS * r + j, ST_A + nv * r + j, 0, r)
                else:
                    fill(FR[r] + 2 * nv * k + 2 * j, VM_C + VM_RS * r + j, ST_C + nv * r + j, 2, r)
    # control: su_arith_compile op words; ld once at S; vector (r, j) emits at EM(r, j)
    mods = dict(cp_m1=1, cm_m1=1) if a.op == 'AB' else dict(cp_m1=1, cm_m1=1, ca_ad=2, co_rnd=1)
    base = dict(no=1, ni=8192, ls=7, lvw=7, dst=1, co_dst=1, cp_imm1=0x3fa00000, cm_imm1=0x3fa00000,
                ce_imm1=0x3fa00000, ca_imm2=0x3ec00000, cs_imm2=0x3ec00000, cx_imm3=0x3f400000, **mods)
    terms = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) for k in range(7))
    pw = SAC.physical_word

    def word(q, r, j, emit, ld):
        rr = 0 if rel else r
        vb = [pw(q, ST_A + nv * rr + j), pw(q, ST_B + j), pw(q, ST_C + nv * rr + j), pw(q, ST_D + j), pw(q, ST_O + nv * rr + j)]
        return SAC.pack(dict(base, ld=ld, ld_c=terms, emit=emit, i_v=j * 128, vb=sum(v << (24 * s) for s, v in enumerate(vb))))
    em = {EM[r][j]: (r, j) for r in range(N) for j in range(nv)}
    for e in range(S, DR[-1][-1] + 2):
        r, j = em.get(e, (0, 0))
        for q in range(4):
            ctl[e][q] = word(q, r, j, int(e in em), int(e == S))
            if rel and e in em:
                setrc(e, q, 16, 4, r)
        if e in em:
            lw[e + FO_EM + L][:] = 128
    # golden
    A = lambda r, j: data[VM_A + VM_RS * r + j]
    C = lambda r, j: data[VM_C + VM_RS * r + j]
    B = lambda j: data[VM_B + j]
    for r in range(N):
        for j in range(nv):
            x = mul(A(r, j), B(j))
            if a.op == 'ABC':
                x = add(x, C(r, j)); bits = x.view(np.uint32); bits = (bits + 0x7fff + ((bits >> 16) & 1)) & 0xffff0000
            else:
                bits = x.view(np.uint32)
            vr = VM_O + VM_RS * r + j
            for hi in range(2):
                e = DR[r][j] + hi
                for q in range(4):
                    for p in range(8):
                        g = p + 8 * hi
                        sec = (q << 13) | (vr << 4) | (hi << 3) | p
                        vs, ss = ((q << 13) | ((vr - VM_RS * r) << 4) | (hi << 3) | p, ST_O + j) if rel else (sec, ST_O + nv * r + j)
                        put(vmw, e, q, p * 39, 39, (1 << 38) | (g << 33) | (ss << 24) | (vs << 8) | 0xff)
                        if rel:
                            setrc(e, q, 8, 4, r); setrc(e, q, 12, 1, 0)
                        expw.append((e + 4 + L, q, p, sec, 0xff, [int(bits[128 * q + 8 * g + k]) for k in range(8)]))
    # files
    with open(out / 'prog.mem', 'w') as f:
        for e in range(NE):
            v = 0
            for q in range(4):
                v |= ((((ctl[e][q] << 240 | vmr[e][q]) << 312 | vmw[e][q]) << 54) << 74) << (q * QW)
            f.write(f'{v:0{QW}x}\n')
    # SUDMA2: the row code as programme column bits: per quarter a 2442-b line {rc20, line2422} (prog_rc.mem, 4 x 2442
    # = 9768 b, quarter q at q x 2442, for su_programme_compile --line-bits 9768 --partition 4); prog_rc0.mem = rc zeroed
    QR = QW + 20
    for nm, use in (('prog_rc.mem', 1), ('prog_rc0.mem', 0)):
        with open(out / nm, 'w') as f:
            for e in range(NE):
                v = 0
                for q in range(4):
                    lq = (((ctl[e][q] << 240 | vmr[e][q]) << 312 | vmw[e][q]) << 54) << 74
                    v |= (lq | (rc[e][q] << QW if use else 0)) << (q * QR)
                f.write(f'{v:0{(4 * QR + 3) // 4}x}\n')
    (out / 'rowc.mem').write_text(''.join(''.join(f'{rc[e][q]:05x}' for q in (3, 2, 1, 0)) + '\n' for e in range(NE)))
    # strides (rowx ports): r_ss A,B,C,D,I (16 b sectors) | r_sr (9 b rows) | w_ss O,R | w_sr | c_vb A,B,C,D,O (24 b)
    rs_sec = [VM_RS << 4, 0, VM_RS << 4, 0, 0] if rel else [0] * 5
    rs_row = [nv, 0, nv, 0, 0] if rel else [0] * 5
    ws_sec = [VM_RS << 4, 0] if rel else [0, 0]
    ws_row = [nv, 0] if rel else [0, 0]
    cvb = [nv << 7, 0, nv << 7, 0, nv << 7] if rel else [0] * 5
    sv = 0; sh = 0
    for vals, w in ((rs_sec, 16), (rs_row, 9), (ws_sec, 16), (ws_row, 9), (cvb, 24)):
        for x in vals:
            sv |= (x & ((1 << w) - 1)) << sh; sh += w
    (out / 'strides.mem').write_text(f'{sv:0{(sh + 3) // 4}x}\n')
    expw.sort(key=lambda x: (x[0], x[1], x[2]))
    with open(out / 'expw.mem', 'w') as f:
        for e, q, p, sec, mask, words in expw:
            dd = 0
            for k, w in enumerate(words): dd |= (w & 0xffffffff) << (32 * k)
            f.write(f'{e:08x}{q:01x}{p:01x}{sec:04x}{mask:02x}{dd:064x}\n')
    (out / 'exps.mem').write_text('0' * 32 + '\n')
    with open(out / 'explw.mem', 'w') as f:
        for e in range(NE + L + 1): f.write(''.join(f'{int(lw[e][q]):02x}' for q in (3, 2, 1, 0)) + '\n')
    # dictionary sizes per 256-b column of the 2422-b quarter word (distinct words over all edges and quarters)
    cols = (QW + 255) // 256
    dic = [set() for _ in range(cols)]
    for e in range(NE):
        for q in range(4):
            w = ((((ctl[e][q] << 240 | vmr[e][q]) << 312 | vmw[e][q]) << 54) << 74)
            for c in range(cols):
                dic[c].add((w >> (256 * c)) & ((1 << 256) - 1))
    # SUDMA2: the row code as a PROGRAMME COLUMN: the 20-b rc rides the spare top bits of column 9 (2422 + 20 = 2442 <=
    # 10 x 256: no new column, no new macro, pslice SB 2422 -> 2442); dictionary words a column with rc included
    dic_rc = [set() for _ in range(cols)]
    for e in range(NE):
        for q in range(4):
            w = ((((ctl[e][q] << 240 | vmr[e][q]) << 312 | vmw[e][q]) << 54) << 74) | rc[e][q] << QW
            for c in range(cols):
                dic_rc[c].add((w >> (256 * c)) & ((1 << 256) - 1))
    first_cmd = 0
    last_w = max(x[0] for x in expw)
    man = dict(schema='opentallas.hbm_next.su_rows.v1', n=N, nv=nv, op=a.op, row_relative=rel, lat=L, edges=NE,
               wsplit=a.wsplit, fw=a.fw,
               ii=II, c1_rule='2 nv B fill + II row-0 fill + 16 + nv emits + 23 + MARGIN + 2 nv drain', row_ops=rowops,
               fr=FR, ld_edge=S, first_emit=EM[0][0], last_drain=DR[-1][-1], first_cmd_edge=first_cmd,
               last_vm_write_edge=last_w, cycles=last_w - first_cmd + 1 - L, expected_vm_writes=len(expw),
               expected_scalars=0, dict_words_per_col=[len(d) for d in dic],
               dict_words_per_col_rc_in_col9=[len(d) for d in dic_rc],
               d4g_pslice_q4_dict_capacity=[128 * b for b in (3, 10, 9, 13, 2, 1, 1, 1, 1, 1)],
               golden='hdc_golden mul/add NumPy FP32 RNE (+ bf16 RNE for ABC), independent of the DUT')
    (out / 'programme.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'NE={NE} NW={len(expw)} NS=0 II={II} cycles={man["cycles"]}')


if __name__ == '__main__':
    main()
