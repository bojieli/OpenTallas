`timescale 1ns/1ps
`default_nettype none
// Two-entry elastic pin FIFO. The legacy r32 module name preserves its callers.
// Each <=10-bit slice owns kept circular pointers and occupancy, so ready only
// drives one pop gate per slice, and no pop condition reaches a wide data mux.
// All slices see the same clock, reset and handshake: their private state stays
// in lockstep. Public latency/ready/full behavior matches the head/tail skid.
module ot_hbm_svc_pin_skid2_r32 #(parameter integer WIDTH=1)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 localparam integer SW=10,N=(WIDTH+SW-1)/SW,NR=(N+3)/4;
 wire [N-1:0]full,empty;
 wire [NR-1:0]rn;
 ot_rst_fanout #(.N(NR)) u_reset(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 assign in_r=rn[0]&&!full[0];assign out_v=rn[0]&&!empty[0];
 for(genvar s=0;s<N;s=s+1)begin:g_slice
  localparam integer B=(WIDTH-s*SW<SW)?WIDTH-s*SW:SW;
  (* keep="true",dont_touch="true" *) reg wp,rp;
  (* keep="true",dont_touch="true" *) reg [1:0]count;
  reg [B-1:0]d0,d1;
  (* keep="true" *) wire push=in_v&&!full[s];
  (* keep="true" *) wire pop=out_r&&!empty[s];
  assign full[s]=(count==2);assign empty[s]=(count==0);
  assign out_data[s*SW+:B]=rp?d1:d0;
  always @(posedge clk or negedge rn[s/4])begin
   if(!rn[s/4])begin wp<=0;rp<=0;count<=0;end
   else begin
    if(push)wp<=!wp;
    if(pop)rp<=!rp;
    case({push,pop})
     2'b10:count<=count+1'b1;
     2'b01:count<=count-1'b1;
     default:;
    endcase
   end
  end
  always @(posedge clk)begin
   if(push&&!wp)d0<=in_data[s*SW+:B];
   if(push&&wp)d1<=in_data[s*SW+:B];
  end
 end
endmodule
`default_nettype wire
