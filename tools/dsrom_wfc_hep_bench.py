#!/usr/bin/env python3
"""dsfd_wfc_hep (two dsfd_wfc_hep_bank tiles, <= 15k sinks per root) against the flat reference dsfd_wfc_hep_flat.

Cycle-exact output compare over a random stage-start stream (users drawn from both banks and their edge addresses,
positions drawn so that re-issues (pos <= last) are frequent, back-to-back starts included), with coverage floors:
starts in each bank, epoch advances in each bank, an epoch wrap, back-to-back same-user starts.

    dsrom_wfc_hep_bench.py --out DIR [--case exact|neg_stale|neg_bank] [--raw-negative]

exact: PASS required.  neg_stale (OT_WFCHEP_MUT_STALE: the epoch never advances) and neg_bank (OT_WFCHEP_MUT_BANK: the
bank select dropped) must FAIL.  Exit 0 iff every case met its expectation (--raw-negative: exit 1 when the single
negative case fails as required, the closure loop's expect=fail convention).
"""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {'exact': ([], 'pass'), 'neg_stale': (['OT_WFCHEP_MUT_STALE'], 'fail'), 'neg_bank': (['OT_WFCHEP_MUT_BANK'], 'fail')}
TB = r'''
module tb_wfc_hep;
    localparam integer NW = 21, UW = 10, EW = 4, N = 200000;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg [UW+2*NW:0] ks = 0;
    wire [UW+NW+EW:0] hd, hr;
    dsfd_wfc_hep      #(.NW(NW), .USER_W(UW), .EW(EW)) dut (.clk(clk), .rst_n(rst_n), .ks(ks), .hep(hd));
    dsfd_wfc_hep_flat #(.NW(NW), .USER_W(UW), .EW(EW)) rf  (.clk(clk), .rst_n(rst_n), .ks(ks), .hep(hr));
    integer i, bad = 0, st0 = 0, st1 = 0, adv0 = 0, adv1 = 0, wrap = 0, b2b = 0, seed = 32'h51a7c0de;
    reg [UW-1:0] u, lu; reg [NW-1:0] p; reg lst; reg [EW-1:0] pe [0:(1<<UW)-1]; reg [(1<<UW)-1:0] ps;
    reg [UW-1:0] hot [0:11];
    initial begin
        hot[0] = 0; hot[1] = 1; hot[2] = 510; hot[3] = 511; hot[4] = 512; hot[5] = 513; hot[6] = 1022; hot[7] = 1023;
        hot[8] = 37; hot[9] = 865; hot[10] = 300; hot[11] = 700;
        ps = 0; lst = 0; lu = 0;
        repeat (4) @(posedge clk); rst_n <= 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            if (($urandom(seed) % 4) != 0) begin
                u = (($urandom(seed) % 8) != 0) ? hot[$urandom(seed) % 12] : $urandom(seed);
                if (lst && ($urandom(seed) % 3) == 0) u = lu;
                p = (($urandom(seed) % 16) == 0) ? $urandom(seed) : ($urandom(seed) % 6);
                ks = {1'b1, u, 21'd0 | $urandom(seed), p};
                if (lst && u == lu) b2b = b2b + 1;
                lst = 1; lu = u;
            end else begin ks = {1'b0, 10'd0 | $urandom(seed), 21'd0 | $urandom(seed), 21'd0 | $urandom(seed)}; lst = 0; end
        end
        @(negedge clk); ks = 0; repeat (4) @(posedge clk);
        $display("HEP_COV st0=%0d st1=%0d adv0=%0d adv1=%0d wrap=%0d b2b=%0d bad=%0d", st0, st1, adv0, adv1, wrap, b2b, bad);
        if (bad == 0 && st0 > 1000 && st1 > 1000 && adv0 > 100 && adv1 > 100 && wrap > 0 && b2b > 100) $display("HEP_BENCH PASS");
        else $display("HEP_BENCH FAIL");
        $finish;
    end
    wire rv = hr[UW+NW+EW]; wire [UW-1:0] ru = hr[NW+EW +: UW]; wire [EW-1:0] re = hr[EW-1:0];
    always @(posedge clk) if (rst_n) begin
        if (hd !== hr) begin bad = bad + 1; if (bad < 6) $display("MISMATCH t=%0t dut=%h ref=%h", $time, hd, hr); end
        if (rv) begin
            if (ru[UW-1]) st1 = st1 + 1; else st0 = st0 + 1;
            if (ps[ru] && re != pe[ru]) begin
                if (ru[UW-1]) adv1 = adv1 + 1; else adv0 = adv0 + 1;
                if (re == 0) wrap = wrap + 1;
            end
            pe[ru] <= re; ps[ru] <= 1'b1;
        end
    end
endmodule
'''


def run(case, out, src):
    defs, expect = CASES[case]
    d = out / case; d.mkdir(parents=True, exist_ok=True)
    (d / 'tb_wfc_hep.sv').write_text(TB)
    files = [src / 'rtl/dsrom_sys/mtp' / f for f in ('dsfd_wfc_kit.sv',)]
    # only the hep modules are elaborated (-s tb_wfc_hep); the kit's other modules in the file stay uninstantiated
    cmd = ['iverilog', '-g2012', '-s', 'tb_wfc_hep', '-o', str(d / 'sim.vvp')] + [f'-D{x}' for x in defs] + \
          [str(d / 'tb_wfc_hep.sv')] + [str(f) for f in files]
    c = subprocess.run(cmd, capture_output=True, text=True)
    if c.returncode:
        (d / 'log').write_text(c.stdout + c.stderr)
        return dict(case=case, expect=expect, verdict='BUILD_FAIL', result=(c.stderr or c.stdout)[-300:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d)
    (d / 'log').write_text(r.stdout + r.stderr)
    ok = 'HEP_BENCH PASS' in r.stdout
    cov = next((l for l in r.stdout.splitlines() if l.startswith('HEP_COV')), '')
    met = ok == (expect == 'pass')
    return dict(case=case, expect=expect, passed=ok, verdict='OK' if met else 'UNEXPECTED', result=cov)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case')
    p.add_argument('--src', type=Path, default=ROOT); p.add_argument('--raw-negative', action='store_true')
    a = p.parse_args()
    recs = [run(c, a.out, a.src) for c in ([a.case] if a.case else CASES)]
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:10s} expect={r['expect']} {r['result']}")
    (a.out / 'hep_bench.json').write_text(json.dumps(recs, indent=1) + '\n')
    if a.raw_negative:
        assert len(recs) == 1 and recs[0]['expect'] == 'fail'
        if recs[0]['verdict'] == 'OK':
            print('WFC_HEP_NEGATIVE FAIL_AS_REQUIRED ' + recs[0]['case']); return 1
        print('WFC_HEP_NEGATIVE UNEXPECTED_PASS ' + recs[0]['case']); return 0
    ok = all(r['verdict'] == 'OK' for r in recs)
    print(f"WFC_HEP_GATE {'PASS' if ok else 'FAIL'} cases={len(recs)}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
