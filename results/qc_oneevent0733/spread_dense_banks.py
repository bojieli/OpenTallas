#!/usr/bin/env python3
"""Spread the fifteen failing QC bank layouts onto adjacent legal rows.

No bit permutation, station, endpoint, macro, clock or cycle change. Intended
only for this unfrozen event candidate; all original failures remain in Git.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import schema as S
from gen_phys import type_pins
import infra_sites as IS


def intersects(a, b):
    return min(a[2], b[2])-max(a[0], b[0]) > 1e-6 and min(a[3], b[3])-max(a[1], b[1]) > 1e-6


def apply(raw):
    raw = copy.deepcopy(raw)
    P = S.Plan(raw)
    targets = json.loads((HERE/'dense_targets.json').read_text())
    records, changed, types = [], set(), set()
    for tn, sn, reg in targets:
        t = P.types[tn]
        slot = next(s for s in t['ft_slots'] if s['name'] == sn)
        at = slot['regs_um'][reg]
        gi = min(range(len(slot['bit_sites_um'])), key=lambda j: sum(
            abs(sum(q[k] for q in slot['bit_sites_um'][j])/len(slot['bit_sites_um'][j])-at[k]) for k in [0, 1]))
        key = tn, sn, gi
        assert key not in changed, key
        changed.add(key); types.add(tn)
        points = slot['bit_sites_um'][gi]
        cw, ch = slot['bit_site_cell_um']
        old_y = sorted(set(y for x, y in points))
        x0, x1 = min(x for x, y in points), max(x for x, y in points)+cw
        old_area = (x1-x0)*(old_y[-1]-old_y[0]+ch)
        old_fill = len(points)*cw*ch/old_area
        assert old_fill > .6, (key, old_fill)
        rows = math.ceil(len(points)*cw*ch/((x1-x0)*.58*ch))
        assert rows > len(old_y), key
        start = math.floor(old_y[0]/ch-(rows-len(old_y))/2+1e-6)
        move = {y: round((start+round(i*(rows-1)/(len(old_y)-1)))*ch, 6)
                for i, y in enumerate(old_y)}
        slot['bit_sites_um'][gi] = [[x, move[y]] for x, y in points]
        records.append(dict(type=tn, slot=sn, group=gi, bits=len(points),
                            old_fill=old_fill, new_fill=len(points)*cw/((x1-x0)*rows),
                            old_rows=len(old_y), new_rows=rows,
                            max_displacement_um=max(abs(y-move[y]) for y in old_y)))
    # Check every bit and every leg in the affected slots with actual primitive
    # centre offsets. Allocated 1.404um envelopes remain the collision reserve.
    max_hop = 0.
    for tn in sorted(types):
        t = P.types[tn]
        pins = {(b, i): (x, y) for b, i, _, x, y, _ in type_pins(P, tn)}
        cores = IS.type_cores(t)
        buckets = {}
        for slot in t['ft_slots']:
            cw, ch = slot.get('bit_site_cell_um', [1.404, .27])
            for gi, group in enumerate(slot.get('bit_sites_um', [])):
                for bit, (x, y) in enumerate(group):
                    rect = x, y, x+cw, y+ch
                    key = tn, slot['name'], gi
                    ident = slot['name'], gi, bit
                    if key in changed:
                        assert 0 <= x and 0 <= y and rect[2] <= t['outline_um'][0] and rect[3] <= t['outline_um'][1], ident
                        assert not any(intersects(rect, c[:4]) for c in cores), (tn, ident, 'core collision')
                    for row in range(math.floor(y/.27+1e-6), math.ceil((y+ch)/.27-1e-6)):
                        for other, other_rect, other_changed in buckets.get(row, []):
                            if key in changed or other_changed:
                                assert not intersects(rect, other_rect), (tn, ident, other, 'station collision')
                        buckets.setdefault(row, []).append((ident, rect, key in changed))
            if not any(k[:2] == (tn, slot['name']) for k in changed):
                continue
            groups = slot['bit_sites_um']; n = len(groups[0])
            assert all(len(g) == n for g in groups)
            assert n == slot['width']+1, (tn, slot['name'], 'epoch inventory')
            for bit in range(n):
                chain = [pins[slot['name']+'_i', bit]]
                chain += [(x+.54, y+.135) for x, y in (g[bit] for g in groups)]
                chain += [pins[slot['name']+'_o', bit]]
                for a, b in zip(chain, chain[1:]):
                    hop = abs(a[0]-b[0])+abs(a[1]-b[1])
                    max_hop = max(max_hop, hop)
                    assert hop <= 405+1e-6, (tn, slot['name'], bit, hop)
    return raw, dict(verdict='PASS', changed_groups=len(records), changed_types=len(types),
                     added_cycles=0, permutation='NONE', max_actual_paired_hop_um=max_hop,
                     collision_basis='allocated slot.bit_site_cell_um envelopes vs every existing station and hard core',
                     hop_basis='fixed type_pins and actual DFFHQNx1 1.08x0.27um cell centres', banks=records)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    path = ROOT/'physical/die_plan/qwen_compute/candidate_oneqc0733.json'
    result, report = apply(S.load(path))
    (HERE/'dense_bank_repair.json').write_text(json.dumps(report, indent=2)+'\n')
    if a.apply:
        path.write_text(json.dumps(result, indent=1)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'banks'}))
