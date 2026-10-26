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

RANK-LOCAL REGION: rank r scans its contiguous quarter [B, B + N) = [r q4, min(n, (r + 1) q4)) (dv_layer_fixtures
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
BENCH = 'results/rtl/s81_l14_idx_1026'
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


def quarter(meta):
    """(n keys after the append, q4, B, N, KB, new-key position, owner rank) of the fixture's indexer layer"""
    li = str(meta['layer_index'])
    rows = meta['state']['rows'][li] if isinstance(meta['state'], dict) else None
    assert rows and rows.get('index_keys'), 'fixture state has no index keys (not an indexer layer)'
    n_pre = int(rows['index_keys'])
    n = n_pre + 1
    q4 = -(-n // TP)
    r = int(meta['rank'])
    B = r * q4
    N = min(n, B + q4) - B
    assert B % 512 == 0, 'rank quarter not block aligned'
    kb = (IKB - 34 * (B >> 9)) % (1 << 30)
    return dict(n=n, q4=q4, B=B, N=N, KB=kb, p_new=n_pre, owner=n_pre // q4, rank=r)


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


def ik_frame(fx, tag, mutant=None):
    """IK_ROW frame words [header, payload] for the owning rank (None on the other ranks)"""
    from lower_svc import hdr
    _, meta, _, _ = _fx(fx)
    q = quarter(meta)
    if q['owner'] != q['rank']:
        return None
    k = newkey_word(fx)
    kb = (IKB if mutant == 'ik_kb' else q['KB'])        # MUTANT ik_kb: the region base without the rank offset
    spec = kb | ((k >> 512) & 0xFFFFFFFF) << 32
    return [hdr(15, 1, tag, spec=spec, pos=q['p_new'], user=USER), k & ((1 << 512) - 1)]


def ik_writes(fx):
    """golden: the 3 HBM writes of the new key {sid, PC parity, sector, strobe, data} (layout, fixture key)"""
    _, meta, _, _ = _fx(fx)
    q = quarter(meta)
    k = newkey_word(fx)
    rg, pc, a0, a1, asc, by = place(q['p_new'], q['KB'])
    sc = (k >> 512) & 0xFFFFFFFF
    return [(rg, pc & 1, a0, 0xFFFFFFFF, k & ((1 << 256) - 1)), (rg, pc & 1, a1, 0xFFFFFFFF, (k >> 256) & ((1 << 256) - 1)),
            (rg, pc & 1, asc, 0xF << by, sc << (8 * by))]


def idx_job(fx, mutant=None):
    """IDX_S header + 64 query words of the rank's quarter scan"""
    fx, meta, files, ops = _fx(fx)
    LC = _lc()
    q = quarter(meta)
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


def state_image(fx):
    """{(die PC, sector): 256-b} of the rank's state keys (the quarter without this position's new key)"""
    fx, meta, files, ops = _fx(fx)
    q = quarter(meta)
    li = meta['layer_index']
    ci, si = files[f'state/kv.ik{li}.codes.bin'], files[f'state/kv.ik{li}.scale.bin']
    lo, hi = ci['rows']
    assert lo == q['B'] and hi == min(q['B'] + q['N'], q['p_new']), (lo, hi, q)
    codes, scs = _ld(fx, f'state/kv.ik{li}.codes.bin', ci), _ld(fx, f'state/kv.ik{li}.scale.bin', si)
    img = {}
    for r in range(hi - lo):
        p = lo + r
        k = key_word(codes[r], scs[r])
        _, pc, a0, a1, asc, by = place(p, q['KB'])
        img[(pc, a0)] = k & ((1 << 256) - 1)
        img[(pc, a1)] = (k >> 256) & ((1 << 256) - 1)
        img[(pc, asc)] = img.get((pc, asc), 0) | ((k >> 512) & 0xFFFFFFFF) << (8 * by)
    return img


def expected(fx):
    """[(lane valid 16, 16 BF16 scores)] per scan word: the fixture golden attn.idx.score of the quarter"""
    fx, meta, files, ops = _fx(fx)
    q = quarter(meta)
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


def scan_cycles(N, P=P_SCAN):
    """IDX_S frame (65 words) + T0 + 10 + P per word: header-to-last-word edges at the first region (rg3 static plan)"""
    nw = -(-N // 16)
    return 65 + T0 + 10 + P * nw


def write_bench(fx, out, tag=0):
    """bench images: svc/<v>/{ikq,ikw}.hex and rg3/{job,exp,hbm_state}.hex (+ rg3 mutant job images)"""
    out = Path(out)
    hx = lambda w, b: f'{w:0{-(-b // 4)}x}'  # noqa: E731
    rec = dict(quarter=quarter(_fx(fx)[1]))
    for v in (None, 'ik_kb'):
        d = out / 'svc' / (v or 'base')
        d.mkdir(parents=True, exist_ok=True)
        fr = ik_frame(fx, tag, mutant=v)
        assert fr is not None, 'this fixture rank does not own the new key (no IK_ROW to bench)'
        (d / 'ikq.hex').write_text(''.join(f'1 {hx(w, 512)}\n' for w in fr) + ''.join(f'0 {hx(0, 512)}\n' for _ in range(8)))
        (d / 'ikw.hex').write_text(''.join(f'{s:x} {pc:x} {a:08x} {st:08x} {hx(dd, 256)}\n' for s, pc, a, st, dd in ik_writes(fx)))
    d = out / 'rg3'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'job.hex').write_text(''.join(hx(w, 512) + '\n' for w in idx_job(fx)))
    ex = expected(fx)
    (d / 'exp.hex').write_text(''.join(f'{kv:04x} {hx(s, 256)}\n' for kv, s in ex))
    img = state_image(fx)
    (d / 'hbm_state.hex').write_text(''.join(f'{pc:02x} {a:08x} {hx(img[(pc, a)], 256)}\n' for pc, a in sorted(img)))
    rec.update(words=len(ex), state_sectors=len(img), scan_cycles=scan_cycles(rec['quarter']['N']))
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
    q = quarter(meta)
    ok, why = _bench_ok()
    layer = ctx.get('layer')
    st = 'LOWERED' if ok else 'PARTIAL'
    gap = None if ok else dict(module='lower_idx', port=BENCH, missing=f'bench: {why}')
    if name == 'attn.idx.newkey':
        if q['owner'] != q['rank']:
            return dict(base, status=st, gap=gap, note=f'no-op on rank {q["rank"]}: the new key (position {q["p_new"]}) '
                        f'belongs to rank {q["owner"]}\'s quarter (q4 {q["q4"]}); that rank\'s svc job carries the IK_ROW '
                        f'frame (bench {BENCH}, rank-{q["owner"]} fixture)', owner_rank=q['owner'])
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
    if q['owner'] == q['rank']:
        r = lower_svc.lower(die, dict(op='attn.own_row_write'), ctx)
        for e in r.get('events', []):
            if e.get('tag') == 'attn.IK_ROW':
                t_ik = max(c for c, _, _ in e['words'])
        if t_ik is not None:
            t0 = max(t0, t_ik + IK_GUARD)
    ws = idx_job(fx)
    cyc = scan_cycles(q['N'])
    words = [[t0 + k, f'{(w << 1) | 1:x}', f'{(1 << 513) - 1:x}'] for k, w in enumerate(ws)]
    ev = [dict(cycle=t0, inst='u_iqf', port='qi', ports=['qi'], dir='in', kind='IDXJ', tag='attn.idx.score',
               payload=f'IDX_S B {q["B"]} N {q["N"]} k {K_SEL} KB {q["KB"]} T0 {T0} P {P_SCAN} ik {IK_STRAP}', words=words,
               valid_bit=0, producer_gap='the IDX_S frame reaches the idx chain from the slice iq send (s_3S_C -> iqf); '
                                          'that xs field programme is not lowered, the bench drives the frame at the '
                                          'chain input')]
    return dict(base, status=st, gap=gap, events=ev, idx_job=dict(B=q['B'], N=q['N'], KB=q['KB'], T0=T0, P=P_SCAN,
                tag=IDX_TAG, ik=IK_STRAP, rank=q['rank'], t_hdr=t0, t_ik_payload=t_ik, cycles_model=cyc,
                priced=round(float(op.get('end', 0)) - float(op.get('start', 0)), 1)),
                files={f'prog/idx/{layer}/idx_job.hex': ''.join(f'{w:0128x}\n' for w in ws)})


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='lower_idx bench images / rg3 HBM merge')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a1 = sub.add_parser('images'); a1.add_argument('--fixtures', required=True); a1.add_argument('--out', required=True)
    a2 = sub.add_parser('merge'); a2.add_argument('state'); a2.add_argument('dump'); a2.add_argument('out')
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if a.cmd == 'images':
        print(json.dumps(write_bench(a.fixtures, a.out)))
    else:
        print('merged writes', merge(a.state, a.dump, a.out))


if __name__ == '__main__':
    main()
