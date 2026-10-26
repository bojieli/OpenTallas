#!/usr/bin/env python3
"""Declare the S81 HBM PHY view/origin and project its real clock/reset pins.

The old hard partition defaulted reset to a synthetic clock-grid point. A bare
PHY has one clock/reset terminal; use the existing native LEF, with an explicit
legal placement origin, and retain every pipeline/data/boot-depth contract.
"""
import argparse
import copy
import json
import re
from pathlib import Path

MODULE = 'ot_hbm3e_phy_v41x_aw30_e8p5'
VIEW = Path('physical/asap7_memory_macros_v2') / MODULE / (MODULE + '.lef')
ORIGIN_UM = (8.64, 8.64)  # 0 mod48nm and ASAP7 site/row grid, with an explicit macro halo


def lef_contract(path):
    text = Path(path).read_text()
    size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', text)
    if not size:
        raise ValueError(f'PHY LEF has no SIZE: {path}')
    pins = {}
    for name in ('clk', 'rst_n'):
        block = re.search(r'^\s*PIN\s+' + name + r'\s*\n(.*?)^\s*END\s+' + name + r'\s*$', text, re.M | re.S)
        if not block:
            raise ValueError(f'PHY LEF has no unique {name}: {path}')
        layer = re.search(r'\bLAYER\s+(\S+)\s*;', block.group(1))
        rectangles = re.findall(r'\bRECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;', block.group(1))
        if not layer or len(rectangles) != 1:
            raise ValueError(f'PHY LEF {name} must have one unambiguous terminal rectangle')
        rect = list(map(float, rectangles[0]))
        pins[name] = dict(layer=layer.group(1), rect_um=rect,
                          center_um=[(rect[0]+rect[2])/2, (rect[1]+rect[3])/2])
    return dict(size_um=list(map(float, size.groups())), pins=pins)


def apply(raw, repo):
    if raw.get('die', {}).get('name') != 's81':
        raise ValueError('native PHY control projection is scoped to S81')
    contract = lef_contract(Path(repo) / VIEW)
    changed = []
    for name, t in raw['partition_types'].items():
        if not t.get('hard'):
            continue
        contents = t.get('contents', [])
        phy = [c for c in contents if c.get('module') == MODULE]
        if not phy:
            continue
        if len(phy) != 1 or len(contents) != 1:
            raise ValueError(f'{name}: HBM PHY must be the sole hard content')
        c = phy[0]
        origin = tuple(c.get('origin_um', ORIGIN_UM))
        if c.get('orient', 'R0') != 'R0':
            raise ValueError(f'{name}: PHY pin projection currently requires its actual R0 placement')
        w, h = contract['size_um']; tw, th = t['outline_um']
        if origin[0] < 4.32 or origin[1] < 4.32 or origin[0]+w+4.32 > tw or origin[1]+h+4.32 > th:
            raise ValueError(f'{name}: PHY footprint/origin does not fit with its real halo')
        before = dict(clock=copy.deepcopy(t.get('clock', {})), reset=copy.deepcopy(t.get('reset', {})),
                      contents=copy.deepcopy(contents))
        c.update(origin_um=list(origin), outline_um=[w,h], orient='R0', lef=str(VIEW),
                 lib=str(VIEW.with_name(MODULE+'_tt.lib')))
        def projected(pin):
            return [round(a+b, 6) for a,b in zip(origin, contract['pins'][pin]['center_um'])]
        t.setdefault('clock', {})['tap_um'] = projected('clk')
        t.setdefault('reset', {})['tap_um'] = projected('rst_n')
        changed.append(dict(type=name, macro_origin_um=list(origin), lef=str(VIEW),
                            clock_um=projected('clk'), reset_um=projected('rst_n'),
                            native=contract, before=before, added_registers=0,
                            added_boot_stages=0, added_data_cycles=0))
    if len(changed) != 1:
        raise ValueError(f'expected one native HBM PHY type, found {len(changed)}')
    return changed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--report',type=Path)
    a=p.parse_args();raw=json.loads(a.plan.read_text());report=apply(raw,a.repo)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(raw,indent=1)+'\n')
    if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
