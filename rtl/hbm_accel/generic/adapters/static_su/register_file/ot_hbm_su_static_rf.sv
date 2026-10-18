`timescale 1ns/1ps
`default_nettype none
// Actual 256-word reduction/scalar register file, 64 independently clocked
// banks of four words. Six coherent bounded flop replicas per bank provide
// gather/A/B/C/D/drain read classes. No reset on payload and no written-bit
// fiction: compiler lifetime proof must exclude reads before producer capture.
// Pin sample n -> read pins n+2, write commit n+1; every edge is a fixed slot.
module ot_hbm_su_static_rf_bank #(parameter integer READERS=6,MUT_COHERENCE=0)(
 input wire clk,rst_n,input wire[READERS-1:0]read_v,
 input wire[READERS*2-1:0]read_addr,output reg[READERS*32-1:0]read_data,
 output reg[READERS-1:0]read_return,
 input wire write_v,input wire[1:0]write_addr,input wire[31:0]write_data
);
 reg[READERS-1:0]rv_pin,rv_mem;
 reg[READERS*2-1:0]ra_pin;
 reg wv_pin;reg[1:0]wa_pin;reg[31:0]wd_pin;
 reg[READERS*32-1:0]raw;
 always @(posedge clk)begin ra_pin<=read_addr;wa_pin<=write_addr;wd_pin<=write_data;read_data<=raw;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rv_pin<=0;rv_mem<=0;read_return<=0;wv_pin<=0;end
  else begin rv_pin<=read_v;rv_mem<=rv_pin;read_return<=rv_mem;wv_pin<=write_v;end
 end
 for(genvar r=0;r<READERS;r=r+1)begin:g_replica
  (* keep *) reg[31:0]v0,v1,v2,v3;
  always @(posedge clk)begin
   if(wv_pin&&!(MUT_COHERENCE!=0&&r==READERS-1))case(wa_pin)
    0:v0<=wd_pin;1:v1<=wd_pin;2:v2<=wd_pin;3:v3<=wd_pin;
   endcase
   if(rv_pin[r])case(ra_pin[r*2+:2])
    0:raw[r*32+:32]<=v0;1:raw[r*32+:32]<=v1;2:raw[r*32+:32]<=v2;3:raw[r*32+:32]<=v3;
   endcase
  end
 end
endmodule
module ot_hbm_su_static_rf #(parameter integer BANKS=64,READERS=6,MUT_COHERENCE=0)(
 input wire[BANKS-1:0]clk_bank,input wire rst_n,
 input wire[BANKS*READERS-1:0]read_v,input wire[BANKS*READERS*2-1:0]read_addr,
 output wire[BANKS*READERS*32-1:0]read_data,output wire[BANKS*READERS-1:0]read_return,
 input wire[BANKS-1:0]write_v,input wire[BANKS*2-1:0]write_addr,input wire[BANKS*32-1:0]write_data
);
 for(genvar b=0;b<BANKS;b=b+1)begin:g_bank
  ot_hbm_su_static_rf_bank #(.READERS(READERS),.MUT_COHERENCE(MUT_COHERENCE))u_bank(
   .clk(clk_bank[b]),.rst_n(rst_n),.read_v(read_v[b*READERS+:READERS]),.read_addr(read_addr[b*READERS*2+:READERS*2]),
   .read_data(read_data[b*READERS*32+:READERS*32]),.read_return(read_return[b*READERS+:READERS]),
   .write_v(write_v[b]),.write_addr(write_addr[b*2+:2]),.write_data(write_data[b*32+:32]));
 end
endmodule
`default_nettype wire
