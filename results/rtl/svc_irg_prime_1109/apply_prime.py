#!/usr/bin/env python3
"""die-s81-85 11-09: apply the opt-in OT_IDX_RG3_PRIME hunk of rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv (7960f12fb4c)
to another rg3-family source that has the same qr pin flop (rl[0]), hdr_job, end_w and fc_set[5] lines.
usage: apply_prime.py <rg3.sv with the hunk> <target.sv> <out.sv> [note]
The two hunks are copied verbatim (an optional one-line note naming the variant's fault output is appended to the
comment); the anchors must occur exactly once, so a text drift refuses instead of guessing."""
import sys
src, tgt, out = sys.argv[1:4]
note = sys.argv[4] if len(sys.argv) > 4 else ''
s = open(src).read()
t = open(tgt).read()
A1 = "    wire       end_w = pay_job && left == 12'd1;\n"
A2 = "            if (hbad1) fc_set[5] <= 1'b1;\n"
i = s.index(A1) + len(A1)
j = s.index("    reg        wdone_p;\n", i)
h1 = s[i:j]
assert h1.startswith('`ifdef OT_IDX_RG3_PRIME\n') and h1.endswith('`endif\n'), 'hunk 1 not found in source'
k = s.index(A2) + len(A2)
h2 = s[k:s.index('`endif\n', k) + len('`endif\n')]
assert h2.startswith('`ifdef OT_IDX_RG3_PRIME\n'), 'hunk 2 not found in source'
if note:
    m = '    // The stream is not stalled or changed.  MUT: PRIME 3 edges short.\n'
    assert h1.count(m) == 1
    h1 = h1.replace(m, m + '    // ' + note + '\n')
for a in (A1, A2, A1 + "    reg        wdone_p;\n"):
    if t.count(a) != 1:
        sys.exit('anchor %r occurs %d times in %s' % (a.strip(), t.count(a), tgt))
if 'OT_IDX_RG3_PRIME' in t:
    sys.exit('%s already carries OT_IDX_RG3_PRIME' % tgt)
t = t.replace(A1 + "    reg        wdone_p;\n", A1 + h1 + "    reg        wdone_p;\n")
t = t.replace(A2, A2 + h2)
open(out, 'w').write(t)
