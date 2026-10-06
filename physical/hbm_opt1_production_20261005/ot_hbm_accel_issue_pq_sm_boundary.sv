`timescale 1ns/1ps
// Physical cut of production SM: unchanged issue instance, s1 and four DS control/address chains.
// Weight data/columns/stack/queue outside cut. Does not establish full SM timing.
module ot_hbm_accel_issue_pq_sm_boundary #(parameter integer ENABLE=0, PQ_ENABLE=0)(
 input wire clk,rst_n,h_start,h_gs,w_valid,sv,h_release,
 input wire [12:0] h_rows,input wire [15:0] h_c,input wire [7:0] h_g,
 input wire [6:0] h_xb,input wire [1:0] h_fmt,
 output wire h_pop,w_ready,busy,arrive,released,
 output wire [87:0] l1_c,output wire [31:0] l1_x
);
 localparam integer IL=8,RMAX=4096,XD=128,NOUT=4,HAZ=1,PIO=2,DS=3,SUB=4;
 localparam integer SW=3,RW=12,XW=7,TAGW=16,CW=22,XBW=8;
 reg [1:0] fmt_q;
 wire h_busy,h_arrive,h_released,adv,row_ok,i_first,i_last,i_glast;
 wire [SW-1:0] si;wire [RW:0] row_now;wire [XW-1:0] xa;
 always @(posedge clk or negedge rst_n)
   if(!rst_n) fmt_q<=2'd0; else if(h_pop) fmt_q<=h_fmt;
    ot_hbm_accel_issue_pq #(.ENABLE(ENABLE), .PQ_ENABLE(PQ_ENABLE), .IL(IL), .RMAX(RMAX), .XDEPTH(XD), .NOUT(NOUT), .HAZ(HAZ)) u_issue (
        .clk(clk), .rst_n(rst_n), .start_v(h_start), .launch(h_pop), .op_rows(h_rows), .op_c(h_c), .op_g(h_g),
        .op_gs(h_gs), .op_xb(h_xb), .op_bf(h_fmt == 2'd0),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released), .hz_wait());
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q({busy, arrive, released}));

    reg              s1_v, s1_first, s1_last;
    reg [TAGW-1:0]   s1_tag;
    reg [XW-1:0]     s1_xa;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_first <= 1'b0; s1_last <= 1'b0; end
        else begin s1_v <= adv && row_ok; s1_first <= i_first; s1_last <= i_last; end
    end
    always @(posedge clk) begin
        s1_tag <= {row_now[RW-1:0], i_glast, si};
        s1_xa <= xa; // production: absolute base already folded into registered issue cursors
    end


 wire bf_op=(fmt_q==2'd0);
 genvar sp;
 for(sp=0;sp<SUB;sp=sp+1) begin:g_sub
 wire [CW-1:0] c_in={s1_v && !bf_op,s1_v && bf_op,s1_first,s1_last,fmt_q==2'd2,bf_op,s1_tag};
 ot_hbm_accel_smv_chain #(.W(2),.D(DS),.RST(1)) u_cv(.clk(clk),.rst_n(rst_n),.d(c_in[CW-1 -: 2]),.q(l1_c[CW*sp+CW-2+:2]));
 ot_hbm_accel_smv_chain #(.W(CW-2),.D(DS),.RST(0)) u_cd(.clk(clk),.rst_n(rst_n),.d(c_in[CW-3:0]),.q(l1_c[CW*sp+:CW-2]));
 ot_hbm_accel_smv_chain #(.W(1),.D(DS),.RST(1)) u_xv(.clk(clk),.rst_n(rst_n),.d(s1_v),.q(l1_x[XBW*sp]));
 ot_hbm_accel_smv_chain #(.W(XW),.D(DS),.RST(0)) u_xa(.clk(clk),.rst_n(rst_n),.d(s1_xa),.q(l1_x[XBW*sp+1+:XW]));
 end
endmodule
