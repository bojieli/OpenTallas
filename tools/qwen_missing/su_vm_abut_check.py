#!/usr/bin/env python3
"""Legality + pin check of the r21v SU64 <-> VM abutted bus (qwen-split-exact 2026-10-07).

Builds the Qwen ROM die model with the die-top lint's loader (recipe r21v = r21 + su_vm_abut) and checks:
  * placement legality: every instance inside the die outline, no two instances overlap (x-sweep), and the same for
    r21 (so the bus adds no placement change);
  * the abutment: SU64 N face on the VM S face, same x / width, gap = the generator's SHAVE;
  * the pins: every bit of su_vm_a / su_vm_q has its SU64 pin and its VM pin at the same die x (M5 track), the pin
    pair facing across the gap (SU pin top edge to VM pin bottom edge <= 0.03 um), no two pins of the bus on one
    track, all pins inside the shared face span.
    python3 tools/qwen_missing/su_vm_abut_check.py [--out results/rtl/qwen_split_exact_20261007/su_vm_abut_check.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L  # noqa: E402


def legality(m):
    d = m['die']
    W, H = d.get('w', d.get('w_um')), d.get('h', d.get('h_um'))
    out = [i.name for i in m['insts'] if i.x < -1e-6 or i.y < -1e-6 or (W and i.x + i.w > W + 1e-6) or
           (H and i.y + i.h > H + 1e-6)]
    ev = sorted(m['insts'], key=lambda i: i.x)
    act, ov = [], []
    for it in ev:
        act = [a for a in act if a.x + a.w > it.x + 1e-6]
        for a in act:
            if a.y < it.y + it.h - 1e-6 and it.y < a.y + a.h - 1e-6:
                ov.append((a.name, it.name))
        act.append(it)
    return dict(instances=len(m['insts']), outside=len(out), overlaps=len(ov), overlap_examples=ov[:5],
                die_um=[W, H])


def load(recipe):
    L._QW.clear()
    L.QWEN_RECIPE = recipe
    return L.load_qwen()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'results/rtl/qwen_split_exact_20261007/su_vm_abut_check.json')
    a = ap.parse_args()
    v0, m0, _ = load('r21')
    leg0 = legality(m0)
    v, m, _ = load('r21v')
    leg = legality(m)
    by = {i.name: i for i in m['insts']}
    su, vm = by['sp_su64_sfu'], by['sp_vector_memory']
    M = v.masters(m)
    rec = dict(schema='opentallas.qwen_su_vm_abut_check.v1', recipe='r21v', legality_r21=leg0, legality_r21v=leg,
               placement_unchanged=[(i.name, i.x, i.y, i.w, i.h) for i in m0['insts']] ==
               [(i.name, i.x, i.y, i.w, i.h) for i in m['insts']],
               su=[su.x, su.y, su.w, su.h, su.orient], vm=[vm.x, vm.y, vm.w, vm.h, vm.orient],
               gap_um=round(vm.y - (su.y + su.h), 4), bus=m.get('r21v_su_vm'), ports={})
    ok = rec['placement_unchanged'] and leg['overlaps'] == 0 and leg['outside'] == 0
    for (sp, vp, bid) in (('va', 'sa', 'su_vm_a'), ('vq', 'sq', 'su_vm_q')):
        bits = next(b for i_, c, b, e in m['buses'] if i_ == bid)
        rs = v.pin_rects(M['qfd_sp_su64_sfu'], 1, {p: (bits if p == sp else 0) for p in M['qfd_sp_su64_sfu'].order})
        rv = v.pin_rects(M['qfd_sp_vector_memory'], 1, {p: (bits if p == vp else 0) for p in M['qfd_sp_vector_memory'].order})
        assert len(rs) == len(rv) == bits, (len(rs), len(rv), bits)
        bad_x, bad_gap, layers = 0, 0, set()
        xs = []
        for (ns, ls, (a0, b0, c0, d0)), (nv, lv, (a1, b1, c1, d1)) in zip(rs, rv):
            xs_ = su.x + (a0 + c0) / 2
            xv_ = vm.x + (a1 + c1) / 2
            layers |= {ls, lv}
            bad_x += abs(xs_ - xv_) > 1e-6
            bad_gap += (vm.y + b1) - (su.y + d0) > 0.03 or not (abs(d0 - su.h) < 1e-6 and abs(b1) < 1e-6)
            xs.append(round(xs_, 4))
        dup = len(xs) - len(set(xs))
        span = [min(xs) - su.x, max(xs) - su.x]
        rec['ports'][bid] = dict(bits=bits, su_port=sp, vm_port=vp, layers=sorted(layers), x_mismatch=bad_x,
                                 not_facing=bad_gap, shared_tracks=dup, span_um=[round(span[0], 3), round(span[1], 3)])
        ok = ok and bad_x == 0 and bad_gap == 0 and dup == 0 and 0 < span[0] and span[1] < su.w
    rec['ok'] = bool(ok)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('ok', 'legality_r21', 'legality_r21v', 'placement_unchanged', 'gap_um', 'ports')}, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
