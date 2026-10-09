`timescale 1ns/1ps
// Source-aware successor. Payload and owner are held together and must cross
// the same service FIFO. Completions are returned from the per-PC source ledger,
// never inferred from aggregate completion or FIFO-pop order.
module ot_hbm_write_merge_sources #(parameter integer ENABLE=0)(
 input wire ck,rst_n,input wire[2:0] src_v,
 input wire[872:0] src_d,output wire[2:0] src_r,
 output wire svc_v,output wire[290:0] svc_d,output wire[1:0] svc_source,
 input wire svc_r,input wire[17:0] service_ack_n,
 output wire[17:0] src_ack_n
);
 generate if(!ENABLE)begin:g_off
  assign src_r=0;assign svc_v=0;assign svc_d=0;assign svc_source=0;assign src_ack_n=0;
 end else begin:g_on
  reg pending,rr;reg[290:0] payload;reg[1:0] owner;
  reg valid_choice;reg[1:0] choice;
  always @(*)begin
   valid_choice=|src_v;choice=0;
   if(src_v[0])choice=0;
   else if(src_v[1]&&src_v[2])choice=rr?2:1;
   else if(src_v[1])choice=1;
   else if(src_v[2])choice=2;
  end
  wire issue=pending&&svc_r;
  wire take=(!pending||issue)&&valid_choice;
  assign src_r=take?(3'b001<<choice):0;
  assign svc_v=pending;assign svc_d=payload;assign svc_source=owner;
  assign src_ack_n=service_ack_n;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin pending<=0;rr<=0;payload<=0;owner<=0;end
   else begin
    if(issue)pending<=0;
    if(take)begin pending<=1;payload<=src_d[choice*291+:291];owner<=choice;
     if(choice!=0)rr<=choice==1;
    end
   end
  end
 end endgenerate
endmodule
