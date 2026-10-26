`timescale 1ns/1ps
`default_nettype none
// Static valid-only NEXT merge: ordinary local_ro payload bypasses all added
// data registers (one combinational mux). HBE alone has two registered stages:
// input predicate roots -> bank selectors, aligned with two payload captures.
// Kept hierarchy prevents synthesis merging those actual <=32 consumer roots.
module dsdv_hostb_tx(input wire ck,rst_n,
 input wire [1103:0] local_ro,forward_ro,return_ro,
 input wire forward_slot,return_slot,
 output wire [1103:0] next_ro, output reg [3:0] fault);
 wire rn;(* keep_hierarchy="yes" *) ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 wire fw=forward_ro[0]&&forward_slot;
 wire rv=return_ro[0]&&return_slot;
 wire input_collision=fw&&rv;
 wire [1:0] allowed={rv,fw}&{2{!input_collision&&fault==0}};
 wire [2:0] select_d={allowed[1],allowed[0],~(|allowed)};
 reg [532:1] f0,f1,r0,r1;
 reg [1:0] vpipe;reg [2:0] ready;
 wire output_collision=vpipe[1]&&local_ro[0];
 always @(posedge ck)begin f0<=forward_ro[532:1];f1<=f0;r0<=return_ro[532:1];r1<=r0;end
 always @(posedge ck or negedge rn)begin
   if(!rn)begin fault<=0;vpipe<=0;ready<=0;end
   else begin
     ready<={ready[1:0],1'b1};vpipe<={vpipe[0],|allowed};
     if(input_collision||output_collision)fault[0]<=1;
     if(forward_ro[0]&&!forward_slot)fault[1]<=1;
     if(return_ro[0]&&!return_slot)fault[2]<=1;
     if((forward_ro[0]&&|forward_ro[1103:533])||(return_ro[0]&&|return_ro[1103:533]))fault[3]<=1;
   end
 end
 // No dynamic arbitration: simultaneous booked HBE and ordinary beat is a fault,
 // neither is emitted. Invalid ordinary payload cannot corrupt selected HBE.
 assign next_ro[0]=ready[2]&&(local_ro[0]||vpipe[1])&&!output_collision;
 wire [8:0] roots;
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:g_root
   (* keep_hierarchy="yes" *) dsdv_hostb_select_root #(.ID(g)) u_root(.ck(ck),.rn(rn),.d(select_d),.q(roots[3*g+:3]));
 end
 for(g=0;g<74;g=g+1)begin:g_bank
   localparam integer LO=1+15*g;
   localparam integer W=(1104-LO<15)?1104-LO:15;
   wire [2:0] sel;
   (* keep_hierarchy="yes" *) dsdv_hostb_select_bank #(.ID(g)) u_sel(.ck(ck),.d(roots[3*(g/25)+:3]),.q(sel));
   wire [W-1:0] fd,rd;
   if(LO+W<=533)begin:g_payload
     assign fd=f1[LO+:W];assign rd=r1[LO+:W];
   end else if(LO>=533)begin:g_zero
     assign fd=0;assign rd=0;
   end else begin:g_split
     localparam integer P=533-LO;
     assign fd={{(W-P){1'b0}},f1[LO+:P]};assign rd={{(W-P){1'b0}},r1[LO+:P]};
   end
   assign next_ro[LO+:W]=({W{sel[0]}}&local_ro[LO+:W])|({W{sel[1]}}&fd)|({W{sel[2]}}&rd);
 end endgenerate
endmodule
module dsdv_hostb_select_root #(parameter integer ID=0)(input wire ck,rn,input wire[2:0]d,output reg[2:0]q);
 always @(posedge ck or negedge rn)if(!rn)q<=0;else q<=d;
endmodule
module dsdv_hostb_select_bank #(parameter integer ID=0)(input wire ck,input wire[2:0]d,output reg[2:0]q);
 always @(posedge ck)q<=d;
endmodule
`default_nettype wire
