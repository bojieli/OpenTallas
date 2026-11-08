#!/usr/bin/env python3
"""Build the OT_Q2NF_DNZ miter from the PATCHED kit RTL text (exact lines): the _55080_ register, the u_program.data_q
assign, and for each of the 3 reductions both the original assign (old) and the new register (new). ok = all old==new.
Also writes a mutant (one data bit dropped from the first new register)."""
import re, sys
from pathlib import Path
src = Path(sys.argv[1]).read_text().split('\n'); out = Path(sys.argv[2]); out.mkdir(exist_ok=True)
P = '\\u_body.g_q2.n_u_fj.u_fj.u.'
ir = [i for i, l in enumerate(src) if l.lstrip().startswith('_55080_ <= {')]; assert len(ir) == 1; ir = ir[0]
ia = [i for i, l in enumerate(src) if l.rstrip().endswith('} = _55080_;')]; assert len(ia) == 1; ia = ia[0]
body = []
for name in ('_32230_', '_32238_', '_32239_'):
    j = [i for i, l in enumerate(src) if l.strip() == '`ifdef OT_Q2NF_DNZ' and src[i + 4].strip().startswith('assign ' + name + ' = ')]
    assert len(j) == 1, name; j = j[0]
    assert src[j + 5].strip() == '`else' and src[j + 7].strip() == '`endif'
    body += [src[j + 1], src[j + 2], src[j + 3], src[j + 4].replace('assign ' + name, 'assign ' + name + 'new'),
             src[j + 6].replace('assign ' + name, 'assign ' + name + 'old'), f'  wire {name}new, {name}old;']
names = sorted(set(re.findall(r'\\\S+', '\n'.join([src[ir], src[ia]] + body))))
decl = [f'  wire {n} ;' for n in names if n.startswith(P) and 'u_program' in n]
ins = [n for n in names if n.startswith(P) and 'u_program' not in n]
assert len(ins) == 256
hdr = 'module dnz_miter(input clk_program, input [255:0] din, output ok);'
txt = [hdr] + decl + [f'  wire {n} ;' for n in ins] + [f'  assign {n} = din[{int(re.search(r"\[(\d+)\]", n)[1])}];' for n in ins]
txt += ['  reg [255:0] _55080_;', '  always @(posedge clk_program)', src[ir], src[ia]] + body
txt += ['  assign ok = (_32230_new == _32230_old) && (_32238_new == _32238_old) && (_32239_new == _32239_old);', 'endmodule']
s = '\n'.join(txt) + '\n'; (out / 'miter_dnz.sv').write_text(s)
# mutant: drop data bit 200 from the first new register only
k = s.index('_dh92_dnz32230_q <= |'); e = s.index(';', k)
seg = s[k:e]; seg2 = seg.replace(P + 'data_q[200] ,', '', 1); assert seg2 != seg
(out / 'mutant_dnz.sv').write_text(s[:k] + seg2 + s[e:])
print('miter', out / 'miter_dnz.sv', 'inputs', len(ins))
