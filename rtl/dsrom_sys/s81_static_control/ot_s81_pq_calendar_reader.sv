`timescale 1ns/1ps
`default_nettype none
// Source-backed paired4096x72-ROM calendar reader. Row144={reserved48,
// timestamp24,action72}. All reads use fixed2-edge launch->capture latency.
// Prime4 rows BEFORE stage_start; stage_start E0 -> timestamp0 pin at E1.
// A due row advances the immutable program, never an engine ready/completion.
module ot_s81_pq_calendar_reader #(
 parameter integer ACTION_BITS=72,END_BIT=(ACTION_BITS==75?72:69)
)(
 input wire ck,rst_n,input wire prime,input wire stage_start,
 input wire[11:0]base,input wire[12:0]length,
 output reg[11:0]rom_addr,input wire[71:0]rom_action,rom_time,
 output reg[ACTION_BITS-1:0]action,output reg active,output reg primed,output reg fault
);
 reg[143:0]rows[0:3];reg[1:0]rp,wp;reg[2:0]count;
 reg[12:0]nrows,fetch_index,consume_index;reg[11:0]base_q;
 reg[1:0]fetch_valid;reg priming;reg[23:0]age,last_timestamp;
 wire due=active&&count!=0&&rows[rp][ACTION_BITS+23:ACTION_BITS]==age;
 wire push=fetch_valid[1];
 wire fetch=(priming&&fetch_index<nrows&&fetch_index<4)||
            (due&&fetch_index<nrows);
 reg[12:0]read_a;integer k;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   rom_addr<=0;action<=0;active<=0;primed<=0;fault<=0;
   rp<=0;wp<=0;count<=0;nrows<=0;fetch_index<=0;consume_index<=0;
   fetch_valid<=0;priming<=0;base_q<=0;age<=0;last_timestamp<=0;
  end else begin
   action<=0;fetch_valid<={fetch_valid[0],fetch};
   if(prime)begin
    if(active||priming||fetch_valid!=0||length==0||length>4096||{1'b0,base}+length>4096)fault<=1;
    else begin
     nrows<=length;base_q<=base;fetch_index<=0;consume_index<=0;
     rp<=0;wp<=0;count<=0;priming<=1;primed<=0;
    end
   end
   if(fetch)begin
    read_a={1'b0,base_q}+fetch_index;rom_addr<=read_a[11:0];fetch_index<=fetch_index+1'b1;
   end
   if(push)begin
    if(count==4&&!due)fault<=1;
    rows[wp]<={rom_time,rom_action};wp<=wp+1'b1;
    if(({rom_time,rom_action} >> (ACTION_BITS+24))!=0 ||
       (({rom_time,rom_action} >> (END_BIT+1)) & ((144'd1 << (ACTION_BITS-END_BIT-1))-1))!=0)fault<=1;
    if(priming&&count+1'b1==(nrows<4?nrows:4))begin priming<=0;primed<=1;end
   end
   if(push||due)count<=count+3'(push)-3'(due);
   if(stage_start)begin
    if(!primed||active||prime)fault<=1;
    active<=1;age<=0;last_timestamp<=0;
   end
   if(active)begin
    age<=age+1'b1;
    if(age==24'hffffff||count==0||rows[rp][ACTION_BITS+23:ACTION_BITS]<age)fault<=1;
    if(due)begin
     action<=rows[rp][ACTION_BITS-1:0];rp<=rp+1'b1;consume_index<=consume_index+1'b1;
     if(consume_index!=0&&rows[rp][ACTION_BITS+23:ACTION_BITS]<=last_timestamp)fault<=1;
     last_timestamp<=rows[rp][ACTION_BITS+23:ACTION_BITS];
     if(rows[rp][END_BIT])begin
      active<=0;primed<=0;
      if(consume_index+1'b1!=nrows)fault<=1;
     end else if(consume_index+1'b1==nrows)begin active<=0;primed<=0;fault<=1;end
    end
   end
  end
 end
endmodule
`default_nettype wire
