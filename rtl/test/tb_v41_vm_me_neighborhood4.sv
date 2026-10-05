`timescale 1ns/1ps
module tb;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,vm_rd_v=0,vm_pre_p=0;
  reg [14:0] vm_rd_base_word=0;
  reg [12:0] vm_pre_e=0;
  reg [3:0] vm_wr_v=0;
  reg [59:0] vm_wr_word_addr=0;
  reg [2047:0] vm_wr_word_data=0;
  reg [1:0] me_rd_rot=0;
  reg [7:0] me_rq_v=0;
  reg [111:0] me_rq_q=0;
  reg [31:0] me_rq_plg=0;
  reg [3:0] sink_ce=4'hf;
  wire [4095:0] sink_data;
  wire vm_rd_fault,vm_wr_fault,vm_collision_fault,cv_fault,cv_saturated;
  ot_v41_vm_me_neighborhood4 u (.*);
  integer k,seen=0;
  initial begin
    for(k=0;k<64;k=k+1) vm_wr_word_data[k*32+:32]=32'h3f800000;
    vm_wr_word_addr={15'd3,15'd2,15'd1,15'd0};
    repeat(4) @(negedge clk);
    rst_n=1;
    vm_wr_v=4'hf;
    @(negedge clk); vm_wr_v=0;
    repeat(5) @(negedge clk);
    vm_rd_v=1; vm_rd_base_word=0; vm_pre_e=13'd64; vm_pre_p=1;
    @(negedge clk); vm_rd_v=0; vm_pre_e=0; vm_pre_p=0;
    repeat(12) begin
      @(posedge clk); #1;
      if(u.cv_v) begin
        seen=seen+1;
        if(u.cv_e!==13'd64 || u.cv_p!==1) $fatal(1,"tag e=%d p=%d",u.cv_e,u.cv_p);
        for(k=0;k<64;k=k+1) if(u.cv_words[k*16+:16]!==16'h3f80)
          $fatal(1,"data %d %h",k,u.cv_words[k*16+:16]);
      end
    end
    if(seen!==1 || vm_rd_fault || vm_wr_fault || vm_collision_fault || cv_fault)
      $fatal(1,"seen %d faults %b%b%b%b",seen,vm_rd_fault,vm_wr_fault,vm_collision_fault,cv_fault);
    $display("PASS neighborhood data/tag beat"); $finish;
  end
endmodule
