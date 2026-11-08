#!/usr/bin/env python3
"""HBM-CONS-2/SUK 11-06: conservative vK RTL of ot_hbm_su_pg_lane_exp_x_core and ot_hbm_su_pg_lane_full_x_core.

Runs results/die_hbm_1106/sux/gen_lane_xd.py (MLAT 7 = C1+C2+C3+C5, ALAT 5, SFU seam 4 / 3) and then:
  lane adder ALAT 5 -> 6: one plain input register stage (v, a, b) in front of ot_hdc_fp32_add_lat5, in ot_hdc_qadd_lat_xb only.
                  The routed full_x vD worst path (-235 ps) is u_dca line -> operand mux -> adder decode/compare -> u_ad u_ca;
                  this cut splits the operand mux from the adder's A1 decode.  Same arithmetic, one edge later.
  The lane's ALAT trap is widened to 3..6.  SFU seam keeps SMLAT 4 / SALAT 3 (sfu_s core unchanged).  dM = 3, dA = 3:
PIN CYCLES (core ports, vs the old part-18 exp_x / full_x):
  write / reducer / fault / coll (lane_vm_*, lane_kv_*, lane_ro_*, lane_fault, lane_coll) +T = 4 dM + dA = +15
  SFU seam out (sx_v, sx_r, sx_fn) and return (sx_y_exp, sx_y_div, sx_fault) +S = 2 dM + dA = +9 (pair moves together)
  full_x side pipe out (lane_side_v, lane_side_x) and return (lane_side_y) +S = +9 (pair moves together)
  all other ports 0.  (vs gen_lane_xd vB: +1 / +1 / +1.)

    gen_lane_xk.py REPO OUTDIR [FULLX_CORE_IN]
"""
import os, subprocess, sys
repo, out = sys.argv[1:3]
fin = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
subprocess.run([sys.executable, '-I', f'{repo}/results/die_hbm_1106/sux/gen_lane_xd.py', repo, out] + ([fin] if fin else []), check=True)


def sub1(txt, a, b):
    assert txt.count(a) == 1, (a[:80], txt.count(a))
    return txt.replace(a, b)


f = f'{out}/ot_hbm_su_static_lane_xb.sv'
t = open(f).read()
t = sub1(t, '    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 5) begin : g_bad_alat\n'
            '        ot_hdc_v41x_vec_lane_ALAT_must_be_3_to_5_and_at_most_MLAT u_trap ();',
         '    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 6) begin : g_bad_alat\n'
         '        ot_hdc_v41x_vec_lane_ALAT_must_be_3_to_6_and_at_most_MLAT u_trap ();')
t = sub1(t, "    end else begin : g_q\n        ot_hdc_qadd_lat #(.KEEP(KEEP), .LAT(LAT)) u (",
         "    end else if (KEEP != 0 && LAT == 6) begin : g_keep6\n"
         "        // HBM-CONS-2/SUK 11-06 vK: LAT 6 = one input register stage + the LAT-5 unit\n"
         "        wire [1:0] err;\n"
         "        wire vo, v_r;\n"
         "        wire [31:0] a_r, b_r;\n"
         "        ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_iv (.clk(clk), .rst_n(rst_n), .d(v), .q(v_r));\n"
         "        ot_hdc_delay #(.W(32), .D(1)) u_ia (.clk(clk), .rst_n(rst_n), .d(a), .q(a_r));\n"
         "        ot_hdc_delay #(.W(32), .D(1)) u_ib (.clk(clk), .rst_n(rst_n), .d(b), .q(b_r));\n"
         "        ot_hdc_fp32_add_lat5 u (.clk(clk), .rst_n(rst_n), .valid_in(v_r), .a(a_r), .b(b_r), .y(y), .err(err), .valid_out(vo));\n"
         "        assign fault = vo && (err != 2'd0);\n"
         "    end else begin : g_q\n        ot_hdc_qadd_lat #(.KEEP(KEEP), .LAT(LAT)) u (")
open(f, 'w').write(t)
HDR = '// then HBM-CONS-2/SUK 11-06 vK (gen_lane_xk.py): ALAT 6 (input register + LAT-5 add). Do not edit.'
for m in ('exp_x', 'full_x') if fin else ('exp_x',):
    f = f'{out}/ot_hbm_su_pg_lane_{m}_core.sv'
    c = open(f).read()
    c = sub1(c, '    parameter integer ALAT = 5,', '    parameter integer ALAT = 6,')
    c = sub1(c, 'seam depths 4 / 3. Do not edit.', 'seam depths 4 / 3,\n' + HDR)
    open(f, 'w').write(c)
print('ok vK MLAT 7 ALAT 6')
