`timescale 1ns/1ps
module tb_pv_identity;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,cv=0,valid=0,go=0;
 reg[19:0]owner;reg[9:0]user_id;reg[7:0]tag_id;reg[1:0]quarter;reg[3:0]tile;
 wire[439:0]p,p0;wire bad,bad0;
 dsdv_pv_source_identity #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_owner(owner),.cfg_valid(valid),.launch(go),.user_id(user_id),.tag_id(tag_id),.quarter(quarter),.tile(tile),.position(21'd777),.provenance(p),.bad(bad));
 dsdv_pv_source_identity off(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_owner(owner),.cfg_valid(valid),.launch(go),.user_id(user_id),.tag_id(tag_id),.quarter(quarter),.tile(tile),.position(21'd777),.provenance(p0),.bad(bad0));
 task tick;@(negedge clk);endtask
 initial begin
  repeat(3)tick();rst_n=1;user_id=10'h345;tag_id=8'h87;quarter=2;tile=9;owner={2'd1,user_id,tag_id};
  tick();cv=1;valid=1;tick();cv=0;go=1;tick();go=0;
  if(p!=={392'd0,21'd777,1'b1,4'd9,2'd2,2'd1,10'h345,8'h87})$fatal(1,"IDENTITY_START");
  owner={2'd2,user_id,tag_id};quarter=3;tile=15;cv=1;tick();cv=0;
  if(p[19:0]!=={2'd1,user_id,tag_id} || p[25:20]!=={4'd9,2'd2})$fatal(1,"IDENTITY_CFG_RELABELED_OLD_DRAIN");
  go=1;tick();go=0;if(p[19:0]!==owner || p[25:20]!=={4'd15,2'd3})$fatal(1,"IDENTITY_NEXT");
  tag_id=tag_id^1;go=1;#0.1;if(!bad)$fatal(1,"IDENTITY_WRONG_TAG_NOT_CAUGHT");tick();go=0;if(p[26])$fatal(1,"IDENTITY_INVALID_LAUNCH_STAMPED");
  if(p0!==0 || bad0)$fatal(1,"IDENTITY_DEFAULT_CHANGED");
  rst_n=0;tick();rst_n=1;go=1;#0.1;if(!bad)$fatal(1,"IDENTITY_RESET_STALE");tick();go=0;
  $display("IDENTITY_PASS sourceGO stamp default0 cfg-relabel wrongtag resetstale");$finish;
 end
endmodule
