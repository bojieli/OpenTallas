#!/usr/bin/env python3
"""p-position verify layer for the Qwen3-8B ROM TP runtime (opt-in, default-off).

A speculative-decoding verify step runs one decoder layer over p consecutive
positions pos0 .. pos0+p-1 of one user.  This tool emits that layer as ONE
program for one die: every operation of the AR layer (tools/hdc_program.py
build_program, the norm-folded TP layer of tools/hdc_qwen_fullshape_program_w12.py)
is issued p times back to back, once per position, so each fixed latency
(engine fill, wire stages, adder tree, stream pipeline) is paid once per
operation group and the issue p times.

Per position j:
  * its own vector-memory regions (X, H, QKV, ..., ACT; T1 is shared, see below);
  * DYN offsets from pos0 + j: the instruction's 3-bit POS_OFF field (bits
    [902:900], unused by the legacy 898-bit layout) selects which of the
    sequencer's per-position DYN tables the core adds (RoPE row, K/V write
    slot, context length T = pos0 + j + 1, position-tile rounds);
  * the causal in-block mask is the context length: position j's scores and
    weighted sum run over T = pos0 + j + 1 positions, so it sees the block's
    positions < j (their K/V rows are written earlier in the same program) and
    never the later ones.

The two all-reduces carry all p positions in one stream: T1 holds the p
partial vectors back to back (p x 4,096 elements from element 0) and the
segment descriptor's word count is p x 256.  That count does not fit the
8-bit field: an AR count's high 4 bits go in descriptor bits [23:20] (unused;
rtl/rom/ot_qwen_tp_seq_w12_vp.sv decodes them with ENABLE_ARP=1).  The post-TP
scale after each all-reduce is one stream op over p rows.

p = 1 reproduces the AR256 program (tools/qwen_rom_ar256_stage_images.py, the
generator with QWEN_O4_AR_WORDS=256) word for word: `--self-check`.

The arithmetic of each position is the AR layer's, operation by operation
(same instructions, same reduction orders); only addresses, DYN rows and
scheduling differ.  tools/qwen_rom_verify_oracle_w12.py proves it on the ISA
golden against p sequential AR decodes.

  qwen_rom_verify_program_w12.py --stages STAGES --p 2 --out DIR [--only L0]
  qwen_rom_verify_program_w12.py --self-check --manifests M0,M1,M2,M3 --ar256 D0,D1,D2,D3
Environment as the pinned images: QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=64.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault('QWEN_O4_AR_WORDS', '256')
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402
import hdc_qwen_fullshape_program_w12 as FP  # noqa: E402

W, IL = I.W_LANES, I.INTERLEAVE
TMAX = FP.TMAX
POS_OFF_OFFSET, POS_OFF_WIDTH = QI.ROW_HIGH_OFFSET + 2, 3
DESC_NW_HIGH_OFFSET, DESC_NW_HIGH_WIDTH = 20, 4
assert POS_OFF_OFFSET + POS_OFF_WIDTH <= I.INSTR_BITS
LINK = ("crom.hex", "matrix_int8.hex", "matrix_scale_bf16.hex")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def f32(x):
    return P.f32(x)


def vm_map_p(p, h=4096, region_major=False):
    """T1 for all p positions first (the all-reduce source, word 0), then one
    copy of every other region of tools/hdc_qwen_fullshape_program_w12.vm_map per
    position.  p = 1 is that map exactly.  region_major (MERGE_SU): the p copies of
    each region are adjacent (copy j at region base + j x aligned size), so an op on
    the p positions is one op with a position stride."""
    one, _ = FP.vm_map()
    names = [n for n in sorted(one, key=one.get)]
    assert names[0] == 'T1' and one['T1'] == 0
    sizes = {n: (one[names[i + 1]] if i + 1 < len(names) else None) for i, n in enumerate(names)}
    _, total1 = FP.vm_map()
    sizes[names[-1]] = total1 - one[names[-1]]
    sizes = {n: sizes[n] - one[n] if n != names[-1] else sizes[n] for n in names}
    out = [dict() for _ in range(p)]
    base = h * p
    for j in range(p):
        out[j]['T1'] = j * h
    if region_major:
        for n in names[1:]:
            for j in range(p):
                base = (base + W - 1) // W * W
                out[j][n] = base
                base += sizes[n]
    else:
        for j in range(p):
            for n in names[1:]:
                base = (base + W - 1) // W * W
                out[j][n] = base
                base += sizes[n]
    total = (base + W - 1) // W * W
    if p == 1:
        assert out[0] == one and total == total1, 'p = 1 must equal the AR map'
    return out, total


def build_verify_layer(lay, p, post_scale_bases=None, merge_su=False):
    """Field dicts of the p-position layer (norm-folded TP layer, layer index 0
    of a single-layer KV window).

    merge_su (default off; region-major VM layout): a stream op with no DYN term
    is issued ONCE for the p positions instead of p times back to back -- its
    rows are the p positions' rows (nout x p) at the region's position stride, so
    every output element is computed by exactly the arithmetic of the per-position
    op (same inputs, same reduction order); only the issue count changes."""
    vms, _ = vm_map_p(p, region_major=merge_su)
    pstride = {n: vms[1][n] - vms[0][n] for n in vms[0]} if p > 1 else {n: 0 for n in vms[0]}
    GR = P.GR
    S_STRIDE = TMAX
    L = 0
    H, HD, NH, KV, half = lay.H, lay.HD, lay.NH, lay.KV, lay.half
    group = NH // KV
    assert getattr(lay, 'norm_fold', False) and lay.tp > 1

    def layer_ops(j):
        """(fields, reads, writes) of position j; markers ('COLL',) and ('SCALE', i)."""
        VM = vms[j]
        prog = []
        tag = lambda s: {f'{x}@{j}' for x in s}  # noqa: E731

        def me(mat, x, out, rnd=True, amax=False, oen=True, reads=(), writes=(), **over):
            f = dict(unit=I.UNIT_ME, me_nout=mat["n"], me_tiles=mat["tiles"], me_k=mat["k"], me_wsrc=0,
                     me_wbase=mat["base"], me_ts=mat["k"] * IL, me_ks=IL, me_js=1, me_xbase=x, me_xks=1,
                     me_wcs=mat.get("scale_base", mat["base"]),
                     me_round=int(rnd), me_obase=out // W, me_ots=IL, me_ojs=1, me_oen=int(oen),
                     me_amax=int(amax), me_split=mat.get("split", 1).bit_length() - 1,
                     me_xcs=mat["k"])
            f.update(over)
            prog.append((f, tag(reads), tag(writes)))

        def su(reads=(), writes=(), red_writes=(), merge=None, **f):
            f = dict(f, unit=I.UNIT_SU, _red_regions=tag(red_writes))
            if merge is not None:
                f['_merge'] = merge
            prog.append((f, tag(reads), tag(writes) | tag(red_writes)))

        sq = dict(red=I.RED_SUM, red_sq=1, r_base=VM["SSX"])

        def rsqrt_rx(n):
            su(su_nout=1, su_nin=1, a_base=VM["SSX"], ma=I.MA_AIMM, imm1=f32(1.0 / n), ad=I.AD_IMM,
               imm2=f32(lay.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM, d_base=VM["RX"],
               reads={"SSX"}, writes={"RX"}, merge=dict(a="SSX", d="RX"))

        # X arrived over the package link: its sum of squares opens the stage
        su(su_nout=1, su_nin=H, a_base=VM["X"], a_si=1, reads={"X"}, red_writes={"SSX"},
           merge=dict(a="X", r="SSX"), **sq)
        nh = NH + KV
        me(lay.mat[(L, "qkv")], VM["X"], VM["QKV"], reads={"X"}, writes={"QKVqk", "QKVv"})
        rsqrt_rx(H)
        rx = dict(ma=I.MA_AB, b_base=VM["RX"])
        su(su_nout=KV, su_nin=HD, a_base=VM["QKV"] + (NH + KV) * HD, a_so=HD, a_si=1,
           dst=I.DST_KV, d_base=lay.v_elem(L, 0, 0, 0), d_d=I.DYN_VWRITE,
           d_so=lay.v_elem(L, 1, 0, 0) - lay.v_elem(L, 0, 0, 0), d_si=1,
           reads={"QKVv", "RX"}, writes={f"V{L}"}, **rx)
        su(su_nout=nh, su_nin=HD, a_base=VM["QKV"], a_so=HD, a_si=1, ma=I.MA_AB, b_base=VM["RX"],
           dst=I.DST_VM, d_base=VM["QKV"], d_so=HD, d_si=1, red=I.RED_SUM, red_sq=1,
           r_base=VM["SS"], r_so=1, reads={"QKVqk", "RX"}, writes={"QKVqk"}, red_writes={"SS"})
        su(su_nout=1, su_nin=nh, a_base=VM["SS"], a_si=1, ma=I.MA_AIMM, imm1=f32(1.0 / HD),
           ad=I.AD_IMM, imm2=f32(lay.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM, d_base=VM["RS"], d_si=1,
           reads={"SS"}, writes={"RS"}, merge=dict(a="SS", d="RS"))
        su(su_nout=nh, su_nin=HD, a_base=VM["QKV"], a_so=HD, a_si=1, ma=I.MA_AB, b_base=VM["RS"],
           b_so=1, c_src=I.SRC_ALT, c_base=lay.cb[(L, "qk")], c_so=HD, c_si=1, mc=I.MC_C,
           dst=I.DST_VM, d_base=VM["QN"], d_so=HD, d_si=1, reads={"QKVqk", "RS"}, writes={"QN"})
        rope = dict(b_src=I.SRC_ALT, b_base=lay.cb["rope"], b_d=I.DYN_ROPE, b_si=1, ma=I.MA_AB,
                    ad=I.AD_Q, a_so=HD, a_si=1, c_so=HD, c_si=1, su_nin=half)
        for lo in (True, False):
            a_off, c_off, mb = (0, half, I.MB_NEG) if lo else (half, 0, I.MB_POS)
            su(su_nout=NH, a_base=VM["QN"] + a_off, c_base=VM["QN"] + c_off, mb=mb,
               dst=I.DST_VM, d_base=VM["QR"] + a_off, d_so=HD, d_si=1,
               reads={"QN"}, writes={"QRlo" if lo else "QRhi"}, **rope)
            kq = VM["QN"] + NH * HD
            su(su_nout=KV, a_base=kq + a_off, c_base=kq + c_off, mb=mb, dst=I.DST_KV,
               d_base=lay.k_elem(L, 0, 0, a_off), d_d=I.DYN_KWRITE,
               d_so=lay.k_elem(L, 1, 0, 0) - lay.k_elem(L, 0, 0, 0), d_si=W,
               reads={"QN"}, writes={f"K{L}lo" if lo else f"K{L}hi"}, **rope)
        jsh = group.bit_length() - 1
        kjs = (lay.k_elem(L, 1, 0, 0) - lay.k_elem(L, 0, 0, 0)) // W if KV > 1 else 0
        vjs = (lay.v_elem(L, 1, 0, 0) - lay.v_elem(L, 0, 0, 0)) // W if KV > 1 else 0
        assert 1 << jsh == group and IL % group == 0
        heads = {f"S{h}" for h in range(NH)}
        s_sc, s_pv = G.attn_splits(HD, lay.groups)
        # causal in-block: position j reads the K/V rows of the block's positions 0..j
        kseen = set().union(*({f"K{L}lo@{i}", f"K{L}hi@{i}"} for i in range(j + 1)))
        vseen = {f"V{L}@{i}" for i in range(j + 1)}
        for hb in range(0, NH, IL):
            nb = min(IL, NH - hb)
            me(dict(n=0, tiles=0, k=HD, base=(lay.k_elem(L, hb // group, 0, 0)) // W), VM["QR"] + hb * HD,
               VM["S"] + hb * S_STRIDE, rnd=True, me_xcs=1, me_wcs=1, me_split=s_sc.bit_length() - 1,
               me_wsrc=1, me_ts=HD, me_ks=s_sc, me_js=kjs,
               me_jsh=jsh, me_xks=s_sc, me_xjs=HD, me_ots=1, me_ojs=S_STRIDE // W, me_mmode=1,
               me_d_nout=I.DYN_T, me_d_tiles=I.DYN_TTILES,
               **(dict(me_rmax=1, me_mbase=VM["M"] + hb) if I.RMAX else {}),
               reads={"QRlo", "QRhi"}, writes={f"S{h}" for h in range(hb, hb + nb)} | ({f"M{hb}"} if I.RMAX else set()))
            prog[-1] = (prog[-1][0], prog[-1][1] | kseen, prog[-1][2])
        sm = dict(su_nout=NH, su_d_nin=I.DYN_T, a_base=VM["S"], a_so=S_STRIDE, a_si=1,
                  d_base=VM["S"], d_so=S_STRIDE, d_si=1, dst=I.DST_VM)
        assert I.RMAX
        su(ma=I.MA_AIMM, imm1=f32(1.0 / np.sqrt(HD)), mb=I.MB_NEG, b_src=I.SRC_ALT, b_base=lay.cb["qscale"],
           c_base=VM["M"], c_so=1, ad=I.AD_Q, sfu=I.SFU_EXP, red=I.RED_SUM, r_base=VM["Z"], r_so=1,
           reads=heads | {f"M{hb}" for hb in range(0, NH, IL)}, writes=heads, red_writes={"Z"}, **sm)
        qt = max(1, HD // W)
        for hb in range(0, NH, IL):
            nb = min(IL, NH - hb)
            me(dict(n=HD, tiles=-(-qt // max(1, lay.groups // s_pv)), k=0,
                    base=lay.v_elem(L, hb // group, 0, 0) // W),
               VM["S"] + hb * S_STRIDE, VM["ATT"] + hb * HD,
               rnd=True, me_xcs=1, me_wcs=qt, me_split=s_pv.bit_length() - 1,
               me_wsrc=1, me_ts=1, me_ks=qt * s_pv,
               me_js=vjs, me_jsh=jsh, me_xks=s_pv,
               me_xjs=S_STRIDE, me_ots=1, me_ojs=max(1, HD // W), me_mmode=1, me_d_k=I.DYN_T,
               reads={f"S{h}" for h in range(hb, hb + nb)}, writes={f"ATT{hb}"})
            prog[-1] = (prog[-1][0], prog[-1][1] | vseen, prog[-1][2])
        su(su_nout=1, su_nin=NH, a_base=VM["Z"], a_si=1, sfu=I.SFU_RECIP, dst=I.DST_VM,
           d_base=VM["RZ"], d_si=1, reads={"Z"}, writes={"RZ"}, merge=dict(a="Z", d="RZ"))
        su(su_nout=NH, su_nin=HD, a_base=VM["ATT"], a_so=HD, a_si=1, ma=I.MA_AB, b_base=VM["RZ"], b_so=1,
           dst=I.DST_VM, d_base=VM["ATTN"], d_so=HD, d_si=1,
           reads={f"ATT{hb}" for hb in range(0, NH, IL)} | {"RZ"}, writes={"ATTN"})
        me(lay.mat[(L, "o")], VM["ATTN"], VM["T1"], reads={"ATTN"}, writes={"T1"})
        prog.append(('COLL', 0))
        prog.append(('SCALE', 0))
        su(su_nout=1, su_nin=H, a_base=VM["X"], a_si=1, c_base=VM["T1"], c_si=1, ad=I.AD_C,
           dst=I.DST_VM, d_base=VM["X"], d_si=1, reads={"X", "T1"}, writes={"X"}, red_writes={"SSX"},
           merge=dict(a="X", c="T1", d="X", r="SSX"), **sq)
        FF, tb = lay.FF, lay.GUB
        me(lay.mat[(L, "gu")], VM["X"], VM["GU"], reads={"X"}, writes={"GUall"})
        rsqrt_rx(H)
        su(su_nout=1, su_nin=2 * FF, a_base=VM["GU"], a_si=1, ma=I.MA_AB, b_base=VM["RX"],
           dst=I.DST_VM, d_base=VM["GU"], d_si=1, reads={"GUall", "RX"},
           writes={f"GU{r}" for r in range(FF // tb)}, merge=dict(a="GU", b="RX", d="GU"))
        su(su_nout=FF // tb, su_nin=tb, a_base=VM["GU"], a_so=2 * tb, a_si=1, ma=I.MA_AIMM, imm1=f32(-1.0),
           sfu=I.SFU_SIGM, c_base=VM["GU"], c_so=2 * tb, c_si=1, mc=I.MC_C, b_base=VM["GU"] + tb,
           b_so=2 * tb, b_si=1, md=I.MD_B, dst=I.DST_VM, d_base=VM["ACT"], d_so=tb, d_si=1,
           reads={f"GU{r}" for r in range(FF // tb)}, writes={f"ACT{r}" for r in range(FF // tb)},
           merge=dict(rows=dict(a="GU", b="GU", c="GU", d="ACT")))
        me(lay.mat[(L, "down")], VM["ACT"], VM["T1"], reads={f"ACT{r}" for r in range(FF // tb)},
           writes={"T1"})
        prog.append(('COLL', 1))
        prog.append(('SCALE', 1))
        su(su_nout=1, su_nin=H, a_base=VM["X"], a_si=1, c_base=VM["T1"], c_si=1, ad=I.AD_C,
           dst=I.DST_VM, d_base=VM["X"], d_si=1, reads={"X", "T1"}, writes={"X"}, red_writes={"SSX"},
           merge=dict(a="X", c="T1", d="X", r="SSX"), **sq)
        return prog

    def merge_op(ops):
        """one op for the p positions: rows = the p positions' rows at the position stride"""
        f0 = {k: v for k, v in ops[0][0].items() if k != '_merge'}
        spec = ops[0][0]['_merge']
        for j, (fj, _, _) in enumerate(ops):   # the copies differ only by the merged operands' bases
            for k, v in fj.items():
                if k in ('_merge', '_red_regions') or k.endswith('_base'):
                    continue
                assert v == f0.get(k), f'merge: field {k} differs between positions'
        f = dict(f0)
        if 'rows' in spec:
            n = f0['su_nout']
            for op, reg in spec['rows'].items():
                assert pstride[reg] == n * f0[f'{op}_so'], f'merge rows: {reg} stride {pstride[reg]} != {n} x {op}_so'
            f['su_nout'] = n * p
        else:
            assert f0['su_nout'] == 1
            f['su_nout'] = p
            for op, reg in spec.items():
                assert f0.get(f'{op}_so', 0) == 0
                f[f'{op}_so'] = pstride[reg]
        for j, (fj, _, _) in enumerate(ops):   # every position's base is the position-0 base + j x stride
            for k, v in fj.items():
                if k.endswith('_base') and k != 'c_base' or (k == 'c_base' and fj.get('c_src', 0) != I.SRC_ALT):
                    if isinstance(v, int) and k[0] in 'abcdr':
                        reg = (spec['rows'] if 'rows' in spec else spec).get(k[0])
                        if reg is not None:
                            assert v == f0[k] + j * pstride[reg], f'merge: {k} of position {j} is not at the stride'
        f['_red_regions'] = set().union(*(o[0]['_red_regions'] for o in ops))
        return (dict(f, _pos_off=0), set().union(*(o[1] for o in ops)), set().union(*(o[2] for o in ops)))

    per = [layer_ops(j) for j in range(p)]
    assert all(len(x) == len(per[0]) for x in per)
    prog = []
    for i in range(len(per[0])):
        ops = [x[i] for x in per]
        if isinstance(ops[0][0], str) and ops[0][0] == 'COLL':
            prog.append((dict(unit=I.UNIT_END, barrier=1, _coll=(P.COLL_ALLREDUCE, 0, p * H // W, 0)),
                         set(), set()))
        elif isinstance(ops[0][0], str) and ops[0][0] == 'SCALE':
            if post_scale_bases is None:
                continue
            f = dict(unit=I.UNIT_SU, barrier=1, su_nout=p, su_nin=H,
                     a_base=vms[0]['T1'], a_si=1, c_src=I.SRC_ALT,
                     c_base=post_scale_bases[ops[0][1]], c_si=1, mc=I.MC_C,
                     dst=I.DST_VM, d_base=vms[0]['T1'], d_si=1, _red_regions=set())
            if p > 1:
                f.update(a_so=H, d_so=H)
            # untracked, as FP.insert_post_tp_scales (applied after scheduling there): the stream
            # unit runs in order, so the residual add behind it reads T1 after it is scaled
            prog.append((f, set(), set()))
        elif merge_su and p > 1 and isinstance(ops[0][0], dict) and '_merge' in ops[0][0]:
            prog.append(merge_op(ops))
        else:
            for j, (f, rd, wr) in enumerate(ops):
                f = {k: v for k, v in f.items() if k != '_merge'}
                prog.append((dict(f, _pos_off=j), rd, wr))
    prog.append((dict(unit=I.UNIT_END, barrier=1, _coll=(P.COLL_END, 0, 0, lay.row0)), set(), set()))
    return schedule(prog, lay)


def schedule(prog, lay):
    """hdc_program.build_program's barrier / per-unit wait / element-chase pass,
    unchanged, over the interleaved list."""
    U = (I.UNIT_ME, I.UNIT_SU)
    out = []
    rdu = {u: set() for u in U}
    wru = {u: set() for u in U}
    last = {I.UNIT_ME: None, I.UNIT_SU: None}
    main = {I.UNIT_ME: set(), I.UNIT_SU: set()}
    for f, reads, writes in prog:
        rd = rdu[I.UNIT_ME] | rdu[I.UNIT_SU]
        wr = wru[I.UNIT_ME] | wru[I.UNIT_SU]
        conflict = (reads & wr) | (writes & (rd | wr))
        other = I.UNIT_SU if f["unit"] == I.UNIT_ME else I.UNIT_ME
        prod = last.get(other)
        chase_n = None
        if (conflict and prod is not None and f["unit"] != I.UNIT_END and not (writes & (rd | wr))
                and conflict <= main[other]):
            chase_n = P.chase_threshold(f, prod[0], lay.groups)
        if chase_n is not None:
            f["chase"], f["chase_n"] = 1, chase_n
        elif conflict or f.get("barrier"):
            waits = set(U) if (f.get("barrier") or f["unit"] == I.UNIT_END) else \
                {u for u in U if (reads & wru[u]) or (writes & (rdu[u] | wru[u]))}
            if waits == set(U):
                f["barrier"] = 1
            else:
                f["wait_me"] = int(I.UNIT_ME in waits)
                f["wait_su"] = int(I.UNIT_SU in waits)
            for u in waits:
                rdu[u], wru[u], main[u] = set(), set(), set()
        if f["unit"] in last:
            rdu[f["unit"]] |= reads
            wru[f["unit"]] |= writes
        out.append(f)
        if f["unit"] in last:
            red = set(f.get("_red_regions", ()))
            last[f["unit"]] = (f, reads, writes, red)
            main[f["unit"]] |= writes - red
    for f in out:
        f.pop("_red_regions", None)
        f.pop("_prev_slots", None)
    return out


def encode_instruction(f):
    off = int(f.get('_pos_off', 0))
    if not 0 <= off < (1 << POS_OFF_WIDTH):
        raise ValueError('position offset exceeds POS_OFF')
    return QI.encode_instruction(f) | (off << POS_OFF_OFFSET)


def decode_pos_off(word):
    return (word >> POS_OFF_OFFSET) & ((1 << POS_OFF_WIDTH) - 1)


def encode_descriptor(kind, vm_word, words, program_base, row0):
    """QI.encode_descriptor, with an all-reduce count above 256 carried in [23:20]."""
    if kind == P.COLL_ALLREDUCE and words > 256:
        if words % 256 or words >= (1 << (8 + DESC_NW_HIGH_WIDTH)):
            raise ValueError('wide all-reduce count must be a multiple of 256 below 4,096')
        return (QI.encode_descriptor(kind, vm_word, 256, program_base, row0)
                | ((words >> 8) << DESC_NW_HIGH_OFFSET))
    return QI.encode_descriptor(kind, vm_word, words, program_base, row0)


def decode_descriptor(word):
    d = QI.decode_descriptor(word)
    hi = (word >> DESC_NW_HIGH_OFFSET) & ((1 << DESC_NW_HIGH_WIDTH) - 1)
    if d['kind'] == P.COLL_ALLREDUCE and hi:
        d['words'] = (hi << 8) | ((word >> 10) & 255)
    return d


def profile(die, p, matrix_rows, post_scale_bases, merge_su=False):
    vm, _ = FP.vm_map()
    lay = FP.LayerZero(None, die, matrix_rows)
    with FP.program_geometry(vm):
        program = build_verify_layer(lay, p, post_scale_bases, merge_su=merge_su)
    words, desc = [], []
    for instrs, (kind, vw, nw, row0) in P.segments(program):
        desc.append(encode_descriptor(kind, vw, nw, len(words), row0))
        words.extend(encode_instruction(f) for f in instrs)
    for f, w in zip(program, words):
        d = QI.decode_instruction(w)
        for k, v in f.items():
            if not k.startswith('_') and d[k] != v:
                raise ValueError(f'ISA round trip failed: {k}')
    _, vm_elems = vm_map_p(p, region_major=merge_su)
    return {'die': die, 'p': p, 'program_hex': [f'{x:0256x}' for x in words],
            'descriptor_hex': [f'{x:016x}' for x in desc], 'vm_elems': vm_elems,
            'x_bases': [m['X'] for m in vm_map_p(p, region_major=merge_su)[0]], 'instructions': len(words),
            'me_ops': sum(f['unit'] == I.UNIT_ME for f in program),
            'su_ops': sum(f['unit'] == I.UNIT_SU for f in program)}


K_ARGNEXT = 3     # rtl/rom/ot_qwen_tp_seq_w12_vp.sv ENABLE_ARP: gather, record, continue


def profile_lm_head_p(die, geometry, p, final_norm_base=0, chunk_words=512):
    """lm_head stage for p positions: per position j (its X_j, H_j, SSX_j, RX_j of
    vm_map_p) the final RMSNorm and the chunked lm_head with running argmax
    (FP.profile_lm_head, unchanged), each ending in an argmax all-gather:
    ARGMAX_NEXT for j < p-1, ARGMAX for the last.  p = 1 is FP.profile_lm_head."""
    vms, _ = vm_map_p(p)
    place = FP.placement()
    words, desc = [], []
    for j in range(p):
        lay = FP.LayerZero(place, die)
        lay.row0 = die * (151936 // FP.TP)
        lay.cb['final'] = final_norm_base
        lay.mat['lm_head'] = {'base': geometry['base'], 'scale_base': geometry['scale_base'],
                              'n': 151936 // FP.TP, 'k': geometry['k_per_split'],
                              'tiles': geometry['rounds'], 'split': geometry['split']}
        with FP.program_geometry(vms[j]):
            program = P.build_program(lay, layers=[], embed=False, head=True, wchunk=chunk_words, scale_bases=True)
        segs = P.segments(program)
        if len(segs) != 1 or segs[0][1][0] != P.COLL_ARGMAX:
            raise ValueError('lm_head stage must be one argmax segment')
        instrs, (kind, vw, nw, row0) = segs[0]
        desc.append(encode_descriptor(P.COLL_ARGMAX if j == p - 1 else K_ARGNEXT, vw, nw, len(words), row0))
        words.extend(encode_instruction(f) for f in instrs)
    return {'die': die, 'p': p, 'program_hex': [f'{x:0256x}' for x in words],
            'descriptor_hex': [f'{x:016x}' for x in desc], 'instructions': len(words),
            'x_bases': [m['X'] for m in vms]}


def self_check(manifests, ar256_dirs):
    res = {}
    for mpath, d in zip(manifests, ar256_dirs):
        man = json.loads(Path(mpath).read_text())
        r = profile(man['die'], 1, man['matrix_layout'], man['post_tp_scale_bases'])
        words = Path(d, 'program.hex').read_text().split()
        segs = Path(d, 'segments.hex').read_text().split()
        ok = r['program_hex'] == words and [x.lower() for x in r['descriptor_hex']] == [x.lower() for x in segs]
        res[f"die{man['die']}"] = {'equal': ok, 'program_sha256': hashlib.sha256(
            (''.join(x + '\n' for x in words)).encode()).hexdigest(), 'words': len(words)}
        if not ok:
            raise SystemExit(f'self-check failed: {mpath}')
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--stages', type=Path, help='pinned stage list (layer stages: their dirs hold program.hex and links)')
    ap.add_argument('--manifest-dirs', help='format string of the img_tp4 dir holding layer{n}_rom.json, {layer} {die}')
    ap.add_argument('--p', type=int, default=2)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--only', default='')
    ap.add_argument('--self-check', action='store_true')
    ap.add_argument('--head-dirs', help='format string {die}: img_tp4 head dirs (head_rom.json geometry); emits the head stage')
    ap.add_argument('--head-src', help='format string {die}: pinned SW64 head stage dirs (crom/matrix links; p = 1 check)')
    ap.add_argument('--manifests', default='')
    ap.add_argument('--merge-su', action='store_true', help='MERGE_SU: one stream op for the p positions where no DYN term (region-major VM)')
    ap.add_argument('--ar256', default='')
    a = ap.parse_args()
    if I.SU_WIDTH != 64:
        raise SystemExit('emit at the runtime stream width: HDC_SU_WIDTH=64')
    report = {'schema': 'opentallas.qwen-rom-verify-program.v1', 'tool_sha256': sha(__file__), 'p': a.p}
    if a.self_check:
        report['self_check'] = self_check(a.manifests.split(','), a.ar256.split(','))
    if a.stages:
        keep = set(filter(None, a.only.split(',')))
        lines, stages = [], []
        for line in a.stages.read_text().splitlines():
            if not line.strip():
                continue
            name, *dirs, kv = line.split()
            if keep and name not in keep:
                continue
            n = int(name[1:])
            nd = []
            for die, src in enumerate(map(Path, dirs)):
                man = json.loads(Path(a.manifest_dirs.format(layer=n, die=die), f'layer{n}_rom.json').read_text())
                r = profile(die, a.p, man['matrix_layout'], man['post_tp_scale_bases'], merge_su=a.merge_su)
                dst = a.out / f'{name}-d{die}'
                dst.mkdir(parents=True, exist_ok=False)
                (dst / 'program.hex').write_text(''.join(x + '\n' for x in r['program_hex']))
                (dst / 'segments.hex').write_text(''.join(x + '\n' for x in r['descriptor_hex']))
                for f in LINK:
                    os.symlink((src / f).resolve(), dst / f)
                stages.append({'stage': name, 'die': die, 'instructions': r['instructions'],
                               'me_ops': r['me_ops'], 'su_ops': r['su_ops'], 'vm_elems': r['vm_elems'],
                               'x_bases': r['x_bases'], 'program_sha256': sha(dst / 'program.hex'),
                               'segments_sha256': sha(dst / 'segments.hex')})
                nd.append(str(dst))
            lines.append(' '.join([name, *nd, kv]))
        (a.out / 'stages.txt').write_text(''.join(x + '\n' for x in lines))
        report['stages'] = stages
        (a.out / 'verify_images.json').write_text(json.dumps(report, indent=1) + '\n')
    if a.head_dirs:
        nd, heads = [], []
        for die in range(FP.TP):
            geo = dict(json.loads(Path(a.head_dirs.format(die=die), 'head_rom.json').read_text())['geometry'])
            geo['scale_base'] = 0
            geo.setdefault('base', 0)
            r = profile_lm_head_p(die, geo, a.p)
            src = Path(a.head_src.format(die=die))
            if a.p == 1:
                same = (r['program_hex'] == src.joinpath('program.hex').read_text().split()
                        and [x.lower() for x in r['descriptor_hex']] == [x.lower() for x in src.joinpath('segments.hex').read_text().split()])
                if not same:
                    raise SystemExit(f'head p=1 differs from the pinned SW64 head stage die {die}')
            dst = a.out / f'head-d{die}'
            dst.mkdir(parents=True, exist_ok=False)
            (dst / 'program.hex').write_text(''.join(x + '\n' for x in r['program_hex']))
            (dst / 'segments.hex').write_text(''.join(x + '\n' for x in r['descriptor_hex']))
            for f in LINK:
                os.symlink((src / f).resolve(), dst / f)
            heads.append({'die': die, 'instructions': r['instructions'], 'x_bases': r['x_bases'],
                          'program_sha256': sha(dst / 'program.hex'), 'segments_sha256': sha(dst / 'segments.hex'),
                          'p1_equals_pinned': a.p == 1})
            nd.append(str(dst))
        (a.out / 'stages_head.txt').write_text(' '.join(['head', *nd, '0']) + '\n')
        report['head'] = heads
        (a.out / 'verify_head_images.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('stages', 'head')}, indent=1))


if __name__ == '__main__':
    main()
