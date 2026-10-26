#!/usr/bin/env python3
"""KV-P7 10-23: carve a KV attention die-slice VEHICLE out of the GENERATED KV bound top (tools/die_plan/bind.py output).

Generalises TOKh's QC bound_carve.py.  Keeps the SEED partition instances of qwen_kvsys_bound_top byte-for-byte (straps
and parameters included) plus every TRANSIT partition that a lane between two kept partitions passes through (closure,
by the '// lane L<n>' tags of the top wires).  Every top wire a kept partition reads but no kept partition drives becomes
a carve INPUT port (bench model / driver), every wire a kept partition drives that no kept partition reads becomes a carve
OUTPUT port (observable).  Ports keep the bound wire names; carve.json lists each boundary port with its lane, width,
direction and the far-end partition (= which model must drive / observe it: phy_* = HBM PC model, hub_Wi/sys_c = host /
d2d / boot, pv_N_* / hroot_*N = the other PV pair).  All partition clocks are kept as separate inputs (bench may tie them).

    kv_bound_carve.py --top qwen_kvsys_bound_top.sv --rtl RTLDIR --seed REGEX --name NAME --out DIR
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path

INST = re.compile(r'^\s*(\w+)\s*(#\(.*\))?\s+(\w+)\s*\($')
CONN = re.compile(r'^\s*\.(\w+)\(([^()]*)\),?$')
WIRE = re.compile(r'^\s*wire\s*(\[(\d+):(\d+)\])?\s*(\w+)\s*;\s*(//\s*lane\s+(\S+))?')
PORT = re.compile(r'^\s*(input|output)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)')
TOPIN = re.compile(r'^\s*input\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)\s*;')


def parse_top(p):
    wires, insts, cur, tin = {}, [], None, {}
    for ln in p.read_text().splitlines():
        if cur is not None:
            m = CONN.match(ln)
            if m:
                cur['conns'].append((m.group(1), m.group(2).strip())); cur['text'].append(ln); continue
            if ln.strip() == ');':
                cur['text'].append(ln); insts.append(cur); cur = None; continue
            raise SystemExit(f'unparsed instance line: {ln[:200]}')
        m = TOPIN.match(ln)
        if m:
            tin[m.group(4)] = dict(width=int(m.group(2)) - int(m.group(3)) + 1 if m.group(1) else 1); continue
        m = WIRE.match(ln)
        if m:
            wires[m.group(4)] = dict(width=int(m.group(2)) - int(m.group(3)) + 1 if m.group(1) else 1,
                                     lane=m.group(6), decl=ln); continue
        m = INST.match(ln)
        if m and m.group(1) != 'module':
            cur = dict(module=m.group(1), name=m.group(3), conns=[], text=[ln])
    return wires, insts, tin


def port_dirs(rtl, module, cache={}):
    if module not in cache:
        f = rtl / f'{module}.sv'
        d = {}
        if f.exists():
            for ln in f.read_text().splitlines():
                m = PORT.match(ln)
                if m:
                    d[m.group(5)] = m.group(1)
                if ln.startswith(');'):
                    break
        cache[module] = d
    return cache[module]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', required=True, type=Path); ap.add_argument('--rtl', required=True, type=Path)
    ap.add_argument('--seed', required=True); ap.add_argument('--name', required=True)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--no-transit', action='store_true')
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    wires, insts, tin = parse_top(a.top)
    byname = {i['name']: i for i in insts}
    seeds = {n for n in byname if re.fullmatch(a.seed, n)}
    # lane -> partitions touching it
    lane_parts = defaultdict(set)
    for i in insts:
        for _, n in i['conns']:
            if n in wires and wires[n]['lane']:
                lane_parts[wires[n]['lane']].add(i['name'])
    keep = set(seeds); transit = defaultdict(int)
    if not a.no_transit:
        changed = True
        while changed:
            changed = False
            for lane, ps in lane_parts.items():
                if len(ps & keep) >= 2 and not ps <= keep:
                    # transit only if the lane's endpoints are both kept: a lane leaving the vehicle is a boundary
                    pass
            # endpoint-based closure: lane src = partition that drives its first wire, dst = reader of its last wire
        # endpoint rule (cheap): a non-seed partition is transit if every lane it carries for the seeds connects 2 seeds
        for lane, ps in lane_parts.items():
            if len(ps & seeds) >= 2:
                for q in ps - seeds:
                    transit[q] += 1
        keep |= set(transit)
    drv, rd = defaultdict(list), defaultdict(list)
    for n in sorted(keep):
        i = byname[n]; pd = port_dirs(a.rtl, i['module'])
        for p, w in i['conns']:
            if not w or w.startswith("'") or re.match(r"^\d", w):
                continue
            d = pd.get(p)
            if d is None:
                raise SystemExit(f'no direction for {n}.{p} ({i["module"]})')
            (drv if d == 'output' else rd)[w].append((n, p))
    other_drv, other_rd = defaultdict(list), defaultdict(list)
    for i in insts:
        if i['name'] in keep:
            continue
        pd = port_dirs(a.rtl, i['module'])
        for p, w in i['conns']:
            if w in rd or w in drv:
                (other_drv if pd.get(p) == 'output' else other_rd)[w].append(i['name'])
    ins = sorted(w for w in rd if w not in drv)
    outs = sorted(w for w in drv if w not in rd and other_rd.get(w))
    internal = sorted((set(drv) | set(rd)) - set(ins) - set(outs))
    hdr, body = [], []
    for w in ins:
        width = (wires.get(w) or tin.get(w))['width']
        hdr.append(f'    input wire [{width - 1}:0] {w}')
    for w in outs:
        hdr.append(f'    output wire [{wires[w]["width"] - 1}:0] {w}')
    L = [f'// GENERATED by kv_bound_carve.py (KV-P7 10-23) from {a.top}', f'// seeds /{a.seed}/ ({len(seeds)}), transit {sorted(transit)}',
         '`timescale 1ns/1ps', f'module {a.name} (', ',\n'.join(hdr), ');']
    for w in internal:
        if w in wires:
            L.append(wires[w]['decl'])
    for n in sorted(keep):
        L += byname[n]['text']
    L.append('endmodule')
    (a.out / f'{a.name}.v').write_text('\n'.join(L) + '\n')
    far = defaultdict(lambda: defaultdict(int)); bound = []
    for w in ins:
        src = other_drv.get(w) or ['TOP_INPUT']
        lane = wires[w]['lane'] if w in wires else None
        bound.append(dict(net=w, dir='in', lane=lane, width=(wires.get(w) or tin.get(w))['width'], far=src, readers=rd[w]))
        far[src[0]]['in'] += bound[-1]['width']
    for w in outs:
        bound.append(dict(net=w, dir='out', lane=wires[w]['lane'], width=wires[w]['width'], far=sorted(set(other_rd[w])), drivers=drv[w]))
        far[bound[-1]['far'][0]]['out'] += wires[w]['width']
    rep = dict(top=str(a.top), name=a.name, seed=a.seed, seeds=sorted(seeds), transit=dict(transit), kept=len(keep),
               modules=sorted({byname[n]['module'] for n in keep}), boundary_by_far_end={k: dict(v) for k, v in sorted(far.items())},
               boundary=bound)
    (a.out / 'carve.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(f'{a.name}: kept {len(keep)} ({len(seeds)} seeds + transit {sorted(transit)}), {len(ins)} in / {len(outs)} out ports, '
          f'{len(internal)} internal nets')
    for k, v in sorted(far.items(), key=lambda x: -sum(x[1].values()))[:25]:
        print(f'  far {k}: {dict(v)}')


if __name__ == '__main__':
    main()
