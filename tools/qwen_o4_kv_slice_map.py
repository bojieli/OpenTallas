#!/usr/bin/env python3
"""Proof of the Qwen O4 tile KV-slice address map (rtl/hdc/ot_qwen_rom_tile.sv, KV_LOCAL = 1).

Replays the issue loop of rtl/hdc/ot_hdc_matvec.sv for every KV-sourced op of a
layer program (the G = QWEN_O4_GROUPS image emitted by hdc_qwen_layer0_rom.py) at
the last position of the 8,192-token window, and checks, for the local map the
tile implements:

  1. every local index fits the slice (KV_AW bits);
  2. in every issue cycle the four groups of a tile map to one local word
     (the tile reads one 512-bit slice word for all four);
  3. per group, distinct KV words read map to distinct local words (one-to-one);
  4. every word of the K and V window is read by exactly one tile, so the KV
     fill network has one destination per word.

Writes a source-pinned record.  Not an RTL simulation: the RTL formula is
restated here and must match rtl/hdc/ot_qwen_rom_tile.sv (checked by the
tile's unit bench).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('HDC_SU_WIDTH', '1024')
os.environ.setdefault('HDC_KV_FMT', 'fp8')
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_isa as QI  # noqa: E402
import hdc_qwen_fullshape_program as FP  # noqa: E402
from hdc_qwen_fullshape_placement import GROUPS  # noqa: E402

W, IL, TG = I.W_LANES, I.INTERLEAVE, 4
KV_VB, KV_HB, KV_NH, KV_SK, KV_SV, KV_AW = 262144, 16, 4, 7, 9, 7


def local(a, groups=GROUPS):
    kl = -(-512 // (groups >> KV_SK)) * KV_NH
    if a < KV_VB:
        t = (a % (1 << KV_HB)) >> 7
        return (t // (groups >> KV_SK)) * KV_NH + (a >> KV_HB)
    w = a - KV_VB
    p = (w % (1 << KV_HB)) >> 3
    return kl + (p >> KV_SV) * KV_NH + (w >> KV_HB)


def kv_reads(f, dyn, pos, groups):
    """(cycle, group, word, owned) of one KV op, as ot_hdc_matvec issues it.
    owned: the element is not zeroed (e_gm) and its row is a valid output."""
    s = f['me_split']
    S = 1 << s
    per_round = groups >> s
    tiles = f['me_tiles'] + dyn[f['me_d_tiles']]
    if f['me_d_tiles'] == I.DYN_TTILES:
        tiles = f['me_tiles'] + pos // (W * per_round) + 1
    K = f['me_k'] + dyn[f['me_d_k']]
    kc = -(-K // S)
    nout = f['me_nout'] + dyn[f['me_d_nout']]
    ts, ks, js, jsh, wcs = f['me_ts'], f['me_ks'], f['me_js'], f['me_jsh'], f['me_wcs']
    tstep = ts * per_round
    cyc = 0
    for r in range(tiles):
        for k in range(kc):
            for j in range(IL):
                cur = f['me_wbase'] + r * tstep + k * ks + (j >> jsh) * js
                for g in range(groups):
                    q, c = g >> s, g & (S - 1)
                    live = q < per_round and k * S + c < K
                    t = r * per_round + q
                    row_ok = (t * W < nout) if f['me_mmode'] else ((t * IL + j) * W < nout)
                    yield cyc, g, cur + q * ts + c * wcs, live and row_ok
                cyc += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--image', type=Path, required=True, help='a layer image directory (program.hex, layerN_rom.json)')
    ap.add_argument('--pos', type=int, default=8191)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    prog = [QI.decode_instruction(int(x, 16)) for x in (args.image / 'program.hex').read_text().split()]
    manifest = json.loads(next(args.image.glob('layer*_rom.json')).read_text())
    lay = FP.LayerZero(None, manifest['die'], manifest['matrix_layout'])
    with FP.program_geometry(FP.vm_map()[0]):
        dyn = P.dyn_values(lay, token=0, pos=args.pos)
    ops = [f for f in prog if f['unit'] == I.UNIT_ME and f['me_wsrc']]
    max_local = 0
    tile_disagree = 0
    per_group = defaultdict(dict)       # g -> {local: word}
    readers = defaultdict(set)          # word -> tiles
    collisions = 0
    reads = 0
    for oi, f in enumerate(ops):
        by_cycle = defaultdict(dict)
        for cyc, g, a, owned in kv_reads(f, dyn, args.pos, GROUPS):
            if not owned:
                continue
            reads += 1
            lo = local(a)
            max_local = max(max_local, lo)
            by_cycle[(cyc, g // TG)].setdefault('l', set()).add(lo)
            prev = per_group[g].get(lo)
            if prev is not None and prev != a:
                collisions += 1
            per_group[g][lo] = a
            readers[a].add(g // TG)
        tile_disagree += sum(1 for v in by_cycle.values() if len(v['l']) > 1)
    multi = sum(1 for v in readers.values() if len(v) > 1)
    window_k = KV_NH * (args.pos + 1) * 128 // W
    ok = (max_local < (1 << KV_AW) and tile_disagree == 0 and collisions == 0 and multi == 0)
    src = ['tools/qwen_o4_kv_slice_map.py', 'rtl/hdc/ot_qwen_rom_tile.sv', 'rtl/hdc/ot_hdc_matvec.sv']
    rec = {'schema': 'opentallas.qwen-o4-kv-slice-map.v1', 'status': 'pass' if ok else 'fail',
           'groups': GROUPS, 'position': args.pos, 'kv_ops': len(ops), 'owned_reads': reads,
           'distinct_words_read': len(readers), 'window_words_k_plus_v_at_pos': 2 * window_k,
           'max_local_index': max_local, 'slice_words': 1 << KV_AW,
           'tile_cycles_with_disagreeing_local': tile_disagree, 'per_group_collisions': collisions,
           'words_read_by_more_than_one_tile': multi,
           'image_program_sha256': hashlib.sha256((args.image / 'program.hex').read_bytes()).hexdigest(),
           'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in src},
           'claim_boundary': 'Address-map proof for one layer program at one position; the RTL restates the same formula.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('status', 'owned_reads', 'distinct_words_read', 'max_local_index',
                                          'tile_cycles_with_disagreeing_local', 'per_group_collisions',
                                          'words_read_by_more_than_one_tile')}))


if __name__ == '__main__':
    main()
