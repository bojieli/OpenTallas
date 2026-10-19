`timescale 1ns/1ps
`default_nettype none
// SAFE-QW-CB16: physical half-ring children, <=258 bits per child.  The full
// 514/516-bit crossing is split into two siblings, keeping each ring <=1032b.
// No schedule-dependent arbitration: free-running, equal-epoch D=4,K=2 ring.
// Keep each <=24-bit slice's select/reset registers so synthesis cannot merge
// the copies into one 258-load enable.  Two face-reset stages shift BOTH
// epochs +1 relative to qfd_c_land_model_{w,r}; data crossing remains exactly K edges.
(* keep_hierarchy = "yes" *)
module qfd_c_land_model_safe_w_slice #(parameter integer W=24)(
 input wire ck,rsi, input wire [W-1:0] i, output wire [4*W-1:0] bank, output wire [3:0] vld);
 (* keep = 1 *) reg r2;
 (* keep = 1 *) reg [3:0] sel;
 (* keep = 1 *) reg [3:0] vld_q;
 reg [W-1:0] b0,b1,b2,b3;
 always @(posedge ck) begin
  r2 <= rsi;
  if (!r2) begin sel <= 4'b0001;vld_q<=0;end
  else begin sel <= {sel[2:0],sel[3]};vld_q<=vld_q|sel;end
  if (r2 && sel[0]) b0 <= i;
  if (r2 && sel[1]) b1 <= i;
  if (r2 && sel[2]) b2 <= i;
  if (r2 && sel[3]) b3 <= i;
 end
 assign bank={b3,b2,b1,b0};
 assign vld=vld_q;
endmodule

module qfd_c_land_model_safe_w #(parameter integer W=258)(
 input wire ck,rsi, input wire [W-1:0] i, output wire [4*W-1:0] bank, output wire [4*((W+23)/24)-1:0] vld);
 (* keep = 1 *) reg rst_l0;
 always @(posedge ck) rst_l0 <= rsi;
 genvar g,s;
 generate for(g=0;g<(W+23)/24;g=g+1) begin:g_slice
  localparam integer N=(W-g*24<24)?W-g*24:24;
  wire [4*N-1:0] b;
  qfd_c_land_model_safe_w_slice #(.W(N)) u(ck,rst_l0,i[g*24+:N],b,vld[g*4+:4]);
  for(s=0;s<4;s=s+1) begin:g_bank
   assign bank[s*W+g*24+:N]=b[s*N+:N];
  end
 end endgenerate
`ifndef SYNTHESIS
 initial if(W>516) $fatal(1,"safe hard-child ring exceeds 1032b");
`endif
endmodule

(* keep_hierarchy = "yes" *)
module qfd_c_land_model_safe_r_slice #(parameter integer W=24, K=2)(
 input wire ck,rsi, input wire [4*W-1:0] bank, input wire [3:0] vld, output reg [W-1:0] o);
 (* keep = 1 *) reg r2;
 (* keep = 1 *) reg [3:0] sel;
 (* keep = 1 *) reg warm;
 reg [1:0] age;
 wire [W-1:0] chosen=(bank[0*W+:W]&{W{sel[0] & vld[0]}})
                         |(bank[1*W+:W]&{W{sel[1] & vld[1]}})
                         |(bank[2*W+:W]&{W{sel[2] & vld[2]}})
                         |(bank[3*W+:W]&{W{sel[3] & vld[3]}});
 always @(posedge ck) begin
  r2<=rsi;
  if(!r2) begin sel<=4'b0001 << ((4-K)%4); age<=0; warm<=0; end
  else begin
   sel<={sel[2:0],sel[3]}; age<=age+1'b1;
   if(age==K-1) warm<=1;
  end
  o<=warm ? chosen : {W{1'b0}};
 end
endmodule

module qfd_c_land_model_safe_r #(parameter integer W=258, K=2)(
 input wire ck,rsi, input wire [4*W-1:0] bank, input wire [4*((W+23)/24)-1:0] vld, output wire [W-1:0] o);
 (* keep = 1 *) reg rst_l0;
 always @(posedge ck) rst_l0 <= rsi;
 genvar g,s;
 generate for(g=0;g<(W+23)/24;g=g+1) begin:g_slice
  localparam integer N=(W-g*24<24)?W-g*24:24;
  wire [4*N-1:0] b;
  for(s=0;s<4;s=s+1) begin:g_bank
   assign b[s*N+:N]=bank[s*W+g*24+:N];
  end
  qfd_c_land_model_safe_r_slice #(.W(N),.K(K)) u(ck,rst_l0,b,vld[g*4+:4],o[g*24+:N]);
 end endgenerate
`ifndef SYNTHESIS
 initial if(W>516 || K<1 || K>3) $fatal(1,"invalid safe hard-child shape/epoch");
`endif
endmodule

module qfd_c_land_model_w257_safe(input wire ck,rsi,input wire [256:0] i,output wire [1027:0] bank,output wire [43:0] vld);
 qfd_c_land_model_safe_w #(.W(257)) u(.ck(ck),.rsi(rsi),.i(i),.bank(bank),.vld(vld));
endmodule

module qfd_c_land_model_w257_narrow(input wire ck,rsi,input wire [256:0] i,output wire [513:0] bank_w,bank_e,output wire [43:0] vld);
 wire [1027:0] b;assign {bank_e,bank_w}=b;
 qfd_c_land_model_safe_w #(.W(257)) u(.ck(ck),.rsi(rsi),.i(i),.bank(b),.vld(vld));
endmodule

module qfd_c_land_model_r257_safe(input wire ck,rsi,output wire [256:0] o,input wire [1027:0] bank,input wire [43:0] vld);
 qfd_c_land_model_safe_r #(.W(257)) u(.ck(ck),.rsi(rsi),.bank(bank),.vld(vld),.o(o));
endmodule

module qfd_c_land_model_r257_narrow(input wire ck,rsi,output wire [256:0] o,input wire [513:0] bank_w,bank_e,input wire [43:0] vld);
 wire [1027:0] b;assign b={bank_e,bank_w};
 qfd_c_land_model_safe_r #(.W(257)) u(.ck(ck),.rsi(rsi),.bank(b),.vld(vld),.o(o));
endmodule

module qfd_c_land_model_w258_safe(input wire ck,rsi,input wire [257:0] i,output wire [1031:0] bank,output wire [43:0] vld);
 qfd_c_land_model_safe_w #(.W(258)) u(.ck(ck),.rsi(rsi),.i(i),.bank(bank),.vld(vld));
endmodule

module qfd_c_land_model_w258_narrow(input wire ck,rsi,input wire [257:0] i,output wire [515:0] bank_w,bank_e,output wire [43:0] vld);
 wire [1031:0] b;assign {bank_e,bank_w}=b;
 qfd_c_land_model_safe_w #(.W(258)) u(.ck(ck),.rsi(rsi),.i(i),.bank(b),.vld(vld));
endmodule

module qfd_c_land_model_r258_safe(input wire ck,rsi,output wire [257:0] o,input wire [1031:0] bank,input wire [43:0] vld);
 qfd_c_land_model_safe_r #(.W(258)) u(.ck(ck),.rsi(rsi),.bank(bank),.vld(vld),.o(o));
endmodule

module qfd_c_land_model_r258_narrow(input wire ck,rsi,output wire [257:0] o,input wire [515:0] bank_w,bank_e,input wire [43:0] vld);
 wire [1031:0] b;assign b={bank_e,bank_w};
 qfd_c_land_model_safe_r #(.W(258)) u(.ck(ck),.rsi(rsi),.bank(b),.vld(vld),.o(o));
endmodule
`default_nettype wire
