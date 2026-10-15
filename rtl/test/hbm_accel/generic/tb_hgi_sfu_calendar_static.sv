`timescale 1ns/1ps
module tb_hgi_sfu_calendar_static;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;
 reg [2:0] cfg_stripe=0;
 reg [9:0] cfg_addr=0;
 reg [255:0] cfg_data=0;
 wire [1741:0] control;
 wire cv,active,done,fault;
 wire [31:0] ordinal;
 reg [1741:0] image[0:623];
 integer checks=0,last_cycle=-1,cycle=0;
 ot_hgi_sfu_calendar_static dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_v(start_v),.start_base(10'd0),.start_limit(11'd624),.start_loops(16'd1),
 .compiler_control(control),.control_v(cv),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
 initial begin
  $readmemh(`SFU_IMAGE,image);
  repeat(8)@(negedge clk);rst_n=1;
  for(integer p=0;p<624;p++)for(integer s=0;s<8;s++)begin
   cfg_we=1;cfg_addr=10'(p);cfg_stripe=3'(s);
   cfg_data=(256'hc7a1<<240)|(256'(p)<<224)|256'(image[p]>>(223*s));
   // Clear bits outside the protected payload, then restore magic and PC.
   if(s==7)cfg_data=(cfg_data&((256'd1<<181)-1))|(256'hc7a1<<240)|(256'(p)<<224);
   else cfg_data=(cfg_data&((256'd1<<223)-1))|(256'hc7a1<<240)|(256'(p)<<224);
   if($test$plusargs("MUT_PC") && p==5 && s==3)cfg_data[224]=~cfg_data[224];
   @(negedge clk);
  end
  cfg_we=0;repeat(3)@(negedge clk);
  start_v=1;@(negedge clk);start_v=0;
  repeat(640)begin
   @(negedge clk);cycle++;
   if(fault)$fatal(1,"SFU_PROGRAM_IDENTITY");
   if(cv)begin
    if(ordinal!=checks || control!==image[checks])$fatal(1,"SFU_PROGRAM_WORD ordinal=%0d expected=%0d",ordinal,checks);
    if(last_cycle>=0 && cycle!=last_cycle+1)$fatal(1,"SFU_PROGRAM_BUBBLE");
    last_cycle=cycle;checks++;
   end
  end
  if(checks!=624)$fatal(1,"SFU_PROGRAM_COUNT %0d",checks);
  $display("PASS SFU actual8SRAM protected programme controls=%0d width=1742 payload=7x223+181 no_bubbles=1",checks);$finish;
 end
endmodule
