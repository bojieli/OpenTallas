`timescale 1ns/1ps
`default_nettype none
// Actual consumer-side contract. Connect seq_host f_host/f_ks and Engram KS
// to these pins; source-mode selection is a genuine static configured pin.
// Physical s0N -> seqhost/Engram crossing is NOT represented as an alias:
// this separately named component adds one explicit registered landing edge.
module dsdv_hostb_landing #(parameter integer ENABLE=0)(
 input wire ck,rst_n,select_hbe,
 input wire [514:0] legacy_f_host,hbe_f_host,
 input wire [52:0] legacy_f_ks,starter_f_ks,
 output wire [514:0] seq_f_host,
 output wire [52:0] seq_f_ks,engram_f_ks,
 output reg [2:0] fault);
 generate if(ENABLE==0)begin:g_legacy
   assign seq_f_host=legacy_f_host;assign seq_f_ks=legacy_f_ks;
   assign engram_f_ks=legacy_f_ks;
   always @* fault=0;
 end else begin:g_hbe
   wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
   reg [513:0] hd;reg [51:0] kd_s,kd_e;reg hv,kv_s,kv_e;
   // Capture all opaque payload bits; reset valid only. Separate KS registers
   // are real independent captures for seqhost and Engram, never a fake token.
   wire [514:0] fh=select_hbe?hbe_f_host:legacy_f_host;
   wire [52:0] fk=select_hbe?starter_f_ks:legacy_f_ks;
   always @(posedge ck)begin hd<=fh[514:1];kd_s<=fk[51:0];kd_e<=fk[51:0];end
   always @(posedge ck or negedge rn)begin
     if(!rn)begin hv<=0;kv_s<=0;kv_e<=0;fault<=0;end
     else begin
       hv<=fh[0]&&fault==0;kv_s<=fk[52]&&fault==0;kv_e<=fk[52]&&fault==0;
       if(select_hbe && legacy_f_host[0])begin fault[0]<=1;hv<=0;end
       if(select_hbe && legacy_f_ks[52])begin fault[1]<=1;kv_s<=0;kv_e<=0;end
       if(!select_hbe && (hbe_f_host[0]||starter_f_ks[52]))fault[2]<=1;
     end
   end
   assign seq_f_host={hd,hv};assign seq_f_ks={kv_s,kd_s};assign engram_f_ks={kv_e,kd_e};
 end endgenerate
endmodule
`default_nettype wire
