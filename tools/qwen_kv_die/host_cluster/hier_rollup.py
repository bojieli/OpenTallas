#!/usr/bin/env python3
"""KVJ-A3 (10-17): roll the hierarchical (non-flattened) mapped Yosys stat of qkd_host_root_admission up to every instance
of the census (clock_tree_census.py output): std cells, std area (um2, ASAP7 RVT TT), flops, macros per instance.
The hierarchical numbers are the per-child synthesis estimate (no cross-child optimisation); the flat synth of the same
root (host_root_synth_sram) is ~0.75x in area.

usage: hier_rollup.py hsyn_mapped.stat elab.json census.json out.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path


def parse(stat):
    mods, cur = {}, None
    for line in Path(stat).read_text().splitlines():
        m = re.match(r'^=== (.+) ===$', line)
        if m:
            cur = mods.setdefault(m.group(1), dict(cells=0, area=0.0, ff=0, sub=Counter(), macros=Counter()))
            insub = False
            continue
        if cur is None:
            continue
        m = re.match(r'^\s+(\d+)\s+(\S+)\s+cells$', line)
        if m:
            cur['cells'] = int(m.group(1))
            continue
        m = re.match(r'^\s+(\d+)\s+\S+\s+submodules$', line)
        if m:
            insub = True
            continue
        m = re.match(r'^\s+(\d+)\s+(\S+)\s+(\S+)$', line)
        if m and insub and m.group(2) in ('-',) or (m and insub and re.match(r'^[\d.E+-]+$', m.group(2))):
            cur['sub'][m.group(3)] += int(m.group(1))
            continue
        m = re.match(r'^\s+(\d+)\s+(\S+)\s+(\S+_ASAP7_75t_R|ot_sram\S+)$', line)
        if m:
            insub = False
            if m.group(3).startswith('ot_sram'):
                cur['macros'][m.group(3)] += int(m.group(1))
            elif m.group(3).startswith('DFF'):
                cur['ff'] += int(m.group(1))
            continue
        m = re.match(r"^\s+Chip area for module '(.+)': ([\d.]+)$", line)
        if m:
            cur['area'] = float(m.group(2))
    return mods


def main():
    stat, elab, census, out = sys.argv[1:5]
    mods = parse(stat)
    memo = {}

    def total(name):
        if name in memo:
            return memo[name]
        m = mods[name]
        t = dict(cells=m['cells'], area=m['area'], ff=m['ff'], macros=Counter(m['macros']))
        for s, n in m['sub'].items():
            if s.startswith('ot_sram'):
                t['macros'][s] += n
                continue
            if s not in mods:
                continue
            st = total(s)
            t['cells'] += n * st['cells']
            t['area'] += n * st['area']
            t['ff'] += n * st['ff']
            for k, v in st['macros'].items():
                t['macros'][k] += n * v
        memo[name] = t
        return t

    em = json.loads(Path(elab).read_text())['modules']
    cen = json.loads(Path(census).read_text())
    # instance path -> full (paramod) module name via the elaboration's cell types
    types = {'top': cen['top']}
    for n in cen['nodes']:
        mt = types.get(n['path'])
        if mt is None:
            continue
        for cn, c in em[mt]['cells'].items():
            if c['type'] in em:
                types[f"{n['path']}/{cn}"] = c['type']
    res = []
    for n in cen['nodes']:
        mt = types.get(n['path'])
        t = total(mt) if mt in mods else None
        res.append(dict(path=n['path'], module=n['module'], klass=n['klass'], families=n['families'], clocks=n['ff'],
                        mem_bits_behavioural=n['mem_bits'],
                        std_cells=t and t['cells'], std_area_um2=t and round(t['area'], 1), ff_mapped=t and t['ff'],
                        macros=t and dict(t['macros'])))
    Path(out).write_text(json.dumps(dict(top=cen['top'], source='hierarchical mapped synth (RVT TT), proc census',
                                         nodes=res), indent=1) + '\n')
    r = res[0]
    print(f"top cells {r['std_cells']} area {r['std_area_um2']} ff {r['ff_mapped']} macros {r['macros']}")


if __name__ == '__main__':
    main()
