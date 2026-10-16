`timescale 1ns/1ps
`default_nettype none
// SFU bank-pair LG boundary leaf (H-SU 2026-10-15). One per VM bank pair g, hardened within 500 um of
// that pair's LG tap (die slot sfu_<q>g). It registers exactly one edge in each direction between the
// SFU core's per-pair LG port slice and the tap: request {v,sector}x2 (34 b) and drain write
// {v,sector,data,mask}x2 (562 b) toward the tap; read return {data,v}x2 (514 b) and write-done (2 b)
// toward the core. Fixed latency, no FIFO, credit or ready: the core's bridge counts these edges in
// READ_RETURN/WRITE_RETURN (ot_hgi_sfu_scheduled_engine LG_PATH). Valid bits are reset; data is not.
module ot_hgi_sfu_lg_pair_leaf (
 input wire clk,rst_n,
 input wire [33:0] c_rq,
 input wire [561:0] c_wq,
 output wire [513:0] c_rr,
 output wire [1:0] c_w_done,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done
);
 for(genvar b=0;b<2;b=b+1)begin:g_bank
  // request: bit 16 valid, 15:0 sector
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_rqv(.clk(clk),.rst_n(rst_n),.d(c_rq[17*b+16]),.q(lg_rq[17*b+16]));
  ot_hdc_delay #(.W(16),.D(1)) u_rqd(.clk(clk),.rst_n(rst_n),.d(c_rq[17*b+:16]),.q(lg_rq[17*b+:16]));
  // drain write: bit 280 valid, 279:0 {sector,data,mask}
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_wqv(.clk(clk),.rst_n(rst_n),.d(c_wq[281*b+280]),.q(lg_wq[281*b+280]));
  ot_hdc_delay #(.W(280),.D(1)) u_wqd(.clk(clk),.rst_n(rst_n),.d(c_wq[281*b+:280]),.q(lg_wq[281*b+:280]));
  // read return: bit 256 valid, 255:0 data
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_rrv(.clk(clk),.rst_n(rst_n),.d(lg_rr[257*b+256]),.q(c_rr[257*b+256]));
  ot_hdc_delay #(.W(256),.D(1)) u_rrd(.clk(clk),.rst_n(rst_n),.d(lg_rr[257*b+:256]),.q(c_rr[257*b+:256]));
 end
 ot_hdc_delay #(.W(2),.D(1),.RESET(1)) u_done(.clk(clk),.rst_n(rst_n),.d(lg_w_done),.q(c_w_done));
endmodule
`default_nettype wire
