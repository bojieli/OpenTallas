#!/usr/bin/env python3
"""QW-TTC9 10-21: restore landing-ring instance names in a bounded native32 netlist (ctlm6_bound_macro u_<idx> naming).

ctlm6_bound_macro names every emitted cell u_<idx>, idx = its position in the construct's cell dict, so the lp.py L5
landing multicycles (get_cells u_lpl_<n>_w.* -> u_lpl_<n>_r.*) cannot bind and the kit fell back to single-cycle STA
on every ring->read cone (safe8u/8bu gate: 46 / 72 failing ring->read endpoints, all u_lpl_<n>_w -> u_lpl_<n>_r).
namemap.json = the exact construct replay (same construct_parent7.py, same parent.json; replay RTL byte-identical, sha
recorded) listing the source cell name of every idx.  Every instance u_<idx> whose source cell sits under u_lpl_<n>_w /
u_lpl_<n>_r is renamed \\u_lpl_<n>_<w|r>.u<idx> ; nothing else changes (connections, modules, parameters, order).
Also drops the sim-only #(.INSTANCE("calendar_m*")) on the two ROM266 calendar macros: ORFS reads the macro from its
liberty (no parameters) and yosys refuses the parameter; content binds by instance path (die ROM_BIND / bench model by
instance suffix, QW-CALR README).
And declares the 1-bit ports as scalars (input wire [0:0] x -> input wire x), the form of the committed lp8_np that the
kit pins / clock_ports bind (r7 construct output had [0:0]; a [0:0] ck_core maps to ck_core[0] and the clock-entry SDC
refuses: 'source clock coverage differs from spec').
usage: landing_names.py namemap.json in.sv out.sv
"""
import json, re, sys, hashlib, collections
nm, src, dst = sys.argv[1:4]
m = json.load(open(nm))
names = m['names']
text = open(src).read()
assert hashlib.sha256(text.encode()).hexdigest() == m['rtl_sha256'], 'netlist differs from the replayed construct'
pat = re.compile(r'^(\(\*[^\n]*?\*\) \S+ #\(\.ID\(\d+\)\) |qfd_dv_ring_delay #\([^\n]*?\) )u_(\d+)\(', re.M)
cnt = collections.Counter()
def sub(mo):
    idx = int(mo.group(2)); n = names[idx].lstrip('\\')
    g = re.match(r'(u_lpl_\d+_[wr])\.', n)
    if not g:
        return mo.group(0)
    cnt[g.group(1)] += 1
    return f'{mo.group(1)}\\{g.group(1)}.u{idx} ('
out = pat.sub(sub, text)
out, ninst = re.subn(r'^(ot_rom_4096x266_m8) #\(\.INSTANCE\("calendar_m[01]"\)\) ', r'\1 ', out, flags=re.M)
assert ninst == 2, ninst
print('ROM266_INSTANCE_PARAMS_DROPPED', ninst)
out, nsc = re.subn(r'^((?:input|output) wire) \[0:0\] (\w+);$', r'\1 \2;', out, flags=re.M)
print('SCALAR_PORTS', nsc)
open(dst, 'w').write(out)
w = sum(v for k, v in cnt.items() if k.endswith('_w')); r = sum(v for k, v in cnt.items() if k.endswith('_r'))
lands = sorted({int(k.split('_')[2]) for k in cnt})
print(f'LANDING_NAMES renamed {sum(cnt.values())} instances (w {w}, r {r}) over {len(lands)} landings {lands}')
print('OUT_SHA256', hashlib.sha256(out.encode()).hexdigest())
