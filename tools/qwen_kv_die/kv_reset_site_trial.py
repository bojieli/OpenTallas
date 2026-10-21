#!/usr/bin/env python3
"""Read-only one-endpoint reset transport/two-capture site trial, not a die repair.

Uses exact final macro envelopes and actual qkd_rlys_1 pin offsets. Writes only a
plan report. No placement/netlist is edited, and no root or reset is substituted.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import kv_child_rst as C


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--inventory', type=Path, required=True)
    ap.add_argument('--endpoint', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--preview-prefix', type=Path,
                    help='write review-only unified netlist/placement diffs; never apply them')
    a = ap.parse_args()
    inv = json.loads(a.inventory.read_text())
    for name in ('die.v', 'place.tcl', 'elements.lef', 'manifest.json'):
        if hashlib.sha256((a.case / name).read_bytes()).hexdigest() != inv['source_sha256'][name]:
            raise ValueError('source mismatch: ' + name)
    rows = [r for r in inv['long_pairs'] if r['id'].split('->')[1] == a.endpoint]
    if len(rows) != 1:
        raise ValueError('endpoint must have exactly one inventoried source')
    row = rows[0]
    die_w, die_h = json.loads((a.case/'manifest.json').read_text())['die_um']
    lef = (a.case / 'elements.lef').read_text()
    sizes = {}
    pinxy = {}
    allpinxy = {}
    macro = pin = None
    for line in lef.splitlines():
        s = line.strip().split()
        if not s:
            continue
        if s[0] == 'MACRO':
            macro = s[1]
        elif s[0] == 'SIZE':
            sizes[macro] = float(s[1]), float(s[3])
        elif s[0] == 'PIN':
            pin = s[1]
        elif s[0] == 'RECT' and pin and (macro == 'qkd_rlys_1' or macro == row['master']):
            pt = ((float(s[1])+float(s[3]))/2, (float(s[2])+float(s[4]))/2)
            basepin = pin.split('[')[0]
            allpinxy.setdefault((macro, basepin), []).append(pt)
            if macro == 'qkd_rlys_1' and basepin in ('a', 'b'):
                pinxy.setdefault(basepin, pt)
        elif s[0] == 'END' and len(s) > 1 and s[1] == pin:
            pin = None
    if sizes.get('qkd_rlys_1') != (C.STN, C.STN) or set(pinxy) != {'a', 'b'}:
        raise ValueError('actual closed reset relay dimensions/pins unresolved')
    masters = dict((m[1], m[0]) for m in re.findall(r'^\s+(\w+) (\S+) \(.*\);\s*$', (a.case/'die.v').read_text(), re.M))
    poses = re.findall(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', (a.case/'place.tcl').read_text())
    pos = {n: (float(x),float(y),o) for n,x,y,o in poses}

    def final_points(instance, port):
        mst = masters[instance]
        x,y,o = pos[instance]
        w,h = sizes[mst]
        if o not in ('R0','MY','MX','R180'):
            raise ValueError('unsupported final pin orientation: ' + o)
        return [(x+(w-px if o in ('MY','R180') else px),
                 y+(h-py if o in ('MX','R180') else py))
                for px,py in allpinxy[(mst,port)]]
    obstacles = []
    for n, x, y, orient in poses:
        if n not in masters or masters[n] not in sizes:
            raise ValueError('unresolved final macro envelope: ' + n)
        w, h = sizes[masters[n]]
        if orient in ('R90', 'R270', 'MXR90', 'MYR90'):
            w, h = h, w
        x, y = float(x), float(y)
        obstacles.append((x-C.HALO, y-C.HALO, x+w+C.HALO, y+h+C.HALO))
    source, target = row['pts']
    source_instance, source_port = row['id'].split('->')[0].rsplit('/',1)
    sink_instance, sink_port = a.endpoint.rsplit('/',1)
    if masters[source_instance] != 'qkd_rlys_1':
        raise ValueError('trial currently requires an actual qkd_rlys_1 source')
    original_source_points = final_points(source_instance, source_port)
    final_target_points = final_points(sink_instance, sink_port)
    report = dict(status='MODEL_ONLY_UNQUALIFIED', source_sha256=inv['source_sha256'],
                  endpoint=row, original_obstacles=len(obstacles), stations=[],
                  note='No netlist, placement, root, or calendar modified')
    try:
        # Reserve both local captures first, then transport to capture one's
        # actual a pin. The second capture's b pin must reach the final load.
        local = (max(0, target[0]-240), max(0, target[1]-240), min(die_w,target[0]+240), min(die_h,target[1]+240))
        free = C.Free(local, obstacles)
        caps = []
        for i in (2, 1):
            spots = free.spots()
            if not len(spots):
                raise ValueError('no legal receiver-local capture site')
            aim = target if i == 2 else (caps[0]['x']+pinxy['a'][0], caps[0]['y']+pinxy['a'][1])
            d = abs(spots[:, 0]+pinxy['b'][0]-aim[0])+abs(spots[:, 1]+pinxy['b'][1]-aim[1])
            j = int(d.argmin())
            if d[j] > 200:
                raise ValueError('local capture cannot reach its actual receiving pin')
            x, y = map(float, spots[j])
            caps.append(dict(name=f'reset_trial_capture{i}', x=x, y=y, ck=row['consumer_clock']))
            free.take(x, y)
            obstacles.append((x-C.HALO, y-C.HALO, x+C.STN+C.HALO, y+C.STN+C.HALO))
        cap1 = caps[1]
        goal = cap1['x']+pinxy['a'][0], cap1['y']+pinxy['a'][1]
        window = (max(0,min(source[0], goal[0])-240), max(0,min(source[1],goal[1])-240),
                  min(die_w,max(source[0],goal[0])+240), min(die_h,max(source[1],goal[1])+240))
        stations, assigned = C.plan('reset_trial_transport', window, obstacles,
            [('entry', goal)], source, lambda _: row['consumer_clock'])
        byname = {s['name']: s for s in stations}
        leaf = assigned['entry']
        cap1['parent'] = leaf
        caps[0]['parent'] = cap1['name']
        allsites = stations + caps
        byname.update({s['name']: s for s in caps})
        spans = []
        for s in allsites:
            p = byname.get(s.get('parent'))
            starts = original_source_points if p is None else [(p['x']+px,p['y']+py) for px,py in allpinxy[('qkd_rlys_1','b')]]
            ends = [(s['x']+px,s['y']+py) for px,py in allpinxy[('qkd_rlys_1','a')]]
            spans.append(max(abs(start[0]-end[0])+abs(start[1]-end[1]) for start in starts for end in ends))
        spans.append(max(abs(caps[0]['x']+px-tx)+abs(caps[0]['y']+py-ty)
                         for px,py in allpinxy[('qkd_rlys_1','b')] for tx,ty in final_target_points))
        if max(spans) > 405 or any(s.get('far') for s in stations):
            raise ValueError('actual-pin reach or far-site fallback refuses site trial')
        report.update(site_trial='PASS_GEOMETRY_ONLY', stations=allsites,
            max_actual_pin_span_um=max(spans), added_edges=byname[leaf]['depth']+2,
            capture_edges=2, transport_edges=byname[leaf]['depth'],
            pin_geometry='maximum over all LEF rectangle-centre pairs including exact oriented original driver and final receiver')
        if a.preview_prefix:
            # Review artifacts only. Never integrate a calendar-changing patch
            # into a chain until its source-bound compiler/protocol proof exists.
            original = (a.case/'die.v').read_text()
            lines = original.splitlines(keepends=True)
            instance_re = re.compile(r'^\s+\w+ '+re.escape(sink_instance)+r' \(')
            found = [i for i,line in enumerate(lines) if instance_re.match(line)]
            if len(found) != 1:
                raise ValueError('preview sink instance is not unique')
            if any(s['name'] in masters for s in allsites):
                raise ValueError('preview instance name collision')
            index = found[0]
            old = '.'+sink_port+'('+row['witness_net']+')'
            new = '.'+sink_port+'(n_'+caps[0]['name']+'[0])'
            if lines[index].count(old) != 1:
                raise ValueError('preview original source expression mismatch')
            lines[index] = lines[index].replace(old,new)
            wires = ''.join('  wire [0:0] n_'+s['name']+';\n' for s in allsites)
            cells = []
            for s in allsites:
                source_net = row['witness_net'] if s.get('parent') is None else 'n_'+s['parent']+'[0]'
                cells.append('  qkd_rlys_1 '+s['name']+' (.ck('+row['consumer_clock']+'), .a('+source_net+'), .b(n_'+s['name']+'[0]));\n')
            wi = max(i for i,line in enumerate(lines) if re.match(r'\s*wire\b',line))
            lines.insert(wi+1,wires)
            ei = max(i for i,line in enumerate(lines) if re.match(r'\s*endmodule\b',line))
            lines.insert(ei,''.join(cells))
            before = (a.case/'place.tcl').read_text()
            places = ''.join('ot_mts::place [$_blk findInst '+s['name']+'] '+f'{s["x"]:.3f} {s["y"]:.3f} R0\n' for s in allsites)
            plines = before.splitlines(keepends=True)
            pi = max(i for i,line in enumerate(plines) if 'ot_mts::place' in line)
            plines.insert(pi+1,places)
            for label,oldtext,newtext in [('die.v',original,''.join(lines)),('place.tcl',before,''.join(plines))]:
                patch = ''.join(difflib.unified_diff(oldtext.splitlines(keepends=True),newtext.splitlines(keepends=True),fromfile='a/'+label,tofile='b/'+label))
                Path(str(a.preview_prefix)+'.'+label+'.patch').write_text(patch)
            report['preview_status'] = 'REVIEW_ONLY_NOT_APPLIED_REQUIRES_RESET_CALENDAR_RECOMPILE'
    except ValueError as e:
        report.update(site_trial='REFUSED', reason=str(e))
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('endpoint','stations')}))
    return 0 if report['site_trial'] == 'PASS_GEOMETRY_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
