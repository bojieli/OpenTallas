`timescale 1ps/1fs
module tb_config_snapshot;
 reg clk=0;always #416.666666667 clk=~clk;
 reg rst_n=0,in_valid=0,lock_valid=0,release_valid=0;
 reg [1:0] in_beat=0;reg [31:0] in_epoch=0,release_epoch=0;reg [15:0] in_tag=0,release_tag=0;reg[1023:0] in_data=0;
 wire in_ready,config_valid,locked,fault;wire[31:0]config_epoch;wire[15:0]config_tag;wire[2601:0]config_data;
 ot_dsrom_softmax_config_snapshot dut(.*);
 reg[3071:0] expected;integer cycle=0,checks=0,lastbeat=0;
 always @(negedge clk)cycle=cycle+1;
 task automatic reset;
  @(negedge clk);rst_n=0;in_valid=0;lock_valid=0;release_valid=0;
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  if(fault||config_valid||!in_ready)$fatal(1,"RESET");
 endtask
 task automatic prepare(input short_t);
  expected=0;
  for(integer i=10;i<2602;i=i+32)expected[i+:32]=32'h3f000000^(32'(i*1973)&32'h007fffff);
  expected[6:0]=short_t?7'd8:7'd40;expected[9:7]=short_t?3'd3:3'd6;
 endtask
 task automatic beat(input integer b);
  @(negedge clk);in_valid=1;in_beat=2'(b);in_data=expected[b*1024+:1024];in_epoch=32'h12345678;in_tag=16'h9021;
  if(!in_ready)$fatal(1,"NOT_READY");
  @(posedge clk);lastbeat=cycle;#1;
  if(config_valid)$fatal(1,"PARTIAL_VISIBLE");
  @(negedge clk);in_valid=0;in_data=0;
 endtask
 task automatic capture(input short_t);
  prepare(short_t);for(integer b=0;b<3;b=b+1)beat(b);
  wait(config_valid);#1;
  if(cycle-lastbeat!=2)$fatal(1,"SNAPSHOT_LATENCY got%0d expected2toValid",cycle-lastbeat);
  if(config_data!==expected[2601:0]||config_epoch!=32'h12345678||config_tag!=16'h9021||fault)$fatal(1,"CONFIG_EXACT");
  checks=checks+1;
 endtask
 task automatic lock;
  @(negedge clk);lock_valid=1;
  @(posedge clk);#1;if(!locked||!config_valid||fault)$fatal(1,"LOCK");
  @(negedge clk);lock_valid=0;
 endtask
 task automatic release_ok;
  @(negedge clk);release_valid=1;release_epoch=32'h12345678;release_tag=16'h9021;
  @(posedge clk);#1;if(fault||config_valid||locked||!in_ready)$fatal(1,"RELEASE");
  @(negedge clk);release_valid=0;
 endtask
 initial begin
  reset();capture(0);lock();
  repeat(20)begin @(negedge clk);in_data=~in_data;if(config_data!==expected[2601:0]||!config_valid||in_ready)$fatal(1,"IMMUTABLE");end
  release_ok();capture(1);
  // Pre-lock CE repair suppresses permission until exact snapshot is restored.
  @(negedge clk);dut.storage.code[40][3]=~dut.storage.code[40][3];#1;
  if(config_valid||fault)$fatal(1,"PRELOCK_CE_PERMISSION");
  repeat(7)@(negedge clk);
  if(!config_valid||config_data!==expected[2601:0]||fault)$fatal(1,"PRELOCK_CE_REPAIR");
  lock();
  @(negedge clk);dut.storage.code[10][3]=~dut.storage.code[10][3];#1;
  if(!fault||config_valid)$fatal(1,"LOCKED_CE_ABORT");
  reset();capture(0);
  @(negedge clk);dut.storage.code[0][0]=~dut.storage.code[0][0];dut.storage.code[0][1]=~dut.storage.code[0][1];#1;
  if(!fault||config_valid)$fatal(1,"UE_ESCAPED");
  reset();prepare(1);beat(0);beat(1);reset();capture(0);lock();release_ok();
  // Malformed nv/lt is not a supported current compiler shape.
  prepare(0);expected[6:0]=7'd7;
  for(integer b=0;b<3;b=b+1)beat(b);
  repeat(4)@(negedge clk);if(!fault||config_valid)$fatal(1,"INVALID_SHAPE_ESCAPED");
  reset();prepare(1);expected[3000]=1;
  for(integer b=0;b<3;b=b+1)beat(b);
  @(negedge clk);if(!fault||config_valid)$fatal(1,"PADDING_ESCAPED");
  reset();prepare(1);beat(0);
  @(negedge clk);in_valid=1;in_beat=1;in_tag=16'h9020;in_data=expected[1024+:1024];
  @(posedge clk);#1;if(!fault||config_valid)$fatal(1,"TAG_ESCAPED");
  $display("PASS_CONFIG_SNAPSHOT exact2602 bits3beats checks%0d bothshapes immutable prelockCE lockedCEabort UE resetpartial shape padding tag",checks);$finish;
 end
endmodule
