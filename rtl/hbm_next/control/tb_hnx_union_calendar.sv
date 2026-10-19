`timescale 1ns/1ps
module tb_hnx_union_calendar;
 parameter MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,union_v=0;
 reg [13:0] cfg_addr=0; reg [80:0] cfg_data=0;
 reg [9:0] union_count=0;
 wire busy,fault,done,selected_v,launch_v;
 wire [9:0] selected_u; wire [13:0] selected_base;
 wire [15:0] launch_mask; wire [31:0] launch_record;
 ot_hnx_union_calendar #(.MUT(MUT)) dut(.*,.n_rows(5'd6),.topk(4'd6),.bank_base(14'd0),.bank_shift(5'd3));
 integer u,j,age,launches,finishes;
 task write_event(input integer addr,input integer cyc,input integer token,input bit last);
 begin
  @(negedge clk); cfg_we=1;cfg_addr=14'(addr);cfg_data={last,32'(cyc),16'h0002,32'(token)};
  @(negedge clk);cfg_we=0;
 end endtask
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  // Thirty-one distinct preinstalled banks, each reserving two P3 passes per expert.
  for(u=6;u<=36;u=u+1) begin
   write_event((u-6)*8,3,u*100,0);
   write_event((u-6)*8+1,10+u*2,u*100+1,0);
   write_event((u-6)*8+2,20+u*4,0,1);
  end
  for(u=6;u<=36;u=u+1) begin
   @(negedge clk);union_count=10'(u);union_v=1;
   @(negedge clk);union_v=0;
   if(!selected_v || selected_u!=u || selected_base!=(u-6)*8) $fatal(1,"UNION_WRONG_VARIANT U%0d selected%0d base%0d",u,selected_u,selected_base);
   launches=0;finishes=0;
   for(age=1;age<=20+u*4;age=age+1) begin
    if(fault) $fatal(1,"calendar fault U%0d age%0d",u,age);
    @(negedge clk);
    if(launch_v) begin
     if((launches==0 && (age!=3 || launch_record!=u*100)) ||
        (launches==1 && (age!=10+u*2 || launch_record!=u*100+1)) || launch_mask!=2)
      $fatal(1,"UNION_EVENT_MISMATCH U%0d age%0d record%0d",u,age,launch_record);
     launches=launches+1;
    end
    if(done) begin if(age!=20+u*4) $fatal(1,"early done");finishes=finishes+1;end
   end
   if(launches!=2 || finishes!=1 || busy) $fatal(1,"incomplete calendar");
  end
  // A range violation faults without a launch; subsequent valid layers remain executable.
  @(negedge clk);union_count=37;union_v=1;
  @(negedge clk);union_v=0;
  if(!fault || busy || selected_v || launch_v) $fatal(1,"missing U bound fault");
  $display("UNION_CALENDAR PASS variants31 launches62 fixed_latency no_ready_or_credit MUT%0d",MUT);$finish;
 end
endmodule
