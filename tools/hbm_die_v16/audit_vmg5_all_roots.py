#!/usr/bin/env python3
"""Read-only uncapped audit of already mapped g5 artifacts; never synthesize."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

base, out = map(Path, sys.argv[1:3])
spec = importlib.util.spec_from_file_location('textbook', Path(__file__).parents[1] / 'textbook_lint.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
out.mkdir(parents=True, exist_ok=True)
for quad in ('sw', 'e', 'nw'):
    run = base / f'hfd_hgi_vms_glue_{quad}_g5-20261019-121352'
    work = run / 'routes/gate/work/orfs'
    net = work / '1_2_yosys.raw.v'
    dump = work / 'gate_dump.json'
    g, top = t.flatten(t.parse_verilog(net.read_text()), f'hfd_hgi_vms_glue_{quad}_t')
    a = t.build(g, json.loads(dump.read_text()))
    clocks, _ = t.clock_nets(g, a)
    roots = []
    for x, (ci, pin) in a['driver'].items():
        if x in clocks or (ci >= 0 and a['kind'][ci] == 'buf'):
            continue
        seen, stack, sinks = {x}, [x], set()
        while stack:
            y = stack.pop()
            for lc, lp, bit in a['loads'].get(y, ()):
                if a['kind'][lc] == 'buf':
                    for z in t._out_nets(g, a, lc):
                        if z not in seen:
                            seen.add(z)
                            stack.append(z)
                else:
                    sinks.add((lc, lp, bit))
        ports = sorted({p for y in seen for p in a['out_ports'].get(y, ())})
        roles = collections.Counter(a['kind'][lc] + ':' + lp for lc, lp, _ in sinks)
        roots.append(dict(net=g.net_name[x], driver=t.net_label(g, a, x),
                          kind='input' if ci < 0 else a['kind'][ci],
                          loads=len(sinks)+len(ports), sink_roles=dict(roles), output_ports=ports,
                          sinks=[dict(cell=g.cells[lc][1], master=g.cells[lc][0], pin=lp, bit=b)
                                 for lc, lp, b in sorted(sinks)]))
    roots.sort(key=lambda r: (-r['loads'], r['driver']))
    summary = dict(top=top, mapped_source=str(net),
                   mapped_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),
                   dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),
                   cells=len(g.cells), kinds=dict(collections.Counter(a['kind'])), roots=len(roots),
                   roots_gt32=sum(r['loads'] > 32 for r in roots),
                   roots_gt32_by_kind=dict(collections.Counter(r['kind'] for r in roots if r['loads'] > 32)),
                   max_by_kind={k:max((r['loads'] for r in roots if r['kind']==k), default=0)
                                for k in ('input','ff','comb','macro','tie')},
                   top_roots=[{k:v for k,v in r.items() if k!='sinks'} for r in roots[:30]],
                   unknown_masters=sorted({g.cells[i][0] for i,k in enumerate(a['kind']) if k=='macro'}),
                   scope='mapped graph; no placement reach or physical clock qualification')
    (out / f'{quad}_all_roots.json').write_text(json.dumps(roots, indent=1)+'\n')
    (out / f'{quad}_summary.json').write_text(json.dumps(summary, indent=1)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('top_roots','mapped_source')}), flush=True)
