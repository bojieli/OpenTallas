`timescale 1ns/1ps
`default_nettype none
module ot_hbm_sm_attn_be #(
    parameter integer CONTROL_DELAY=8,
    parameter integer SUB  = 4,
    parameter integer RPT  = 2,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer TAGW = 16,
    parameter integer NH   = 4,
    parameter integer STK  = 1              // 1: ot_hbm_accel_stack (pending lookup registered, +1 cycle); 0: ot_gpu_stack
) (
    input  wire                              clk,
    input wire rst_n,
    input wire [2:0] attn_column,
    input wire [28:0] command,
    input  wire [SUB*(2+32+TAGW)-1:0]        gin,
    input  wire [(NH-1)*(2+32+$clog2(RMAX))-1:0] qin,
    output wire [NH*(2+32+$clog2(RMAX))-1:0]     qout
);
    wire [28:0] bc;
    ot_hbm_accel_smv_chain #(.W(29),.D(CONTROL_DELAY),.RST(1)) u_control(
        .clk(clk),.rst_n(rst_n),.d(command),.q(bc));
    wire [1:0] mode=bc[27:26];
    wire clear_scores=bc[25],publish_score=bc[24];
    wire [3:0] score_index=bc[23:20];
    wire [11:0] output_row=bc[19:8];
    wire expected_score=bc[attn_column];
    initial if(RMAX!=4096 || TAGW!=16 || SUB!=4)$fatal(1,"attention BE requires source-shaped production ports");
    localparam integer GLW = 2 + 32 + TAGW;
    localparam integer RW  = $clog2(RMAX);
    localparam integer SW  = $clog2(IL);
    localparam integer QLW = 2 + 32 + RW;
    localparam integer PM  = (SUB - 1) / RPT;
    wire [SUB*GLW-1:0] tl;                 // per row, at the tree-input stage
    genvar k;
    generate for (k = 0; k < SUB; k = k + 1) begin : g_ln
        localparam integer ROW = SUB - 1 - k;
        // a lane from tile hop t = k / RPT has passed 3t pass-through registers: deskew 1 + 3 (PM - t)
        ot_hbm_accel_smv_chain #(.W(2), .D(1 + 3 * (PM - k / RPT)), .RST(1)) u_v (.clk(clk), .rst_n(rst_n),
            .d(gin[k*GLW + GLW - 2 +: 2]), .q(tl[ROW*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smv_chain #(.W(GLW-2), .D(1 + 3 * (PM - k / RPT)), .RST(0)) u_d (.clk(clk), .rst_n(rst_n),
            .d(gin[k*GLW +: GLW-2]), .q(tl[ROW*GLW +: GLW-2]));
    end endgenerate
    wire              tv_in = tl[GLW - 1];                  // row 0's valid
    wire [TAGW-1:0]   tt_in = tl[TAGW-1:0];                 // row 0's tag
    wire [SUB*32-1:0] td_in;
    wire [SUB-1:0]    tf_in;
    genvar sp;
    generate for (sp = 0; sp < SUB; sp = sp + 1) begin : g_td
        assign td_in[32*sp +: 32] = tl[sp*GLW + TAGW +: 32];
        assign tf_in[sp] = tl[sp*GLW + GLW - 2];
    end endgenerate
    reg gfault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gfault <= 1'b0;
        else gfault <= |tf_in;
    wire tv, tf;
    wire [31:0] ty;
    wire [TAGW-1:0] tt;
    ot_gpu_tree #(.N(SUB), .TAGW(TAGW), .ALAT(7)) u_comb (.clk(clk), .rst_n(rst_n), .v(tv_in && mode<2), .d(td_in),
                                                          .tag(tt_in), .ov(tv), .y(ty), .otag(tt), .fault(tf));
    wire kv, kf;
    wire [31:0] ky;
    wire [RW-1:0] krow;
    generate if (STK != 0) begin : g_hs
        ot_hbm_accel_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(kv), .y(ky), .otag(krow), .fault(kf));
    end else begin : g_gs
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(kv), .y(ky), .otag(krow), .fault(kf));
    end endgenerate
    reg cf_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cf_q <= 1'b0;
        else cf_q <= gfault | tf | kf;
    // Bounded real score landing. DS uses one selected row slot/column;
    // Qwen paired columns retain two selected leaves for each of8slots.
    // Publication is a compiler pulse; a missing score faults, never stalls.
    reg [31:0] scores[0:15];
    reg [15:0] score_valid;
    reg score_fault;
    integer z;
    wire [11:0] row_base=tt_in[15:4];
    reg [31:0] pv_scalar;
    reg [11:0] pv_row;
    reg pv_present,pv_collision;
    always @(*)begin
        pv_scalar=0;pv_row=0;pv_present=0;pv_collision=0;
        for(integer j=0;j<4;j=j+1)if(tl[j*GLW+GLW-1])begin
            if(pv_present)pv_collision=1;
            pv_present=1;pv_scalar=td_in[32*j+:32];pv_row=tl[j*GLW+4+:12];
        end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin score_valid<=0;score_fault<=0;end
        else begin
            if(clear_scores)score_valid<=0;
            if(mode==1 && kv && krow[2:0]==attn_column)begin scores[0]<=ky;score_valid[0]<=1;end
            if(mode==2 && tv_in)begin
                for(z=0;z<4;z=z+1)if((z%2)==attn_column[0])begin
                    scores[{row_base[4:2],1'b0}+(z/2)]<=td_in[32*z+:32];
                    score_valid[{row_base[4:2],1'b0}+(z/2)]<=1;
                end
            end
            if(publish_score && (mode==1 || mode==2) && expected_score &&
               !score_valid[mode==1?0:score_index])score_fault<=1;
            if(mode==3 && pv_collision)score_fault<=1;
            if(bc[28])score_fault<=1;
        end
    wire own_v=mode==0?kv:mode==3?pv_present:publish_score;
    wire [31:0] own_y=mode==0?ky:mode==3?pv_scalar:
        expected_score?scores[mode==1?0:score_index]:32'd0;
    wire [11:0] own_row=mode==0?krow:mode==3?pv_row:output_row;
    ot_hbm_accel_smh_kreg #(.W(2),.RST(1)) u_q0v(.clk(clk),.rst_n(rst_n),.en(1'b1),
        .d({own_v,cf_q|score_fault|(mode==3&&pv_collision)}),.q(qout[QLW-2+:2]));
    ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_q0d(.clk(clk),.rst_n(rst_n),.en(1'b1),
        .d({own_y,own_row}),.q(qout[0+:QLW-2]));
    genvar ln;
    // (margin m2) pass lanes land at the qin pins and launch from a second register at the qout pins (+1 per hop)
    generate for (ln = 1; ln < NH; ln = ln + 1) begin : g_q
        wire [QLW-1:0] ql;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW + QLW - 2 +: 2]), .q(ql[QLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW +: QLW-2]), .q(ql[0 +: QLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(ql[QLW - 2 +: 2]), .q(qout[ln*QLW + QLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(ql[0 +: QLW-2]), .q(qout[ln*QLW +: QLW-2]));
    end endgenerate
endmodule
`default_nettype wire
