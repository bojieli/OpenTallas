`timescale 1ns/1ps
`default_nettype none
// One actual source quarter per root: 53 x (32 data + one matching mask).
// Four leaves replace one original 53 x (128 data + four masks) pin register.
// 1,749 data/mask flops per leaf; same one-edge observation calendar.
module s81_a2_w0_payload33(
 input wire ck,rst_n,
 input wire [52:0] i_mask,input wire [1695:0] i_data,
 output reg [52:0] o_mask,output reg [1695:0] o_data,
 output reg [2:0] o_epoch
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck)rst_pin_q<=rst_n;
 always @(posedge ck)if(!rst_pin_q)begin
`ifdef S81_PAY33_MUT_RESET
  rr<=2'b01;
`else
  rr<=0;
`endif
 end else rr<={rr[0],1'b1};
 always @(posedge ck)begin
`ifdef S81_PAY33_MUT_MASK
  o_mask<=i_mask^53'd1;
`else
  o_mask<=i_mask;
`endif
`ifdef S81_PAY33_MUT_DATA
  o_data<=i_data^1696'd1;
`else
  o_data<=i_data;
`endif
  if(!rr[1])o_epoch<=0;else begin
`ifdef S81_PAY33_MUT_EPOCH
   o_epoch<=o_epoch+3'd2;
`else
   o_epoch<=o_epoch+3'd1;
`endif
  end
 end
endmodule
// Pure wiring wrapper. Every quarter has independent clock/reset pins and an
// observed epoch, so no old clock root or reset/epoch tail is silently tied off.
module s81_a2_w0_payload_split4(
 input wire [3:0] ck,rst_n,
 input wire [211:0] i_mask,input wire [6783:0] i_data,
 output wire [211:0] o_mask,output wire [6783:0] o_data,
 output wire [11:0] o_epoch
);
 genvar q,s;
 generate for(q=0;q<4;q=q+1)begin:quarter
  wire [52:0] mi,mo;wire [1695:0] di,dout;
  for(s=0;s<53;s=s+1)begin:source
   assign mi[s]=i_mask[4*s+q];
   assign di[32*s+:32]=i_data[128*s+32*q+:32];
   assign o_mask[4*s+q]=mo[s];
   assign o_data[128*s+32*q+:32]=dout[32*s+:32];
  end
  s81_a2_w0_payload33 u_leaf(ck[q],rst_n[q],mi,di,mo,dout,o_epoch[3*q+:3]);
 end endgenerate
endmodule
`default_nettype wire
`default_nettype none
// Explicit pure-wire epoch grouping used by the actual candidate front and its
// minimal parent-visible OR-fault proof. All 16 root epochs remain observed.
module s81_a2_payload33_epoch_groups(input wire [47:0] i_epoch,output wire [47:0] o_epoch);
`ifdef S81_PAY33_MUT_OMIT_EPOCH
 assign o_epoch={i_epoch[44:42],i_epoch[44:0]}; // drops root 15; duplicates root 14
`else
 assign o_epoch=i_epoch;
`endif
endmodule
`default_nettype wire
