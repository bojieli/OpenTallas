#!/usr/bin/env python3
"""dv_lower_vec: DV slice lowering of the lane-local VECTOR op families of the Qwen compute-die layer programme
(QLB-C4b/3a 10-18, layer-bench gap G-C4, continuation of tools/qwen_layerbench/dv_lower.py).

dv_lower.py lowers the global RMSNorm sum of squares (per-slice SSQ, PSUM tags = golden blocks, fused ROOT r).  This
module lowers, on the same slice map / ownership / VM map, the programme's lane-local vector ops (the q3h programme
results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex, read and checked field by field):

 (1) NORM APPLY + BF16 STREAM.  The programme is NORM-FOLDED (hdc_program norm_fold: the input / post-attention
     RMSNorm gains are folded into the qkv / gate-up weights, CROM cb 'in' / 'post' are reserved and carry no gain;
     the matvec consumes raw X -- PC1 / PC16 me_xbase = X -- and r multiplies the matvec OUTPUT rows: PC3 V, PC4 q/k,
     PC18 gate/up).  So the lowered norm apply is: each slice streams BF16(x) of its owned residual rows (SU window 01,
     the x packer: RNE, 64-element beats, eaddr = global element) to every slice (the column heads tap every x word),
     and `* r` is lowered at the consumers (families 3 and 4).  The DV README's consumer-side h = (x r) g form is NOT
     the programme's arithmetic (a numerics change vs the folded golden) and is not emitted.
     Stream directions: slice 0 (dvs_W5) east only, slices 1..11 both (slice 11's east word leaves at the E5 chain
     end); the schedule makes every (slice, edge) see at most ONE x word (qfd_dv_stream: a pass word and an own word
     in one direction on one edge, or two x words at one slice, is a sticky fault).
 (2) RESIDUAL ADD (PC14 + PC15, PC22 + PC23).  t (the all-reduce return) lands over the AR return chain into each
     slice's T region by compiled PORTS windows (a slice-major AR return calendar: slice 0's owned blocks, then slice
     1's, ...; on / off PORTS edges derived from the RTL: return word at chain edge t is in slice k's pin register at
     t + k, PORTS at entry edge c arms ar_en from c + 2k + 1).  One fused SU op per slice: x <- (t * pscale) + x
     (pscale = CROM lo, the post-TP scale rows the slice owns: PC14's T1 * c then PC15's X + T1 in one pass, IEEE add
     commutes) with the sum of squares chased (red_sq) to the PSUM window (tags = golden block, as dv_lower), fused
     ROOT r on dvs_W5.
 (3) QK-NORM + RoPE on the qkv L9 receiver slices (2t: q heads on slices 0 / 2 / 4 / 6, k on 8, v on 10):
     qr = q * r with SS = csum8(qr^2) (PC4), RS = rsqrt(SS 2^-7 + eps) (PC5), QN = (qr RS) g (PC6, g = CROM lo),
     lo = a cos + b (-sin), hi = b cos + a sin (PC7..10, cos / sin = CROM (lo, hi) of the token's RoPE row): q leaves
     on D2D kind 0, k on D2D kind 1 in FP8 E4M3 (DST_KV), v = v * r on D2D kind 2 in FP8 (PC3).
 (4) SiLU x up (PC18 + PC19) on the gate/up L7 slices (slice s owns gate block s + up block s: hdc_program interleave
     per 128 rows): GU *= r, act = (g sigm(-g)) u -> BF16 stream (the down matvec's x), eaddr = 128 s + i.

Timing constants are MEASURED on the slice2 RTL (rtl/test/qwen_dv/dv_lower_vec_bench.py calibrate, Verilator 5.050)
into results/rtl/qlb_c4b_1018/dv_lower_vec/vec_ages.json; the compiler refuses to schedule without them.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_lower as D  # noqa: E402

ROOT = D.ROOT
AGES_VEC = 'results/rtl/qlb_c4b_1018/dv_lower_vec/vec_ages.json'
PROG = 'results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex'
N, BLOCK = D.NSLICE, D.BLOCK
HD, NQ = 128, 4                                   # head dim, q heads per die (qkv = q 512 | k 128 | v 128)
ROPE_THETA = 1000000.0                            # Qwen3 rope_theta
MA_BYP, MA_AB, MA_AA, MA_AIMM = range(4)
MB_OFF, MB_POS, MB_NEG = range(3)
AD_BYP, AD_Q, AD_C, AD_NEGB, AD_IMM = range(5)
SFU_NONE, SFU_EXP, SFU_RECIP, SFU_RSQRT, SFU_SIGM = range(5)
DST_NONE, DST_VM, DST_KV = range(3)
KV_K, KV_V = 1 << 22, 2 << 22                    # DST_KV address [23:22] = D2D kind (1 K, 2 V)
PIDX = dict(ssq=0, res1=1, res2=2, xs=3, qkr=4, rs=5, qn=6, rlo=7, rhi=8, gur=9, silu=10)
MARGIN = 8                                        # edges between a VM-only producer's measured last write and a reader
LowerError = D.LowerError


def f32(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


# ------------------------------------------------------------------------------------------------ programme check
def isa_vec(prog=PROG):
    """the programme's vector ops this lowering reproduces, fail closed on any field the DV lowering does not keep"""
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_qwen_fullshape_isa_w12 as ISA
    ops = [ISA.decode_instruction(int(w, 16)) for w in (ROOT / prog).read_text().split()]
    su = [(pc, o) for pc, o in enumerate(ops) if o['unit'] == 2]

    def find(name, pred, n=None):
        hit = [(pc, o) for pc, o in su if pred(o)]
        if not hit or (n is not None and len(hit) != n):
            raise LowerError(f'programme: {name} ops {[pc for pc, _ in hit]} (expected {n or ">= 1"})')
        return hit
    ps = find('post-TP scale', lambda o: o['su_nin'] == 4096 and o['c_src'] == 1 and o['mc'] == 1 and o['ma'] == 0
              and o['a_base'] == o['d_base'] and o['red'] == 0, 2)
    res = find('residual add + SSQ', lambda o: o['su_nin'] == 4096 and o['ad'] == AD_C and o['red'] == 1
               and o['red_sq'] == 1, 2)
    for (p1, a), (p2, b) in zip(ps, res):
        if p2 != p1 + 1 or b['c_base'] != a['d_base'] or b['d_base'] != b['a_base']:
            raise LowerError(f'PC{p1}/PC{p2}: not T1 *= pscale; X = X + T1')
    qkr = find('q/k * r + head SSQ', lambda o: o['su_nin'] == HD and o['ma'] == MA_AB and o['red'] == 1
               and o['red_sq'] == 1 and o['su_nout'] == NQ + 1, 1)[0][1]
    v = find('v * r -> KV', lambda o: o['su_nin'] == HD and o['ma'] == MA_AB and o['dst'] == DST_KV
             and o['su_nout'] == 1 and o['b_base'] == qkr['b_base'], 1)[0][1]
    rs = find('head rsqrt', lambda o: o['sfu'] == SFU_RSQRT and o['su_nin'] == NQ + 1, 1)[0][1]
    kh = -math.log2(struct.unpack('<f', struct.pack('<I', rs['imm1']))[0])
    if kh != 7 or rs['ad'] != AD_IMM or rs['ma'] != MA_AIMM:
        raise LowerError('head rsqrt is not rsqrt(SS 2^-7 + eps)')
    qn = find('QK-norm gain', lambda o: o['su_nin'] == HD and o['c_src'] == 1 and o['mc'] == 1 and o['ma'] == MA_AB
              and o['c_so'] == HD, 1)[0][1]
    rope = find('RoPE', lambda o: o['su_nin'] == HD // 2 and o['b_src'] == 1 and o['ad'] == AD_Q
                and o['mb'] in (MB_POS, MB_NEG), 4)
    signs = sorted((o['mb'], o['a_base'] < o['c_base']) for _, o in rope)
    if signs != [(MB_POS, False), (MB_POS, False), (MB_NEG, True), (MB_NEG, True)]:
        raise LowerError(f'RoPE: lo = a cos - b sin / hi = b cos + a sin not found ({signs})')
    gur = find('gate/up * r', lambda o: o['su_nin'] == 3072 and o['ma'] == MA_AB and o['a_base'] == o['d_base'], 1)[0][1]
    silu = find('SiLU x up', lambda o: o['sfu'] == SFU_SIGM, 1)[0][1]
    if (silu['ma'], silu['imm1'], silu['mc'], silu['md'], silu['a_so'], silu['su_nin']) != \
            (MA_AIMM, f32(-1.0), 1, 1, 2 * BLOCK, BLOCK) or silu['b_base'] != silu['a_base'] + BLOCK \
            or silu['c_base'] != silu['a_base']:
        raise LowerError('SiLU op is not act = (g sigm(-g)) u over interleaved 128-row gate/up blocks')
    return dict(post_scale_bases=[o['c_base'] for _, o in ps], post_scale_pcs=[pc for pc, _ in ps],
                residual_pcs=[pc for pc, _ in res], head_k=int(kh), head_eps=rs['imm2'], sigm_imm=silu['imm1'],
                rope_pcs=[pc for pc, _ in rope], norm_fold='qkv / gu matvecs read raw X (PC1 / PC16 me_xbase); '
                'r multiplies V (PC3), q/k (PC4), gate/up (PC18)')


# ------------------------------------------------------------------------------------------------ maps
def vm_map_vec(own):
    vm = dict(D.vm_map(own))
    nres = max(len(b) for b in own['residual']['blocks_per_slice'])
    a = max(r['base'] + r['size'] for r in vm.values())
    for n, size, what in (('T', BLOCK * nres, 'AR landing of t (owned o / down rows, AR calendar order = owned order)'),
                          ('QKV', HD, 'qkv receiver: the head block the L9 station lands (q head / k / v)'),
                          ('SS', 16, 'head sum of squares (reducer window 00)'),
                          ('RS', 16, 'head rsqrt'),
                          ('QN', HD, 'QK-normed head'),
                          ('GU', 2 * BLOCK, 'gate block s (0..127) + up block s (128..255): the L7 station landing')):
        a = (a + 15) // 16 * 16
        vm[n] = dict(base=a, size=size, what=what)
        a += size
    if a > D.VM_EL:
        raise LowerError(f'VM map {a} > {D.VM_EL}')
    return vm


def crom_map(own):
    nres = max(len(b) for b in own['residual']['blocks_per_slice'])
    out, a = {}, 0
    for n, size, what in (('PS1', BLOCK * nres, 'post-TP scale of the o rows the slice owns (residual 1)'),
                          ('PS2', BLOCK * nres, 'post-TP scale of the down rows the slice owns (residual 2)'),
                          ('QG', HD, 'q_norm gain (q receivers)'), ('KG', HD, 'k_norm gain (k receiver)'),
                          ('ROPE', HD // 2, '(cos, sin) of the token position (rewritten per token)')):
        out[n] = dict(base=a, size=size, what=what)
        a += (size + 15) // 16 * 16
    if a > 16384:
        raise LowerError('CROM map overflow')
    return out


def qkv_roles(own):
    """L9 receiver slice of each qkv block: blocks 0..3 = q heads, 4 = k, 5 = v (hdc_program qkv = concat(q, k, v))"""
    out = {}
    for b in own['qkv']['blocks']:
        role = 'q' if b['block'] < NQ else ('k' if b['block'] == NQ else 'v')
        out[b['slice']] = dict(block=b['block'], role=role, head=b['block'] if role == 'q' else 0)
    if sorted(out) != [0, 2, 4, 6, 8, 10]:
        raise LowerError(f'qkv receivers {sorted(out)}')
    return out


def gu_check(own):
    bl = own['gu']['blocks']
    for s in range(N):
        mine = sorted((b['pair'], b['block']) for b in bl if b['slice'] == s)
        if mine != [(0, 2 * s), (1, 2 * s + 1)]:
            raise LowerError(f'gu: slice {s} owns {mine}: not gate block {s} (lower pair) + up block {s} (upper)')


# ------------------------------------------------------------------------------------------------ SU words
def words(s, own, vm, cr, isa, mutant=None):
    bl = own['residual']['blocks_per_slice'][s]
    st = bl[1] - bl[0] if len(bl) > 1 else 0
    n = len(bl)
    roles = qkv_roles(own)
    W = {}
    for name, ps in (('res1', 'PS1'), ('res2', 'PS2')):
        W[name] = D.su_word(nout=n, nin=BLOCK, a=vm['T']['base'], aso=BLOCK, asi=1, bsrc=1, b=cr[ps]['base'], bso=BLOCK,
                            bsi=1, c=vm['X']['base'], cso=BLOCK, csi=1, ma=MA_AB, ad=AD_C, dst=DST_VM,
                            d=vm['X']['base'], dso=BLOCK, dsi=1, red=1, redsq=1, rb=D.W_SC | bl[0], rso=st)
    W['xs'] = D.su_word(nout=n, nin=BLOCK, a=vm['X']['base'], aso=BLOCK, asi=1, dst=DST_VM, d=D.W_X | (BLOCK * bl[0]),
                        dso=BLOCK * st, dsi=1)
    r = roles.get(s)
    if r and r['role'] in 'qk':
        W['qkr'] = D.su_word(nout=1, nin=HD, a=vm['QKV']['base'], asi=1, b=vm['RX']['base'], ma=MA_AB, dst=DST_VM,
                             d=vm['QKV']['base'], dsi=1, red=1, redsq=1, rb=vm['SS']['base'])
        W['rs'] = D.su_word(nout=1, nin=1, a=vm['SS']['base'], ma=MA_AIMM, imm1=f32(2.0 ** -isa['head_k']), ad=AD_IMM,
                            imm2=isa['head_eps'], sfu=SFU_RSQRT, dst=DST_VM, d=vm['RS']['base'])
        W['qn'] = D.su_word(nout=1, nin=HD, a=vm['QKV']['base'], asi=1, b=vm['RS']['base'], ma=MA_AB, csrc=1,
                            c=cr['QG' if r['role'] == 'q' else 'KG']['base'], csi=1, mc=1, dst=DST_VM, d=vm['QN']['base'],
                            dsi=1)
        dst, d = (DST_VM, D.W_D2D | (HD * r['head'])) if r['role'] == 'q' else (DST_KV, KV_K)
        qn, rope = vm['QN']['base'], cr['ROPE']['base']
        lo_mb, hi_mb = (MB_POS, MB_NEG) if mutant == 'ropesign' else (MB_NEG, MB_POS)
        W['rlo'] = D.su_word(nout=1, nin=HD // 2, a=qn, asi=1, bsrc=1, b=rope, bsi=1, ma=MA_AB, c=qn + HD // 2, csi=1,
                             mb=lo_mb, ad=AD_Q, dst=dst, d=d, dsi=1)
        W['rhi'] = D.su_word(nout=1, nin=HD // 2, a=qn + HD // 2, asi=1, bsrc=1, b=rope, bsi=1, ma=MA_AB, c=qn, csi=1,
                             mb=hi_mb, ad=AD_Q, dst=dst, d=d + HD // 2, dsi=1)
    elif r and r['role'] == 'v':
        W['qkr'] = D.su_word(nout=1, nin=HD, a=vm['QKV']['base'], asi=1, b=vm['RX']['base'], ma=MA_AB, dst=DST_KV,
                             d=KV_V, dsi=1)
    gu = vm['GU']['base']
    W['gur'] = D.su_word(nout=1, nin=2 * BLOCK, a=gu, asi=1, b=vm['RX']['base'], ma=MA_AB, dst=DST_VM, d=gu, dsi=1)
    W['silu'] = D.su_word(nout=1, nin=BLOCK, a=gu, asi=1, ma=MA_AIMM, imm1=isa['sigm_imm'], sfu=SFU_SIGM, c=gu, csi=1,
                          mc=1, b=gu + BLOCK, bsi=1, md=1, dst=DST_VM, d=D.W_X | (BLOCK * s), dsi=1)
    return W


def image(s, W, ssq_word):
    img = [0] * (max(PIDX.values()) + 1)
    img[PIDX['ssq']] = ssq_word
    for k, w in W.items():
        img[PIDX[k]] = w
    return img


def crom_table(own, cr, consts):
    """kind-1 stream table words [(dst, eaddr, payload)]: per slice post-scales of its owned rows, the q / k norm
    gains and the token's RoPE row (broadcast dst 15)"""
    import numpy as np
    out = []

    def put(dst, base, lo, hi=None):
        lo = np.asarray(lo, dtype=np.float32)
        hi = np.zeros(len(lo), dtype=np.float32) if hi is None else np.asarray(hi, dtype=np.float32)
        lb, hb = lo.view(np.uint32), hi.view(np.uint32)
        for w in range(0, len(lo), 16):
            pay = 0
            for j in range(min(16, len(lo) - w)):
                pay |= (int(lb[w + j]) | (int(hb[w + j]) << 32)) << (64 * j)
            out.append((dst, (base + w) // 16, pay))
    blocks = own['residual']['blocks_per_slice']
    for key, ps in (('ps1', 'PS1'), ('ps2', 'PS2')):
        if key in consts:
            for s in range(N):
                put(s, cr[ps]['base'], np.concatenate([consts[key][BLOCK * b:BLOCK * (b + 1)] for b in blocks[s]]))
    if 'q_norm' in consts:
        put(15, cr['QG']['base'], consts['q_norm'])
        put(15, cr['KG']['base'], consts['k_norm'])
    if 'pos' in consts:
        sys.path.insert(0, str(ROOT / 'tools'))
        import hdc_golden as G
        cos, sin, half = G.rope_tables(consts['pos'], HD, ROPE_THETA)
        if half != HD // 2:
            raise LowerError('RoPE half != 64')
        put(15, cr['ROPE']['base'], cos, sin)
    return out


# ------------------------------------------------------------------------------------------------ schedule
class Sched:
    """one command an edge at dvs_W5.cmd_wi; occupancy of the downward scalar chain, the x stream (one x word per slice
    per edge) and the outbound D2D chain (one word per W5 edge after the 2-edge hops); SU busy per slice"""

    def __init__(self, smap):
        self.smap, self.arr = smap, smap['cmd_arrival']
        self.cmds, self.occ, self.su_free, self.exp = {}, {}, [0] * N, []

    def keys(self, s, entry, kind, offs):
        out = []
        for j, o in enumerate(offs):
            e = entry + self.arr[s] + o
            if kind == 'psum':
                out += [(('sc', m, e + D.sc_down_edges(self.smap, s, m)), j) for m in range(s, -1, -1)]
            elif kind == 'x':
                out += [(('x', m, e + 2 * abs(m - s)), j) for m in range(N)]
            elif kind == 'd2d':
                out.append((('d', e + 2 * s), j))
        return out

    def cmd(self, edge, c, label):
        if edge in self.cmds:
            raise LowerError(f'two commands on edge {edge}: {self.cmds[edge][1]} / {label}')
        D.decode_cmd(c)
        self.cmds[edge] = (c, label)

    def free_cmd(self, e):
        while e in self.cmds:
            e += 1
        return e

    def place(self, s, c, label, earliest, kind=None, offs=(), span=0, check=True):
        e = max(earliest, self.su_free[s])
        while True:
            e = self.free_cmd(e)
            ks = self.keys(s, e, kind, offs) if kind else []
            if not check or not any(k in self.occ for k, _ in ks):
                break
            e += 1
        for k, j in ks:
            self.occ.setdefault(k, []).append((s, label, j))
        self.cmd(e, c, label)
        self.su_free[s] = e + span + MARGIN
        return e

    def collisions(self):
        return sorted((k, v) for k, v in self.occ.items() if len(v) > 1)

    def commands(self):
        return [dict(edge=e, cmd=f'{c:029x}', label=l) for e, (c, l) in sorted(self.cmds.items())]


def load_ages(path=AGES_VEC):
    p = Path(path) if Path(path).is_absolute() else ROOT / path
    if not p.exists():
        raise LowerError(f'{path} missing: measure it (rtl/test/qwen_dv/dv_lower_vec_bench.py --mode calibrate)')
    a = json.loads(p.read_text())
    for k in ('add_psum_out', 'xs_out', 'silu_out', 'd2d', 'red_vm', 'root_cfg_lead'):
        if k not in a:
            raise LowerError(f'{path}: no {k}')
    return a


def span(ages, op):
    return max(ages['d2d'][op]) if op in ages['d2d'] else 0


def lower_vec(mode, mutant=None, ages=None, consts=None, prog=PROG, ar_order='slice'):
    """mode resid (families 1 + 2), qk (3), silu (4).  Mutants (bench witnesses): resid 'arwin' (PORTS on windows one
    edge early: slice k > 0 also lands the last t word of slice k - 1), 'xslot' (x stream entries without the stream occupancy check); qk 'ropesign' (lo / hi signs swapped);
    silu 'nor' (the gate/up * r op dropped).
    ar_order (QW-CLAYER 10-18): 'slice' = the slice-major AR return calendar (QLB-C4b/3a assumption); 'row' = the
    io_collective message order (word w = 8 b + j, global row order: what qfd_io_collective_static returns and what
    dv_lower_mat's o / down AR messages send): per owned block one PORTS arm (ar_base = T + 128 i) entering t_b - s - 1
    and one disarm entering t_b + 7 - s (t_b = return word 8 b at the dvs_W5 return pin), the stage-0 embedding rule."""
    if mode not in ('resid', 'qk', 'silu'):
        raise LowerError(f'mode {mode}')
    smap, own = D.slice_map(), D.ownership()
    vm, cr = vm_map_vec(own), crom_map(own)
    roles = qkv_roles(own)
    gu_check(own)
    isa_n, isa = D.isa_rmsnorm(prog), isa_vec(prog)
    ages = ages or load_ages()
    consts = consts or {}
    k, eps = isa_n['rsqrt'][0]['k'], isa_n['rsqrt'][0]['eps']
    blocks = own['residual']['blocks_per_slice']
    Wd, img = {}, {}
    for s in range(N):
        bl = blocks[s]
        ssq = D.su_word(nout=len(bl), nin=BLOCK, a=vm['X']['base'], aso=BLOCK, asi=1, red=1, redsq=1,
                        rb=D.W_SC | bl[0], rso=bl[1] - bl[0] if len(bl) > 1 else 0)
        Wd[s] = words(s, own, vm, cr, isa, mutant)
        img[s] = image(s, Wd[s], ssq)
    S = Sched(smap)
    tables = crom_table(own, cr, consts)
    tw = [dict(edge=i, dst=d, eaddr=a, payload=f'{p:0256x}') for i, (d, a, p) in enumerate(tables)]
    t = len(tw) + 2 * N + 8                    # every table word has passed slice 11 before the first op lands
    ar_cal, expect = [], dict(psum={}, x=[], d2d=[])
    if mode == 'resid':
        for s in range(N):                     # ROOT cfg: root dvs_W5, fused r (as dv_lower)
            S.cmd(t + s, D.cmd_root(s, int(s == 0), len(sum(blocks, [])), vm['SSX']['base'], fuse=int(s == 0),
                                    rx=vm['RX']['base'], eps=eps if s == 0 else 0, k=k if s == 0 else 0), f'ROOT s{s}')
        t += N
        for s in range(N):
            S.cmd(t + s, D.cmd_stream(s, 1 if s == 0 else 3, 1), f'STREAM s{s} dirs {1 if s == 0 else 3} tag 1')
        t += N + 2
        # AR return calendar (slice-major owned blocks) + PORTS windows
        r0, land = t + N + 2, {}
        if ar_order not in ('slice', 'row'):
            raise LowerError(f'ar_order {ar_order}')
        if ar_order == 'row':
            owner = {b: (s, i) for s in range(N) for i, b in enumerate(blocks[s])}
            nb = len(owner)
            for b in range(nb):
                s, i = owner[b]
                tb = r0 + 8 * b
                for w in range(BLOCK // 16):
                    ar_cal.append(dict(edge=tb + w, slice=s, block=b, word=w))
                on = tb - s - 1 - (1 if mutant == 'arwin' and s else 0)
                S.cmd(on, D.cmd_ports(s, ar_base=vm['T']['base'] + BLOCK * i, ar_en=1), f'PORTS s{s} AR on (T+{BLOCK * i}) b{b}')
                S.cmd(tb + 7 - s, D.cmd_ports(s, ar_base=vm['T']['base'] + BLOCK * i, ar_en=0), f'PORTS s{s} AR off b{b}')
                land[s] = (min(land.get(s, (tb, 0))[0], tb), tb + 7)
        else:
            tt = r0
            for s in range(N):
                first = tt
                for b in blocks[s]:
                    for w in range(BLOCK // 16):
                        ar_cal.append(dict(edge=tt, slice=s, block=b, word=w))
                        tt += 1
                land[s] = (first, tt - 1)
            for s in range(N):
                first, last = land[s]
                on = first - s - 1 - (1 if mutant == 'arwin' and s else 0)
                S.cmd(on, D.cmd_ports(s, ar_base=vm['T']['base'], ar_en=1), f'PORTS s{s} AR on (T)')
                S.cmd(last - s, D.cmd_ports(s, ar_base=vm['T']['base'], ar_en=0), f'PORTS s{s} AR off')
        # fused residual add + SSQ: after the slice's last t word landed, collision-free scalar chain
        L = ages['add_psum_out']
        ent = {}
        for s in range(N):
            ready = land[s][1] - s + 8
            ent[s] = S.place(s, D.cmd_su(PIDX['res1'], s), f'RES1 s{s} blocks {blocks[s]}', ready, 'psum',
                             L[:len(blocks[s])], span=L[len(blocks[s]) - 1])
            for j, b in enumerate(blocks[s]):
                lv = ent[s] + smap['cmd_arrival'][s] + L[j]
                for m in range(s, 0, -1):
                    expect['psum'][f'{m},{lv + D.sc_down_edges(smap, s, m)}'] = b
        # the x stream of the updated residual (folded norm apply): after the slice's add wrote x
        O = ages['xs_out']
        start = max(ent.values())
        for s in range(N):
            n = len(blocks[s])
            e = S.place(s, D.cmd_su(PIDX['xs'], s), f'XS s{s}', max(start, ent[s] + L[n - 1] + MARGIN), 'x',
                        O[:2 * n], span=O[2 * n - 1], check=mutant != 'xslot')
            for j in range(2 * n):
                b = blocks[s][j // 2]
                expect['x'].append(dict(slice=s, eaddr=BLOCK * b + 64 * (j % 2),
                                        edge_e5=e + smap['cmd_arrival'][s] + O[j] + 2 * (N - 1 - s)))
        expect['root'] = dict(slice=0, k=k, eps=eps)
    elif mode == 'qk':
        recv = sorted(roles)
        a = ages['d2d']
        for s in recv:
            role = roles[s]['role']
            if role == 'v':
                e = S.place(s, D.cmd_su(PIDX['qkr'], s), f'V*r s{s} -> KV fp8', t, 'd2d', a['v'], span=span(ages, 'v'))
                expect['d2d'] += [dict(slice=s, op='v', word=j, edge_w5=e + smap['cmd_arrival'][s] + o + 2 * s)
                                  for j, o in enumerate(a['v'])]
                continue
            e4 = S.place(s, D.cmd_su(PIDX['qkr'], s), f'{role}*r+SS s{s}', t, span=ages['red_vm'])
            e5 = S.place(s, D.cmd_su(PIDX['rs'], s), f'RS s{s}', e4 + ages['red_vm'] + MARGIN, span=span(ages, 'rs'))
            e6 = S.place(s, D.cmd_su(PIDX['qn'], s), f'QN s{s}', e5 + span(ages, 'rs') + MARGIN, span=span(ages, 'qn'))
            op = 'rope_q' if role == 'q' else 'rope_k'
            prev = e6 + span(ages, 'qn') + MARGIN
            for nm in ('rlo', 'rhi'):
                e = S.place(s, D.cmd_su(PIDX[nm], s), f'{nm} s{s} ({role})', prev, 'd2d', a[op], span=span(ages, op))
                expect['d2d'] += [dict(slice=s, op=f'{nm}_{role}', word=j, edge_w5=e + smap['cmd_arrival'][s] + o + 2 * s)
                                  for j, o in enumerate(a[op])]
                prev = e
    else:
        for s in range(N):
            S.cmd(t + s, D.cmd_stream(s, 1 if s == 0 else 3, 3), f'STREAM s{s} dirs {1 if s == 0 else 3} tag 3')
        t += N + 2
        O = ages['silu_out']
        for s in range(N):
            prev = t
            if mutant != 'nor':
                e9 = S.place(s, D.cmd_su(PIDX['gur'], s), f'GU*r s{s}', t, span=span(ages, 'gur'))
                prev = e9 + span(ages, 'gur') + MARGIN
            e = S.place(s, D.cmd_su(PIDX['silu'], s), f'SILU s{s}', prev, 'x', O, span=O[-1])
            for j in range(len(O)):
                expect['x'].append(dict(slice=s, eaddr=BLOCK * s + 64 * j,
                                        edge_e5=e + smap['cmd_arrival'][s] + O[j] + 2 * (N - 1 - s)))
    coll = S.collisions()
    if coll and mutant != 'xslot':
        raise LowerError(f'collisions {coll[:3]}')
    return dict(
        schema='opentallas.qwen.dv-lowering-vec.v1', tool='tools/qwen_layerbench/dv_lower_vec.py', mode=mode,
        mutant=mutant, ar_order=ar_order, ar_r0=r0 if mode == 'resid' else None, slice_map=smap, ownership=own, vm=vm, crom=cr, qkv_roles=roles, isa=isa, isa_rmsnorm=isa_n,
        ages=ages, pidx=PIDX,
        prog={s: [f'{w:0115x}' for w in ws] for s, ws in img.items()},
        prog_stream={s: [dict(eaddr=a_, payload=f'{p:0256x}') for a_, p in D.prog_words(ws)] for s, ws in img.items()},
        crom_table=tw, ar_return=ar_cal, commands=S.commands(), expected=expect,
        collisions=[[list(k_), v] for k_, v in coll],
        assumptions=['AR return calendar slice-major (slice 0 owned blocks ascending, then slice 1, ...): the io_collective '
                     'all-reduce must return the reduced t words in this order (the return word has no address)',
                     'D2D addresses: q = global q row (128 head + i), k / v = head-dim index; the KV die adds the token '
                     'position (its own landing)',
                     'slice 11 x words also leave east at the E5 chain end (st_up_o of dvs_E5: no consumer on the die)'],
        not_lowered=['STN commands of qkv / o / gu / down / LM head (the station landings QKV / GU / AR this lowering '
                     'reads are their contract: sibling QLB-C4b/3b)', 'XC collectives', 'LM-head AMAX',
                     'stage-0 slice commands (embedding landing em_base)', 'head-row (hr / xpf) control of the column '
                     'heads that consume the x stream', 'splice into the ctlm decode calendar'],
        die_gaps=['dvs_W5.st_wi tied 0 on the die (dv_lower die_gaps): the PROG and CROM table words this lowering '
                  'emits (incl. the per-token RoPE row) have no load path on the die'])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=('resid', 'qk', 'silu'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutant')
    a = ap.parse_args()
    try:
        r = lower_vec(a.mode, a.mutant)
    except LowerError as e:
        print(f'DV_LOWER_VEC REFUSED: {e}')
        return 2
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(dict(mode=a.mode, commands=len(r['commands']), last=r['commands'][-1]['edge'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
