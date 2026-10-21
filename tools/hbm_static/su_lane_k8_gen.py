#!/usr/bin/env python3
"""HBM-KIND8 (10-20): native-32 lane + pin-register copies for the KIND1/KIND2 lane leaves.

Reads the generated lane (ot_hbm_su_static_lane.sv) and pin-register wrapper (ot_hbm_su_static_lane_pinreg.sv) and
writes k8/ot_hbm_su_static_lane_k8.sv + k8/ot_hbm_su_static_lane_pinreg_k8.sv: the same arithmetic, the same edges,
with kept same-edge register copies (keep_hierarchy modules ot_su_kff_k8 / ot_su_kffr_k8) wherever one register drove
a wide select / enable / mask (pre-gate native census 10-20: s_q ld 604, lane_id 320, ldp_v 483, bank 240, g2_v 262,
cx_imm3 sign 207, ca_ad 88, cs_sfu 70, cm_m1 60, ...) and the k8 multiplier / exp.  Every patch is an exact,
counted replacement (the script refuses on drift).  Shared files are not edited (closed views keep their sources).
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
A = ROOT / 'rtl/hbm_accel/generic/adapters/static_su/arithmetic'


def sub(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        sys.exit(f'su_lane_k8_gen: expected {n} x {old[:80]!r}, found {c}')
    return s.replace(old, new)


KFF = '''
// HBM-KIND8 kept same-edge register copies; HBM-KIND9: each copy is an ot_k9_fam copy family (3 identical members per bit,
// loads balanced <= 32 by the kit's ot_rst_copies splitter; it3 census: single copies drove up to 84 loads)
module ot_su_kff_k8 #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    ot_k9_fam #(.W(W), .N(3)) u_f (.clk(clk), .d(d), .q(q));
endmodule
// HBM-KIND9: reset copies as ot_k9_famr copy families (it3: ldp_v / g2_v copies 48 loads)
module ot_su_kffr_k8 #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    ot_k9_famr #(.W(W), .N(3)) u_f (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
// one kept copy of an enabled register (q <= en ? d : q)
(* keep_hierarchy = "yes" *)
module ot_su_kffe_k8 #(parameter integer W = 1) (input wire clk, input wire en, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep = 1 *) reg [W-1:0] r;
    always @(posedge clk) if (en) r <= d;
    assign q = r;
endmodule
'''

# copies the pin-register wrapper supplies (field, width, copies)
COPIES = [('lane_id', 11, 5), ('cx_imm3', 32, 8), ('ca_ad', 3, 4), ('cs_sfu', 3, 2), ('cm_m1', 3, 2),
          ('cm_m2', 2, 2), ('co_rnd', 1, 2), ('ce_e2', 2, 2), ('cs_e1', 3, 2), ('cp_m1', 3, 4), ('ci_sfu', 3, 4)]
NS = 4                    # insertion-line slices (each slice's load select reads its own v / sel copy)


def ins(src, old_mod, new_mod):
    """insertion line with NS slices: v / sel arrive as NS copies; slice j's load / bypass selects use copy j"""
    s = sub(src, f'module {old_mod} #(', f'module {new_mod} #(\n    parameter integer NS = {NS},             // HBM-KIND8: v / sel copies, one per data slice')
    s = sub(s, '''    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice''', '''    input  wire [NS-1:0]   v,                // HBM-KIND8: NS kept copies of v
    input  wire [NS*K-1:0] sel,              // NS copies of the one-hot depth choice''')
    s = sub(s, '''                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;''', '''                    wire [NS-1:0] ldv;
                    wire [W-1:0]  nxt;
                    for (genvar j = 0; j < NS; j = j + 1) begin : g_sl
                        localparam integer LO = j * ((W + NS - 1) / NS);
                        localparam integer HI = (LO + (W + NS - 1) / NS > W) ? W : LO + (W + NS - 1) / NS;
                        assign ldv[j] = v[j] && has(p, sel[j*K +: K]);
                        if (HI > LO) begin : g_d
                            assign nxt[HI-1:LO] = ldv[j] ? d[HI-1:LO] : nx[HI-1:LO];
                        end
                    end
                    wire ld = ldv[0];
                    assign cl[p] = ld && nxv;''')
    s = sub(s, 'r[p] <= ld ? d : nx;', 'r[p] <= nxt;', 2)
    s = sub(s, '''            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];''', '''            wire [NS-1:0] nowv;
            for (genvar j = 0; j < NS; j = j + 1) begin : g_q
                localparam integer LO = j * ((W + NS - 1) / NS);
                localparam integer HI = (LO + (W + NS - 1) / NS > W) ? W : LO + (W + NS - 1) / NS;
                assign nowv[j] = v[j] && has(0, sel[j*K +: K]);
                if (HI > LO) begin : g_d
                    assign q[HI-1:LO] = nowv[j] ? d[HI-1:LO] : r[1][HI-1:LO];
                end
            end
            wire now = nowv[0];
            assign vo = now || rv[1];''')
    s = sub(s, '            assign vo = v; assign q = d; assign coll = 1\'b0; assign busy = 1\'b0;',
            '            assign vo = v[0]; assign q = d; assign coll = 1\'b0; assign busy = 1\'b0;')
    return s

NLD, NBK = 16, 5          # ld strobe copies (5 streams x 3 groups + 1), bank copies (one per stream)


def lane():
    s = (A / 'ot_hbm_su_static_lane.sv').read_text()
    s = sub(s, '// Generated by tools/hbm_static/su_arith_generate.py; native arithmetic unchanged.\n',
            '// GENERATED by tools/hbm_static/su_lane_k8_gen.py from ot_hbm_su_static_lane.sv (HBM-KIND8 native-32 copies); do not edit.\n')
    s = sub(s, 'module ot_hbm_su_static_lane #(', 'module ot_hbm_su_static_lane_k8 #(')
    # ---- extra copy ports
    ports = ''.join(f'    input  wire [{c}*{w}-1:0] {f}_c,     // HBM-KIND8: {c} kept pin-register copies of {f}\n'
                    for f, w, c in COPIES)
    ports += f'    input  wire [{NLD}-1:0] ld_x,     // HBM-KIND8: kept copies of the ld strobe\n'
    ports += f'    input  wire [{NBK}-1:0] bank_x,   // HBM-KIND8: kept copies of bank (one per stream)\n'
    s = sub(s, '    input  wire              ld,\n', ports + '    input  wire              ld,\n')
    # ---- bank select of the offset sums: copy gs per stream
    s = sub(s, '.b(bank ? off1[gs] : off0[gs])', '.b(bank_x[gs] ? off1[gs] : off0[gs])')
    # ---- offset load (g_ld3k): ld / lane_id / ldp_v / ldq copies
    s = sub(s, '''        reg          ldp_v, ldq_v, ldp_bank, ldq_bank;
        always @(posedge clk_stage[0] `OT_SU_ARST(rst_stage_n[0])) begin
            if (!rst_stage_n[0]) begin ldp_v <= 1'b0; ldq_v <= 1'b0; end
            else begin ldp_v <= ld_e; ldq_v <= ldp_v; end
        end
        always @(posedge clk_stage[0]) begin
            if (ld_e) ldp_bank <= ldbank_e;
            if (ldp_v) ldq_bank <= ldp_bank;
        end
        genvar ss, jj, kk;''', f'''        // HBM-KIND8: ldp_v as 11 kept copies (10 q-register enables, 1 for ldq), ldq_v / ldq_bank one pair per stream
        wire [10:0]  ldp_vc;
        wire [9:0]   ldq_vc, ldq_bc;                  // HBM-KIND9: one pair per (stream, AW half) (it3: off0/off1 enables 48)
        wire         ldp_bank;
        for (genvar c = 0; c < 11; c = c + 1) begin : g_ldpv
            ot_su_kffr_k8 u_k (.clk(clk_stage[0]), .rst_n(rst_stage_n[0]), .d(ld_x[{NLD-1}]), .q(ldp_vc[c]));
        end
        for (genvar c = 0; c < 10; c = c + 1) begin : g_ldq
            ot_su_kffr_k8 u_v (.clk(clk_stage[0]), .rst_n(rst_stage_n[0]), .d(ldp_vc[10]), .q(ldq_vc[c]));
            ot_su_kffe_k8 u_b (.clk(clk_stage[0]), .en(ldp_vc[10]), .d(ldp_bank), .q(ldq_bc[c]));
        end
        reg ldp_bank_r;
        always @(posedge clk_stage[0]) if (ld_x[{NLD-1}]) ldp_bank_r <= ldbank_e;
        assign ldp_bank = ldp_bank_r;
        genvar ss, jj, kk;''')
    s = sub(s, '''        always @(posedge clk_stage[0])
            if (ldq_v)
                for (s = 0; s < 5; s = s + 1)
                    if (ldq_bank) off1[s] <= s_bus[s*AW +: AW]; else off0[s] <= s_bus[s*AW +: AW];''',
            '''        always @(posedge clk_stage[0])
            for (s = 0; s < 5; s = s + 1) begin
                if (ldq_vc[2*s]) begin
                    if (ldq_bc[2*s]) off1[s][AW/2-1:0] <= s_bus[s*AW +: AW/2]; else off0[s][AW/2-1:0] <= s_bus[s*AW +: AW/2];
                end
                if (ldq_vc[2*s+1]) begin
                    if (ldq_bc[2*s+1]) off1[s][AW-1:AW/2] <= s_bus[s*AW+AW/2 +: AW-AW/2]; else off0[s][AW-1:AW/2] <= s_bus[s*AW+AW/2 +: AW-AW/2];
                end
            end''')
    s = sub(s, "assign t[kk*AW +: AW] = lane_id[LO + kk] ? ldc_e[(ss*LN + LO + kk)*AW +: AW] : {AW{1'b0}};",
            "assign t[kk*AW +: AW] = lane_id_c[ss*11 + LO + kk] ? ldc_e[(ss*LN + LO + kk)*AW +: AW] : {AW{1'b0}};")
    s = sub(s, '''                if (ld_e) begin p0 <= grp[0 +: AW]; p1 <= grp[AW +: AW]; p2 <= grp[2*AW +: AW]; end
                if (ldp_v) begin q01 <= s_01; q2 <= p2; end''',
            '''                if (ld_x[ss*3 + 0]) p0 <= grp[0 +: AW];
                if (ld_x[ss*3 + 1]) p1 <= grp[AW +: AW];
                if (ld_x[ss*3 + 2]) p2 <= grp[2*AW +: AW];
                if (ldp_vc[2*ss + 0]) q01 <= s_01;
                if (ldp_vc[2*ss + 1]) q2 <= p2;''')
    # ---- G2: g2_v as 6 kept copies (the read-address / source / tag selects)
    s = sub(s, '''        if (!rst_stage_n[0]) begin g1_v <= 1'b0; g2_v <= 1'b0; end
        else begin g1_v <= fg_v && fg_g; g2_v <= g1_v; end
    end''', '''        if (!rst_stage_n[0]) begin g1_v <= 1'b0; g2_v <= 1'b0; end
        else begin g1_v <= fg_v && fg_g; g2_v <= g1_v; end
    end
    // HBM-KIND8: g2_v copies: [0] A, [1] B, [2] C, [3] D, [4] source + pair, [5] tag
    wire [5:0] g2_vc;
    for (genvar c = 0; c < 6; c = c + 1) begin : g_g2v
        ot_su_kffr_k8 u_k (.clk(clk_stage[0]), .rst_n(rst_stage_n[0]), .d(g1_v), .q(g2_vc[c]));
    end''')
    s = sub(s, '''    wire          mr_v  = mr_nv || g2_v;
    wire [AW-1:0] mr_a  = g2_v ? g2_a : f_a;
    wire [AW-1:0] mr_c  = (g2_v ? g2_cpair : f_cpair) ? (mr_a ^ {{(AW-1){1'b0}}, 1'b1}) : (g2_v ? g2_c : f_c);
    wire [7:0]    mr_src = g2_v ? g2_src : f_src;
    assign rd_addr = {g2_v ? g2_d : f_d, mr_c, g2_v ? g2_b : f_b, mr_a};''',
            '''    wire          mr_v  = mr_nv || g2_v;
    wire [AW-1:0] mr_a  = g2_vc[0] ? g2_a : f_a;
    wire [AW-1:0] mr_c  = (g2_vc[4] ? g2_cpair : f_cpair) ? (mr_a ^ {{(AW-1){1'b0}}, 1'b1}) : (g2_vc[2] ? g2_c : f_c);
    wire [7:0]    mr_src = g2_vc[4] ? g2_src : f_src;
    assign rd_addr = {g2_vc[3] ? g2_d : f_d, mr_c, g2_vc[1] ? g2_b : f_b, mr_a};''')
    s = sub(s, '            tag[0] <= {g2_v ? g2_o : f_o, g2_v ? g2_par : f_par};',
            '            tag[0] <= {g2_vc[5] ? g2_o : f_o, g2_vc[5] ? g2_par : f_par};')
    # ---- G1 shift amount: two copies (low / high half of the scaled index)
    s = sub(s, '''    ot_hdc_kadd #(.W(AW), .K(K)) u_g2a (.a(g1_a), .b(vi_q[AW-1:0] << g1_sh), .cin(1'b0), .s(g2_sum), .cout(unused_c2));''',
            '''    wire [4:0] g1_sh2;                               // HBM-KIND8: kept copy of g1_sh for the upper half
    ot_su_kff_k8 #(.W(5)) u_g1sh (.clk(clk_stage[0]), .d(fg_sh), .q(g1_sh2));
    wire [AW-1:0] g_shl = vi_q[AW-1:0] << g1_sh, g_shh = vi_q[AW-1:0] << g1_sh2;
    ot_hdc_kadd #(.W(AW), .K(K)) u_g2a (.a(g1_a), .b({g_shh[AW-1:AW/2], g_shl[AW/2-1:0]}), .cin(1'b0), .s(g2_sum), .cout(unused_c2));''')
    # ---- X: x_a twice (compares / increment vs the PRE select)
    s = sub(s, '''        x_a <= rd_q[31:0]; x_b <= rd_q[63:32]; x_c <= rd_q[95:64]; x_d <= rd_q[127:96];
    end''', '''        x_a <= rd_q[31:0]; x_b <= rd_q[63:32]; x_c <= rd_q[95:64]; x_d <= rd_q[127:96];
    end
    wire [31:0] x_a2, x_a3, x_c2;                    // HBM-KIND8: kept copies: x_a2 PRE select, x_a3 BF16 candidates, x_c2 lo compare
    ot_su_kff_k8 #(.W(32)) u_xa2 (.clk(clk_stage[0]), .d(rd_q[31:0]), .q(x_a2));
    ot_su_kff_k8 #(.W(32)) u_xa3 (.clk(clk_stage[0]), .d(rd_q[31:0]), .q(x_a3));
    ot_su_kff_k8 #(.W(32)) u_xc2 (.clk(clk_stage[0]), .d(rd_q[95:64]), .q(x_c2));''')
    s = sub(s, '''    wire [31:0] a_t  = {x_a[31:16], 16'd0};''', '''    wire [31:0] a_t  = {x_a3[31:16], 16'd0};''')
    s = sub(s, '''    ot_hdc_kinc #(.W(16), .K(K)) u_au (.a(x_a[31:16]), .inc(1'b1), .y(a_hi1));''',
            '''    ot_hdc_kinc #(.W(16), .K(K)) u_au (.a(x_a3[31:16]), .inc(1'b1), .y(a_hi1));''')
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_cgl (.a(okey(x_c)), .b(okey(c_lo)), .ge(c_ge_lo));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_cgl (.a(okey(x_c2)), .b(okey(c_lo)), .ge(c_ge_lo));")
    # ---- PRE: imm3 copies [0] okey for the A compares, [1] A select, [2] C clip compares, [3] C select
    s = sub(s, '    wire [31:0] k_imm3 = okey(cx_imm3);', '''    // HBM-KIND8: 8 imm3 copies: 0 lex, 1 A select, 2 c_lo, 3 C select, 4 let, 5 leu, 6 le0, 7 clh / clo
    wire [31:0] imm3_0 = cx_imm3_c[0 +: 32], imm3_1 = cx_imm3_c[32 +: 32], imm3_2 = cx_imm3_c[64 +: 32],
                imm3_3 = cx_imm3_c[96 +: 32], imm3_4 = cx_imm3_c[128 +: 32], imm3_5 = cx_imm3_c[160 +: 32],
                imm3_6 = cx_imm3_c[192 +: 32], imm3_7 = cx_imm3_c[224 +: 32];
    wire [31:0] k_imm3 = okey(imm3_0), k_imm3c = okey(imm3_7), k_imm3t = okey(imm3_4), k_imm3u = okey(imm3_5),
                k_imm30 = okey(imm3_6);''')
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_let (.a(k_imm3), .b(okey(a_t)), .ge(le_t));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_let (.a(k_imm3t), .b(okey(a_t)), .ge(le_t));")
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_leu (.a(k_imm3), .b(okey(a_u)), .ge(le_u));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_leu (.a(k_imm3u), .b(okey(a_u)), .ge(le_u));")
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_le0 (.a(k_imm3), .b(32'h80000000), .ge(le_0));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_le0 (.a(k_imm30), .b(32'h80000000), .ge(le_0));")
    s = sub(s, '''    wire [31:0] a_mx = pre_a2(x_a, cx_arelu, cx_amin, cx_imm3, le_x, le_0);
    wire [31:0] a_mt = pre_a2(a_t, cx_arelu, cx_amin, cx_imm3, le_t, le_0);
    wire [31:0] a_mu = pre_a2(a_u, cx_arelu, cx_amin, cx_imm3, le_u, le_0);''',
            '''    wire [31:0] a_mx = pre_a2(x_a2, cx_arelu, cx_amin, imm3_1, le_x, le_0);
    wire [31:0] a_mt = pre_a2(a_t, cx_arelu, cx_amin, imm3_1, le_t, le_0);
    wire [31:0] a_mu = pre_a2(a_u, cx_arelu, cx_amin, imm3_1, le_u, le_0);''')
    s = sub(s, "    wire [31:0] c_lo = {1'b1, cx_imm3[30:0]};", "    wire [31:0] c_lo = {1'b1, imm3_2[30:0]};")
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_clh (.a(k_imm3), .b(okey(x_c)), .ge(c_le_hi));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_clh (.a(k_imm3c), .b(okey(x_c)), .ge(c_le_hi));")
    s = sub(s, "    ot_hdc_kge #(.W(32), .K(K)) u_clo (.a(k_imm3), .b(okey(c_lo)), .ge(c_lohi));",
            "    ot_hdc_kge #(.W(32), .K(K)) u_clo (.a(k_imm3c), .b(okey(c_lo)), .ge(c_lohi));")
    s = sub(s, "    wire [31:0] c_m = !cx_cclip ? x_c : c_ge_lo ? (c_le_hi ? x_c : cx_imm3) : (c_lohi ? c_lo : cx_imm3);",
            "    wire [31:0] c_m = !cx_cclip ? x_c : c_ge_lo ? (c_le_hi ? x_c : imm3_3) : (c_lohi ? c_lo : imm3_3);")
    # ---- insertion lines: v / sel copies (p_v x NS kept, v3 x NS kept; cp_m1 / ci_sfu pin copies)
    s = sub(s, '''        if (!rst_stage_n[0]) p_v <= 1'b0; else p_v <= x_v;
    end''', f'''        if (!rst_stage_n[0]) p_v <= 1'b0; else p_v <= x_v;
    end
    wire [{NS}-1:0] p_vc;                             // HBM-KIND8: kept copies of p_v for the M1 insertion line slices
    for (genvar c = 0; c < {NS}; c = c + 1) begin : g_pvc
        ot_su_kffr_k8 u_k (.clk(clk_stage[0]), .rst_n(rst_stage_n[0]), .d(x_v), .q(p_vc[c]));
    end''')
    s = sub(s, '''            ot_hdc_v41x_ins #(.W(T1W), .K(2), .DEPTHS({H_DIV, H_M}), .DMAX(19)) u_l1 (
                .clk(clk_stage[1]), .rst_n(rst_stage_n[1]), .v(p_v), .sel({p_div, !p_div}), .d({p_b, p_c, p_d, p_o, p_par}),''',
            f'''            wire [2*{NS}-1:0] l1_sel;
            for (genvar c = 0; c < {NS}; c = c + 1) begin : g_l1s
                wire dv = (cp_m1_c[3*c +: 3] == M1_DIVB) || (cp_m1_c[3*c +: 3] == M1_DIVIMM);
                assign l1_sel[2*c +: 2] = {{dv, !dv}};
            end
            ot_hdc_v41x_ins_k8 #(.W(T1W), .K(2), .DEPTHS({{H_DIV, H_M}}), .DMAX(19)) u_l1 (
                .clk(clk_stage[1]), .rst_n(rst_stage_n[1]), .v(p_vc), .sel(l1_sel), .d({{p_b, p_c, p_d, p_o, p_par}}),''')
    s = sub(s, '''    wire v3 = v3l[ALAT];''', f'''    wire v3 = v3l[ALAT];
    wire [{NS}-1:0] v3c;                              // HBM-KIND8: kept copies of v3 for the S insertion line slices
    for (genvar c = 0; c < {NS}; c = c + 1) begin : g_v3c
        ot_su_kffr_k8 u_k (.clk(clk_stage[3]), .rst_n(rst_stage_n[3]), .d(v3l[ALAT-1]), .q(v3c[c]));
    end''')
    s = sub(s, '''            if (FULL != 0) begin : g_full
                ot_hbm_su_static_ins #(''', f'''            wire [7*{NS}-1:0] l4_sel;
            for (genvar c = 0; c < {NS}; c = c + 1) begin : g_l4s
                wire [2:0] cf = ci_sfu_c[3*c +: 3];
                assign l4_sel[7*c +: 7] = {{cf == SFU_EGATE, cf == SFU_SPSQRT, cf == SFU_SQRT, cf == SFU_RSQRT,
                                           cf == SFU_SIGM || cf == SFU_SILU, cf == SFU_EXP, cf == SFU_NONE}};
            end
            wire [3*{NS}-1:0] l4_sel3;
            for (genvar c = 0; c < {NS}; c = c + 1) begin : g_l4t
                assign l4_sel3[3*c +: 3] = l4_sel[7*c +: 3];
            end
            if (FULL != 0) begin : g_full
                ot_hbm_su_static_ins_k8 #(''')
    s = sub(s, '''                    .v(v3), .sel(sel), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4), .coll(c4), .busy());''',
            '''                    .v(v3c), .sel(l4_sel), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4), .coll(c4), .busy());''')
    s = sub(s, '''                ot_hbm_su_static_ins #(.W(T4W), .K(3), .DEPTHS({H_SIG, H_EXP, 16'd0}), .DMAX(D_SIG)) u_l4 (''',
            '''                ot_hbm_su_static_ins_k8 #(.W(T4W), .K(3), .DEPTHS({H_SIG, H_EXP, 16'd0}), .DMAX(D_SIG)) u_l4 (''')
    s = sub(s, '''                    .v(v3), .sel(sel[2:0]), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4),''',
            '''                    .v(v3c), .sel(l4_sel3), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4),''')
    # ---- stage-4 (SFU) reset leaves: extra relays with the same release edge (exp vline / muls / adds, div, lines)
    s = sub(s, '''    /* verilator hier_block */''', '''    wire [6:0] rst4x;                                 // HBM-KIND8: stage-4 reset leaves (each its own relay, same edge)
`ifdef OT_SU_SYNC_RST
    for (genvar r = 0; r < 7; r = r + 1) begin : g_rst4x
        ot_sync_rst_relay u_reset (.clk_sync(RSYNC_EXT ? clk_rsync : clk_stage[0]), .clk(clk_stage[4]), .rst_n_in(rst_n), .rst_n(rst4x[r]));
    end
`else
    assign rst4x = {7{rst_n}};
`endif
    /* verilator hier_block */''')
    s = sub(s, '''ot_hdc_v41x_exp #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk_stage[4]), .rst_n(rst_stage_n[4]),''',
            '''ot_hdc_v41x_exp_k8 #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk_stage[4]), .rst_n(rst4x[0]), .rst_m(rst4x[1]), .rst_a(rst4x[2]),''')
    s = sub(s, '''            ot_hdc_v41x_fdiv u_div (.clk(clk_stage[4]), .rst_n(rst_stage_n[4]),''',
            '''            ot_hdc_v41x_fdiv u_div (.clk(clk_stage[4]), .rst_n(rst4x[3]),''')
    s = sub(s, '''ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk_stage[4]), .rst_n(rst_stage_n[4]),''',
            '''ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk_stage[4]), .rst_n(rst4x[4]),''')
    s = sub(s, '''ot_hdc_vline #(.D(D_EXP)) u_vs (.clk(clk_stage[4]), .rst_n(rst_stage_n[4]),''',
            '''ot_hdc_vline #(.D(D_EXP)) u_vs (.clk(clk_stage[4]), .rst_n(rst4x[5]),''')
    s = sub(s, '''ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT)) u_den (clk_stage[4], rst_stage_n[4],''',
            '''ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT)) u_den (clk_stage[4], rst4x[6],''')
    s = sub(s, '''ot_hdc_vline #(.D(ALAT)) u_vdn (.clk(clk_stage[4]), .rst_n(rst_stage_n[4]),''',
            '''ot_hdc_vline #(.D(ALAT)) u_vdn (.clk(clk_stage[4]), .rst_n(rst4x[6]),''')
    # ---- multipliers / exp: the k8 units
    s = sub(s, 'ot_hdc_qmul_lat #(MLAT)', 'ot_hdc_qmul_lat_k8 #(MLAT)', 5)
    # ---- FP adds: Codex FP6 ot_hdc_fp32_add_n32 (HBM-KIND9; native-32 adder internals, the HBM-QCORE9 adder)
    s = sub(s, 'ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT))', 'ot_hdc_qadd_lat_k8 #(.KEEP(K), .LAT(ALAT))', 3)
    # ---- dividers: native-32 halves (HBM-KIND9, k8/ot_hdc_v41x_fdiv_k8.sv)
    s = sub(s, 'ot_hdc_v41x_fdiv u_', 'ot_hdc_v41x_fdiv_k8 u_', 2)
    # ---- HBM-KIND9: every lane reset relay = ot_k9_rst_fam (3-member copy family of the local relay register)
    s = sub(s, 'ot_sync_rst_relay u_reset (', 'ot_k9_rst_fam #(.N(3)) u_reset (', 3)
    # ---- HBM-KIND9: 10 stage-4 reset leaves; the two D_EXP valid lines and the exp valid line each on 2 leaves (it3: 52-56)
    s = sub(s, '    wire [6:0] rst4x;', '    wire [9:0] rst4x;')
    s = sub(s, '    for (genvar r = 0; r < 7; r = r + 1) begin : g_rst4x', '    for (genvar r = 0; r < 10; r = r + 1) begin : g_rst4x')
    s = sub(s, '    assign rst4x = {7{rst_n}};', '    assign rst4x = {10{rst_n}};')
    s = sub(s, 'ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk_stage[4]), .rst_n(rst4x[4]),',
            'ot_hdc_vline_k8 #(.D(D_EXP), .R(2)) u_ve (.clk(clk_stage[4]), .rst_n({rst4x[8], rst4x[4]}),')
    s = sub(s, 'ot_hdc_vline #(.D(D_EXP)) u_vs (.clk(clk_stage[4]), .rst_n(rst4x[5]),',
            'ot_hdc_vline_k8 #(.D(D_EXP), .R(2)) u_vs (.clk(clk_stage[4]), .rst_n({rst4x[9], rst4x[5]}),')
    s = sub(s, '.rst_m(rst4x[1]), .rst_a(rst4x[2]),', '.rst_m(rst4x[1]), .rst_a(rst4x[2]), .rst_v(rst4x[7]),')
    # ---- M1 out select (cm_m1): two copies, one per half
    s = sub(s, '''    wire [31:0] P = (cm_m1 == M1_DIVB || cm_m1 == M1_DIVIMM) ? div1_y :
                    (cm_m1 == M1_AB || cm_m1 == M1_AA || cm_m1 == M1_AIMM) ? mul1_y : byp1;''',
            '''    function automatic [15:0] psel(input [2:0] m, input [15:0] d, input [15:0] mu, input [15:0] by);
        psel = (m == M1_DIVB || m == M1_DIVIMM) ? d : (m == M1_AB || m == M1_AA || m == M1_AIMM) ? mu : by;
    endfunction
    wire [31:0] P = {psel(cm_m1_c[5:3], div1_y[31:16], mul1_y[31:16], byp1[31:16]),
                     psel(cm_m1_c[2:0], div1_y[15:0], mul1_y[15:0], byp1[15:0])};''')
    s = sub(s, "u_m2 (clk_stage[2], rst_stage_n[2], v1 && cm_m2 != M2_BYP, P, (cm_m2 == M2_C) ? m_c : cm_imm1, m2_y, f_m2);",
            "u_m2 (clk_stage[2], rst_stage_n[2], v1 && cm_m2 != M2_BYP, P,\n                      {(cm_m2_c[3:2] == M2_C) ? m_c[31:16] : cm_imm1[31:16], (cm_m2_c[1:0] == M2_C) ? m_c[15:0] : cm_imm1[15:0]}, m2_y, f_m2);")
    # ---- AD operand select (ca_ad): four copies, one per byte
    s = sub(s, '''    reg [31:0] ad_y;
    always @(*) begin
        case (ca_ad)
            AD_Q:    ad_y = q_y;
            AD_C:    ad_y = a2_c;
            AD_NEGB: ad_y = {~a2_b[31], a2_b[30:0]};
            AD_IMM:  ad_y = ca_imm2;
            default: ad_y = a2_d;
        endcase
    end''', '''    reg [31:0] ad_y;
    wire [31:0] nb_b = {~a2_b[31], a2_b[30:0]};
    integer ai;
    always @(*) begin
        for (ai = 0; ai < 4; ai = ai + 1)
            case (ca_ad_c[3*ai +: 3])
                AD_Q:    ad_y[8*ai +: 8] = q_y[8*ai +: 8];
                AD_C:    ad_y[8*ai +: 8] = a2_c[8*ai +: 8];
                AD_NEGB: ad_y[8*ai +: 8] = nb_b[8*ai +: 8];
                AD_IMM:  ad_y[8*ai +: 8] = ca_imm2[8*ai +: 8];
                default: ad_y[8*ai +: 8] = a2_d[8*ai +: 8];
            endcase
    end''')
    # ---- S out select (cs_sfu): two copies, one per half
    s = sub(s, '''            assign S = (cs_sfu == SFU_EXP) ? y_exp : (cs_sfu == SFU_SIGM || cs_sfu == SFU_SILU) ? y_div :
                       (cs_sfu == SFU_NONE) ? t4[T4W-1 -: 32] : side_y;''',
            '''            function automatic [15:0] ssel(input [2:0] c, input [15:0] e, input [15:0] dv, input [15:0] t, input [15:0] sd);
                ssel = (c == SFU_EXP) ? e : (c == SFU_SIGM || c == SFU_SILU) ? dv : (c == SFU_NONE) ? t : sd;
            endfunction
            wire [31:0] t4r = t4[T4W-1 -: 32];
            assign S = {ssel(cs_sfu_c[5:3], y_exp[31:16], y_div[31:16], t4r[31:16], side_y[31:16]),
                        ssel(cs_sfu_c[2:0], y_exp[15:0], y_div[15:0], t4r[15:0], side_y[15:0])};''')
    # ---- E1 code into the T select: delayed twice (two halves)
    s = sub(s, '''    ot_hdc_delay #(.W(32 * 2 + AW + 3), .D(MLAT)) u_d5 (.clk(clk_stage[5]), .rst_n(rst_stage_n[5]), .d({S, s_b, s_o, cs_e1}),
                                                   .q({e1_byp, e_b, e_o, e_e1}));''',
            '''    ot_hdc_delay #(.W(32 * 2 + AW + 3), .D(MLAT)) u_d5 (.clk(clk_stage[5]), .rst_n(rst_stage_n[5]), .d({S, s_b, s_o, cs_e1_c[2:0]}),
                                                   .q({e1_byp, e_b, e_o, e_e1}));
    wire [2:0] e_e1h;                                // HBM-KIND8: second E1 code line for the upper half of T
    ot_hdc_delay #(.W(3), .D(MLAT)) u_d5h (.clk(clk_stage[5]), .rst_n(rst_stage_n[5]), .d(cs_e1_c[5:3]), .q(e_e1h));''')
    s = sub(s, '''    wire [31:0] T = (e_e1 == E1_MULC || e_e1 == E1_MULIMM) ? e1m : (e_e1 == E1_ADDC || e_e1 == E1_ADDIMM) ? e1a :
                    e1_byp;''', '''    function automatic [15:0] tsel(input [2:0] c, input [15:0] m, input [15:0] a, input [15:0] b);
        tsel = (c == E1_MULC || c == E1_MULIMM) ? m : (c == E1_ADDC || c == E1_ADDIMM) ? a : b;
    endfunction
    wire [31:0] T = {tsel(e_e1h, e1m[31:16], e1a[31:16], e1_byp[31:16]), tsel(e_e1, e1m[15:0], e1a[15:0], e1_byp[15:0])};''')
    # ---- E2 operand select (ce_e2) halves
    s = sub(s, "T, (ce_e2 == E2_MULB) ? e_b : ce_imm1, e2m, f_e2);",
            "T, {(ce_e2_c[3:2] == E2_MULB) ? e_b[31:16] : ce_imm1[31:16], (ce_e2_c[1:0] == E2_MULB) ? e_b[15:0] : ce_imm1[15:0]}, e2m, f_e2);")
    # ---- OUT rounding select (co_rnd) halves
    s = sub(s, '    wire [31:0] out = co_rnd ? u_bf : U;',
            '    wire [31:0] out = {co_rnd_c[1] ? u_bf[31:16] : U[31:16], co_rnd_c[0] ? u_bf[15:0] : U[15:0]};')
    return s + KFF


def pinreg():
    s = (A / 'ot_hbm_su_static_lane_pinreg.sv').read_text()
    s = sub(s, 'module ot_hbm_su_static_lane_pinreg', 'module ot_hbm_su_static_lane_pinreg_k8')
    s = sub(s, '    ot_hbm_su_static_lane #(', '    ot_hbm_su_static_lane_k8 #(')
    cp = '''    // ---- HBM-KIND8: kept same-edge pin-register copies (the lane's wide selects / masks read their own copy)
'''
    conn = ''
    for f, w, c in COPIES:
        cp += f'    wire [{c}*{w}-1:0] k_{f};\n'
        cp += f'    for (genvar j = 0; j < {c}; j = j + 1) begin : g_k_{f}\n'
        cp += f'        ot_su_kff_k8 #(.W({w})) u_k (.clk(c0), .d({f}), .q(k_{f}[j*{w} +: {w}]));\n    end\n'
        conn += f'.{f}_c(k_{f}), '
    cp += f'''    wire [{NLD}-1:0] k_ld; wire [{NBK}-1:0] k_bank;
`ifdef OT_SU_SYNC_RST
    wire k_cmd = rst_command_n;
`else
    wire k_cmd = rst_n;
`endif
    for (genvar j = 0; j < {NLD}; j = j + 1) begin : g_k_ld
        ot_su_kff_k8 u_k (.clk(c0), .d(k_cmd & ld), .q(k_ld[j]));
    end
    for (genvar j = 0; j < {NBK}; j = j + 1) begin : g_k_bank
        ot_su_kff_k8 u_k (.clk(c0), .d(k_cmd & bank), .q(k_bank[j]));
    end
'''
    conn += '.ld_x(k_ld), .bank_x(k_bank), '
    s = sub(s, '    // ---- the unchanged lane\n', cp + '    // ---- the lane (k8 copies)\n')
    s = sub(s, '.clk_rsync(c0), .clk_stage(clk_stage),', '.clk_rsync(c0), .clk_stage(clk_stage), ' + conn)
    return s


if __name__ == '__main__':
    (A / 'k8').mkdir(exist_ok=True)
    (A / 'k8/ot_hbm_su_static_lane_k8.sv').write_text(lane())
    (A / 'k8/ot_hbm_su_static_lane_pinreg_k8.sv').write_text(pinreg())
    (A / 'k8/ot_hbm_su_static_ins_k8.sv').write_text(
        '// GENERATED by tools/hbm_static/su_lane_k8_gen.py from ot_hbm_su_static_ins.sv (HBM-KIND8: sliced v / sel copies); do not edit.\n'
        + ins((A / 'ot_hbm_su_static_ins.sv').read_text(), 'ot_hbm_su_static_ins', 'ot_hbm_su_static_ins_k8'))
    v41 = (ROOT / 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv').read_text()
    hdr = v41[:v41.index('// ---------------------------------------------------------------------------')]
    body = v41[v41.index('module ot_hdc_v41x_ins #('):]
    (A / 'k8/ot_hdc_v41x_ins_k8.sv').write_text(
        hdr + '// GENERATED by tools/hbm_static/su_lane_k8_gen.py from ot_hdc_v41x_ins (rtl/hdc/v41x/ot_hdc_v41x_sfu.sv; HBM-KIND8 sliced v / sel copies); do not edit.\n'
        + ins(body, 'ot_hdc_v41x_ins', 'ot_hdc_v41x_ins_k8'))
    print('su_lane_k8_gen: wrote k8/ot_hbm_su_static_lane_k8.sv, k8/ot_hbm_su_static_lane_pinreg_k8.sv')
