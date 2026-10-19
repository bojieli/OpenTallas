`timescale 1ns/1ps
`default_nettype none
// Model: results/rtl/hbm_pgstream_safe_1019/MODEL.md
// Kept regions contain actual local counter/phase/warm state, not buffers.
module ot_hbm_su_multirate_bridge_q_regional #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer SAFE_COPY=0, MUT=0
)(input wire serial_clk,rst_n,
 input wire [RQ_BITS-1:0] serial_rq,input wire [WQ_BITS-1:0] serial_wq,
 output wire [RR_BITS-1:0] serial_rr,output wire serial_done,
 output wire [RQ_BITS-1:0] rq_b0,rq_b1,output wire [WQ_BITS-1:0] wq_b0,wq_b1,
 input wire [RR_BITS-1:0] rr_b0,rr_b1,input wire dn_b0,dn_b1);
if(SAFE_COPY==0)begin:g_legacy
ot_hbm_su_multirate_bridge_q #(.RQ_BITS(RQ_BITS),.WQ_BITS(WQ_BITS),.RR_BITS(RR_BITS),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_original(.serial_clk(serial_clk),.rst_n(rst_n),.serial_rq(serial_rq),.serial_wq(serial_wq),.serial_rr(serial_rr),.serial_done(serial_done),.rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),.dn_b0(dn_b0),.dn_b1(dn_b1));
end else begin:g_safe
wire [RQ_BITS+WQ_BITS-1:0] request={serial_wq,serial_rq};
wire [RQ_BITS+WQ_BITS-1:0] bank0,bank1;
assign {wq_b0,rq_b0}=bank0; assign {wq_b1,rq_b1}=bank1;
for(genvar r=0;r<(RQ_BITS+WQ_BITS+14)/15;r=r+1)begin:req
 localparam integer W=((RQ_BITS+WQ_BITS-r*15)>15)?15:RQ_BITS+WQ_BITS-r*15;
 ot_hbm_pgs_request_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(serial_clk),.rst_n(rst_n),.d(request[r*15+:W]),.b0(bank0[r*15+:W]),.b1(bank1[r*15+:W]));
end
for(genvar r=0;r<(RR_BITS+14)/15;r=r+1)begin:ret
 localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
 ot_hbm_pgs_return_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(serial_clk),.rst_n(rst_n),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]),.d(serial_rr[r*15+:W]));
end
// A one-bit canonical done path; no payload fanout from this copy.
ot_hbm_su_multirate_bridge_q #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_done(
 .serial_clk(serial_clk),.rst_n(rst_n),.serial_rq(1'b0),.serial_wq(1'b0),.serial_rr(),.serial_done(serial_done),
 .rq_b0(),.rq_b1(),.wq_b0(),.wq_b1(),.rr_b0(1'b0),.rr_b1(1'b0),.dn_b0(dn_b0),.dn_b1(dn_b1));
end
wire rsel;
if(SAFE_COPY==0)assign rsel=g_legacy.u_original.rsel;
else assign rsel=g_safe.ret[0].u_copy.u_q.rsel;
endmodule
module ot_hbm_su_multirate_bridge_s_regional #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer SAFE_COPY=0, MUT=0
)(input wire stream_clk,rst_n,
 input wire [RQ_BITS-1:0] rq_b0,rq_b1,input wire [WQ_BITS-1:0] wq_b0,wq_b1,
 output wire [RR_BITS-1:0] rr_b0,rr_b1,output wire dn_b0,dn_b1,
 output wire [RQ_BITS-1:0] stream_rq,output wire [WQ_BITS-1:0] stream_wq,
 input wire [RR_BITS-1:0] stream_rr,input wire stream_done,
 output wire fault);
if(SAFE_COPY==0)begin:g_legacy
ot_hbm_su_multirate_bridge_s #(.RQ_BITS(RQ_BITS),.WQ_BITS(WQ_BITS),.RR_BITS(RR_BITS),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_original(.stream_clk(stream_clk),.rst_n(rst_n),.rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),.dn_b0(dn_b0),.dn_b1(dn_b1),.stream_rq(stream_rq),.stream_wq(stream_wq),.stream_rr(stream_rr),.stream_done(stream_done),.fault(fault));
end else begin:g_safe
wire [RQ_BITS+WQ_BITS-1:0] bank0={wq_b0,rq_b0},bank1={wq_b1,rq_b1};
wire [RQ_BITS+WQ_BITS-1:0] launched;
assign {stream_wq,stream_rq}=launched;
for(genvar r=0;r<(RQ_BITS+WQ_BITS+14)/15;r=r+1)begin:req
 localparam integer W=((RQ_BITS+WQ_BITS-r*15)>15)?15:RQ_BITS+WQ_BITS-r*15;
 ot_hbm_pgs_request_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(stream_clk),.rst_n(rst_n),.b0(bank0[r*15+:W]),.b1(bank1[r*15+:W]),.d(launched[r*15+:W]));
end
for(genvar r=0;r<(RR_BITS+14)/15;r=r+1)begin:ret
 localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
 ot_hbm_pgs_return_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(stream_clk),.rst_n(rst_n),.d(stream_rr[r*15+:W]),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]));
end
// Original actual valid/calendar fault equations; data copies do not invent validity.
ot_hbm_su_multirate_bridge_s #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_monitor(
 .stream_clk(stream_clk),.rst_n(rst_n),.rq_b0(rq_b0[RQ_BITS-1]),.rq_b1(rq_b1[RQ_BITS-1]),
 .wq_b0(wq_b0[WQ_BITS-1]),.wq_b1(wq_b1[WQ_BITS-1]),.rr_b0(),.rr_b1(),.dn_b0(dn_b0),.dn_b1(dn_b1),
 .stream_rq(),.stream_wq(),.stream_rr(stream_rr[RR_BITS-1]),.stream_done(stream_done),.fault(fault));
end
wire rd_v,rd_b;
if(SAFE_COPY==0)begin assign rd_v=g_legacy.u_original.rd_v; assign rd_b=g_legacy.u_original.rd_b;end
else begin assign rd_v=g_safe.req[0].u_copy.u_s.rd_v; assign rd_b=g_safe.req[0].u_copy.u_s.rd_b;end
endmodule
(* keep_hierarchy = 1 *) module ot_hbm_pgs_request_q_region #(parameter integer W=15,ID=0,READ_RETURN=18,WRITE_RETURN=15,MUT=0)(input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] b0,b1);
ot_hbm_su_multirate_bridge_q #(.RQ_BITS(1),.WQ_BITS(W),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_q(.serial_clk(clk),.rst_n(rst_n),.serial_rq(1'b0),.serial_wq(d),.serial_rr(),.serial_done(),.rq_b0(),.rq_b1(),.wq_b0(b0),.wq_b1(b1),.rr_b0(1'b0),.rr_b1(1'b0),.dn_b0(1'b0),.dn_b1(1'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_hbm_pgs_return_q_region #(parameter integer W=15,ID=0,READ_RETURN=18,WRITE_RETURN=15,MUT=0)(input wire clk,rst_n,input wire [W-1:0] b0,b1,output wire [W-1:0] d);
ot_hbm_su_multirate_bridge_q #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(W),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_q(.serial_clk(clk),.rst_n(rst_n),.serial_rq(1'b0),.serial_wq(1'b0),.serial_rr(d),.serial_done(),.rq_b0(),.rq_b1(),.wq_b0(),.wq_b1(),.rr_b0(b0),.rr_b1(b1),.dn_b0(1'b0),.dn_b1(1'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_hbm_pgs_request_s_region #(parameter integer W=15,ID=0,READ_RETURN=18,WRITE_RETURN=15,MUT=0)(input wire clk,rst_n,input wire [W-1:0] b0,b1,output wire [W-1:0] d);
ot_hbm_su_multirate_bridge_s #(.RQ_BITS(W),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_s(.stream_clk(clk),.rst_n(rst_n),.rq_b0(b0),.rq_b1(b1),.wq_b0(1'b0),.wq_b1(1'b0),.rr_b0(),.rr_b1(),.dn_b0(),.dn_b1(),.stream_rq(d),.stream_wq(),.stream_rr(1'b0),.stream_done(1'b0),.fault());
endmodule
(* keep_hierarchy = 1 *) module ot_hbm_pgs_return_s_region #(parameter integer W=15,ID=0,READ_RETURN=18,WRITE_RETURN=15,MUT=0)(input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] b0,b1);
ot_hbm_su_multirate_bridge_s #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(W),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_s(.stream_clk(clk),.rst_n(rst_n),.rq_b0(1'b0),.rq_b1(1'b0),.wq_b0(1'b0),.wq_b1(1'b0),.rr_b0(b0),.rr_b1(b1),.dn_b0(),.dn_b1(),.stream_rq(),.stream_wq(),.stream_rr(d),.stream_done(1'b0),.fault());
endmodule
`default_nettype wire
