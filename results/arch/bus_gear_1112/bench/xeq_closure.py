#!/usr/bin/env python3
"""BUS-GEAR-2: static module closure for the x-gear EQ bench.
usage: closure2.py REPO SEL_IN SEL_OUT [ASBUILT.json]   (SEL entries are repo-relative paths, plus tb_s81_xgear_eq.sv)
Index = every module defined under rtl/ and physical/die_plan/s81/bind/models (first definition wins, preferring files
already in SEL, then the as-built manifest's prefer + files lists = the bind's own source choice).  Adds the defining file of every identifier used as a module type in the selection until fixpoint."""
import os, re, sys

repo, sin, sout = sys.argv[1:4]
ab = sys.argv[4] if len(sys.argv) > 4 else None
sel = [l.strip() for l in open(sin) if l.strip()]
MOD = re.compile(r'^\s*(?:module|macromodule)\s+(\w+)', re.M)
INST = re.compile(r'^\s*(\w+)\s*(?:#\s*\(|\w+\s*(?:\[[^\]]*\]\s*)?\()', re.M)
KW = {'module', 'if', 'for', 'case', 'assign', 'always', 'initial', 'function', 'task', 'begin', 'end', 'wire', 'reg',
      'logic', 'input', 'output', 'inout', 'generate', 'else', 'while', 'repeat', 'return', 'localparam', 'parameter'}


def strip(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', s)


def path(f):
    return f if f == 'tb_s81_xgear_eq.sv' else os.path.join(repo, f)


idx = {}
for f in sel:
    for m in MOD.findall(strip(open(path(f), errors='replace').read())):
        idx.setdefault(m, f)
if ab:
    import json
    A = json.load(open(ab))
    for rel in list(A.get('prefer', [])) + list(A.get('files', [])):
        try:
            txt = strip(open(os.path.join(repo, rel), errors='replace').read())
        except OSError:
            continue
        for m in MOD.findall(txt):
            idx.setdefault(m, rel)
for root in ('rtl', 'physical/die_plan/s81/bind/models'):
    for dp, _, fs in os.walk(os.path.join(repo, root)):
        for fn in sorted(fs):
            if fn.endswith(('.sv', '.v')):
                rel = os.path.relpath(os.path.join(dp, fn), repo)
                if rel.startswith('rtl/test/'):
                    continue   # testbench / pinned copies never resolve a design module
                try:
                    txt = strip(open(os.path.join(repo, rel), errors='replace').read())
                except OSError:
                    continue
                for m in MOD.findall(txt):
                    idx.setdefault(m, rel)
have = set(sel)
added = []
changed = True
while changed:
    changed = False
    defined = set()
    used = set()
    for f in list(have):
        t = strip(open(path(f), errors='replace').read())
        defined |= set(MOD.findall(t))
        used |= {u for u in INST.findall(t) if u not in KW}
    for u in sorted(used - defined):
        f = idx.get(u)
        if f and f not in have:
            have.add(f); added.append((u, f)); changed = True
missing = sorted(u for u in used - defined if u not in idx and not u.startswith('$'))
out = sel + [f for _, f in added]
open(sout, 'w').write('\n'.join(out) + '\n')
print('added', len(added), 'files'); [print('  +', u, f) for u, f in added]
print('unresolved identifiers (may be non-modules):', missing[:40])
