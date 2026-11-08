`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-2 (2026-10-17, S81-DV p4h): ot_s81_su_sms, the SM SHARE of ONE regional service slice dsdv_svc_rs (x16 on the
// die, one softmax head each).  The interface the svc slice instantiates; wires only, no logic of its own:
//   ot_s81_su_smq (per-head tap, hard tile s81su_smq)  <->  ot_s81_su_smh (head lane subtree, hard cluster s81su_smh).
// Physically the tap abuts the cluster's pin face, so the tap <-> subtree links are direct (both ends registered).
//
// Slice-facing ports (all registered at the tap: flop-first / flop-last), statically scheduled, NO ready / credit:
//   cfg_g[3:0]                 strap: the global head index g (0..15) of this slice
//   j_st, j_kind[3:0], j_jid   job announce (SE = 4, SO = 5; any other kind leaves the share idle)
//   r_v, r_p, r_j[2:0], r_d    row port: r_p = 1 parameter row r_j (SE: rows 0, 1; SO: rows 0..4), one a cycle after
//                              j_st; r_p = 0 the head's operand row (SE: 16 scores of a score vector; SO: 16 lanes of a
//                              P.V vector), one a cycle, after the job's last parameter row (row rules: ot_s81_su_smq)
//   w_v, w_a[13:0], w_m[15:0], w_d[511:0]   the head's write row (SE: e row, mask FFFF, addr obase + 16 oc + g;
//                              SO: o row, this head's half (00FF g even, FF00 g odd), addr obase + 8 oc + g / 2)
//   o_fu, o_fo, o_alive, o_den, o_rjid[7:0] status (divide fault, row-order / overflow fault, alive, den reached, job)
// Fixed latencies (cycles, measured by tools/s81_su_sm/sms_bench.sh, recorded in lanes/S81U-2.md): every result row is a
// fixed number of cycles after the row that produced it; the compiler schedules the slice's row port and write window
// from them.  SRL = relay stations on every intra-cluster link (2, the hardened cluster's value).
// MUT (bench mutants): 1..3 = ot_s81_su_smq's (sink column, SO half mask, cos / sin pair), 5 = stale den (smd).
// -DSU_SMU_T: the head subtree is the regional-cluster composition dsfd_su_t_smh (4 lane quads + root); MUT 6 = its
// root -> quad hop one station short (split-latency mutant).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_sms #(
    parameter integer SM_NVMAX = 40, LM = 5, LA = 4, SRL = 2, MUT = 0
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_g,
    input  wire          j_st,
    input  wire [3:0]    j_kind,
    input  wire [7:0]    j_jid,
    input  wire          r_v,
    input  wire          r_p,
    input  wire [2:0]    r_j,
    input  wire [511:0]  r_d,
    output wire          w_v,
    output wire [13:0]   w_a,
    output wire [15:0]   w_m,
    output wire [511:0]  w_d,
    output wire          o_fu,
    output wire          o_fo,
    output wire          o_alive,
    output wire          o_den,
    output wire [7:0]    o_rjid
);
    wire s_v, p_v, c_v, cs_v, e_v, o_v, den_v;
    wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale, c_sink; wire [4:0] cs_i; wire [63:0] cs_d;
    wire [511:0] d, e_d; wire [255:0] o_d; wire [7:0] f;

    ot_s81_su_smq #(.MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_smq (
        .clk(clk), .rst_in(rst_in), .cfg_g(cfg_g), .j_st(j_st), .j_kind(j_kind), .j_jid(j_jid),
        .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d),
        .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
        .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .d_o(d),
        .e_v(e_v), .e_d(e_d), .o_vi(o_v), .o_di(o_d), .den_v(den_v), .f_i(f),
        .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rjid(o_rjid));

    // the tap forwards its operand row registered WITH the valids: DOP = SRL
`ifdef SU_SMU_T
    dsfd_su_t_smh #(.SRL(SRL), .MUT((MUT == 5 || MUT == 6) ? MUT : 0)) u_smh (
`else
    ot_s81_su_smh #(.SM_NVMAX(SM_NVMAX), .LM(LM), .LA(LA), .SRL(SRL), .MUT(MUT == 5 ? 5 : 0), .DOP(SRL)) u_smh (
`endif
        .clk(clk), .rst_in(rst_in), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale),
        .c_sink(c_sink), .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .d(d),
        .e_v(e_v), .e_d(e_d), .o_v(o_v), .o_d(o_d), .den_v(den_v), .f(f));
endmodule
