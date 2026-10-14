`timescale 1ns/1ps
// Eight-entry true own-flop landing root. Pop carries the exact published
// head epoch. A delayed/stale command cannot retire a different flit.
module ot_hcoll_landing545 #(parameter integer MUT=0)(
 input wire clk,rst_n,push,input wire[544:0]data,
 input wire pop,input wire[7:0]pop_epoch,
 output reg valid,output wire[544:0]head,output reg[7:0]head_epoch,output reg fault
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg push_pin,pop_pin;reg[544:0]data_pin;reg[7:0]epoch_pin,epoch;reg[3:0]count;
 reg[2:0]wp;reg[544:0]mem[0:7];
 wire retire=pop_pin&&(count!=0)&&((MUT==1)||(epoch_pin==epoch));
 always @(posedge clk)begin data_pin<=data;epoch_pin<=pop_epoch;end
 // Local memory payload has no reset-derived write enable.
 always @(posedge clk)if(push_pin)mem[wp]<=data_pin;
 for(genvar s=0;s<18;s=s+1)begin:g_head
  localparam integer LO=s*32,WW=(545-LO<32)?545-LO:32;
  (* keep *)reg[2:0]rp;reg[WW-1:0]q;
  always @(posedge clk or negedge rr[0])if(!rr[0])rp<=0;else if(retire)rp<=rp+1'b1;
  always @(posedge clk)q<=mem[rp][LO+:WW];
  assign head[LO+:WW]=q;
 end
 always @(posedge clk or negedge rr[0])begin
  if(!rr[0])begin push_pin<=0;pop_pin<=0;epoch<=0;count<=0;wp<=0;valid<=0;head_epoch<=0;fault<=0;end
  else begin
   push_pin<=push;pop_pin<=pop;valid<=count!=0;head_epoch<=epoch;
   if(push_pin)wp<=wp+1'b1;
   if(retire)epoch<=epoch+1'b1;
   count<=count+4'(push_pin)-4'(retire);
   if(push_pin&&count==8&&!retire)fault<=1;
  end
 end
endmodule
