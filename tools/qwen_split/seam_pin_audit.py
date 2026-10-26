#!/usr/bin/env python3
"""Audit the SU/VM seam from emitted LEF pins, not projected block centroids.

This is a source-geometry audit: it never grants layer ownership, native timing,
GRT closure, a cut omission, or occupancy over unexamined nets.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

LAYERS = {'M5': (.012, .048), 'M7': (.016, .064)}


def pins(text, master):
    body = text.split('MACRO ' + master + '\n', 1)[1].split('END ' + master + '\n', 1)[0]
    result = {}
    for name, block in re.findall(r'^  PIN (\S+)\n(.*?)^  END \1$', body, re.M | re.S):
        layer = re.search(r'\bLAYER (\S+)\s*;', block)
        rect = re.search(r'\bRECT ([\d.eE+-]+) ([\d.eE+-]+) ([\d.eE+-]+) ([\d.eE+-]+)\s*;', block)
        if layer and rect:
            x0, y0, x1, y1 = map(float, rect.groups())
            result[name] = (layer[1], (x0+x1)/2, (y0+y1)/2)
    return result


def audit(lef, graph, place, netlist, mutant=False):
    data = json.loads(graph.read_text())
    insts = {x['n']: x for x in data['insts']}
    sn, vn = 'sp_su64_sfu', 'sp_vector_memory'
    su, vm = insts[sn], insts[vn]
    locations = {n: (float(x), float(y), o) for n, x, y, o in re.findall(
        r'ot_mts::place \[\$_blk findInst (\S+)\] (\S+) (\S+) (\S+)', place.read_text())}
    problems = []
    connections = {}
    for name in (sn, vn):
        line = next(line for line in netlist.read_text().splitlines() if re.match(r'  \w+ '+name+r' \(',line))
        connections[name] = dict(re.findall(r'\.(\w+)\(([^()]*)\)',line))
    for a,b in (('va','sa'),('vq','sq')):
        if re.sub(r'\s+', '', connections[sn][a]) != re.sub(r'\s+', '', connections[vn][b]):
            problems.append(f'netlist order/connectivity mismatch {a}/{b}')
    for name in (sn, vn):
        if name not in locations or locations[name][2] != 'R0':
            raise ValueError('seam audit currently supports explicit R0 placement only: '+name)
        if any(abs(a-b) > .001 for a,b in zip(locations[name][:2], (insts[name]['x'],insts[name]['y']))):
            raise ValueError('graph/placement mismatch: '+name)
    text = lef.read_text()
    sp, vp = pins(text, su['m']), pins(text, vm['m'])
    if mutant:
        layer,x,y=vp['sa[0]']; vp['sa[0]']=(layer,x+.096,y)
    rows, occupied = [], {}
    counts = collections.Counter()
    for a,b,width in (('va','sa',2367),('vq','sq',6144)):
        for k in range(width):
            an, bn = f'{a}[{k}]', f'{b}[{k}]'
            if an not in sp or bn not in vp:
                problems.append(f'missing pin {an}/{bn}'); continue
            sl,x,y=sp[an]; vl,u,v=vp[bn]
            x,y,u,v=x+su['x'],y+su['y'],u+vm['x'],v+vm['y']
            if sl != vl or sl not in LAYERS or abs(x-u) > .0002:
                problems.append(f'pair {an}/{bn} layer/x mismatch {sl}/{vl} {x}/{u}'); continue
            # Both emitted face rectangles must touch the correct physical boundary.
            if not (su['y'] <= y <= su['y']+.2 and vm['y']+vm['h']-.2 <= v <= vm['y']+vm['h']):
                problems.append(f'pair {an}/{bn} not on facing boundaries'); continue
            offset,pitch=LAYERS[sl]; track=round((x-offset)/pitch)
            if abs(x-(offset+pitch*track))>.0002:
                problems.append(f'{an}: global off-track {sl} x{x}'); continue
            key=(sl,track)
            if key in occupied:
                problems.append(f'seam track collision {an} / {occupied[key]}'); continue
            occupied[key]=an
            # Reject any third instance body intersecting the proposed short straight wire.
            for name,i in insts.items():
                if name in (sn,vn): continue
                if i['x'] < x < i['x']+i['w'] and max(min(y,v),i['y']) < min(max(y,v),i['y']+i['h']):
                    problems.append(f'{an}: proposed track intersects {name}')
            counts[sl]+=1
            rows.append((sl,round(x,4),round(abs(y-v),4),an,bn))
    windows=[]
    if rows:
        for start in range(int(min(r[1] for r in rows))-260,int(max(r[1] for r in rows))+1,10):
            use=collections.Counter(r[0] for r in rows if start<=r[1]<start+260)
            windows.append(dict(x_um=[start,start+260],bits=sum(use.values()),layers=dict(use)))
    return dict(schema='opentallas.qwen.seam_pin_audit.v1',qualification=False,
        basis='emitted LEF and exact explicit R0 placement; raw source track occupancy only',
        inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (lef,graph,place,netlist)},
        mutant=mutant,pairs_expected=8511,pairs_verified=len(rows),layers=dict(counts),
        source_geometry_pass=not problems and len(rows)==8511,problems=problems[:50],problem_count=len(problems),
        max_pair_length_um=max((r[2] for r in rows),default=None),
        pair_table_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),
        worst_260um_window=max(windows,key=lambda w:w['bits'],default=None),
        exceptions=['sq[0:2047] also feeds seq_su: extra branch remains unexamined',
                    'PDN and other routed signal occupancy not proved; no cut omission is authorized',
                    'unclosed diagnostic pin plans are not native physical views'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lef',type=Path,required=True);p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--place',type=Path,required=True);p.add_argument('--netlist',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mutant',action='store_true');a=p.parse_args()
    d=audit(a.lef,a.graph,a.place,a.netlist,a.mutant);a.out.write_text(json.dumps(d,indent=1)+'\n')
    print(json.dumps({k:d[k] for k in ('source_geometry_pass','pairs_verified','problem_count','max_pair_length_um','worst_260um_window')}))
    raise SystemExit(0 if d['source_geometry_pass'] else 1)

if __name__=='__main__':main()
