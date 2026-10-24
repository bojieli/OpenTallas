#!/usr/bin/env python3
"""KV-TOK 10-24: drop #(...) parameter overrides from the bound top's partition instances when EVERY override equals the
partition module's own default (exact: same elaborated design).  Why: Verilator 5.050 --hierarchical builds each
hier_block once with its defaults; an instance that carries explicit overrides is not matched to that block and is
inlined into the top (10-23 kv41 run: all hg/hgi/pv/hub_C/pc_*_0 instances inlined -> 853 MB root header, 11,900 top .cpp).
Any override that differs from the default is an error (would need a per-parameter-set module; none on kv41).
    strip_default_params.py TOP.sv PART_DIR OUT_TOP.sv"""
import glob, re, sys
top, pdir, out = sys.argv[1:4]
defs = {}
for f in glob.glob(f'{pdir}/kv3_*.sv'):
    s = open(f).read()
    for mm in re.finditer(r'^module\s+(\w+)\s*#\((.*?)\)\s*\(', s, re.M | re.S):
        defs[mm.group(1)] = dict(re.findall(r'parameter\s*(?:\[[^\]]*\])?\s*(\w+)\s*=\s*([^,\n]+?)\s*(?:,|$)', mm.group(2), re.M))
t = open(top).read()
n = bad = 0
def sub(m):
    global n, bad
    mod, params, inst = m.group(2), m.group(3), m.group(4)
    ov = re.findall(r'\.(\w+)\(([^()]*)\)', params)
    for k, v in ov:
        if defs.get(mod, {}).get(k) != v.strip():
            bad += 1; print(f'DIFF {inst} {mod}.{k} = {v} default {defs.get(mod, {}).get(k)}')
    n += 1
    return f'{m.group(1)}{mod} {inst} ('
t2 = re.sub(r'^(\s*)(kv3_\w+)\s*#\((.*?)\)\s+(\w+)\s*\(', sub, t, flags=re.M)
if bad:
    sys.exit(f'strip_default_params: {bad} overrides differ from defaults; not stripped')
open(out, 'w').write(t2)
print(f'stripped #() on {n} partition instances (all overrides == defaults)')
