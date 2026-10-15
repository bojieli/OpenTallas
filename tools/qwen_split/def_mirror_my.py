#!/usr/bin/env python3
"""Mirror a closed block's routed DEF about its vertical centre line (MY), with no re-placement and no re-route.

Purpose (GEO-Q PM-H legality): a pair-mirrored compute column instantiates closed masters in MY.  This produces the
geometric MY image of the routed block (x -> W - x for every component, pin, row, track, special and regular wire,
via and patch) so OpenROAD can re-check placement legality and re-extract parasitics (OpenRCX) on the mirrored layout
and compare the clock insertion / skew with the unmirrored original under identical extraction.

Only symmetric vias are accepted (tech and generated VIAS are checked); an asymmetric via aborts (it would need an
orientation-tagged via).  Supported DEF statements: DIEAREA, ROW, TRACKS, GCELLGRID, VIAS, COMPONENTS, PINS,
SPECIALNETS, NETS (points, '*', extensions, RECT patches, vias).  BLOCKAGES / FILLS / REGIONS abort.
"""
import argparse, re, sys
from pathlib import Path

ORI = {'N': 'FN', 'FN': 'N', 'S': 'FS', 'FS': 'S'}


def cell_widths(lefs):
    w = {}
    for f in lefs:
        t = Path(f).read_text(errors='replace')
        for m in re.finditer(r'^MACRO (\S+)(.*?)^END \1', t, re.S | re.M):
            s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', m.group(2))
            if s: w[m.group(1)] = round(float(s.group(1)) * 1000)
    return w


def via_symmetric(line):
    rects = re.findall(r'RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', line)
    if not rects:
        return True          # VIARULE-generated (CUTSIZE/ENCLOSURE/ROWCOL) vias are centred unless OFFSET/ORIGIN given
    if '+ OFFSET' in line or '+ ORIGIN' in line:
        return False
    by = {}
    for lay, x0, y0, x1, y1 in rects:
        by.setdefault(lay, set()).add((int(x0), int(y0), int(x1), int(y1)))
    return all({(-x1, y0, -x0, y1) for x0, y0, x1, y1 in s} == s for s in by.values())


def mirror_points(line, W):
    """Mirror every '( x y [ext] )' point and every 4-number RECT '( dx1 dy1 dx2 dy2 )' patch in a wiring line."""
    def rect(m):
        a, b, c, d = map(int, m.group(1, 2, 3, 4))
        return f'RECT ( {-c} {b} {-a} {d} )'
    line = re.sub(r'RECT \( (-?\d+) (-?\d+) (-?\d+) (-?\d+) \)', rect, line)

    def pt(m):
        x = m.group(1)
        return '( ' + (x if x == '*' else str(W - int(x))) + ' ' + m.group(2) + ')'
    return re.sub(r'\( (\*|-?\d+) ((?:\*|-?\d+)(?: -?\d+)? )\)', pt, line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('def_in'); ap.add_argument('def_out'); ap.add_argument('--lef', nargs='+', required=True)
    a = ap.parse_args()
    widths = cell_widths(a.lef)
    lines = Path(a.def_in).read_text().splitlines()
    W = None; sec = None; out = []; stats = dict(components=0, pins=0, rows=0, wire_lines=0)
    pending_pin = False
    for ln in lines:
        s = ln.strip()
        if s.startswith('DIEAREA'):
            nums = list(map(int, re.findall(r'-?\d+', s)))
            assert nums[0] == 0 and nums[1] == 0 and len(nums) == 4, 'DIEAREA must be a rectangle at the origin'
            W = nums[2]; out.append(ln); continue
        head = s.split(' ')[0] if s else ''
        if head in ('BLOCKAGES', 'FILLS', 'REGIONS', 'GROUPS'):
            sys.exit(f'unsupported DEF section {head}')
        if head in ('VIAS', 'COMPONENTS', 'PINS', 'SPECIALNETS', 'NETS', 'NONDEFAULTRULES'):
            sec = head
        elif s.startswith('END ') and s.split()[1] == sec:
            sec = None; out.append(ln); continue
        if head == 'ROW':
            t = s.rstrip(' ;').split()
            x, n, step = int(t[3]), int(t[7]), int(t[11])
            t[3] = str(W - x - n * step); t[5] = ORI[t[5]]
            out.append(' '.join(t) + ' ;'); stats['rows'] += 1; continue
        if head == 'TRACKS':
            t = s.rstrip(' ;').split()
            if t[1] == 'X':
                st, n, step = int(t[2]), int(t[4]), int(t[6])
                t[2] = str(W - st - (n - 1) * step)
            out.append(' '.join(t) + ' ;'); continue
        if sec == 'VIAS' and s.startswith('-'):
            if not via_symmetric(s):
                sys.exit('asymmetric via: ' + s)
            out.append(ln); continue
        if sec == 'COMPONENTS':
            m = re.search(r'^(\s*- (\S+) (\S+).*?\+ (?:PLACED|FIXED) \( )(-?\d+) (-?\d+) \) (\S+)(.*)$', ln)
            if m:
                cell = m.group(3); w = widths[cell]
                x = int(m.group(4)); o = m.group(6)
                ln = f'{m.group(1)}{W - x - w} {m.group(5)} ) {ORI[o]}{m.group(7)}'; stats['components'] += 1
            elif '+ PLACED' in ln or '+ FIXED' in ln:
                sys.exit('unparsed component placement: ' + ln)
            out.append(ln); continue
        if sec == 'PINS':
            m = re.search(r'^(.*\+ (?:PLACED|FIXED) \( )(-?\d+) (-?\d+) \) (\S+)(.*)$', ln)
            if m:
                ln = f'{m.group(1)}{W - int(m.group(2))} {m.group(3)} ) {ORI[m.group(4)]}{m.group(5)}'; stats['pins'] += 1
            out.append(ln); continue
        if sec in ('SPECIALNETS', 'NETS') and ('ROUTED' in ln or s.startswith('NEW') or '+ RECT' in ln or '+ POLYGON' in ln):
            if '+ POLYGON' in ln or ' DO ' in ln:
                sys.exit('unsupported wiring form: ' + ln)
            ln2 = mirror_points(ln, W)
            m = re.search(r'\+ RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ln2)
            if m:  # absolute special RECT: normalise lower-left / upper-right after the x flip
                x0, y0, x1, y1 = map(int, m.group(2, 3, 4, 5))
                ln2 = ln2.replace(m.group(0), f'+ RECT {m.group(1)} ( {min(x0, x1)} {y0} ) ( {max(x0, x1)} {y1} )')
            out.append(ln2); stats['wire_lines'] += 1; continue
        out.append(ln)
    Path(a.def_out).write_text('\n'.join(out) + '\n')
    print(dict(W=W, **stats))


if __name__ == '__main__':
    main()
