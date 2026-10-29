#!/usr/bin/env python3
"""TOKSIM-HBM-su fork A (10-19): production-shape SU.VOP record programmes for the WHOLE static SU bench
(tb_toksim_su_top = tb_hbm_su_static_top with runtime counts).  One programme = ONE record measured in isolation:

  [setup]  (only for records whose B operand is a broadcast scalar, VM desc ibcast=1): the scalar(s) the PRODUCER record
           left in the RF -- filled from VM, copied by lane 0..k-1 (BYP issue), loaded + exported by the reducer to RF
           words; NOT counted (it is the previous record's product).
  DISPATCH = first FILL command of the record.
  FILL     every VM operand row (store row = VM row) through the 32 SU-station VM ports (port p fills store groups p, p+8),
           one sector per port per edge, only the sectors holding live elements; ahead of the issue that needs them.
  ISSUE    one control line per serial edge (ld once, 8 edges before the first emit, inside the fill window); light ops
           on all 128 lanes/quarter, SFU-lane ops (exp / sigmoid / SiLU / divider) on lanes 0..31/quarter (lvw 5);
           element e of the record = issue e // (4L), quarter (e % 4L) // L, lane e % L.
  DRAIN    every output row back through the VM ports (LG samples E+4), as soon as its lane writes committed.
  REDUCE   (R descriptor) as BUILT on the bound die (no pre-tree module in die.v): the reducer takes ONE lane output per
           quarter per edge (red_sel lane at the output edge), so each issue is re-emitted once per live lane (dst only
           on the first); 10 interleaved accumulation chains + pairwise tree per quarter, export to RF, then reducer 0
           combines the quarter roots (((q0+q1)+q2)+q3) through its RF replica (stree, L_TREE 32), exports the record's
           R word(s) and the RF sector is drained to VM (slice 0 port 0, src 1).
  RETIRE   = last LG write sampled (E+4) + WR (write done; WR = the bridge's serial done edge SWD in the multirate
           profiles).  cycles_serial = RETIRE - DISPATCH; stream (833 ps) = x 4/3.
Edge rules = the RTL headers (pgslice FILL commit E+RR+3; lane write = emit + 28 (MLAT 4, ALAT 3, LEAF 1) + SFU depth;
reducer issue E+2, scalar E+11, commit / dependent distance 10; RF word readable >= export + 13 + L_RF).
Golden: independent NumPy (hdc_golden add/mul/to_bf16/exp, IEEE float32 division) in the calendar's order.
usage: prod_compile.py OUT RECORD_NAME --rr RR --wr WR [--pretree [--qpr 0|1|2|4]]     (records: see RECS)

PRETREE (HBM-PRETREE2 10-20, --pretree; the bench build must be PRETREE=1): reductions go through the closed HH-6
reducer pre-tree (pgslice ot_hbm_su_red_pretree_s x16 + qcore ot_hbm_su_red_pretree_j) instead of one lane operand per
quarter per edge, and their result is the MODEL's reduction, not the calendar's:
  * order = the models' R-ARITH chunk8 csum (hdc_golden_v41.csum: DeepSeek-V4.1 HDC_V41_ARITH=chunk8 norms / softmax
    denominators / Engram dots; tools/qwen_r25_golden.py RMSNorm csum8(x*x), softmax Z = csum8_p(e_p), m = max_p s_p);
    max = the reducer's ordered max with canonical +0 (order-free).  Every exported value is asserted equal to
    hdc_golden_v41.csum / the ordered max over the record row's element vector (independent of the lowering).
  * placement: a row is cut into QPR quarter runs of SW = NCp*8/QPR words (NCp = csum's padded chunk count), each run
    an aligned csum subtree; run j -> quarter (row group)*QPR + j; an issue carries block k (L words, aligned) of every
    run (QPR 1: rows round-robin over the quarters).  Emission order per row: groups of <= DEP block pairs, even blocks
    first, odd blocks >= DEP edges after their partner (so the odd block's ADD_EXT meets its partner's LOAD at the
    reducer's same-address distance).
  * per emission at edge e: tree_cmd (tree.mem, su_pretree_lower.tree_cmd_word, cnt = live lanes) at E = e + LAT,
    reducer LOAD / ADD_EXT|MAX_EXT {osel 1, lane 0x20} at E + PT_RED (80); in-quarter pairwise ADD_TREE|MAX_TREE over the
    pair nodes (odd node carried up = csum's +0 padding); quarter roots exported to RF and joined ((Q0+Q1)+(Q2+Q3)) on
    the row group's first reducer; final export -> RF word 128+row -> RF sector drain (as before).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/hbm_static')); sys.path.insert(0, str(ROOT / 'tools'))
from su_arith_compile import pack, physical_word  # noqa: E402
import su_pretree_lower as SPL  # noqa: E402  (closed HH-6 pre-tree: tree_cmd_word, block_subtree, PT_RED)
from hdc_golden import add, mul, to_bf16, exp, neg, z, rsqrt  # noqa: E402
F = np.float32
import su_lane_build as SLB  # noqa: E402  (HBM-CORES-REBAL-9: lane build depths, one place)
MLAT, ALAT, LEAF = 4, 3, 1                                # as built; --mlat (REBAL-9 opt-in MLAT 5)
WCOPY = 0                                                 # --wcopy 1: pinned-bank write copy, every bank write commits +1
LIN = SLB.lin(MLAT, ALAT, LEAF)                           # emit -> lane write (= su_top_compile FO - 8) = 28 (HBM-SUFIX: was +4 = 32)
FPIN = 2                                                  # fill: bank pins sample E+RR+2 (pgslice fd/fr_v), commit E+RR+3
HOLD = 16                                                 # HBM-SUFIX: record fields held on non-emit lines past the last lane write
RLAT, DEP, NCH, LRF, RFL = 9, 10, 10, 1, 32              # reducer; RF_LOCAL 1; L_TREE 32 (stree)
QW = 1742 + 240 + 312 + 54 + 74
def u32(x): return int(np.float32(x).view(np.uint32))
def f32(u): return np.uint32(u).view(np.float32)


SIDE_FN = (2, 3, 6, 7)          # rsqrt, sqrt, sqrt(softplus), Engram gate: global lane 0 (KIND 2) side pipe only


def sfu_depth(m):
    s = SLB.depths(MLAT, ALAT)[m.get('ci_sfu', 0)]          # lane H_* insertion depths (ot_hbm_su_static_lane D_*)
    return s + (SLB.div_extra(MLAT) if m.get('cp_m1') in (4, 5) else 0)


# Records: name -> (design, shape key from census, N per row, rows, roles {role: 'vm'|'rf'}, mods, red)
# roles: A/B/C/D VM vectors of N*rows elements; 'rf' = broadcast scalar per row (ibcast).  red: None | 'sum' | 'max'.
IMM_SCALE = 0x3d351e13            # an attention scale-like immediate (exact value immaterial to timing)
RECS = {
 # ---------------- DS AR
 'ds_res_copy': ('ds_ar', 20480, 1, dict(A='vm'), dict(), None, True),
 'ds_moe_sum0': ('ds_ar', 53, 1, dict(A='vm', C='vm'), dict(ca_ad=4, cs_e1=2), None, True),
 'ds_moe_sum2': ('ds_ar', 53, 1, dict(A='vm', C='vm', D='vm'), dict(ca_ad=5, cs_e1=2), None, True),
 'ds_q_norm_y': ('ds_ar', 1280, 1, dict(A='vm', B='rf', C='vm'), dict(cp_m1=1, cm_m1=1, cs_e1=1, co_rnd=1), None, True),
 'ds_kv_norm_y': ('ds_ar', 512, 1, dict(A='vm', B='rf', C='vm'), dict(cp_m1=1, cm_m1=1, cs_e1=1, co_rnd=1), None, True),
 'ds_scores_bias': ('ds_ar', 384, 1, dict(A='vm', C='vm'), dict(ca_ad=2), None, True),
 'ds_bf16_p640': ('ds_ar', 640, 1, dict(A='vm'), dict(co_rnd=1), None, True),
 'ds_bf16_p128': ('ds_ar', 128, 1, dict(A='vm'), dict(co_rnd=1), None, True),
 'ds_attend_norm': ('ds_ar', 512, 1, dict(A='vm', B='rf'), dict(cp_m1=4, cm_m1=4, co_rnd=1), None, True),
 'ds_route_weights': ('ds_ar', 6, 1, dict(A='vm', B='rf'), dict(cp_m1=4, cm_m1=4, cs_e1=3, cs_imm2=0x3fc00000), None, True),
 'ds_w_scale': ('ds_ar', 32, 1, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=0x3c800000, cm_imm1=0x3c800000, co_rnd=1), None, True),
 'ds_attend_den': ('ds_ar', 1, 1, dict(A='vm', B='vm', C='vm'), dict(ca_ad=3, ci_sfu=1, cs_sfu=1, cs_e1=2), None, True),
 'ds_q_norm_ss': ('ds_ar', 1280, 1, dict(A='vm'), dict(cp_m1=2, cm_m1=2), 'sum', False),
 'ds_kv_norm_ss': ('ds_ar', 512, 1, dict(A='vm'), dict(cp_m1=2, cm_m1=2), 'sum', False),
 'ds_route_total': ('ds_ar', 6, 1, dict(A='vm'), dict(), 'sum', False),
 'ds_attend_max640': ('ds_ar', 640, 1, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE), 'max', False),
 'ds_attend_exp_sum640': ('ds_ar', 640, 1, dict(A='vm', B='rf'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE, ca_ad=3, ci_sfu=1, cs_sfu=1), 'sum', True),
 'ds_attend_max128': ('ds_ar', 128, 1, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE), 'max', False),
 'ds_attend_exp_sum128': ('ds_ar', 128, 1, dict(A='vm', B='rf'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE, ca_ad=3, ci_sfu=1, cs_sfu=1), 'sum', True),
 'ds_swiglu': ('ds_ar', 24, 7, dict(A='vm', B='rf', C='vm'), dict(cx_amin=1, cx_cclip=1, cx_imm3=0x41200000, ci_sfu=5, cs_sfu=5, cs_e1=1, ce_e2=1, co_rnd=1), None, True),
 'ds_rs': ('ds_ar', 1, 1, dict(A='vm'), dict(cp_m1=5, cm_m1=5, cp_imm1=0x44a00000, cm_imm1=0x44a00000, ca_ad=4, ca_imm2=0x1e3ce508, cs_imm2=0x1e3ce508, ci_sfu=2, cs_sfu=2), None, True),
 'ds_spsqrt4': ('ds_ar', 4, 1, dict(A='vm'), dict(ci_sfu=6, cs_sfu=6), None, True),
 'ds_engram_gate': ('ds_ar', 4, 1, dict(A='vm', B='vm'), dict(cp_m1=1, cm_m1=1), None, True),
 # ---------------- Qwen AR
 'qw_bf16_p': ('qwen', 8192, 8, dict(A='vm'), dict(co_rnd=1), None, True),
 'qw_row_scale_res': ('qwen', 4096, 1, dict(A='vm', B='vm', C='vm'), dict(cp_m1=1, cm_m1=1, ca_ad=2), None, True),
 'qw_row_scale_gu': ('qwen', 6144, 1, dict(A='vm', B='vm'), dict(cp_m1=1, cm_m1=1), None, True),
 'qw_row_scale_qkv': ('qwen', 1536, 1, dict(A='vm', B='vm'), dict(cp_m1=1, cm_m1=1), None, True),
 'qw_round_q': ('qwen', 1024, 1, dict(A='vm'), dict(co_rnd=1), None, True),
 'qw_pv_normalize': ('qwen', 128, 8, dict(A='vm', B='rf'), dict(cp_m1=4, cm_m1=4), None, True),
 'qw_softmax_max': ('qwen', 8192, 8, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE), 'max', False),
 # small production-sized points of the reduction law (same record class, fewer rows)
 'qw_softmax_exp_sum_r1': ('qwen', 8192, 1, dict(A='vm', B='rf'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE, ca_ad=3, ci_sfu=1, cs_sfu=1), 'sum', True),
 'qw_softmax_max_r1': ('qwen', 8192, 1, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE), 'max', False),
 # HBM-PRETREE2: 2/3-row exp_sum points (the 8-row record needs 1,024 store rows on 32 SFU lanes/quarter > 512)
 'qw_softmax_exp_sum_r2': ('qwen', 8192, 2, dict(A='vm', B='rf'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE, ca_ad=3, ci_sfu=1, cs_sfu=1), 'sum', True),
 'qw_softmax_exp_sum_r3': ('qwen', 8192, 3, dict(A='vm', B='rf'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE, ca_ad=3, ci_sfu=1, cs_sfu=1), 'sum', True),
 # HBM-COLLFUSE: Qwen TP-8 die shapes (Geometry(tp=8): nq = 4 q heads, nk = 1 KV head a die); the census TP-4 programme
 # carried nq = 8.  exp_sum at 4 rows needs 2 x 256 store rows (> 500): affine law from the measured 1-row record.
 'qw8_softmax_max': ('qwen', 8192, 4, dict(A='vm'), dict(cp_m1=3, cm_m1=3, cp_imm1=IMM_SCALE, cm_imm1=IMM_SCALE), 'max', False),
 'qw8_bf16_p': ('qwen', 8192, 4, dict(A='vm'), dict(co_rnd=1), None, True),
 'qw8_pv_normalize': ('qwen', 128, 4, dict(A='vm', B='rf'), dict(cp_m1=4, cm_m1=4), None, True),
 'qw8_round_q': ('qwen', 512, 1, dict(A='vm'), dict(co_rnd=1), None, True),
 'qw8_row_scale_qkv': ('qwen', 768, 1, dict(A='vm', B='vm'), dict(cp_m1=1, cm_m1=1), None, True),
}
ROW_OF = dict(A=0, B=1, C=2, D=3, O=4)


def golden(mods, a, b, c, d):
    x = a.copy()
    imm3 = f32(mods.get('cx_imm3', 0))
    if mods.get('cx_arnd'): x = to_bf16(x)
    if mods.get('cx_arelu'): x = np.where(np.signbit(x), F(0), x).astype(F)
    if mods.get('cx_amin'): x = np.minimum(x, imm3).astype(F)
    if mods.get('cx_cclip'): c = np.clip(c, -imm3, imm3).astype(F)
    m = mods.get('cp_m1', 0)
    imm1 = f32(mods.get('cp_imm1', 0)); imm2 = f32(mods.get('cs_imm2', mods.get('ca_imm2', 0)))
    if m == 1: x = mul(x, b)
    elif m == 2: x = mul(x, x)
    elif m == 3: x = mul(x, imm1)
    elif m == 4:
        with np.errstate(all='ignore'): x = z(np.asarray(x, F) / np.asarray(b, F))
    elif m == 5:
        with np.errstate(all='ignore'): x = z(np.asarray(x, F) / imm1)
    elif m == 6: x = np.maximum(x, b).astype(F)
    ad = mods.get('ca_ad', 0)
    if ad == 2: x = add(x, c)
    elif ad == 3: x = add(x, neg(b))
    elif ad == 4: x = add(x, f32(mods.get('ca_imm2', 0)))
    elif ad == 5: x = add(x, d)
    sf = mods.get('ci_sfu', 0)
    if sf == 1: x = exp(x)
    elif sf == 2: x = rsqrt(x)
    elif sf == 6:
        import hdc_golden_v41 as G41
        x = G41.sqrt(G41.softplus(x))
    elif sf in (4, 5):
        den = add(exp(neg(x)), F(1.0))
        with np.errstate(all='ignore'): x = z(np.asarray(x if sf == 5 else np.full_like(x, F(1.0)), F) / np.asarray(den, F))
    e1 = mods.get('cs_e1', 0)
    if e1 == 1: x = mul(x, c)
    elif e1 == 2: x = add(x, c)
    elif e1 == 3: x = mul(x, imm2)
    elif e1 == 4: x = add(x, imm2)
    e2 = mods.get('ce_e2', 0)
    if e2 == 1: x = mul(x, b)
    elif e2 == 2: x = mul(x, f32(mods.get('ce_imm1', 0)))
    bits_ = np.asarray(x, F).view(np.uint32).astype(np.uint64)
    if mods.get('co_rnd'): bits_ = ((bits_ + 0x7fff + ((bits_ >> 16) & 1)) & 0xffff0000)
    return bits_.astype(np.uint32)


def fmax_u(a, b):
    fa, fb = f32(a), f32(b)
    r = a if (fa > fb or (fa == fb and not (a >> 31))) else b
    return 0 if (r & 0x7fffffff) == 0 else r


class Prog:
    def __init__(s, n):
        s.n = n
        s.ctl = [[0] * 4 for _ in range(n)]; s.vmr = [[0] * 4 for _ in range(n)]; s.vmw = [[0] * 4 for _ in range(n)]
        s.rf = [[0] * 4 for _ in range(n)]; s.red = [[0] * 4 for _ in range(n)]
        s.expw, s.exps = [], []; s.lw = np.zeros((n, 4), dtype=np.int64)
        s.bankw = set()                                    # (edge, q, bank) write-port use (fill pins / lane write)
        s.tree = [[0] * 4 for _ in range(n)]               # PRETREE: per edge, per quarter 4 x 12-b slice tree commands

    def put(s, arr, e, q, sh, w, val):
        assert 0 <= val < 1 << w and 0 <= e < s.n
        assert (arr[e][q] >> sh) & ((1 << w) - 1) == 0, ('slot busy', e, q, sh)
        arr[e][q] |= val << sh

    def free(s, arr, e, q, sh, w): return (arr[e][q] >> sh) & ((1 << w) - 1) == 0

    def write(s, out, seed):
        (out / 'arith').mkdir(parents=True, exist_ok=True)
        (out / 'arith/seed.mem').write_text('\n'.join(f'{x:08x}' for x in seed.view(np.uint32).ravel()) + '\n')
        with open(out / 'prog.mem', 'w') as f:
            for e in range(s.n):
                v = 0
                for q in range(4):
                    qv = ((((s.ctl[e][q] << 240 | s.vmr[e][q]) << 312 | s.vmw[e][q]) << 54 | s.rf[e][q]) << 74) | s.red[e][q]
                    v |= qv << (q * QW)
                f.write(f'{v:0{4 * QW // 4}x}\n')
        s.expw.sort(key=lambda x: (x[0], x[1], x[2]))
        with open(out / 'expw.mem', 'w') as f:
            for e, q, p, sec, mask, words in s.expw:
                data = 0
                for k, w in enumerate(words): data |= (int(w) & 0xffffffff) << (32 * k)
                f.write(f'{e:08x}{q:01x}{p:01x}{sec:04x}{mask:02x}{data:064x}\n')
        s.exps.sort()
        with open(out / 'exps.mem', 'w') as f:
            for e, q, tag, val in s.exps: f.write(f'{e:08x}{q:08x}{tag:08x}{val:08x}\n')
        with open(out / 'explw.mem', 'w') as f:
            for e in range(s.n): f.write(''.join(f'{int(s.lw[e][q]):02x}' for q in (3, 2, 1, 0)) + '\n')


def model_reduce(kind, vals_u):
    """the MODEL's reduction of one row (independent of the lowering): R-ARITH csum8 / ordered canonical max"""
    import hdc_golden_v41 as G41
    w = np.asarray(vals_u, dtype=np.uint32)
    if kind == 'sum':
        return u32(G41.csum(w.view(np.float32)))
    r = int(w[0])
    for v in w[1:]: r = fmax_u(r, int(v))
    return fmax_u(r, r)


def reduce_pretree(P, a, red, emits, live, EI, N, ROWS, QPR, NGRP, NBQ, PERM, LAT, gold):
    """PRETREE lowering (see the module docstring); returns rinfo (+ '_last_lg')"""
    mx = 1 if red == 'max' else 0
    comb = fmax_u if mx else (lambda x, y: u32(add(f32(x), f32(y))))
    op_ext, op_tree = (3, 5) if mx else (1, 2)
    PTR = SPL.PT_RED
    blk = {}                                             # (row, q, k) -> (consume edge, value)
    for (e, g, j) in emits:
        E = e + LAT
        s_, t_ = divmod(g, NBQ); k = PERM[t_]
        for q in range(4):
            cnt = int(live[g, q])
            if cnt == 0: continue
            ids = [EI(g, q, b) for b in range(cnt)]
            row = ids[0] // N
            words = [int(gold[i]) for i in ids]
            assert P.tree[E][q] == 0, ('tree slot busy', E, q)
            P.tree[E][q] = SPL.tree_cmd_word(mx, cnt)
            blk[(row, q, k)] = (E + PTR, SPL.block_subtree(red, words, cnt))
    addr_next = {q: 0 for q in range(4)}
    def new_addr(q):
        x = addr_next[q]; addr_next[q] += 1; assert x < 1000, 'reducer addresses'; return x
    roots = {}
    rows_q = sorted(set((r, q) for (r, q, k) in blk))
    # level 0: pair (2i, 2i+1) of each quarter run -> LOAD + ADD_EXT (odd >= DEP after its partner)
    nodes = {}
    for (r, q) in rows_q:
        ks = sorted(k for (rr, qq, k) in blk if rr == r and qq == q)
        assert ks == list(range(len(ks))), ('blocks not contiguous', r, q, ks)
        lv = []
        for i in range(0, len(ks), 2):
            ce, v = blk[(r, q, ks[i])]
            d = new_addr(q)
            P.put(P.red, ce, q, 0, 74, (1 << 73) | (0 << 70) | (d << 40) | (1 << 7) | 0x20)
            ready = ce + DEP
            if i + 1 < len(ks):
                co, vo = blk[(r, q, ks[i + 1])]
                assert co >= ce + DEP, ('pair spacing', r, q, ks[i], ce, co)
                P.put(P.red, co, q, 0, 74, (1 << 73) | (op_ext << 70) | (d << 60) | (d << 40) | (1 << 7) | 0x20)
                v = comb(v, vo); ready = co + DEP
            lv.append((d, ready, v))
        nodes[(r, q)] = lv
    # in-quarter pairwise tree (free reducer slots), odd node carried up; export the quarter root
    for (r, q) in rows_q:
        lv = nodes[(r, q)]; last = 0
        while len(lv) > 1:
            nl = []
            for i in range(0, len(lv) - 1, 2):
                (xa, ra, va), (xb, rb, vb) = lv[i], lv[i + 1]
                e = max(ra, rb, last + 1)
                while not P.free(P.red, e, q, 0, 74): e += 1
                last = e; d = new_addr(q)
                P.put(P.red, e, q, 0, 74, (1 << 73) | (op_tree << 70) | (xa << 60) | (xb << 50) | (d << 40))
                nl.append((d, e + DEP, comb(va, vb)))
            if len(lv) % 2: nl.append(lv[-1])
            lv = nl
        roots[(r, q)] = lv[0]
    finals = {}
    for r in sorted(set(r for r, _ in rows_q)):
        qs = sorted(q for (rr, q) in rows_q if rr == r)
        qb = qs[0]
        assert qb % QPR == 0 and all(q // QPR == qb // QPR for q in qs), ('row quarters', r, qs)
        wfin = 128 + r; tagf = 0x100 | wfin
        if len(qs) == 1:
            d, rdy, v = roots[(r, qb)]
            e = rdy
            while not P.free(P.red, e, qb, 0, 74): e += 1
            P.put(P.red, e, qb, 0, 74, (1 << 73) | (4 << 70) | (d << 60) | (tagf << 8))
            P.exps.append((e + RLAT + 3, qb, tagf, v)); finals[r] = (wfin, e + RLAT + 4 + RFL, v)
            continue
        # quarter roots -> RF words, then ((Q0+Q1)+(Q2+Q3)) on reducer qb through RF class 4
        rw = {}
        for q in qs:
            d, rdy, v = roots[(r, q)]
            e = rdy
            while not P.free(P.red, e, q, 0, 74): e += 1
            w = 8 + (r * 4 + q) % 112; tag = 0x100 | w
            P.put(P.red, e, q, 0, 74, (1 << 73) | (4 << 70) | (d << 60) | (tag << 8))
            P.exps.append((e + RLAT + 3, q, tag, v)); rw[q] = (w, e + RLAT + 4 + RFL, v)
        def rfop(e0, op, aa, dd, w):
            ee = e0
            while not (P.free(P.red, ee, qb, 0, 74) and P.free(P.rf, ee - 2, qb, 4 * 9, 9)): ee += 1
            P.put(P.rf, ee - 2, qb, 4 * 9, 9, (1 << 8) | w)
            P.put(P.red, ee, qb, 0, 74, (1 << 73) | (op << 70) | (aa << 60) | (dd << 40) | (1 << 7))
            return ee
        halves = []
        for h in range(0, len(qs), 2):
            pq = qs[h:h + 2]
            d = new_addr(qb)
            w0, r0, v0 = rw[pq[0]]
            e0 = rfop(r0 + 2, 0, 0, d, w0); rdy = e0 + DEP; v = v0
            if len(pq) == 2:
                w1, r1, v1 = rw[pq[1]]
                e1 = rfop(max(r1 + 2, e0 + DEP), op_ext, d, d, w1); rdy = e1 + DEP; v = comb(v, v1)
            halves.append((d, rdy, v))
        if len(halves) == 2:
            (xa, ra, va), (xb, rb, vb) = halves
            e = max(ra, rb)
            while not P.free(P.red, e, qb, 0, 74): e += 1
            d = new_addr(qb)
            P.put(P.red, e, qb, 0, 74, (1 << 73) | (op_tree << 70) | (xa << 60) | (xb << 50) | (d << 40))
            halves = [(d, e + DEP, comb(va, vb))]
        d, rdy, v = halves[0]
        e = rdy
        while not P.free(P.red, e, qb, 0, 74): e += 1
        P.put(P.red, e, qb, 0, 74, (1 << 73) | (4 << 70) | (d << 60) | (tagf << 8))
        P.exps.append((e + RLAT + 3, qb, tagf, v)); finals[r] = (wfin, e + RLAT + 4 + RFL, v)
    # the MODEL check: every row's lowered value == csum8 / ordered max of the row (independent reference)
    for r, (w, rdy, v) in finals.items():
        ref = model_reduce(red, gold[r * N:(r + 1) * N])
        assert v == ref, ('pre-tree lowering != model reduction', r, hex(v), hex(ref))
    # RF sector drains of words 128.. (sector 16 + row//8), as the as-built path
    last_lg = 0
    for sec_i in sorted(set(w // 8 for w, _, _ in finals.values())):
        ws = {w: v for w, rdy, v in finals.values() if w // 8 == sec_i}
        rdy = max(rr for w, rr, v in finals.values() if w // 8 == sec_i)
        e = rdy + a.rfd_slack
        while not (P.free(P.vmw, e + 1, 0, 0, 39) and P.free(P.rf, e - LRF, 0, 5 * 9, 9)): e += 1
        P.put(P.rf, e - LRF, 0, 5 * 9, 9, (1 << 8) | (8 * sec_i))
        mask = 0; words = []
        for k in range(8):
            w = 8 * sec_i + k
            if w in ws: mask |= 1 << k; words.append(ws[w])
            else: words.append(0)
        sec = (0 << 13) | (498 << 4)
        P.put(P.vmw, e + 1, 0, 0, 39, (1 << 38) | (1 << 37) | (sec << 8) | mask)
        P.expw.append((e + 1 + 4, 0, 0, sec, mask, words))
        last_lg = max(last_lg, e + 1 + 4)
    return dict(rows=len(finals), finals={str(r): f'{v[2]:08x}' for r, v in finals.items()},
                model_check='PASS (hdc_golden_v41.csum chunk8 / ordered canonical max == lowered tree, every row)',
                _last_lg=last_lg)


# Exact TP8 four-head records; use the same model-order lowering and storage admission.
for _name, _base in [('qw_softmax_max_r4','qw_softmax_max'),('qw_softmax_exp_sum_r4','qw_softmax_exp_sum_r3')]:
    _r=list(RECS[_base]); _r[2]=4; RECS[_name]=tuple(_r)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('rec')
    ap.add_argument('--rr', type=int, default=12); ap.add_argument('--wr', type=int, default=10)
    ap.add_argument('--fill-slack', type=int, default=1); ap.add_argument('--drain-slack', type=int, default=2)
    ap.add_argument('--side-ii', type=int, default=0)
    ap.add_argument('--rfd-slack', type=int, default=1)  # HBM-SUFIX: class-5 RF drain strictly after RF commit (su_top_compile Z > g_ready)
    ap.add_argument('--pretree', action='store_true')    # HBM-PRETREE2: reductions through the bound pre-tree (build PRETREE=1)
    ap.add_argument('--qpr', type=int, default=0)        # quarters per reduction row: 1/2/4; 0 = try all, keep the fastest
    ap.add_argument('--alat', type=int, default=3)       # explicit physical candidate, default unchanged
    ap.add_argument('--mlat', type=int, default=4)       # HBM-CORES-REBAL-9: lane build (die su / pg_lane* MLAT)
    ap.add_argument('--wcopy', type=int, default=0)      # HBM-CORES-REBAL-9: pinned-bank WCOPY (bank write commit +1)
    a = ap.parse_args()
    global MLAT, ALAT, LIN, WCOPY
    SLB.check(a.mlat, a.alat, LEAF, a.wcopy)
    MLAT, ALAT, WCOPY = a.mlat, a.alat, SLB.commit_extra(a.wcopy)
    LIN = SLB.lin(MLAT, ALAT, LEAF)
    if a.pretree and RECS[a.rec][5] and a.qpr == 0:
        import copy, io, contextlib
        best = None
        for qpr in (1, 2, 4):
            b = copy.copy(a); b.qpr = qpr
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    r = compile_rec(b)
            except AssertionError as ex:
                print(f'qpr {qpr}: not feasible ({ex})', file=sys.stderr); continue
            print(f'qpr {qpr}: cycles_serial {r}', file=sys.stderr)
            if best is None or r < best[0]: best = (r, qpr)
        if best is None:
            ap.error("no feasible pre-tree quarter allocation: production record exceeds storage/shape admission")
        a.qpr = best[1]
    compile_rec(a)


def compile_rec(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    design, N, ROWS, roles, mods, red, writes_o = RECS[a.rec]
    RR, WR = a.rr, a.wr
    sfu = bool(mods.get('ci_sfu')) or mods.get('cp_m1') in (4, 5)
    side = mods.get('ci_sfu', 0) in SIDE_FN
    L = 1 if side else (32 if sfu else 128); LV = 0 if side else (5 if sfu else 7)
    NT = N * ROWS
    PT = bool(a.pretree and red)
    if PT:
        assert not side, 'pre-tree reductions need lane issues'
        QPR = a.qpr or 4
        NCp = 1 << max(0, (-(-N // 8) - 1).bit_length())          # csum's padded chunk count
        SW = N if QPR == 1 else NCp * 8 // QPR                      # words per quarter run (aligned csum subtree)
        assert QPR in (1, 2, 4) and (QPR == 1 or (SW >= 8 and SW * QPR >= N)), ('qpr', QPR, N)
        NGRP = 4 // QPR                                            # rows in flight (one per quarter group)
        NBQ = -(-min(SW, N) // L)                                  # blocks (issues) per row slot
        SLOTS = -(-ROWS // NGRP)
        # emission order inside a row slot: groups of <= DEP pairs, evens then odds
        PERM, MINGAP = [], {}
        npairs = -(-NBQ // 2)
        for g0 in range(0, npairs, DEP):
            P_ = min(DEP, npairs - g0)
            ev = [2 * (g0 + i) for i in range(P_)]
            od = [2 * (g0 + i) + 1 for i in range(P_) if 2 * (g0 + i) + 1 < NBQ]
            for k in od: MINGAP[k] = k - 1                         # odd block k waits >= DEP after block k-1
            PERM += ev + od
        assert sorted(PERM) == list(range(NBQ))
    # HBM-SUFIX: a per-row RF broadcast scalar is ONE word per issue, so rows that do not fill whole issues get their
    # own issues (PR); otherwise elements are packed contiguously across issues.
    PR = (not side) and roles.get('B') == 'rf' and ROWS > 1 and N % (4 * L) != 0
    GR = -(-N // (4 * L)) if PR else 0
    G = NT if side else (ROWS * GR if PR else -(-NT // (4 * L)))
    if PT:
        PR = False; G = SLOTS * NBQ
    LAT = LIN + sfu_depth(mods)
    import zlib
    rng = np.random.default_rng(zlib.crc32(a.rec.encode()))
    # seed: 512 store rows x 512 global lanes; finite, divisors away from 0, exp arguments moderate
    seed = (rng.integers(-2000, 2000, size=(512, 512)).astype(F) * F(1 / 1024.)).astype(F)
    seed = np.where(np.abs(seed) < F(1 / 64.), F(0.75), seed).astype(F)
    if mods.get('ci_sfu') == 2: seed = np.abs(seed).astype(F)          # rsqrt argument: a sum of squares
    # Phased production compiler may provide an explicit full external VM seed image.
    if getattr(a, 'seed_override', None) is not None:
        seed = np.asarray(a.seed_override, dtype=F).copy()
        assert seed.shape == (512, 512), ('seed image shape', seed.shape)
    # element placement: element e -> issue g, quarter q, lane b
    def place(e):
        if PT:
            row, i = divmod(e, N); s_, grp = divmod(row, NGRP); j, o = divmod(i, SW) if QPR > 1 else (0, i)
            k, b = divmod(o, L); return s_ * NBQ + PERM.index(k), grp * QPR + j, b
        if side: return e, 0, 0                          # every element on global lane 0 (quarter 0, lane 0)
        if PR:
            row, i = divmod(e, N); k, r = divmod(i, 4 * L); return row * GR + k, r // L, r % L
        g, r = divmod(e, 4 * L); return g, r // L, r % L
    def EI(g, q, b):                                     # element index of (issue, quarter, lane) or None
        if PT:
            s_, t_ = divmod(g, NBQ); grp, j = divmod(q, QPR); row = s_ * NGRP + grp
            o = PERM[t_] * L + b; i = j * SW + o
            return row * N + i if (row < ROWS and b < L and o < SW and i < N) else None
        if side: return g if (q == 0 and b == 0 and g < NT) else None
        if PR:
            row, k = divmod(g, GR); i = k * 4 * L + q * L + b; return row * N + i if i < N else None
        i = g * 4 * L + q * L + b; return i if i < NT else None
    vm_roles = [r for r in 'ABCD' if roles.get(r) == 'vm']
    rows_per = G                                          # store rows per operand (one row per issue)
    base = {}
    nxt = 0
    for r in vm_roles + (['O'] if writes_o else []):
        base[r] = nxt; nxt += rows_per
    assert nxt <= 500, ('store rows', nxt)
    # per-issue live lanes per quarter
    live = np.zeros((G, 4), dtype=np.int64)
    for g in range(G):
        for q in range(4):
            live[g, q] = sum(1 for b in range(L) if EI(g, q, b) is not None)
    # element values
    def elem(role, e):
        g, q, b = place(e); return seed[base[role] + g, q * 128 + b]
    E = np.arange(NT)
    val = {r: np.array([elem(r, e) for e in E], dtype=F) for r in vm_roles}
    # broadcast scalar per row: RF words 200 + row (setup); values from seed row 499
    rf_words = {}
    if 'B' in roles and roles['B'] == 'rf':
        bsc = [seed[499, k] if mods.get('cp_m1') != 4 else F(abs(seed[499, k]) + F(0.5)) for k in range(ROWS)]
        seed[499, :ROWS] = np.array(bsc, dtype=F)
        val['B'] = np.array([bsc[e // N] for e in E], dtype=F)
        for k in range(ROWS): rf_words[k] = 200 + k
    if mods.get('cp_m1') == 4 and roles.get('B') == 'vm':
        pass
    for r in 'ABCD':
        if r not in val: val[r] = np.zeros(NT, dtype=F)
    gold = golden(mods, val['A'], val['B'], val['C'], val['D'])
    # ------------------------------------------------------------ calendar
    NE = 64 + 40 * ROWS + G * (L if red else 1) * 3 + 8 * G + 2000
    P = Prog(NE)
    t = 2
    setup_end = t
    if rf_words:
        # producer-side setup (not counted): fill row 499 (q0 groups), BYP issue on q0 lanes 0..ROWS-1 per scalar,
        # reducer 0 load + export to RF word 200+k
        ngrp = -(-ROWS // 8)
        for j in range(ngrp):
            p, hi = j % 8, j // 8
            P.put(P.vmr, t + hi, 0, p * 30, 30, (1 << 29) | (((0 << 13) | (499 << 4) | (hi << 3) | p) << 13) | ((p + 8 * hi) << 9) | 499)
        commit = t + 1 + RR + 3
        ldc = sum((1 << k) << (24 * (s * 10 + k)) for s in range(5) for k in range(7))
        ld_e = commit - 8 + 8
        f = dict(no=1, ni=ROWS, ls=7, lvw=7, ld_c=ldc, dst=0, co_dst=0,
                 vb=sum(physical_word(0, 499, 0) << (s * 24) for s in range(5)))
        P.ctl[ld_e][0] = pack(dict(f, ld=1))
        em0 = ld_e + 8
        last_exp = 0
        for k in range(ROWS):
            e_em = em0 + k
            P.ctl[e_em][0] = pack(dict(f, emit=1, i_v=0))
            w = e_em + LIN
            P.put(P.red, w, 0, 0, 74, (1 << 73) | (0 << 70) | ((300 + k) << 40) | k)
            ex = w + DEP + ROWS  # after all loads (one red cmd slot per edge)
            ex = max(ex, last_exp + 1); last_exp = ex
            P.put(P.red, ex, 0, 0, 74, (1 << 73) | (4 << 70) | ((300 + k) << 60) | ((0x100 | rf_words[k]) << 8))
            P.exps.append((ex + RLAT + 3, 0, 0x100 | rf_words[k], u32(seed[499, k])))
        hold_to = em0 + ROWS + LIN + HOLD                # HBM-SUFIX: stage fields are read from the live line
        for e in range(ld_e + 1, hold_to):
            if P.ctl[e][0] == 0: P.ctl[e][0] = pack(f)
        setup_end = last_exp + RLAT + 4 + RFL + 2
    # ---- record
    D0 = setup_end + 2                                   # DISPATCH
    # fill: sector list per (issue, role): for each quarter, groups holding live lanes
    fill_ready = {}
    e_f = D0
    vmr_next = D0
    for g in range(G):
        rdy = 0
        for r in vm_roles:
            row = base[r] + g
            for hi in (0, 1):
                any_ = False
                for q in range(4):
                    nl = live[g, q]
                    for p in range(8):
                        j = p + 8 * hi
                        if j * 8 < nl:
                            any_ = True
                if not any_: continue
                e = vmr_next
                while True:
                    ok = all((e + RR + FPIN, q, (p + 8 * hi) * 8 + k) not in P.bankw
                             for q in range(4) for p in range(8) if (p + 8 * hi) * 8 < live[g, q] for k in range(8))
                    if ok: break
                    e += 1
                for q in range(4):
                    for p in range(8):
                        j = p + 8 * hi
                        if j * 8 < live[g, q]:
                            sec = (q << 13) | (row << 4) | (hi << 3) | p
                            P.put(P.vmr, e, q, p * 30, 30, (1 << 29) | (sec << 13) | (j << 9) | row)
                            for k in range(8): P.bankw.add((e + RR + FPIN, q, j * 8 + k))
                vmr_next = e + 1
                rdy = max(rdy, e + RR + 3 + WCOPY)          # bank commit (WCOPY: per-column copy +1)
        fill_ready[g] = rdy
    # issues
    ldc = 0
    for s, role in enumerate('ABCDO'):
        if role == 'B' and roles.get('B') == 'rf': continue
        ldc |= sum((1 << k) << (24 * (s * 10 + k)) for k in range(7))
    srcs = (1 << 2) if roles.get('B') == 'rf' else 0
    first_em = max(fill_ready.get(0, D0) + a.fill_slack, D0 + 8)
    ld_e = first_em - 8
    def _row(g):
        for q in range(4):
            for b in range(L):
                x = EI(g, q, b)
                if x is not None: return x // N
        return 0
    row_of_issue = [_row(g) for g in range(G)]
    def rowq(g, q):                                      # PRETREE: rows differ per quarter group -> per-quarter RF word
        if PT and g < G:
            for b in range(L):
                x = EI(g, q, b)
                if x is not None: return x // N
        return row_of_issue[g] if g < G else 0
    def fields(q, g, emit, dst):
        nl_tot = (G - 1) * L + live[G - 1, q] if G else 0
        vb = 0
        for s, role in enumerate('ABCDO'):
            if role == 'B' and roles.get('B') == 'rf':
                vb |= rf_words[rowq(g, q)] << (s * 24)
            elif role in base:
                vb |= physical_word(q, base[role] + g, 0) << (s * 24)
            else:                                        # HBM-SUFIX: unused stream still reads; keep it in-quarter
                vb |= physical_word(q, base['A'] + g, 0) << (s * 24)
        return dict(mods, no=1, ni=g * L + live[g, q],  # HBM-SUFIX: per-issue liveness bound (partial issues mid-record)
                    ls=7, lvw=LV, ld_c=ldc, srcs=srcs, emit=emit,
                    i_v=g * L, vb=vb, dst=dst, co_dst=dst)
    emits = []                                           # (edge, g, j)
    te = first_em
    reps = L if (red and not PT) else 1
    em_edge = {}                                         # PT: issue -> emission edge (pair spacing)
    # HBM-SUFIX: the SIDE pipe is built at MLAT 3 (ot_hbm_su_static_side localparam) while the bound lane takes its
    # result at its MLAT-4 insertion depth; the side result register is overwritten by the next element first unless
    # side elements are spaced by (lane depth - side depth + 1).  RTL lever: side pipe at the lane's MLAT.
    SII = (a.side_ii if a.side_ii > 0 else SLB.side_ii(mods.get('ci_sfu', 0), MLAT, ALAT)) if side else 1
    prev_row = 0
    for g in range(G):
        rk = tuple(rowq(g, q) for q in range(4)) if PT else row_of_issue[g]
        if roles.get('B') == 'rf' and g > 0 and rk != prev_row:
            te += 8                                      # RF broadcast word changes: window gap
        prev_row = rk
        te = max(te, fill_ready[g] + a.fill_slack)
        if PT:
            s_, t_ = divmod(g, NBQ); k = PERM[t_]
            if k in MINGAP: te = max(te, em_edge[s_ * NBQ + PERM.index(MINGAP[k])] + DEP)
            em_edge[g] = te
        for j in range(reps):
            if red and j >= max(live[g]):
                break
            if writes_o:                                 # HBM-SUFIX: every rep writes (co_dst is a stage field)
                while any((te + LAT, q, b) in P.bankw for q in range(4) for b in range(live[g, q])): te += 1
            emits.append((te, g, j)); te += SII
    last_em = emits[-1][0]
    for q in range(4):
        P.ctl[ld_e][q] = pack(dict(fields(q, 0, 0, 1 if writes_o else 0), ld=1))
    # HBM-SUFIX: the lane takes each stage's op fields from the LIVE control line (ot_hbm_su_static_lane header:
    # 'a lane takes each stage's fields from it'), so the record's fields are held until its last element left OUT.
    for e in range(ld_e + 1, last_em + LAT + HOLD):
        for q in range(4): P.ctl[e][q] = pack(fields(q, 0, 0, 1 if writes_o else 0))
    out_w = {}                                           # issue -> lane write edge
    for (e, g, j) in emits:
        dst = 1 if writes_o else 0
        for q in range(4):
            if live[g, q] == 0: P.ctl[e][q] = pack(fields(q, g, 0, dst)); continue
            P.ctl[e][q] = pack(fields(q, g, 1, dst))
            if dst:
                P.lw[e + LAT][q] = live[g, q]
                for b in range(live[g, q]):
                    assert (e + LAT, q, b) not in P.bankw, ('lane write vs fill pin collision', e + LAT, q, b)
                    P.bankw.add((e + LAT, q, b))
        if dst: out_w[g] = e + LAT
    # RF class-1 broadcast windows (per row)
    if roles.get('B') == 'rf':
        for q in range(4):
            for row in sorted(set(rowq(g, q) for g in range(G))):
                es = [e for (e, g, j) in emits if rowq(g, q) == row]
                for e in range(min(es) - 1 - LRF, max(es) + 6 - LRF):
                    P.put(P.rf, e, q, 1 * 9, 9, (1 << 8) | rf_words[row])
    retire = None; last_lg = 0
    # drains
    if writes_o:
        dnext = 0
        for g in range(G):
            row = base['O'] + g
            for hi in (0, 1):
                if not any((p + 8 * hi) * 8 < live[g, q] for q in range(4) for p in range(8)): continue
                e = max(dnext, out_w[g] + a.drain_slack + WCOPY)   # read after the lane write commits
                for q in range(4):
                    for p in range(8):
                        j = p + 8 * hi
                        nl = live[g, q]
                        if j * 8 >= nl: continue
                        mask = 0
                        words = []
                        for k in range(8):
                            b = j * 8 + k
                            if b < nl:
                                mask |= 1 << k; words.append(int(gold[EI(g, q, b)]))
                            else: words.append(0)
                        sec = (q << 13) | (row << 4) | (hi << 3) | p
                        P.put(P.vmw, e, q, p * 39, 39, (1 << 38) | (0 << 37) | (j << 33) | (row << 24) | (sec << 8) | mask)
                        P.expw.append((e + 4, q, p, sec, mask, words))
                last_lg = max(last_lg, e + 4); dnext = e + 1
    # reductions
    rinfo = {}
    if PT:
        rinfo = reduce_pretree(P, a, red, emits, live, EI, N, ROWS, QPR, NGRP, NBQ, PERM, LAT, gold)
        last_lg = max(last_lg, rinfo.pop('_last_lg'))
    if red and not PT:
        comb = (lambda x, y: u32(add(f32(x), f32(y)))) if red == 'sum' else fmax_u
        op_ext, op_tree = (1, 2) if red == 'sum' else (3, 5)
        vals_u = gold
        # operand stream per quarter: (edge, lane, value, row)
        streams = {q: [] for q in range(4)}
        for (e, g, j) in emits:
            for q in range(4):
                if j < live[g, q]:
                    eidx = EI(g, q, j)
                    streams[q].append((e + LAT, j, int(vals_u[eidx]), eidx // N))
        roots = {}                                      # (row, q) -> (addr, ready, value)
        addr_next = {q: 0 for q in range(4)}
        last_cmd = {q: 0 for q in range(4)}
        for q in range(4):
            byrow = {}
            for it in streams[q]: byrow.setdefault(it[3], []).append(it)
            pend = []
            for row, items in sorted(byrow.items()):
                nch = min(NCH, len(items))
                ab = addr_next[q]; addr_next[q] += 2 * nch + 2
                acc = [None] * nch; ready = {}
                for c, (e, lane, v, _) in enumerate(items):
                    k = c % nch
                    if c < nch:
                        P.put(P.red, e, q, 0, 74, (1 << 73) | (0 << 70) | ((ab + k) << 40) | lane); acc[k] = v
                    else:
                        assert e >= ready[ab + k], ('chain dependency', e, ready[ab + k])
                        P.put(P.red, e, q, 0, 74, (1 << 73) | (op_ext << 70) | ((ab + k) << 60) | ((ab + k) << 40) | lane)
                        acc[k] = comb(acc[k], v)
                    ready[ab + k] = e + DEP; last_cmd[q] = max(last_cmd[q], e)
                pend.append((row, ab, nch, acc, ready))
            # trees (after all accumulation of this quarter; free slots)
            for row, ab, nch, acc, ready in pend:
                vv = {ab + i: acc[i] for i in range(nch)}
                level = [ab + i for i in range(nch)]; na = ab + nch
                while len(level) > 1:
                    nl = []
                    for i in range(0, len(level) - 1, 2):
                        x, y = level[i], level[i + 1]
                        e = max(ready[x], ready[y])
                        while not P.free(P.red, e, q, 0, 74): e += 1
                        P.put(P.red, e, q, 0, 74, (1 << 73) | (op_tree << 70) | (x << 60) | (y << 50) | (na << 40))
                        vv[na] = comb(vv[x], vv[y]); ready[na] = e + DEP; nl.append(na); na += 1
                    if len(level) % 2: nl.append(level[-1])
                    level = nl
                rt = level[0]
                e = ready[rt]
                while not P.free(P.red, e, q, 0, 74): e += 1
                w = 8 + (row * 4 + q) % 192                 # RF word of the quarter root (rows x quarters)
                tag = 0x100 | w
                P.put(P.red, e, q, 0, 74, (1 << 73) | (4 << 70) | (rt << 60) | (tag << 8))
                P.exps.append((e + RLAT + 3, q, tag, vv[rt]))
                roots[(row, q)] = (w, e + RLAT + 4 + RFL, vv[rt])
        # combine on reducer 0 (only quarters holding elements of the row), export, drain RF sector
        finals = {}
        for row in sorted(set(r for r, _ in roots)):
            qs = sorted(q for (r, q) in roots if r == row)
            if len(qs) == 1 and qs[0] == 0 and False:
                pass
            ca = 900 + 4 * row
            e = max(roots[(row, q)][1] for q in qs) + 2
            acc = None
            for i, q in enumerate(qs):
                w, rdy, v = roots[(row, q)]
                ee = max(e, rdy + 2)
                while not (P.free(P.red, ee, 0, 0, 74) and P.free(P.rf, ee - 2, 0, 4 * 9, 9)): ee += 1
                P.put(P.rf, ee - 2, 0, 4 * 9, 9, (1 << 8) | w)
                P.put(P.red, ee, 0, 0, 74, (1 << 73) | ((0 if i == 0 else op_ext) << 70) | (ca << 60) | (ca << 40) | (1 << 7))
                acc = v if i == 0 else comb(acc, v)
                e = ee + DEP
            while not P.free(P.red, e, 0, 0, 74): e += 1
            wfin = 128 + row
            tag = 0x100 | wfin
            P.put(P.red, e, 0, 0, 74, (1 << 73) | (4 << 70) | (ca << 60) | (tag << 8))
            P.exps.append((e + RLAT + 3, 0, tag, acc))
            finals[row] = (wfin, e + RLAT + 4 + RFL, acc)
        # RF sector drains of words 128.. (sector 16 + row//8)
        for sec_i in sorted(set(w // 8 for w, _, _ in finals.values())):
            ws = {w: v for w, rdy, v in finals.values() if w // 8 == sec_i}
            rdy = max(r for w, r, v in finals.values() if w // 8 == sec_i)
            e = max(rdy + a.rfd_slack, last_lg - 3)
            while not (P.free(P.vmw, e + 1, 0, 0, 39) and P.free(P.rf, e - LRF, 0, 5 * 9, 9)): e += 1
            P.put(P.rf, e - LRF, 0, 5 * 9, 9, (1 << 8) | (8 * sec_i))
            mask = 0; words = []
            for k in range(8):
                w = 8 * sec_i + k
                if w in ws: mask |= 1 << k; words.append(ws[w])
                else: words.append(0)
            vrow = 498
            sec = (0 << 13) | (vrow << 4) | (0 << 3) | 0
            P.put(P.vmw, e + 1, 0, 0, 39, (1 << 38) | (1 << 37) | (0 << 33) | (0 << 24) | (sec << 8) | mask)
            P.expw.append((e + 1 + 4, 0, 0, sec, mask, words))
            last_lg = max(last_lg, e + 1 + 4)
        rinfo = dict(rows=len(finals), finals={str(r): f'{v[2]:08x}' for r, v in finals.items()})
    retire = last_lg + WR
    ne = retire + 8
    assert ne < NE
    P.n = ne
    P.ctl = P.ctl[:ne]; P.vmr = P.vmr[:ne]; P.vmw = P.vmw[:ne]; P.rf = P.rf[:ne]; P.red = P.red[:ne]; P.lw = P.lw[:ne]
    P.tree = P.tree[:ne]
    P.write(out, seed)
    if PT:
        with open(out / 'tree.mem', 'w') as f:
            for e in range(ne):
                f.write(''.join(f'{P.tree[e][q]:012x}' for q in (3, 2, 1, 0)) + '\n')
    ser = retire - D0
    man = dict(schema='toksim.hbm.su_vop_record.v1', record=a.rec, design=design, N=N, rows=ROWS, roles=roles,
               mods={k: v for k, v in mods.items()}, red=red, sfu_lanes=sfu, lanes_per_quarter=L, issues=G,
               emissions=len(emits), issue_to_write=LAT, RR=RR, WR=WR, fill_slack=a.fill_slack, drain_slack=a.drain_slack,
               dispatch_edge=D0, first_emit=first_em, last_emit=last_em, last_lg_write=last_lg, retire_edge=retire,
               cycles_serial=ser, cycles_stream_833ps=round(ser * 4 / 3, 2), edges=ne,
               expected_vm_writes=len(P.expw), expected_scalars=len(P.exps), reduction=rinfo,
               golden=('hdc_golden add/mul/to_bf16/exp + NumPy float32 division (independent of the DUT); reduction = the '
                       'MODEL order (hdc_golden_v41.csum chunk8 / ordered canonical max), asserted on the lowered tree') if PT else
                      'hdc_golden add/mul/to_bf16/exp + NumPy float32 division (independent of the DUT), calendar order',
               pretree=dict(on=True, qpr=QPR, quarter_run_words=SW, blocks_per_row=NBQ, pt_red=SPL.PT_RED) if PT else None)
    if (MLAT, ALAT, WCOPY) != (4, 3, 0):
        man['lane_build'] = dict(mlat=MLAT, alat=ALAT, leaf=LEAF, wcopy=WCOPY, lin=LIN, source='tools/hbm_static/su_lane_build.py')
    (out / 'programme.json').write_text(json.dumps(man, indent=1) + '\n')
    print(json.dumps({k: man[k] for k in ('record', 'issues', 'emissions', 'cycles_serial', 'cycles_stream_833ps', 'edges', 'expected_vm_writes', 'expected_scalars')}))
    return ser


if __name__ == '__main__':
    main()
