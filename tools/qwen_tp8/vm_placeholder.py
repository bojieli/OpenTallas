#!/usr/bin/env python3
"""Qwen TP8 VM: PLACEHOLDER abstract + Liberty of the die master qfd_sp_vector_memory at the SLOT CHANGE REQUEST v2
rectangle (VM4, 2026-10-13), so the die route + STA can carry the VM at its new place before the region clusters close.

    vm_placeholder.py --lef CASE_VM_MACRO.lef[.gz] --port-dirs CASE/port_dirs.json --out DIR

Input = the die generator's own VM macro (case elements.lef, MACRO qfd_sp_vector_memory at the v4 envelope
4708.8 x 2347.92 at (13284.0, 17249.76)).  Output = the same macro at 4838.4 x 2546.64 at (13284.0, 17051.04):
  * the W edge and the N face do not move on the die (N-face pins keep their x: the SU abutment span is unchanged),
  * S-face pins keep their x and follow the face 198.72 um to the south (local y stays 0),
  * the pin groups at the E end of the S face (x > 4,600: ar, xe_d, xe_r) follow the E edge (+129.6 um),
  * area pins (ck) move to the new centre; PG pin shapes are stretched to the new outline,
  * OBS M1 .. --obs-top (default M7 = the die generator's own VM obstruction, so tonight's die case is unchanged above M7;
    the region clusters will need M8 / M9 too: lane plan capacity is M4 - M9, see el1011-qwen-tp8.log VM4).
Liberty = tools/qwen_die_element_lib.py ASSUMED single-flop views (the die lead's die_sta_libs.py constants), library
qfd_vm_placeholder_<corner>, cell qfd_sp_vector_memory; directions from the case port_dirs.json.
NOT a routed view: pin positions are the die generator's provisional bundles, not the leaves' pins."""
import argparse, gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_die_element_lib as E   # noqa: E402
import abstract_pin_windows as APW   # noqa: E402

OLD = (4708.8, 2347.92); NEW = (4838.4, 2546.64); ORIGIN = (13284.0, 17051.04); DX = round(NEW[0] - OLD[0], 4)
EAST_X = 4600.0
LAYERS = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lef', required=True); ap.add_argument('--port-dirs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--obs-top', default='M7')
    # Q-DIE11b 10-18: pin-access windows (tools/abstract_pin_windows.py) at every face pin cluster, OBS-free on
    # M<lowest signal pin layer>..obs-top.  Default 0 (env OT_ABS_PIN_WINDOW_UM unset) = the previous full-outline OBS.
    import os
    ap.add_argument('--pin-window', type=float, default=float(os.environ.get('OT_ABS_PIN_WINDOW_UM', '0') or 0))
    a = ap.parse_args()
    op = gzip.open if a.lef.endswith('.gz') else open
    src = op(a.lef, 'rt').read().split('\n')
    out, pin, use, moved, n_pins = [], None, None, {}, 0
    sig_rects, layer = [], None
    i = 0
    while i < len(src):
        ln = src[i]; t = ln.split()
        if t[:1] == ['SIZE']:
            assert abs(float(t[1]) - OLD[0]) < 1e-6 and abs(float(t[3]) - OLD[1]) < 1e-6, ln
            ln = f'  SIZE {NEW[0]:.3f} BY {NEW[1]:.3f} ;'
        elif t[:1] == ['PIN']:
            pin = t[1]; use = None; n_pins += 1
        elif t[:1] == ['USE']:
            use = t[1]
        elif t[:1] == ['LAYER'] and pin:
            layer = t[1]
        elif t[:1] == ['OBS']:
            out.append('  OBS')
            sig = [r for r in sig_rects if r[2][0] <= 0.5 or r[2][1] <= 0.5 or r[2][2] >= NEW[0] - 0.5 or r[2][3] >= NEW[1] - 0.5]
            top = LAYERS.index(a.obs_top) + 1
            lo = min((int(r[1][1:]) for r in sig), default=4)
            win = APW.windows(NEW[0], NEW[1], sig, a.pin_window, max(lo, 1), top) if a.pin_window > 0 else {}
            for k_, L in enumerate(LAYERS[:top], 1):
                out += [f'    LAYER {L} ;'] + [f'      RECT {q[0]:.3f} {q[1]:.3f} {q[2]:.3f} {q[3]:.3f} ;' if win.get(k_) else
                                               f'      RECT 0 0 {NEW[0]:.3f} {NEW[1]:.3f} ;'
                                               for q in (APW.minus(NEW[0], NEW[1], win[k_]) if win.get(k_) else [None])]
            out.append('  END')
            while src[i].strip() != 'END':
                i += 1
            i += 1; pin = None; continue
        elif t[:1] == ['RECT'] and pin:
            x0, y0, x1, y1 = (float(v) for v in t[1:5]); g = pin.split('[')[0]
            if use in ('POWER', 'GROUND'):                    # stripes: stretch to the new outline
                if x1 - x0 > OLD[0] / 2: x1 = round(x1 + DX, 3)
                if y1 - y0 > OLD[1] / 2: y1 = round(y1 + NEW[1] - OLD[1], 3)
                how = 'pg'
            elif y1 >= OLD[1] - 1e-6:                         # N face: same x, new top
                y0, y1 = round(y0 + NEW[1] - OLD[1], 3), NEW[1]; how = 'N'
            elif y0 <= 1e-6:                                  # S face: follows the face; the E-end groups follow the E edge
                if x0 > EAST_X: x0, x1 = round(x0 + DX, 3), round(x1 + DX, 3); how = 'S_east_end'
                else: how = 'S'
            else:                                             # area pin: new centre
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; w, h = x1 - x0, y1 - y0
                nx, ny = round(NEW[0] / 2 / 0.048) * 0.048, round(NEW[1] / 2 / 0.048) * 0.048
                x0, x1, y0, y1 = round(nx - w / 2, 3), round(nx + w / 2, 3), round(ny - h / 2, 3), round(ny + h / 2, 3); how = 'area'
            if use not in ('POWER', 'GROUND') and layer:
                sig_rects.append((pin, layer, (x0, y0, x1, y1)))
            moved.setdefault(g, dict(how=how, bits=0, x=[x0, x1], layer=None)); m = moved[g]; m['bits'] += 1
            m['x'] = [min(m['x'][0], x0), max(m['x'][1], x1)]
            ln = f'        RECT {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} ;'
        out.append(ln); i += 1
    od = Path(a.out); od.mkdir(parents=True, exist_ok=True)
    lef = od / 'qfd_sp_vector_memory.lef'
    hdr = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', '']
    lef.write_text('\n'.join(hdr + out).rstrip('\n') + '\n\nEND LIBRARY\n')
    pins = E.lef_pins(lef)
    dirs = json.loads(Path(a.port_dirs).read_text())['qfd_sp_vector_memory']
    stubs = {'qfd_sp_vector_memory': {p: [d, 0, set()] for p, d in dirs.items()}}
    for c in ('tt', 'ff', 'ss'):
        p = od / f'qfd_sp_vector_memory_{c}.lib'
        E.write_lib(c, pins, stubs, p)
        p.write_text(p.read_text().replace(f'library (qfd_elements_{c})', f'library (qfd_vm_placeholder_{c})', 1))
    rec = dict(schema='opentallas.qwen-tp8.vm-placeholder.v1', master='qfd_sp_vector_memory', kind='PLACEHOLDER (assumed single-flop pins, no routed view)',
               size_um=list(NEW), origin_um=list(ORIGIN), was=dict(size_um=list(OLD), origin_um=[13284.0, 17249.76]),
               obs_layers=LAYERS[:LAYERS.index(a.obs_top) + 1], pin_window_um=a.pin_window, pins=n_pins, port_dirs=dirs,
               groups={g: dict(how=m['how'], shapes=m['bits'], x_um=[round(v, 3) for v in m['x']]) for g, m in sorted(moved.items())},
               rule='W edge and N face fixed on the die; S face 198.72 um south; ar / xe_d / xe_r follow the E edge (+129.6 um)')
    (od / 'placeholder.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(pins=n_pins, groups=len(moved), lef=str(lef))))


if __name__ == '__main__':
    main()
