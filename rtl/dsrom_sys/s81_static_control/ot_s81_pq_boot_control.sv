`timescale 1ns/1ps
`default_nettype none
// Boot-only real host PW36 control demultiplexer. Page6/address0 configures
// {length_minus_one12,base12}; page6/address1 sets fixed job->reprime edges24.
// Page5/address0/payload0 primes the real reader initially. Other pages reach
// the actual PHW10 descriptor endpoint. Every later prime comes from the
// programmed counter, without testing readiness. Status only raises faults.
module ot_s81_pq_boot_control(
 input wire ck,rst_n,input wire[35:0]pw,input wire job_launch,busy,
 input wire image_sealed,calendar_primed,calendar_fault,
 output reg[35:0]f_desc_pw,output reg calendar_prime,
 output wire stage_start,output reg[11:0]calendar_base,
 output reg[12:0]calendar_length,output reg fault
);
 wire control=pw[27:25]==3'd5 || pw[27:25]==3'd6;
 reg[1:0]configured;
 reg[23:0]reprime_edges,age;reg rearm_pending;
 assign stage_start=job_launch;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin f_desc_pw<=0;configured<=0;calendar_base<=0;calendar_length<=0;calendar_prime<=0;fault<=0;reprime_edges<=0;age<=0;rearm_pending<=0;end
  else begin
   calendar_prime<=0;
   f_desc_pw<={pw[35]&&!control,pw[34:0]};
   if(calendar_fault)fault<=1;
   if(pw[35]&&control)begin
    if(job_launch||busy||rearm_pending||pw[24])fault<=1;
    else if(pw[27:25]==6)begin
     if(pw[34:28]==0)begin
      if({1'b0,pw[11:0]}+{1'b0,pw[23:12]}+13'd1>4096)fault<=1;
      else begin configured[0]<=1;calendar_base<=pw[11:0];calendar_length<={1'b0,pw[23:12]}+13'd1;end
     end else if(pw[34:28]==1&&pw[23:0]!=0)begin configured[1]<=1;reprime_edges<=pw[23:0];end
     else fault<=1;
    end else if(pw[34:28]!=0||pw[23:0]!=0||configured!=3||!image_sealed)fault<=1;
    else begin
`ifndef OT_SSEQS_MUT_PQ_PRIME
     calendar_prime<=1;
`endif
    end
   end
   if(rearm_pending)begin
    age<=age+1'b1;
    if(age==reprime_edges-1'b1)begin
     rearm_pending<=0;
`ifndef OT_SSEQS_MUT_PQ_PRIME
     calendar_prime<=1;
`endif
    end
   end
   if(job_launch)begin
    if(configured!=3||!image_sealed||!calendar_primed||pw[35]||rearm_pending)fault<=1;
    // Availability never gates this fixed counter or the stage_start pin.
    age<=0;rearm_pending<=1;
   end
  end
 end
endmodule
`default_nettype wire
