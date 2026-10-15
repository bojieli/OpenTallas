`timescale 1ns/1ps
module tb_rom_relocate;
 parameter N=1;
 reg[766:0]vectors[0:N-1];
 reg[379:0]cmd;reg[5:0]stage;
 wire[379:0]actual;wire fault;
 reg[379:0]expected;reg expected_fault;
 string filename;integer i;
 ot_qwen_tp8_rom_relocate dut(.in_cmd(cmd),.in_stage(stage),.out_cmd(actual),.fault(fault));
 initial begin
  if(!$value$plusargs("VECTORS=%s",filename))$fatal(1,"missing actual vectors");
  $readmemh(filename,vectors);
  for(i=0;i<N;i=i+1)begin
   {expected_fault,expected,stage,cmd}=vectors[i];#1;
   if(actual!==expected||fault!==expected_fault)$fatal(1,"ROM RELOCATION vector=%0d stage=%0d localWCS=%0d gotWCS=%0d expectedWCS=%0d",i,stage,cmd[278:255],actual[278:255],expected[278:255]);
  end
  $display("ACTUAL_ROM_RELOCATION_PASS vectors=%0d",N);$finish;
 end
endmodule
