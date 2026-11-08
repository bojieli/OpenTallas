#!/usr/bin/env python3
"""DIE-HBM-92-OPEN/Q2NF vD source patch on the q2nf_rest kit RTL (default-off defines, PIN CYCLES 0).

OT_Q2NF_FLOWADDR: flow SRAM addr_in select uses fr (read) instead of fw (write, behind the loaded[addr] lookup):
  old addr = fw ? addr_q[10:3] : fa ; new addr = fr ? fa : addr_q[10:3].
  Lemma (Codex miter, re-proved here): fw and fr are exclusive and CE=fw|fr -> old==new; ce_in/we_in unchanged;
  the 1rw SRAM ignores addr_in when ce_in=0 (tools/mem_compiler/sram_gen.py: if (ce_in && ...)).
OT_Q2NF_DNZ: the two data_q non-zero reductions on the fw fault cone (|data_q[255:64], |data_q[63:57]) are
  computed one stage early from the unconditional pipeline input (_55080_ <= u.data_q, no enable/reset) into two
  registers on the same clock, so the fw cone no longer reaches back to the 256 data_q flops.
  Invariant nz_q == |slice(_55080_) holds from the second edge (proved by induction in prove_dnz).
"""
import re, sys, hashlib
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text(); before = hashlib.sha256(s.encode()).hexdigest()
assert 'OT_Q2NF_FLOWADDR' not in s and 'OT_Q2NF_DNZ' not in s, 'already patched'
L = s.split('\n')
P = '\\u_body.g_q2.n_u_fj.u_fj.u.u_program.'
def one(pred, what):
    idx = [i for i, l in enumerate(L) if pred(l)]
    assert len(idx) == 1, (what, len(idx)); return idx[0]
# ---- FLOWADDR
i = one(lambda l: l.lstrip().startswith('assign { _45012_, _45011_, _45010_, _45009_, _45008_, _45007_, _45006_, _45005_ } ='), 'flow addr')
m = re.match(r'^(\s*assign \{[^}]*\} = )(\\\S+ ) \? (\{[^}]*\}) : (\{[^}]*\});$', L[i])
assert m and m[2].strip() == P + 'g_fsram.fw', L[i][:200]
A, F = m[3], m[4]
assert 'addr_q[10]' in A and 'addr_q[3]' in A and 'g_fsram.fa[7]' in F and 'g_fsram.fa[0]' in F
new = m[1] + P + 'g_fsram.fr  ? ' + F + ' : ' + A + ';'
L[i] = '`ifdef OT_Q2NF_FLOWADDR\n' + new + '\n`else\n' + L[i] + '\n`endif'
# ---- DNZ
ia = one(lambda l: l.lstrip().startswith('assign {') and l.rstrip().endswith('} = _55080_;') and P + 'data_q[255]' in l, 'data_q assign')
lhs = re.findall(r'\\\S+data_q\[(\d+)\] ', L[ia]); assert [int(x) for x in lhs] == list(range(255, -1, -1))
ir = one(lambda l: l.lstrip().startswith('_55080_ <= {'), '_55080_ D')
assert L[ir - 1].strip() == 'always @(posedge clk_program)' and L[ir - 2].strip() == 'reg [255:0] _55080_;', (L[ir-2], L[ir-1])
src = re.findall(r'(\\\S+data_q\[\d+\]) ', L[ir]); assert len(src) == 256 and all('u_fj.u.data_q[' in x for x in src)
umap = {255 - k: src[k] for k in range(256)}          # u_program.data_q[j] = _55080_[j] = u.data_q-term at position 255-j
regs = []
for name in ('_32230_', '_32238_', '_32239_'):
    j = one(lambda l, n=name: l.lstrip().startswith('assign ' + n + ' = | {'), name)
    body = re.match(r'^\s*assign ' + name + r' = \| \{(.*)\};$', L[j])[1]
    terms = [t.strip() for t in body.split(',')]
    newt = []
    for t in terms:
        mm = re.fullmatch(re.escape(P) + r'data_q\[(\d+)\]', t)
        if mm: newt.append(umap[int(mm[1])] + ' ')
        else:
            assert re.fullmatch(r"\d+'h0+", t), t; newt.append(t)
    rq = '_dh92_dnz' + name.strip('_') + '_q'
    regs.append(rq)
    L[j] = ('`ifdef OT_Q2NF_DNZ\n  reg ' + rq + ';\n  always @(posedge clk_program)\n    ' + rq + ' <= | { ' + ', '.join(newt) +
            ' };\n  assign ' + name + ' = ' + rq + ';\n`else\n' + L[j] + '\n`endif')
out = '\n'.join(L); p.write_text(out)
print('PATCHED', p, 'before', before, 'after', hashlib.sha256(out.encode()).hexdigest(), 'regs', regs)
