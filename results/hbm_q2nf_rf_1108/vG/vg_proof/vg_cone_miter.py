#!/usr/bin/env python3
"""HBM-Q2NF-RF vG lock-step proof, part 1 (combinational): for each link, the duplicated cone f_dup (inputs: rf's D bits)
equals the original rf-only cone f (inputs: rf bits) when D == rf, bit for bit at the frontier.  Writes miter_k.v for
yosys `sat -prove`.  Part 2 (sequential) is structural and is asserted here: rf <= D sits directly under an
`always @(posedge clk)` with no reset and no enable, and q <= f_dup(D) is on the same clock line; hence for every cycle
t >= 1, q(t) = f_dup(D(t-1)) = f(rf(t)).  Usage: vg_cone_miter.py OLD.sv NEW.sv OUTDIR"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crc_cone as C

old, new, outd = sys.argv[1:4]
ol, oa = C.parse(old)
nl, na = C.parse(new)
for k in (0, 1):
    pre = r'\u_body.g_link[%d].u_link.u_ctl.u.u_core.u_codec.' % k
    rfb = pre + 'rf'
    ai = [i for i, l in enumerate(nl) if l.strip().startswith('assign { ' + rfb + '[611]')][0]
    lhs, rhs = nl[ai].strip()[len('assign '):-1].split('=', 1)
    rf_bits = [C.norm(x) for x in C.split_concat(lhs)]
    reg = C.norm(rhs)
    di = [i for i, l in enumerate(nl) if l.strip().startswith(reg + ' <= {')][0]
    hdr = nl[di - 1].strip()
    assert re.fullmatch(r'always @\(posedge [^ ,()]+(\[\d+\])?\)', hdr), hdr          # no reset, no enable
    dlist = C.split_concat(nl[di].strip()[len(reg + ' <= '):-1])
    # frontier: assigns in NEW whose rhs is now a __vg_q register
    fr = []
    for l in nl:
        m = re.match(r'\s*assign\s+(\S+)\s*=\s*(\S+)\s*;\s*// HBM-Q2NF-RF vG: retimed', l)
        if m: fr.append((m.group(1), m.group(2)))
    mine = []
    for lk, r in fr:
        q = r.strip()
        qi = [i for i, l in enumerate(nl) if l.strip() == q + ' <= ' + C.rename(lk).strip() + ';' or l.strip() == q + ' <= ' + C.rename(lk) + ';']
        assert qi, lk
        if nl[qi[0] - 1].strip() == hdr:
            mine.append(lk)
    assert len(mine) >= 1
    # collect cones
    dup = {lk: r for lk, (i, r) in na.items() if lk.endswith('__vg') or lk.endswith('__vg ')}
    orig = {}
    todo = list(mine)
    while todo:
        n = todo.pop()
        if n in orig or n not in oa: continue
        orig[n] = oa[n][1]
        todo += C.refs(oa[n][1])
    rfset = {re.sub(r'\s+', '', b) for b in rf_bits}
    leaves_old = set()
    for n, r in orig.items():
        for x in C.refs(r):
            if x not in orig and x in rfset: leaves_old.add(x)
    assert all((x in rfset) or re.fullmatch(r"h[0-9a-f]*|\d+", x) or x in orig for n, r in orig.items() for x in C.refs(r)), 'non-rf leaf in old cone'
    ports = sorted(leaves_old)
    dmap = dict(zip([re.sub(r'\s+', '', b) for b in rf_bits], dlist))
    v = ['module miter_%d(input wire [%d:0] x, output wire ok);' % (k, len(ports) - 1)]
    decl = set()
    for j, p in enumerate(ports):
        v.append('  wire %s ; assign %s = x[%d];' % (p, p, j))
        d = dmap[p].strip()
        v.append('  wire %s ; assign %s = x[%d];' % (d, d, j))
    for n, r in orig.items():
        v.append('  wire %s ; assign %s = %s;' % (n, n, r))
    sub = [n for n in dup if any(C.rename(m).strip() == n.strip() for m in orig)]
    for n in sub:
        v.append('  wire %s ; assign %s = %s;' % (n, n, dup[n]))
    v.append('  assign ok = ' + ' && '.join('(%s == %s)' % (m, C.rename(m).strip() + ' ') for m in mine) + ';')
    v.append('endmodule')
    open(os.path.join(outd, 'miter_%d.v' % k), 'w').write('\n'.join(v) + '\n')
    print('link', k, 'frontier', [m.strip() for m in mine], 'old cone', len(orig), 'dup', len(sub), 'inputs', len(ports), 'clock', hdr)
