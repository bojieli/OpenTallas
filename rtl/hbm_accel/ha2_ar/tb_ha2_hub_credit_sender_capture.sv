`timescale 1ns/1ps
module tb_ha2_hub_credit_sender_capture #(parameter integer MUTANT=0, STALL=1);
 localparam integer W=544,INJ=2,D=35,ROWS=192;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 wire [INJ-1:0] issue_ready,arrive_v,send_v,hub_idle;
 reg [INJ-1:0] issue_v=0,receiver_ready=0;
 reg [INJ*W-1:0] source_data=0;
 wire [INJ*W-1:0] arrive_data,send_data;
 wire quiet,fault;
 integer issued[0:INJ-1],received[0:INJ-1];
 integer cycle=0,stalls=0,first_issue=-1,last_receive=-1;
 function automatic [W-1:0] row(input integer lane,n);
  for(integer j=0;j<W/32;j=j+1)row[32*j+:32]=32'h10203040^(lane<<24)^(n<<8)^j;
 endfunction
 for(genvar i=0;i<INJ;i=i+1)begin:g_pipe
  ot_ha2_delay_quiet #(.W(W),.D(D)) delay_pipe(.clk(clk),.rst_n(rst_n),
   .v_in(issue_v[i]),.d_in(source_data[i*W+:W]),.quiet(hub_idle[i]),
   .v_out(arrive_v[i]),.d_out(arrive_data[i*W+:W]));
 end
 ot_ha2_hub_credit_sender_capture #(.CAPTURE(1),.W(W),.INJ(INJ),.AW(6),.MUTANT(MUTANT)) dut
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(arrive_v),
   .arrival_data(arrive_data),.receiver_ready(receiver_ready),.issue_ready(issue_ready),
   .send_v(send_v),.send_data(send_data),.quiet(quiet),.fault(fault));
 initial begin
  for(integer i=0;i<INJ;i=i+1)begin issued[i]=0;received[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<2000;cycle=cycle+1)begin
   @(negedge clk);
   // Long initial stop fills every reservation, including35 cycles still on wire.
   receiver_ready[0]=!STALL || ((cycle>=220)&&(cycle%5!=0));
   receiver_ready[1]=!STALL || ((cycle>=260)&&(cycle%7<3));
   issue_v=0;
   if(&issue_ready)for(integer i=0;i<INJ;i=i+1)if(issued[i]<ROWS)begin
    issue_v[i]=1;source_data[i*W+:W]=row(i,issued[i]);end
   if(!(&issue_ready)&&issued[0]<ROWS)stalls=stalls+1;
   @(posedge clk);
   for(integer i=0;i<INJ;i=i+1)if(issue_v[i])begin
    issued[i]=issued[i]+1;if(first_issue<0)first_issue=cycle;end
   #1;
   if(fault)$fatal(1,"CREDIT_FAIL reservation or FIFO fault cycle=%0d",cycle);
   for(integer i=0;i<INJ;i=i+1)if(send_v[i])begin
    if(!receiver_ready[i])$fatal(1,"CREDIT_FAIL send without prior-edge receiver credit");
    if(received[i]>=issued[i] || send_data[i*W+:W]!==row(i,received[i]))
     $fatal(1,"CREDIT_FAIL lost/duplicated/reordered payload lane=%0d row=%0d",i,received[i]);
    received[i]=received[i]+1;last_receive=cycle;
   end
   if(received[0]==ROWS&&received[1]==ROWS)begin
    @(negedge clk);issue_v=0;repeat(3)@(negedge clk);
    if(!quiet || !(&hub_idle) || (STALL&&stalls==0))$fatal(1,"CREDIT_FAIL quiet/stall coverage");
    $display("PASS_HA2_HUB_CREDIT_CAPTURE rows=%0d lanes=%0d width=%0d flight=%0d stalls=%0d cycles=%0d",ROWS,INJ,W,D,stalls,last_receive-first_issue+1);
    $finish;
   end
  end
  $fatal(1,"CREDIT_FAIL simulation cycle bound; rows %0d/%0d",received[0],received[1]);
 end
endmodule
