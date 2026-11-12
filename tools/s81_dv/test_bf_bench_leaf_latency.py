#!/usr/bin/env python3
"""S81-FRAME-FIX-1 11-11: the as-built BF bench returns every leaf at the schedule's leaf_path.

A frame schedule traced with --bound-plan composes returns over the plan's fint depths (plan_h2_2249: u_s01 11,
u_s12 6).  The 11-11 bench kept the plain 2-flop s81b_fint seams, so every BF and q return through u_s01 / u_s12 came
9 / 4 edges early and measure needed a leaf_ret_corr.  prepare.py --bound-plan now inserts the plan's D - 2 whole-bus
stations (the bind's own ot_dp_st) after each seam; bench_leaf_latency.py checks the bench against the schedule.

  1. bound_seams + bench_seam_depths (Yosys): a synthetic two-band frame elaborates at 2 flops per seam plain and at the
     plan depth with the stages; a plan seam missing from the wrapper is refused.
  2. the committed receipts (results/rtl/s81_bf_asbuilt_1101/newkit_1111): per shape, the measured BF leaf returns
     of the PLAIN-seam bench (11-11 a29d655 runs) FAIL against the schedule's leaf_path, the bound bench's PASS, with
     leaf_ret_corr {} in every record; the structural receipts (every BF and q leaf) are FAIL plain / PASS bound.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv/bf_asbuilt_1101'), str(ROOT / 'tools/s81_dv'),
                str(ROOT / 'tools/s81_dv/layer_prog')]
import bench_leaf_latency as B  # noqa: E402
import prepare as PR  # noqa: E402

RES = ROOT / 'results/rtl/s81_bf_asbuilt_1101/newkit_1111'
SHAPES = ('col_h9_asb_x', 'col_h9_asb_nx', 'col_h10_asb_x')

KIT = '''module col_t_l4_lp_r0 #(parameter INSTANCE = "t", parameter [11:0] LK = 0) (
    input wire clk, input wire [3:0] x_i0, output wire [3:0] ret_o0, output wire [7:0] frame_int_o0, input wire [7:0] frame_int_i0);
    reg [7:0] o; reg [3:0] r; always @(posedge clk) begin o <= {x_i0, x_i0}; r <= frame_int_i0[3:0]; end
    assign frame_int_o0 = o; assign ret_o0 = r;
endmodule
module col_t_l4_lp_r1 #(parameter INSTANCE = "t", parameter [11:0] LK = 0) (
    input wire clk, input wire [7:0] frame_int_i1, output wire [7:0] frame_int_o1);
    reg [7:0] o; always @(posedge clk) o <= frame_int_i1; assign frame_int_o1 = o;
endmodule
'''
WRAP = '''module s81b_fint #(parameter integer W = 1) (input wire cka, input wire ckb, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] a, b;
    always @(posedge cka) a <= d;
    always @(posedge ckb) b <= a;
    assign q = b;
endmodule
module col_t_l4_lp_asb_x #(parameter INSTANCE = "t") (
    input wire ck_r0, input wire ck_r1, input wire rst_n, input wire [3:0] x, output wire [3:0] ret);
    wire [7:0] r0_o0, r1_i1;
    wire [7:0] r1_o1, r0_i0;
    col_t_l4_lp_r0 #(.INSTANCE(INSTANCE), .LK(0)) u_r0 (.clk(ck_r0), .x_i0(x), .ret_o0(ret), .frame_int_o0(r0_o0), .frame_int_i0(r0_i0));
    col_t_l4_lp_r1 #(.INSTANCE(INSTANCE), .LK(0)) u_r1 (.clk(ck_r1), .frame_int_i1(r1_i1), .frame_int_o1(r1_o1));
    s81b_fint #(.W(8)) u_s01 (.cka(ck_r0), .ckb(ck_r1), .d(r0_o0), .q(r1_i1));
    s81b_fint #(.W(8)) u_s10 (.cka(ck_r1), .ckb(ck_r0), .d(r1_o1), .q(r0_i0));
endmodule
'''


def bench(td, wrap, cell=None):
    d = Path(td)
    (d / 'kit.sv').write_text(KIT)
    (d / 'models.sv').write_text(wrap)
    files = [str(d / 'kit.sv'), str(d / 'models.sv')]
    if cell:
        (d / 'cell.sv').write_text(cell)
        files.append(str(d / 'cell.sv'))
    (d / 'static.f').write_text('\n'.join(files) + '\n')
    return d


def test_bench_seam_depths():
    if not Path(B.YOSYS).is_file() and not shutil.which('yosys'):
        print('SKIP yosys absent')
        return
    y = B.YOSYS if Path(B.YOSYS).is_file() else shutil.which('yosys')
    _, cell = PR.bind_station_cell(ROOT)
    assert 'module ot_dp_st' in cell and 'q <= d' in cell
    with tempfile.TemporaryDirectory() as td:
        assert B.bench_seam_depths(bench(td, WRAP), 'col_t', 'asb_x', y) == {'u_s01': 2, 'u_s10': 2}
    want = {'u_s01': 11, 'u_s10': 2}
    with tempfile.TemporaryDirectory() as td:
        fixed = PR.bound_seams(WRAP, 'col_t_l4_lp_asb_x', want)
        assert fixed.count('ot_dp_st #(.W(8))') == 9
        assert B.bench_seam_depths(bench(td, fixed, cell), 'col_t', 'asb_x', y) == want
    try:
        PR.bound_seams(WRAP, 'col_t_l4_lp_asb_x', {'u_s01': 11, 'u_s10': 2, 'u_s12': 6})
    except ValueError as e:
        assert 'differ from the wrapper seams' in str(e)
    else:
        raise AssertionError('a plan seam absent from the wrapper was accepted')


def test_receipts():
    for s in SHAPES:
        d = RES / s
        topo = json.loads((d / 'schedule.json').read_text())['topology']
        plain = json.loads((d / 'measure_plain_seam.json').read_text())
        fixed = json.loads((d / 'measure.json').read_text())
        _, pf = B.run_leaf_check(topo, plain)
        rows, ff = B.run_leaf_check(topo, fixed)
        assert pf, (s, 'plain-seam bench run must fail the leaf_path check')
        assert not ff and len(rows) == 6, (s, ff, len(rows))
        assert all(r['leaf_ret_corr'] == {} and r['ret_self_check'] for r in fixed.values()), s
        sp = json.loads((d / 'leaf_latency_plain_seam.json').read_text())
        sb = json.loads((d / 'leaf_latency.json').read_text())
        assert sp['verdict'] == 'FAIL' and sb['verdict'] == 'PASS', s
        assert sb['bench_seam_depths'] == sb['schedule_seam_depths'] == {'u_s01': 11, 'u_s10': 2, 'u_s12': 6, 'u_s21': 2}
        assert {r['kind'] for r in sb['leaves']} == {'bf', 'q'} and all(r['bench'] == r['schedule'] for r in sb['leaves'])
        assert any(r['bench'] != r['schedule'] for r in sp['leaves'] if r['kind'] == 'q')


if __name__ == '__main__':
    test_bench_seam_depths()
    test_receipts()
    print('PASS test_bf_bench_leaf_latency')
