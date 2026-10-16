`timescale 1ns/1ps
`default_nettype none
// Actual control4 r1 TT-109.37ps: reset qualified all53 valid bits before deep prefix trees.
// Calculate prefix from raw pin-register values; qualify only final enables/bad. No exception or data cycle added.
// ID merge is a onehot OR: ascending-source prefix admits at most one source per (bank,slot); illegal overflow faults.
module s81_a2f_control_resetlocal #(parameter integer NSRC=53)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output reg [4*168-1:0] ids,output reg [31:0] dr_v,output reg [63:0] dr_s,output reg [3:0] fault
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck_control) rst_pin_q<=rst_n;
 always @(posedge ck_control)if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
`ifdef S81_A2F_MUT_HELD_RESET
 wire rn=1'b1;
`else
 wire rn=rr[1];
`endif
 reg [2:0] control_epoch,own_epoch_q,header_pin;
 reg [11:0] payload_pin;
 always @(posedge ck_control)begin
  header_pin<=header_epoch;payload_pin<=payload_epoch;own_epoch_q<=control_epoch;
  if(!rn)control_epoch<=0;else control_epoch<=control_epoch+3'd1;
 end
 wire phase_bad=(header_pin!=own_epoch_q) ||
   (payload_pin[2:0]!=own_epoch_q) || (payload_pin[5:3]!=own_epoch_q) ||
   (payload_pin[8:6]!=own_epoch_q) || (payload_pin[11:9]!=own_epoch_q);
 reg [2*NSRC-1:0] lane;reg [NSRC-1:0] lv;
 // Monotone threshold code: bit0=count>=1, bit1=count>=2, bit2=count>=3.
 // A balanced merge uses Boolean thresholds instead of six levels of binary add/carry/saturation.
 function automatic [2:0] threshold3(input [2:0] a, input [2:0] b);
  begin threshold3[0]=a[0]|b[0];
   threshold3[1]=a[1]|b[1]|(a[0]&b[0]);
   threshold3[2]=a[2]|b[2]|(a[1]&b[0])|(a[0]&b[1]);
  end
 endfunction
 localparam integer NP = 64;
 reg rn_pin_d;
 reg [NSRC-1:0] raw_src_v;wire [NSRC-1:0] s_v=raw_src_v; reg [8*NSRC-1:0] s_bank;
 always @(posedge ck_control) begin
  s_bank <= src_bank;
  raw_src_v <= src_v; rn_pin_d <= rn;
 end
 reg [NSRC-1:0] lane_v_d; reg [2*NSRC-1:0] lane_d; reg lane_bad_d;
 always @* begin : p_lane integer c, d, w, k; reg [4:0] bc, bd; reg [2:0] t [0:NP-1]; reg [1:0] n;
  lane_bad_d = 1'b0;
  for (c = 0; c < NSRC; c = c + 1) begin
   bc = s_bank[8*c +: 5] ^ {s_bank[8*c+5 +: 3], 2'b00};
   for (d = 0; d < NP; d = d + 1) begin
    t[d] = 3'd0;
    if (d < c) begin
     bd = s_bank[8*d +: 5] ^ {s_bank[8*d+5 +: 3], 2'b00};
     t[d] = {2'b00, s_v[d] && bd == bc};
    end
   end
   for (w = NP / 2; w >= 1; w = w / 2)
    for (k = 0; k < w; k = k + 1) t[k] = threshold3(t[2*k], t[2*k+1]);
   n = t[0][2] ? 2'd3 : t[0][1] ? 2'd2 : t[0][0] ? 2'd1 : 2'd0;
   lane_d[2*c +: 2] = n;
   lane_v_d[c] = rn_pin_d && s_v[c] && n != 2'd3;
   if (s_v[c] && n == 2'd3) lane_bad_d = 1'b1;
  end
  lane_bad_d = lane_bad_d && rn_pin_d;
 end
 reg [8*NSRC-1:0] bank_d;
 reg lane_bad;
 always @(posedge ck_control)begin
  bank_d<=s_bank;lane<=lane_d;
  if(!rn)begin lv<=0;lane_bad<=0;end
  else begin lv<=lane_v_d;lane_bad<=lane_bad_d;end
 end
 genvar q;
 generate for(q=0;q<4;q=q+1)begin:quarter
  localparam integer BASE=8*q;
  reg [167:0] id_d;reg [23:0] id_valid;
  integer g,c;reg [4:0] bc;
  always @*begin
   id_d=0;id_valid=0;bc=0;
   for(g=0;g<24;g=g+1)for(c=0;c<NSRC;c=c+1)begin
    bc=bank_d[8*c+:5]^{bank_d[8*c+5+:3],2'b00};
`ifdef S81_A2F_MUT_BASE
    if(lv[c] && bc==((BASE+8)%32)+g/3 && lane[2*c+:2]==g%3)begin
`else
    if(lv[c] && bc==BASE+g/3 && lane[2*c+:2]==g%3)begin
`endif
     id_d[g*7+:6]=id_d[g*7+:6] | c[5:0];id_d[g*7+6]=1;
    end
   end
`ifdef S81_A2C_MUT_IDBIT
   id_d[0]=~id_d[0];
`endif
   for(g=0;g<24;g=g+1)id_valid[g]=ids[168*q+g*7+6];
  end
  always @(posedge ck_control)if(!rn)ids[168*q+:168]<=0;else ids[168*q+:168]<=id_d;
  reg [23:0] h0,h1,h2;
  reg [7:0] drain_v_d;reg [15:0] drain_s_d;reg drain_bad;
  integer b;reg l0,l1,l2;
  always @*begin
   drain_v_d=0;drain_s_d=0;drain_bad=0;l0=0;l1=0;l2=0;
   for(b=0;b<8;b=b+1)begin
    l0=h0[3*b];l1=h1[3*b+1];l2=h2[3*b+2];
    drain_v_d[b]=l0|l1|l2;
    drain_s_d[2*b+:2]=l0?0:l1?1:2;
    if((l0&&l1)||(l0&&l2)||(l1&&l2))drain_bad=1;
   end
  end
  always @(posedge ck_control)begin
   if(!rn)begin h0<=0;h1<=0;h2<=0;dr_v[8*q+:8]<=0;dr_s[16*q+:16]<=0;fault[q]<=0;end
   else begin
    h0<=id_valid;h1<=h0;h2<=h1;
    dr_v[8*q+:8]<=drain_v_d;dr_s[16*q+:16]<=drain_s_d;
    fault[q]<=fault[q]|lane_bad|drain_bad|phase_bad;
   end
  end
 end endgenerate
endmodule

module s81_a2f_control4_resetlocal(
 input wire ck_control,rst_n,input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [671:0] ids,output wire [31:0] dr_v,output wire [63:0] dr_s,output wire [3:0] fault
);
 s81_a2f_control_resetlocal #(.NSRC(53)) u_impl(ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule
`default_nettype wire
