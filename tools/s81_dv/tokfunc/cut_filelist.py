#!/usr/bin/env python3
"""cut_filelist.py CUT.f OUT.f ROOT... : close a cut file list over modules defined in non-eponymous files.
Indexes `module X` in every .sv/.v under the ROOTs (bind.f's own source trees), then adds, transitively, the file that
defines each instantiated module not defined by the list.  Ambiguous module names (several defining files) prefer a
file already in the list, then a file under the same tree as the instantiating file; the rest are reported."""
import re, sys
from collections import defaultdict
from pathlib import Path
ID = r'[A-Za-z_][A-Za-z0-9_$]*'
KW = set('module endmodule input output inout wire reg logic assign always initial if else for begin end case generate genvar integer localparam parameter function task return typedef struct enum'.split())
def strip(t):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', ' ', t, flags=re.S))
def defs(t): return set(re.findall(r'\bmodule\s+(' + ID + ')', t))
MAC = {}   # `define NAME <module id> (module names picked by macro, e.g. `OT_SH_M257)
def uses(t):
    mu = {MAC[n] for n in re.findall(r'`(' + ID + r')\s+' + ID + r'\s*\(', t) if n in MAC}
    return mu | {m for m in re.findall(r'(?:^|;|\bend\b|\bbegin\b|\)\s*)\s*(' + ID + r')\s*(?:#\s*\(|\s+' + ID + r'\s*\()', t, flags=re.M) if m not in KW}
lst = [Path(x) for x in Path(sys.argv[1]).read_text().split()]
roots = [Path(r) for r in sys.argv[3:]]
idx = defaultdict(list)
for r in roots:
    for f in list(r.rglob('*.sv')) + list(r.rglob('*.v')):
        try: t = strip(f.read_text(errors='ignore'))
        except Exception: continue
        for m in defs(t): idx[m].append(f)
        for n, v in re.findall(r'`define\s+(' + ID + r')\s+(' + ID + r')\s*$', f.read_text(errors='ignore'), flags=re.M):
            MAC.setdefault(n, v) if v.startswith('ot_') or v.startswith('ds') else None
have, files, todo, amb, miss = set(), list(lst), list(lst), {}, set()
cache = {}
def txt(f):
    if f not in cache: cache[f] = strip(f.read_text(errors='ignore'))
    return cache[f]
for f in lst: have |= defs(txt(f))
while todo:
    f = todo.pop()
    for m in uses(txt(f)) - have:
        c = idx.get(m)
        if not c: miss.add(m); continue
        pick = [x for x in c if x in files] or [x for x in c if any(str(x).startswith(str(r)) and str(f).startswith(str(r)) for r in roots)] or c
        pick = [x for x in pick if not x.name.endswith('_bb.v')] or pick   # behavioural macro model, not the blackbox
        if len(set(pick)) > 1: amb[m] = sorted(map(str, set(pick)))
        g = sorted(pick, key=str)[0]
        if g not in files:
            files.append(g); todo.append(g); have |= defs(txt(g))
        have.add(m)
# packages referenced (import P:: / P::) -> their defining file first; include dirs of every listed file
pidx = defaultdict(list)
for r in roots:
    for f in r.rglob('*.sv'):
        try: t = strip(f.read_text(errors='ignore'))
        except Exception: continue
        for m in re.findall(r'\bpackage\s+(' + ID + ')', t): pidx[m].append(f)
pk = []
for f in list(files):
    for m in set(re.findall(r'\b(' + ID + r')::', txt(f))):
        c = pidx.get(m)
        if c:
            same = [x for x in c if any(str(x).startswith(str(r)) and str(f).startswith(str(r)) for r in roots)] or c
            g = sorted(same, key=str)[0]
            if g not in pk and g not in files: pk.append(g)
files = pk + [f for f in files if f not in pk]
inc = sorted({str(f.parent) for f in files})
Path(sys.argv[2]).write_text('\n'.join(['+incdir+' + d for d in inc] + list(map(str, files))) + '\n')
print('packages', [str(x) for x in pk])
print(f'{len(lst)} -> {len(files)} files; unresolved {len(miss)}: {sorted(miss)[:30]}; ambiguous {len(amb)}: {list(amb)[:10]}')
