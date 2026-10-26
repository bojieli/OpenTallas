#!/usr/bin/env python3
"""TOK-DS-4 (10-26): lowering of the indexer score scan (attn.idx.score -> dsdv_idx_rg3 IDX_S job) and the new-key row
write (attn.idx.newkey -> dsdv_svc_att IK_ROW q frame) TOGETHER: both use ONE HBM index-key layout, so the compiler
emits them from one layout function and the two benches are chained (the svc bench's observed IK_ROW writes are the
rg3 bench's HBM delta).

KEY LAYOUT (dsdv_idx_rg.sv:11-20, dsdv_svc_att.sv IK_ROW, tb_dsdv_idx_rg3 place()): position p, word j = p >> 4,
lane i = p & 15, region rg = i ^ j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12] (= the svc slice sid owning the PC pair), group
g = j >> 4, PC g & 1 (die PC 2 rg + (g & 1)), block n = g >> 1, a = KB + 34 n: codes[255:0] at a + 2 c, codes[511:256]
at a + 2 c + 1, scales at a + 32 + (c >> 3) bytes 4 (c & 7) .. + 3, c = j & 15.  Key word {4 UE8M0 scales, 128 E2M1
codes, dim d at [4 d + 3:4 d]} (ot_hdc_v41x_idx.sv key format) = LC.pack_fp4_ue8m0 bytes little-endian.

TOK-DS-6 (10-26, COORD tok-ds-5 ruling 1): KEY SHARD.  The rank quarter is NOT scanned on one die: lower_bk SHARD_K
(S81-SCAND option D; L2 / L8 / L14 k = 3, L20 k = 6) puts a rank's keys on k adjacent TP4 stages (one HBM stack a die),
shard j = lower_bk.shard_range(q4, k, j) = [r q4 + j ceil(q4 / k), ...) (L14: 43,691 / 43,691 / 43,690 keys).  Every
shard die runs its own IDX_S job over its shard [B, B + N) (B need not be block aligned: the reader's lane-valid
mask clips the first / last word) and its keys sit at KB = IKB - 34 (B >> 9) on its own stack; the new key is written
(IK_ROW) only by the svc job of the shard die that owns its position.  The die index comes from ctx shard_die (lower_bk
convention) or OT_IDX_SHARD_DIE (default 0, the rank's home / tree root); k from ctx shard_k or lower_bk.SHARD_K.
Before TOK-DS-6 the scan ran k = 1 (the whole 131,072-key quarter on one die: 25,103 edges, 7.459 % AR).

RANK-LOCAL REGION (k = 1 form; with k > 1 read "shard" for "quarter"): rank r scans its contiguous quarter [B, B + N) = [r q4, min(n, (r + 1) q4)) (dv_layer_fixtures
indexer, q4 = ceil(n / 4), n = keys after this position's append).  Positions are absolute in both units (rg3 spec B,
IK_ROW pos), so the compiler offsets the base: KB = IKB - 34 (B >> 9) (mod 2^30), i.e. the rank's 256 blocks occupy
sectors IKB .. IKB + 34 * 256 - 1 of every PC (no space for the other ranks' keys).  IKB = 0x8000 is above the
lower_svc window ring (WB 0x100 + 68 u) and the compressed-row region (SB 0x1000 + 9 (g >> 9) < 0x5800).

NEW KEY: attn.idx.newkey (compressed position p = n - 1, the fixture's index_keys count) belongs to rank p // q4.  At
L14 (n = 524288, q4 = 131072) p = 524287 is the LAST key of rank 3's quarter: rank 3's svc attention job carries ONE
IK_ROW frame (type 15, len 1) -- lower_svc appends it to the job's q frames (it must pass the ot_s81_svc_job gate as a
frame of the armed job) at >= the op's priced start; the other ranks emit nothing (the op is a no-op on their die).
Static order (no ready / credit): the 3 writes issue on PC 2 rg + p[8] within IK_WR_EDGES of the frame's payload word
at the slice, and the IDX_S header is sent >= IK_GUARD edges after it, so the writes precede the reader window of
that controller (a slice request in a reader slot is a controller fault) and the scan's read of the key.

IDX_S JOB (dsdv_idx_rg.sv:22-45): type 4, len 64, spec B / N / k / KB / T0 / P / ik / om; payload word 2 h = head h's
128 FP4 codes (attn.idx.q, UE8M0 per 32), word 2 h + 1 = {[47:32] BF16 head weight (attn.idx.weights), [31:0] 4
scales}.  Rate: one 16-key word every P edges on the score chain; P = 3 is the scan rung proven by the S81-IDX3R
campaign at 87,382 keys (P = 2 failed the rate at that size on the rg2 probe), so a 131,072-key quarter = 8,192 words
= 24,576 edges + T0 + 10.  The price (attn.idx.score) assumes ~2,951.

Benches (chained, run_idx_l14.sh): (1) tb_dsdv_svc_att_ik +img (one dsdv_svc_att x 16 sids, the compiled IK_ROW frame,
golden = these layout writes) -> dump of the observed writes; (2) tb_dsdv_idx_rg3 +img (8 rg3 + 16 dsfd_ctrl_rg3 +
HBM model; HBM = the rank's state keys + the svc dump; expected = fixture attn.idx.score of the quarter).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

OPS = [r'^attn\.idx\.(newkey|score)$']

ROOT = Path(__file__).resolve().parents[3]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
TP = 4
IKB = 0x8000                 # rank-local index-key region base (PC-local sector, every PC)
USER = 3                     # = lower_svc USER
IDX_TAG = 0x41               # IDX_S job tag (selector lane words carry it)
K_SEL = 512
T0 = 400                     # run-ahead window (S81-IDX3R campaign value)
P_SCAN = 3                   # scan rung (S81-IDX3R b3 pass_l20 / pass_l20s2 at 87,382 keys)
IK_STRAP = 4                 # 877 u_bk_sel ik strap (lower_bk straps)
IK_WR_EDGES = 4              # IK payload at the slice q pin -> the 3 write requests leave the slice (bench-measured)
IK_GUARD = 64                # IK frame payload edge -> IDX_S header edge (>= slice->PC + controller + margin)
BENCH = 'results/rtl/s81_l14_idx_k3_1026'   # TOK-DS-6: the SHARD_K = 3 bench (k = 1 record: s81_l14_idx_1026)
UNIT_NK = 'dsdv_svc_att IK_ROW (q frame type 15) of the owning svc slice (sid = region hash) in the svc attention job'
UNIT_SC = 'idx chain u_iqf -> u_irg_00..07 (dsdv_idx_rg3) score chain -> u_bk_sel vi_idx (IDX_S job)'
INSTS = [f'u_irg_{i:02d}' for i in range(8)] + ['u_iqf']


def hj(j):
    return (j ^ (j >> 4) ^ (j >> 8) ^ (j >> 12)) & 15


def place(p, kb):
    """(region rg, die PC, code sector 0, code sector 1, scale sector, scale byte offset) of key position p"""
    j, i = p >> 4, p & 15
    rg = i ^ hj(j & 0xFFFF)
    g = j >> 4
    n, c = g >> 1, j & 15
    a = (kb + 34 * n) & ((1 << 30) - 1)
    return rg, 2 * rg + (g & 1), a + 2 * c, a + 2 * c + 1, a + 32 + (c >> 3), 4 * (c & 7)


def key_word(codes64, sc4):
    """packed E2M1 bytes (low nibble first) + 4 UE8M0 bytes -> the 544-b key word"""
    return int.from_bytes(bytes(np.asarray(codes64, np.uint8)), 'little') | int.from_bytes(bytes(np.asarray(sc4, np.uint8)), 'little') << 512


def _fx(fx):
    fx = Path(fx)
    meta = json.loads((fx / 'meta.json').read_text())
    files = json.loads((fx / 'files.json').read_text())
    ops = json.loads((fx / 'ops.json').read_text())
    return fx, meta, files, ops


def _ld(fx, rel, info):
    return np.fromfile(fx / rel, dtype=np.dtype(info['dtype'])).reshape(info['shape'])


def shard_of(layer, k=None, die=None):
    """(k dies a rank's keys are sharded over, this die's index) -- lower_bk.SHARD_K / ctx / OT_IDX_SHARD_DIE"""
    if k is None:
        import lower_bk
        k = lower_bk.shard_k(str(layer))
    if die is None:
        die = int(os.environ.get('OT_IDX_SHARD_DIE', '0'))
    k, die = int(k), int(die)
    assert 0 <= die < k, f'shard die {die} not in 0..{k - 1}'
    return k, die


def quarter(meta, k=None, die=None):
    """(n keys after the append, q4, B, N, KB, new-key position, owner rank, owner shard die) of THIS shard die of the
    fixture's indexer layer (k = 1: the rank quarter)"""
    import lower_bk
    k, die = shard_of(meta.get('layer', 'L%d' % int(meta['layer_index'])), k, die)
    li = str(meta['layer_index'])
    rows = meta['state']['rows'][li] if isinstance(meta['state'], dict) else None
    assert rows and rows.get('index_keys'), 'fixture state has no index keys (not an indexer layer)'
    n_pre = int(rows['index_keys'])
    n = n_pre + 1
    q4 = -(-n // TP)
    r = int(meta['rank'])
    B4 = r * q4
    N4 = min(n, B4 + q4) - B4
    assert B4 % 512 == 0, 'rank quarter not block aligned'
    lo, m = lower_bk.shard_range(N4, k, die)
    B, N = B4 + lo, m
    assert N > 0, 'empty shard'
    kb = (IKB - 34 * (B >> 9)) % (1 << 30)
    owner = n_pre // q4
    o_die = next(j for j in range(k) if lower_bk.shard_range(N4, k, j)[0] <= n_pre - owner * q4 <
                 sum(lower_bk.shard_range(N4, k, j)))
    return dict(n=n, q4=q4, B=B, N=N, KB=kb, p_new=n_pre, owner=owner, rank=r, k=k, die=die, owner_die=o_die,
                B4=B4, N4=N4, owns_new=(owner == r and o_die == die))


def _lc():
    sys.path.insert(0, str(ROOT / 'tools'))
    import rtl_v41_fullshape_layer_campaign as LC
    return LC


def newkey_word(fx):
    """the 544-b key word of attn.idx.newkey (FP4 QDQ values -> codes + UE8M0, round-trip asserted by the packer)"""
    fx, meta, files, ops = _fx(fx)
    LC = _lc()
    v = _ld(fx, f'ops/attn.idx.newkey.bin', ops['attn.idx.newkey']).astype(np.float32)
    nib, sc = LC.pack_fp4_ue8m0(v.reshape(1, -1))
    return key_word(nib[0], sc[0])


def ik_frame(fx, tag, mutant=None, k=None, die=None):
    """IK_ROW frame words [header, payload] for the owning (rank, shard die) (None on every other die)"""
    from lower_svc import hdr
    _, meta, _, _ = _fx(fx)
    q = quarter(meta, k, die)
    if not q['owns_new']:
        return None
    k = newkey_word(fx)
    kb = (IKB if mutant == 'ik_kb' else q['KB'])        # MUTANT ik_kb: the region base without the rank offset
    spec = kb | ((k >> 512) & 0xFFFFFFFF) << 32
    return [hdr(15, 1, tag, spec=spec, pos=q['p_new'], user=USER), k & ((1 << 512) - 1)]


def ik_writes(fx, k=None, die=None):
    """golden: the 3 HBM writes of the new key {sid, PC parity, sector, strobe, data} (layout, fixture key)"""
    _, meta, _, _ = _fx(fx)
    q = quarter(meta, k, die)
    k = newkey_word(fx)
    rg, pc, a0, a1, asc, by = place(q['p_new'], q['KB'])
    sc = (k >> 512) & 0xFFFFFFFF
    return [(rg, pc & 1, a0, 0xFFFFFFFF, k & ((1 << 256) - 1)), (rg, pc & 1, a1, 0xFFFFFFFF, (k >> 256) & ((1 << 256) - 1)),
            (rg, pc & 1, asc, 0xF << by, sc << (8 * by))]


def idx_job(fx, mutant=None, k=None, die=None):
    """IDX_S header + 64 query words of this shard die's scan (mutant 'shard_k1': the TOK-DS-4 whole-quarter spec)"""
    fx, meta, files, ops = _fx(fx)
    LC = _lc()
    q = quarter(meta, 1, 0) if mutant == 'shard_k1' else quarter(meta, k, die)
    qv = _ld(fx, 'ops/attn.idx.q.bin', ops['attn.idx.q']).astype(np.float32)          # [32, 128] FP4 QDQ
    wt = _ld(fx, 'ops/attn.idx.weights.bin', ops['attn.idx.weights']).astype(np.float32)
    wb = wt.view(np.uint32)
    assert not (wb & 0xFFFF).any(), 'index head weights not BF16'
    nib, sc = LC.pack_fp4_ue8m0(qv)
    assert qv.shape == (32, 128)
    h = (4 << 508) | (IDX_TAG << 495) | (64 << 480) | (USER << 449)
    h |= q['B'] | q['N'] << 20 | K_SEL << 41 | q['KB'] << 51 | T0 << 81 | P_SCAN << 97 | IK_STRAP << 101
    ws = [h]
    for hh in range(32):
        ws.append(int.from_bytes(bytes(nib[hh]), 'little'))
        ws.append(int.from_bytes(bytes(sc[hh]), 'little') | int(wb[hh] >> 16) << 32)
    return ws


def state_image(fx, k=None, die=None):
    """{(die PC, sector): 256-b} of this shard die's state keys (its shard without this position's new key)"""
    fx, meta, files, ops = _fx(fx)
    q = quarter(meta, k, die)
    li = meta['layer_index']
    ci, si = files[f'state/kv.ik{li}.codes.bin'], files[f'state/kv.ik{li}.scale.bin']
    lo4, hi4 = ci['rows']
    assert lo4 == q['B4'] and hi4 == min(q['B4'] + q['N4'], q['p_new']), (lo4, hi4, q)
    codes, scs = _ld(fx, f'state/kv.ik{li}.codes.bin', ci), _ld(fx, f'state/kv.ik{li}.scale.bin', si)
    lo, hi = q['B'], min(q['B'] + q['N'], q['p_new'])
    img = {}
    for p in range(lo, hi):
        r = p - lo4
        k = key_word(codes[r], scs[r])
        _, pc, a0, a1, asc, by = place(p, q['KB'])
        img[(pc, a0)] = k & ((1 << 256) - 1)
        img[(pc, a1)] = (k >> 256) & ((1 << 256) - 1)
        img[(pc, asc)] = img.get((pc, asc), 0) | ((k >> 512) & 0xFFFFFFFF) << (8 * by)
    return img


def expected(fx, k=None, die=None):
    """[(lane valid 16, 16 BF16 scores)] per scan word: the fixture golden attn.idx.score of this shard"""
    fx, meta, files, ops = _fx(fx)
    q = quarter(meta, k, die)
    s = _ld(fx, 'ops/attn.idx.score.bin', ops['attn.idx.score']).astype(np.float64)
    assert len(s) == q['n']
    sb = s.astype(np.float32).view(np.uint32)
    assert np.array_equal(sb.view(np.float32).astype(np.float64), s) and not (sb & 0xFFFF).any() and np.all(np.isfinite(s)), \
        'golden index scores not finite BF16'
    B, N = q['B'], q['N']
    j0, j1 = B >> 4, (B + N - 1) >> 4
    out = []
    for j in range(j0, j1 + 1):
        kv, sw = 0, 0
        for i in range(16):
            p = 16 * j + i
            if B <= p < B + N:
                kv |= 1 << i
                sw |= int(sb[p] >> 16) << (16 * i)
        out.append((kv, sw))
    return out


def scan_cycles(N, P=P_SCAN, B=0):
    """IDX_S frame (65 words) + T0 + 10 + P per word: header-to-last-word edges at the first region (rg3 static plan);
    words = (B + N - 1) / 16 - B / 16 + 1 (an unaligned shard base adds a partial first word)"""
    nw = ((B + N - 1) >> 4) - (B >> 4) + 1
    return 65 + T0 + 10 + P * nw


def write_bench(fx, out, tag=0, k=None, die=None):
    """bench images: svc/<v>/{ikq,ikw}.hex (owning shard die only) and rg3/{job,exp,hbm_state}.hex (+ rg3 mutant job
    rg3/job_shard_k1.hex = the TOK-DS-4 whole-quarter spec on this shard's HBM / expectation: must FAIL)"""
    out = Path(out)
    hx = lambda w, b: f'{w:0{-(-b // 4)}x}'  # noqa: E731
    rec = dict(quarter=quarter(_fx(fx)[1], k, die))
    if rec['quarter']['owns_new']:
        for v in (None, 'ik_kb'):
            d = out / 'svc' / (v or 'base')
            d.mkdir(parents=True, exist_ok=True)
            fr = ik_frame(fx, tag, mutant=v, k=k, die=die)
            (d / 'ikq.hex').write_text(''.join(f'1 {hx(w, 512)}\n' for w in fr) + ''.join(f'0 {hx(0, 512)}\n' for _ in range(8)))
            (d / 'ikw.hex').write_text(''.join(f'{s:x} {pc:x} {a:08x} {st:08x} {hx(dd, 256)}\n'
                                               for s, pc, a, st, dd in ik_writes(fx, k, die)))
    d = out / 'rg3'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'job.hex').write_text(''.join(hx(w, 512) + '\n' for w in idx_job(fx, k=k, die=die)))
    (d / 'job_shard_k1.hex').write_text(''.join(hx(w, 512) + '\n' for w in idx_job(fx, mutant='shard_k1')))
    ex = expected(fx, k, die)
    (d / 'exp.hex').write_text(''.join(f'{kv:04x} {hx(s, 256)}\n' for kv, s in ex))
    img = state_image(fx, k, die)
    (d / 'hbm_state.hex').write_text(''.join(f'{pc:02x} {a:08x} {hx(img[(pc, a)], 256)}\n' for pc, a in sorted(img)))
    rec.update(words=len(ex), state_sectors=len(img), scan_cycles=scan_cycles(rec['quarter']['N'], B=rec['quarter']['B']))
    (out / 'image.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def merge(state_hex, dump, out):
    """rg3 HBM image = the state keys + the IK_ROW writes the svc bench observed (strobed bytes over the state)"""
    img = {}
    for ln in Path(state_hex).read_text().splitlines():
        pc, a, d = ln.split()
        img[(int(pc, 16), int(a, 16))] = int(d, 16)
    nw = 0
    for ln in Path(dump).read_text().splitlines():
        s, pc, a, st, d = (int(x, 16) for x in ln.split())
        key = (2 * s + pc, a)
        old, m = img.get(key, 0), sum(0xFF << (8 * b) for b in range(32) if st >> b & 1)
        img[key] = (old & ~m) | (d & m)
        nw += 1
    Path(out).write_text(''.join(f'{pc:02x} {a:08x} {img[(pc, a)]:064x}\n' for pc, a in sorted(img)))
    return nw


# ================================================================================================= family lowering
def _bench_ok():
    sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
    from dv_layer_compile import bench_ok
    return bench_ok(BENCH)


def lower(die, op, ctx):
    name = op['op']
    fx = ctx.get('fixtures')
    unit = UNIT_NK if name.endswith('newkey') else UNIT_SC
    base = dict(unit=unit, insts=(['u_rsv_%02d' % i for i in range(16)] if name.endswith('newkey') else INSTS), bench=BENCH,
                rows=[], templates=[], gunit_rows=[], svc_jobs=[], files={}, events=[])
    if fx is None:
        return dict(base, status='GAP', gap=dict(module='lower_idx', port='fixtures', missing='no fixture dir'))
    _, meta, _, ops = _fx(fx)
    if 'attn.idx.newkey' not in ops or 'attn.idx.score' not in ops:
        return dict(base, status='GAP', gap=dict(module='lower_idx', port='fixtures', missing='not an indexer layer'))
    k_sh, d_sh = shard_of(ctx.get('layer') or meta.get('layer'), ctx.get('shard_k'), ctx.get('shard_die'))
    # lower_svc builds the IK_ROW frame without ctx (shard_of defaults): the ctx shard must equal those defaults
    assert (k_sh, d_sh) == shard_of(meta.get('layer')), \
        f'ctx shard {(k_sh, d_sh)} != lower_svc IK_ROW shard {shard_of(meta.get("layer"))} (set OT_IDX_SHARD_DIE)'

    q = quarter(meta, k_sh, d_sh)
    ok, why = _bench_ok()
    layer = ctx.get('layer')
    st = 'LOWERED' if ok else 'PARTIAL'
    gap = None if ok else dict(module='lower_idx', port=BENCH, missing=f'bench: {why}')
    if name == 'attn.idx.newkey':
        if not q['owns_new']:
            return dict(base, status=st, gap=gap, note=f'no-op on rank {q["rank"]} shard die {q["die"]}/{q["k"]}: the new '
                        f'key (position {q["p_new"]}) belongs to rank {q["owner"]} shard die {q["owner_die"]} (q4 '
                        f'{q["q4"]}); that die\'s svc job carries the IK_ROW frame (bench {BENCH})',
                        owner_rank=q['owner'], owner_die=q['owner_die'])
        import lower_svc
        r = lower_svc.lower(die, dict(op='attn.own_row_write'), ctx)
        ev = [e for e in r.get('events', []) if e.get('tag') == 'attn.IK_ROW']
        assert len(ev) == 2, 'IK_ROW frame missing from the svc job of the owning rank'
        # the frame's q events are emitted once, by lower_svc (attn.own_row_write: every frame of the job)
        return dict(base, status=st, gap=gap, owner_rank=q['owner'], ik_frame_cycle=ev[0]['cycle'],
                    files={f'prog/idx/{layer}/ik_writes.json': json.dumps(
                        [dict(sid=s, pc=2 * s + pc, sector=a, strobe=f'{stb:08x}') for s, pc, a, stb, _ in ik_writes(fx)],
                        indent=1) + '\n'})
    # attn.idx.score: the IDX_S job of this rank's quarter
    t0 = int(np.ceil(float(op.get('start', 0))))
    import lower_svc
    t_ik = None
    if q['owns_new']:
        r = lower_svc.lower(die, dict(op='attn.own_row_write'), ctx)
        for e in r.get('events', []):
            if e.get('tag') == 'attn.IK_ROW':
                t_ik = max(c for c, _, _ in e['words'])
        if t_ik is not None:
            t0 = max(t0, t_ik + IK_GUARD)
    ws = idx_job(fx, k=k_sh, die=d_sh)
    cyc = scan_cycles(q['N'], B=q['B'])
    words = [[t0 + k, f'{(w << 1) | 1:x}', f'{(1 << 513) - 1:x}'] for k, w in enumerate(ws)]
    ev = [dict(cycle=t0, inst='u_iqf', port='qi', ports=['qi'], dir='in', kind='IDXJ', tag='attn.idx.score',
               payload=f'IDX_S shard {q["die"]}/{q["k"]} B {q["B"]} N {q["N"]} k {K_SEL} KB {q["KB"]} T0 {T0} P {P_SCAN} ik {IK_STRAP}', words=words,
               valid_bit=0, producer_gap='the IDX_S frame reaches the idx chain from the slice iq send (s_3S_C -> iqf); '
                                          'that xs field programme is not lowered, the bench drives the frame at the '
                                          'chain input')]
    return dict(base, status=st, gap=gap, events=ev, idx_job=dict(B=q['B'], N=q['N'], KB=q['KB'], T0=T0, P=P_SCAN,
                tag=IDX_TAG, ik=IK_STRAP, rank=q['rank'], shard_k=q['k'], shard_die=q['die'], t_hdr=t0, t_ik_payload=t_ik, cycles_model=cyc,
                priced=round(float(op.get('end', 0)) - float(op.get('start', 0)), 1)),
                files={f'prog/idx/{layer}/idx_job.hex': ''.join(f'{w:0128x}\n' for w in ws)})


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='lower_idx bench images / rg3 HBM merge')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a1 = sub.add_parser('images'); a1.add_argument('--fixtures', required=True); a1.add_argument('--out', required=True)
    a1.add_argument('--k', type=int, default=None, help='shard dies a rank (default lower_bk.SHARD_K[layer])')
    a1.add_argument('--die', type=int, default=None, help='shard die (default OT_IDX_SHARD_DIE or 0)')
    a2 = sub.add_parser('merge'); a2.add_argument('state'); a2.add_argument('dump'); a2.add_argument('out')
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if a.cmd == 'images':
        print(json.dumps(write_bench(a.fixtures, a.out, k=a.k, die=a.die)))
    else:
        print('merged writes', merge(a.state, a.dump, a.out))


if __name__ == '__main__':
    main()
