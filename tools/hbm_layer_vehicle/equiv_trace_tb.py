#!/usr/bin/env python3
"""HBMc/TOKEN2 (10-22): random-stimulus output-trace tb for a cut slice (HIERWRAP vs flat equivalence).

Drives every slice input from a fixed-seed 64-bit LFSR each refclk cycle (por_n / *rst* inputs held low for the
first RESET cycles, then high), folds every slice output into a 64-bit running hash on each negedge of refclk and
prints TRACE_HASH checkpoints every 500 cycles and at the end.  Two builds of the same slice are cycle-exact iff
all checkpoints match.   equiv_trace_tb.py --slice DIR [--cycles N] -> DIR/tb_slice.sv (module tb_hbm_slice)
"""
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--slice', required=True); ap.add_argument('--cycles', type=int, default=4000)
    ap.add_argument('--reset', type=int, default=200)
    a = ap.parse_args(); S = Path(a.slice); b = json.load(open(S / 'boundary.json'))
    ins, outs = b['inputs'], b['outputs']
    L = ['`timescale 1ns/1ps', 'module tb_hbm_slice;', '  reg refclk = 0, por_n = 0;', '  always #5 refclk = ~refclk;',
         "  reg [63:0] lf = 64'h9E3779B97F4A7C15, h = 64'h0; integer cyc = 0;"]
    for x in ins:
        if x['name'] not in ('hb_ckgen__refclk', 'hb_ckgen__por_n'):
            L.append(f"  reg [{x['width'] - 1}:0] {x['name']} = 0;")
    for x in outs:
        L.append(f"  wire [{x['width'] - 1}:0] {x['name']};")
    conn = [f".{x['name']}({'refclk' if x['name'] == 'hb_ckgen__refclk' else 'por_n' if x['name'] == 'hb_ckgen__por_n' else x['name']})" for x in ins]
    conn += [f".{x['name']}({x['name']})" for x in outs]
    L.append(f"  {b['slice_top']} dut (" + ', '.join(conn) + ');')
    L.append('  function automatic [63:0] step(input [63:0] s); step = {s[62:0], s[63] ^ s[62] ^ s[60] ^ s[59]}; endfunction')
    L.append('  always @(posedge refclk) begin')
    L.append(f'    cyc <= cyc + 1; if (cyc == {a.reset}) por_n <= 1;')
    k = 0
    for x in ins:
        n, w = x['name'], x['width']
        if n in ('hb_ckgen__refclk', 'hb_ckgen__por_n'):
            continue
        if 'rst' in n.lower():
            L.append(f"    {n} <= (cyc >= {a.reset + 20}) ? {{{w}{{1'b1}}}} : {{{w}{{1'b0}}}};")
            continue
        reps = (w + 63) // 64
        L.append(f"    {n} <= {{{reps}{{lf ^ 64'd{k * 0x9E37 + 1}}}}};")
        k += 1
    L.append('    lf <= step(step(lf));')
    L.append('  end')
    L.append('  always @(negedge refclk) begin')
    for x in outs:
        n, w = x['name'], x['width']
        chunks = ' ^ '.join(f"64'({n}[{min(i + 63, w - 1)}:{i}])" for i in range(0, w, 64))
        L.append(f'    h = {{h[62:0], h[63]}} * 64\'d1099511628211 ^ ({chunks});')
    L.append(f'    if (cyc % 500 == 0) $display("TRACE_HASH cyc=%0d %h", cyc, h);')
    L.append(f'    if (cyc == {a.cycles}) begin $display("TRACE_FINAL cyc=%0d %h", cyc, h); $finish; end')
    L.append('  end')
    L.append('endmodule')
    (S / 'tb_slice.sv').write_text('\n'.join(L) + '\n')
    print(f'EQUIV_TB inputs={len(ins)} outputs={len(outs)} cycles={a.cycles}')


if __name__ == '__main__':
    main()
