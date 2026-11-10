"""Generate rtl/dsrom_sys/s81_svc/ot_s81_svc_fp32_f12_cs.sv from rtl/hdc/ot_hdc_fp32_f12.sv (read only).

DIE-S81-85 svc census (COORD loopgap-153x-1109 + 11-10 ruling): census-safe S81 copies of the f12 binary32 multiply
and add.  Same function, same latency, same CUTS; only cut bits above 64 load pins get kept replicas.
Usage: python3 gen_f12_cs.py REPO_ROOT
"""
import re, sys
from pathlib import Path

root = Path(sys.argv[1])
src = (root / 'rtl/hdc/ot_hdc_fp32_f12.sv').read_text()


def block(name):
    m = re.search(r'^module ' + name + r' #\(.*?^endmodule\n', src, re.M | re.S)
    assert m, name
    return m.group(0)


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old))
    return text.replace(old, new)


mul = block('ot_hdc_fp32_mul_f12')
mul = sub(mul, 'module ot_hdc_fp32_mul_f12 #(\n    parameter integer CUTS = 8\'b01101010\n)',
          'module ot_s81_svc_mul_f12_cs #(\n    parameter integer CUTS = 8\'b01101010,\n'
          '    parameter integer YXR = 0          // yx: kept replica of y (0: none, = y; 1: y[30:23]; 2: all 32 bits); 3: + yx2, a second full replica)\n)')
mul = sub(mul, '    output reg         valid_out\n);',
          '    output reg         valid_out,\n    output wire [31:0] yx,\n    output wire [31:0] yx2\n);\n'
          '    generate if (((CUTS / 32) % 2) != 1) begin : g_bad\n'
          '        $error("ot_s81_svc_mul_f12_cs needs the K5 cut");\n'
          '    end endgenerate')
# kept replicas of the K5 cut bits above 64 loads: s2_sh (r[96..101]) per output slice of the subnormal shift
# (built MSB stage first, so a slice's stage widths follow its own bits; sh[5] x2 per slice) and s2_prod[47] (r[175])
mul = sub(mul, '    // ---- select, subnormal shift, round / sticky bits; both encode exponents',
          '    // census-safe replicas (same D as u_k5 r[96..99] / r[175], plain flops like the cut data bits)\n'
          '    (* keep = 1 *) reg [5:0] sh_b, sh_c, sh_d;     // = s2_sh, slices 1..3 (slice 0: s2_sh)\n'
          '    (* keep = 1 *) reg [3:0] sh5_x;               // = s2_sh[5], the upper half of each slice\'s first stage\n'
          '    (* keep = 1 *) reg       top_b, top_c;\n'
          '    always @(posedge clk) begin sh_b <= q_sh; sh_c <= q_sh; sh_d <= q_sh; sh5_x <= {4{q_sh[5]}}; top_b <= prod[47]; top_c <= prod[47]; end\n'
          '    // ---- select, subnormal shift, round / sticky bits; both encode exponents')
mul = sub(mul, '    wire is_sub = top ? s2_sub47 : s2_sub46;\n    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;',
          '    wire is_sub = top_c ? s2_sub47 : s2_sub46;\n    wire signed [11:0] fl = top_c ? s2_fl47 : s2_fl46;')
mul = sub(mul, '    wire [47:0] sub_shifted = s2_prod >> s2_sh;\n    wire [23:0] s_main = sub_shifted[23:0];',
          '    wire [5:0] sub_0, sub_1, sub_2, sub_3;            // = (s2_prod >> s2_sh)[23:0], six bits each\n'
          '    ot_s81_svc_shr48_slice_cs #(.A(0))  u_sb0 (.p(s2_prod), .sh(s2_sh), .sh5x(sh5_x[0]), .o(sub_0));\n'
          '    ot_s81_svc_shr48_slice_cs #(.A(6))  u_sb1 (.p(s2_prod), .sh(sh_b),  .sh5x(sh5_x[1]), .o(sub_1));\n'
          '    ot_s81_svc_shr48_slice_cs #(.A(12)) u_sb2 (.p(s2_prod), .sh(sh_c),  .sh5x(sh5_x[2]), .o(sub_2));\n'
          '    ot_s81_svc_shr48_slice_cs #(.A(18)) u_sb3 (.p(s2_prod), .sh(sh_d),  .sh5x(sh5_x[3]), .o(sub_3));\n'
          '    wire [23:0] s_main = {sub_3, sub_2, sub_1, sub_0};')
mul = sub(mul, '    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];\n    wire n_rb = top ? s2_prod[23] : s2_prod[22];\n    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);',
          '    wire [23:0] n_main = {top_b ? s2_prod[47:36] : s2_prod[46:35], top ? s2_prod[35:24] : s2_prod[34:23]};\n    wire n_rb = top_b ? s2_prod[23] : s2_prod[22];\n    wire n_st = top_b ? (|s2_prod[22:0]) : (|s2_prod[21:0]);')
mul = sub(mul, '    wire [7:0]  fa = top ? fa47 : fa46, fb = top ? fb47 : fb46;\n'
               '    wire        oa = top ? oa47 : oa46, ob = top ? ob47 : ob46;',
          '    wire [7:0]  fa = top_c ? fa47 : fa46, fb = top_c ? fb47 : fb46;\n'
          '    wire        oa = top_c ? oa47 : oa46, ob = top_c ? ob47 : ob46;')
mul = sub(mul, '            else begin y <= (code[30:0] == 31\'d0) ? 32\'d0 : code; err <= E_NONE; end\n        end\n    end\n',
          '            else begin y <= (code[30:0] == 31\'d0) ? 32\'d0 : code; err <= E_NONE; end\n        end\n    end\n'
          '    wire [31:0] y_nx = (o_byp || over || code[30:0] == 31\'d0) ? 32\'d0 : code;   // = y next\n'
          '    genvar yb;\n'
          '    generate for (yb = 0; yb < 32; yb = yb + 1) begin : g_yx\n'
          '        if (YXR >= 2 || (YXR == 1 && yb >= 23 && yb <= 30)) begin : g_r\n'
          '            (* keep = 1 *) reg q;                 // = y[yb], cycle for cycle\n'
          '            always @(posedge clk `OT_ARST(rst_n)) begin\n'
          '                if (!rst_n) q <= 1\'b0;\n'
          '                else q <= y_nx[yb];\n'
          '            end\n'
          '            assign yx[yb] = q;\n'
          '        end else begin : g_w\n'
          '            assign yx[yb] = y[yb];\n'
          '        end\n'
          '        if (YXR == 3) begin : g_r2\n'
          '            (* keep = 1 *) reg q;                 // = y[yb], cycle for cycle\n'
          '            always @(posedge clk `OT_ARST(rst_n)) begin\n'
          '                if (!rst_n) q <= 1\'b0;\n'
          '                else q <= y_nx[yb];\n'
          '            end\n'
          '            assign yx2[yb] = q;\n'
          '        end else begin : g_w2\n'
          '            assign yx2[yb] = y[yb];\n'
          '        end\n'
          '    end endgenerate\n')

add = block('ot_hdc_fp32_add_f12')
add = sub(add, 'module ot_hdc_fp32_add_f12 #(', 'module ot_s81_svc_add_f12_cs #(')
add = sub(add, '    output reg         valid_out\n);',
          '    output reg         valid_out\n);\n'
          '    generate if (((CUTS / 8) % 2) != 1) begin : g_bad\n'
          '        $error("ot_s81_svc_add_f12_cs needs the K3 cut");\n'
          '    end endgenerate')
# kept replicas of the K3 cut bits above 64 loads: lz[4:0] (u_k3 r[1..5]) per third of the cancellation shift, and
# w_sub for the high half of the value select
add = sub(add, '    // ---- the cancellation shift, the exponent adjust',
          '    (* keep = 1 *) reg [4:0] lzb, lzc;              // = u_k3 lz[4:0] (r[5:1]), census-safe replicas\n'
          '    (* keep = 1 *) reg       sub_b;                 // = u_k3 w_sub, census-safe replica\n'
          '    always @(posedge clk) begin lzb <= lz_w[4:0]; lzc <= lz_w[4:0]; sub_b <= t_sub; end\n'
          '    // ---- the cancellation shift, the exponent adjust')
add = sub(add, '    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];',
          '    wire [26:0] sv_0 = w_dif[26:0] << lz[4:0];\n'
          '    wire [26:0] sv_1 = w_dif[26:0] << lzb;\n'
          '    wire [26:0] sv_2 = w_dif[26:0] << lzc;\n'
          '    wire [26:0] sub_val = {sv_2[26:18], sv_1[17:9], sv_0[8:0]};')
add = sub(add, '            w_sub ? sub_val : w_add}), .q(q4));',
          '            sub_b ? sub_val[26:13] : w_add[26:13], w_sub ? sub_val[12:0] : w_add[12:0]}), .q(q4));')


lat = (root / 'rtl/hdc/ot_hdc_fastfp_lat_f12.sv').read_text()


def lblock(name):
    m = re.search(r'^module ' + name + r' #\(.*?^endmodule\n', lat, re.M | re.S)
    assert m, name
    return m.group(0)


qm = lblock('ot_hdc_qmul_lat')
qm = sub(qm, 'module ot_hdc_qmul_lat #(\n    parameter integer LAT = 3\n)',
         'module ot_s81_svc_qmul_lat_cs #(\n    parameter integer LAT = 5,\n    parameter integer YXR = 0\n)')
qm = sub(qm, '    output wire        fault\n);', '    output wire        fault,\n    output wire [31:0] yx,\n    output wire [31:0] yx2\n);')
qm = sub(qm, '        ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));',
         '        ot_s81_svc_mul_f12_l5_cs #(.YXR(YXR)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),\n'
         '            .valid_out(vo), .yx(yx), .yx2(yx2));')
qm = sub(qm, '    assign fault = vo && (err != 2\'d0);\nendmodule',
         '    generate if (LAT != 5) begin : g_nyx\n        assign yx = y; assign yx2 = y;\n'
         '        $error("ot_s81_svc_qmul_lat_cs: census-safe unit only at LAT 5");\n    end endgenerate\n'
         '    assign fault = vo && (err != 2\'d0);\nendmodule')
qa = lblock('ot_hdc_qadd_lat')
qa = sub(qa, 'module ot_hdc_qadd_lat #(\n    parameter integer KEEP = 0,\n    parameter integer LAT = 3\n)',
         'module ot_s81_svc_qadd_lat_cs #(\n    parameter integer KEEP = 1,\n    parameter integer LAT = 4\n)')
qa = sub(qa, '        ot_hdc_fp32_add_f12_l4 u (', '        ot_s81_svc_add_f12_l4_cs u (')
qa = sub(qa, '    assign fault = vo && (err != 2\'d0);\nendmodule',
         '    generate if (KEEP != 1 || LAT != 4) begin : g_bad\n'
         '        $error("ot_s81_svc_qadd_lat_cs: census-safe unit only at KEEP 1 / LAT 4");\n    end endgenerate\n'
         '    assign fault = vo && (err != 2\'d0);\nendmodule')
tops = ('// fixed tops (as ot_hdc_fp32_mul_f12_l5 / ot_hdc_fp32_add_f12_l4)\n'
        'module ot_s81_svc_mul_f12_l5_cs #(parameter integer YXR = 0) (input wire clk, rst_n, valid_in, input wire [31:0] a, b,\n'
        '    output wire [31:0] y, output wire [1:0] err, output wire valid_out, output wire [31:0] yx, output wire [31:0] yx2);\n'
        '    ot_s81_svc_mul_f12_cs #(.CUTS(8\'b01101010), .YXR(YXR)) u (.*);\nendmodule\n'
        'module ot_s81_svc_add_f12_l4_cs (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,\n'
        '    output wire [1:0] err, output wire valid_out);\n'
        '    ot_s81_svc_add_f12_cs #(.CUTS(6\'b101010)) u (.*);\nendmodule\n'
        'module ot_s81_svc_add_f12_l5x_cs (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,\n'
        '                                  output wire [1:0] err, output wire valid_out);\n'
        '    ot_s81_svc_add_f12_cs #(.CUTS(7\'b1101010)) u (.*);\nendmodule\n\n'
        '// o = (p >> sh)[A+W-1:A], log shifter with the 32 stage first (each stage only as wide as this slice needs);\n'
        '// sh5x = sh[5] (a kept copy) selects the first stage\'s upper 16 positions\n'
        'module ot_s81_svc_shr48_slice_cs #(parameter integer A = 0, W = 6) (input wire [47:0] p, input wire [5:0] sh,\n'
        '                                                                 input wire sh5x, output wire [W-1:0] o);\n'
        '    wire [63:0] t6 = {16\'d0, p};\n'
        '    wire [63:0] t5, t4, t3, t2, t1, t0;\n'
        '    genvar i;\n'
        '    generate for (i = 0; i < 64; i = i + 1) begin : g_s\n'
        '        if (i < 32) begin : g_5\n'
        '            assign t5[i] = ((i < A + 16) ? sh[5] : sh5x) ? t6[i + 32] : t6[i];\n'
        '        end else begin : g_5z\n'
        '            assign t5[i] = sh[5] ? 1\'b0 : t6[i];\n'
        '        end\n'
        '        assign t4[i] = (sh[4] && i + 16 < 64) ? t5[(i + 16) % 64] : (sh[4] ? 1\'b0 : t5[i]);\n'
        '        assign t3[i] = (sh[3] && i + 8 < 64)  ? t4[(i + 8) % 64]  : (sh[3] ? 1\'b0 : t4[i]);\n'
        '        assign t2[i] = (sh[2] && i + 4 < 64)  ? t3[(i + 4) % 64]  : (sh[2] ? 1\'b0 : t3[i]);\n'
        '        assign t1[i] = (sh[1] && i + 2 < 64)  ? t2[(i + 2) % 64]  : (sh[1] ? 1\'b0 : t2[i]);\n'
        '        assign t0[i] = (sh[0] && i + 1 < 64)  ? t1[(i + 1) % 64]  : (sh[0] ? 1\'b0 : t1[i]);\n'
        '    end endgenerate\n'
        '    assign o = t0[A +: W];\nendmodule\n\n'
        '// drop-ins for ot_hdc_qmul_lat / ot_hdc_qadd_lat (rtl/hdc/ot_hdc_fastfp_lat_f12.sv, copied, unit swapped)\n'
        + qm + '\n' + qa)
i = src.index('`ifndef OT_ARST')
j = src.index('`endif\n', src.index('`endif\n', i) + 1) + len('`endif\n')
hdr = src[i:j]
out = ['`timescale 1ns/1ps\n',
       '// GENERATED by tools/s81_dv/svc_cs/gen_f12_cs.py from rtl/hdc/ot_hdc_fp32_f12.sv (unchanged there); do not edit.\n',
       '// DIE-S81-85 svc census 11-10 (COORD loopgap-153x-1109, 11-10 ruling): census-safe S81 copies of the f12 binary32\n',
       '// multiply / add for the S81 svc provider boxes only.  Same function, same latency, same CUTS; only the cut bits above\n',
       '// 64 load pins get a kept replica (mul: K5 sh x3 + sh[5] x4 + prod[47] x2, y optional; add: K3 lz[4:0] x2 + sub).  Needs rtl/hdc/ot_hdc_fp32_f12.sv\n',
       '// (ot_hdc_f12_cut), ot_hdc_fastfp.sv and ot_hdc_prefix.sv in the source list.  EQ: tools/s81_dv/svc_cs/eq_cs.sh.\n',
       hdr, '\n', mul, '\n', add, '\n',
       tops]
dst = root / 'rtl/dsrom_sys/s81_svc/ot_s81_svc_fp32_f12_cs.sv'
dst.write_text(''.join(out))
print('wrote', dst)
