#!/usr/bin/env python3
"""Bounded exact-source hard-red geometry model; no layout or cycle inference."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/codex_slice2_native_1021/resume1340/red2b_binding_plan'


def pins(path):
    result = {}
    for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s*\n', path.read_text(), re.S):
        result[m[1]] = [list(map(float, q)) for q in re.findall(
            r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;', m[2])]
    return result


def moved(rects, x, y):
    return [[a+x, b+y, c+x, d+y] for a, b, c, d in rects]


def distance(a, b):
    return max(a[0]-b[2], b[0]-a[2], 0) + max(a[1]-b[3], b[1]-a[3], 0)


def main():
    fp = json.loads((OUT / 'selected_parent_floorplan.json').read_text())
    blocks = {b['inst']: b for b in fp['blocks']}
    lp_path = ROOT / 'rtl/qwen_dv/s5/s8/lp/qfd_dv_s8_lp.sv'
    lp = lp_path.read_text()
    assert re.search(r'qfd_dv_s5_red2_leaf\s+u_red\s*\([^;]*\.l_out\(L_l_out\)', lp)
    for lane in range(8):
        assert re.search(rf'qfd_dv_s5_lrly\s+u_lrly{lane}\s*\([^;]*'
                         rf'\.l_out\(L_l_out\[{32*lane+31}:{32*lane}\]\)', lp)
        assert blocks[f'u_lrly{lane}']['orient'] == 'R0'
    lr, red = pins(OUT / 'lrly.lef'), pins(OUT / 'red2b.lef')
    # Exact selected slice9 r_su central domain plus slice10's top override.
    domain = [950.4, 2980.8, 1512.0, 3542.4]
    width, height, rule = 280.8, 194.4, 405.0
    candidates = []
    for ix in range(100):
        x = round(43.2*ix, 3)
        if not domain[0] <= x <= domain[2]-width:
            continue
        for iy in range(120):
            y = round(43.2*iy, 3)
            if not domain[1] <= y <= domain[3]-height:
                continue
            clearance = min(max(max(b['x']-x-width, x-b['x']-b['w'], 0),
                                max(b['y']-y-height, y-b['y']-b['h'], 0))
                            for b in fp['blocks'])
            if clearance < 20:
                continue
            reaches = []
            for lane in range(8):
                b = blocks[f'u_lrly{lane}']
                for bit in range(32):
                    src = moved(lr[f'l_out[{bit}]'], b['x'], b['y'])
                    dst = moved(red[f'l_out[{32*lane+bit}]'], x, y)
                    reaches.append((min(distance(a, z) for a in src for z in dst), lane, bit))
            worst = max(reaches)
            candidates.append(dict(at=[x, y], orientation='R0',
                                   min_macro_clearance_um=round(clearance, 3),
                                   max_matching_rect_min_um=round(worst[0], 3),
                                   worst_lane_bit=list(worst[1:])))
    # Necessary horizontal condition for ANY translation/orientation, even with
    # independently favourable choices of pin rectangles. Rotations cannot make
    # this rectangular child wider than max(width,height).
    a = moved(lr['l_out[0]'], blocks['u_lrly0']['x'], blocks['u_lrly0']['y'])
    b = moved(lr['l_out[0]'], blocks['u_lrly7']['x'], blocks['u_lrly7']['y'])
    span = min(q[0] for q in b) - max(q[2] for q in a)
    lower = (span-max(width, height))/2
    assert lower > rule
    result = dict(verdict='FAIL direct hard-red binding', rule_um=rule,
                  legal_domain=domain, outline_um=[width, height],
                  source_pin_span_lower_um=round(span, 3),
                  any_placement_orientation_minimax_horizontal_lower_um=round(lower, 3),
                  legal_grid_candidates=candidates,
                  best_R0=min(candidates, key=lambda q: q['max_matching_rect_min_um']),
                  source_edge='Direct L_l_out wires; no LP landing on this edge',
                  scope='Source geometry model only, not a placed-parent qualification',
                  required_action='Real registered transport or distributed reduction; stage count unpriced',
                  input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [lp_path, OUT/'selected_parent_floorplan.json', OUT/'red2b.lef', OUT/'lrly.lef']})
    (OUT / 'geometry.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['verdict', 'source_pin_span_lower_um',
                                           'any_placement_orientation_minimax_horizontal_lower_um', 'best_R0']}))


if __name__ == '__main__':
    main()
