#!/usr/bin/env python3
"""STEWARD-HBMd/GLUE 2026-10-23: lockstep equivalence bench of the VM-glue SPLIT parent hfd_hgi_vms_glue_<k>_s
(gen_vms_glue_split.py: RS x2 + HUB children, zero-logic parent) against
  --ref tile : the g7 tile master hfd_hgi_vms_glue_<k>_t (gen_vms_glue_tiles.py) at the SAME ports -> proves the split
               changes no edge and no function (the die-contract latency budget is untouched);
  --ref ref  : the contract reference hfd_hgi_vms_glue_<k>_t_ref (historical children + explicit edges) at the flat
               ports, with the tile's per-lane / per-bank ports wired by slice arithmetic (vms_glue_tile_equiv.tile_slice).
Same stimulus discipline as vms_glue_tile_equiv.py: random inputs on every port every edge, rst_n re-asserted for 8 edges
every 128 edges, EVERY output bit compared on every edge while rst_n is high.  Prints
"VMS_GLUE_SPLIT_EQUIV <Q> PASS|FAIL checks=N errors=M".
Mutants on the split (must FAIL): rmut (MUT 1, ring-stop flit bit, both RS), g3 (MUT 4), g4 (MUT 5: pi / rce seam
relays bypassed), g5 (MUT 6), g7 (MUT 7), split (MUT 9: the CW pi seam relay pi0_r missing), sid (E: strap = the other
E quadrant's sid).
    vms_glue_split_equiv.py --quadrant SW|NW|SE|NE --ref tile|ref --out DIR [--mut ...] [--cycles N]
"""
import argparse, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import gen_vms_glue_tiles as G  # noqa: E402
import vms_glue_tile_equiv as E  # noqa: E402

TAG = 'VMS_GLUE_SPLIT_EQUIV'
MUTS = dict(rmut=1, g3=4, g4=5, g5=6, g7=7, split=9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quadrant', required=True, choices=list(E.KEY))
    ap.add_argument('--ref', required=True, choices=('tile', 'ref'))
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--mut', choices=tuple(MUTS) + ('sid',))
    ap.add_argument('--cycles', type=int, default=4000)
    a = ap.parse_args(); q = a.quadrant; k = E.KEY[q]; c = G.M[k]
    if a.mut == 'sid' and q not in E.SID:
        raise SystemExit('vms_glue_split_equiv: --mut sid is for the strapped E master (SE / NE)')
    mut = MUTS.get(a.mut, 0)
    tp = G.ports(k, c)
    if a.ref == 'tile':
        ins = [(n, w) for n, d, w in tp if d == 'input' and n not in ('clk', 'rst_n', 'sid')]
        outs = [(n, w) for n, d, w in tp if d == 'output']
    else:
        rp = G.ref_ports(k, c)
        ins = [(n, w) for n, d, w in rp if d == 'input' and n not in ('clk', 'rst_n', 'sid')]
        outs = [(n, w) for n, d, w in rp if d == 'output']
    T = ['`timescale 1ns/1ps', 'module tb_vms_glue_split;', '  reg clk = 0; always #0.5 clk = ~clk;', '  reg rst_n;']
    T += [f'  reg {G.w(wd)}{n};' for n, wd in ins]
    T += [f'  wire {G.w(wd)}a_{n}, b_{n};' for n, wd in outs]
    strap = rstrap = ''
    if c['sid'] == 'strap':
        s = E.SID[q]; sd = E.SID['NE' if q == 'SE' else 'SE'] if a.mut == 'sid' else s
        T.append(f"  wire [1:0] sid_ref = 2'd{s}, sid_dut = 2'd{sd};")
        strap, rstrap = '.sid(sid_dut), ', '.sid(sid_ref), '
    if a.ref == 'tile':
        dconn = [f'.{n}({n})' for n, _ in ins] + [f'.{n}(a_{n})' for n, _ in outs]
    else:
        dconn = []
        for nm, d, wd in tp:
            if nm in ('clk', 'rst_n', 'sid'):
                continue
            f, hi, lo = E.tile_slice(nm, c)
            tgt = f if d == 'input' else f'a_{f}'
            dconn.append(f'.{nm}({tgt}[{hi}:{lo}])' if hi is not None else f'.{nm}({tgt})')
    T.append(f'  hfd_hgi_vms_glue_{k}_s #(.MUT({mut})) dut (.clk(clk), .rst_n(rst_n), {strap}\n    ' + ',\n    '.join(dconn) + ');')
    rconn = [f'.{n}({n})' for n, _ in ins] + [f'.{n}(b_{n})' for n, _ in outs]
    rmod = f'hfd_hgi_vms_glue_{k}_t #(.MUT(0))' if a.ref == 'tile' else f'hfd_hgi_vms_glue_{k}_t_ref'
    T.append(f'  {rmod} u_ref (.clk(clk), .rst_n(rst_n), {rstrap}\n    ' + ',\n    '.join(rconn) + ');')
    T.append('  integer cyc, chk, errs;')
    T.append('  task rnd; begin')
    T += [f'    {n} = {{{(wd + 31) // 32}{{$random}}}};' for n, wd in ins]
    T.append('  end endtask')
    T.append('  initial begin')
    T.append('    chk = 0; errs = 0; rst_n = 0; rnd;')
    T.append('    repeat (8) begin @(negedge clk); rnd; end')
    T.append('    rst_n = 1;')
    T.append(f'    for (cyc = 0; cyc < {a.cycles}; cyc = cyc + 1) begin')
    T.append('      @(negedge clk);')
    T.append('      if (rst_n) begin')
    for n, _ in outs:
        T.append(f'        chk = chk + 1; if (a_{n} !== b_{n}) begin errs = errs + 1; if (errs < 6) $display("MISMATCH cyc %0d {n}", cyc); end')
    T.append('      end')
    T.append('      rnd;')
    T.append('      if (cyc % 128 == 119) rst_n = 0;')
    T.append('      if (cyc % 128 == 127) rst_n = 1;')
    T.append('    end')
    T.append(f'    $display("{TAG} {q} %s checks=%0d errors=%0d", (errs == 0 && chk > 0) ? "PASS" : "FAIL", chk, errs);')
    T.append('    $finish;')
    T.append('  end')
    T.append('endmodule')
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_vms_glue_split.sv').write_text('\n'.join(T) + '\n')
    print('VMS_GLUE_SPLIT_TB', q, f'hfd_hgi_vms_glue_{k}_s vs {rmod}', 'MUT=' + (a.mut or 'none'), f'cycles={a.cycles}')


if __name__ == '__main__':
    main()
