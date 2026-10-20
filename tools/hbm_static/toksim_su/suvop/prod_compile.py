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
usage: prod_compile.py OUT RECORD_NAME --rr RR --wr WR      (records: see RECS)
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/hbm_static')); sys.path.insert(0, str(ROOT / 'tools'))
from su_arith_compile import pack, physical_word  # noqa: E402
from hdc_golden import add, mul, to_bf16, exp, neg, z, rsqrt  # noqa: E402
F = np.float32
MLAT, ALAT, LEAF = 4, 3, 1
LIN = 23 + 4 * (MLAT - 3) + (ALAT - 3) + LEAF + 4        # emit -> lane write (= su_top_compile FO - 8) = 28
RLAT, DEP, NCH, LRF, RFL = 9, 10, 10, 1, 32              # reducer; RF_LOCAL 1; L_TREE 32 (stree)
QW = 1742 + 240 + 312 + 54 + 74
def u32(x): return int(np.float32(x).view(np.uint32))
def f32(u): return np.uint32(u).view(np.float32)


SIDE_FN = (2, 3, 6, 7)          # rsqrt, sqrt, sqrt(softplus), Engram gate: global lane 0 (KIND 2) side pipe only


def sfu_depth(m):
    d_exp = 7 * MLAT + 8 * ALAT + 4
    s = {0: 0, 1: d_exp, 4: d_exp + ALAT + 19, 5: d_exp + ALAT + 19,
         2: 1 + 9 * MLAT + 3 * ALAT, 3: 31, 6: 180, 7: 111}[m.get('ci_sfu', 0)]   # lane H_* insertion depths (MLAT 4)
    return s + ((19 - MLAT) if m.get('cp_m1') in (4, 5) else 0)


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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('rec')
    ap.add_argument('--rr', type=int, default=12); ap.add_argument('--wr', type=int, default=10)
    ap.add_argument('--fill-slack', type=int, default=1); ap.add_argument('--drain-slack', type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    design, N, ROWS, roles, mods, red, writes_o = RECS[a.rec]
    RR, WR = a.rr, a.wr
    sfu = bool(mods.get('ci_sfu')) or mods.get('cp_m1') in (4, 5)
    side = mods.get('ci_sfu', 0) in SIDE_FN
    L = 1 if side else (32 if sfu else 128); LV = 0 if side else (5 if sfu else 7)
    NT = N * ROWS
    G = NT if side else -(-NT // (4 * L))
    LAT = LIN + sfu_depth(mods)
    import zlib
    rng = np.random.default_rng(zlib.crc32(a.rec.encode()))
    # seed: 512 store rows x 512 global lanes; finite, divisors away from 0, exp arguments moderate
    seed = (rng.integers(-2000, 2000, size=(512, 512)).astype(F) * F(1 / 1024.)).astype(F)
    seed = np.where(np.abs(seed) < F(1 / 64.), F(0.75), seed).astype(F)
    if mods.get('ci_sfu') == 2: seed = np.abs(seed).astype(F)          # rsqrt argument: a sum of squares
    # element placement: element e -> issue g, quarter q, lane b
    def place(e):
        if side: return e, 0, 0                          # every element on global lane 0 (quarter 0, lane 0)
        g, r = divmod(e, 4 * L); return g, r // L, r % L
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
            live[g, q] = (1 if q == 0 else 0) if side else max(0, min(L, NT - g * 4 * L - q * L))
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
        for e in range(ld_e + 1, em0 + ROWS + 2):
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
                    ok = all((e + 1 + RR + 2, q, (p + 8 * hi) * 8 + k) not in P.bankw
                             for q in range(4) for p in range(8) if (p + 8 * hi) * 8 < live[g, q] for k in range(8))
                    if ok: break
                    e += 1
                for q in range(4):
                    for p in range(8):
                        j = p + 8 * hi
                        if j * 8 < live[g, q]:
                            sec = (q << 13) | (row << 4) | (hi << 3) | p
                            P.put(P.vmr, e, q, p * 30, 30, (1 << 29) | (sec << 13) | (j << 9) | row)
                            for k in range(8): P.bankw.add((e + 1 + RR + 2, q, j * 8 + k))
                vmr_next = e + 1
                rdy = max(rdy, e + RR + 3)
        fill_ready[g] = rdy
    # issues
    ldc = 0
    for s, role in enumerate('ABCDO'):
        if role == 'B' and roles.get('B') == 'rf': continue
        ldc |= sum((1 << k) << (24 * (s * 10 + k)) for k in range(7))
    srcs = (1 << 2) if roles.get('B') == 'rf' else 0
    first_em = max(fill_ready.get(0, D0) + a.fill_slack, D0 + 8)
    ld_e = first_em - 8
    def fields(q, g, emit, dst):
        nl_tot = (G - 1) * L + live[G - 1, q] if G else 0
        vb = 0
        for s, role in enumerate('ABCDO'):
            if role == 'B' and roles.get('B') == 'rf':
                vb |= rf_words[((g if side else g * 4 * L)) // N if g < G else 0] << (s * 24)
            elif role in base:
                vb |= physical_word(q, base[role] + g, 0) << (s * 24)
        return dict(mods, no=1, ni=nl_tot if nl_tot else 0, ls=7, lvw=LV, ld_c=ldc, srcs=srcs, emit=emit,
                    i_v=g * L, vb=vb, dst=dst, co_dst=dst)
    emits = []                                           # (edge, g, j)
    te = first_em
    reps = L if red else 1
    row_of_issue = [((g if side else g * 4 * L)) // N for g in range(G)]
    prev_row = 0
    for g in range(G):
        if roles.get('B') == 'rf' and row_of_issue[g] != prev_row:
            te += 8; prev_row = row_of_issue[g]          # RF broadcast word changes: window gap
        te = max(te, fill_ready[g] + a.fill_slack)
        for j in range(reps):
            if red and j >= max(live[g]):
                break
            if writes_o and j == 0:
                while any((te + LAT, q, b) in P.bankw for q in range(4) for b in range(live[g, q])): te += 1
            emits.append((te, g, j)); te += 1
    last_em = emits[-1][0]
    for q in range(4):
        P.ctl[ld_e][q] = pack(dict(fields(q, 0, 0, 1 if writes_o else 0), ld=1))
    for e in range(ld_e + 1, last_em + 1):
        for q in range(4): P.ctl[e][q] = pack(fields(q, 0, 0, 1 if writes_o else 0))
    out_w = {}                                           # issue -> lane write edge
    for (e, g, j) in emits:
        dst = 1 if (writes_o and j == 0) else 0
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
        for row in sorted(set(row_of_issue)):
            es = [e for (e, g, j) in emits if row_of_issue[g] == row]
            for e in range(min(es) - 1 - LRF, max(es) + 6 - LRF):
                for q in range(4): P.put(P.rf, e, q, 1 * 9, 9, (1 << 8) | rf_words[row])
    retire = None; last_lg = 0
    # drains
    if writes_o:
        dnext = 0
        for g in range(G):
            row = base['O'] + g
            for hi in (0, 1):
                if not any((p + 8 * hi) * 8 < live[g, q] for q in range(4) for p in range(8)): continue
                e = max(dnext, out_w[g] + a.drain_slack)
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
                                mask |= 1 << k; words.append(int(gold[g if side else g * 4 * L + q * L + b]))
                            else: words.append(0)
                        sec = (q << 13) | (row << 4) | (hi << 3) | p
                        P.put(P.vmw, e, q, p * 39, 39, (1 << 38) | (0 << 37) | (j << 33) | (row << 24) | (sec << 8) | mask)
                        P.expw.append((e + 4, q, p, sec, mask, words))
                last_lg = max(last_lg, e + 4); dnext = e + 1
    # reductions
    rinfo = {}
    if red:
        comb = (lambda x, y: u32(add(f32(x), f32(y)))) if red == 'sum' else fmax_u
        op_ext, op_tree = (1, 2) if red == 'sum' else (3, 5)
        vals_u = gold
        # operand stream per quarter: (edge, lane, value, row)
        streams = {q: [] for q in range(4)}
        for (e, g, j) in emits:
            for q in range(4):
                if j < live[g, q]:
                    eidx = g if side else g * 4 * L + q * L + j
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
            e = max(rdy, last_lg - 3)
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
    P.write(out, seed)
    ser = retire - D0
    man = dict(schema='toksim.hbm.su_vop_record.v1', record=a.rec, design=design, N=N, rows=ROWS, roles=roles,
               mods={k: v for k, v in mods.items()}, red=red, sfu_lanes=sfu, lanes_per_quarter=L, issues=G,
               emissions=len(emits), issue_to_write=LAT, RR=RR, WR=WR, fill_slack=a.fill_slack, drain_slack=a.drain_slack,
               dispatch_edge=D0, first_emit=first_em, last_emit=last_em, last_lg_write=last_lg, retire_edge=retire,
               cycles_serial=ser, cycles_stream_833ps=round(ser * 4 / 3, 2), edges=ne,
               expected_vm_writes=len(P.expw), expected_scalars=len(P.exps), reduction=rinfo,
               golden='hdc_golden add/mul/to_bf16/exp + NumPy float32 division (independent of the DUT), calendar order')
    (out / 'programme.json').write_text(json.dumps(man, indent=1) + '\n')
    print(json.dumps({k: man[k] for k in ('record', 'issues', 'emissions', 'cycles_serial', 'cycles_stream_833ps', 'edges', 'expected_vm_writes', 'expected_scalars')}))


if __name__ == '__main__':
    main()
