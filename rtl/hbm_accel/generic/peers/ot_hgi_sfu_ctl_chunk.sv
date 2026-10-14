`timescale 1ns/1ps
// Chronological partition of actual c12 ot_hdc_v41x_ins shift semantics.
// Independent same-edge clock roots, not asynchronous domains. Unassigned physical leaf.
module ot_hgi_sfu_ctl_chunk #(
 parameter integer W=75, OFFSET=0, STAGES=138,
 parameter integer MUT_BOUNDARY=0, PIN_CAPTURE=0, STATUS_REG=0
)(
 input wire clk,rst_n,v,
 input wire [2:0] sfu,
 input wire [W-1:0] d, tail_d,
 input wire tail_v,
 output wire [W-1:0] q,
 output wire vo,coll,busy
);
 function automatic integer depth(input [2:0] fn);
  case(fn)
   0:depth=0;1:depth=94;2:depth=77;3:depth=35;
   4,5:depth=122;6:depth=276;7:depth=158;
  endcase
 endfunction
 // Optional registered injection face. Insert at depth-1 after this edge, preserving original total depth.
 reg [W-1:0] d_pin;
 reg [2:0] sfu_pin;
 reg v_pin;
 always @(posedge clk)begin d_pin<=d;sfu_pin<=sfu;end
 always @(posedge clk or negedge rst_n)if(!rst_n)v_pin<=1'b0;else v_pin<=v;
 wire [W-1:0] inject_d=PIN_CAPTURE?d_pin:d;
 wire [2:0] inject_fn=PIN_CAPTURE?sfu_pin:sfu;
 wire inject_v=PIN_CAPTURE?v_pin:v;
 reg [W-1:0] r[1:STAGES];
 reg [STAGES:1] rv;
 wire [STAGES:1] collision;
 for(genvar p=1;p<=STAGES;p++)begin:g_stage
  wire inject=inject_v && depth(inject_fn)==OFFSET+p+PIN_CAPTURE;
  wire [W-1:0] nx;
  wire nxv;
  if(p==STAGES)begin:g_tail
   assign nx=tail_d;assign nxv=MUT_BOUNDARY?1'b0:tail_v;
  end else begin:g_next
   assign nx=r[p+1];assign nxv=rv[p+1];
  end
  always @(posedge clk)r[p]<=inject?inject_d:nx;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)rv[p]<=1'b0;else rv[p]<=inject||nxv;
  assign collision[p]=inject&&nxv;
 end
 assign q=r[1];assign vo=rv[1];
 // Data/valid pins are registered. coll/busy are status reductions: registered relay stillrequired physically.
 generate if(STATUS_REG==2)begin:g_local_status_terms
  reg [STAGES:1] collision_q,occupancy_q;
  reg c,b,front_q;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin collision_q<=0;occupancy_q<=0;front_q<=0;c<=0;b<=0;end
   else begin collision_q<=collision;occupancy_q<=rv;front_q<=PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0;c<=|collision_q;b<=(|occupancy_q)||front_q;end
  assign coll=c;assign busy=b;
 end else if(STATUS_REG==1)begin:g_registered_status
  reg c,b;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin c<=1'b0;b<=1'b0;end
   else begin c<=|collision;b<=(|rv)||(PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0);end
  assign coll=c;assign busy=b;
 end else begin:g_legacy_status
  assign coll=|collision;assign busy=(|rv)||(PIN_CAPTURE&&v_pin&&depth(sfu_pin)!=0);
 end endgenerate
 initial if((W!=75&&W!=60)||STAGES!=138||(OFFSET!=0&&OFFSET!=138))
  $fatal(1,"SFU chronological chunk requires75/60bit x138stage exact partitions");
endmodule
