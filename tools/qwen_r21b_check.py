#!/usr/bin/env python3
"""Qwen ROM die r21m / r21b / r21bt legality + slot check (qwen-repack 2026-10-08).

Builds the die of a die_top_lint Qwen recipe and records: die size against the 858 mm2 reticle, instance legality
(overlaps / outside), the spine blocks (tree top, VM, SU, sequencer, per-band serializer / slab / band-lane stacks),
the stack abutment gaps, the SU-VM gap, relay count and the spine free space left.

  python3 tools/qwen_r21b_check.py r21b --out results/rtl/qwen_repack_20261008/r21b_check.json
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L              # noqa: E402
import qwen_rom_fulldie_b3r2 as B     # noqa: E402

RETICLE_MM2 = 858.0


def overlaps(insts):
    ev = sorted(insts, key=lambda i: i.x)
    act, bad = [], []
    for i in ev:
        act = [a for a in act if a.x + a.w > i.x + 1e-3]
        for a in act:
            if min(a.y + a.h, i.y + i.h) - max(a.y, i.y) > 1e-3 and min(a.x + a.w, i.x + i.w) - max(a.x, i.x) > 1e-3:
                bad.append((a.name, i.name))
        act.append(i)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recipe', choices=sorted(L.QWEN_RECIPES))
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    r = dict(L.QWEN_RECIPES[a.recipe])
    cdc = r.pop('cdc')
    v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    die, g, ins = m['die'], m['geo'], m['insts']
    W, H = die['w'], die['h']
    ov = overlaps(ins)
    out = [i.name for i in ins if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > W + 1e-3 or i.y + i.h > H + 1e-3]
    sp = {i.name: i for i in ins if i.kind == 'spine_block'}
    box = lambda i: [round(i.x, 3), round(i.y, 3), round(i.w, 3), round(i.h, 3)]   # noqa: E731
    stacks = []
    for b in range(B.BANDS):
        s, p, bl = sp.get(f'sp_res_ser_{b}'), sp.get(f'sp_port_tiles_{b}'), sp.get(f'sp_band_lanes_{b}')
        if s and p and bl:
            stacks.append(dict(band=b, ser=box(s), slab=box(p), lanes=box(bl), same_x=abs(s.x - p.x) < 1e-3 and abs(bl.x - p.x) < 1e-3,
                               ser_gap_um=round(p.y - (s.y + s.h), 3), lanes_gap_um=round(bl.y - (p.y + p.h), 3)))
    su, vm, tt = sp.get('sp_su64_sfu'), sp.get('sp_vector_memory'), sp.get('sp_tree_top')
    inst_mm2 = sum(i.w * i.h for i in ins) / 1e6
    sp_mm2 = sum(i.w * i.h for i in sp.values()) / 1e6
    cw = g['cw']
    ncol = 3 if g.get('x_col_m') is not None else 2
    rec = dict(
        schema='opentallas.qwen_r21b_check.v1', recipe=a.recipe, recipe_args={k: v_ for k, v_ in r.items()},
        die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 3), reticle_mm2=RETICLE_MM2,
        margin_mm2=round(RETICLE_MM2 - W * H / 1e6, 3), fits_reticle=W * H / 1e6 <= RETICLE_MM2,
        instances=len(ins), instance_mm2=round(inst_mm2, 2), die_utilisation=round(inst_mm2 / (W * H / 1e6), 4),
        spine_columns=ncol, spine_block_mm2=round(sp_mm2, 2), spine_column_mm2=round(ncol * cw * H / 1e6, 2),
        spine_utilisation=round(sp_mm2 / (ncol * cw * H / 1e6), 4),
        relays=sum(1 for i in ins if 'relay' in (i.kind or '') or i.name.startswith('relay')), buses=len(m['buses']),
        legality=dict(overlaps=len(ov), overlap_examples=ov[:10], outside=len(out), outside_examples=out[:10]),
        tree_top=box(tt) if tt else None, vm=box(vm) if vm else None, su=box(su) if su else None,
        su_vm_gap_um=round(vm.y - (su.y + su.h), 3) if su and vm else None,
        slots_um=g.get('r21m_slots_um'), stacks=stacks, spine_free_after_um=g.get('spine_free_after_um'),
        spine_parts=g.get('spine_parts_r21m'))
    ok = rec['fits_reticle'] and not ov and not out and all(s['same_x'] and abs(s['ser_gap_um']) < 0.05
                                                            and abs(s['lanes_gap_um']) < 0.05 for s in stacks)
    rec['ok'] = ok
    txt = json.dumps(rec, indent=1, default=str) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt)
    print(json.dumps({k: rec[k] for k in ('recipe', 'die_um', 'die_mm2', 'margin_mm2', 'instances', 'die_utilisation',
                                          'spine_utilisation', 'relays', 'legality', 'tree_top', 'su_vm_gap_um', 'ok')}))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
