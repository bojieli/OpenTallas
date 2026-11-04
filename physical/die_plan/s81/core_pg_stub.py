#!/usr/bin/env python3
"""M5 ports for S81 plan stubs using the standard core PDN recipe.

The native core recipe has CORE_AREA inset4.32 and M5 width.12 spacing.072
pitch4.32 offset2.064. Measured ORFS follow-pin ordering is VSS then VDD,
not alternating half-pitch rails. Signed/write_abstract views must not use this.
"""
import argparse
import re
from pathlib import Path


def rectangles(width, height):
    margin, pitch, offset, wire, spacing = 4.32, 4.32, 2.064, 0.12, 0.072
    if min(width,height) <= 2*margin:
        raise ValueError('core too small for the existing standard PDN recipe')
    result = {}
    for net, shift in [('VSS',0),('VDD',wire+spacing)]:
        rows=[];x=margin+offset+shift
        while x+wire/2 <= width-margin+1e-9:
            rows.append([round(x-wire/2,6),margin,round(x+wire/2,6),round(height-margin,6)])
            x+=pitch
        if not rows:raise ValueError('no complete core PG stripe for '+net)
        result[net]=rows
    return result


def port_lines(width,height):
    output=[]
    for net,rows in rectangles(width,height).items():
        output += [f'  PIN {net}','    DIRECTION INOUT ;',f"    USE {'POWER' if net=='VDD' else 'GROUND'} ;",'    PORT','      LAYER M5 ;']
        output += ['        RECT %.6f %.6f %.6f %.6f ;'%tuple(row) for row in rows]
        output += ['    END',f'  END {net}']
    return output


def refresh(text):
    size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
    if not size:raise ValueError('missing LEF SIZE')
    for net in ['VDD','VSS']:
        pattern=r'(?m)^  PIN '+net+r'\s*\n.*?^  END '+net+r'\s*\n'
        match=re.search(pattern,text,re.S|re.M)
        if match:
            if re.search(r'\bRECT\b',match.group()):
                raise ValueError('preserve existing actual PG geometry: '+net)
            text=text[:match.start()]+text[match.end():]
    where=re.search(r'(?m)^  OBS\s*$',text)
    if not where:raise ValueError('stub has no OBS insertion point')
    lines='\n'.join(port_lines(float(size[1]),float(size[2])))+'\n'
    return text[:where.start()]+lines+text[where.start():]


NATIVE_TOP = "M5"   # native S81 core recipe: MAX_ROUTING_LAYER M5 (gen_core_kit_legacy; signed ve_m abstract OBS M1-M5)


def clip_obs(text, top=NATIVE_TOP):
    """Drop OBS layers above `top` (the native core's routing ceiling).  A stub that obstructs M6/M7 over its M5 PG
    pins makes the parent core_pg grid (M5 -> M6 connect) fail PDN-0006 and blocks the parent M6/M7 straps that the
    signed write_abstract view leaves open."""
    lim = int(top[1:])
    out, skip, in_obs = [], False, False
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s == "OBS":
            in_obs = True
        elif in_obs and s == "END":
            in_obs, skip = False, False
        elif in_obs and s.startswith("LAYER "):
            m = re.match(r"LAYER M(\d+)\b", s)
            skip = bool(m and int(m.group(1)) > lim)
            if skip:
                continue
        elif in_obs and skip:
            continue
        out.append(line)
    return "".join(out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lef',type=Path)
    parser.add_argument('--out',type=Path,required=True,help='fresh candidate output, never rewrite a signed view')
    parser.add_argument('--clip-obs',action='store_true',help='only clip OBS above the native ceiling (PG pins kept)')
    args=parser.parse_args()
    if args.out.exists():parser.error('refusing existing output')
    src=args.lef.read_text()
    args.out.write_text(clip_obs(src) if args.clip_obs else clip_obs(refresh(src)))
