#!/usr/bin/env python3
"""DIE-HEAD-28 10-29: lockstep-with-offset miter of a HEAD wrapper whose planned internal stations were realized
(tools/s81_head/head_realize_spn_source.py -> kit_istations) against the reference wrapper of the same SOURCE7.

  head_spn_station_miter.py REF_SRC_DIR REAL_SRC_DIR TYPE OUT_DIR [--repo R] [--cycles N]

Claim checked: REAL == REF with exactly the PLAN's internal_stations count (len(regs_um), read from REF's
source_plan.json -- not from the realization report) of extra register stages on each named bus, and nothing else.
Method (cut-point lockstep, same as a sequential LEC with the leaf cores as cut points):
  * both wrappers are elaborated with the SAME RTL for every non-leaf cell (face/relay/landing/reset cells);
  * the leaf cores (the wrapper's leaf instances, e.g. ot_s81hd_spo/spr) are replaced by STUBS whose outputs are a
    free-running xorshift stream identical in REF and REAL (so out-bus data is arbitrary every cycle) and whose
    inputs are compared through hierarchical references: leaf input pin p fed by in-bus b must satisfy
    REAL.p(t) == REF.p(t - N_b) for every bit and cycle; every other leaf input REAL.p(t) == REF.p(t);
  * every wrapper output o on an out-bus with N_o stations: data bits REAL.o(t) == REF.o(t - N_o); every other
    output REAL.o(t) == REF.o(t) bit-exact every cycle;
  * out-bus epoch bit [W-1] (eq chain, async-cleared by reset): REAL.eq(t) == REF.eq(t - N_o) except the
    conservative case REAL=0/REF=1 within N_o+RESET_WIN cycles of a reset ASSERTION (stations clear at once, the
    delayed reference clears N_o cycles later); REAL=1/REF=0 anywhere is a FAIL;
  * random stimulus on every data/control input, all clock taps and forwarded clocks = one clock, arst_n wavefront
    reset at t=0 AND mid-run (warm reset), straps constant random;
  * toggle census on every compared signal (a check that never toggles is reported, not counted as coverage).
Mutants (each must FAIL): bypass the last station of the deepest in-bus, bypass the last station of the deepest
out-bus, and feed one leaf in-bus pin from a station of a different bus.
Writes OUT_DIR/{ref.sv,real.sv,stubs.sv,tb.sv,files.f,mutants/*.sv,spec.json}; run_miter.sh builds/runs them."""
import argparse
import json
import re
from pathlib import Path

PORT = re.compile(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)\s*,?', re.M)
RESET_WIN = 24


def ports(text, module):
    m = re.search(r'module\s+%s\s*(?:#\s*\(.*?\)\s*)?\((.*?)\);' % module, text, re.S)
    out = []
    for pm in PORT.finditer(m.group(1)):
        out.append((pm.group(1), int(pm.group(2)) + 1 if pm.group(2) else 1, pm.group(3)))
    return out


def leaf_insts(text, leaf_mods):
    res = {}
    for mod in leaf_mods:
        for im in re.finditer(r'^\s*%s\s+(\w+)\s*\((.*?)\);' % mod, text, re.S | re.M):
            conns = dict(re.findall(r'\.(\w+)\s*\(\s*([\w\[\]:]*)\s*\)', im.group(2)))
            res[im.group(1)] = dict(module=mod, conns=conns)
    return res


def rename(text, mod, new):
    t = re.sub(r'\bmodule\s+%s\b' % mod, 'module ' + new, text, count=1)
    return re.sub(r'\bendmodule\s*:\s*%s\b' % mod, 'endmodule : ' + new, t)


def stub(mod, text):
    ps = ports(text, mod)
    outs = [(w, n) for d, w, n in ps if d == 'output']
    tot = sum(w for w, _ in outs)
    k = (tot + 63) // 64
    body = ['module %s (' % mod + ', '.join(n for _, _, n in ps) + ');']
    for d, w, n in ps:
        body.append('    %s wire %s%s;' % (d, '[%d:0] ' % (w - 1) if w > 1 else '', n))
    body.append('    reg [63:0] s [0:%d];' % (k - 1))
    body.append('    integer j;')
    body.append('    initial for (j = 0; j < %d; j = j + 1) s[j] = 64\'h9E3779B97F4A7C15 ^ (64\'(j) * 64\'hBF58476D1CE4E5B9);' % k)
    ck = next(n for _, _, n in ps if n in ('ck', 'clk'))
    body.append('    always @(posedge %s) for (j = 0; j < %d; j = j + 1) begin' % (ck, k))
    body.append('        s[j] = s[j] ^ (s[j] << 13); s[j] = s[j] ^ (s[j] >> 7); s[j] = s[j] ^ (s[j] << 17);')
    body.append('    end')
    body.append('    wire [%d:0] all_o = {%s};' % (64 * k - 1, ', '.join('s[%d]' % j for j in range(k - 1, -1, -1))))
    off = 0
    for w, n in outs:
        body.append('    assign %s = all_o[%d:%d];' % (n, off + w - 1, off))
        off += w
    body.append('    // stub: inputs are observed by the miter through hierarchical references')
    body.append('endmodule')
    return '\n'.join(body) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref'); ap.add_argument('real'); ap.add_argument('type'); ap.add_argument('out')
    ap.add_argument('--repo', default='.'); ap.add_argument('--cycles', type=int, default=4096)
    a = ap.parse_args()
    ref_dir, real_dir, out, repo = Path(a.ref), Path(a.real), Path(a.out), Path(a.repo)
    plan = json.loads((ref_dir / 'source_plan.json').read_text())
    ty = plan['partition_types'][a.type]
    mod = ty['module']
    planned = {}
    for e in ty.get('internal_stations', []):
        c = e['conn']
        assert c.startswith('bus:'), c
        planned[c[4:]] = planned.get(c[4:], 0) + len(e['regs_um'])
    rtxt = (ref_dir / (mod + '.sv')).read_text()
    xtxt = (real_dir / (mod + '.sv')).read_text()
    assert ports(rtxt, mod) == ports(xtxt, mod), 'wrapper port lists differ'
    pl = ports(rtxt, mod)
    leaf_mods = sorted({m for m in re.findall(r'^\s{4}(ot_s81hd_\w+)\s+u_\w+\s*\(', rtxt, re.M)})
    rleaf, xleaf = leaf_insts(rtxt, leaf_mods), leaf_insts(xtxt, leaf_mods)
    assert set(rleaf) == set(xleaf)
    # planned delay per leaf input pin / wrapper output
    pname = {n for _, _, n in pl}
    in_bus = {b: n for b, n in planned.items() if b in pname and next(d for d, _, x in pl if x == b) == 'input'}
    out_bus = {b: n for b, n in planned.items() if b in pname and next(d for d, _, x in pl if x == b) == 'output'}
    assert set(in_bus) | set(out_bus) == set(planned), ('unmapped planned bus', planned)
    leafchk = []
    for inst, li in sorted(rleaf.items()):
        sp = ports(next(Path(p).read_text() for p in [repo / s for s in ty['sources']]
                        if re.search(r'module\s+%s\b' % li['module'], Path(p).read_text())), li['module'])
        for d, w, n in sp:
            if d != 'input':
                continue
            net = li['conns'].get(n, '')
            bus = next((b for b in in_bus if net == b + '_q'), None)
            leafchk.append(dict(inst=inst, pin=n, width=w, delay=in_bus[bus] if bus else 0, bus=bus, ref_net=net,
                                real_net=xleaf[inst]['conns'].get(n)))
    assert {c['bus'] for c in leafchk if c['bus']} == set(in_bus), ('in-bus without leaf reader', in_bus, leafchk)
    outchk = [dict(name=n, width=w, delay=out_bus.get(n, 0)) for d, w, n in pl if d == 'output']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ref.sv').write_text(rename(rtxt, mod, mod + '__ref'))
    (out / 'real.sv').write_text(rename(xtxt, mod, mod + '__real'))
    stubs = ''
    for lm in leaf_mods:
        src = next(Path(repo / s).read_text() for s in ty['sources'] if re.search(r'module\s+%s\b' % lm, Path(repo / s).read_text()))
        stubs += stub(lm, src)
    (out / 'stubs.sv').write_text(stubs)
    # mutants on the REAL text
    muts = {}
    deep_in = max(in_bus, key=lambda b: in_bus[b]) if in_bus else None
    deep_out = max(out_bus, key=lambda b: out_bus[b]) if out_bus else None
    if deep_in:
        n = in_bus[deep_in]
        pin = next(c['pin'] for c in leafchk if c['bus'] == deep_in)
        old = '.%s(%s_is%d_q)' % (pin, deep_in, n - 1)
        assert xtxt.count(old) == 1, old
        muts['bypass_in_%s' % deep_in] = xtxt.replace(old, ('.%s(%s_is%d_q)' % (pin, deep_in, n - 2)) if n > 1 else '.%s(%s_q)' % (pin, deep_in))
        other = next((b for b in in_bus if b != deep_in), None)
        if other:
            muts['wrongbus_in_%s' % deep_in] = xtxt.replace(old, '.%s(%s_is%d_q)' % (pin, other, in_bus[other] - 1))
    if deep_out:
        n = out_bus[deep_out]
        old = '.d(%s_is%d_q), .ea(%s_is%d_eq)' % (deep_out, n - 1, deep_out, n - 1)
        assert xtxt.count(old) == 1, old
        new = ('.d(%s_is%d_q), .ea(%s_is%d_eq)' % (deep_out, n - 2, deep_out, n - 2)) if n > 1 else '.d(%s_d), .ea(1\'b1)' % deep_out
        muts['bypass_out_%s' % deep_out] = xtxt.replace(old, new)
    (out / 'mutants').mkdir(exist_ok=True)
    for k, t in muts.items():
        (out / 'mutants' / (k + '.sv')).write_text(rename(t, mod, mod + '__real'))
    # testbench
    L = ['`timescale 1ns/1ps', 'module tb;', '    reg clk = 0;', '    integer cyc = 0, fails = 0, checks = 0, eq_cons = 0, last_rst_fall = -1000;',
         '    integer rcount [0:%d];' % (len(leafchk) + len(outchk)), '    reg [63:0] rs = 64\'hD1B54A32D192ED03;']
    ins = [(w, n) for d, w, n in pl if d == 'input']
    for w, n in ins:
        if n.startswith('clk') or n.startswith('fclk_in'):
            continue
        L.append('    reg %s%s;' % ('[%d:0] ' % (w - 1) if w > 1 else '', 'i_' + n))
    for w, n in [(w, n) for d, w, n in pl if d == 'output']:
        for s in ('r', 'x'):
            L.append('    wire %s%s_%s;' % ('[%d:0] ' % (w - 1) if w > 1 else '', s, n))
    for side, m in (('r', '__ref'), ('x', '__real')):
        conns = []
        for d, w, n in pl:
            if d == 'input':
                conns.append('.%s(%s)' % (n, 'clk' if (n.startswith('clk') or n.startswith('fclk_in')) else 'i_' + n))
            else:
                conns.append('.%s(%s_%s)' % (n, side, n))
        L.append('    %s%s u_%s (%s);' % (mod, m, side, ', '.join(conns)))
    D = 9
    for j, c in enumerate(leafchk):
        L.append('    reg [%d:0] lh%d [0:%d];' % (c['width'] - 1, j, D))
    for j, c in enumerate(outchk):
        L.append('    reg [%d:0] oh%d [0:%d];' % (c['width'] - 1, j, D))
    L.append('    reg [%d:0] prev_l [0:%d]; reg [%d:0] prev_o [0:%d];' % (
        max(c['width'] for c in leafchk) - 1, len(leafchk) - 1, max(c['width'] for c in outchk) - 1, len(outchk) - 1))
    L.append('    integer k;')
    L.append('    initial begin')
    for j, c in enumerate(leafchk):
        L.append('        for (k = 0; k <= %d; k = k + 1) lh%d[k] = 0;' % (D, j))
    for j, c in enumerate(outchk):
        L.append('        for (k = 0; k <= %d; k = k + 1) oh%d[k] = 0;' % (D, j))
    L.append('        for (k = 0; k <= %d; k = k + 1) rcount[k] = 0;' % (len(leafchk) + len(outchk)))
    for w, n in ins:
        if n.startswith('clk') or n.startswith('fclk_in'):
            continue
        L.append('        i_%s = %s;' % (n, "{%d{1'b0}}" % w if w > 1 else "1'b0"))
        if n.startswith('strap_'):
            L.append("        i_%s = %s;" % (n, rnd(w)))
    L.append('    end')
    L.append('    always #1 clk = ~clk;')
    L.append('    function automatic [63:0] xs(input [63:0] v); reg [63:0] t; begin t = v ^ (v << 13); t = t ^ (t >> 7); xs = t ^ (t << 17); end endfunction')
    L.append('    always @(negedge clk) begin')
    # compare
    for j, c in enumerate(leafchk):
        rr = 'u_r.%s.%s' % (c['inst'], c['pin']); xx = 'u_x.%s.%s' % (c['inst'], c['pin'])
        exp = 'lh%d[%d]' % (j, c['delay'] - 1) if c['delay'] else rr
        L.append('        checks = checks + 1; if (%s !== %s) begin fails = fails + 1; if (fails < 20) $display("MISMATCH leaf %s.%s cyc %%0d", cyc); end' % (xx, exp, c['inst'], c['pin']))
        L.append('        if (%s != prev_l[%d][%d:0]) rcount[%d] = rcount[%d] + 1; prev_l[%d][%d:0] = %s;' % (rr, j, c['width'] - 1, j, j, j, c['width'] - 1, rr))
    for j, c in enumerate(outchk):
        rr = 'r_%s' % c['name']; xx = 'x_%s' % c['name']; w = c['width']; jj = len(leafchk) + j
        if c['delay']:
            exp = 'oh%d[%d]' % (j, c['delay'] - 1)
            L.append('        checks = checks + 1; if (%s[%d:0] !== %s[%d:0]) begin fails = fails + 1; if (fails < 20) $display("MISMATCH out-data %s cyc %%0d", cyc); end' % (xx, w - 2, exp, w - 2, c['name']))
            L.append('        checks = checks + 1; if (%s[%d] !== %s[%d]) begin if (%s[%d] == 1\'b0 && cyc - last_rst_fall <= %d) eq_cons = eq_cons + 1; else begin fails = fails + 1; if (fails < 20) $display("MISMATCH out-epoch %s cyc %%0d real %%0d ref %%0d", cyc, %s[%d], %s[%d]); end end' % (
                xx, w - 1, exp, w - 1, xx, w - 1, c['delay'] + RESET_WIN, c['name'], xx, w - 1, exp, w - 1))
        else:
            L.append('        checks = checks + 1; if (%s !== %s) begin fails = fails + 1; if (fails < 20) $display("MISMATCH out %s cyc %%0d", cyc); end' % (xx, rr, c['name']))
        L.append('        if (%s != prev_o[%d][%d:0]) rcount[%d] = rcount[%d] + 1; prev_o[%d][%d:0] = %s;' % (rr, j, w - 1, jj, jj, j, w - 1, rr))
    # shift histories
    for j, c in enumerate(leafchk):
        L.append('        for (k = %d; k > 0; k = k - 1) lh%d[k] = lh%d[k-1]; lh%d[0] = u_r.%s.%s;' % (D, j, j, j, c['inst'], c['pin']))
    for j, c in enumerate(outchk):
        L.append('        for (k = %d; k > 0; k = k - 1) oh%d[k] = oh%d[k-1]; oh%d[0] = r_%s;' % (D, j, j, j, c['name']))
    # drive next inputs
    L.append('        cyc = cyc + 1;')
    for w, n in ins:
        if n.startswith('clk') or n.startswith('fclk_in') or n.startswith('strap_'):
            continue
        if n == 'arst_n':
            L.append("        i_arst_n = !((cyc < 30) || (cyc >= %d && cyc < %d));" % (a.cycles // 2, a.cycles // 2 + 30))
            L.append("        if (cyc == %d) last_rst_fall = cyc;" % (a.cycles // 2))
            continue
        if n == 'start_i':
            L.append("        i_start_i = !((cyc < 60) || (cyc >= %d && cyc < %d));" % (a.cycles // 2, a.cycles // 2 + 60))
            continue
        L.append('        i_%s = %s;' % (n, rnd(w)))
    L.append('        if (cyc == %d) begin' % a.cycles)
    L.append('            $display("MITER_RESULT checks=%0d fails=%0d eq_conservative=%0d cycles=%0d", checks, fails, eq_cons, cyc);')
    for j, c in enumerate(leafchk):
        L.append('            $display("TOGGLE leaf %s.%s delay %d changes %%0d", rcount[%d]);' % (c['inst'], c['pin'], c['delay'], j))
    for j, c in enumerate(outchk):
        L.append('            $display("TOGGLE out %s delay %d changes %%0d", rcount[%d]);' % (c['name'], c['delay'], len(leafchk) + j))
    L.append('            $finish;')
    L.append('        end')
    L.append('    end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    files = [str(Path(a.ref).resolve() / 'ot_dp_cells.sv')]
    if (ref_dir / 'start_stages.sv').is_file():
        files.append(str(ref_dir.resolve() / 'start_stages.sv'))
    files += [str((repo / f).resolve()) for f in ('rtl/common/ot_dp_clk_landing.sv', 'rtl/common/ot_dp_clk_landing_ca.sv',
                                                  'rtl/common/ot_meso_fifo.sv')]
    (out / 'files.f').write_text('\n'.join(files) + '\n')
    spec = dict(type=a.type, module=mod, planned_from='REF source_plan.json internal_stations len(regs_um)', planned=planned,
                in_bus=in_bus, out_bus=out_bus, leaf_checks=leafchk, out_checks=outchk, mutants=sorted(muts),
                cycles=a.cycles, reset_win=RESET_WIN)
    (out / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(json.dumps(dict(type=a.type, planned=planned, stages=sum(planned.values()), leaf_pins=len(leafchk),
                          outputs=len(outchk), mutants=sorted(muts))))


def rnd(w):
    parts = []
    left = w
    while left > 0:
        parts.append('32\'($urandom)')
        left -= 32
    return '%d\'({%s})' % (w, ', '.join(parts)) if w > 1 else "1'($urandom)"


if __name__ == '__main__':
    main()
