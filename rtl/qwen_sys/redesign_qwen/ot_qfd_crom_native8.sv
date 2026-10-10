`timescale 1ns/1ps
// Opt-in functional binding. The original closed group0 executable is untouched.
// Other lane bases and the new fault collector require physical qualification.
// STRAP = 1 (qwen-1010/c 2026-10-10): all eight groups are the ONE strap tile ot_qfd_crom_gs with crom_lb = 8 g (MUT 1:
// every strap tied 0; MUT 5: group 3's strap tied to group 2's base), so the closure of one tile covers the composition.
module ot_qfd_crom_native8 #(parameter integer MUT=0, parameter integer STRAP=0)(
 input wire clk,rst_n,
 input wire [63:0] crom_re,
 input wire [1535:0] crom_addr,
 input wire [5:0] crom_stage,
 output wire [4095:0] crom_q,
 output wire fault,
 output wire [1:0] fault_code
);
 wire [7:0] gf;
 wire [15:0] gc;
 genvar g;
 generate for(g=0;g<8;g=g+1) begin: groups
  if(STRAP!=0) begin: strap_group
   ot_qfd_crom_gs #(.IMG_LB(8*g),.MUT(MUT==2&&g==7?1:0)) u(.clk(clk),.rst_n(rst_n),.crom_re(crom_re[8*g+:8]),
    .crom_addr(crom_addr[192*g+:192]),.crom_stage(crom_stage),
    .crom_lb(MUT==1?6'd0:(MUT==5&&g==3)?6'd16:6'(8*g)),
    .crom_q(crom_q[512*g+:512]),.fault(gf[g]),.fault_code(gc[2*g+:2]));
  end else if(g==0) begin: closed_group0
   ot_qfd_crom_g u(.clk(clk),.rst_n(rst_n),.crom_re(crom_re[8*g+:8]),
    .crom_addr(crom_addr[192*g+:192]),.crom_stage(crom_stage),
    .crom_q(crom_q[512*g+:512]),.fault(gf[g]),.fault_code(gc[2*g+:2]));
  end else begin: native_group
   ot_qfd_crom #(.SW(8),.LB(MUT==1?0:8*g),.MUT(MUT==2&&g==7?1:0)) u
    (.clk(clk),.rst_n(rst_n),.crom_re(crom_re[8*g+:8]),
    .crom_addr(crom_addr[192*g+:192]),.crom_stage(crom_stage),
    .crom_q(crom_q[512*g+:512]),.fault(gf[g]),.fault_code(gc[2*g+:2]));
  end
 end endgenerate
 reg [1:0] candidate;
 reg seen;
 reg [1:0] held;
 integer i;
 always @* begin
  candidate=0;
  // The original64-lane block prioritizes range, alignment, then disagreement
  // on its first global fault edge. Later faults must not overwrite that cause.
  for(i=0;i<8;i=i+1) if(gf[i]&&gc[2*i+:2]==3) candidate=3;
  for(i=0;i<8;i=i+1) if(gf[i]&&gc[2*i+:2]==2) candidate=2;
  for(i=0;i<8;i=i+1) if(gf[i]&&gc[2*i+:2]==1) candidate=1;
  if(MUT==3) begin
   for(i=0;i<8;i=i+1) if(gf[i]&&gc[2*i+:2]==3) candidate=3;
  end
 end
 assign fault=|gf;
 // Before the collector samples a first fault, expose the exact same-edge
 // cause. On the following edge the held cause prevents later tile faults
 // from changing the full64-lane first-cause ABI.
 assign fault_code=(seen&&MUT!=4)?held:candidate;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin seen<=0;held<=0;end
  else if(!seen&&fault) begin seen<=1;held<=candidate;end
 end
endmodule
