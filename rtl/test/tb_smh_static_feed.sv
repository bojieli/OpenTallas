`timescale 1ns/1ps
module tb_smh_static_feed;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [82:0] command=0;
 reg [1098:0] packet=0;
 wire [42:0] expected_request;
 wire fault;
 wire [1081:0] lt0,lt1;
 wire [569:0] lb0,lb1;
 wire [11:0] fm;
 ot_smh_static_feed #(.MUT(MUT)) dut(.*);
 wire [1081:0] ref_lt0,ref_lt1;
 wire [569:0] ref_lb0,ref_lb1;
 wire [11:0] ref_fm;
 smh_original_s1_reference reference_path(.clk(clk),.rst_n(rst_n),.command(command),.packet(packet),
   .lt0(ref_lt0),.lt1(ref_lt1),.lb0(ref_lb0),.lb1(ref_lb1),.fm(ref_fm));
 reg [25:0] prev_control=0;
 reg [1087:0] prev_data=0;
 reg [1081:0] want_l;
 reg [569:0] want_b;
 integer i,j;
 task tick;
 begin
   @(posedge clk);#1;
   if(lt0!==ref_lt0 || lt1!==ref_lt1 || lb0!==ref_lb0 || lb1!==ref_lb1 || fm!==ref_fm)
      $fatal(1,"original static S1 lockstep mismatch i=%0d",i);
   if(expected_request!==command[82:40])$fatal(1,"request schedule changed");
   prev_control=command[25:0];prev_data=packet[1087:0];
 end
 endtask
 initial begin
   repeat(3)@(negedge clk);
   rst_n=1;
   // Reset data flops are intentionally absent; warm pipeline before compare.
   @(posedge clk);#1;@(negedge clk);
   for(i=0;i<4096;i=i+1)begin
     command=0;packet=0;
     command[82:40]={1'b1,32'(i*128),10'(i%1024)};
     command[39:30]=10'(i%1024);command[29]=1;
     command[28:26]={i%256==0,2'(i/1024%3)};
     command[25:0]={1'b1,i%8==0,i%8==7,12'(i/8),i%256==255,3'(i%8),7'(i%128)};
     packet[1098]=1;packet[1097:1088]=10'(i%1024);
     for(j=0;j<34;j=j+1)packet[32*j+:32]=32'((i+1)*37+j*997);
     tick();
     if(fault)$fatal(1,"valid calendar fault");
     @(negedge clk);
   end
   // Missing packet is a fault and must not delay the control word.
   command[29]=1;command[25]=1;packet[1098]=0;
   tick();if(!fault)$fatal(1,"missing packet escaped");
   @(negedge clk);command=0;packet=0;tick();
   if(!lt0[1081])$fatal(1,"arrival fault dynamically gated issue");
   $display("PASS static feed 4096 consecutive productionwidth lines II1 latency2; missing arrival faults without stall");
   $finish;
 end
endmodule
