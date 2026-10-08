`timescale 1ns/1ps
// Opt-in SRAM-only successor. Control and arithmetic-register protection separate.
module ot_hbrom_smv_leaf_protected #(
    parameter integer PROTECT = 0,
    parameter integer SUB = 4,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 1,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 2,
    parameter integer COL = 0,
    parameter integer SP  = 0,
    parameter integer TCK = 1
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [6+TAGW-1:0]        c_in,
    input  wire [LBS*266+LSB*16-1:0] w_in,
    input  wire                     x_ce,
    input  wire [$clog2(XD)-1:0]    x_addr,
    input  wire                     b_en,
    input  wire [$clog2(XD)-1:0]    b_addr,
    input  wire [NBEAT-1:0]         b_oh,
    input  wire [2047:0]            b_data,
    output reg                      gv,
    output reg  [31:0]              gy,
    output reg  [TAGW-1:0]          gt,
    output reg                      gf
);
    generate if(PROTECT==0)begin:g_legacy
      ot_hbm_accel_smv_leaf #(.SUB(SUB),.LBS(LBS),.LSB(LSB),.NC(NC),.IL(IL),.TAGW(TAGW),
        .XD(XD),.NBEAT(NBEAT),.COL(COL),.SP(SP),.TCK(TCK)) legacy(.*);
    end else begin:g_protected
      if(SUB!=4||LBS!=2||LSB!=16||NC!=1||XD!=128||NBEAT!=2||COL!=0||SP<0||SP>3)
        initial $fatal(1,"protected leaf requires fixed full AR NC1 shape");
      localparam integer SLW=788,WSW=788,CW=6+TAGW;
      wire xv,xc,xf,xpending;
      wire leaf_control_bad;
      reg leaf_fault;
      (* keep = "true", dont_touch = "yes" *) reg leaf_fault_shadow;
      wire leaf_stop=leaf_fault||leaf_control_bad;
      wire[787:0]ix;
      ot_hbrom_xstore_protected #(.SP(SP)) storage(
        .clk(clk),.rst_n(rst_n),.read_en(x_ce&&!leaf_stop),.read_addr(x_addr),
        .write_en(b_en&&!leaf_stop),.write_addr(b_addr),.write_oh(b_oh),.write_data(b_data),
        .read_valid(xv),.read_data(ix),.corrected(xc),.fault(xf),.write_pending(xpending));
      reg[CW-1:0]c3,c4,c5,c6;
      (* keep = "true", dont_touch = "yes" *) reg[CW-1:0]cs3,cs4,cs5,cs6;
      assign leaf_control_bad=(cs3!==~c3)||(cs4!==~c4)||(cs5!==~c5)||(cs6!==~c6)||
        (leaf_fault_shadow!==~leaf_fault);
      always @(posedge clk or negedge rst_n)
       if(!rst_n)begin cs3<={CW{1'b1}};cs4<={CW{1'b1}};cs5<={CW{1'b1}};cs6<={CW{1'b1}};leaf_fault<=0;leaf_fault_shadow<=1;end
       else begin
        cs3<=~c_in;cs4<=cs3;cs5<=cs4;cs6<=cs5;
        if(leaf_control_bad)begin leaf_fault<=1;leaf_fault_shadow<=0;end
       end
      reg[WSW-1:0]w3,w4,w5,w6;
      always @(posedge clk or negedge rst_n)
        if(!rst_n)begin c3<=0;c4<=0;c5<=0;c6<=0;end
        else begin c3<=c_in;c4<=c3;c5<=c4;c6<=c5;end
      always @(posedge clk)begin w3<=w_in;w4<=w3;w5<=w4;w6<=w5;end
      wire iv_b=c6[CW-1]&&xv&&!xf&&!leaf_stop;
      wire iv_f=c6[CW-2]&&xv&&!xf&&!leaf_stop;
      wire ifirst=c6[CW-3],ilast=c6[CW-4],ifp4=c6[CW-5],ibf=c6[CW-6];
      wire[TAGW-1:0]itag=c6[TAGW-1:0];
      wire[WSW-1:0]iw=w6;
      genvar qq;
    // ---- the column macros ----
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
        if (LBS == 2 && IL == 8 && TAGW == 16) begin : g_hbd
            ot_gpu_bd_col u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq({ix[266 +: 256], ix[0 +: 256]}),
                .xe({ix[266 + 256 +: 10], ix[256 +: 10]}),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end else begin : g_sbd
            wire [LBS*256-1:0] xq_s;
            wire [LBS*10-1:0]  xe_s;
            for (qq = 0; qq < LBS; qq = qq + 1) begin : g_b
                assign xq_s[256*qq +: 256] = ix[qq*266 +: 256];
                assign xe_s[10*qq +: 10]   = ix[qq*266 + 256 +: 10];
            end
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end
        if (LSB == 16 && TAGW == 16 && IL == 8 && TCK != 0) begin : g_hardk
            ot_hbm_accel_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (LSB == 16 && TAGW == 16 && IL == 8) begin : g_hard
            ot_gpu_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (TCK != 0) begin : g_softk
            ot_hbm_accel_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else begin : g_soft
            ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end
    // ---- G1: this sub's combine-tree input, selected by the op's format (registered with the op) ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gv <= 1'b0; gf <= 1'b0; end
        else begin gv <= (bov | fov) && !xf && !leaf_stop; gf <= bfault | ffault | (bov & fov) | xf | leaf_stop; end
    always @(posedge clk) begin
        gy <= ibf ? fy : by;
        gt <= ibf ? ftag : btag;
    end
    end endgenerate
endmodule
