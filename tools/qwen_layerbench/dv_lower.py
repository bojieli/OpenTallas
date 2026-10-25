#!/usr/bin/env python3
"""dv_lower: DV slice lowering of the Qwen compute-die static schedule (QLB-C4 10-18, layer-bench gap G-C4).

ctlm_image.py compiles the qfd_tt_ctlm_dv image (ME programme, fixed-issue rows, XPF, the qfd_dv_cmd_cal calendar) and
issues every SU op as ONE broadcast slice command `SU pidx = PC`.  On the DV die that is not a programme: the twelve
qfd_dv_slice2 instances each hold 1/12 of the vector rows, run their own SU words from their own PROG store, and
combine global reductions on the scalar chain.  This pass is the lowering the calendar was missing:

 1. SLICE MAP (die model + die-run relay table): the cmd chain order from dvs_W5 (the tt_ctlm end) to dvs_E5, the SETID
    enumeration id of every slice (slice2: SETID latches id, forwards id + 1), and the per-hop ages of the cmd chain
    (2 edges a hop: pin register + cmd_o register, + relay stages) and of the downward scalar chain (2 edges a hop: pin
    register + dn_o register, + relay stages).  The die (dv2f14bq) has no relay on any slice-to-slice cmd / sc hop.
 2. ROW OWNERSHIP (token_source_plan layer_matrix_layout + the slice2 station modes): a matvec's 128-row blocks finish
    where the split's tree level finishes (rtl/qwen_dv/README.md, SPEC dv2): split 256 (o / down) -> level 8 in the
    quad's station, 12 tiles a round, block b -> slice (b mod 12) [tile t = quad t of the tree order = column quad t =
    SETID id t: compute_spine.ref_tile_id t // 64 = c // 4 and qfd_dv_heads column = 4 sid + i]; split 128 (gate/up)
    -> level 7, 24 tiles a round, two per quad (lower pair even, upper pair odd); split 512 (qkv / LM head) -> level 9
    between the pair stations, 6 tiles a round, block b -> receiver slice 2 (b mod 6).  The residual rows each slice
    owns are its o / down rows (the residual add is slice-local; o and down must own identically).
 3. SLICE-LOCAL VM MAP: per slice, every region the lowered ops touch, at 16-aligned local FP32 addresses inside the
    qfd_dv_vm 16,384-element VM (3 replicas x 2 banks x 1,024 x 8); fail closed on overlap / overflow / misalignment.
 4. PROG IMAGE: the 457-b SU issue words (qfd_seq_su su[456:0] layout, the qfd_dv_slice2 si bit map) of every lowered
    op, packed two per kind-3 stream table word (qfd_dv_stream / qfd_dv_vm: eaddr = pair index, tw_addr[23:8] = 0).
 5. COMMANDS + SCHEDULE: the slice command words (qfd_dv_slice2 decode: SU / STN / ROOT / PORTS / STREAM / AMAX / XC /
    SETID field maps, every field range-checked), the edge each one enters the cmd chain at dvs_W5.cmd_wi (one word an
    edge), and a fail-closed collision check of the downward scalar chain (qfd_dv_scalar2: one word a direction an
    edge; a pass and an own word on one edge drop a word).

LOWERED NOW (the global RMSNorm sum of squares, the q3h programme's PC0 / PC15 / PC23 + the rsqrt PC2 / PC17):
    per slice SSQ: nout = owned blocks, nin = 128 (one csum8 block a row, R-ARITH aligned subtree), red to the PSUM
    window with r_base = the slice's first global block index and r_so = 12 (its next block's index), so every PSUM
    tag IS the golden block position; the root (SETID 0 = dvs_W5, rdir 0: the whole chain is up of it) combines the
    32 slots in the golden pairwise order and forms r fused (k = log2(1 / imm1) exactly, eps = imm2), RB to every
    slice's rx.  The SU rsqrt op disappears into the ROOT.
NOT LOWERED YET (recorded in lower()['not_lowered']): the norm apply + BF16 stream, residual adds, QK-norm / RoPE, the
    STN commands of the matvecs, PORTS (AR / D2D / embedding landings), XC collectives, SiLU, the LM-head AMAX.

SU timing constants are MEASURED on the slice2 RTL (rtl/test/qwen_dv/dv_lower_bench.py --calibrate, Verilator 5.050):
results/rtl/qlb_c4_1018/dv_lower/slice_ages.json; the compiler refuses to schedule without them.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DV_MODEL = 'results/arch/qwen_split_compute_1014/dieplan2_1016/dv2r8f7r_qdv_p2462.json'
RELAY = 'results/rtl/qlb_gen_1018/dv2f14bq/relay_stages_compute.json'
PLAN = 'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/token_source_plan.json'
AGES = 'results/rtl/qlb_c4_1018/dv_lower/slice_ages.json'
NSLICE, VM_EL, PROG_N, BLOCK = 12, 16384, 512, 128
CMD_HOP = 2                       # slice2 and s8: cmd pin register + cmd_o register per hop
# Scalar-chain hop = a property of the slice RTL the commands are compiled for (TOK-QK/S8B 10-25):
#   'slice2' qfd_dv_slice2 / qfd_dv_scalar2: fdn pin register + dn_o register                                  = 2
#   's8'     the bound compute-die slice (bound_r8: qfd_dv_s8_flat / s8_ce_w5 / ce_l9h / ce_e5), u_sc = qfd_dv_s5_sc2_leaf
#            (k79 netlist of qfd_dv_s5_sc2): fdn scu_q pin register + sc2 face-in f_up + qfd_dv_scalar3 dn_o + sc2
#            face-out dn_o (qfd_dv_s5_sc2 header: every input lands in a face register, every output leaves from one) = 4
# Selected by DV2_S8DIE=1 (tb_qfd_dv2 FACE 3, dv_bench2) -- never edited per run; dv_lower_bench --calibrate measures it.
# The bound die's intra-slice partition crossings (bind_latency x_fw_sc / x_sc_fw) are NOT in this hop: they are die
# terms of the bound top, not of the slice RTL (see results/rtl/tokqw_1024/stages/stg_die).
SC_HOP_BY_SLICE = {'slice2': 2, 's8': 4}
SLICE_RTL = 's8' if os.environ.get('DV2_S8DIE', '0') == '1' else 'slice2'
SC_HOP = SC_HOP_BY_SLICE[SLICE_RTL]
# x stream (st_up / st_dn) pass hop, same rule:
#   'slice2' qfd_dv_stream: sw_q pin register + so_e / so_w register                                            = 2
#   's8'     u_stm = qfd_dv_s6_stm -> qfd_dv_stream_tile (QW-STREAM3): sw_q pin + DP 2 (face root + leaf) + so_e   = 4
#            (stream_tile header: 'sw_i / se_i: reference inputs delayed DP = 2 edges ... relay outputs on the reference edge')
# The D2D return chain (ch, 2 edges a hop) and the cmd chain are unchanged in s8 (vec calibrate d2d ages equal for all slices).
ST_HOP_BY_SLICE = {'slice2': 2, 's8': 4}
ST_HOP = ST_HOP_BY_SLICE[SLICE_RTL]
W_VM, W_X, W_D2D, W_SC = 0, 1 << 22, 2 << 22, 3 << 22
SPLIT_LEVEL = {128: 7, 256: 8, 512: 9}


class LowerError(Exception):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def f32(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def pack(fields):
    v, s = 0, 0
    for val, w in fields:
        val = int(val)
        if not 0 <= val < (1 << w):
            raise LowerError(f'field value {val} does not fit {w} bits')
        v |= val << s
        s += w
    return v, s


# ------------------------------------------------------------------------------------------------ 1. slice map
def slice_map(model=DV_MODEL, relay=RELAY):
    d = json.loads((ROOT / model).read_text())
    sl = sorted((i for i in d['insts'] if i['n'].startswith('dvs_')), key=lambda i: i['x'])
    names = [i['n'] for i in sl]
    if len(names) != NSLICE or names[0] != 'dvs_W5' or names[-1] != 'dvs_E5':
        raise LowerError(f'die model slices {names}: expected 12, dvs_W5 .. dvs_E5 W to E')
    r = json.loads((ROOT / relay).read_text())
    by = {}
    for b in r['buses']:
        s_, d_ = b['src'], b['dst']
        if s_['inst'].startswith('dvs_') and d_['inst'].startswith('dvs_'):
            by[(s_['inst'], s_['port'][:-1], d_['inst'])] = b
    hops = []
    for a, b in zip(names, names[1:]):
        # the cmd chain runs W5 -> E5; slice faces are named per master face (E-row masters are MY: face swap)
        c = [v for (si, sp, di), v in by.items() if si == a and di == b and sp.startswith('cmd_')]
        s = [v for (si, sp, di), v in by.items() if si == b and di == a and sp.startswith('sc_')]
        if len(c) != 1 or len(s) != 1:
            raise LowerError(f'relay table: {a} -> {b} cmd hop {len(c)} / {b} -> {a} sc hop {len(s)} (one each expected)')
        age = lambda v: v.get('age_edges', v['stages']) if v.get('age_edges') is not None else v['stages']
        hops.append(dict(frm=a, to=b, cmd_bus=c[0]['id'], cmd_extra=age(c[0]), sc_bus=s[0]['id'], sc_extra=age(s[0])))
    cmd_at = [0]
    for h in hops:
        cmd_at.append(cmd_at[-1] + CMD_HOP + h['cmd_extra'])
    return dict(names=names, ids={n: k for k, n in enumerate(names)}, hops=hops, cmd_arrival=cmd_at,
                sources={model: sha(ROOT / model), relay: sha(ROOT / relay)},
                rule='SETID 0 enters at dvs_W5; slice k latches id k (qfd_dv_slice2 SETID: id, forward id + 1)')


def sc_down_edges(smap, k, m):
    """edges a downward scalar word leaving slice k (dn_o register) needs to leave slice m < k"""
    return sum(SC_HOP + h['sc_extra'] for h in smap['hops'][m:k])


# ------------------------------------------------------------------------------------------------ 2. ownership
def ownership(plan=PLAN):
    p = json.loads((ROOT / plan).read_text())
    mats = {m['name']: m for m in p['layer_matrix_layout']}
    mats['lm_head'] = p['head_geometry']
    out = {}
    for name, m in mats.items():
        lv = SPLIT_LEVEL.get(m['split'])
        if lv is None:
            raise LowerError(f'{name}: split {m["split"]} has no slice2 station mode')
        T = m['tiles_per_round']
        want = {7: 2 * NSLICE, 8: NSLICE, 9: NSLICE // 2}[lv]
        if T != want:
            raise LowerError(f'{name}: {T} tiles a round at split {m["split"]} (level {lv}); the 12-slice die finishes {want}')
        nblk = math.ceil(m['rows'] / BLOCK)
        if nblk > T * m['rounds']:
            raise LowerError(f'{name}: {nblk} row blocks > {T} x {m["rounds"]} rounds')
        rows = []
        for b in range(nblk):
            t, rnd = b % T, b // T
            if lv == 8:
                s, pair, mode = t, None, 'L8'
            elif lv == 7:
                s, pair, mode = t // 2, t % 2, 'L7'
            else:
                s, pair, mode = 2 * t, None, 'L9 receiver (sender 2t+1)'
            rows.append(dict(block=b, rows=[BLOCK * b, min(BLOCK * (b + 1), m['rows'])], slice=s, round=rnd, pair=pair,
                             mode=mode))
        out[name] = dict(split=m['split'], level=lv, tiles_per_round=T, rounds=m['rounds'], blocks=rows)
    own = lambda n: [[r['block'] for r in out[n]['blocks'] if r['slice'] == s] for s in range(NSLICE)]
    if own('o') != own('down'):
        raise LowerError('o and down own different row blocks: the residual add would not be slice-local')
    out['residual'] = dict(blocks_per_slice=own('o'), rule='= o / down ownership (residual add slice-local)')
    out['sources'] = {plan: sha(ROOT / plan)}
    return out


# ------------------------------------------------------------------------------------------------ 3. VM map
def vm_map(own):
    """per slice local FP32 regions; one layout for every slice (the PROG words are slice-specific only in the block
    index fields), sized for the largest owner."""
    nres = max(len(b) for b in own['residual']['blocks_per_slice'])
    regions = [('X', BLOCK * nres, 'residual x rows (owned o / down blocks, ascending global block)'),
               ('SSX', 16, 'root: the 32-slot total spill (ROOT ss; unused with fuse 1)'),
               ('RX', 16, 'rb landing: r = rsqrt(sum / 4096 + eps) (ROOT rx, every slice)')]
    out, a = {}, 0
    for n, size, what in regions:
        a = (a + 15) // 16 * 16
        out[n] = dict(base=a, size=size, what=what)
        a += size
    if a > VM_EL:
        raise LowerError(f'VM map {a} elements > {VM_EL}')
    return out


# ------------------------------------------------------------------------------------------------ 4. SU words / PROG
SU_FIELDS = [('go', 1), ('nout', 18), ('nin', 18), ('asrc', 1), ('a', 24), ('aso', 24), ('asi', 24), ('bsrc', 1),
             ('b', 24), ('bso', 24), ('bsi', 24), ('csrc', 1), ('c', 24), ('cso', 24), ('csi', 24), ('ma', 2), ('mb', 2),
             ('ad', 3), ('sfu', 3), ('mc', 1), ('md', 1), ('dst', 2), ('d', 24), ('dso', 24), ('dsi', 24), ('red', 2),
             ('redsq', 1), ('rb', 24), ('rso', 24), ('imm1', 32), ('imm2', 32)]


def su_word(**f):
    """the 457-b SU issue word (qfd_dv_slice2 si[456:0]); go (bit 0) is 0 in the store (the slice issues it)."""
    bad = set(f) - {n for n, _ in SU_FIELDS}
    if bad or f.get('go'):
        raise LowerError(f'SU word fields {bad or "go"}')
    if f.get('nin', 1) < 1 or f.get('nout', 1) < 1:
        raise LowerError('SU op with nin / nout 0')
    v, n = pack([(f.get(k, 0), w) for k, w in SU_FIELDS])
    assert n == 457
    return v


def su_unpack(v):
    out, s = {}, 0
    for k, w in SU_FIELDS:
        out[k] = (v >> s) & ((1 << w) - 1)
        s += w
    return out


def prog_words(words):
    """SU words (pidx order) -> kind-3 stream table payloads [(eaddr pair, payload 1024)]"""
    if not 0 < len(words) <= PROG_N:
        raise LowerError(f'{len(words)} SU words (PROG holds {PROG_N})')
    w = list(words) + ([0] if len(words) % 2 else [])
    out = []
    for i in range(0, len(w), 2):
        if w[i] >> 457 or w[i + 1] >> 457:
            raise LowerError('SU word wider than 457 b')
        out.append((i // 2, w[i] | (w[i + 1] << 512)))
    if out[-1][0] >> 8:
        raise LowerError('PROG pair index beyond tw_addr[7:0]')
    return out


def stream_table_word(kind, dst, eaddr, payload, src=0xE, tag=0):
    """1,088-b stream word {v, kind 3, dst 4, src 4, eaddr 24, tag 28, payload 1024} (qfd_dv_stream)"""
    if kind not in (1, 2, 3) or not 0 <= dst < 16 or eaddr >> 24 or payload >> 1024:
        raise LowerError('stream table word field out of range')
    ctl, _ = pack([(tag, 28), (eaddr, 24), (src, 4), (dst, 4), (kind, 3), (1, 1)])
    return (ctl << 1024) | payload


# ------------------------------------------------------------------------------------------------ 5. commands
def _cmd(kind, fields, dst):
    if not (0 <= dst <= 11 or dst == 15):
        raise LowerError(f'cmd dst {dst}')
    v, n = pack([(1, 1), (kind, 3)] + fields)
    if n > 112:
        raise LowerError('command fields overlap dst [115:112]')
    return v | (dst << 112)


def cmd_setid(i):
    return _cmd(7, [(i, 4)], 0)


def cmd_su(pidx, dst):
    return _cmd(1, [(pidx, 9)], dst)


def cmd_root(dst, root, nb, ss, fuse=0, rx=0, eps=0, k=0, amnb=0, rdir=0):
    if nb > 32 or (root and nb == 0):
        raise LowerError(f'ROOT nb {nb} (32 slots)')
    return _cmd(3, [(root, 1), (nb, 6), (ss, 24), (fuse, 1), (rx, 24), (eps, 32), (k, 5), (amnb, 6), (rdir, 1)], dst)


def cmd_ports(dst, ar_base=0, dd_base=0, ar_en=0, dd_en=0, em_base=0, em_en=0):
    return _cmd(4, [(ar_base, 24), (dd_base, 24), (ar_en, 1), (dd_en, 1), (em_base, 24), (em_en, 1)], dst)


def cmd_stn(dst, mode, wsrc, nwords, sbase, sdst, dbase, *, kc, amax=0):   # kc mandatory (MU-DQ-SLICEKC 10-19)
    # kc: k steps per (round, j) of the op's tiles (they stream the running accumulator every k step; qfd_dv_redstn2
    # keeps only the k = kc - 1 block of every pair: STN [66:59] = kc - 1, QW-DIEFIX 10-19; [52:51] = MU STN user)
    if not 1 <= kc <= 256:
        raise LowerError(f'STN kc {kc} (1..256)')
    return _cmd(2, [(mode, 2), (wsrc, 1), (nwords, 8), (sbase, 9), (sdst, 2), (dbase, 24), (amax, 1), (0, 8), (kc - 1, 8)],
                dst)


def cmd_stream(dst, dirs, tag):
    return _cmd(5, [(dirs, 2), (tag, 28)], dst)


def cmd_amax(dst, clear=0, emit=0, arx=0, gather=0):
    return _cmd(6, [(clear, 1), (emit, 1), (arx, 1), (gather, 1)], dst)


def cmd_xc(dst, mode, words, tag):
    return _cmd(0, [(0, 2), (mode, 1), (words, 16), (tag, 32)], dst)


def cmd_rope_arm(dst, crom_word):
    # QW-LAYERGAP 10-20 (qfd_dv_slice2 RP 1): XC sub 1 = ROPE ARM, cmd[15:6] = CROM 16-pair word base; the slice writes the
    # next 8 group-1 D2D return words (beat k = 0..7) into CROM word base + k // 2, bank k % 2, then disarms
    if not 0 <= crom_word < 1024:
        raise LowerError(f'ROPE ARM CROM word {crom_word}')
    return _cmd(0, [(1, 2), (crom_word, 10)], dst)


def decode_cmd(c):
    """the qfd_dv_slice2 decode (mirror of its cmd_q field slices)"""
    kind, dst = (c >> 1) & 7, c >> 112
    b = lambda lo, w: (c >> lo) & ((1 << w) - 1)
    d = dict(go=c & 1, kind=kind, dst=dst)
    if kind == 1:
        d.update(pidx=b(4, 9))
    elif kind == 2:     # STN (qfd_dv_slice2 u_stn / u_amax): kc = cmd[66:59] + 1 (redstn2 last-k), MU user [52:51]
        d.update(mode=b(4, 2), wsrc=b(6, 1), nwords=b(7, 8), sbase=b(15, 9), sdst=b(24, 2), dbase=b(26, 24),
                 amax=b(50, 1), user=b(51, 2), kc=b(59, 8) + 1)
    elif kind == 3:
        d.update(root=b(4, 1), nb=b(5, 6), ss=b(11, 24), fuse=b(35, 1), rx=b(36, 24), eps=b(60, 32), k=b(92, 5),
                 amnb=b(97, 6), rdir=b(103, 1))
    elif kind == 4:
        d.update(ar_base=b(4, 24), dd_base=b(28, 24), ar_en=b(52, 1), dd_en=b(53, 1), em_base=b(54, 24), em_en=b(78, 1))
    elif kind == 0:     # XC: sub 0 COLL {mode, words, tag}; sub 1 ROPE ARM {CROM word} (QW-LAYERGAP, RP 1)
        d.update(sub=b(4, 2))
        if d['sub'] == 0:
            d.update(mode=b(6, 1), words=b(7, 16), tag=b(23, 32))
        elif d['sub'] == 1:
            d.update(crom_word=b(6, 10))
    elif kind == 7:
        d.update(id=b(4, 4))
    return d


# ------------------------------------------------------------------------------------------------ the lowering
def load_ages(path=AGES):
    p = ROOT / path
    if not p.exists():
        raise LowerError(f'{path} missing: measure it (rtl/test/qwen_dv/dv_lower_bench.py --calibrate)')
    a = json.loads(p.read_text())
    for k in ('ssq_psum_out', 'root_cfg_lead'):
        if k not in a:
            raise LowerError(f'{path}: no {k}')
    return a


def isa_rmsnorm(prog, lowering=None):
    """the q3h programme's global sum of squares + its rsqrt, as the lowering reads them (fail closed on any field the
    DV lowering does not reproduce exactly)"""
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_qwen_fullshape_isa_w12 as ISA
    ops = [ISA.decode_instruction(int(w, 16)) for w in (ROOT / prog).read_text().split()]
    ssq = [pc for pc, o in enumerate(ops) if o['unit'] == 2 and o['su_nin'] == 4096 and o['red'] == 1 and o['red_sq'] == 1]
    rsq = [pc for pc, o in enumerate(ops) if o['unit'] == 2 and o['sfu'] == 3 and o['su_nin'] == 1 and o['ma'] == 3]
    if not ssq or len(rsq) != 2:
        raise LowerError(f'programme: sum-of-squares ops {ssq}, rsqrt ops {rsq}')
    for pc in ssq:
        o = ops[pc]
        if (o['a_si'], o['a_so'], o['su_nout'], o['r_so']) != (1, 0, 1, 0):
            raise LowerError(f'PC{pc}: not one contiguous 4,096-element sum of squares')
    out = []
    for pc in rsq:
        o = ops[pc]
        k = -math.log2(struct.unpack('<f', struct.pack('<I', o['imm1']))[0])
        if k != int(k) or not 0 < k < 32 or o['ad'] != 4:
            raise LowerError(f'PC{pc}: imm1 is not 2^-k / ad is not +imm2: the fused ROOT cannot reproduce it')
        out.append(dict(pc=pc, k=int(k), eps=o['imm2'], src=o['a_base']))
    return dict(ssq_pcs=ssq, rsqrt=out, sums=sorted({ops[pc]['r_base'] for pc in ssq}))


def lower(mutant=None, ages=None, prog='results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex'):
    """mutant (unit-bench witness only): 'rso1' = PSUM tags 1 apart (wrong block positions);
    'broadcast' = the SSQ as ONE dst-15 command (what ctlm_image emits today): scalar-chain collisions."""
    smap = slice_map()
    own = ownership()
    vm = vm_map(own)
    ages = ages or load_ages()
    isa = isa_rmsnorm(prog)
    k, eps = isa['rsqrt'][0]['k'], isa['rsqrt'][0]['eps']
    if any((r['k'], r['eps']) != (k, eps) for r in isa['rsqrt']):
        raise LowerError('the two norms use different 1/n or eps')
    blocks = own['residual']['blocks_per_slice']
    nb = sum(len(b) for b in blocks)
    if nb != 4096 // BLOCK or sorted(x for b in blocks for x in b) != list(range(nb)):
        raise LowerError('residual blocks do not tile the 4,096 rows')
    # PROG: one SSQ word per slice (pidx 0)
    prog_img, ssq = {}, {}
    for s in range(NSLICE):
        bl = blocks[s]
        stride = bl[1] - bl[0] if len(bl) > 1 else 0
        if any(b2 - b1 != stride for b1, b2 in zip(bl, bl[1:])):
            raise LowerError(f'slice {s}: owned blocks {bl} are not one arithmetic progression (r_so)')
        rso = 1 if mutant == 'rso1' else stride
        w = su_word(nout=len(bl), nin=BLOCK, a=vm['X']['base'], aso=BLOCK, asi=1, red=1, redsq=1,
                    rb=W_SC | bl[0], rso=rso)
        prog_img[s] = [w]
        ssq[s] = dict(pidx=0, blocks=bl, tags=[bl[0] + j * rso for j in range(len(bl))], word=f'{w:0115x}')
    # schedule (edges at the dvs_W5 cmd pin): SETID, ROOT cfg of every slice, then the 12 SSQ commands so that no two
    # downward scalar words want to leave one slice on one edge
    ev = [(0, cmd_setid(0), 'SETID 0')]
    t = 4 + smap['cmd_arrival'][-1]
    root_s = 0
    for s in range(NSLICE):
        c = cmd_root(s, int(s == root_s), nb, vm['SSX']['base'], fuse=int(s == root_s), rx=vm['RX']['base'],
                     eps=eps if s == root_s else 0, k=k if s == root_s else 0, rdir=0)
        ev.append((t + s, c, f'ROOT s{s}' + (' (root, fused r)' if s == root_s else '')))
    t0 = t + NSLICE + ages['root_cfg_lead']
    L = ages['ssq_psum_out']                     # PSUM j leaves the slice's dn_o this many edges after the cmd lands
    occ, sched = {}, {}

    def words(s, entry):
        for j in range(len(blocks[s])):
            leave = entry + smap['cmd_arrival'][s] + L[j]
            for m in range(s, -1, -1):
                yield (m, leave + sc_down_edges(smap, s, m)), j

    if mutant == 'broadcast':                    # as ctlm_image issues SU ops today: ONE dst-15 command
        for s in range(NSLICE):
            sched[s] = t0
            for key, j in words(s, t0):
                occ.setdefault(key, []).append((s, j))
        ev.append((t0, cmd_su(0, 15), 'SSQ broadcast (dst 15)'))
    else:
        entry = t0
        for s in range(NSLICE - 1, -1, -1):      # far first: their words pass every nearer slice
            while entry in {x[0] for x in ev} or any(k_ in occ for k_, _ in words(s, entry)):
                entry += 1
            for key, j in words(s, entry):
                occ.setdefault(key, []).append((s, j))
            sched[s] = entry
            ev.append((entry, cmd_su(0, s), f'SSQ s{s} blocks {blocks[s]}'))
            entry += 1
    ev.sort(key=lambda e: e[0])
    if len({e[0] for e in ev}) != len(ev):
        raise LowerError('two commands enter the chain on one edge')
    coll = sorted((k_, v) for k_, v in occ.items() if len(v) > 1)
    if coll and mutant != 'broadcast':
        raise LowerError(f'scalar chain collisions {coll[:3]}')
    for _, c, _ in ev:
        decode_cmd(c)
    # the root's last PSUM: from the farthest-arriving word
    last_ps = max(e for (m, e) in occ if m == 0)
    return dict(
        schema='opentallas.qwen.dv-lowering.v1', tool='tools/qwen_layerbench/dv_lower.py', mutant=mutant,
        slice_map=smap, ownership=own, vm=vm, ages=ages, isa=isa,
        prog={s: [f'{w:0115x}' for w in ws] for s, ws in prog_img.items()},
        prog_stream={s: [dict(eaddr=a, payload=f'{p:0256x}') for a, p in prog_words(ws)] for s, ws in prog_img.items()},
        ssq=ssq, ssq_entry=sched, root=dict(slice=root_s, nb=nb, k=k, eps=eps, rx=vm['RX']['base'], ss=vm['SSX']['base']),
        commands=[dict(edge=e, cmd=f'{c:029x}', label=l) for e, c, l in ev],
        expected=dict(last_psum_leaves_root_dn=last_ps, collisions=[[list(k_), v] for k_, v in coll]),
        not_lowered=['norm apply h = (x r) g + BF16 stream (CROM gains, window 01 x packer)', 'residual adds (AR landings, PORTS)',
                     'QK-norm / RoPE on the qkv receiver slices', 'STN commands of qkv / o / gate-up / down / LM head',
                     'XC collectives', 'SiLU x up', 'LM-head AMAX', 'stage-0 slice commands (embedding landing em_base)'],
        die_gaps=['dvs_W5.st_wi is tied 1088\'h0 on the die (dv_case chain-end idle rule) and no master emits stream '
                  'table words (kinds 1..3): the slice PROG / CROM / BTAB stores have NO load path on the die; this '
                  'image reaches them only in a bench that drives W5.st_wi'])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutant', choices=('rso1', 'broadcast'))
    a = ap.parse_args()
    try:
        r = lower(a.mutant)
    except LowerError as e:
        print(f'DV_LOWER REFUSED: {e}')
        return 2
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(dict(commands=len(r['commands']), slices=NSLICE, root=r['root'], last_psum=r['expected']['last_psum_leaves_root_dn'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
