`timescale 1ns/1ps
// Component gate at the declared mix/table input boundary. Tests all seven divider phases;
// does not qualify the projection, ingress SRAM path, quadrant clients or a full die.
module tb_hbm_hc_tail_unit_static;
  parameter integer MUT=0;
  reg clk=0; always #1 clk=~clk;
  reg rst_n=1,launch=0;
  reg [31:0] mixmem[0:23],expected[0:23];reg [255:0] tbl[0:11];
  reg [767:0] mixes,bases;reg [95:0] scales;
  wire result_v,fault;wire [767:0] result;
  integer cycle=0,launch_cycle,seen=0,bad=0,phase;
  ot_hbm_hc_tail_unit_static #(.MUT_PRE(MUT)) dut(.clk(clk),.rst_n(rst_n),.launch(launch),
    .mixes(mixes),.bases(bases),.scales(scales),.result_v(result_v),.result(result),.fault(fault));
  always @(posedge clk) cycle<=cycle+1;
  reg had_fault=0;
  always @(negedge clk) begin
    if(fault && !had_fault) begin
      $display("TAIL FIRST_FAULT cycle=%0d age=%0d own=%b tf=%b active=%b armed=%b captured=%b sage=%0d sl=%b cap=%b sv=%b sf=%b sinkfault=%b",cycle,dut.age,dut.own_fault,dut.tf,dut.active,dut.armed,dut.captured,dut.sage,dut.sl,dut.capture_q,dut.u_tail.sv,dut.u_tail.sf,dut.u_tail.sink_fault);
      had_fault=1;
    end
    if(result_v) $display("TAIL RESULT_PULSE cycle=%0d delta=%0d fault=%b",cycle,cycle-launch_cycle,fault);
  end
  initial begin
    #0.1; rst_n=0; // Explicit reset edge also reaches the derived clock domain.
    $readmemh("expmix.mem",mixmem);$readmemh("exptail.mem",expected);$readmemh("tbl.mem",tbl);
    for(integer i=0;i<24;i=i+1)mixes[i*32+:32]=mixmem[i];
    bases={tbl[10],tbl[9],tbl[8]};scales=tbl[11][95:0];
    repeat(4) @(negedge clk);rst_n=1;
    for(phase=0;phase<7;phase=phase+1)begin
      // Select the actual divider counter phase explicitly, before a fixed launch.
      wait(dut.cnt==phase);@(negedge clk);launch=1;launch_cycle=cycle;
      @(negedge clk);launch=0;
      repeat(495) @(negedge clk);
      if(!result_v || fault || cycle-launch_cycle!=496)
        $fatal(1,"TAIL CONTRACT phase=%0d delta=%0d valid=%0d fault=%0d",phase,cycle-launch_cycle,result_v,fault);
      for(integer j=0;j<24;j=j+1)if(result[j*32+:32] !== expected[j])begin
        bad=bad+1;
        if(bad<6)$display("TAIL MISMATCH phase=%0d word=%0d got=%08x expected=%08x",phase,j,result[j*32+:32],expected[j]);
      end
      seen=seen+1;$display("TAIL PHASE phase=%0d delta=%0d checked=24 bad=%0d",phase,cycle-launch_cycle,bad);
      repeat(4) @(negedge clk);
    end
    if(bad || seen!=7)$fatal(1,"TAIL FAIL bad=%0d seen=%0d",bad,seen);
    $display("HC_TAIL_UNIT PASS phases=7 words=168 fixed timing");$finish;
  end
  initial begin #20000;$fatal(1,"watchdog");end
endmodule
