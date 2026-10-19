`timescale 1ns/1ps
module protocol_tb;
 reg clk=0,rst_n=1,start=0,q_word=0,go=0;
 reg [511:0] f_hdr=0,q_d=0;
 reg [11:0] f_idx=0;
 wire eq_v,run; wire[9:0] rc; wire[4:0] q_have; wire[31:0] fc;
 wire [511:0] native_data,ref_data;
 reg [511:0] payload [0:15];
 reg [15:0] written=0;
 integer consumed=0,total=0,aborted=0,j,h,k,early=0;
 controller_vehicle ctrl(clk,rst_n,start,q_word,go,eq_v,rc,q_have,run,fc);
 candidate_0 dut(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),native_data);
 reference_vehicle refm(clk,q_word,f_hdr,q_d,f_idx,rc,ref_data);
 function automatic [511:0] data(input integer job,input integer head);
  integer b;
  for(b=0;b<16;b++) data[32*b+:32]=32'h41400001 ^ (32'(job)<<21) ^ (32'(head)<<11) ^ 32'(b<<2);
 endfunction
 task automatic tick(input bit wr,input integer head,input integer job,input bit st,input bit g);
 begin
  clk=0;q_word=wr;f_hdr='0;f_hdr[448]=1'(head>>3);f_idx=12'((head&7)<<4);q_d=data(job,head);start=st;go=g;#2;
  // Actual engine samples the PRE-edge registered q_v and registered macro output.
  if(eq_v) begin
   if(!written[consumed]) $fatal(1,"FIRST_USE_FAIL head=%0d",consumed);
   if(native_data!==payload[consumed] || ref_data!==payload[consumed]) $fatal(1,"PROTOCOL_DATA_FAIL head=%0d",consumed);
   consumed++;total++;
  end
  clk=1;#2;
  if(st) written=0;
  if(wr) begin written[head]=1;payload[head]=q_d;end
  clk=0;#1;
 end
 endtask
 task automatic reset_occupied;
 begin
  clk=0;q_word=0;go=0;start=0;rst_n=0;#2;
  if(eq_v || run || q_have!=0 || rc!=0) $fatal(1,"RESET_INVALIDATION_FAIL");
  written=0;consumed=0;#2;rst_n=1;
 end
 endtask
 initial begin
  if(!$value$plusargs("early=%d",early)) early=0;
  reset_occupied();
  for(j=1;j<=4;j++) begin
   tick(0,0,j,1,0);consumed=0;
   for(h=0;h<(early?15:16);h++) tick(1,h,j,0,0);
   tick(0,0,j,0,1);
   if(early) begin
    if(!fc[9]) $fatal(1,"EARLY_GO_GUARD_MISSING");
    $fatal(1,"EARLY_GO_FAULT_OBSERVED q_have=%0d",q_have);
   end
   if(fc) $fatal(1,"UNEXPECTED_PARENT_FAULT code=%h",fc);
   if(j==2) begin
    // Reset an active, occupied job after seven real engine q captures.
    while(consumed<7) tick(0,0,j,0,0);
    aborted++;
    reset_occupied();
    for(k=0;k<5;k++) tick(0,0,j,0,0);
   end else begin
    for(k=0;k<20;k++) tick(0,0,j,0,0);
    if(consumed!=16) $fatal(1,"PROTOCOL_HEAD_COUNT_FAIL got=%0d",consumed);
   end
  end
  if(total!=55 || aborted!=1) $fatal(1,"PROTOCOL_COVERAGE_FAIL");
  $display("QMEM8_PROTOCOL_PASS captures=%0d complete_jobs=3 aborted_jobs=1 occupied_reset=1 original_GO_to_head_age=unchanged",total);
  $finish;
 end
endmodule
