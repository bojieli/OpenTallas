#!/usr/bin/env python3
"""Routed-netlist vs contract-RTL edge-count equivalence (H-SM 2026-10-17, H-DIE/H-NETLIST VM bank binding hold).

Simulates the ROUTED gate netlist (6_final.v of the closure-loop route, ASAP7 cell models, SRAM behavioural model) and the
CONTRACT RTL side by side on identical random inputs (every data input re-randomised every edge; every clock port of the
view tied to the one tb clock; reset pulsed once).  The RTL's inputs are delayed by DIN edges and its outputs by DOUT edges;
the routed view must equal that RTL on every output bit, every edge after warm-up.  Run at the claimed (DIN, DOUT) it must
PASS; at any other pair it must FAIL (mutant).  X handling: a gate-level X where the RTL is 0/1 is counted separately
(x_gl) and reported, never counted as a match.

  view_vs_rtl_edges.py --gl 6_final.v --top TOP --rtl-top RTLTOP --din 1 --dout 0 --out DIR [--cycles 3000] [--const p=v ...]
writes DIR/gl.v (top renamed TOP__gl, physical-only cells dropped, LVT/SLVT names mapped to the RVT models) and DIR/tb.sv.
"""
import argparse, re
from pathlib import Path

PHYS = re.compile(r'^\s*(TAPCELL|FILLER|DECAP|FILLCELL|ENDCAP|BOUNDARY)\w*\s+\S+\s*\(.*?\);', re.S | re.M)


def ports(text, mod):
    text = re.sub(r'//[^\n]*', '', text); text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    m = re.search(rf'module\s+{re.escape(mod)}\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);(.*?)endmodule', text, re.S)
    if not m:
        raise SystemExit(f'module {mod} not found')
    hdr, body = m.group(2), m.group(3)
    out = {}
    d = w = None
    for tok in hdr.split(','):
        tok = tok.strip()
        mm = re.match(r'(input|output|inout)\b\s*(?:wire|reg|logic)?\s*(?:signed\s*)?(\[\s*(\d+)\s*:\s*0\s*\])?\s*(\w+)$', tok)
        if mm:
            d = mm.group(1); w = int(mm.group(3)) + 1 if mm.group(3) else 1; out[mm.group(4)] = (d, w)
        elif re.match(r'^\w+$', tok) and d is not None and not re.search(r'\binput\b|\boutput\b', body[:0]):
            out[tok] = (d, w)
    if all(re.match(r'^\w+$', x.strip()) for x in hdr.split(',') if x.strip()):  # non-ANSI header
        out = {}
        for dd, ww, names in re.findall(r'^\s*(input|output)\s+(?:wire\s+)?(\[\d+:0\])?\s*([^;]+);', body, re.M):
            for n in names.split(','):
                n = n.strip()
                if n: out[n] = (dd, int(ww[1:].split(':')[0]) + 1 if ww else 1)
    return out


def split_output_ports(gl, mod):
    """OpenROAD write_verilog keeps an internal net that carries an output port's NAME while the port itself is driven
    through `assign <port> = <port net>;` (pad / buffer chain).  In Verilog that is one identifier with two drivers.  The
    hardware has two nets: rename every output port P to P__o, keep P as an internal wire, and point each
    `assign P[...] = N;` at P__o; an output bit with no assign is driven straight by its internal net (assign P__o = P)."""
    pp = ports(gl, mod)
    outs = {n: w for n, (d, w) in pp.items() if d == 'output'}
    m = re.search(rf'module\s+{re.escape(mod)}\s*\((.*?)\);', gl, re.S)
    hdr = m.group(1)
    new_hdr = ','.join((x.replace(x.strip(), x.strip() + '__o') if x.strip() in outs else x) for x in hdr.split(','))
    gl = gl[:m.start(1)] + new_hdr + gl[m.end(1):]
    for n, w in outs.items():
        gl = re.sub(rf'^(\s*)output\s+(\[\d+:0\]\s*)?{re.escape(n)}\s*;', lambda mm: f"{mm.group(1)}output {mm.group(2) or ''}{n}__o;\n{mm.group(1)}wire {mm.group(2) or ''}{n};", gl, count=1, flags=re.M)
    assigned = {n: set() for n in outs}
    def fix(mm):
        lhs, idx, rhs = mm.group(1), mm.group(2), mm.group(3)
        if lhs in outs:
            assigned[lhs].add(int(idx) if idx is not None else 0)
            return f" assign {lhs}__o{'['+idx+']' if idx is not None else ''} = {rhs};"
        return mm.group(0)
    gl = re.sub(r'^\s*assign\s+(\w+)(?:\[(\d+)\])?\s*=\s*([^;]+);', fix, gl, flags=re.M)
    extra = []
    for n, w in outs.items():
        for i in range(w):
            if i not in assigned[n]:
                extra.append(f" assign {n}__o{'['+str(i)+']' if w > 1 else ''} = {n}{'['+str(i)+']' if w > 1 else ''};")
    k = gl.index('endmodule', m.end())
    return gl[:k] + '\n'.join(extra) + '\n' + gl[k:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gl', required=True); ap.add_argument('--top', required=True); ap.add_argument('--rtl-top', required=True)
    ap.add_argument('--rtl-src', nargs='+', required=True)
    ap.add_argument('--din', type=int, required=True); ap.add_argument('--dout', type=int, required=True)
    ap.add_argument('--cycles', type=int, default=3000); ap.add_argument('--out', required=True)
    ap.add_argument('--const', nargs='*', default=[], help='port=value held constant (straps)')
    ap.add_argument('--clocks', default='^clk')
    ap.add_argument('--reset', default='rst_n')
    a = ap.parse_args()
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    gl = Path(a.gl).read_text()
    gl = re.sub(r'_ASAP7_75t_(L|SL)\b', '_ASAP7_75t_R', gl)
    gl = PHYS.sub('', gl)
    gl = re.sub(rf'\bmodule\s+{re.escape(a.top)}\b', f'module {a.top}__gl', gl, count=1)
    gl = split_output_ports(gl, a.top + '__gl')
    (o / 'gl.v').write_text(gl)
    gp = ports(gl, a.top + '__gl')
    rtl_text = '\n'.join(Path(p).read_text() for p in a.rtl_src)
    rp = ports(rtl_text, a.rtl_top)
    const = dict(c.split('=') for c in a.const)
    clk_re = re.compile(a.clocks)
    ins = [n for n, (d, w) in rp.items() if d == 'input' and not clk_re.search(n) and n != a.reset]
    outs = [n for n, (d, w) in rp.items() if d == 'output']
    for n in ins + outs:
        if n not in gp and n + '__o' not in gp: raise SystemExit(f'port {n} of {a.rtl_top} missing in the routed view')
    L = ['`timescale 1ns/1ps', 'module tb_view_edges;', f'  localparam integer DIN={a.din}, DOUT={a.dout}, N={a.cycles};',
         '  reg clk=0; always #5 clk=~clk; reg rst_n=0;']
    for n in ins:
        w = rp[n][1]
        L.append(f'  reg [{w-1}:0] i_{n}; reg [{w-1}:0] d_{n} [0:7];')
    for n in outs:
        w = rp[n][1]
        L.append(f'  wire [{w-1}:0] g_{n}, r_{n}; reg [{w-1}:0] q_{n} [0:7];')
    # RTL inputs delayed DIN
    L.append('  always @(posedge clk) begin')
    for n in ins:
        L.append(f'    d_{n}[0] <= i_{n}; for (integer k=1;k<8;k=k+1) d_{n}[k] <= d_{n}[k-1];')
    for n in outs:
        L.append(f'    q_{n}[0] <= r_{n}; for (integer k=1;k<8;k=k+1) q_{n}[k] <= q_{n}[k-1];')
    L.append('  end')
    def rin(n): return f'(DIN==0 ? i_{n} : d_{n}[DIN-1])'
    def rout(n): return f'(DOUT==0 ? r_{n} : q_{n}[DOUT-1])'
    gconn = []
    for n, (d, w) in gp.items():
        if d == 'input':
            if clk_re.search(n): gconn.append(f'.{n}(clk)')
            elif n == a.reset: gconn.append(f'.{n}(rst_n)')
            elif n in ins: gconn.append(f'.{n}(i_{n})')
            else: raise SystemExit(f'routed view input {n} not in the RTL')
        else:
            base = n[:-3] if n.endswith('__o') else n
            gconn.append(f'.{n}(g_{base})' if base in outs else f'.{n}()')
    rconn = []
    for n, (d, w) in rp.items():
        if d == 'input':
            if clk_re.search(n): rconn.append(f'.{n}(clk)')
            elif n == a.reset: rconn.append(f'.{n}(rst_n)')
            else: rconn.append(f'.{n}({rin(n)})')
        else:
            rconn.append(f'.{n}(r_{n})')
    L.append(f'  {a.top}__gl u_gl({", ".join(gconn)});')
    L.append(f'  {a.rtl_top} u_rtl({", ".join(rconn)});')
    L.append('  integer t, checks=0, mism=0, xgl=0, xr=0;')
    L.append('  task automatic rnd; begin')
    for n in ins:
        w = rp[n][1]
        if n in const: L.append(f'    i_{n} = {w}\'d{const[n]};')
        else: L.append(f'    for (integer b=0;b<{w};b=b+32) i_{n}[b+:32] = $urandom;' if w > 32 else f'    i_{n} = $urandom;')
    L.append('  end endtask')
    L.append('  initial begin')
    L.append('    rnd(); repeat (4) @(posedge clk); #1 rst_n = 1;')
    L.append('    for (t=0;t<N;t=t+1) begin @(posedge clk); #1 rnd(); end')
    L.append('    $display("VIEW_EDGES %s DIN=%0d DOUT=%0d checks=%0d mismatches=%0d x_gl=%0d x_rtl=%0d", "' + a.top + '", DIN, DOUT, checks, mism, xgl, xr);')
    L.append('    if (mism==0 && checks>1000) $display("VIEW_EDGES PASS"); else $display("VIEW_EDGES FAIL");')
    L.append('    $finish; end')
    L.append('  integer cyc=0; always @(negedge clk) if (rst_n) begin cyc=cyc+1; if (cyc>24) begin')
    for n in outs:
        L.append(f'    if (^{rout(n)} === 1\'bx) xr=xr+1; else if (^g_{n} === 1\'bx) xgl=xgl+1; else begin checks=checks+1; '
                 f'if (g_{n} !== {rout(n)}) begin mism=mism+1; if (mism<6) $display("MISMATCH {n} t=%0d", cyc); end end')
    L.append('  end end')
    L.append('endmodule')
    (o / 'tb.sv').write_text('\n'.join(L) + '\n')
    print(f'ins={len(ins)} outs={len(outs)} gl_ports={len(gp)}')


if __name__ == '__main__':
    main()
