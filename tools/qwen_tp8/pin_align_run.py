#!/usr/bin/env python3
"""qwen-tp8 die lead r9: tools/hier_contract/pin_align.py on the tp8b generator's OWN pin rectangles (v.pin_rects, the
same rectangles the case LEF gets, instance orientation applied) -- no RTL files, no die_top_lint binding tables, so it
runs in the generator's build tree right after the relay plan.  record(v, m) -> (record, rows)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import pin_align as PA   # noqa: E402


def record(v, m, top=200):
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    tab = {}
    for name, mst in M.items():
        t = {}
        for nm, layer, r in v.pin_rects(mst, 1, {q: pw.get((name, q), 0) for q in mst.order}):
            mm = re.fullmatch(r'(.*)\[(\d+)\]', nm)
            base, i = (mm.group(1), int(mm.group(2))) if mm else (nm, 0)
            t.setdefault(base, {})[i] = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, layer)
        tab[name] = (mst.w, mst.h, t)
    extra = getattr(v, 'PIN_POS_EXTRA', None) or {}

    def locate(it, port, bits):
        if (it.name, port) in extra:                  # a PHY pin group known by its centroid only: length, no face
            x, y = extra[(it.name, port)]
            return [(x, y, None, None)] * bits
        w, h, t = tab.get(it.master, (it.w, it.h, {}))
        pins = t.get(port.lstrip('*'))
        if pins is None:
            return [None] * bits
        out = []
        for i in range(bits):
            q = pins.get(i)
            if q is None:
                out.append(None)
                continue
            x, y, layer = q
            d = dict(W=x, E=w - x, S=y, N=h - y)
            f = min(d, key=d.get) if min(d.values()) <= 1.0 else None
            if it.orient in ('MY', 'R180'):
                x = w - x
                f = {'E': 'W', 'W': 'E'}.get(f, f)
            if it.orient in ('MX', 'R180'):
                y = h - y
                f = {'N': 'S', 'S': 'N'}.get(f, f)
            out.append((it.x + x, it.y + y, f, layer))
        return out
    rows = []
    rec = PA.analyze_points(m['insts'], m['buses'], locate, top=top, rows_out=rows)
    rec.update(die='qwen_rom_tp8', pin_source='generator pin rectangles (v.pin_rects, tools/qwen_tp8/pin_align_run.py)')
    return rec, rows, PA.line(rec)
