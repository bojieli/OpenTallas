#!/usr/bin/env python3
"""Legality / area / abutment check of the r21m Qwen ROM die recipe (qwen-vm-me 2026-10-08).

Builds the die model with the die-top lint's loader (recipe r21m = r21f + su_core_clock + vm_me) and r21f, and checks:
  * placement legality: every instance inside the die outline, no two instances overlap (x-sweep);
  * the reticle: die area <= 858 mm2 (the owner's hard limit), and the utilisation of the die (instance area / die)
    and of the spine (spine-block area / the three spine columns);
  * the r21m spine: the banked VM, the stream unit abutted below it (same x / width, gap = the generator's SHAVE),
    the sequencer, one band-lane block stacked on each band's W primary slab (abutted), one result serializer a band;
  * the SU <-> VM descriptor bus: every bit's SU pin and VM pin at the same die x, facing across the gap, one track each.
    python3 tools/qwen_vm_me/r21m_check.py [--out results/rtl/qwen_vm_me_20261008/r21m_check.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_missing'))
import die_top_lint as L  # noqa: E402
from su_vm_abut_check import legality  # noqa: E402


def load(recipe):
    L._QW.clear()
    L.QWEN_RECIPE = recipe
    return L.load_qwen()


def summary(v, m):
    g = m['geo']
    die = m['die']
    inst = sum(i.w * i.h for i in m['insts']) / 1e6
    sp = [i for i in m['insts'] if i.kind == 'spine_block']
    ncol = 3 if getattr(v, 'XCOL', 0.0) else 2
    col_h = (g['y_top'] - g['y0']) - 2 * v.HCH
    spine_area = ncol * g['cw'] * col_h / 1e6
    return dict(die_um=[round(die['w'], 3), round(die['h'], 3)], die_mm2=die['mm2'], margin_mm2=die['margin_mm2'],
                instance_mm2=round(inst, 2), die_utilisation=round(inst / die['mm2'], 4),
                spine_columns=ncol, spine_block_mm2=round(sum(i.w * i.h for i in sp) / 1e6, 2),
                spine_column_mm2=round(spine_area, 2),
                spine_utilisation=round(sum(i.w * i.h for i in sp) / 1e6 / spine_area, 4),
                relays=sum(1 for i in m['insts'] if i.kind == 'relay'), instances=len(m['insts']), buses=len(m['buses']))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'results/rtl/qwen_vm_me_20261008/r21m_check.json')
    a = ap.parse_args()
    v0, m0, _ = load('r21f')
    s0 = summary(v0, m0)
    v, m, _ = load('r21m')
    s1 = summary(v, m)
    leg = legality(m)
    by = {i.name: i for i in m['insts']}
    su, vm = by['sp_su64_sfu'], by['sp_vector_memory']
    stacks = []
    for b in range(6):
        bl = by[f'sp_band_lanes_{b}']
        prim = by[m['b3r2']['groups']['primary'][b]]
        sr = by[f'sp_res_ser_{b}']
        stacks.append(dict(band=b, primary=prim.name, lanes_y=round(bl.y, 3), slab_top=round(prim.y + prim.h, 3),
                           gap_um=round(bl.y - (prim.y + prim.h), 4), ser_gap_um=round(prim.y - (sr.y + sr.h), 4),
                           same_x=abs(bl.x - prim.x) < 1e-6 and abs(sr.x - prim.x) < 1e-6))
    sers = [dict(name=i.name, x=round(i.x, 3), y=round(i.y, 3), h=round(i.h, 3)) for i in m['insts']
            if i.name.startswith('sp_res_ser_')]
    M = v.masters(m)
    ports = {}
    ok = leg['overlaps'] == 0 and leg['outside'] == 0 and m['die']['mm2'] <= 858
    for (sp, vp, bid) in (('va', 'sa', 'su_vm_a'), ('vq', 'sq', 'su_vm_q')):
        bits = next(b for i_, c, b, e in m['buses'] if i_ == bid)
        rs = v.pin_rects(M['qfd_sp_su64_sfu'], 1, {p: (bits if p == sp else 0) for p in M['qfd_sp_su64_sfu'].order})
        rv = v.pin_rects(M['qfd_sp_vector_memory'], 1, {p: (bits if p == vp else 0) for p in M['qfd_sp_vector_memory'].order})
        bad_x = bad_gap = 0
        xs = []
        for (_, _, (a0, b0, c0, d0)), (_, _, (a1, b1, c1, d1)) in zip(rs, rv):
            xs_ = su.x + (a0 + c0) / 2
            bad_x += abs(xs_ - (vm.x + (a1 + c1) / 2)) > 1e-6
            bad_gap += (vm.y + b1) - (su.y + d0) > 0.03
            xs.append(round(xs_, 4))
        ports[bid] = dict(bits=bits, su_pins=len(rs), vm_pins=len(rv), x_mismatch=bad_x, not_facing=bad_gap,
                          shared_tracks=len(xs) - len(set(xs)))
        ok = ok and len(rs) == len(rv) == bits and bad_x == 0 and bad_gap == 0 and len(xs) == len(set(xs))
    ok = ok and all(s['same_x'] and 0.0 <= s['gap_um'] <= 0.05 and 0.0 <= s['ser_gap_um'] <= 0.05 for s in stacks) and len(sers) == 6
    rec = dict(schema='opentallas.qwen_r21m_check.v1', recipe='r21m', r21f=s0, r21m_summary=s1, legality_r21m=leg,
               su=[su.x, su.y, su.w, su.h], vm=[vm.x, vm.y, vm.w, vm.h], su_vm_gap_um=round(vm.y - (su.y + su.h), 4),
               su_vm_ports=ports, band_lane_stacks=stacks, serializers=sers, r21m_record=m.get('r21m'),
               spine_parts=m['geo'].get('spine_parts_r21m'), spine_free_after_um=m['geo'].get('spine_free_after_um'),
               ok=bool(ok))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps({k: rec[k] for k in ('ok', 'r21f', 'r21m_summary', 'legality_r21m', 'su_vm_gap_um', 'su_vm_ports')},
                     indent=1, default=str))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
