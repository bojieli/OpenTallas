`timescale 1ns/1ps
// =====================================================================================================================
// QW-S5-LP 10-21 (Q.STA.SLICE.3/.4, slice2 W/E masters w6/w6b/e6/e6b): census-safe successors of the soft s5 face / tap
// leaves of rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv, plus the closed-child adapters the s6 flat parent binds.
//
// e5/e5b pre-gate native census (QW-SLICE2E6 10-21 03:35): the one-flop leaf reset u_rl.rst drove every register of the
// leaf (u_fdn 3,858 / u_fup 2,357 / u_tap 91 loads), and the tap's valid s1_v fanned out to the 1,024 masked write bits
// (1,051), q_v to the descriptor capture (150), the constant-mask e4_m flop (yosys merged the 64 copies: 128) and the
// split p_sp[2] (33).  Structural fix (owner 10-20 09:05: reset only control / valid bits, datapath unreset):
//   * every leaf still lands rst_n in its OWN two registered stages (same release edge as qfd_dv_s5_rst2, so no reset
//     schedule change), but the second stage is a set of KEPT copies (qfd_dv_s6_rk, one module instance each, listed
//     in route.synth_keep_modules) with <= 32 async-clear loads per copy;
//   * only valid / control bits are reset: cmd v (bit 0), hr v (bit 0), stream v (bit 1087), scalar v (bit 47), return
//     chain ar v (1037) / dd v (519), treq v (8), outbound chain ar v (1094) / dd v (547), the 10 ag status bits and the
//     pc_bad flag; every payload bit is a plain register (it is only consumed under its valid);
//   * the tap's fill tap is a FIXED-configuration copy of ot_qfd_xs_tap (STATIC_SCHEDULE 1, NATIVE_AFFINE 1, attention
//     input unused as in qfd_dv_s5_tap, sw_m all ones) with the valid replicated into kept per-lane copies (each <= 17
//     loads), q_v replicated per descriptor field group, e4_m kept per lane, p_sp kept twice.  Cycle-exact with
//     ot_qfd_xs_tap at those parameters (same edges, same values on every output bit that is consumed under its valid;
//     the descriptor payload d_o[*][DESC-1:1] holds its last claim instead of resetting to 0, valid d_o[*][0] resets).
// Values / arithmetic / order / edges unchanged vs the s5 leaves; the only schedule entries are the ones of the s5 HARD
// leaves (fdn pc_bad +1, tap cid +1), unchanged.
// =====================================================================================================================

// one kept reset copy: the second landing stage (async assert, synchronous release one edge after its input)
module qfd_dv_s6_rk (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
// one kept valid copy (async clear from its reset copy)
module qfd_dv_s6_vk (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
// one kept payload copies (no reset)
module qfd_dv_s6_pk1 (input wire ck, input wire d, output reg q);
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s6_pk4 (input wire ck, input wire [3:0] d, output reg [3:0] q);
    always @(posedge ck) q <= d;
endmodule

// 2-stage reset landing with a kept second stage: stage 1 (rs1) drives only the N copies; copy k drives <= 32 loads.
// Release edge = qfd_dv_s5_rst2 (rs1 -> rs2): every copy releases on the same edge as the s5 leaf's rst.
module qfd_dv_s6_rst2x4 (input wire ck, input wire rst_n, output wire [3:0] rst);
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    qfd_dv_s6_rk u_k0 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[0]));
    qfd_dv_s6_rk u_k1 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[1]));
    qfd_dv_s6_rk u_k2 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[2]));
    qfd_dv_s6_rk u_k3 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[3]));
endmodule

// Opt-in FUP delivery: private two-stage reset chain for one physical control group.
// The second stage takes both D and asynchronous clear from stage 1. Assertion
// propagates in the same simulation time step; release retains the original two
// clock edges. This lets both reset and D wires use the same <=405um two hops.
// Keep the module boundary and both stages: shared first stages would recreate
// the long AGU/CHU/CMD reset legs that this structural variant removes.
(* keep_hierarchy = 1, keep = 1 *)
module qfd_dv_s6_rst2_local (input wire ck, input wire rst_n, output wire rst);
    (* keep = 1 *) reg rs1;
    (* keep = 1 *) reg rs2;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    always @(posedge ck or negedge rs1) if (!rs1) rs2 <= 1'b0; else rs2 <= rs1;
    assign rst = rs2;
endmodule

// ---------------------------------------------------------------------------------------------------------- dn face
// = qfd_dv_s5_fdn (HARD 1) with valid-only reset (20 reset loads on one kept copy; 3,858 before).
module qfd_dv_s6_fdn (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [115:0]   cmd_i,
    input  wire [452:0]   hr_i,
    input  wire [1087:0]  st_up_i,
    input  wire [47:0]    sc_up_i,
    input  wire [1037:0]  ch_dn_i,
    input  wire [8:0]     treq_i,
    output reg  [115:0]   cmd_q,
    output reg  [452:0]   hr_q,
    output reg  [1087:0]  sw_q,
    output reg  [47:0]    scu_q,
    output reg  [1037:0]  chd_q,
    output reg  [8:0]     treq_q,
    input  wire [1094:0]  chu_q,
    input  wire [1094:0]  own_ch,
    output reg  [1094:0]  ch_dn_o,
    output wire           pc_bad,
    input  wire [9:0]     agu_q,
    input  wire [9:0]     ag_own,
    output reg  [9:0]     ag_dn_o,
    input  wire [1087:0]  st_dn_c,
    output wire [1087:0]  st_dn_o,
    input  wire [47:0]    sc_dn_c,
    output wire [47:0]    sc_dn_o,
    input  wire [106:0]   st_c,
    output wire [106:0]   st,
    input  wire [49:0]    cc_c,
    output wire [49:0]    cc_o,
    input  wire [513:0]   l9_i,
    output wire [65:0]    l9_r0, l9_r1, l9_r2, l9_r3, l9_r4, l9_r5, l9_r6, l9_r7,
    output wire [8:0]     treq_c
);
    assign st_dn_o = st_dn_c; assign sc_dn_o = sc_dn_c; assign st = st_c; assign cc_o = cc_c;
    assign l9_r0 = {l9_i[513:512], l9_i[63:0]};
    assign l9_r1 = {l9_i[513:512], l9_i[127:64]};
    assign l9_r2 = {l9_i[513:512], l9_i[191:128]};
    assign l9_r3 = {l9_i[513:512], l9_i[255:192]};
    assign l9_r4 = {l9_i[513:512], l9_i[319:256]};
    assign l9_r5 = {l9_i[513:512], l9_i[383:320]};
    assign l9_r6 = {l9_i[513:512], l9_i[447:384]};
    assign l9_r7 = {l9_i[513:512], l9_i[511:448]};
    assign treq_c = treq_i;
    wire [3:0] rst;
    qfd_dv_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    // valid / control bits (reset copy 0: 20 loads)
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin cmd_q[0] <= 1'b0; hr_q[0] <= 1'b0; sw_q[1087] <= 1'b0; scu_q[47] <= 1'b0;
                           chd_q[1037] <= 1'b0; chd_q[519] <= 1'b0; treq_q[8] <= 1'b0; end
        else begin cmd_q[0] <= cmd_i[0]; hr_q[0] <= hr_i[0]; sw_q[1087] <= st_up_i[1087]; scu_q[47] <= sc_up_i[47];
                   chd_q[1037] <= ch_dn_i[1037]; chd_q[519] <= ch_dn_i[519]; treq_q[8] <= treq_i[8]; end
    // payload (no reset)
    always @(posedge ck) begin
        cmd_q[115:1] <= cmd_i[115:1]; hr_q[452:1] <= hr_i[452:1]; sw_q[1086:0] <= st_up_i[1086:0];
        scu_q[46:0] <= sc_up_i[46:0]; chd_q[1036:520] <= ch_dn_i[1036:520]; chd_q[518:0] <= ch_dn_i[518:0];
        treq_q[7:0] <= treq_i[7:0];
    end
    wire p_ar = chu_q[1094], p_dd = chu_q[547];
    wire [1094:0] ch_m = {p_ar ? chu_q[1094:548] : own_ch[1094:548], p_dd ? chu_q[547:0] : own_ch[547:0]};
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin ch_dn_o[1094] <= 1'b0; ch_dn_o[547] <= 1'b0; ag_dn_o <= 10'd0; end
        else begin ch_dn_o[1094] <= ch_m[1094]; ch_dn_o[547] <= ch_m[547]; ag_dn_o <= agu_q | ag_own; end
    always @(posedge ck) begin ch_dn_o[1093:548] <= ch_m[1093:548]; ch_dn_o[546:0] <= ch_m[546:0]; end
    wire pc = (p_ar && own_ch[1094]) || (p_dd && own_ch[547]);
    reg pq;
    always @(posedge ck or negedge rst[0]) if (!rst[0]) pq <= 1'b0; else pq <= pc;
    assign pc_bad = pq;
endmodule

// ---------------------------------------------------------------------------------------------------------- up face
// = qfd_dv_s5_fup (MUT 0) with valid-only reset (15 reset loads; 2,357 before).
module qfd_dv_s6_fup (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [1087:0]  st_dn_i,
    input  wire [47:0]    sc_dn_i,
    input  wire [1094:0]  ch_up_i,
    input  wire [9:0]     ag_up_i,
    output reg  [1087:0]  se_q,
    output reg  [47:0]    scd_q,
    output reg  [1094:0]  chu_q,
    output reg  [9:0]     agu_q,
    input  wire [115:0]   cmd_q,
    output reg  [115:0]   cmd_o,
    input  wire [1087:0]  st_up_c,
    output wire [1087:0]  st_up_o,
    input  wire [47:0]    sc_up_c,
    output wire [47:0]    sc_up_o,
    input  wire [452:0]   hr_c,
    output wire [452:0]   hr_o,
    input  wire [1037:0]  chr_c,
    output wire [1037:0]  ch_up_o,
    input  wire [8:0]     treq_c,
    output wire [8:0]     treq_o,
    input  wire [513:0]   l9_c,
    output wire [513:0]   l9_o
);
    assign st_up_o = st_up_c; assign sc_up_o = sc_up_c; assign hr_o = hr_c; assign ch_up_o = chr_c; assign treq_o = treq_c;
    assign l9_o = l9_c;
    wire [3:0] rst;
    qfd_dv_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    wire [115:0] cmd_n = setid ? {cmd_q[115:8], cmd_q[7:4] + 4'd1, cmd_q[3:0]} : cmd_q;
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin se_q[1087] <= 1'b0; scd_q[47] <= 1'b0; chu_q[1094] <= 1'b0; chu_q[547] <= 1'b0; agu_q <= 10'd0;
                           cmd_o[0] <= 1'b0; end
        else begin se_q[1087] <= st_dn_i[1087]; scd_q[47] <= sc_dn_i[47]; chu_q[1094] <= ch_up_i[1094];
                   chu_q[547] <= ch_up_i[547]; agu_q <= ag_up_i; cmd_o[0] <= cmd_n[0]; end
    always @(posedge ck) begin
        se_q[1086:0] <= st_dn_i[1086:0]; scd_q[46:0] <= sc_dn_i[46:0];
        chu_q[1093:548] <= ch_up_i[1093:548]; chu_q[546:0] <= ch_up_i[546:0]; cmd_o[115:1] <= cmd_n[115:1];
    end
endmodule

// Explicit opt-in full-FUP variant; original master above remains byte-identical.
module qfd_dv_s6_fup_reset_local #(parameter bit LOCAL_RESET_COPIES = 1'b1) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [1087:0]  st_dn_i,
    input  wire [47:0]    sc_dn_i,
    input  wire [1094:0]  ch_up_i,
    input  wire [9:0]     ag_up_i,
    output reg  [1087:0]  se_q,
    output reg  [47:0]    scd_q,
    output reg  [1094:0]  chu_q,
    output reg  [9:0]     agu_q,
    input  wire [115:0]   cmd_q,
    output reg  [115:0]   cmd_o,
    input  wire [1087:0]  st_up_c,
    output wire [1087:0]  st_up_o,
    input  wire [47:0]    sc_up_c,
    output wire [47:0]    sc_up_o,
    input  wire [452:0]   hr_c,
    output wire [452:0]   hr_o,
    input  wire [1037:0]  chr_c,
    output wire [1037:0]  ch_up_o,
    input  wire [8:0]     treq_c,
    output wire [8:0]     treq_o,
    input  wire [513:0]   l9_c,
    output wire [513:0]   l9_o
);
    assign st_up_o = st_up_c; assign sc_up_o = sc_up_c; assign hr_o = hr_c; assign ch_up_o = chr_c; assign treq_o = treq_c;
    assign l9_o = l9_c;
    wire [3:0] rst;
    wire [3:0] rst_legacy;
    qfd_dv_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_legacy));
    assign rst[0] = rst_legacy[0];
    generate if (LOCAL_RESET_COPIES) begin : g_local_reset
        qfd_dv_s6_rst2_local u_agu (.ck(ck), .rst_n(rst_n), .rst(rst[1]));
        qfd_dv_s6_rst2_local u_chu (.ck(ck), .rst_n(rst_n), .rst(rst[2]));
        qfd_dv_s6_rst2_local u_cmd (.ck(ck), .rst_n(rst_n), .rst(rst[3]));
    end else begin : g_legacy_reset
        assign rst[3:1] = {3{rst_legacy[0]}};
    end endgenerate
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    wire [115:0] cmd_n = setid ? {cmd_q[115:8], cmd_q[7:4] + 4'd1, cmd_q[3:0]} : cmd_q;
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin se_q[1087] <= 1'b0; scd_q[47] <= 1'b0; end
        else begin se_q[1087] <= st_dn_i[1087]; scd_q[47] <= sc_dn_i[47]; end
    always @(posedge ck or negedge rst[1])
        if (!rst[1]) agu_q <= 10'd0; else agu_q <= ag_up_i;
    always @(posedge ck or negedge rst[2])
        if (!rst[2]) begin chu_q[1094] <= 1'b0; chu_q[547] <= 1'b0; end
        else begin chu_q[1094] <= ch_up_i[1094]; chu_q[547] <= ch_up_i[547]; end
    always @(posedge ck or negedge rst[3])
        if (!rst[3]) cmd_o[0] <= 1'b0; else cmd_o[0] <= cmd_n[0];
    always @(posedge ck) begin
        se_q[1086:0] <= st_dn_i[1086:0]; scd_q[46:0] <= sc_dn_i[46:0];
        chu_q[1093:548] <= ch_up_i[1093:548]; chu_q[546:0] <= ch_up_i[546:0]; cmd_o[115:1] <= cmd_n[115:1];
    end
endmodule

// ---------------------------------------------------------------------------------------------------------- fill tap
// ot_qfd_xs_tap #(AW 24, NW 18, XCW 12, STATIC_SCHEDULE 1, NATIVE_AFFINE 1, MUT 0) with aw_v = 0, sw_m = all ones
// (exactly how qfd_dv_s5_tap instantiates it), fixed (no parameters: kept copies survive synthesis by name).
module qfd_dv_s6_xs_tap (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              xpf_v,
    input  wire [23:0]       xpf_xbase,
    input  wire [11:0]       xpf_xcs,
    input  wire [11:0]       xpf_xks,
    input  wire [3:0]        xpf_split,
    input  wire [17:0]       xpf_k,
    input  wire              xpf_round,
    input  wire              sw_v,
    input  wire [23:0]       sw_a,
    input  wire [64*32-1:0]  sw_d,
    input  wire [379:0]      gi,
    output wire [1566:0]     hw,
    input  wire              fw_i,
    input  wire              fe_i,
    output reg               fault
);
    localparam integer AW = 24, NW = 18, XCW = 12;
    localparam integer BW = AW - 6;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;     // 73
    localparam integer IBW = 3 * NW + 13 * AW + 13;              // 379
    // reset: 2 landing stages, the second as 4 kept copies (<= 32 loads each)
    wire [3:0] rs;
    qfd_dv_s6_rst2x4 u_rl (.ck(clk), .rst_n(rst_n), .rst(rs));
    // ---- go / ib ----
    reg g1_v, g2_v;
    reg [IBW-1:0] g1_ib, g2_ib;
    always @(posedge clk or negedge rs[0])
        if (!rs[0]) begin g1_v <= 1'b0; g2_v <= 1'b0; end
        else begin g1_v <= gi[0]; g2_v <= g1_v; end
    always @(posedge clk) begin g1_ib <= gi[IBW:1]; g2_ib <= g1_ib; end
    reg fwq, feq;
    // ---- E1: pin registers ----
    reg              p_v, p_rnd;
    reg [AW-1:0]     p_xb;
    reg [XCW-1:0]    p_xcs, p_xks;
    reg [NW-1:0]     p_k;
    reg [AW-1:0]     s1_a;
    reg [64*32-1:0]  s1_d;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) p_v <= 1'b0; else p_v <= xpf_v;
    always @(posedge clk) begin
        p_xb <= xpf_xbase; p_xcs <= xpf_xcs; p_xks <= xpf_xks; p_k <= xpf_k; p_rnd <= xpf_round;
        s1_a <= sw_a; s1_d <= sw_d;
    end
    // split: two kept copies (q_s1 shifter / fault check, q_sp descriptor)
    wire [3:0] p_spa, p_spb;
    qfd_dv_s6_pk4 u_spa (.ck(clk), .d(xpf_split), .q(p_spa));
    qfd_dv_s6_pk4 u_spb (.ck(clk), .d(xpf_split), .q(p_spb));
    // write valid s1_v: 64 per-lane kept copies (lane l masks its 16 live data bits + its mask bit) + 1 control copy
    // (w_v / w_a mask) + 1 for the fault term; reset copies 1..3 (<= 32 loads each)
    wire [63:0] s1_vl;
    wire        s1_vc, s1_vf;
    genvar gl;
    generate for (gl = 0; gl < 64; gl = gl + 1) begin : g_sv
        qfd_dv_s6_vk u_v (.ck(clk), .rst_n(rs[1 + gl / 32]), .d(sw_v), .q(s1_vl[gl]));
    end endgenerate
    qfd_dv_s6_vk u_svc (.ck(clk), .rst_n(rs[3]), .d(sw_v), .q(s1_vc));
    qfd_dv_s6_vk u_svf (.ck(clk), .rst_n(rs[3]), .d(sw_v), .q(s1_vf));
    // ---- E2 ----
    reg              q_rnd;
    reg [AW-1:0]     q_xb;
    reg [XCW-1:0]    q_xcs, q_xks;
    reg [3:0]        q_sp;
    reg [NW-1:0]     q_k;
    reg [AW-1:0]     q_s1;
    // q_v: 4 kept copies -- arm / epoch / range state (qa), descriptor 0 (qd0), descriptor 1 (qd1), round + spare (qr)
    wire qa, qd0, qd1, qr;
    qfd_dv_s6_vk u_qa  (.ck(clk), .rst_n(rs[3]), .d(p_v), .q(qa));
    qfd_dv_s6_vk u_qd0 (.ck(clk), .rst_n(rs[3]), .d(p_v), .q(qd0));
    qfd_dv_s6_vk u_qd1 (.ck(clk), .rst_n(rs[3]), .d(p_v), .q(qd1));
    qfd_dv_s6_vk u_qr  (.ck(clk), .rst_n(rs[3]), .d(p_v), .q(qr));
    always @(posedge clk) begin
        q_xb <= p_xb; q_xcs <= p_xcs; q_xks <= p_xks; q_sp <= p_spb; q_k <= p_k; q_rnd <= p_rnd;
        q_s1 <= {{(AW-XCW){1'b0}}, p_xcs} << p_spa;
    end
    // ---- E3: arm + descriptor ----
    reg              ep_nx;
    reg  [1:0]       arm;
    reg  [AW-1:0]    lo [0:1];
    reg  [AW-1:0]    lo_minus64 [0:1];
    reg  [1:0]       lo_below64;
    reg  [AW:0]      hi [0:1];
    reg  [1:0]       rnd;
    reg  [DESC-1:0]  d_o [0:1];
    always @(posedge clk or negedge rs[0])
        if (!rs[0]) begin ep_nx <= 1'b0; arm <= 2'b00; end
        else if (qa) begin arm <= ep_nx ? 2'b10 : 2'b01; ep_nx <= ~ep_nx; end
    always @(posedge clk)
        if (qa) begin
            lo[ep_nx] <= q_xb; lo_minus64[ep_nx] <= q_xb - 64; lo_below64[ep_nx] <= (q_xb < 64);
            hi[ep_nx] <= {1'b0, q_xb} + q_s1;
        end
    always @(posedge clk) if (qr) rnd[ep_nx] <= q_rnd;
    // descriptor valid d_o[*][0] (reset; cleared each edge unless a claim), payload held between claims
    always @(posedge clk or negedge rs[0])
        if (!rs[0]) begin d_o[0][0] <= 1'b0; d_o[1][0] <= 1'b0; end
        else begin d_o[0][0] <= qd0; d_o[1][0] <= qd1; end
    always @(posedge clk) begin
        if (qd0) d_o[0][DESC-1:1] <= {q_rnd, q_k, q_sp, q_xks, q_xcs, q_xb, ep_nx};
        if (qd1) d_o[1][DESC-1:1] <= {q_rnd, q_k, q_sp, q_xks, q_xcs, q_xb, ep_nx};
    end
    // ---- writes (STATIC_SCHEDULE: no queue; attention input unused) ----
    wire          w_v = s1_vc;
    wire [AW-1:0] w_a = s1_a & {AW{s1_vc}};
    wire [AW:0]   wa_lo = {1'b0, w_a};
    wire [1:0]    hit;
    assign hit[0] = arm[0] && (wa_lo < hi[0]) && (lo_below64[0] || w_a > lo_minus64[0]);
    assign hit[1] = arm[1] && (wa_lo < hi[1]) && (lo_below64[1] || w_a > lo_minus64[1]);
    wire        hep = hit[1];
    wire        hrd = rnd[hep];
    wire [5:0]  off = w_a[5:0];
    reg  [1023:0] h_d;
    reg  [63:0]   c_y;
    integer l;
    reg [31:0] xe;
    always @* begin
        for (l = 0; l < 64; l = l + 1) begin
            xe = s1_d[32*l +: 32] & {32{s1_vl[l]}};
            h_d[16*l +: 16] = xe[31:16];
            c_y[l] = (xe[15:0] > 16'h8000) || (xe[15:0] == 16'h8000 && xe[16]);
        end
    end
    reg              e4_v, e4_ep, e4_rnd;
    reg [BW-1:0]     e4_b;
    reg [5:0]        e4_off;
    reg [63:0]       e4_cy;
    reg [1023:0]     e4_h;
    // e4_m[l] = w_m[l] = s1_v (sw_m all ones): one kept copy per lane (2 loads each: the two head-root e5_m copies)
    wire [63:0]      e4_m;
    generate for (gl = 0; gl < 64; gl = gl + 1) begin : g_m
        qfd_dv_s6_pk1 u_m (.ck(clk), .d(s1_vl[gl]), .q(e4_m[gl]));
    end endgenerate
    always @(posedge clk or negedge rs[0])
        if (!rs[0]) begin e4_v <= 1'b0; fault <= 1'b0; fwq <= 1'b0; feq <= 1'b0; end
        else begin
            e4_v <= w_v && (hit != 2'b00);
            fwq <= fw_i; feq <= fe_i;
            if ((s1_vf && hit == 2'b11) || fwq || feq ||
                (p_v && (p_xks != 1 || p_xcs != p_k ||
                 !(p_k == 2 || p_k == 6 || p_k == 8 || p_k == 24 || p_k == 32)))) fault <= 1'b1;
        end
    always @(posedge clk) begin
        e4_ep <= hep; e4_rnd <= hrd; e4_b <= w_a[AW-1:6]; e4_off <= off; e4_cy <= c_y; e4_h <= h_d;
    end
    // E3 out: the W head root only (qfd_dv_s5_tap leaves he unused)
    reg [1023:0] e5n;
    integer k;
    always @* for (k = 0; k < 64; k = k + 1) e5n[16*k +: 16] = e4_h[16*k +: 16] + {15'd0, e4_rnd & e4_cy[k]};
    (* keep *) reg              e5_v, e5_ep, g3_v;
    (* keep *) reg [BW-1:0]     e5_b;
    (* keep *) reg [5:0]        e5_off;
    (* keep *) reg [63:0]       e5_m;
    (* keep *) reg [1023:0]     e5_d;
    (* keep *) reg [IBW-1:0]    g3_ib;
    always @(posedge clk or negedge rs[0])
        if (!rs[0]) begin e5_v <= 1'b0; g3_v <= 1'b0; end else begin e5_v <= e4_v; g3_v <= g2_v; end
    always @(posedge clk) begin
        e5_ep <= e4_ep; e5_b <= e4_b; e5_off <= e4_off; e5_m <= e4_m; e5_d <= e5n; g3_ib <= g2_ib;
    end
    assign hw = {e5_d, e5_m, e5_off, e5_b, e5_ep, e5_v, d_o[0], g3_ib, g3_v};
endmodule

// = qfd_dv_s5_tap (HARD 1, TAP_MUT 0, MUT 0) on the census-safe fill tap; the leaf itself has no other reset load.
module qfd_dv_s6_tap (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire [452:0]   hr_q,
    input  wire           xt_v,
    input  wire [23:0]    xt_a,
    input  wire [1023:0]  xt_d,
    input  wire           xt_bad,
    input  wire [31:0]    lq_bad,
    output wire [1566:0]  hw,
    output wire [4*6-1:0] cid,
    output wire           tap_fault
);
    localparam integer AW = 24, NW = 18, XCW = 12;
    reg  [64*32-1:0] xt_f;
    integer l;
    always @(*) for (l = 0; l < 64; l = l + 1) xt_f[32*l +: 32] = {xt_d[16*l +: 16], 16'h0000};
    wire hv = hr_q[0];
    wire [71:0]  xpf = {hr_q[72:2], hr_q[1] & hv};
    wire [379:0] gi  = {hr_q[451:73], hr_q[452] & hv};
    qfd_dv_s6_xs_tap u_tap (
        .clk(ck), .rst_n(rst_n),
        .xpf_v(xpf[0]), .xpf_xbase(xpf[1 +: AW]), .xpf_xcs(xpf[1+AW +: XCW]), .xpf_xks(xpf[1+AW+XCW +: XCW]),
        .xpf_split(xpf[1+AW+2*XCW +: 4]), .xpf_k(xpf[1+AW+2*XCW+4 +: NW]), .xpf_round(xpf[1+AW+2*XCW+4+NW]),
        .sw_v(xt_v), .sw_a(xt_a), .sw_d(xt_f),
        .gi(gi), .hw(hw), .fw_i(|lq_bad), .fe_i(xt_bad), .fault(tap_fault));
    wire [23:0] cid_c = {4'(sid) * 6'd4 + 6'd3, 4'(sid) * 6'd4 + 6'd2, 4'(sid) * 6'd4 + 6'd1, 4'(sid) * 6'd4};
    reg [23:0] cq;
    always @(posedge ck) cq <= cid_c;
    assign cid = cq;
endmodule

// ---------------------------------------------------------------------------------------------------------- btab
// the station's BTAB copy bound to the CLOSED qfd_dv_s5_btab_s4 view (main physical/ref_tile/qfd_dv_s5_btab_s4: same
// read path / 2-edge answer as qfd_dv_s5_btab, split output faces).  Wires only.
module qfd_dv_s6_btab (
    input  wire           ck,
    input  wire           bt_re,
    input  wire [8:0]     bt_word,
    output wire [255:0]   bt_q,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data
);
    qfd_dv_s5_btab_s4 u_bt (.ck(ck), .bt_re(bt_re), .bt_word(bt_word), .bt_ql(bt_q[127:0]), .bt_qh(bt_q[255:128]),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_lo(tw_data[511:0]), .tw_hi(tw_data[1023:512]));
endmodule

// ---------------------------------------------------------------------------------------------------------- stm
// = qfd_dv_s5_stm_closed (Codex 5949f90af: CLOSED stream c3r + tload ns4) with the tload parameter overrides only under
// OT_S6_SIM: the kits synthesise the ns4 view (parameters baked: SLICE 0, CAPTURE_STAGE 1, LOCAL_JOIN 1), the benches
// (+define+OT_S6_SIM) simulate the RTL at those parameters.
module qfd_dv_s6_stm #(parameter integer HARD = 1, parameter integer MUT = 0, parameter integer TSLICE = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire [30:0]    stm_cfg,
    input  wire [1087:0]  sw_i,
    input  wire [1087:0]  se_i,
    output wire [1087:0]  so_e,
    output wire [1087:0]  so_w,
    input  wire [7:0]     vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire [8:0]     treq_i,
    output wire           tw_we,
    output wire [1:0]     tw_kind,
    output wire [23:0]    tw_addr,
    output wire [1023:0]  tw_data,
    output wire           xt_v,
    output wire [23:0]    xt_a,
    output wire [1023:0]  xt_d,
    output wire           xt_bad,
    output wire           stm_fault,
    output wire           tld_fault
);
    wire rst;
    // Preserve the existing stm adapter reset run before each child's own landing.
    qfd_dv_s5_rst2 u_rl(.ck(ck),.rst_n(rst_n),.rst(rst));
    wire[7:0]su_x_we=(|vm_we&&vm_waddr[23:22]==2'b01)?vm_we:8'd0;
    wire s_we;wire[1:0]s_kind;wire[23:0]s_addr;wire[1023:0]s_data;
    qfd_dv_stream_tile u_stream(.ck(ck),.rst_n(rst),.sid(sid),
        .cfg_v(stm_cfg[30]),.cfg_dir(stm_cfg[29:28]),.cfg_tag(stm_cfg[27:0]),
        .sw_lo(sw_i[543:0]),.sw_hi(sw_i[1086:544]),.sw_v(sw_i[1087]),
        .se_lo(se_i[543:0]),.se_hi(se_i[1086:544]),.se_v(se_i[1087]),
        .so_e(so_e),.so_w(so_w),.xw_we(su_x_we),.xw_addr(vm_waddr),.xw_data(vm_wdata),
        .tw_we(s_we),.tw_kind(s_kind),.tw_addr(s_addr),.tw_data_lo(s_data[511:0]),.tw_data_hi(s_data[1023:512]),
        .xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d[511:0]),.xt_d_hi(xt_d[1023:512]),.xt_bad(xt_bad),.fault(stm_fault));
    wire j_we;wire[1:0]j_kind;wire[23:0]j_addr;wire[1023:0]j_data;
    qfd_dv_slice_tload
`ifdef OT_S6_SIM
        #(.SLICE(TSLICE),.CAPTURE_STAGE(1),.LOCAL_JOIN(1))   // the CLOSED ns4 view's baked parameters (sim only: a hard view has none)
`endif
        u_tload(
        .ck(ck),.rst_n(rst),.treq(treq_i),.s_we(s_we),.s_kind(s_kind),.s_addr(s_addr),.s_data(s_data),
        .tw_we(j_we),.tw_kind(j_kind),.tw_addr(j_addr),.tw_data(j_data),.busy(),.done(),.fault(tld_fault));
    // Original HARD parent table-write publication retained, payload/reset policy unchanged.
    reg twv;reg[1:0]twk;reg[23:0]twa;reg[1023:0]twd;
    always @(posedge ck or negedge rst)if(!rst)twv<=0;else twv<=j_we;
    always @(posedge ck)begin twk<=j_kind;twa<=j_addr;twd<=j_data;end
    assign tw_we=twv;assign tw_kind=twk;assign tw_addr=twa;assign tw_data=twd;
endmodule
