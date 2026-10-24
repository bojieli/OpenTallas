`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// CORE-S81 (10-23, CORE-HARDEN fallback): ot_s81sl_ve r5 cut into TWO hard cores along its two independent streams.
// ve (rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv, r5 f51f4ec42) is two disjoint datapaths that share only the reset relay and
// the sticky fault flop:  reduce  r_* -> mul4 -> pack -> chunk8 x3 -> beat trees -> p_*   (relay regions 0..13)
//                         add     a_* -> add8 -> o_*                                      (relay regions 14..17)
//   ot_s81sl_ve_r  = the reduce stream, its own ot_rst_relay (14 regions: region k = r5 region k)
//   ot_s81sl_ve_a  = the add stream, its own ot_rst_relay (5 regions: 0 = control, 1..4 = r5 regions 14..17)
//   ot_s81sl_ve_s2 = thin wrapper with the ot_s81sl_ve ports: fault = fault_r | fault_a (two sticky flops, the r5 OR terms
//                    split by stream: f_order / mul / chunk / tree / lock -> r, add8 -> a) -> same edge as r5's one flop.
// Every core pin is registered (inputs land in the r5 input flops, outputs leave the r5 output flops); the cut crosses
// no signal (the streams never meet), so the static schedule, the calendars (reduce 129 cyc GAP 0, add 44) and every
// output edge are r5's exactly; no ready / credit.  Reset: each relay is the r5 relay (2 sync + 1 tree stage), so every
// region releases on the r5 edge.  Arithmetic leaves are r5's modules (ot_s81sl_ve.sv + ot_s81sl_ve_fp.sv), unchanged.
// MUT as r5 (bench only): 1 / 2 / 3 reach the reduce core.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ve_r #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    output reg          p_v,
    output reg  [1:0]   p_c,
    output reg  [31:0]  p_hh, p_kk, p_dd,
    output reg          fault
);
    localparam integer NR = 14;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    wire rn = rq[0];

    reg         rv_q;
    reg [1:0]   rc_q;
    reg [127:0] rh_q, rk_q, rw_q;
    always @(posedge clk or negedge rn)
        if (!rn) rv_q <= 1'b0;
        else rv_q <= r_v;
    always @(posedge clk) begin rc_q <= r_c; rh_q <= r_h; rk_q <= r_k; rw_q <= r_w; end

    reg [5:0] icnt;
    reg       f_order;
    always @(posedge clk or negedge rn)
        if (!rn) begin icnt <= 6'd0; f_order <= 1'b0; end
        else if (rv_q) begin
            icnt <= icnt + 6'd1;
            if (rc_q != icnt[5:4]) f_order <= 1'b1;
        end

    wire         mv, mvpre;
    wire [127:0] mhh, mkk, mdd;
    wire         mf;
    ot_s81sl_ve_mul4 #(.LM(LM), .MUT(MUT == 1 ? 1 : 0)) mul (clk, rq[4:1], rv_q, 1'b0, rh_q, rk_q, rw_q,
                                                              mv, mvpre, mhh, mkk, mdd, mf);
    reg         half;
    reg         cv;
    always @(posedge clk or negedge rn)
        if (!rn) begin half <= 1'b0; cv <= 1'b0; end
        else begin
            cv <= mv && half;
            if (mv) half <= ~half;
        end
    wire e_lo_d = mvpre && !(half ^ mv);
    (* keep = "true" *) reg [23:0] e_lo;
    always @(posedge clk) e_lo <= {24{e_lo_d}};
    reg  [383:0] sbus;
    wire [383:0] mbus = {mdd, mkk, mhh};
    genvar g;
    generate for (g = 0; g < 24; g = g + 1) begin : g_lo
        always @(posedge clk) if (e_lo[g]) sbus[16*g +: 16] <= mbus[16*g +: 16];
    end endgenerate
    reg [255:0] chh, ckk, cdd;
    always @(posedge clk) begin
        chh <= {mhh, sbus[127:0]}; ckk <= {mkk, sbus[255:128]}; cdd <= {mdd, sbus[383:256]};
    end

    wire [2:0]  sv, sf;
    wire [31:0] shh_s, skk_s, sdd_s;
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_hh (clk, rq[6:5],  cv, chh, sv[0], shh_s, sf[0]);
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_kk (clk, rq[8:7],  cv, ckk, sv[1], skk_s, sf[1]);
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_dd (clk, rq[10:9], cv, cdd, sv[2], sdd_s, sf[2]);

    wire [2:0]  tv, tf;
    wire [1:0]  tc0, tc1, tc2;
    wire [31:0] thh, tkk, tdd;
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_hh (clk, rq[11], sv[0], shh_s, tv[0], tc0, thh, tf[0]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_kk (clk, rq[12], sv[1], skk_s, tv[1], tc1, tkk, tf[1]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_dd (clk, rq[13], sv[2], sdd_s, tv[2], tc2, tdd, tf[2]);

    always @(posedge clk or negedge rn)
        if (!rn) p_v <= 1'b0;
        else p_v <= tv[0];
    always @(posedge clk) begin p_c <= tc0; p_hh <= thh; p_kk <= tkk; p_dd <= tdd; end
    wire f_lock = (tv[0] != tv[1]) || (tv[0] != tv[2]) || (sv[0] != sv[1]) || (sv[0] != sv[2]) ||
                  (tv[0] && ((tc0 != tc1) || (tc0 != tc2)));
    always @(posedge clk or negedge rn)
        if (!rn) fault <= 1'b0;
        else if (f_order || mf || (|sf) || (|tf) || f_lock) fault <= 1'b1;
endmodule

module ot_s81sl_ve_a #(parameter integer LM = 5, LA = 4) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output reg          o_v,
    output reg  [1:0]   o_c,
    output reg  [255:0] o_y,
    output reg          fault
);
    localparam integer NR = 5;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    wire rn = rq[0];

    reg         av_q;
    reg [1:0]   ac_q;
    reg [255:0] ah_q, aval_q;
    reg [31:0]  ag_q;
    always @(posedge clk or negedge rn)
        if (!rn) av_q <= 1'b0;
        else av_q <= a_v;
    always @(posedge clk) begin ac_q <= a_c; ah_q <= a_h; aval_q <= a_val; ag_q <= a_g; end

    wire         yv;
    wire [255:0] yd;
    wire         yf;
    wire [1:0]   yc;
    ot_s81sl_ve_add8 #(.LM(LM), .LA(LA)) add (clk, rq[4:1], av_q, 1'b1, ah_q, aval_q, ag_q, ac_q, yv, yd, yf, yc);
    always @(posedge clk or negedge rn)
        if (!rn) o_v <= 1'b0;
        else o_v <= yv;
    always @(posedge clk) begin o_c <= yc; o_y <= yd; end
    always @(posedge clk or negedge rn)
        if (!rn) fault <= 1'b0;
        else if (yf) fault <= 1'b1;
endmodule

module ot_s81sl_ve_s2 #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    output wire         p_v,
    output wire [1:0]   p_c,
    output wire [31:0]  p_hh, p_kk, p_dd,
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output wire         o_v,
    output wire [1:0]   o_c,
    output wire [255:0] o_y,
    output wire         fault
);
    wire fr, fa;
    ot_s81sl_ve_r #(.LM(LM), .LA(LA), .MUT(MUT)) u_ver (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_c(r_c), .r_h(r_h),
        .r_k(r_k), .r_w(r_w), .p_v(p_v), .p_c(p_c), .p_hh(p_hh), .p_kk(p_kk), .p_dd(p_dd), .fault(fr));
    ot_s81sl_ve_a #(.LM(LM), .LA(LA)) u_vea (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_c(a_c), .a_h(a_h), .a_val(a_val),
        .a_g(a_g), .o_v(o_v), .o_c(o_c), .o_y(o_y), .fault(fa));
    assign fault = fr | fa;
endmodule
