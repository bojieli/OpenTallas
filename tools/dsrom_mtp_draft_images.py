#!/usr/bin/env python3
"""MD-2 draft-die ROM images: the A/B split of the released DSpark drafter experts, one image per draft die.

    python3 tools/dsrom_mtp_draft_images.py build  --out <dir> [--snapshot <released V4.1-Flash>]
    python3 tools/dsrom_mtp_draft_images.py check  --out <dir> --record <json> [--mutants]

Draft die (MD-2 P2, package-pair fan-out; generator: tools/dsrom_s81_fulldie.py --die layer1 --draft A|B):
5 row packages x 4 ranks x {A, B} = 40 dies.  Every row package holds the SAME eight images (the 5 row replicas
share a side/rank image), so 8 distinct images serve the 40 dies.
  die A = mtp.0 experts 0..127 + mtp.2 experts 0..63, die B = mtp.1 experts 0..127 + mtp.2 experts 64..127
  (rank k = row quarter k of every expert matrix, tools/dsrom_1m_field matrix_map rank_slices).
Storage layout = the selected whole-superrow rowpack (tools/dsrom_mtp_p2_rowpack.py: 1,792 pairs, 14 pairs a
region, region (superrow + 32 expert) mod 128, one full-K segment a superrow, chunk8 order unchanged); word order
inside a pair phase = the element issue order (v41_rom_ksplit_bankmap.element_order), exactly as
tools/dsrom_mtp_p2_rowpack_image.emit writes one pair (that per-pair writer is the reference: `check` compares
sampled pairs byte for byte against it).

Image file: <out>/draft_<side>_rank<k>.bin = a .npy array (uint8, 14,680,064 x 2 x 34: 1,792 pairs x 8,192
addresses pair-major x 2 banks x 34 bytes = little-endian 272-bit words, two FP4 32-blocks of 16 code bytes + 1 E8M0
scale byte each); the raw ROM words follow the 128-byte .npy header.

`check` = the image-level exactness gate: it reads the eight images back WITHOUT the emitter, rebuilds every
released expert tensor (codes .weight I8-packed FP4 + .scale E8M0) from A and B together over the 4 ranks and
compares it with the released safetensors byte for byte; it also requires each tensor on the side the MD-2 rule
names (computed from the tensor name, not the plan), every image word outside the plan zero, and no address
written twice.  --mutants runs three mutant splits that must FAIL: (m1) mtp.2 boundary moved to 63 (expert 63
read from B: missing bytes), (m2) one B word with its two banks (rows 2r / 2r+1) swapped, (m3) the rank-1 B image
served as rank 0.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_mtp_p2 as P
import dsrom_mtp_p2_rowpack as R
import v41_rom_ksplit_bankmap as S

DEPTH, PAIRS, WB = 8192, 1792, 2 * 34
SIDES, RANKS = ('A', 'B'), range(4)


def md2_side(tensor, boundary=64):
    """MD-2 rule from the tensor name alone: stage 0 -> A, stage 1 -> B, stage 2 expert < boundary -> A."""
    _, st, _, _, ex = tensor.split('.')[:5]
    st, ex = int(st), int(ex)
    return 'A' if st == 0 or (st == 2 and ex < boundary) else 'B'


def word_maps(plan):
    """Per side: flat arrays over every image word the plan writes: global address, tensor id, superrow, u, b
    (the emitter's (idx, u, b, h) order per (phase, pair), h unused for FP4)."""
    tensors = sorted({sg['tensor'] for ph in plan['phases'] for sg in ph['segments']})
    tid = {t: i for i, t in enumerate(tensors)}
    out = {}
    for side in SIDES:
        addr, ti, sr, uu, bb = [], [], [], [], []
        for ph in plan['phases']:
            if ph['side'] != side:
                continue
            bypair = collections.defaultdict(list)
            for x in ph['segments']:
                bypair[x['pair']].append(x)
            for pair, ss in bypair.items():
                ss.sort(key=lambda x: (x['superrow'], x['mi']))
                segs = [dict(fmt='fp4', e0=0, elems=x['K'], row=x['superrow'], tensor=x['mi']) for x in ss]
                order = S.element_order(segs)
                assert len(order) == sum(x['words'] for x in ss)
                base = pair * DEPTH + min(x['base'] for x in ss)
                o = np.asarray(order, dtype=np.int64)
                idx = o[:, 0]
                addr.append(base + np.arange(len(order), dtype=np.int64))
                ti.append(np.asarray([tid[ss[i]['tensor']] for i in range(len(ss))], dtype=np.int32)[idx])
                sr.append(np.asarray([ss[i]['superrow'] for i in range(len(ss))], dtype=np.int32)[idx])
                uu.append(o[:, 1].astype(np.int32))
                bb.append(o[:, 2].astype(np.int32))
        a = np.concatenate(addr)
        assert len(np.unique(a)) == len(a), 'an address written twice'
        out[side] = dict(addr=a, t=np.concatenate(ti), sr=np.concatenate(sr), u=np.concatenate(uu),
                         b=np.concatenate(bb))
    meta = {}
    for ph in plan['phases']:
        for x in ph['segments']:
            meta[x['tensor']] = dict(K=x['K'], side=ph['side'], rank_rows=[s_['rows'] for s_ in x['rank_slices']])
    return tensors, meta, out


def _rows_blocks(wm, sel, r0, mb, half):
    row = r0 + 2 * wm['sr'][sel] + mb
    block = (2 * wm['u'][sel] + half) * 8 + wm['b'][sel]
    return row, block


def build(a):
    plan = R.schedule(a.snapshot)
    tensors, meta, wms = word_maps(plan)
    raw = P.Raw(a.snapshot)
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.dsrom-mtp-draft-images.v1', source_sha256=P.digest(__file__),
               rowpack_sha256=P.digest(R.__file__), snapshot=a.snapshot.name,
               index_sha256=P.digest(a.snapshot / 'model.safetensors.index.json'), images={})
    for side in SIDES:
        wm = wms[side]
        by_t = collections.defaultdict(list)
        order = np.argsort(wm['t'], kind='stable')
        tsorted = wm['t'][order]
        bounds = np.searchsorted(tsorted, np.arange(len(tensors) + 1))
        for rank in RANKS:
            t0 = time.time()
            fn = a.out / f'draft_{side}_rank{rank}.bin'
            img = np.lib.format.open_memmap(str(fn) + '.npy', mode='w+', dtype=np.uint8, shape=(PAIRS * DEPTH, 2, 34))
            blocks = 0
            for i, t in enumerate(tensors):
                sel = order[bounds[i]:bounds[i + 1]]
                if len(sel) == 0:
                    continue
                m = meta[t]
                codes = raw.array(t)
                scale = raw.array(t[:-6] + 'scale')
                c3 = codes.reshape(codes.shape[0], -1, 16)
                r0 = m['rank_rows'][rank][0]
                ad = wm['addr'][sel]
                for mb in range(2):
                    for half in range(2):
                        row, block = _rows_blocks(wm, sel, r0, mb, half)
                        ok = block * 32 < m['K']
                        off = half * 17
                        img[ad[ok], mb, off:off + 16] = c3[row[ok], block[ok]]
                        img[ad[ok], mb, off + 16] = scale[row[ok], block[ok]]
                        blocks += int(ok.sum())
            img.flush()
            del img
            os.replace(str(fn) + '.npy', fn)      # .npy header kept: np.load(mmap_mode='r') reads it back
            rec['images'][f'{side}{rank}'] = dict(file=fn.name, sha256=P.digest(fn), bytes=fn.stat().st_size,
                                                  words=int(len(wm['addr'])), released_blocks=blocks,
                                                  seconds=round(time.time() - t0, 1))
            print(json.dumps({f'{side}{rank}': rec['images'][f'{side}{rank}']}), flush=True)
    rec['tensors'] = len(tensors)
    rec['words_per_side'] = {s_: int(len(wms[s_]['addr'])) for s_ in SIDES}
    (a.out / 'images.json').write_text(json.dumps(rec, indent=1) + '\n')
    return 0


def recombine(images, plan_maps, tensors, meta, raw, boundary=64):
    """Rebuild every released expert tensor from the images; returns (ok, problems)."""
    probs = []
    wms = plan_maps
    for side in SIDES:
        used = np.zeros(PAIRS * DEPTH, dtype=bool)
        used[wms[side]['addr']] = True
        for rank in RANKS:
            img = images[(side, rank)]
            # every word the plan does not write must be zero (sampled in strides to bound the read)
            unused = np.flatnonzero(~used)
            if len(unused) and np.any(img[unused[::97]]):
                probs.append(f'{side}{rank}: nonzero word outside the plan')
    for i, t in enumerate(tensors):
        m = meta[t]
        codes = raw.array(t)
        scale = raw.array(t[:-6] + 'scale')
        rc = np.zeros(codes.shape[:1] + (codes.shape[1] // 16, 16), dtype=np.uint8)
        rs = np.zeros(scale.shape, dtype=np.uint8)
        hit = np.zeros(scale.size, dtype=np.int64)
        want = md2_side(t, boundary)
        for side in SIDES:
            wm = wms[side]
            sel = np.flatnonzero(wm['t'] == i)
            if len(sel) == 0:
                continue
            if side != want:
                continue         # a tensor on the wrong side is never read back: it shows up as missing bytes
            for rank in RANKS:
                img = images[(side, rank)]
                r0 = m['rank_rows'][rank][0]
                ad = wm['addr'][sel]
                for mb in range(2):
                    for half in range(2):
                        row, block = _rows_blocks(wm, sel, r0, mb, half)
                        ok = block * 32 < m['K']
                        off = half * 17
                        rc[row[ok], block[ok]] = img[ad[ok], mb, off:off + 16]
                        rs[row[ok], block[ok]] = img[ad[ok], mb, off + 16]
                        hit += np.bincount(row[ok] * scale.shape[1] + block[ok], minlength=scale.size)
        if (hit != 1).any():
            probs.append(f'{t}: {int((hit == 0).sum())} blocks missing, {int((hit > 1).sum())} duplicated')
        elif rc.reshape(codes.shape).tobytes() != np.asarray(codes).tobytes() or rs.tobytes() != np.asarray(scale).tobytes():
            probs.append(f'{t}: bytes differ from the released tensor')
    return not probs, probs


def check(a):
    plan = R.schedule(a.snapshot)
    tensors, meta, wms = word_maps(plan)
    raw = P.Raw(a.snapshot)
    rec_in = json.loads((a.out / 'images.json').read_text())
    images = {}
    for side in SIDES:
        for rank in RANKS:
            fn = a.out / f'draft_{side}_rank{rank}.bin'
            assert P.digest(fn) == rec_in['images'][f'{side}{rank}']['sha256'], fn
            images[(side, rank)] = np.load(fn, mmap_mode='r')
    # rule: every tensor on the MD-2 side computed from its name; all 2,304 released expert headers covered
    wrong = [t for t in tensors if meta[t]['side'] != md2_side(t)]
    out = dict(schema='opentallas.dsrom-mtp-draft-images-check.v1', source_sha256=P.digest(__file__),
               images=rec_in['images'], tensors=len(tensors), md2_rule_violations=wrong[:5])
    # reference: sampled pairs byte for byte against the per-pair rowpack_image emitter
    import dsrom_mtp_p2_rowpack_image as RI
    import tempfile
    ref = []
    for side, rank, pair in ((('A', 0, 0), ('A', 3, 1791), ('B', 1, 637), ('B', 2, 1200))):
        with tempfile.TemporaryDirectory() as td:
            pr = RI.emit(plan, a.snapshot, side, rank, pair, Path(td) / 'p.bin')
            got = images[(side, rank)][pair * DEPTH:(pair + 1) * DEPTH].tobytes()
            ref.append(dict(side=side, rank=rank, pair=pair,
                            equal=(Path(td) / 'p.bin').read_bytes() == got, released_blocks=pr['released_blocks']))
    out['emitter_reference_pairs'] = ref
    t0 = time.time()
    ok, probs = recombine(images, wms, tensors, meta, raw)
    out['recombine'] = dict(verdict='PASS' if ok else 'FAIL', problems=probs[:10], seconds=round(time.time() - t0, 1))
    if a.mutants:
        mut = {}
        ok1, p1 = recombine(images, wms, tensors, meta, raw, boundary=63)
        mut['m1_mtp2_boundary_63'] = dict(verdict='PASS' if ok1 else 'FAIL', problems=p1[:3])
        imgs2 = dict(images)
        b0 = np.array(images[('B', 0)])
        w = int(wms['B']['addr'][12345])
        b0[w, [0, 1]] = b0[w, [1, 0]]
        imgs2[('B', 0)] = b0
        ok2, p2 = recombine(imgs2, wms, tensors, meta, raw)
        mut['m2_bank_swap_one_word'] = dict(verdict='PASS' if ok2 else 'FAIL', problems=p2[:3])
        del b0
        imgs3 = dict(images)
        imgs3[('B', 0)] = images[('B', 1)]
        ok3, p3 = recombine(imgs3, wms, tensors, meta, raw)
        mut['m3_rank1_B_as_rank0'] = dict(verdict='PASS' if ok3 else 'FAIL', problems=p3[:3])
        out['mutants'] = mut
    good = ok and not wrong and all(r['equal'] for r in ref) and \
        (not a.mutants or all(v['verdict'] == 'FAIL' for v in out['mutants'].values()))
    out['verdict'] = 'PASS' if good else 'FAIL'
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('verdict', 'recombine', 'emitter_reference_pairs')}, indent=1))
    if a.mutants:
        print(json.dumps({k: v['verdict'] for k, v in out['mutants'].items()}))
    return 0 if good else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['build', 'check'])
    p.add_argument('--snapshot', type=Path, default=P.D.SNAP_DEFAULT)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--record', type=Path)
    p.add_argument('--mutants', action='store_true')
    a = p.parse_args()
    return build(a) if a.mode == 'build' else check(a)


if __name__ == '__main__':
    raise SystemExit(main())
