#!/usr/bin/env python3
"""Materialize an existing clock topology using PG-aware fixed-wire planning.

No GRT guide is consumed. Inputs are the existing clock netlist, exact cell sites,
real LEF pin metal, die PG grid and the prepared source's endpoint ITerm map.
This is a die-local adapter around existing fixed-wire geometry/encoder APIs.
"""
import argparse
from collections import Counter, defaultdict
import contextlib
import hashlib
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools/die_plan'))
import clock_routed as CR
import die_clock_128 as C128
import die_clock_mesh as DCM
import die_infra as DI


def lef_access(text, master):
    match = re.search(r'(?ms)^MACRO\s+'+re.escape(master)+r'\s*\n(.*?)^END\s+'+re.escape(master)+r'\s*$', text)
    if not match:
        raise ValueError(f'LEF macro absent: {master}')
    body = match[1]
    size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
    access = {}
    for pin in ('A', 'Y'):
        pm = re.search(r'(?ms)^\s*PIN\s+'+pin+r'\s*\n(.*?)^\s*END\s+'+pin+r'\s*$', body)
        if not pm:
            raise ValueError(f'{master}/{pin} absent')
        layers = re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\Z)', pm[1], re.S)
        rects = [tuple(map(float, r)) for layer, contents in layers if layer == 'M1'
                 for r in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', contents)]
        # Choose an actual vertical M1 bar, keeping A/Y on distinct escape rows.
        bars = [r for r in rects if r[3]-r[1] > r[2]-r[0] and r[2]-r[0] >= .0179]
        target_y = .09 if pin == 'A' else .18
        bars = [r for r in bars if r[1]+.008 <= target_y <= r[3]-.008]
        if not bars:
            raise ValueError(f'no legal M1 access bar for {master}/{pin}')
        chosen = min(bars, key=lambda r:r[0]) if pin == 'A' else max(bars, key=lambda r:r[2])
        access[pin] = ((chosen[0]+chosen[2])/2, target_y)
    return tuple(map(float, size.groups())), access


def clock_graph(text, tree):
    cells, driven, loads = {}, {}, defaultdict(list)
    pattern = r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);'
    for master, name, pins in re.findall(pattern, text):
        pp = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pins))
        if set(pp) != {'A', 'Y'}:
            raise ValueError(f'clock cell is not an A/Y primitive: {name}')
        key = name[3:] if name.startswith('ck_') else name
        xy = tree['sites'].get(key)
        if xy is None:
            raise ValueError(f'no exact physical site: {name}')
        cells[name] = dict(x=xy[0], y=xy[1], lib=master, orient='R0')
        if pp['Y'] in driven:
            raise ValueError(f'multiple clock drivers: {pp["Y"]}')
        driven[pp['Y']] = name
        loads[pp['A']].append(name)
    if not cells:
        raise ValueError('no clock primitives parsed')
    aliases = dict(re.findall(r'(?m)^\s*assign\s+(\w+)\s*=\s*(\w+)\s*;', text))
    tap_ports = {t['port'] for t in tree['taps']}
    if set(aliases) != tap_ports:
        raise ValueError('clock output aliases do not match the exact tree taps')
    for port, net in aliases.items():
        loads[net].append('port:'+port)
    driven['root'] = 'port:root'
    if set(loads) != set(driven):
        raise ValueError(f'undriven/dead nets: {sorted(set(loads)^set(driven))}')
    nets = [dict(name=name, drv=drv, loads=loads[name]) for name, drv in driven.items()]
    return cells, nets


@contextlib.contextmanager
def real_pin_access(access):
    old = dict(CR.PIN_ACCESS)
    original_join = CR._port_join
    def adjacent_join(*args, **kwargs):
        pts = original_join(*args, **kwargs)
        out = [pts[0]]
        for point in pts[1:]:
            prev = out[-1]
            if point[0] != prev[0]:
                assert point[1:] == prev[1:]
                a, b = int(prev[0][1:]), int(point[0][1:])
                step = 1 if b > a else -1
                out.extend((f'M{i}', *point[1:]) for i in range(a+step, b, step))
            out.append(point)
        return out
    try:
        CR.PIN_ACCESS.update(access)
        CR._port_join = adjacent_join
        yield
    finally:
        CR.PIN_ACCESS.clear()
        CR.PIN_ACCESS.update(old)
        CR._port_join = original_join


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('tree', 'netlist', 'lef', 'plan', 'endpoints', 'out'):
        ap.add_argument('--'+key, required=True)
    ap.add_argument('--max-move', type=float, default=8.64)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tree = json.loads(Path(args.tree).read_text())
    raw_endpoints = json.loads(Path(args.endpoints).read_text())
    endpoints = raw_endpoints.get('endpoints', raw_endpoints)
    endpoints = {k:dict(v,xy=v.get('xy_um',v.get('xy'))) for k,v in endpoints.items()}
    cells, nets = clock_graph(Path(args.netlist).read_text(), tree)
    if set(endpoints) != {t['port'] for t in tree['taps']}:
        raise ValueError('endpoint map does not cover every tree tap exactly')
    lef = Path(args.lef).read_text()
    masters = {c['lib'] for c in cells.values()}
    sizes, access = {}, {}
    for master in masters:
        sizes[master], access[master] = lef_access(lef, master)
    for c in cells.values():
        c['w'] = sizes[c['lib']][0]
        if abs(c['x']/.054-round(c['x']/.054)) > 1e-5 or abs(c['y']/.27-round(c['y']/.27)) > 1e-5:
            raise ValueError(f'off-grid existing cell: {c}')
    P = DI.load_plan(args.plan)
    root = tree['nodes']['0']
    taps = []
    for tap in tree['taps']:
        ep = endpoints[tap['port']]
        if ep['inst'] != tap['part'] or ep['pin'] != tap['tap'] or ep['layer'] != 'M7':
            raise ValueError(f'endpoint identity/layer mismatch: {tap["port"]}')
        if max(abs(a-b) for a,b in zip(ep['xy'], tap['xy'])) > .001:
            raise ValueError(f'endpoint coordinate mismatch: {tap["port"]}')
        taps.append(dict(tap, layer=ep['layer']))
    M = dict(meta=dict(root_um=[root['x'],root['y']]), taps=taps)
    ports = {t['port']:dict(layer=t['layer'],xy=t['xy']) for t in taps}
    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])
    nd = dict(width=.08, space=.32, rf=.5, cf=1.15)
    pg = DI.pg_rects(P, C128.pg_grid(P))
    router = C128.TrackRouter(nd,'VSS',DCM.DEFAULT_TRACKS,args.max_move)
    router.reserve(C128.pg_shapes(pg))
    summary = dict(status='PREBUILD', physical_route=False, source_cells=len(cells), source_nets=len(nets),
                   tap_iterms=len(taps), source_masters=sorted(masters), pin_access=access,
                   inputs={k:dict(path=getattr(args,k),sha256=hashlib.sha256(Path(getattr(args,k)).read_bytes()).hexdigest())
                           for k in ('tree','netlist','lef','plan','endpoints')})
    try:
        wires = C128.fixed_wires(M,cells,nets,max(v[0] for v in sizes.values()),.27,router=router,pin_stack=False)
    except C128.PlanError as error:
        summary.update(status='FAIL', cause='no legal fixed-wire geometry', findings=error.rows)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise
    with real_pin_access(access):
        shapes = CR.stair_shapes(wires,cells,ports,next(iter(masters)))
        census = CR.stair_census(shapes)
        lines, rec = CR.routed_tcl(wires,cells,ports,next(iter(masters)),'QC_CLOCK_NDR')
    if census.get('shorts'):
        summary.update(status='FAIL',cause='pin-access shorts',pin_access_census=census)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise ValueError('fixed-wire pin stacks short; revise before materializing')
    text = '\n'.join(lines)+'\n'
    for port, ep in endpoints.items():
        old = '$e addBTerm [BT '+port+']'
        replacement = '$e addITerm [IT '+ep['inst']+' '+ep['pin']+']'
        if text.count(old) != 1:
            raise ValueError(f'endpoint encoder count is not one: {port}')
        text = text.replace(old,replacement)
    header = 'set blk [ord::get_db_block]\nset tech [[ord::get_db] getTech]\ncreate_ndr -name QC_CLOCK_NDR -width {M8 .08 M9 .08} -spacing {M8 .32 M9 .32}\n'
    (out/'fixed_clock.tcl').write_text(header+text)
    (out/'fixed_wires.json').write_text(json.dumps(wires)+'\n')
    (out/'infra_nets.txt').write_text('\n'.join(n['name'] for n in nets)+'\n')
    summary.update(status='PASS_PREBUILD',encoder=rec,pin_access_census=census,
                   note='No physical job or route proof. Render/review before source materialization. PG wires must exist separately.')
    (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('inputs','pin_access_census')},indent=1))


if __name__ == '__main__':
    main()
