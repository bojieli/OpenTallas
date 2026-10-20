#!/usr/bin/env python3
"""S81-BF6: classify native-census violations on a yosys 'rename -wire' mapped netlist.

usage: classify.py mapped.v census.json [out.json]
For each violation: driver cell name/type, (comb) the named flops / ports in its fan-in cone (<= 8 levels), and a sample
of the named flops it reaches (<= 4 levels), grouped by a name stem (indices stripped)."""
import json, re, sys, collections

SEQ = re.compile(r'^(DFF|DHL|DLL|SDF|ASYNC|ICG)')
inst_re = re.compile(r'^\s*(\S+)\s+(\\\S+|\S+)\s*\(\s*$')
pin_re = re.compile(r'^\s*\.(\w+)\((.*)\)\s*,?\s*$')
assign_re = re.compile(r'^\s*assign\s+(.+?)\s*=\s*(.+?)\s*;\s*$')


def norm(n):
    n = n.strip()
    if n.startswith('\\'):
        parts = n.split()
        n = parts[0][1:] + (parts[1] if len(parts) > 1 else '')
    return n.replace(' ', '')


def parse(path):
    cells = {}      # name -> (type, {pin: net})
    alias = {}
    cur = None
    for line in open(path):
        if cur is None:
            m = inst_re.match(line)
            if m and m.group(1) not in ('module', 'input', 'output', 'wire', 'assign', 'inout', 'reg'):
                cur = (m.group(1), norm(m.group(2)), {})
                continue
            m = assign_re.match(line)
            if m:
                alias[norm(m.group(1))] = norm(m.group(2))
        else:
            m = pin_re.match(line)
            if m:
                cur[2][m.group(1)] = norm(m.group(2))
            if line.strip().startswith(');'):
                cells[cur[1]] = (cur[0], cur[2])
                cur = None
    return cells, alias


def main():
    cells, alias = parse(sys.argv[1])
    cen = json.load(open(sys.argv[2]))
    outpins = {'Y', 'QN', 'Q', 'CON', 'SN', 'GCLK'}

    def canon(n):
        seen = 0
        while n in alias and seen < 20:
            n = alias[n]; seen += 1
        return n
    drv, loads = {}, collections.defaultdict(list)
    for name, (typ, pins) in cells.items():
        for p, n in pins.items():
            n = canon(n)
            if p in outpins:
                drv[n] = (name, typ)
            else:
                loads[n].append((name, typ, p))
    # names for nets: every alias target named with a non-anonymous name
    netname = collections.defaultdict(set)
    for a, b in alias.items():
        if not a.startswith('_'):
            netname[canon(b)].add(a)

    def label(cellname, typ):
        return cellname if not cellname.startswith('_') else typ

    def fanin(net, depth=8):
        out, todo, seen = set(), [(net, 0)], set()
        while todo:
            n, d = todo.pop()
            if n in seen: continue
            seen.add(n)
            if n not in drv:
                out.add('PORT/' + (sorted(netname[n])[0] if netname[n] else n)); continue
            c, t = drv[n]
            if SEQ.match(t) or d >= depth:
                out.add(('FF/' if SEQ.match(t) else 'DEEP/') + (c if not c.startswith('_') else (sorted(netname[n])[0] if netname[n] else c)))
                continue
            for p, m in cells[c][1].items():
                if p not in outpins: todo.append((canon(m), d + 1))
        return out

    def fanout(net, depth=4, cap=4000):
        out, todo, seen = collections.Counter(), [(net, 0)], set()
        while todo and len(seen) < cap:
            n, d = todo.pop()
            if n in seen: continue
            seen.add(n)
            for c, t, p in loads.get(n, []):
                if SEQ.match(t):
                    out[(c if not c.startswith('_') else t) + '.' + p] += 1
                elif d < depth:
                    for q, m in cells[c][1].items():
                        if q in outpins: todo.append((canon(m), d + 1))
        return out

    stem = lambda s: re.sub(r'\[\d+\]', '[]', re.sub(r'_\d+_', '_', s))
    res = []
    for v in sorted(cen['violations'], key=lambda x: -x['loads']):
        net = canon(v['net'])
        dc = v['driver'].rsplit('/', 1)[0]
        fi = sorted(fanin(net)) if v['driver_role'] != 'sequential' else []
        fo = fanout(net)
        fos = collections.Counter()
        for k, n in fo.items(): fos[stem(k)] += n
        res.append({'loads': v['loads'], 'driver': v['driver'], 'role': v['driver_role'],
                    'net_names': sorted(netname[net])[:4], 'fanin': [stem(x) for x in fi][:12],
                    'fanout_stems': fos.most_common(6)})
    out = sys.argv[3] if len(sys.argv) > 3 else None
    if out: json.dump(res, open(out, 'w'), indent=1)
    grp = collections.defaultdict(list)
    for r in res:
        key = (stem(r['driver']) if r['role'] == 'sequential' else 'comb<-' + ','.join(sorted(set(r['fanin']))[:3]))
        grp[key].append(r)
    for k, rs in sorted(grp.items(), key=lambda kv: -max(r['loads'] for r in kv[1])):
        r0 = max(rs, key=lambda r: r['loads'])
        print(f"{len(rs):4d} x max {r0['loads']:5d}  {k[:150]}\n        names={r0['net_names'][:2]} fo={r0['fanout_stems'][:3]}")


if __name__ == '__main__':
    main()
