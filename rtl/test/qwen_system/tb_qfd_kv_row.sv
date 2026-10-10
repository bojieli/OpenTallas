`timescale 1ns/1ps
module tb_qfd_kv_row;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [6:0] rr=0;
 reg [31:0] h_v=0;reg [63:0] h_need=0;reg [8191:0] h_data=0;
 reg [351:0] h_tile0=0,h_tile1=0;reg [223:0] h_loc0=0,h_loc1=0;
 reg [63:0] h_sel0=0,h_sel1=0;reg [31:0] h_isk=0,h_tail=0;
 reg [127:0] h_tail_lanes=0;reg [31:0] tile_credit_return=0;
 wire [63:0] h_grant;wire [2:0] row_v;wire [842:0] row_data;wire fault;
 ot_qfd_kv_row_arb #(.ENABLE(1),.MUT_V_ATOMIC(MUT)) dut(.*);
 reg [63:0] want_grant;reg [2:0] want_v;reg [842:0] want_data;
 reg [1023:0] path;integer fd,rc,checks=0,slots=0;
 task fail;
 begin
  if(MUT)begin $display("NEG_DETECTED V half must progress independently across rows checks%0d",checks);$fatal(1);end
  $display("FAIL row checks%0d grants%h want%h v%h wantv%h fault%h",checks,h_grant,want_grant,row_v,want_v,fault);$fatal(1);
 end endtask
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"missing vectors");
  fd=$fopen(path,"r");if(!fd)$fatal(1,"missing vector file");
  repeat(3)@(negedge clk);rst_n=1;
  while(!$feof(fd))begin
   @(negedge clk);
   rc=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",rr,h_v,h_need,h_data,h_tile0,h_tile1,h_loc0,h_loc1,h_sel0,h_sel1,h_isk,h_tail,h_tail_lanes,tile_credit_return,want_grant,want_v,want_data);
   if(rc==17)begin
    #1;if(h_grant!==want_grant||fault)fail();
    @(posedge clk);#1;
    if(row_v!==want_v||fault)fail();
    for(integer j=0;j<3;j=j+1)if(want_v[j])begin
     if(row_data[j*281+:281]!==want_data[j*281+:281])fail();slots=slots+1;
    end
    checks=checks+1;
   end
  end
  @(negedge clk);rst_n=0;h_v=0;tile_credit_return=0;
  repeat(2)@(negedge clk);rst_n=1;tile_credit_return=32'h80000000;
  @(posedge clk);#1;if(!fault||row_v!=0)$fatal(1,"duplicate credit did not fail closed");
  $display("PASS row full32PC cycles%0d fragments%0d exact281bit packets, independent V halves, finite8mergedword credits; duplicate-return fail-closed",checks,slots);$finish;
 end
endmodule
