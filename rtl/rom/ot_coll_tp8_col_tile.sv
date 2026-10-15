`timescale 1ns/1ps
// Production TP8 wrapper column, fixed hardened master, five replicas.
// Pure sequential factoring: unchanged original edge timing, no datapath reset.
// Nine 32x128 SRAMs, six local queue controllers, pin/relay/held/output rows.
module ot_coll_tp8_col_tile (
 input wire clk,rst_n,
 input wire [127:0] in_d,dp_d,dr_d,lo,hi,gh_d,eq_wd,lq_wd,tq_wd,e_tx,m_d,
 input wire [383:0] sr_d,
 input wire [5:0] c_push,c_pop,
 input wire c_hold,
 output reg [127:0] ir,rl,up,dp,hl,hh,gh,ur,dr,od,
 output reg [383:0] sr,sx,
 output wire [127:0] lb_hd,pq_hd,eq_hd,lq_hd,tq_hd,rq_hd,
 output wire [5:0] hv,ovf
);
 always @(posedge clk) begin
  ir<=in_d;rl<=ir;up<=rl;dp<=dp_d;
  if(c_hold)begin hl<=lo;hh<=hi;end
  gh<=gh_d;sr<=sr_d;sx<={3{e_tx}};ur<=tq_hd;dr<=dr_d;od<=m_d;
 end
 ot_coll_tp8_col_q #(.W(128),.D(64),.MEM(1)) u_lb(.clk(clk),.rst_n(rst_n),.push(c_push[0]),.pop(c_pop[0]),.wd(rl),.hd(lb_hd),.hv(hv[0]),.ovf(ovf[0]));
 ot_coll_tp8_col_q #(.W(128),.D(64),.MEM(1)) u_pq(.clk(clk),.rst_n(rst_n),.push(c_push[1]),.pop(c_pop[1]),.wd(dp),.hd(pq_hd),.hv(hv[1]),.ovf(ovf[1]));
 ot_coll_tp8_col_q #(.W(128),.D(32),.MEM(1)) u_eq(.clk(clk),.rst_n(rst_n),.push(c_push[2]),.pop(c_pop[2]),.wd(eq_wd),.hd(eq_hd),.hv(hv[2]),.ovf(ovf[2]));
 ot_coll_tp8_col_q #(.W(128),.D(64),.MEM(1)) u_lq(.clk(clk),.rst_n(rst_n),.push(c_push[3]),.pop(c_pop[3]),.wd(lq_wd),.hd(lq_hd),.hv(hv[3]),.ovf(ovf[3]));
 ot_coll_tp8_col_q #(.W(128),.D(32),.MEM(1)) u_tq(.clk(clk),.rst_n(rst_n),.push(c_push[4]),.pop(c_pop[4]),.wd(tq_wd),.hd(tq_hd),.hv(hv[4]),.ovf(ovf[4]));
 ot_coll_tp8_col_q #(.W(128),.D(32),.MEM(1)) u_rq(.clk(clk),.rst_n(rst_n),.push(c_push[5]),.pop(c_pop[5]),.wd(dr),.hd(rq_hd),.hv(hv[5]),.ovf(ovf[5]));
endmodule

module ot_coll_tp8_col_q #(parameter integer W = 8, parameter integer D = 4, parameter integer MEM = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] wd,
    input  wire         pop,
    output wire         hv,
    output wire [W-1:0] hd,
    output reg          ovf
);
    localparam integer AB = (D > 1) ? $clog2(D) : 1;
    wire qr;                                   // the queue's own reset leaf (2-edge release)
    (* keep_hierarchy *) ot_coll_rst_leaf u_qr (.clk(clk), .arst_n(rst_n), .q(qr));
    generate if (MEM == 0) begin : g_f
        reg [W-1:0] m [0:D-1];
        reg [AB-1:0] wp, rp;
        reg [AB:0] n;
        always @(posedge clk) if (push) m[wp] <= wd;
        always @(posedge clk or negedge qr)
            if (!qr) begin wp <= 0; rp <= 0; n <= 0; ovf <= 1'b0; end
            else begin
                if (push) wp <= (wp == D - 1) ? {AB{1'b0}} : wp + 1'b1;
                if (pop && n != 0) rp <= (rp == D - 1) ? {AB{1'b0}} : rp + 1'b1;
                n <= n + (push ? 1'b1 : 1'b0) - ((pop && n != 0) ? 1'b1 : 1'b0);
                if ((push && n == D && !pop) || (pop && n == 0)) ovf <= 1'b1;
            end
        assign hv = (n != 0);
        assign hd = m[rp];
    end else begin : g_m
        localparam integer K = D / 32;
        localparam integer MW = 128;
        initial if (D % 32 != 0 || W > MW || (K & (K - 1)) != 0) $error("ot_coll_tp8_q MEM: D = 32 * 2^k, W <= 546");
        reg [AB-1:0] wp, rp;
        reg [AB:0] mcnt;
        reg rf;
        reg [1:0] obn;
        reg [W-1:0] ob0, ob1;
        reg [(K > 1 ? $clog2(K) : 1)-1:0] rsel;
        wire popv = pop && (obn != 0);
        wire [2:0] after = {1'b0, obn} + {2'b0, rf} - {2'b0, popv};
        wire rd = (mcnt != 0) && (after <= 3'd1);
        wire [MW-1:0] rdo [0:K-1];
        genvar gk;
        for (gk = 0; gk < K; gk = gk + 1) begin : g_k
            wire sel_r = (K == 1) ? 1'b1 : (rp >> 5) == gk;
            wire sel_w = (K == 1) ? 1'b1 : (wp >> 5) == gk;
            ot_sram_1r1w_32x128_m1 u_m (.clk(clk), .r_ce_in(rd && sel_r), .r_addr_in(rp[4:0]), .rd_out(rdo[gk]),
                .w_ce_in(push && sel_w), .w_addr_in(wp[4:0]), .wd_in({{(MW-W){1'b0}}, wd}), .w_mask_in({MW{1'b1}}));
        end
        wire [W-1:0] rdat = rdo[rsel][W-1:0];
        wire [1:0] n0 = obn - (popv ? 2'd1 : 2'd0);
        always @(posedge clk) begin
            if (popv) ob0 <= ob1;
            if (rf) begin if (n0 == 0) ob0 <= rdat; else ob1 <= rdat; end
            if (rd) rsel <= (K == 1) ? 0 : (rp >> 5);
        end
        always @(posedge clk or negedge qr)
            if (!qr) begin wp <= 0; rp <= 0; mcnt <= 0; rf <= 1'b0; obn <= 0; ovf <= 1'b0; end
            else begin
                if (push) wp <= wp + 1'b1;
                if (rd) rp <= rp + 1'b1;
                mcnt <= mcnt + (push ? 1'b1 : 1'b0) - (rd ? 1'b1 : 1'b0);
                rf <= rd;
                obn <= n0 + (rf ? 2'd1 : 2'd0);
                if ((push && mcnt == D && !rd) || (pop && obn == 0)) ovf <= 1'b1;
            end
        assign hv = (obn != 0);
        assign hd = ob0;
    end endgenerate
endmodule
