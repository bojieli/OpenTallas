#!/usr/bin/env python3
"""KV-TOK 10-24: make every bound partition type a substitutable Verilator hierarchical block (exact transformation).

Verilator 5.050 --hierarchical never substitutes a hier_block module that HAS parameters: the top step re-elaborates it
inline (10-24 minimal test: a 2-parameter module, overrides or not, is inlined; the same module with no parameters or with
header localparams binds its protect-lib wrapper).  The 10-23 kv41 build therefore inlined every partition type with strap
parameters (hg / hgi / pv / pc*_0 / hub_C / ...) into the top: 853 MB root header, 11,900 top .cpp, top step > 500 GB.
The bound top's partition parameters are type constants: every instance override equals the module default (checked
here; any difference is an error).  So: (1) drop the #(...) overrides from the top, (2) turn each partition module's
header `parameter` into `localparam` (same values) -> identical elaborated design, every type a real hier block.
    strip_default_params.py TOP.sv PART_DIR OUT_DIR    -> OUT_DIR/qwen_kvsys_bound_top.sv + OUT_DIR/kv3_*.sv (converted)"""
import glob, os, re, sys
top, pdir, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
defs, nconv = {}, 0
for f in sorted(glob.glob(f'{pdir}/kv3_*.sv')):
    s = open(f).read()
    mm = re.search(r'^module\s+(\w+)\s*#\((.*?)\)\s*\(', s, re.M | re.S)
    if mm:
        defs[mm.group(1)] = dict(re.findall(r'parameter\s*(?:\[[^\]]*\])?\s*(\w+)\s*=\s*([^,\n]+?)\s*(?:,|$)', mm.group(2), re.M))
        hdr = re.sub(r'\bparameter\b', 'localparam', mm.group(2))
        s = s[:mm.start(2)] + hdr + s[mm.end(2):]
        nconv += 1
    open(os.path.join(out, os.path.basename(f)), 'w').write(s)
t = open(top).read()
n = bad = 0
def sub(m):
    global n, bad
    mod, params, inst = m.group(2), m.group(3), m.group(4)
    for k, v in re.findall(r'\.(\w+)\(([^()]*)\)', params):
        if defs.get(mod, {}).get(k) != v.strip():
            bad += 1; print(f'DIFF {inst} {mod}.{k} = {v} default {defs.get(mod, {}).get(k)}')
    n += 1
    return f'{m.group(1)}{mod} {inst} ('
t2 = re.sub(r'^(\s*)(kv3_\w+)\s*#\((.*?)\)\s+(\w+)\s*\(', sub, t, flags=re.M)
if bad:
    sys.exit(f'strip_default_params: {bad} overrides differ from defaults; not stripped')
open(os.path.join(out, os.path.basename(top)), 'w').write(t2)
print(f'stripped #() on {n} partition instances (all overrides == defaults); header parameter -> localparam in {nconv} types')
