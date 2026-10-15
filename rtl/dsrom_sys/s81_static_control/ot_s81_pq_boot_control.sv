`timescale 1ns/1ps
`default_nettype none
// Boot-only real host PW36 control demultiplexer. Page6/address0 configures
// {length_minus_one12,base12}; page5/address0/payload0 primes the real reader.
// Other pages reach the actual PHW10 descriptor endpoint. No runtime ready
// selects a production edge. Missing image/calendar raises a sticky fault.
module ot_s81_pq_boot_control(
 input wire ck,rst_n,input wire[35:0]pw,input wire job_launch,busy,
 input wire image_sealed,calendar_primed,calendar_fault,
 output wire[35:0]f_desc_pw,output reg calendar_prime,
 output wire stage_start,output reg[11:0]calendar_base,
 output reg[12:0]calendar_length,output reg fault
);
 wire control=pw[27:25]==3'd5 || pw[27:25]==3'd6;
 reg configured;
 assign f_desc_pw={pw[35]&&!control,pw[34:0]};
 assign stage_start=job_launch;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin configured<=0;calendar_base<=0;calendar_length<=0;calendar_prime<=0;fault<=0;end
  else begin
   calendar_prime<=0;
   if(calendar_fault)fault<=1;
   if(pw[35]&&control)begin
    if(job_launch||busy||pw[34:28]!=0||pw[24])fault<=1;
    else if(pw[27:25]==6)begin
     if({1'b0,pw[11:0]}+{1'b0,pw[23:12]}+13'd1>4096)fault<=1;
     else begin configured<=1;calendar_base<=pw[11:0];calendar_length<={1'b0,pw[23:12]}+13'd1;end
    end else if(pw[23:0]!=0||!configured||!image_sealed)fault<=1;
    else begin
`ifndef OT_SSEQS_MUT_PQ_PRIME
     calendar_prime<=1;
`endif
    end
   end
   if(job_launch&&(!configured||!image_sealed||!calendar_primed||pw[35]))fault<=1;
  end
 end
endmodule
`default_nettype wire
