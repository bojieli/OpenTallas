`timescale 1ns/1ps
// H8 compact PVQ (4 x8 heads, 1064 bits) through the adopted 17-bank v2
// provider. The physical capacity is unchanged. This soft adapter preserves
// the raw asynchronous-read -> registered513-bit output age (one edge).
module ot_svc_pvq_h8_capture_pad #(parameter integer MUT=0)(
 input wire clk,dr_on,
 input wire[2:0]p_i,ra,wa,
 input wire[1063:0]wd,wm,
 input wire[47:0]provenance,
 input wire head_pass,
 output wire[512:0]out
);
 wire[2119:0]wide_d,wide_m;
 wire write_any=|wm;
 assign wide_d[63:0]={32'd0,wd[31:0]};
 assign wide_m[63:0]={{32{write_any}},wm[31:0]};
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:g_data
  localparam integer S=(MUT==1)?(g^1):g;
  assign wide_d[64+512*g+:512]={256'd0,wd[32+256*S+:256]};
  wire[255:0]m=wm[32+256*S+:256]&((MUT==3&&g==0)?~256'd1:{256{1'b1}});
  assign wide_m[64+512*g+:512]={{256{write_any}},m};
 end endgenerate
 assign wide_d[2119:2112]=wd[1063:1056];
 assign wide_m[2119:2112]=wm[1063:1056];
 wire[512:0]native_o;
 ot_t7_pvq_capture_v2 u_native(.clk(clk),.dr_on(dr_on),.p_i(p_i),.ra(ra),.wa(wa),
 .wd(wide_d),.wm(wide_m),.provenance(provenance),.out(native_o));
 // Source headerflags[32] comes from the CURRENT pass at the header read,
 // rather than the pass that wrote a queue entry. Capture beside native kind.
 reg pass_q;
 always @(posedge clk)if(dr_on&&p_i==0)pass_q<=(MUT==2)?!head_pass:head_pass;
 assign out=native_o[512]?(native_o | (513'(pass_q)<<32)):native_o;
endmodule
