#!/usr/bin/env python3
"""HBM-FORM-SPLIT-13-EXPX 11-06: vC (RE-FORM) of ot_hbm_su_pg_lane_exp_x_core: one more pipeline cut in every lane
multiplier and adder on top of the DIE-HBM-77-EXPX vB form.

Runs results/die_hbm_1105/expx_vb/gen_lane_xb.py (vB: MLAT 5 / ALAT 4, SFU seam depths 4 / 3) and then:
  lane multiplier  MLAT 5 -> 6: ot_hdc_fp32_mul_lat #(LAT 6) default cuts C1 + C2 + C3 (= lat5i plus C2, which splits
                   the four carry-save levels from the 48-bit prefix add; vB routed TT: s1_rows -> s2_prod -80 ps)
  lane adder       ALAT 4 -> 5: ot_hdc_fp32_add_lat5 default cuts A + B (= lat4i plus B, which splits the 28-bit
                   sum/difference from the normalise; vB routed TT: s1_big -> s2_val -37 ps, s1_small -> s2_val -18)
  Both units are existing bit-identical cut variants of the same binary32 datapath (no new arithmetic).
  The lane's ALAT trap is widened to 3..5; the adder goes through ot_hdc_qadd_lat_xb (defined in the generated lane
  file: LAT 5 -> ot_hdc_fp32_add_lat5, else ot_hdc_qadd_lat), so the shared rtl/hdc wrappers are unchanged.
  The SFU seam keeps SMLAT 4 / SALAT 3 (sfu_s core unchanged).  dM = 2, dA = 2, so (gen_lane_xb.py formulas):
PIN CYCLES (core ports, vs the old part-18 exp_x):  write / reducer / fault / coll (vm_*, kv_*, ro_*, fault, coll) +T = 4 dM
  + dA = +10; SFU seam out (sx_v, sx_r, sx_fn) and return (sx_y_exp, sx_y_div, sx_fault) +S = 2 dM + dA = +6; all others 0.
  (vs vB: write side +5 more, seam +3 more.)

    gen_lane_xc.py REPO OUTDIR
"""
import os, subprocess, sys
repo, out = sys.argv[1:3]
MLAT, ALAT = 6, 5
os.makedirs(out, exist_ok=True)
subprocess.run([sys.executable, '-I', f'{repo}/results/die_hbm_1105/expx_vb/gen_lane_xb.py', repo, out], check=True)


def sub1(txt, a, b):
    assert txt.count(a) == 1, (a[:80], txt.count(a))
    return txt.replace(a, b)


f = f'{out}/ot_hbm_su_static_lane_xb.sv'
t = open(f).read()
t = sub1(t, '    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 4) begin : g_bad_alat\n'
            '        ot_hdc_v41x_vec_lane_ALAT_must_be_3_or_4_and_at_most_MLAT u_trap ();',
         '    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 5) begin : g_bad_alat\n'
         '        ot_hdc_v41x_vec_lane_ALAT_must_be_3_to_5_and_at_most_MLAT u_trap ();')
assert t.count('ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT))') == 2
t = t.replace('ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT))', 'ot_hdc_qadd_lat_xb #(.KEEP(K), .LAT(ALAT))')
t = t.replace('Do not edit.\n', 'Do not edit.\n// HBM-FORM-SPLIT-13-EXPX 11-06 vC: post-patched by results/die_hbm_1106/expx_vc/gen_lane_xc.py (ALAT 5, '
              'ot_hdc_qadd_lat_xb).\n', 1)
t += '''
// HBM-FORM-SPLIT-13-EXPX 11-06 vC: ot_hdc_qadd_lat with the LAT-5 keep-prefix adder (ot_hdc_fp32_add_lat5: cuts A + B of
// rtl/hdc/ot_hdc_fp32_add_lat.sv, bit-identical to the LAT-3 unit); every other (KEEP, LAT) is ot_hdc_qadd_lat itself.
module ot_hdc_qadd_lat_xb #(
    parameter integer KEEP = 0,
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
    generate if (KEEP != 0 && LAT == 5) begin : g_keep5
        wire [1:0] err;
        wire vo;
        ot_hdc_fp32_add_lat5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else begin : g_q
        ot_hdc_qadd_lat #(.KEEP(KEEP), .LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y), .fault(fault));
    end endgenerate
endmodule
'''
open(f, 'w').write(t)

f = f'{out}/ot_hbm_su_pg_lane_exp_x_core.sv'
c = open(f).read()
c = sub1(c, '    parameter integer MLAT = 5,         // DIE-HBM-77-EXPX vB: lat5i input-cut multiplier\n'
            '    parameter integer ALAT = 4,         // lat4i input-cut add\n',
         f'    parameter integer MLAT = {MLAT},         // HBM-FORM-SPLIT-13-EXPX vC: LAT-6 multiplier (C1 + C2 + C3)\n'
         f'    parameter integer ALAT = {ALAT},         // LAT-5 add (A + B)\n')
c = sub1(c, 'MLAT 5 / ALAT 4 lane, seam depths 4 / 3. Do not edit.',
         'MLAT 5 / ALAT 4 lane, seam depths 4 / 3,\n'
         '// then HBM-FORM-SPLIT-13-EXPX 11-06 vC (results/die_hbm_1106/expx_vc/gen_lane_xc.py): MLAT 6 / ALAT 5. Do not edit.')
open(f, 'w').write(c)
print('ok vC MLAT', MLAT, 'ALAT', ALAT)
