#!/usr/bin/env python3
"""HBM-KITS-C/VMGLUE 2026-10-18 (g2): lockstep equivalence bench of the VM hub-glue TILE masters
(rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv: g3 pipelined _lt children (HH-3 10-19), reset-light, parallel hub demultiplex, regional
reset relay, per-lane ring / per-bank ports, one landing / relay stage on every bank-side port) against their CONTRACT
reference <tile>_ref (hfd_hgi_vms_glue_tiles_ref.sv: the UNCHANGED historical children wired as
ot_vms_slice_static_glue with the g3 edges as explicit 1-edge delays, COMMIT_DELAY 8, behind one delay stage per
bank-side port, at the historical flat ports).
The testbench drives both with the same random inputs on EVERY port (flat buses; the tile's per-lane / per-bank ports
are wired by slice arithmetic computed here, independent of the generator's concatenations), re-asserts rst_n for 8
edges every 128 edges (re-arms the sticky faults; proves the reset-light payload flush), and compares EVERY output bit
on every edge while rst_n is high.  Prints "VMS_GLUE_LT_EQUIV <Q> PASS|FAIL checks=N errors=M".
The historical glue == the full slice (per bank port wiring, banks hoisted) is the 10-18 witness of 6e62dbac4
(results/rtl/vm_glue_1018/bench/*pos.sim.log, VMS_HOIST_EQUIV / VMS_QB_EQUIV); ref adds only the latency contract.
Mutants (must FAIL):  --mut rmut  tile MUT 1 (ring-stop egress flit bit flipped)
                      --mut land  tile MUT 3 (eg not landed: the contract's +1 edge on egress missing)
                      --mut sid   (SE / NE) the tile strap gets the OTHER E quadrant's sid
                      --mut g3    tile MUT 4 (hub pq without the g3 face-group edge: the contract's +1 on pq missing)
                      --mut g4    tile MUT 5 (hub -> ring pi and ring -> replay rce without the g4 reach relays: the contract's +1s missing)
                      --mut g5    tile MUT 6 (hub bank select copies fed by the decode, not the g5 hub-side register: pq select one edge early)
                      --mut g7    tile MUT 7 (the g6 hub landing br kept on the bank returns: the contract's g7 pr -1 missing)
                      --mut g7e   tile MUT 8 (the g6 eg tile relays kept: the contract's g7 eg -2 missing)
    vms_glue_tile_equiv.py --quadrant SW|NW|SE|NE --out DIR [--mut rmut|land|sid] [--cycles N]
"""
import argparse, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import gen_vms_glue_tiles as G  # noqa: E402

KEY = dict(SW='sw', NW='nw', SE='e', NE='e')
SID = dict(SE=1, NE=3)


def tile_slice(nm, c):
    """tile port name -> (flat ref port, msb, lsb) by index arithmetic"""
    for n, _ in G.RINGB:
        if nm == f'{n}_h':
            return n, 2223, 2208
        for b in range(8):
            if nm == f'{n}_l{b}':
                return n, b * 276 + 275, b * 276
    if nm[0] == 'b' and nm[1].isdigit() and nm[2] == '_':
        b, base = int(nm[1]), nm[3:]
        for n, _, wd, f in G.bankp(c):
            if n == base:
                return f, b * wd + wd - 1, b * wd
    return nm, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quadrant', required=True, choices=list(KEY))
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--mut', choices=('rmut', 'land', 'sid', 'g3', 'g4', 'g5', 'g7', 'g7e'))
    ap.add_argument('--cycles', type=int, default=4000)
    a = ap.parse_args(); q = a.quadrant; k = KEY[q]; c = G.M[k]
    if a.mut == 'sid' and q not in SID:
        raise SystemExit('vms_glue_tile_equiv: --mut sid is for the strapped E master (SE / NE)')
    rp = G.ref_ports(k, c); tp = G.ports(k, c)
    ins = [(n, w) for n, d, w in rp if d == 'input' and n not in ('clk', 'rst_n', 'sid')]
    outs = [(n, w) for n, d, w in rp if d == 'output']
    mut = dict(rmut=1, land=3, g3=4, g4=5, g5=6, g7=7, g7e=8).get(a.mut, 0)
    T = ['`timescale 1ns/1ps', 'module tb_vms_glue_lt;', '  reg clk = 0; always #0.5 clk = ~clk;', '  reg rst_n;']
    T += [f'  reg {G.w(wd)}{n};' for n, wd in ins]
    T += [f'  wire {G.w(wd)}a_{n}, b_{n};' for n, wd in outs]
    strap = ''
    if c['sid'] == 'strap':
        s = SID[q]; sd = SID['NE' if q == 'SE' else 'SE'] if a.mut == 'sid' else s
        T.append(f"  wire [1:0] sid_ref = 2'd{s}, sid_dut = 2'd{sd};")
        strap = '.sid(sid_dut), '
    conn = []
    for nm, d, wd in tp:
        if nm in ('clk', 'rst_n', 'sid'):
            continue
        f, hi, lo = tile_slice(nm, c)
        tgt = f if d == 'input' else f'a_{f}'
        conn.append(f'.{nm}({tgt}[{hi}:{lo}])' if hi is not None else f'.{nm}({tgt})')
    T.append(f'  hfd_hgi_vms_glue_{k}_t #(.MUT({mut})) dut (.clk(clk), .rst_n(rst_n), {strap}\n    ' + ',\n    '.join(conn) + ');')
    rconn = [f'.{n}({n})' for n, _ in ins] + [f'.{n}(b_{n})' for n, _ in outs]
    rstrap = '.sid(sid_ref), ' if c['sid'] == 'strap' else ''
    T.append(f'  hfd_hgi_vms_glue_{k}_t_ref u_ref (.clk(clk), .rst_n(rst_n), {rstrap}\n    ' + ',\n    '.join(rconn) + ');')
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
    T.append(f'    $display("VMS_GLUE_LT_EQUIV {q} %s checks=%0d errors=%0d", (errs == 0 && chk > 0) ? "PASS" : "FAIL", chk, errs);')
    T.append('    $finish;')
    T.append('  end')
    T.append('endmodule')
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_vms_glue_lt.sv').write_text('\n'.join(T) + '\n')
    print('VMS_GLUE_TILE_TB', q, f'hfd_hgi_vms_glue_{k}_t', 'MUT=' + (a.mut or 'none'), f'cycles={a.cycles}')


if __name__ == '__main__':
    main()
