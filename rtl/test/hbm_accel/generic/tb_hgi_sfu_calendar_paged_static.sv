`timescale 1ns/1ps
module tb_hgi_sfu_calendar_paged_static;
 localparam PAGE_AW=1, AW=11, NWORDS=1968, CHUNK=222, PCLO=223;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;
 reg [2:0] cfg_stripe=0;
 reg [AW-1:0] cfg_addr=0;
 reg [255:0] cfg_data=0;
 wire [1741:0] control;
 wire cv,active,done,fault;
 wire [31:0] ordinal;
 reg [1741:0] image[0:NWORDS-1];
 integer checks=0,last_cycle=-1,cycle=0;
 ot_hgi_sfu_calendar_paged_static dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_v(start_v),.start_base(11'd0),.start_limit(12'd1968),.start_loops(16'd2),
 .compiler_control(control),.control_v(cv),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
 initial begin
  $readmemh(`SFU_IMAGE,image);
  repeat(8)@(negedge clk);rst_n=1;
  for(integer p=0;p<NWORDS;p++)for(integer s=0;s<8;s++)begin
   cfg_we=1;cfg_addr=AW'(p);cfg_stripe=3'(s);
   cfg_data=256'(image[p]>>(CHUNK*s));
   if(s==7)cfg_data=(cfg_data&((256'd1<<188)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   else cfg_data=(cfg_data&((256'd1<<CHUNK)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   // Genuine global-page identity mutant: low ten PC bits remain correct.
   if($test$plusargs("MUT_PC") && p==1024 && s==3)cfg_data[PCLO+10]=~cfg_data[PCLO+10];
   @(negedge clk);
  end
  cfg_we=0;repeat(3)@(negedge clk);
  start_v=1;@(negedge clk);start_v=0;
  repeat(2*NWORDS+16)begin
   @(negedge clk);cycle++;
   if(fault)$fatal(1,"SFU_PROGRAM_IDENTITY");
   if(cv)begin
    if(ordinal!=checks || control!==image[checks%NWORDS])$fatal(1,"SFU_PROGRAM_WORD ordinal=%0d expected=%0d",ordinal,checks);
    if(last_cycle>=0 && cycle!=last_cycle+1)$fatal(1,"SFU_PROGRAM_BUBBLE");
    last_cycle=cycle;checks++;
   end
  end
  if(checks!=2*NWORDS)$fatal(1,"SFU_PROGRAM_COUNT %0d",checks);
  $display("PASS SFU actual16SRAM protected paged programme controls=%0d width=1742 payload=7x222+188 globalPC11 page1023to1024=exact loop_boundary=exact no_bubbles=1",checks);$finish;
 end
endmodule
