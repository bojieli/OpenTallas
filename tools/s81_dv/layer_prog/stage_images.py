#!/usr/bin/env python3
"""ROM-WEIGHTS-1119 (11-24): real-weight ROM images of one S81 stage rank die, every frame, plus an independent
readback of the emitted via maps against the raw checkpoint.

  build   compile every frame of the plan-of-record 72-frame die (the DRIVE-S81-SVCPLAN column-reduced inventory the
          241-stage map was qualified on: results/arch/s81_dense2_1020/capacity_cols.py, frame inventory sha pinned
          by the map) from a weights-only stage fixture (stage_fixtures.py) with xs_place.compile_frame under the
          map's release env + the stage's DENSE2 half (xs_capacity.spec_env / spec_ops, the shared-expert and X-stage
          rules of xs_capacity.frame_alloc) and LEGALISED placement (default iters), then xs_place.write_images:
          <frame>_e<k>{,b}_<par>.viamap.hex (q pair weight macros, ot_rom_4096x274_m8 PP banks), <frame>_e<k>{w,e}_<par>
          (BF pairs), <frame>_c<k>_<0..6>.viamap.hex (cfg7 banks, ot_rom_4096x72_m8), spine_*.  Writes
          manifest.json: per frame every image sha256 and, per field phase, the matrices the image writer placed
          (name, tag offset, the fixture-tensor rows of every tag) -- the provenance the readback needs.
  verify  INDEPENDENT readback: decode each frame's cfg7 ROMs (segments: row tag, seg, nseg, fmt, phase start) and
          weight via maps (PP parity banks), recompute every placed segment's ROM words from the RAW CHECKPOINT
          bytes (safetensors header offsets; FP8 E4M3 + UE8M0 32x32 block / FP4 E2M1 + per-row UE8M0 block words),
          and require, per phase x pair macro, the multiset of programmed words to equal the expected one and no
          programmed word outside a phase.  --corrupt FRAME:FILE:ROW:BIT flips one via first (negative control).

    stage_images.py build  --fixture FIX --out OUT [--jobs 16] [--frames F ...]
    stage_images.py verify --out OUT --snapshot CKPT [--frames F ...] [--corrupt ...] [--report R.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in ('tools', 'tools/s81_dv', 'tools/s81_dv/layer_prog', 'tools/s81_static_control'):
    sys.path.insert(0, str(ROOT / p))

SCHEMA = 'opentallas.s81_dv.stage_images.v1'
NSEG, CW = 8, 25
SENT = 0x8000
# the 72-frame inventory of the map of record (241_c*.exact.log SVCPLAN_INVENTORY; s81_map72_1021/run72.sh + capacity72.py)
INV72 = dict(OT_SVCPLAN_COLS='8', OT_SVCPLAN_DROPFC='1R,3R,4L,6L', OT_SVCPLAN_ROW0='1')


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ die
def die72(cache):
    """the column-reduced 72-frame die model the map was qualified on: s81_dense2_1020/capacity_cols.cols (f84 filter)
    + s81_map72_1021/capacity72.py (also drop the north h10, row 11, of every kept column); returns (die, inv, sha)"""
    import dv_layer_compile as C
    import xs_topo as TP
    nc = int(INV72['OT_SVCPLAN_COLS'])
    drop = {(int(x[0]), x[1]) for x in INV72['OT_SVCPLAN_DROPFC'].split(',')}

    def keep(n):
        m = re.fullmatch(r'f_(\d)([LR])(\d)(\d)', n)
        c, t, r = int(m.group(1)), int(m.group(3)), int(m.group(4))
        return c < nc and (c, m.group(2)) not in drop and not (t == 0 and r == 0) and not n.endswith('11')
    die = C.Die(C.die_tree(C.DIE_REF, None, cache=cache))
    gone = {b['name'] for b in die.plan['blocks'] if (b['kind'] == 'frame' and not keep(b['name']))
            or (b['kind'] == 'slice' and int(b['name'][2]) >= nc)}
    die.plan['blocks'] = [b for b in die.plan['blocks'] if b['name'] not in gone]
    die.inst = {k: v for k, v in die.inst.items() if k[2:] not in gone}
    orig = die.slices

    def slices():
        s = orig()
        order = sorted(s, key=lambda k: (s[k]['sid'] if s[k]['sid'] is not None else 99, k))
        for i, k in enumerate(order):
            s[k]['sid'] = i
        return s
    die.slices = slices
    TP.set_from_die(die)
    inv = sorted('u_' + b['name'] for b in die.plan['blocks'] if b['kind'] == 'frame')
    h = hashlib.sha256(json.dumps(inv).encode()).hexdigest()
    os.environ['OT_XS_FRAME_INVENTORY_SHA256'] = h
    return die, inv, h


def stage_env(meta, mapdoc):
    import xs_capacity as XC
    env = dict(mapdoc['verdict']['env'])
    e = XC.spec_env(meta['spec'], env)
    XC._apply_env(e)
    os.environ['OT_XS_STAGE'] = meta['stage']
    os.environ['OT_XS_STAGE_MAP'] = str(ROOT / meta['stage_map']['path']) if not Path(meta['stage_map']['path']).is_absolute() else meta['stage_map']['path']
    return e


# ------------------------------------------------------------------------------------------------ compile one frame
def compile_stage_frame(die, frame, fixd, meta, out):
    """xs_place.compile_frame of a stage frame (xs_capacity.frame_alloc's stage rules, legalised) + images +
    per-phase matrix provenance"""
    import lower_xs as LX
    import v41_die_images_w17w10 as I
    import xs_place as XP
    spec = meta['spec']
    shared = meta['shared']
    orig = (XP.op_groups, LX.placement, I.add_phase)
    prov = []

    def og(fx, op):
        g = orig[0](fx, op)
        return g if shared or op != 'ffn.down' else [x for x in g if x.get('expert') != 'shared']

    def pl(die_, sl, fx=None, *, selected_frame=None):
        g, p = orig[1](die_, sl, fx, selected_frame=selected_frame)
        return g, ([dict(r, rows=[]) for r in p] if spec.get('dense_layer') is None else p)

    def ap(field, mats, *a, **k):
        ph = orig[2](field, mats, *a, **k)
        # frame_programme also places a_proj on a scratch field: keep only the returned field's phases
        prov.append((field, [dict(name=m.name, fmt=m.fmt, K=int(m.K), off=int(mi['off']), src=[int(r) for _, r in m.src])
                             for m, mi in zip(mats, ph['matrices'])]))
        return ph
    XP.op_groups, LX.placement, I.add_phase = og, pl, ap
    try:
        rec, field = XP.compile_frame(die, frame, fixd, list(meta['xs_ops']) + list(meta['bf_ops']))
    finally:
        XP.op_groups, LX.placement, I.add_phase = orig
    prov = [v for f, v in prov if f is field]
    assert len(prov) == len([p for p in field.phases if not p.get('idle_no_issue')]), ('provenance', len(prov))
    pidx = [i for i, p in enumerate(field.phases) if not p.get('idle_no_issue')]
    img = Path(out) / 'images'
    img.mkdir(parents=True, exist_ok=True)
    names, _ = XP.write_images(field, rec['pairs'], rec['q_pairs'], rec['bf_pairs'], rec['frame'], img)
    files = {n: sha((img / n).read_bytes()) for n in sorted(names)}
    faults = sum(p['faults'] for p in rec['phases'] if p.get('calendar') != 'not_legalised')
    return dict(frame=frame, master=rec['master'], q_pairs=list(rec['pairs']), bf_pairs=list(rec['bf_pairs'][:int(field.bf.sum())]),
                all_q=list(rec['q_pairs']), all_bf=list(rec['bf_pairs']), slot_of_q={str(k): i for i, k in enumerate(rec['pairs'])},
                nphases=rec['nphases'], max_fill=max(rec['fill']) if rec['fill'] else 0, depth=rec['depth'], faults=faults,
                phase_ops=[p['op'] for p in rec['phases']], provenance={str(i): v for i, v in zip(pidx, prov)},
                images=files)


def _build_one(args):
    fixd, out, frame, cache = args
    meta = json.loads((Path(fixd) / 'meta.json').read_text())
    mapdoc = json.loads(Path(os.environ['OT_XS_STAGE_MAP']).read_text())
    stage_env(meta, mapdoc)
    die, _, _ = die72(cache)
    t = time.time()
    r = compile_stage_frame(die, frame, fixd, meta, Path(out) / 'frames' / frame)
    r['seconds'] = round(time.time() - t, 1)
    return r


def cmd_build(a):
    import multiprocessing as mp
    fixd = Path(a.fixture)
    meta = json.loads((fixd / 'meta.json').read_text())
    mp_ = meta['stage_map']['path']
    os.environ['OT_XS_STAGE_MAP'] = str(ROOT / mp_) if not Path(mp_).is_absolute() else mp_
    mapdoc = json.loads(Path(os.environ['OT_XS_STAGE_MAP']).read_text())
    assert sha(Path(os.environ['OT_XS_STAGE_MAP']).read_bytes()) == meta['stage_map']['sha256'], 'stage map changed since the fixture'
    stage_env(meta, mapdoc)
    import xs_capacity as XC
    XC.verdict(stage=meta['stage'])
    cache = str(Path(a.out) / 'dieref')
    die, inv, h = die72(cache)
    assert len(inv) == mapdoc['die_frames'] and h == mapdoc['frame_inventory_sha256'], ('die inventory differs from the map of record', len(inv), h)
    frames = a.frames or inv
    out = Path(a.out)
    (out / 'frames').mkdir(parents=True, exist_ok=True)
    with mp.get_context('fork').Pool(a.jobs) as pool:
        recs = pool.map(_build_one, [(str(fixd), str(out), f, cache) for f in frames], chunksize=1)
    man = dict(schema=SCHEMA, stage=meta['stage'], rank=meta['rank'], spec=meta['spec'], fixture=str(fixd),
               fixture_manifest_sha256=sha((fixd / 'manifest.sha256').read_bytes()), stage_map=meta['stage_map'],
               env={k: os.environ.get(k) for k in sorted(mapdoc['verdict']['env']) + ['OT_XS_DENSE_SPLIT2', 'OT_XS_DENSE_SPLIT2_ROWS']},
               inventory_sha256=h, x_policy=meta['x_policy'], frames={r['frame']: r for r in recs},
               images=sum(len(r['images']) for r in recs), faults=sum(r['faults'] for r in recs),
               max_fill=max(r['max_fill'] for r in recs), sources={f: sha((ROOT / f).read_bytes()) for f in (
                   'tools/s81_dv/layer_prog/stage_images.py', 'tools/s81_dv/layer_prog/stage_fixtures.py',
                   'tools/s81_dv/layer_prog/xs_place.py', 'tools/v41_die_images_w17w10.py')})
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(json.dumps(dict(stage=man['stage'], rank=man['rank'], frames=len(recs), images=man['images'],
                          faults=man['faults'], max_fill=man['max_fill'])))
    return 0 if man['faults'] == 0 else 1


def frame_cli(a):
    """xs_place.py frame --fixtures <weights-only stage fixture>: one frame of the stage die (same compile as build)"""
    fixd = Path(a.fixtures)
    meta = json.loads((fixd / 'meta.json').read_text())
    mp_ = meta['stage_map']['path']
    os.environ['OT_XS_STAGE_MAP'] = str(ROOT / mp_) if not Path(mp_).is_absolute() else mp_
    mapdoc = json.loads(Path(os.environ['OT_XS_STAGE_MAP']).read_text())
    stage_env(meta, mapdoc)
    import xs_capacity as XC
    XC.verdict(stage=meta['stage'])
    die, inv, h = die72(str(Path(a.out) / 'dieref'))
    assert h == mapdoc['frame_inventory_sha256'], 'die inventory differs from the map of record'
    r = compile_stage_frame(die, a.frame, fixd, meta, Path(a.out))
    (Path(a.out) / 'frame.json').write_text(json.dumps(r, indent=1) + '\n')
    print(f"XS_FRAME {a.frame} stage {meta['stage']} r{meta['rank']} phases {r['nphases']} max fill {r['max_fill']}/{r['depth']} faults {r['faults']}")
    return 0 if r['faults'] == 0 else 1


# ------------------------------------------------------------------------------------------------ readback
class Raw:
    """raw safetensors bytes by tensor name (index + header offsets only)"""

    def __init__(self, snap):
        self.snap = Path(snap)
        self.map = json.loads((self.snap / 'model.safetensors.index.json').read_text())['weight_map']
        self.hdr, self.fh = {}, {}

    def meta(self, name):
        f = self.map[name]
        if f not in self.hdr:
            fh = open(self.snap / f, 'rb')
            n = struct.unpack('<Q', fh.read(8))[0]
            self.hdr[f] = (json.loads(fh.read(n)), 8 + n)
            self.fh[f] = fh
        h, base = self.hdr[f]
        return h[name], base, self.fh[f]

    def bytes_at(self, name, row, b0, n):
        m, base, fh = self.meta(name)
        w = {'F8_E4M3': 1, 'F8_E8M0': 1, 'I8': 1, 'BF16': 2}[m['dtype']]
        cols = m['shape'][1] * w
        fh.seek(base + m['data_offsets'][0] + row * cols + b0)
        return fh.read(n)

    def dtype(self, name):
        return self.meta(name)[0]['dtype']

    def shape(self, name):
        return self.meta(name)[0]['shape']


def _vm_words(path, width_hex, rows=512):
    """address -> word of one via map (bit b*8+s of row r = bit b of address 8r+s)"""
    lines = Path(path).read_text().split()
    assert len(lines) == rows and all(len(x) == width_hex for x in lines), ('via map shape', path)
    out = {}
    for r, x in enumerate(lines):
        v = int(x, 16)
        if not v:
            continue
        nb = width_hex * 4 // 8
        for s in range(8):
            w = 0
            for b in range(nb):
                if (v >> (8 * b + s)) & 1:
                    w |= 1 << b
            if w:
                out[8 * r + s] = w
    return out


def _weights_of(img, frame, k, mb):
    out = {}
    for par in (0, 1):
        for a, w in _vm_words(img / f'{frame}_e{k}{"b" if mb else ""}_{par}.viamap.hex', 548).items():
            out[2 * a + par] = w
    return out


def _cfg_of(img, frame, k, nph):
    banks = [_vm_words(img / f'{frame}_c{k}_{jb}.viamap.hex', 144) for jb in range(7)]
    words = []
    for p in range(nph):
        words.append([banks[w % 7].get(4 * p + w // 7, 0) & ((1 << 48) - 1) for w in range(CW)])
    return words


class Expect:
    """ROM words of a fixture matrix row recomputed from the raw checkpoint"""

    def __init__(self, raw, files):
        self.raw, self.files = raw, files

    def src(self, name, row):
        """(tensor, scale tensor, checkpoint row, column element offset) of a fixture matrix row"""
        if name.endswith('.w13'):
            nff = self.files[f'weights/{name[:-3]}w1.bin']['shape'][0]
            name, row = (name[:-3] + 'w1', row) if row < nff else (name[:-3] + 'w3', row - nff)
        f, fs = self.files[f'weights/{name}.bin'], self.files[f'weights/{name}.scale.bin']
        r0 = f['rows'][0] if f['rows'] else 0
        c0 = f['cols'][0] if f['cols'] else 0
        return f['tensor'], fs['tensor'], r0 + row, c0

    def block(self, fmt, name, row, chunk, b):
        t, ts, r, c0 = self.src(name, row)
        blk = chunk * 8 + b
        sh, ssh = self.raw.shape(t), self.raw.shape(ts)
        if fmt == 'fp8':
            codes = self.raw.bytes_at(t, r, c0 + blk * 32, 32)
            per_row = ssh[0] == sh[0]
            e = self.raw.bytes_at(ts, r if per_row else r // 32, c0 // 32 + blk, 1)[0]
            return int.from_bytes(codes, 'little') | (e << 256)
        codes = self.raw.bytes_at(t, r, c0 // 2 + blk * 16, 16)
        e = self.raw.bytes_at(ts, r, c0 // 32 + blk, 1)[0]
        return int.from_bytes(codes, 'little') | (e << 128)

    def segment(self, fmt, name, row, e0, elems):
        import v41_rom_ksplit_bankmap as S
        out = []
        for (u, b, h) in S.segment_order(fmt, e0, elems):
            if fmt == 'fp8':
                out.append(self.block('fp8', name, row, 2 * u + h, b))
            else:
                w = 0
                for half in (0, 1):
                    c = 2 * u + half
                    if e0 <= c * 256 < e0 + elems:
                        w |= self.block('fp4', name, row, c, b) << (136 * half)
                out.append(w)
        return out


def verify_frame(out, fr, files, raw, corrupt=None):
    import v41_rom_ksplit_bankmap as S
    img = Path(out) / 'frames' / fr['frame'] / 'images'
    frame = fr['frame']
    for name, h in fr['images'].items():
        if sha((img / name).read_bytes()) != h and not corrupt:
            raise ValueError(f'image sha differs from the manifest: {name}')
    ex = Expect(raw, files)
    nph = fr['nphases']
    checked = segs = 0
    for k in fr['q_pairs']:
        cfg = _cfg_of(img, frame, k, nph)
        for mb in (0, 1):
            have = _weights_of(img, frame, k, mb)
            used = set()
            for p in range(nph):
                prov = fr['provenance'].get(str(p))
                words = cfg[p]
                slot_ws = [w for w in words[:NSEG] if w]
                if not slot_ws:
                    continue
                assert prov is not None, ('cfg phase without provenance', frame, k, p)
                if any((w >> 42) & 1 for w in slot_ws):
                    continue      # BF16 segment on a q pair: out of this bench's scope (none in FP stages)
                start = (words[2 * NSEG] >> 6) & 0x3fff
                expect = []
                for slot in range(NSEG):
                    w = words[slot]
                    if not w:
                        continue
                    tag = words[2 * NSEG + 1 + slot] if mb else (w & 0xffff)
                    seg, nseg, fp4, base = (w >> 16) & 31, (w >> 21) & 31, (w >> 26) & 1, (w >> 29) & 0x1fff
                    if tag & SENT:
                        continue
                    mi = [m for m in prov if m['off'] <= tag < m['off'] + len(m['src'])]
                    assert len(mi) == 1, ('tag outside the phase matrices', frame, k, p, tag)
                    m = mi[0]
                    assert (m['fmt'] == 'fp4') == bool(fp4), ('cfg fmt differs from provenance', frame, k, p)
                    e0, el = S.segments(m['K'], nseg)[seg]
                    expect += ex.segment(m['fmt'], m['name'], m['src'][tag - m['off']], e0, el)
                    segs += 1
                K = prov[0]['K']
                n = sum(len(S.segment_order('fp4' if (w >> 26) & 1 else 'fp8',
                                            *S.segments(K, (w >> 21) & 31)[(w >> 16) & 31])) for w in words[:NSEG] if w)
                addrs = range(start, start + n)
                got = [have.get(a, 0) for a in addrs]
                used.update(addrs)
                exp_full = expect + [0] * (n - len(expect))    # SENT rows leave their addresses dark
                if Counter(got) != Counter(exp_full):
                    bad = sorted((set(exp_full) ^ set(got)) - {0})[:1]
                    raise ValueError(f'ROM words differ from the checkpoint: {frame} e{k}{"b" if mb else ""} phase {p} '
                                     f'({len(expect)} expected words){" e.g. " + hex(bad[0])[:24] if bad else ""}')
                checked += len(expect)
            stray = [a for a in have if a not in used]
            if stray:
                raise ValueError(f'programmed words outside every phase: {frame} e{k}{"b" if mb else ""} {stray[:4]}')
    return checked, segs


def cmd_verify(a):
    out = Path(a.out)
    man = json.loads((out / 'manifest.json').read_text())
    files = json.loads((Path(man['fixture']) / 'files.json').read_text())
    raw = Raw(a.snapshot)
    frames = a.frames or sorted(man['frames'])
    if a.corrupt:
        fr_, fn, row, bit = a.corrupt.split(':')
        p = out / 'frames' / fr_ / 'images' / fn
        lines = p.read_text().split('\n')
        v = int(lines[int(row)], 16) ^ (1 << int(bit))
        lines[int(row)] = f'{v:0{len(lines[int(row)])}x}'
        p.write_text('\n'.join(lines))
        frames = [fr_]
    res = dict(schema=SCHEMA + '.verify', stage=man['stage'], rank=man['rank'], frames=len(frames), corrupt=a.corrupt)
    try:
        tot = segs = 0
        for f in frames:
            c, s = verify_frame(out, man['frames'][f], files, raw, corrupt=a.corrupt)
            tot += c
            segs += s
        res.update(verdict='PASS', words_checked=tot, segments_checked=segs)
    except Exception as e:  # noqa: BLE001 -- the verdict
        res.update(verdict='FAIL', error=f'{type(e).__name__}: {e}')
    if a.report:
        Path(a.report).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res))
    return 0 if res['verdict'] == 'PASS' else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('build')
    b.add_argument('--fixture', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--jobs', type=int, default=16)
    b.add_argument('--frames', nargs='*')
    v = sp.add_parser('verify')
    v.add_argument('--out', required=True)
    v.add_argument('--snapshot', required=True)
    v.add_argument('--frames', nargs='*')
    v.add_argument('--corrupt')
    v.add_argument('--report')
    a = ap.parse_args(argv)
    return {'build': cmd_build, 'verify': cmd_verify}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
