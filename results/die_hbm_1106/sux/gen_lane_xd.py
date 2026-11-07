#!/usr/bin/env python3
"""HBM-FORM-SPLIT-14-SUX 11-06: vB (safe by construction) RTL of ot_hbm_su_pg_lane_exp_x_core and ot_hbm_su_pg_lane_full_x_core.

Runs results/die_hbm_1106/expx_vc/gen_lane_xc.py (vC: MLAT 6 = C1+C2+C3, ALAT 5 = A+B, SFU seam 4 / 3) and then:
  lane multiplier MLAT 6 -> 7: ot_hdc_fp32_mul_lat #(.LAT(7), .CUTS(23)) = C1 + C2 + C3 + C5.  C5 splits the operand
                  field decode / subnormal LZC from the normalise shift, i.e. the input stage that carries the SFU face
                  return (sx_y_exp / sx_y_div -> S mux -> u_e1m) and the line / operand multiplexers into u_m1 / u_m2 /
                  u_q / u_e1m / u_me2 (routed full_x vB TT: sx_y_exp -> u_e1m c1 still -1.1 ps at ZERO skew).  Existing
                  bit-identical cut of the same binary32 datapath (rtl/hdc/ot_hdc_fp32_mul_lat.sv), no new arithmetic.
                  The five lane multipliers go through ot_hdc_qmul_lat_xd (defined in the generated lane file: LAT 7 ->
                  CUTS 23, else ot_hdc_qmul_lat), so the shared rtl/hdc wrappers are unchanged.
  lane adder      ALAT 5 (vC, unchanged).   SFU seam SMLAT 4 / SALAT 3 (sfu_s core unchanged).
  E1-add fault alignment: 2 dM - dA (gen_lane_xb.py uses dM, correct only while dM == dA; see below).
  dM = 3, dA = 2 (gen_lane_xb.py formulas):
PIN CYCLES (core ports, vs the old part-18 exp_x / full_x):
  write / reducer / fault / coll (lane_vm_*, lane_kv_*, lane_ro_*, lane_fault, lane_coll) +T = 4 dM + dA = +14
  SFU seam out (sx_v, sx_r, sx_fn) and return (sx_y_exp, sx_y_div, sx_fault) +S = 2 dM + dA = +8 (pair moves together)
  full_x side pipe out (lane_side_v, lane_side_x) and return (lane_side_y) +S = +8 (pair moves together)
  all other ports 0.  (vs exp_x vC: +4 / +2; vs full_x vB (MLAT 5 / ALAT 4): +9 / +5.)

    gen_lane_xd.py REPO OUTDIR [FULLX_CORE_IN]
      writes OUTDIR/ot_hbm_su_static_lane_xb.sv, ot_hbm_su_static_lane_pinreg_xb.sv, ot_hbm_su_pg_lane_exp_x_core.sv and,
      with FULLX_CORE_IN (the part-18 / forms19 ot_hbm_su_pg_lane_full_x_core.sv, KIND 2), ot_hbm_su_pg_lane_full_x_core.sv
"""
import os, subprocess, sys
repo, out = sys.argv[1:3]
fin = sys.argv[3] if len(sys.argv) > 3 else None
MLAT, ALAT, CUTS = 7, 5, 23
os.makedirs(out, exist_ok=True)
subprocess.run([sys.executable, '-I', f'{repo}/results/die_hbm_1106/expx_vc/gen_lane_xc.py', repo, out], check=True)


def sub1(txt, a, b):
    assert txt.count(a) == 1, (a[:80], txt.count(a))
    return txt.replace(a, b)


f = f'{out}/ot_hbm_su_static_lane_xb.sv'
t = open(f).read()
assert t.count('ot_hdc_qmul_lat #(MLAT)') == 5, t.count('ot_hdc_qmul_lat #(MLAT)')
t = t.replace('ot_hdc_qmul_lat #(MLAT)', 'ot_hdc_qmul_lat_xd #(MLAT)')
t = sub1(t, '(ALAT 5, ot_hdc_qadd_lat_xb).\n',
         '(ALAT 5, ot_hdc_qadd_lat_xb).\n// HBM-FORM-SPLIT-14-SUX 11-06 vB: post-patched by results/die_hbm_1106/sux/gen_lane_xd.py (MLAT 7 = C1+C2+C3+C5, '
         'ot_hdc_qmul_lat_xd).\n')
t += f'''
// HBM-FORM-SPLIT-14-SUX 11-06 vB: ot_hdc_qmul_lat with the LAT-7 input-decode-cut multiplier (ot_hdc_fp32_mul_lat CUTS {CUTS} =
// C1 + C2 + C3 + C5 of rtl/hdc/ot_hdc_fp32_mul_lat.sv, bit-identical to the LAT-3 unit); every other LAT is ot_hdc_qmul_lat.
module ot_hdc_qmul_lat_xd #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    generate if (LAT == 7) begin : g_l7d
        wire [1:0] err;
        wire vo;
        ot_hdc_fp32_mul_lat #(.LAT(7), .CUTS({CUTS})) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                              .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else begin : g_q
        ot_hdc_qmul_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y), .fault(fault));
    end endgenerate
endmodule
'''
# f_e1a (the E1 ADD fault) leaves u_e1a after ALAT, before the u_e1ad MLAT - ALAT re-delay of its data, so its growth is
# M1 + M2 + AD + E1-add = 2 dM + 2 dA and its alignment to +T is 2 dM - dA.  gen_lane_xb.py aligns it like f_e1m
# (T - 3 dM - dA = dM): identical only while dM == dA (vB 1/1, vC 2/2); here dM 3 / dA 2 it would put E1-add faults one edge EARLY
# on lane_fault (bench MUT 0 caught it: 95 lane_fault mismatches, NaN epochs only).
t = sub1(t, 'ot_hdc_delay #(.W(1), .D((4 * DM + DA) - 3 * DM - DA), .RESET(1)) u_al_f_e1a',
         'ot_hdc_delay #(.W(1), .D((4 * DM + DA) - 2 * DM - 2 * DA), .RESET(1)) u_al_f_e1a')
open(f, 'w').write(t)

HDR = ('// then HBM-FORM-SPLIT-14-SUX 11-06 vB (results/die_hbm_1106/sux/gen_lane_xd.py): MLAT 7 (C1+C2+C3+C5) / ALAT 5, '
       'seam depths 4 / 3. Do not edit.')
f = f'{out}/ot_hbm_su_pg_lane_exp_x_core.sv'
c = open(f).read()
c = sub1(c, f'    parameter integer MLAT = 6,         // HBM-FORM-SPLIT-13-EXPX vC: LAT-6 multiplier (C1 + C2 + C3)\n',
         f'    parameter integer MLAT = {MLAT},         // HBM-FORM-SPLIT-14-SUX vB: LAT-7 multiplier (C1 + C2 + C3 + C5)\n')
c = sub1(c, 'MLAT 6 / ALAT 5. Do not edit.', 'MLAT 6 / ALAT 5,\n' + HDR)
open(f, 'w').write(c)

if fin:
    c = open(fin).read()
    lines = c.split('\n', 1)
    assert lines[0].startswith('// HBM-REFORM-A 11-04: GENERATED') and lines[0].endswith(' Do not edit.')
    c = lines[0][:-len(' Do not edit.')].rstrip('.') + ',\n' + HDR + '\n' + lines[1]
    c = sub1(c, '    parameter integer MLAT = 4,\n    parameter integer ALAT = 3,',
             f'    parameter integer MLAT = {MLAT},         // HBM-FORM-SPLIT-14-SUX vB: LAT-7 multiplier (C1 + C2 + C3 + C5)\n'
             f'    parameter integer ALAT = {ALAT},         // LAT-5 add (A + B)\n'
             '    parameter integer SMLAT = 4,        // sfu_s_core chain (unchanged)\n'
             '    parameter integer SALAT = 3,\n    parameter integer MUT = 0,')
    c = sub1(c, 'ot_hbm_su_static_lane_pinreg_x #(.XS(XS),', 'ot_hbm_su_static_lane_pinreg_xb #(.SMLAT(SMLAT),.SALAT(SALAT),.MUT(MUT),.XS(XS),')
    open(f'{out}/ot_hbm_su_pg_lane_full_x_core.sv', 'w').write(c)
print('ok vB(xd) MLAT', MLAT, 'CUTS', CUTS, 'ALAT', ALAT, 'fullx' if fin else '')
