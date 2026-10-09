`timescale 1ns/1ps
// cont-takeover 2026-10-09: testbench-only valid/ready views of the LINK_CREDIT=1 HC blocks.  Each wrapper keeps the
// original port list and parameters; every stream channel crosses an ot_link_credit_tb_chan (LAT link flops each way,
// a TB-side credit sender / landing receiver), so the unchanged exact benches drive the credit-relay boundary.
// MUT_CRED > 0: mean -- the TB-side senders hold that many credits too many (landing-overflow negative); join -- the TB
// sender loses its first DEPTH returned credits (lost-credit negative: the arrival stream stalls).
module ot_dsrom_hc_seed_join_lk #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,MAX_CONTEXT=1048576,ECC_PIPE=0,MACRO_CAP=0,IN_SKID=0,OUT_SKID=0,
    parameter [71:0] READ_INJECT=72'd0, parameter integer LAT=2, DEPTH=8, MUT_CRED=0
)(
    input wire clk,rst_n,
    input wire in_valid,output wire in_ready,input wire [511:0] in_data,
    input wire [USER_W-1:0] in_user,input wire [POS_W-1:0] in_position,
    input wire [EPOCH_W-1:0] in_epoch,input wire [1:0] in_capture,input wire [5:0] in_frame,input wire in_last,
    output wire out_valid,input wire out_ready,output wire [511:0] out_data,
    output wire [USER_W-1:0] out_user,output wire [POS_W-1:0] out_position,
    output wire [EPOCH_W-1:0] out_epoch,output wire [1:0] out_capture,
    output wire [5:0] out_frame,output wire out_last,output wire out_corrected,
    output wire busy,output wire fault
);
    localparam integer WI=512+USER_W+POS_W+EPOCH_W+2+6+1, WO=512+USER_W+POS_W+EPOCH_W+2+6+2;
    wire dv,dc,uv,uc,dut_fault,tf;wire [WI-1:0] dd;wire [WO-1:0] ud;
    ot_link_credit_tb_chan #(.W(WI),.DIR(0),.DEPTH(DEPTH),.LAT(LAT),.LEAK(MUT_CRED?DEPTH:0)) ci(.clk(clk),.rst_n(rst_n),
        .t_valid(in_valid),.t_ready(in_ready),.t_data({in_data,in_user,in_position,in_epoch,in_capture,in_frame,in_last}),
        .r_valid(),.r_ready(1'b0),.r_data(),.fault(),.d_valid(dv),.d_data(dd),.d_credit(dc),.u_valid(1'b0),.u_data('0),.u_credit());
    ot_link_credit_tb_chan #(.W(WO),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) co(.clk(clk),.rst_n(rst_n),
        .t_valid(1'b0),.t_ready(),.t_data('0),.r_valid(out_valid),.r_ready(out_ready),
        .r_data({out_data,out_user,out_position,out_epoch,out_capture,out_frame,out_last,out_corrected}),.fault(tf),
        .d_valid(),.d_data(),.d_credit(1'b0),.u_valid(uv),.u_data(ud),.u_credit(uc));
    wire [511:0] a;wire [USER_W-1:0] b;wire [POS_W-1:0] c;wire [EPOCH_W-1:0] d;wire [1:0] e;wire [5:0] f;wire g;
    assign {a,b,c,d,e,f,g}=dd;
    wire [511:0] oa;wire [USER_W-1:0] ob;wire [POS_W-1:0] oc;wire [EPOCH_W-1:0] od;wire [1:0] oe;wire [5:0] of_;wire og,oh;
    assign ud={oa,ob,oc,od,oe,of_,og,oh};
    ot_dsrom_hc_seed_join #(.USER_W(USER_W),.POS_W(POS_W),.EPOCH_W(EPOCH_W),.MAX_CONTEXT(MAX_CONTEXT),.ECC_PIPE(ECC_PIPE),
        .MACRO_CAP(MACRO_CAP),.LINK_CREDIT(1),.LINK_DEPTH(DEPTH),.READ_INJECT(READ_INJECT)) dut(.clk(clk),.rst_n(rst_n),
        .in_valid(dv),.in_ready(dc),.in_data(a),.in_user(b),.in_position(c),.in_epoch(d),.in_capture(e),.in_frame(f),.in_last(g),
        .out_valid(uv),.out_ready(uc),.out_data(oa),.out_user(ob),.out_position(oc),.out_epoch(od),.out_capture(oe),
        .out_frame(of_),.out_last(og),.out_corrected(oh),.busy(busy),.fault(dut_fault));
    assign fault=dut_fault|tf;
endmodule

module ot_dsrom_hc_mean_capture_lk #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,ADD_LAT=7,MUL_LAT=7,MAX_CONTEXT=1048576,ECC_PIPE=0,MACRO_CAP=0,
    parameter integer IN_SKID=0,OUT_SKID=0,SINGLE_CAPTURE=0,MUT_TREE=0,MUT_LAYER_ALIAS=0,
    parameter [71:0] READ_INJECT=72'd0, parameter integer LAT=2, DEPTH=8, MUT_CRED=0
)(
    input wire clk,rst_n,
    input wire cmd_valid, output wire cmd_ready, input wire [1:0] cmd_capture,
    input wire [USER_W-1:0] cmd_user, input wire [POS_W-1:0] cmd_position, input wire [EPOCH_W-1:0] cmd_epoch,
    input wire in_valid, output wire in_ready, input wire [7:0] in_beat, input wire [511:0] in_residuals,
    output wire out_valid, input wire out_ready, output wire [511:0] out_data,
    output wire [USER_W-1:0] out_user, output wire [POS_W-1:0] out_position, output wire [EPOCH_W-1:0] out_epoch,
    output wire [1:0] out_capture, output wire [5:0] out_frame, output wire out_last, output wire out_corrected,
    output wire capture_done, output wire [1:0] capture_done_capture,
    output wire busy, output wire fault
);
    localparam integer WC=2+USER_W+POS_W+EPOCH_W, WI=8+512, WO=512+USER_W+POS_W+EPOCH_W+2+6+2;
    wire cv,cc,iv,ic,uv,uc,dut_fault,tf;wire [WC-1:0] cd;wire [WI-1:0] id;wire [WO-1:0] ud;
    ot_link_credit_tb_chan #(.W(WC),.DIR(0),.DEPTH(DEPTH),.LAT(LAT),.CRED_BIAS(MUT_CRED)) cc_(.clk(clk),.rst_n(rst_n),
        .t_valid(cmd_valid),.t_ready(cmd_ready),.t_data({cmd_capture,cmd_user,cmd_position,cmd_epoch}),
        .r_valid(),.r_ready(1'b0),.r_data(),.fault(),.d_valid(cv),.d_data(cd),.d_credit(cc),.u_valid(1'b0),.u_data('0),.u_credit());
    ot_link_credit_tb_chan #(.W(WI),.DIR(0),.DEPTH(DEPTH),.LAT(LAT),.CRED_BIAS(MUT_CRED)) ci(.clk(clk),.rst_n(rst_n),
        .t_valid(in_valid),.t_ready(in_ready),.t_data({in_beat,in_residuals}),
        .r_valid(),.r_ready(1'b0),.r_data(),.fault(),.d_valid(iv),.d_data(id),.d_credit(ic),.u_valid(1'b0),.u_data('0),.u_credit());
    ot_link_credit_tb_chan #(.W(WO),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) co(.clk(clk),.rst_n(rst_n),
        .t_valid(1'b0),.t_ready(),.t_data('0),.r_valid(out_valid),.r_ready(out_ready),
        .r_data({out_data,out_user,out_position,out_epoch,out_capture,out_frame,out_last,out_corrected}),.fault(tf),
        .d_valid(),.d_data(),.d_credit(1'b0),.u_valid(uv),.u_data(ud),.u_credit(uc));
    wire [1:0] a;wire [USER_W-1:0] b;wire [POS_W-1:0] c;wire [EPOCH_W-1:0] d;assign {a,b,c,d}=cd;
    wire [7:0] ib;wire [511:0] ir;assign {ib,ir}=id;
    wire [511:0] oa;wire [USER_W-1:0] ob;wire [POS_W-1:0] oc;wire [EPOCH_W-1:0] od;wire [1:0] oe;wire [5:0] of_;wire og,oh;
    assign ud={oa,ob,oc,od,oe,of_,og,oh};
    wire cdone;wire [1:0] cdc;
    ot_dsrom_hc_mean_capture #(.USER_W(USER_W),.POS_W(POS_W),.EPOCH_W(EPOCH_W),.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT),
        .MAX_CONTEXT(MAX_CONTEXT),.ECC_PIPE(ECC_PIPE),.MACRO_CAP(MACRO_CAP),.LINK_CREDIT(1),.LINK_DEPTH(DEPTH),
        .SINGLE_CAPTURE(SINGLE_CAPTURE),.MUT_TREE(MUT_TREE),.MUT_LAYER_ALIAS(MUT_LAYER_ALIAS),.READ_INJECT(READ_INJECT)) dut(
        .clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_ready(cc),.cmd_capture(a),.cmd_user(b),.cmd_position(c),.cmd_epoch(d),
        .in_valid(iv),.in_ready(ic),.in_beat(ib),.in_residuals(ir),
        .out_valid(uv),.out_ready(uc),.out_data(oa),.out_user(ob),.out_position(oc),.out_epoch(od),.out_capture(oe),
        .out_frame(of_),.out_last(og),.out_corrected(oh),.capture_done(capture_done),.capture_done_capture(capture_done_capture),
        .busy(busy),.fault(dut_fault));
    assign fault=dut_fault|tf;
endmodule

module ot_dsrom_hc_input_reader_lk #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,MAX_CONTEXT=1048576,ECC_PIPE=0,PLAIN_ROWS=0,REG_IO=1,
    parameter [71:0] HOLD_INJECT=72'd0, parameter integer LAT=2, DEPTH=8
)(
    input wire clk,rst_n,
    input wire cmd_valid, output wire cmd_ready, input wire [1:0] cmd_capture, input wire [USER_W-1:0] cmd_user,
    input wire [POS_W-1:0] cmd_position, input wire [EPOCH_W-1:0] cmd_epoch, input wire [13:0] cmd_h_row,
    input wire [1:0] cmd_rank, input wire [14:0] cmd_region_rows,
    output wire mean_cmd_valid,input wire mean_cmd_ready, output wire [1:0] mean_cmd_capture,
    output wire [USER_W-1:0] mean_cmd_user, output wire [POS_W-1:0] mean_cmd_position, output wire [EPOCH_W-1:0] mean_cmd_epoch,
    output wire req_valid,input wire req_ready,output wire [13:0] req_row,
    input wire rsp_valid,input wire [511:0] rsp_data,input wire rsp_fault,
    output wire mean_valid,input wire mean_ready, output wire [7:0] mean_beat,output wire [511:0] mean_residuals,
    output wire busy,output wire fault
);
    localparam integer WC=2+USER_W+POS_W+EPOCH_W+14+2+15, WM=2+USER_W+POS_W+EPOCH_W, WB=8+512;
    wire cv,cc,mv,mc,bv,bc,qv,qc,dut_fault,f1,f2,f3;wire [WC-1:0] cd;wire [WM-1:0] md;wire [WB-1:0] bd;wire [13:0] qd;
    ot_link_credit_tb_chan #(.W(WC),.DIR(0),.DEPTH(DEPTH),.LAT(LAT)) c0(.clk(clk),.rst_n(rst_n),.t_valid(cmd_valid),.t_ready(cmd_ready),
        .t_data({cmd_capture,cmd_user,cmd_position,cmd_epoch,cmd_h_row,cmd_rank,cmd_region_rows}),
        .r_valid(),.r_ready(1'b0),.r_data(),.fault(),.d_valid(cv),.d_data(cd),.d_credit(cc),.u_valid(1'b0),.u_data('0),.u_credit());
    ot_link_credit_tb_chan #(.W(WM),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) c1(.clk(clk),.rst_n(rst_n),.t_valid(1'b0),.t_ready(),.t_data('0),
        .r_valid(mean_cmd_valid),.r_ready(mean_cmd_ready),.r_data({mean_cmd_capture,mean_cmd_user,mean_cmd_position,mean_cmd_epoch}),
        .fault(f1),.d_valid(),.d_data(),.d_credit(1'b0),.u_valid(mv),.u_data(md),.u_credit(mc));
    ot_link_credit_tb_chan #(.W(WB),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) c2(.clk(clk),.rst_n(rst_n),.t_valid(1'b0),.t_ready(),.t_data('0),
        .r_valid(mean_valid),.r_ready(mean_ready),.r_data({mean_beat,mean_residuals}),
        .fault(f2),.d_valid(),.d_data(),.d_credit(1'b0),.u_valid(bv),.u_data(bd),.u_credit(bc));
    ot_link_credit_tb_chan #(.W(14),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) c3(.clk(clk),.rst_n(rst_n),.t_valid(1'b0),.t_ready(),.t_data('0),
        .r_valid(req_valid),.r_ready(req_ready),.r_data(req_row),
        .fault(f3),.d_valid(),.d_data(),.d_credit(1'b0),.u_valid(qv),.u_data(qd),.u_credit(qc));
    wire [1:0] a;wire [USER_W-1:0] b;wire [POS_W-1:0] c;wire [EPOCH_W-1:0] d;wire [13:0] e;wire [1:0] f;wire [14:0] g;
    assign {a,b,c,d,e,f,g}=cd;
    wire [1:0] ma;wire [USER_W-1:0] mb;wire [POS_W-1:0] mcp;wire [EPOCH_W-1:0] md_;assign md={ma,mb,mcp,md_};
    wire [7:0] bb;wire [511:0] br;assign bd={bb,br};
    ot_dsrom_hc_input_reader #(.USER_W(USER_W),.POS_W(POS_W),.EPOCH_W(EPOCH_W),.MAX_CONTEXT(MAX_CONTEXT),.ECC_PIPE(ECC_PIPE),
        .PLAIN_ROWS(PLAIN_ROWS),.REG_IO(1),.LINK_CREDIT(1),.LINK_DEPTH(DEPTH),.HOLD_INJECT(HOLD_INJECT)) dut(.clk(clk),.rst_n(rst_n),
        .cmd_valid(cv),.cmd_ready(cc),.cmd_capture(a),.cmd_user(b),.cmd_position(c),.cmd_epoch(d),.cmd_h_row(e),.cmd_rank(f),
        .cmd_region_rows(g),.mean_cmd_valid(mv),.mean_cmd_ready(mc),.mean_cmd_capture(ma),.mean_cmd_user(mb),
        .mean_cmd_position(mcp),.mean_cmd_epoch(md_),.req_valid(qv),.req_ready(qc),.req_row(qd),
        .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_fault(rsp_fault),.mean_valid(bv),.mean_ready(bc),.mean_beat(bb),
        .mean_residuals(br),.busy(busy),.fault(dut_fault));
    assign fault=dut_fault|f1|f2|f3;
endmodule
